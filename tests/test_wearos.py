"""Tests for nova.mobile.wearos."""

from __future__ import annotations

import json

import pytest

from nova.mobile.wearos import (
    WatchMessageType,
    WatchNudge,
    WatchQuickReply,
    WatchWake,
    default_chips,
    encode,
)


def test_wake_roundtrip() -> None:
    w = WatchWake(confidence=0.92, battery_pct=80)
    out = WatchWake.from_dict(w.to_dict())
    assert out.confidence == pytest.approx(0.92)
    assert out.battery_pct == 80


def test_quick_reply_roundtrip() -> None:
    q = WatchQuickReply(chip_id="yes", text="yes")
    out = WatchQuickReply.from_dict(q.to_dict())
    assert out.chip_id == "yes"


def test_nudge_roundtrip_with_chips() -> None:
    n = WatchNudge(text="meeting in 5", suggested_chips=["yes", "snooze"])
    out = WatchNudge.from_dict(n.to_dict())
    assert out.suggested_chips == ["yes", "snooze"]
    assert out.vibration_ms == 200


def test_default_chips() -> None:
    chips = default_chips()
    assert "yes" in chips
    assert "no" in chips
    assert len(chips) == 4


def test_encode_dispatches_per_type() -> None:
    parsed = json.loads(encode(WatchWake(confidence=0.5)))
    assert parsed["type"] == WatchMessageType.WAKE


def test_encode_quick_reply() -> None:
    parsed = json.loads(encode(WatchQuickReply(chip_id="no", text="no")))
    assert parsed["type"] == WatchMessageType.QUICK_REPLY


def test_encode_nudge() -> None:
    parsed = json.loads(encode(WatchNudge(text="x")))
    assert parsed["type"] == WatchMessageType.NUDGE


def test_encode_unknown_raises() -> None:
    with pytest.raises(TypeError):
        encode(object())


def test_message_type_values() -> None:
    assert WatchMessageType.WAKE == "watch_wake"
    assert WatchMessageType.QUICK_REPLY == "watch_quick_reply"
