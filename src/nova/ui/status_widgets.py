"""Status tray widgets: cost today, requests today, next reminder, last command.

These are pure-data accessors the tray menu pulls on each refresh.
The tray itself ships in nova.ui.tray; here we own only the strings
the user sees so they're easy to test.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


class _CostSource(Protocol):
    @property
    def spend_usd(self) -> float: ...
    @property
    def tokens(self) -> int: ...


@dataclass(frozen=True, slots=True)
class WidgetSnapshot:
    cost_today: str
    requests_today: str
    next_reminder: str
    last_command: str


@dataclass
class StatusWidgets:
    """Render the four tray widgets from the underlying live sources."""

    cost: _CostSource | None = None
    requests_today_fn: Callable[[], int] | None = None
    next_reminder_fn: Callable[[], tuple[str, datetime] | None] | None = None
    last_command: str = ""

    _request_count: int = field(default=0, init=False)

    def record_request(self) -> None:
        self._request_count += 1

    def set_last_command(self, text: str) -> None:
        self.last_command = text.strip()

    def cost_today(self) -> str:
        if self.cost is None:
            return "$0.00"
        return f"${self.cost.spend_usd:.2f}"

    def requests_today(self) -> str:
        n = self.requests_today_fn() if self.requests_today_fn else self._request_count
        return f"{n} requests"

    def next_reminder(self) -> str:
        if self.next_reminder_fn is None:
            return "no reminders"
        result = self.next_reminder_fn()
        if result is None:
            return "no reminders"
        text, when = result
        delta = when - datetime.now()
        minutes = max(0, int(delta.total_seconds() / 60))
        if minutes < 60:
            return f"{text} (in {minutes}m)"
        hours = minutes // 60
        return f"{text} (in {hours}h)"

    def last_command_label(self) -> str:
        if not self.last_command:
            return "no recent command"
        if len(self.last_command) <= 40:
            return self.last_command
        return self.last_command[:37] + "..."

    def snapshot(self) -> WidgetSnapshot:
        return WidgetSnapshot(
            cost_today=self.cost_today(),
            requests_today=self.requests_today(),
            next_reminder=self.next_reminder(),
            last_command=self.last_command_label(),
        )


__all__ = ["StatusWidgets", "WidgetSnapshot"]
