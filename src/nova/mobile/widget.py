"""Android home-screen widget: last 5 actions + quick-redo.

Python side owns the data model the Glance widget renders.  The Android
``NovaActionsWidget`` reads ``WidgetState`` over the WebSocket and lays
out one row per action with a redo button bound to ``RedoEvent``.
"""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class WidgetAction:
    id: str
    label: str
    timestamp: datetime
    succeeded: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "timestamp": self.timestamp.isoformat(),
            "succeeded": self.succeeded,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> WidgetAction:
        return cls(
            id=str(d["id"]),
            label=str(d["label"]),
            timestamp=datetime.fromisoformat(str(d["timestamp"])),
            succeeded=bool(d.get("succeeded", True)),
        )


@dataclass
class WidgetState:
    """Most-recent-N action ring buffer feeding the widget."""

    capacity: int = 5
    _items: deque[WidgetAction] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        self._items = deque(maxlen=self.capacity)

    def push(self, action: WidgetAction) -> None:
        self._items.append(action)

    def push_many(self, actions: Iterable[WidgetAction]) -> None:
        for a in actions:
            self.push(a)

    def actions(self) -> list[WidgetAction]:
        # Newest first — matches widget render order
        return list(reversed(self._items))

    def find(self, action_id: str) -> WidgetAction | None:
        for a in self._items:
            if a.id == action_id:
                return a
        return None

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "widget_state",
            "actions": [a.to_dict() for a in self.actions()],
        }

    def encode(self) -> str:
        return json.dumps(self.to_dict())

    def __len__(self) -> int:
        return len(self._items)


@dataclass
class RedoEvent:
    """User tapped the redo button on a widget row."""

    action_id: str
    timestamp: datetime = field(default_factory=datetime.now)

    MESSAGE_TYPE: str = field(default="widget_redo", init=False, repr=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.MESSAGE_TYPE,
            "action_id": self.action_id,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> RedoEvent:
        return cls(
            action_id=str(d["action_id"]),
            timestamp=datetime.fromisoformat(str(d["timestamp"])),
        )


__all__ = ["RedoEvent", "WidgetAction", "WidgetState"]
