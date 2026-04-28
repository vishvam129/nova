"""Per-user voice profile + diarization gate.

Diarization assigns speaker labels to chunks of audio.  The trust gate
filters those labels to a set of enrolled, trusted users — only their
utterances are forwarded to the agent.

Diarization is delegated to a ``Diarizer`` Protocol; a simple speaker-
verification-based diarizer is provided.  Real deployments can plug in
pyannote.audio or NeMo without changing this module.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from nova.safety.speaker_verify import SpeakerVerifier


@dataclass(frozen=True, slots=True)
class Segment:
    pcm: bytes
    speaker: str
    start_s: float
    end_s: float


class Diarizer(Protocol):
    """Anything that can split audio into per-speaker segments."""

    def diarize(self, pcm: bytes, sample_rate: int = 16_000) -> Sequence[Segment]: ...


@dataclass
class VerifierDiarizer:
    """Score each fixed-length window against enrolled voices.

    Useful when you already have voice prints and want diarization
    without a heavyweight model.  Window length defaults to 1 s.
    """

    verifier: SpeakerVerifier
    window_s: float = 1.0
    min_score: float = 0.5

    def diarize(self, pcm: bytes, sample_rate: int = 16_000) -> list[Segment]:
        bytes_per_window = int(sample_rate * 2 * self.window_s)
        if bytes_per_window <= 0:
            return []
        out: list[Segment] = []
        for offset in range(0, len(pcm), bytes_per_window):
            chunk = pcm[offset : offset + bytes_per_window]
            if not chunk:
                continue
            _, name, score = self.verifier.verify(chunk)
            speaker = name if score >= self.min_score else "unknown"
            start = offset / (sample_rate * 2)
            end = (offset + len(chunk)) / (sample_rate * 2)
            out.append(Segment(pcm=chunk, speaker=speaker, start_s=start, end_s=end))
        return out


@dataclass
class TrustGate:
    """Drops segments from speakers not in *trusted_users*."""

    trusted_users: set[str] = field(default_factory=set)

    def filter(self, segments: Sequence[Segment]) -> list[Segment]:
        return [s for s in segments if s.speaker in self.trusted_users]

    def has_trusted_speech(self, segments: Sequence[Segment]) -> bool:
        return any(s.speaker in self.trusted_users for s in segments)

    def add(self, user: str) -> None:
        self.trusted_users.add(user)

    def remove(self, user: str) -> None:
        self.trusted_users.discard(user)


__all__ = ["Diarizer", "Segment", "TrustGate", "VerifierDiarizer"]
