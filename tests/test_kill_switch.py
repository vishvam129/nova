"""Tests for KillSwitch."""

from __future__ import annotations

import threading
import time

from nova.safety.kill_switch import KillSwitch


def test_starts_not_tripped() -> None:
    k = KillSwitch()
    assert k.is_tripped is False


def test_trip_sets_event() -> None:
    k = KillSwitch()
    k.trip()
    assert k.is_tripped is True
    assert k.cancel_token.is_set()


def test_reset_clears_event() -> None:
    k = KillSwitch()
    k.trip()
    k.reset()
    assert k.is_tripped is False


def test_listeners_fire_on_trip() -> None:
    k = KillSwitch()
    fired: list[int] = []
    k.on_trip(lambda: fired.append(1))
    k.on_trip(lambda: fired.append(2))
    k.trip()
    assert fired == [1, 2]


def test_listener_exception_does_not_block_others() -> None:
    k = KillSwitch()
    fired: list[int] = []

    def boom() -> None:
        raise RuntimeError("nope")

    k.on_trip(boom)
    k.on_trip(lambda: fired.append(1))
    k.trip()
    assert fired == [1]


def test_match_phrase_trips() -> None:
    k = KillSwitch()
    assert k.match_phrase("please Nova STOP EVERYTHING now") is True
    assert k.is_tripped is True


def test_match_phrase_ignores_unrelated() -> None:
    k = KillSwitch()
    assert k.match_phrase("nova, open spotify") is False
    assert k.is_tripped is False


def test_wait_returns_true_when_tripped_soon() -> None:
    k = KillSwitch()

    def trip_soon() -> None:
        time.sleep(0.02)
        k.trip()

    threading.Thread(target=trip_soon).start()
    assert k.wait(timeout=1.0) is True


def test_wait_returns_false_on_timeout() -> None:
    k = KillSwitch()
    assert k.wait(timeout=0.01) is False
