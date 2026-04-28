"""Speaker verification before sensitive actions.

Uses a local speaker-embedding model (Resemblyzer / SpeechBrain ECAPA) to
compare an enrollment voice print against the live audio.  The embedder
is a Protocol so we can plug in a real model in production and a hash-
based stub in tests / CI.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class Embedder(Protocol):
    """Anything that produces a fixed-length voice embedding from PCM."""

    def embed(self, pcm: bytes) -> Sequence[float]: ...


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


@dataclass
class HashEmbedder:
    """Stable, deterministic stub embedder for tests / fallback.

    Hashes 80-byte windows of audio into a 64-dim vector.  Not secure,
    but produces consistent embeddings for the same audio.
    """

    dim: int = 64

    def embed(self, pcm: bytes) -> Sequence[float]:
        vec = [0.0] * self.dim
        for i in range(0, len(pcm), 80):
            window = pcm[i : i + 80]
            h = hash(window)
            for d in range(self.dim):
                vec[d] += ((h >> d) & 1) * 2 - 1
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


@dataclass
class SpeakerVerifier:
    """Enrolls one or more authorized speakers and verifies new utterances."""

    embedder: Embedder
    threshold: float = 0.75
    enrollments: dict[str, list[float]] = field(default_factory=dict)

    def enroll(self, name: str, pcm: bytes) -> None:
        self.enrollments[name] = list(self.embedder.embed(pcm))

    def verify(self, pcm: bytes) -> tuple[bool, str, float]:
        """Return ``(matched, name, score)``.

        ``matched`` is True iff the best similarity is >= threshold.
        """
        if not self.enrollments:
            return False, "", 0.0
        emb = self.embedder.embed(pcm)
        best_name = ""
        best_score = -1.0
        for name, ref in self.enrollments.items():
            score = cosine(emb, ref)
            if score > best_score:
                best_name = name
                best_score = score
        return best_score >= self.threshold, best_name, best_score

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.enrollments))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        self.enrollments = {k: list(map(float, v)) for k, v in json.loads(path.read_text()).items()}


__all__ = ["Embedder", "HashEmbedder", "SpeakerVerifier", "cosine"]
