"""Tests for nova.server.active_device."""

from __future__ import annotations

from nova.server.active_device import ActiveDevicePicker, WakeReport


def test_no_reports_picks_none() -> None:
    p = ActiveDevicePicker()
    assert p.pick() is None


def test_window_open_blocks_pick() -> None:
    p = ActiveDevicePicker(coalesce_window_s=10.0)
    p.submit(WakeReport(device_id="a", wake_confidence=0.9, timestamp=0.0))
    assert p.pick(now=1.0) is None  # still collecting


def test_pick_after_window_closes() -> None:
    p = ActiveDevicePicker(coalesce_window_s=0.5)
    p.submit(WakeReport(device_id="a", wake_confidence=0.9, timestamp=0.0))
    winner = p.pick(now=1.0)
    assert winner is not None
    assert winner.device_id == "a"


def test_pick_highest_confidence_when_proximity_equal() -> None:
    p = ActiveDevicePicker(coalesce_window_s=0.1)
    p.submit(WakeReport("a", 0.9, proximity_db=10, timestamp=0.0))
    p.submit(WakeReport("b", 0.5, proximity_db=10, timestamp=0.0))
    winner = p.pick(now=1.0)
    assert winner is not None
    assert winner.device_id == "a"


def test_pick_closer_device_with_similar_confidence() -> None:
    p = ActiveDevicePicker(coalesce_window_s=0.1)
    p.submit(WakeReport("far", 0.9, proximity_db=5, timestamp=0.0))
    p.submit(WakeReport("close", 0.9, proximity_db=50, timestamp=0.0))
    winner = p.pick(now=1.0)
    assert winner is not None
    assert winner.device_id == "close"


def test_clears_after_pick() -> None:
    p = ActiveDevicePicker(coalesce_window_s=0.1)
    p.submit(WakeReport("a", 0.9, timestamp=0.0))
    p.pick(now=1.0)
    assert p.reports() == []
    assert p.pick(now=2.0) is None


def test_is_window_open_when_no_reports() -> None:
    p = ActiveDevicePicker()
    assert p.is_window_open() is False


def test_window_starts_on_first_submit() -> None:
    p = ActiveDevicePicker(coalesce_window_s=1.0)
    p.submit(WakeReport("a", 0.5, timestamp=10.0))
    assert p.is_window_open(now=10.5) is True
    assert p.is_window_open(now=11.5) is False
