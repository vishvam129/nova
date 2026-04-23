"""Emergency stop (kill switch).

Provides a single ``KillSwitch`` event consulted by every long-running
agent, tool executor, or playback loop. Triggers:

* ``trip()`` — programmatic (hotkey handler, UI button).
* ``match_phrase()`` — STT backend feeds each transcript segment; a
  match fires ``trip()`` so the agent halts within one frame.

Callers should check ``is_tripped`` at loop boundaries and pass a
``cancel_token`` into blocking waits (backed by the underlying
``threading.Event``).
"""

from __future__ import annotations

import contextlib
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass, field

DEFAULT_PHRASES: tuple[str, ...] = (
    "nova stop everything",
    "nova kill switch",
    "nova abort",
    "nova emergency stop",
)


@dataclass
class KillSwitch:
    phrases: tuple[str, ...] = DEFAULT_PHRASES
    _event: threading.Event = field(default_factory=threading.Event, init=False)
    _listeners: list[Callable[[], None]] = field(default_factory=list, init=False)

    @property
    def is_tripped(self) -> bool:
        return self._event.is_set()

    @property
    def cancel_token(self) -> threading.Event:
        return self._event

    def trip(self, reason: str | None = None) -> None:
        self._event.set()
        for cb in list(self._listeners):
            with contextlib.suppress(Exception):
                cb()

    def reset(self) -> None:
        self._event.clear()

    def on_trip(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def match_phrase(self, transcript: str) -> bool:
        norm = re.sub(r"[^a-z ]+", "", transcript.lower()).strip()
        for phrase in self.phrases:
            if phrase in norm:
                self.trip(reason=f"phrase:{phrase}")
                return True
        return False

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout)


__all__ = ["DEFAULT_PHRASES", "KillSwitch"]
