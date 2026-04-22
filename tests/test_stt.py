"""Tests for the STT engine abstraction (hardware-free)."""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from nova.voice.stt import (
    SttEngine,
    Transcript,
    available_stts,
    create_stt,
    register_stt,
)


class FakeStt:
    sample_rate = 16000

    def __init__(self, reply: str = "hello world") -> None:
        self.reply = reply
        self.calls = 0

    def transcribe(self, pcm16: bytes) -> Transcript:
        self.calls += 1
        return Transcript(text=self.reply, language="en", confidence=0.9)

    def stream(self, frames: Iterable[bytes]) -> Iterable[Transcript]:
        for _ in frames:
            yield self.transcribe(b"")


def test_builtin_backends_registered() -> None:
    names = available_stts()
    for n in ("whisper", "faster-whisper", "distil-whisper", "moonshine", "parakeet"):
        assert n in names


def test_unknown_backend_raises() -> None:
    with pytest.raises(ValueError):
        create_stt("no-such-stt")


def test_register_and_create_custom_backend() -> None:
    register_stt("fake", lambda **kw: FakeStt(**kw))  # type: ignore[arg-type]
    engine = create_stt("fake")
    assert isinstance(engine, SttEngine)
    result = engine.transcribe(b"\x00\x00" * 16000)
    assert isinstance(result, Transcript)
    assert result.text == "hello world"
    assert result.language == "en"


def test_stream_yields_per_frame() -> None:
    register_stt("fake", lambda **kw: FakeStt(**kw))  # type: ignore[arg-type]
    engine = create_stt("fake")
    outs = list(engine.stream([b"a", b"b", b"c"]))
    assert len(outs) == 3
    assert all(t.text == "hello world" for t in outs)


def test_transcript_is_immutable() -> None:
    t = Transcript(text="hi", language="en")
    with pytest.raises(AttributeError):
        t.text = "nope"  # type: ignore[misc]
