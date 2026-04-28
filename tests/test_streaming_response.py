"""Tests for nova.brain.streaming.StreamingResponse."""

from __future__ import annotations

from nova.brain.streaming import StreamingResponse


def test_yields_all_tokens_when_not_cancelled() -> None:
    s = StreamingResponse(token_source=iter(["a", "b", "c"]))
    assert list(s) == ["a", "b", "c"]
    assert s.emitted_text == "abc"


def test_cancel_stops_iteration() -> None:
    tokens = ["a", "b", "c", "d"]
    s = StreamingResponse(token_source=iter(tokens))
    out: list[str] = []
    for tok in s:
        out.append(tok)
        if tok == "b":
            s.cancel()
    assert out == ["a", "b"]
    assert s.cancelled is True


def test_cancel_invokes_callback() -> None:
    called: list[bool] = []
    s = StreamingResponse(token_source=iter([]), on_cancel=lambda: called.append(True))
    s.cancel()
    assert called == [True]


def test_cancel_idempotent() -> None:
    called: list[bool] = []
    s = StreamingResponse(token_source=iter([]), on_cancel=lambda: called.append(True))
    s.cancel()
    s.cancel()
    assert called == [True]


def test_cancel_callback_exception_swallowed() -> None:
    def boom() -> None:
        raise RuntimeError("nope")

    s = StreamingResponse(token_source=iter([]), on_cancel=boom)
    s.cancel()  # must not raise
    assert s.cancelled is True


def test_emitted_text_empty_until_iterated() -> None:
    s = StreamingResponse(token_source=iter(["x"]))
    assert s.emitted_text == ""
    list(s)
    assert s.emitted_text == "x"
