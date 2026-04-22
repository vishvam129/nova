"""Tests for barge-in state machine."""

from __future__ import annotations

import numpy as np

from nova.voice.bargein import BargeInPlayer, PlaybackState, _attenuate
from nova.voice.tts import AudioBytes
from nova.voice.vad import AdaptiveVad, EnergyVad


def _silence(ms: int = 30, sr: int = 16000) -> bytes:
    return np.zeros(sr * ms // 1000, dtype=np.int16).tobytes()


def _speech(ms: int = 30, sr: int = 16000, amp: int = 15000) -> bytes:
    t = np.linspace(0, 2 * np.pi * 20, sr * ms // 1000, dtype=np.float32)
    return (np.sin(t) * amp).astype(np.int16).tobytes()


def _make_player(**kw) -> BargeInPlayer:  # type: ignore[no-untyped-def]
    vad = AdaptiveVad(EnergyVad(threshold=500.0), margin=0.05, initial_floor=0.0)
    return BargeInPlayer(vad=vad, **kw)


def test_starts_playing() -> None:
    player = _make_player()
    assert player.state == PlaybackState.PLAYING


def test_transitions_to_ducked_then_stopped() -> None:
    player = _make_player(duck_after_ms=100, stop_after_ms=300)
    clock = [0.0]

    def now() -> float:
        return clock[0]

    # Warm up noise floor with silence.
    for _ in range(30):
        player.observe(_silence(), now=now)
    clock[0] = 1.0
    player.observe(_speech(), now=now)
    clock[0] = 1.15  # 150ms of speech -> duck
    assert player.observe(_speech(), now=now) == PlaybackState.DUCKED
    clock[0] = 1.35  # 350ms of speech -> stop
    assert player.observe(_speech(), now=now) == PlaybackState.STOPPED


def test_recovers_from_ducked_when_silence_returns() -> None:
    player = _make_player(duck_after_ms=100, stop_after_ms=500)
    clock = [0.0]

    def now() -> float:
        return clock[0]

    for _ in range(30):
        player.observe(_silence(), now=now)
    clock[0] = 1.0
    player.observe(_speech(), now=now)
    clock[0] = 1.15
    assert player.observe(_speech(), now=now) == PlaybackState.DUCKED
    clock[0] = 1.2
    assert player.observe(_silence(), now=now) == PlaybackState.PLAYING


def test_apply_returns_none_when_stopped() -> None:
    player = _make_player()
    player._state = PlaybackState.STOPPED
    assert player.apply(AudioBytes(pcm16=b"\x00" * 100, sample_rate=16000)) is None


def test_apply_attenuates_when_ducked() -> None:
    player = _make_player()
    player._state = PlaybackState.DUCKED
    loud = (np.ones(100, dtype=np.int16) * 16000).tobytes()
    out = player.apply(AudioBytes(pcm16=loud, sample_rate=16000))
    assert out is not None
    samples = np.frombuffer(out.pcm16, dtype=np.int16)
    assert samples.max() < 16000


def test_attenuate_halves_amplitude() -> None:
    loud = (np.ones(100, dtype=np.int16) * 10000).tobytes()
    audio = AudioBytes(pcm16=loud, sample_rate=16000)
    out = _attenuate(audio, 0.5)
    samples = np.frombuffer(out.pcm16, dtype=np.int16)
    assert abs(int(samples[0]) - 5000) <= 1


def test_play_stops_yielding_after_stop() -> None:
    player = _make_player()
    player._state = PlaybackState.STOPPED
    chunks = list(player.play(iter([AudioBytes(pcm16=b"x", sample_rate=16000)])))
    assert chunks == []
