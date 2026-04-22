"""Tests for the wake-word abstraction."""

from __future__ import annotations

import time

from nova.voice.wake_word import (
    WakeEvent,
    WakeWordEngine,
    available_backends,
    create_engine,
    register_backend,
)


class FakeEngine:
    sample_rate = 16000

    def __init__(self, phrase: str = "hey_nova") -> None:
        self.phrase = phrase
        self.calls = 0

    def feed(self, pcm16: bytes) -> WakeEvent | None:
        self.calls += 1
        if b"TRIGGER" in pcm16:
            return WakeEvent(phrase=self.phrase, score=0.99, timestamp=time.time())
        return None

    def close(self) -> None:
        pass


def test_register_and_build_backend() -> None:
    register_backend("fake", lambda **kw: FakeEngine(**kw))  # type: ignore[arg-type]
    assert "fake" in available_backends()
    engine = create_engine("fake")
    assert isinstance(engine, WakeWordEngine)


def test_unknown_backend_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        create_engine("does-not-exist")


def test_builtin_backends_registered() -> None:
    names = available_backends()
    assert "openwakeword" in names
    assert "porcupine" in names


def test_fake_engine_triggers_on_marker() -> None:
    register_backend("fake", lambda **kw: FakeEngine(**kw))  # type: ignore[arg-type]
    engine = create_engine("fake")
    assert engine.feed(b"silence...") is None
    event = engine.feed(b"...TRIGGER...")
    assert event is not None
    assert event.phrase == "hey_nova"
    assert event.score > 0.9
