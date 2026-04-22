"""Kokoro-as-default + TTFS budget tests (feature #18)."""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from nova.config import VoiceConfig, load_config
from nova.voice.tts import AudioBytes, create_tts, register_tts, time_to_first_sound_ms


class _InstantFakeTts:
    """Simulates Kokoro's <300ms TTFS by returning instantly."""

    sample_rate = 24000

    def synth(self, text: str) -> AudioBytes:
        return AudioBytes(pcm16=b"\x00\x01" * 512, sample_rate=self.sample_rate)

    def stream(self, text: str) -> Iterable[AudioBytes]:
        yield self.synth(text)


def test_voice_config_defaults_to_kokoro() -> None:
    voice = VoiceConfig()
    assert voice.tts_backend == "kokoro"
    assert voice.tts_ttfs_budget_ms == 300


def test_load_config_picks_kokoro_by_default(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("NOVA_VOICE__TTS_BACKEND", raising=False)
    cfg = load_config()
    assert cfg.voice.tts_backend == "kokoro"


def test_create_tts_default_is_kokoro() -> None:
    # "kokoro" must be the registered builder's default target.
    from nova.voice.tts import create_tts as _create

    # create_tts has default arg "kokoro" — verified by signature.
    sig = _create.__defaults__
    assert sig is not None
    assert "kokoro" in sig


def test_ttfs_helper_under_budget_with_fake_engine() -> None:
    register_tts("instant-fake", lambda **_: _InstantFakeTts())
    engine = create_tts("instant-fake")
    ttfs = time_to_first_sound_ms(engine, "Hi there.")
    assert ttfs < 300, f"TTFS {ttfs:.1f}ms exceeded 300ms budget"


def test_ttfs_helper_requires_non_empty_first_chunk() -> None:
    class EmptyFirstTts:
        sample_rate = 24000

        def synth(self, text: str) -> AudioBytes:
            return AudioBytes(pcm16=b"", sample_rate=self.sample_rate)

        def stream(self, text: str) -> Iterable[AudioBytes]:
            yield self.synth(text)

    register_tts("empty-fake", lambda **_: EmptyFirstTts())
    engine = create_tts("empty-fake")
    with pytest.raises(AssertionError):
        time_to_first_sound_ms(engine, "hi")
