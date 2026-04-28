"""Android notification listener → brain context.

The Android NotificationListenerService streams every system notification
to the WebSocket; this module filters / dedupes / shapes them into the
brain's context window.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class Notification:
    package: str
    title: str
    body: str
    posted_at: datetime
    category: str = ""
    is_ongoing: bool = False

    MESSAGE_TYPE: str = field(default="notification", init=False, repr=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.MESSAGE_TYPE,
            "package": self.package,
            "title": self.title,
            "body": self.body,
            "posted_at": self.posted_at.isoformat(),
            "category": self.category,
            "is_ongoing": self.is_ongoing,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> Notification:
        return cls(
            package=str(d["package"]),
            title=str(d["title"]),
            body=str(d.get("body", "")),
            posted_at=datetime.fromisoformat(str(d["posted_at"])),
            category=str(d.get("category", "")),
            is_ongoing=bool(d.get("is_ongoing", False)),
        )


# Default ignore list — package noise we never want in context
_DEFAULT_IGNORE = frozenset(
    {
        "android",
        "com.android.systemui",
        "com.google.android.gms",
        "com.google.android.googlequicksearchbox",
    }
)


@dataclass
class NotificationFilter:
    """Drops noisy / system notifications and dedupes repeats."""

    ignore_packages: frozenset[str] = field(default_factory=lambda: _DEFAULT_IGNORE)
    dedupe_window_s: float = 30.0
    drop_ongoing: bool = True
    _recent: deque[tuple[datetime, str]] = field(default_factory=deque, init=False)

    def accept(self, n: Notification) -> bool:
        if n.package in self.ignore_packages:
            return False
        if self.drop_ongoing and n.is_ongoing:
            return False
        signature = f"{n.package}|{n.title}|{n.body}"
        cutoff = datetime.now() - timedelta(seconds=self.dedupe_window_s)
        while self._recent and self._recent[0][0] < cutoff:
            self._recent.popleft()
        for _ts, sig in self._recent:
            if sig == signature:
                return False
        self._recent.append((datetime.now(), signature))
        return True

    def reset(self) -> None:
        self._recent.clear()


@dataclass
class NotificationContext:
    """Recent accepted notifications for the brain to consult."""

    capacity: int = 25
    _items: deque[Notification] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        self._items = deque(maxlen=self.capacity)

    def add(self, n: Notification) -> None:
        self._items.append(n)

    def recent(self, limit: int | None = None) -> list[Notification]:
        items = list(self._items)
        if limit is None:
            return items
        return items[-limit:]

    def by_package(self, package: str) -> list[Notification]:
        return [n for n in self._items if n.package == package]

    def to_brain_summary(self, limit: int = 10) -> str:
        items = self.recent(limit)
        if not items:
            return "No recent notifications."
        lines = [f"Recent notifications ({len(items)}):"]
        for n in items:
            line = f"- [{n.package}] {n.title}"
            if n.body:
                line += f": {n.body}"
            lines.append(line)
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._items)


def decode_notification_frame(raw: str | bytes) -> Notification:
    return Notification.from_dict(json.loads(raw))


__all__ = [
    "Notification",
    "NotificationContext",
    "NotificationFilter",
    "decode_notification_frame",
]
