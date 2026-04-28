"""Tests for nova.ui.overlay."""

from __future__ import annotations

from nova.ui.overlay import HudLine, HudLineKind, OverlayHud


def test_push_transcript() -> None:
    h = OverlayHud()
    line = h.push_transcript("hello world")
    assert line.kind is HudLineKind.TRANSCRIPT
    assert line.text == "hello world"
    assert h.lines() == [line]


def test_push_all_kinds() -> None:
    h = OverlayHud()
    h.push_transcript("t")
    h.push_thought("th")
    h.push_tool_call("open_app", "spotify")
    h.push_reply("hi")
    h.push_error("oops")
    kinds = {ln.kind for ln in h.lines()}
    assert kinds == {
        HudLineKind.TRANSCRIPT,
        HudLineKind.THOUGHT,
        HudLineKind.TOOL_CALL,
        HudLineKind.REPLY,
        HudLineKind.ERROR,
    }


def test_tool_call_formats_args() -> None:
    h = OverlayHud()
    line = h.push_tool_call("send_sms", "to=+1, body=hi")
    assert "send_sms" in line.text
    assert "to=+1" in line.text


def test_filter_by_kind() -> None:
    h = OverlayHud()
    h.push_transcript("a")
    h.push_thought("b")
    h.push_transcript("c")
    transcripts = h.filter(HudLineKind.TRANSCRIPT)
    assert len(transcripts) == 2


def test_max_lines_truncates_oldest() -> None:
    h = OverlayHud(max_lines=3)
    for i in range(5):
        h.push_transcript(str(i))
    texts = [ln.text for ln in h.lines()]
    assert texts == ["2", "3", "4"]


def test_clear() -> None:
    h = OverlayHud()
    h.push_transcript("x")
    h.clear()
    assert h.lines() == []


def test_observers_called_on_push() -> None:
    h = OverlayHud()
    seen: list[HudLine] = []
    h.subscribe(seen.append)
    h.push_transcript("x")
    h.push_thought("y")
    assert len(seen) == 2


def test_unsubscribe_stops_callbacks() -> None:
    h = OverlayHud()
    seen: list[HudLine] = []
    h.subscribe(seen.append)
    h.push_transcript("x")
    h.unsubscribe(seen.append)
    h.push_transcript("y")
    assert len(seen) == 1


def test_visibility_toggle() -> None:
    h = OverlayHud()
    assert h.visible is True
    h.hide()
    assert h.visible is False
    h.show()
    assert h.visible is True
