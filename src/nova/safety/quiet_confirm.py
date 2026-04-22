"""Quiet-confirm toast: 1s cancellable action prompt.

Shown as a small, unobtrusive toast on desktop (libnotify / NSAlert /
WinToast) and as a banner on mobile (Android notification, iOS
banner). During the ``timeout_ms`` window the user can tap/click to
cancel; if the window elapses without a cancel signal, the action
proceeds. The UI implementation is pluggable via a ``ToastPresenter``
callable.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class ToastOutcome(StrEnum):
    PROCEED = "proceed"
    CANCELLED = "cancelled"


ToastPresenter = Callable[[str, float], bool]
"""Display a toast and return True if the user cancelled before timeout."""


@dataclass
class QuietConfirmToast:
    """A single-shot 1s cancellable toast."""

    timeout_ms: int = 1000
    presenter: ToastPresenter | None = None

    def confirm(self, message: str) -> ToastOutcome:
        presenter = self.presenter or _default_console_presenter
        cancelled = presenter(message, self.timeout_ms / 1000.0)
        return ToastOutcome.CANCELLED if cancelled else ToastOutcome.PROCEED


def _default_console_presenter(message: str, timeout_s: float) -> bool:
    """Fallback: print + sleep. Never cancels (no interactive input)."""
    print(f"[nova] {message}  (proceeding in {timeout_s:.1f}s — press Ctrl+C to cancel)")
    try:
        time.sleep(timeout_s)
    except KeyboardInterrupt:
        return True
    return False


def threaded_presenter(cancel_flag: threading.Event) -> ToastPresenter:
    """Build a presenter backed by an externally-set cancel flag.

    Useful for GUIs: wire the toast's cancel button to ``flag.set()``
    and pass this presenter. The toast waits for either the timeout or
    the flag to fire.
    """

    def _present(_message: str, timeout_s: float) -> bool:
        cancel_flag.clear()
        cancel_flag.wait(timeout_s)
        return cancel_flag.is_set()

    return _present
