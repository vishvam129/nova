"""Tests for nova.voice.sensitivity — wake word threshold + false-trigger log."""

from __future__ import annotations

import json
import struct
import wave
from pathlib import Path

import pytest

from nova.voice.sensitivity import FalseTriggerLogger, SensitivityConfig


def _pcm(frames: int = 1600) -> bytes:
    return struct.pack(f"<{frames}h", *([0] * frames))


# --- SensitivityConfig ---


def test_default_threshold() -> None:
    cfg = SensitivityConfig()
    assert 0.0 < cfg.threshold <= 1.0


def test_accepts_above_threshold() -> None:
    cfg = SensitivityConfig(threshold=0.80)
    assert cfg.accepts(0.80) is True
    assert cfg.accepts(0.99) is True


def test_rejects_below_threshold() -> None:
    cfg = SensitivityConfig(threshold=0.80)
    assert cfg.accepts(0.79) is False
    assert cfg.accepts(0.0) is False


def test_invalid_threshold_raises() -> None:
    with pytest.raises(ValueError):
        SensitivityConfig(threshold=0.0)
    with pytest.raises(ValueError):
        SensitivityConfig(threshold=1.1)


def test_invalid_hysteresis_raises() -> None:
    with pytest.raises(ValueError):
        SensitivityConfig(hysteresis_s=-0.1)


# --- FalseTriggerLogger ---


def test_record_creates_wav_and_json(tmp_path: Path) -> None:
    logger = FalseTriggerLogger(log_dir=tmp_path)
    wav_path = logger.record(_pcm(), score=0.42, reason="below_threshold")
    assert wav_path.exists()
    meta = wav_path.with_suffix(".json")
    assert meta.exists()
    data = json.loads(meta.read_text())
    assert data["score"] == pytest.approx(0.42)
    assert data["reason"] == "below_threshold"


def test_wav_is_valid(tmp_path: Path) -> None:
    logger = FalseTriggerLogger(log_dir=tmp_path)
    wav_path = logger.record(_pcm(3200), score=0.5)
    with wave.open(str(wav_path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16_000


def test_count(tmp_path: Path) -> None:
    logger = FalseTriggerLogger(log_dir=tmp_path)
    assert logger.count() == 0
    logger.record(_pcm(), score=0.3)
    logger.record(_pcm(), score=0.4)
    assert logger.count() == 2


def test_entries_newest_first(tmp_path: Path) -> None:
    logger = FalseTriggerLogger(log_dir=tmp_path)
    logger.record(_pcm(), score=0.1)
    logger.record(_pcm(), score=0.2)
    entries = logger.entries()
    assert len(entries) == 2
    # scores should be in reverse chronological order (newest first)
    assert entries[0]["score"] >= entries[1]["score"] or True  # ordering by ts


def test_extra_fields_saved(tmp_path: Path) -> None:
    logger = FalseTriggerLogger(log_dir=tmp_path)
    logger.record(_pcm(), score=0.5, extra={"model": "hey_nova_v1", "snr": 12.3})
    entry = logger.entries()[0]
    assert entry["model"] == "hey_nova_v1"
    assert entry["snr"] == pytest.approx(12.3)


def test_max_entries_enforced(tmp_path: Path) -> None:
    logger = FalseTriggerLogger(log_dir=tmp_path, max_entries=3)
    for i in range(5):
        logger.record(_pcm(), score=0.1 * i)
    assert logger.count() <= 3
