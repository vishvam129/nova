"""Tests for nova.voice.wake_word_training — synthetic data pipeline."""

from __future__ import annotations

import shutil
import struct
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

from nova.voice.wake_word_training import (
    AugmentationConfig,
    PiperSynthesizer,
    WakeWordDataPipeline,
    augment_wav,
    wav_duration_seconds,
)


def _write_wav(path: Path, duration_frames: int = 1600, rate: int = 16_000) -> None:
    """Write a minimal valid mono 16-bit WAV file."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack(f"<{duration_frames}h", *([0] * duration_frames)))


def test_wav_duration_seconds(tmp_path: Path) -> None:
    wav = tmp_path / "test.wav"
    _write_wav(wav, duration_frames=16_000)
    assert abs(wav_duration_seconds(wav) - 1.0) < 0.01


def test_augment_wav_no_sox_copies(tmp_path: Path) -> None:
    src = tmp_path / "src.wav"
    dst = tmp_path / "dst.wav"
    _write_wav(src)
    with patch("shutil.which", return_value=None):
        result = augment_wav(src, dst, AugmentationConfig())
    assert result == dst
    assert dst.exists()


def test_augment_wav_with_sox(tmp_path: Path) -> None:
    src = tmp_path / "src.wav"
    dst = tmp_path / "dst.wav"
    _write_wav(src)
    shutil.copy2(src, dst)

    with (
        patch("shutil.which", return_value="/usr/bin/sox"),
        patch("nova.voice.wake_word_training.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        augment_wav(src, dst, AugmentationConfig(reverb_prob=0.0))
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "sox"
        assert "speed" in cmd


def test_piper_synthesizer_calls_piper(tmp_path: Path) -> None:
    synth = PiperSynthesizer(
        voices=["en_US-test-medium"],
        download_dir=tmp_path / "models",
    )
    out = tmp_path / "out.wav"

    with patch("nova.voice.wake_word_training.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        _write_wav(out)  # simulate piper writing the file
        synth.synthesize("hey nova", "en_US-test-medium", out)
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "piper"
        assert "--model" in cmd


def test_pipeline_dry_run(tmp_path: Path) -> None:
    pipeline = WakeWordDataPipeline(out_dir=tmp_path / "dataset")
    result = pipeline.run(dry_run=True)
    assert result["dry_run"] is True
    assert "out_dir" in result


def test_pipeline_creates_dirs(tmp_path: Path) -> None:
    pipeline = WakeWordDataPipeline(out_dir=tmp_path / "dataset")
    pipeline.run(dry_run=True)
    # dry_run still creates dirs
    assert (tmp_path / "dataset").exists()


def test_augmentation_config_defaults() -> None:
    cfg = AugmentationConfig()
    assert 0.0 <= cfg.noise_prob <= 1.0
    assert cfg.speed_range[0] < cfg.speed_range[1]
    assert cfg.pitch_semitones[0] <= cfg.pitch_semitones[1]
