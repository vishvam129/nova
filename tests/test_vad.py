"""Tests for VAD backends and the adaptive wrapper."""

from __future__ import annotations

import numpy as np

from nova.voice.vad import (
    AdaptiveVad,
    EnergyVad,
    available_vads,
    create_vad,
)


def _silence(frame_size: int = 480) -> bytes:
    return np.zeros(frame_size, dtype=np.int16).tobytes()


def _tone(frame_size: int = 480, amp: int = 10000) -> bytes:
    t = np.linspace(0, 2 * np.pi * 10, frame_size, dtype=np.float32)
    return (np.sin(t) * amp).astype(np.int16).tobytes()


def test_energy_vad_silence_low() -> None:
    vad = EnergyVad()
    assert vad.probability(_silence()) < 0.1


def test_energy_vad_tone_high() -> None:
    vad = EnergyVad(threshold=500.0)
    assert vad.probability(_tone()) > 0.5


def test_available_vads() -> None:
    names = available_vads()
    assert "energy" in names
    assert "silero" in names


def test_create_vad_unknown_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        create_vad("no-such-backend")


def test_adaptive_marks_speech_above_floor() -> None:
    energy = EnergyVad(threshold=500.0)
    adaptive = AdaptiveVad(energy, margin=0.1)
    # Warm up with silence so the noise floor stabilises low.
    for _ in range(50):
        adaptive.process(_silence())
    frame = adaptive.process(_tone())
    assert frame.is_speech
    assert frame.probability > 0.5


def test_adaptive_floor_updates_only_on_silence() -> None:
    energy = EnergyVad(threshold=500.0)
    adaptive = AdaptiveVad(energy, margin=0.1, decay=0.5, initial_floor=0.0)
    adaptive.process(_silence())
    floor_after_silence = adaptive.noise_floor
    adaptive.process(_tone())  # speech -> floor must not move
    assert adaptive.noise_floor == floor_after_silence


def test_create_vad_energy_adaptive_wraps() -> None:
    vad = create_vad("energy", adaptive=True)
    assert isinstance(vad, AdaptiveVad)
    assert vad.sample_rate == 16000
