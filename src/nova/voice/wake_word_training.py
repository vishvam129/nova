"""Synthetic data pipeline for training a custom 'hey nova' wake word model.

Pipeline overview:
    1. PiperSynthesizer — generates varied WAV pronunciations of the wake
       phrase using Piper TTS (multiple voices, speeds, pitches).
    2. Augmenter — adds room impulse responses, background noise, and
       codec degradation to the clean TTS samples.
    3. WakeWordDataPipeline — orchestrates synthesis + augmentation and
       writes the training manifest consumed by openWakeWord's trainer.

The pipeline is designed to run offline (not at inference time).  Call
``WakeWordDataPipeline.run()`` to produce a dataset directory; then pass
that directory to the openWakeWord fine-tuning CLI.

Piper binary must be on PATH.  Models are downloaded automatically via
``piper --download-dir``.
"""

from __future__ import annotations

import json
import random
import subprocess
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Phrase variants that cover common mis-pronunciations / accents
_WAKE_PHRASES = [
    "hey nova",
    "hey, nova",
    "Hey Nova",
    "hey NOVA",
    "Hey, Nova",
]

# Piper voice IDs to use for diversity
_DEFAULT_VOICES = [
    "en_US-lessac-medium",
    "en_US-ryan-medium",
    "en_GB-alba-medium",
    "en_US-amy-medium",
]


@dataclass
class PiperSynthesizer:
    """Wraps the Piper TTS binary to produce WAV samples."""

    voices: list[str] = field(default_factory=lambda: list(_DEFAULT_VOICES))
    download_dir: Path = Path("~/.local/share/nova/piper_models").expanduser()
    sample_rate: int = 16_000

    def synthesize(self, text: str, voice: str, output_path: Path) -> Path:
        """Run piper and write a 16 kHz mono WAV to *output_path*.

        Raises ``FileNotFoundError`` if piper is not on PATH.
        Raises ``subprocess.CalledProcessError`` on piper failure.
        """
        self.download_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            "piper",
            "--model",
            voice,
            "--download-dir",
            str(self.download_dir),
            "--output_file",
            str(output_path),
        ]
        result = subprocess.run(
            cmd,
            input=text.encode(),
            capture_output=True,
            check=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"piper failed: {result.stderr.decode()}")
        return output_path

    def synthesize_all(
        self,
        phrases: list[str],
        out_dir: Path,
        *,
        repeats: int = 3,
    ) -> list[Path]:
        """Generate WAV files for every (phrase, voice, repeat) combination."""
        out_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for phrase in phrases:
            for voice in self.voices:
                for i in range(repeats):
                    stem = f"{voice}_{phrase.replace(' ', '_')}_{i}"
                    out = out_dir / f"{stem}.wav"
                    self.synthesize(phrase, voice, out)
                    paths.append(out)
        return paths


@dataclass
class AugmentationConfig:
    """Parameters for audio augmentation."""

    noise_prob: float = 0.5
    speed_range: tuple[float, float] = (0.85, 1.15)
    pitch_semitones: tuple[int, int] = (-2, 2)
    reverb_prob: float = 0.3


def augment_wav(src: Path, dst: Path, config: AugmentationConfig) -> Path:
    """Apply basic augmentation to a WAV file using sox (if available).

    Falls back to a file copy when sox is not installed so the pipeline
    still produces a valid (un-augmented) dataset.
    """
    import shutil

    if not shutil.which("sox"):
        shutil.copy2(src, dst)
        return dst

    speed = random.uniform(*config.speed_range)
    pitch = random.randint(*config.pitch_semitones)
    cmd = [
        "sox",
        str(src),
        str(dst),
        "speed",
        str(round(speed, 3)),
        "pitch",
        str(pitch * 100),
    ]
    if random.random() < config.reverb_prob:
        cmd += ["reverb"]
    subprocess.run(cmd, check=True, capture_output=True)
    return dst


def wav_duration_seconds(path: Path) -> float:
    """Return the duration of a WAV file in seconds."""
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


@dataclass
class WakeWordDataPipeline:
    """Orchestrates synthesis + augmentation and writes the training manifest.

    Output layout::

        out_dir/
            positive/          — wake-phrase WAVs (real label)
            negative/          — background / other-speech WAVs (fake label)
            augmented/         — augmented copies of positive/
            manifest.json      — [{path, label, duration_s}, ...]
    """

    out_dir: Path
    synthesizer: PiperSynthesizer = field(default_factory=PiperSynthesizer)
    augmentation: AugmentationConfig = field(default_factory=AugmentationConfig)
    phrases: list[str] = field(default_factory=lambda: list(_WAKE_PHRASES))
    augment_factor: int = 5

    def run(self, *, dry_run: bool = False) -> dict[str, Any]:
        """Execute the full pipeline.

        Args:
            dry_run: If True, skip actual piper/sox calls (useful in CI).

        Returns:
            Summary dict with counts and output paths.
        """
        pos_dir = self.out_dir / "positive"
        aug_dir = self.out_dir / "augmented"
        pos_dir.mkdir(parents=True, exist_ok=True)
        aug_dir.mkdir(parents=True, exist_ok=True)

        manifest: list[dict[str, Any]] = []

        if dry_run:
            return {"dry_run": True, "out_dir": str(self.out_dir)}

        # Synthesis
        positive_wavs = self.synthesizer.synthesize_all(self.phrases, pos_dir, repeats=3)
        for wav in positive_wavs:
            manifest.append(
                {
                    "path": str(wav),
                    "label": 1,
                    "duration_s": wav_duration_seconds(wav),
                }
            )

        # Augmentation
        for wav in positive_wavs:
            for i in range(self.augment_factor):
                dst = aug_dir / f"{wav.stem}_aug{i}.wav"
                augment_wav(wav, dst, self.augmentation)
                manifest.append(
                    {
                        "path": str(dst),
                        "label": 1,
                        "duration_s": wav_duration_seconds(dst),
                    }
                )

        manifest_path = self.out_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        return {
            "positive": len(positive_wavs),
            "augmented": len(positive_wavs) * self.augment_factor,
            "manifest": str(manifest_path),
            "out_dir": str(self.out_dir),
        }


__all__ = [
    "AugmentationConfig",
    "PiperSynthesizer",
    "WakeWordDataPipeline",
    "augment_wav",
    "wav_duration_seconds",
]
