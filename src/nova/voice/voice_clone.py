"""XTTS-v2 voice cloning from a 6-second sample, stored encrypted per user.

The XTTS model isn't bundled (300+ MB); this module owns the *enrollment*
and *speaker-vector cache* with NaCl encryption so the sample never lands
on disk in plaintext.  ``XttsCloner.synthesize`` is a Protocol so the
real backend can plug in without changing callers.
"""

from __future__ import annotations

import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

_DEFAULT_DIR = Path("~/.local/share/nova/voices").expanduser()


class XttsBackend(Protocol):
    def encode_speaker(self, pcm: bytes, sample_rate: int) -> bytes: ...
    def synthesize(self, text: str, speaker_vector: bytes) -> bytes: ...


@dataclass
class VoiceProfile:
    user: str
    sample_rate: int
    duration_s: float
    encrypted_vector_path: Path


def _encrypt(blob: bytes, key: bytes) -> bytes:
    from nacl.secret import SecretBox
    from nacl.utils import random as nacl_random

    box = SecretBox(key)
    nonce = nacl_random(SecretBox.NONCE_SIZE)
    return nonce + box.encrypt(blob, nonce).ciphertext


def _decrypt(blob: bytes, key: bytes) -> bytes:
    from nacl.secret import SecretBox

    box = SecretBox(key)
    nonce = blob[: SecretBox.NONCE_SIZE]
    ciphertext = blob[SecretBox.NONCE_SIZE :]
    return bytes(box.decrypt(ciphertext, nonce))


def _wav_duration_s(wav_path: Path) -> float:
    with wave.open(str(wav_path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


@dataclass
class VoiceCloneStore:
    """Per-user XTTS speaker-vector store with NaCl encryption."""

    backend: XttsBackend
    encryption_key: bytes  # 32 bytes
    storage_dir: Path = field(default_factory=lambda: _DEFAULT_DIR)
    min_seconds: float = 5.0
    max_seconds: float = 30.0

    def __post_init__(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        if len(self.encryption_key) != 32:
            raise ValueError("encryption_key must be 32 bytes")

    def enroll(self, user: str, sample_wav: Path) -> VoiceProfile:
        duration = _wav_duration_s(sample_wav)
        if duration < self.min_seconds:
            raise ValueError(f"sample too short ({duration:.1f}s < {self.min_seconds}s)")
        if duration > self.max_seconds:
            raise ValueError(f"sample too long ({duration:.1f}s > {self.max_seconds}s)")
        with wave.open(str(sample_wav), "rb") as wf:
            sample_rate = wf.getframerate()
            pcm = wf.readframes(wf.getnframes())
        vector = self.backend.encode_speaker(pcm, sample_rate)
        encrypted = _encrypt(vector, self.encryption_key)
        out_path = self.storage_dir / f"{user}.vec.enc"
        out_path.write_bytes(encrypted)
        return VoiceProfile(
            user=user,
            sample_rate=sample_rate,
            duration_s=duration,
            encrypted_vector_path=out_path,
        )

    def synthesize(self, user: str, text: str) -> bytes:
        profile_path = self.storage_dir / f"{user}.vec.enc"
        if not profile_path.exists():
            raise FileNotFoundError(f"no voice profile for {user!r}")
        vector = _decrypt(profile_path.read_bytes(), self.encryption_key)
        return self.backend.synthesize(text, vector)

    def forget(self, user: str) -> bool:
        profile_path = self.storage_dir / f"{user}.vec.enc"
        if not profile_path.exists():
            return False
        profile_path.unlink()
        return True

    def list_users(self) -> list[str]:
        return sorted(p.stem.removesuffix(".vec") for p in self.storage_dir.glob("*.vec.enc"))


__all__ = ["VoiceCloneStore", "VoiceProfile", "XttsBackend"]
