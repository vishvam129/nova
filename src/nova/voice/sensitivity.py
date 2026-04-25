"""Wake word sensitivity tuning and false-trigger logging.

``SensitivityConfig`` holds the confidence threshold and hysteresis window.
``FalseTriggerLogger`` persists rejected audio clips + metadata to disk so
they can be folded back into the next training run as negative examples.

Usage::

    config = SensitivityConfig(threshold=0.85)
    logger = FalseTriggerLogger(log_dir=Path("~/.local/share/nova/false_triggers"))

    score = wake_word_engine.score(audio_frame)
    if score >= config.threshold:
        handle_wake()
    else:
        logger.record(audio_frame, score=score, reason="below_threshold")
"""

from __future__ import annotations

import json
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_DEFAULT_LOG_DIR = Path("~/.local/share/nova/false_triggers").expanduser()


@dataclass
class SensitivityConfig:
    """Tuneable parameters for wake word detection.

    Attributes:
        threshold:         Minimum confidence score to accept a detection.
                           Range [0, 1].  Higher = fewer false positives but
                           more missed wakes.
        hysteresis_s:      Seconds to ignore subsequent detections after a
                           confirmed wake (prevents double-firing).
        log_false_triggers: Whether to persist rejected clips for retraining.
    """

    threshold: float = 0.80
    hysteresis_s: float = 1.5
    log_false_triggers: bool = True

    def __post_init__(self) -> None:
        if not 0.0 < self.threshold <= 1.0:
            raise ValueError(f"threshold must be in (0, 1], got {self.threshold}")
        if self.hysteresis_s < 0:
            raise ValueError(f"hysteresis_s must be >= 0, got {self.hysteresis_s}")

    def accepts(self, score: float) -> bool:
        """Return True if *score* meets the detection threshold."""
        return score >= self.threshold


@dataclass
class FalseTriggerLogger:
    """Persists rejected audio clips and their scores for retraining.

    Each record produces two files in *log_dir*:
      - ``<timestamp>_<score>.wav``   — raw PCM audio (16-bit, 16 kHz, mono)
      - ``<timestamp>_<score>.json``  — metadata (score, reason, timestamp)
    """

    log_dir: Path = field(default_factory=lambda: _DEFAULT_LOG_DIR)
    sample_rate: int = 16_000
    max_entries: int = 10_000

    def __post_init__(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        pcm: bytes,
        *,
        score: float,
        reason: str = "below_threshold",
        extra: dict[str, Any] | None = None,
    ) -> Path:
        """Save a rejected audio clip and its metadata.

        Args:
            pcm:    Raw PCM bytes (16-bit signed, mono, 16 kHz).
            score:  Detection confidence score that was rejected.
            reason: Human-readable reason for rejection.
            extra:  Optional extra fields written to the JSON sidecar.

        Returns:
            Path to the written WAV file.
        """
        ts = f"{time.time():.3f}"
        stem = f"{ts}_{score:.4f}"
        wav_path = self.log_dir / f"{stem}.wav"
        meta_path = self.log_dir / f"{stem}.json"

        _write_wav(wav_path, pcm, self.sample_rate)

        metadata: dict[str, Any] = {
            "timestamp": ts,
            "score": score,
            "reason": reason,
            "sample_rate": self.sample_rate,
        }
        if extra:
            metadata.update(extra)
        meta_path.write_text(json.dumps(metadata, indent=2))

        self._enforce_limit()
        return wav_path

    def entries(self) -> list[dict[str, Any]]:
        """Return metadata for all logged false triggers, newest first."""
        results: list[dict[str, Any]] = []
        for meta_file in sorted(self.log_dir.glob("*.json"), reverse=True):
            try:
                results.append(json.loads(meta_file.read_text()))
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def count(self) -> int:
        return len(list(self.log_dir.glob("*.wav")))

    def _enforce_limit(self) -> None:
        """Delete the oldest entries when max_entries is exceeded."""
        wav_files = sorted(self.log_dir.glob("*.wav"))
        overflow = len(wav_files) - self.max_entries
        if overflow <= 0:
            return
        for old_wav in wav_files[:overflow]:
            old_wav.unlink(missing_ok=True)
            old_wav.with_suffix(".json").unlink(missing_ok=True)


def _write_wav(path: Path, pcm: bytes, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)


__all__ = ["FalseTriggerLogger", "SensitivityConfig"]
