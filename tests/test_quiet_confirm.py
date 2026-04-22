"""Tests for QuietConfirmToast."""

from __future__ import annotations

import threading
import time

from nova.safety.quiet_confirm import QuietConfirmToast, ToastOutcome, threaded_presenter


def test_no_cancel_proceeds() -> None:
    toast = QuietConfirmToast(timeout_ms=50, presenter=lambda _m, _t: False)
    assert toast.confirm("delete 3 files?") is ToastOutcome.PROCEED


def test_cancel_returns_cancelled() -> None:
    toast = QuietConfirmToast(timeout_ms=50, presenter=lambda _m, _t: True)
    assert toast.confirm("push force?") is ToastOutcome.CANCELLED


def test_threaded_presenter_cancels_when_flag_fires() -> None:
    flag = threading.Event()
    presenter = threaded_presenter(flag)
    toast = QuietConfirmToast(timeout_ms=500, presenter=presenter)

    def cancel_soon() -> None:
        time.sleep(0.05)
        flag.set()

    threading.Thread(target=cancel_soon).start()
    assert toast.confirm("risky") is ToastOutcome.CANCELLED


def test_threaded_presenter_proceeds_on_timeout() -> None:
    flag = threading.Event()
    toast = QuietConfirmToast(timeout_ms=50, presenter=threaded_presenter(flag))
    assert toast.confirm("safe-ish") is ToastOutcome.PROCEED


def test_presenter_receives_message_and_timeout() -> None:
    captured: list[tuple[str, float]] = []

    def presenter(msg: str, timeout_s: float) -> bool:
        captured.append((msg, timeout_s))
        return False

    QuietConfirmToast(timeout_ms=750, presenter=presenter).confirm("do thing")
    assert captured == [("do thing", 0.75)]
