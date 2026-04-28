"""Floating overlay HUD: live transcript, agent thoughts, tool calls.

Backend-agnostic: ``OverlayHud`` holds state, observers re-render.  The
real overlay (Qt / Tauri / GTK) subscribes via ``subscribe()`` and gets
called whenever the state changes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class HudLineKind(StrEnum):
    TRANSCRIPT = "transcript"
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    REPLY = "reply"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class HudLine:
    kind: HudLineKind
    text: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OverlayHud:
    """Mutable HUD state with observer pub/sub."""

    max_lines: int = 50
    _lines: list[HudLine] = field(default_factory=list, init=False)
    _observers: list[Callable[[HudLine], None]] = field(default_factory=list, init=False)
    _visible: bool = field(default=True, init=False)

    # ---- writes ----

    def push_transcript(self, text: str) -> HudLine:
        return self._push(HudLine(HudLineKind.TRANSCRIPT, text))

    def push_thought(self, text: str) -> HudLine:
        return self._push(HudLine(HudLineKind.THOUGHT, text))

    def push_tool_call(self, name: str, args: str = "") -> HudLine:
        text = f"{name}({args})" if args else name
        return self._push(HudLine(HudLineKind.TOOL_CALL, text))

    def push_reply(self, text: str) -> HudLine:
        return self._push(HudLine(HudLineKind.REPLY, text))

    def push_error(self, text: str) -> HudLine:
        return self._push(HudLine(HudLineKind.ERROR, text))

    def clear(self) -> None:
        self._lines.clear()

    def show(self) -> None:
        self._visible = True

    def hide(self) -> None:
        self._visible = False

    # ---- reads ----

    def lines(self) -> list[HudLine]:
        return list(self._lines)

    def filter(self, kind: HudLineKind) -> list[HudLine]:
        return [ln for ln in self._lines if ln.kind is kind]

    @property
    def visible(self) -> bool:
        return self._visible

    # ---- pub/sub ----

    def subscribe(self, observer: Callable[[HudLine], None]) -> None:
        self._observers.append(observer)

    def unsubscribe(self, observer: Callable[[HudLine], None]) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    # ---- internals ----

    def _push(self, line: HudLine) -> HudLine:
        self._lines.append(line)
        if len(self._lines) > self.max_lines:
            self._lines = self._lines[-self.max_lines :]
        for obs in list(self._observers):
            obs(line)
        return line


__all__ = ["HudLine", "HudLineKind", "OverlayHud"]
