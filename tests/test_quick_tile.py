"""Tests for nova.mobile.quick_tile."""

from __future__ import annotations

from nova.mobile.quick_tile import (
    TileState,
    TileTapEvent,
    label_for,
    next_state_after_tap,
)


def test_label_for_each_state() -> None:
    assert label_for(TileState.INACTIVE) == "Nova"
    assert "Listening" in label_for(TileState.LISTENING)
    assert "Thinking" in label_for(TileState.THINKING)
    assert label_for(TileState.SPEAKING) == "Speaking"
    assert "retry" in label_for(TileState.ERROR)


def test_tap_inactive_starts_listening() -> None:
    assert next_state_after_tap(TileState.INACTIVE) is TileState.LISTENING


def test_tap_listening_cancels() -> None:
    assert next_state_after_tap(TileState.LISTENING) is TileState.INACTIVE


def test_tap_speaking_barges_in() -> None:
    assert next_state_after_tap(TileState.SPEAKING) is TileState.INACTIVE


def test_tap_thinking_is_noop() -> None:
    assert next_state_after_tap(TileState.THINKING) is TileState.THINKING


def test_event_roundtrip() -> None:
    e = TileTapEvent(
        source="quick_tile",
        current_state=TileState.SPEAKING,
        extras={"app": "spotify"},
    )
    out = TileTapEvent.from_dict(e.to_dict())
    assert out.source == "quick_tile"
    assert out.current_state is TileState.SPEAKING
    assert out.extras == {"app": "spotify"}


def test_event_message_type() -> None:
    e = TileTapEvent(source="bubble", current_state=TileState.INACTIVE)
    assert e.to_dict()["type"] == "quick_tile_tap"


def test_event_encode_is_json() -> None:
    import json as j

    e = TileTapEvent(source="bubble", current_state=TileState.INACTIVE)
    parsed = j.loads(e.encode())
    assert parsed["source"] == "bubble"
