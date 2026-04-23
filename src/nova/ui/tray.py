"""System-tray controller.

Holds tray state (mic status, last action, menu items) independent of
any icon backend so logic can be unit-tested without a display.
``to_pystray`` converts the spec into a real ``pystray`` icon when
called on a machine that actually has a desktop.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TrayStatus(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class MenuItem:
    label: str
    action: Callable[[], None]
    checked: bool | None = None


@dataclass
class TrayController:
    title: str = "Nova"
    _status: TrayStatus = TrayStatus.IDLE
    _last_action: str = ""
    _items: list[MenuItem] = field(default_factory=list)
    _observers: list[Callable[[TrayStatus], None]] = field(default_factory=list, init=False)

    @property
    def status(self) -> TrayStatus:
        return self._status

    @property
    def last_action(self) -> str:
        return self._last_action

    def set_status(self, status: TrayStatus) -> None:
        self._status = status
        for obs in list(self._observers):
            obs(status)

    def note_action(self, text: str) -> None:
        self._last_action = text

    def add_item(self, item: MenuItem) -> None:
        self._items.append(item)

    def menu(self) -> list[MenuItem]:
        return list(self._items)

    def tooltip(self) -> str:
        base = f"{self.title} — {self._status.value}"
        if self._last_action:
            return f"{base}\n{self._last_action}"
        return base

    def subscribe(self, observer: Callable[[TrayStatus], None]) -> None:
        self._observers.append(observer)

    def to_pystray(self) -> Any:  # pragma: no cover
        from pystray import Icon, Menu
        from pystray import MenuItem as PItem

        def _build() -> Menu:
            items = [PItem(i.label, lambda _icon, _item, i=i: i.action()) for i in self._items]
            return Menu(*items)

        return Icon(self.title, title=self.tooltip(), menu=_build())


__all__ = ["MenuItem", "TrayController", "TrayStatus"]
