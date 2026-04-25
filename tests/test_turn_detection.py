"""Tests for nova.voice.turn_detection — VAD + model-based turn detectors."""

from __future__ import annotations

import struct
import time

import pytest

from nova.voice.turn_detection import (
    HybridTurnDetector,
    ModelTurnDetector,
    TurnDetector,
    VadTurnDetector,
)


def _silence(frames: int = 800) -> bytes:
    return struct.pack(f"<{frames}h", *([0] * frames))


def _loud(frames: int = 800, amplitude: int = 8000) -> bytes:
    return struct.pack(f"<{frames}h", *([amplitude] * frames))


# --- Protocol conformance ---


def test_vad_implements_protocol() -> None:
    assert isinstance(VadTurnDetector(), TurnDetector)


def test_model_implements_protocol() -> None:
    assert isinstance(ModelTurnDetector(), TurnDetector)


def test_hybrid_implements_protocol() -> None:
    assert isinstance(HybridTurnDetector(), TurnDetector)


# --- VadTurnDetector ---


def test_vad_not_complete_initially() -> None:
    det = VadTurnDetector(silence_ms=100)
    assert det.is_turn_complete() is False


def test_vad_not_complete_during_speech() -> None:
    det = VadTurnDetector(energy_threshold=0.01, silence_ms=50)
    for _ in range(10):
        det.push_audio(_loud())
    assert det.is_turn_complete() is False


def test_vad_complete_after_silence(monkeypatch: pytest.MonkeyPatch) -> None:
    det = VadTurnDetector(energy_threshold=0.5, silence_ms=100)
    t = [0.0]

    def mock_monotonic() -> float:
        return t[0]

    monkeypatch.setattr("nova.voice.turn_detection.time.monotonic", mock_monotonic)

    det.push_audio(_silence())  # silence_start = 0.0
    t[0] = 0.15  # 150 ms later
    det.push_audio(_silence())
    assert det.is_turn_complete() is True


def test_vad_reset_clears_state() -> None:
    det = VadTurnDetector(energy_threshold=0.5, silence_ms=10)
    det.push_audio(_silence())
    time.sleep(0.02)
    det.push_audio(_silence())
    det.reset()
    assert det.is_turn_complete() is False


def test_vad_speech_resets_silence_timer() -> None:
    det = VadTurnDetector(energy_threshold=0.01, silence_ms=50)
    det.push_audio(_silence())
    det.push_audio(_loud())  # resets timer
    assert det.is_turn_complete() is False


def test_vad_latency_ms() -> None:
    det = VadTurnDetector(silence_ms=800)
    assert det.latency_ms == pytest.approx(800.0)


# --- ModelTurnDetector (no onnxruntime installed — push_audio is a no-op) ---


def test_model_detector_no_onnx_does_not_crash() -> None:
    det = ModelTurnDetector()
    det.push_audio(_silence())  # onnxruntime missing → silently no-op
    assert det.is_turn_complete() is False


def test_model_latency_ms() -> None:
    assert ModelTurnDetector().latency_ms == pytest.approx(250.0)


def test_model_reset() -> None:
    det = ModelTurnDetector()
    det.push_audio(_silence())
    det.reset()
    assert det.is_turn_complete() is False


# --- HybridTurnDetector ---


def test_hybrid_falls_back_to_vad() -> None:
    det = HybridTurnDetector()
    det.push_audio(_silence())  # model probe fails → falls back to VAD
    assert det.active_backend == "VadTurnDetector"


def test_hybrid_not_complete_during_speech() -> None:
    det = HybridTurnDetector(energy_threshold=0.01, vad_silence_ms=500)
    for _ in range(5):
        det.push_audio(_loud())
    assert det.is_turn_complete() is False


def test_hybrid_reset() -> None:
    det = HybridTurnDetector()
    det.push_audio(_silence())
    det.reset()
    assert det.is_turn_complete() is False
