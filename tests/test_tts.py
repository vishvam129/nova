"""Tests for the TTS engine abstraction (hardware-free)."""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from nova.voice.tts import (
    AudioBytes,
    TtsEngine,
    available_ttses,
    create_tts,
    register_tts,
    split_sentences,
)


class FakeTts:
    sample_rate = 16000

    def __init__(self, prefix: str = "AUDIO:") -> None:
        self.prefix = prefix

    def synth(self, text: str) -> AudioBytes:
        return AudioBytes(pcm16=(self.prefix + text).encode(), sample_rate=self.sample_rate)

    def stream(self, text: str) -> Iterable[AudioBytes]:
        for s in split_sentences(text):
            yield self.synth(s)


def test_builtin_backends_registered() -> None:
    names = available_ttses()
    for n in ("piper", "kokoro", "styletts2", "xtts", "elevenlabs"):
        assert n in names


def test_unknown_backend_raises() -> None:
    with pytest.raises(ValueError):
        create_tts("no-such-tts")


def test_register_and_create_custom_backend() -> None:
    register_tts("fake-tts", lambda **kw: FakeTts(**kw))  # type: ignore[arg-type]
    engine = create_tts("fake-tts")
    assert isinstance(engine, TtsEngine)
    audio = engine.synth("hello")
    assert isinstance(audio, AudioBytes)
    assert audio.sample_rate == 16000
    assert audio.pcm16 == b"AUDIO:hello"


def test_stream_yields_per_sentence() -> None:
    register_tts("fake-tts", lambda **kw: FakeTts(**kw))  # type: ignore[arg-type]
    engine = create_tts("fake-tts")
    chunks = list(engine.stream("Hello there. How are you? Fine."))
    assert len(chunks) == 3
    texts = [c.pcm16.decode() for c in chunks]
    assert "Hello there." in texts[0]
    assert "How are you?" in texts[1]
    assert "Fine" in texts[2]


def test_split_sentences_handles_newlines_and_punct() -> None:
    out = split_sentences("One. Two!\nThree? four")
    assert out == ["One.", "Two!", "Three?", "four"]


def test_audio_bytes_is_immutable() -> None:
    a = AudioBytes(pcm16=b"\x00\x00", sample_rate=16000)
    with pytest.raises(AttributeError):
        a.sample_rate = 8000  # type: ignore[misc]
