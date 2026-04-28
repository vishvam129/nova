"""Tests for nova.voice.streaming_stt — StreamingPipeline."""

from __future__ import annotations

from nova.voice.streaming_stt import Final, Partial, StreamingPipeline, stream


class _Echo:
    def transcribe(self, pcm: bytes) -> str:
        words = max(1, len(pcm) // 4800)
        return " ".join(["word"] * words)


def test_push_returns_partial_after_threshold() -> None:
    p = StreamingPipeline(transcriber=_Echo(), partial_every_ms=100)
    chunk = b"\x00" * (16_000 * 2 // 10)
    evt = p.push(chunk)
    assert isinstance(evt, Partial)


def test_push_no_event_below_threshold() -> None:
    p = StreamingPipeline(transcriber=_Echo(), partial_every_ms=300)
    assert p.push(b"\x00" * 100) is None


def test_partial_only_when_text_changes() -> None:
    class Static:
        def transcribe(self, pcm: bytes) -> str:
            return "same"

    p = StreamingPipeline(transcriber=Static(), partial_every_ms=10)
    chunk = b"\x00" * 1000
    first = p.push(chunk)
    second = p.push(chunk)
    assert isinstance(first, Partial)
    assert second is None


def test_finalize_returns_final() -> None:
    p = StreamingPipeline(transcriber=_Echo())
    p.push(b"\x00" * 4800)
    f = p.finalize()
    assert isinstance(f, Final)
    assert "word" in f.text


def test_finalize_resets() -> None:
    p = StreamingPipeline(transcriber=_Echo())
    p.push(b"\x00" * 4800)
    p.finalize()
    assert len(p._buffer) == 0


def test_stream_drives_pipeline() -> None:
    p = StreamingPipeline(transcriber=_Echo(), partial_every_ms=50)
    events: list[Partial | Final] = []
    chunks = iter([b"\x00" * 4800] * 3)
    stream(p, chunks, events.append)
    assert any(isinstance(e, Partial) for e in events)
    assert isinstance(events[-1], Final)
