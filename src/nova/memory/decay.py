"""Memory decay / importance scoring.

Each ``MemoryItem`` has an ``importance`` (0..1) and a recency component
that decays exponentially with age.  ``score()`` blends them; ``MemoryDecay``
prunes items below a configurable threshold.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemoryItem:
    content: str
    importance: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    def __post_init__(self) -> None:
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(f"importance must be in [0, 1], got {self.importance}")

    def touch(self, now: datetime | None = None) -> None:
        self.last_accessed = now or datetime.now()
        self.access_count += 1


@dataclass
class MemoryDecay:
    """Decays memory scores by age and access frequency.

    Score formula::
        score = importance * recency * frequency_boost
        recency = exp(-age_hours / half_life_hours)
        frequency_boost = 1 + log(1 + access_count) / 5
    """

    half_life_hours: float = 168.0  # ~1 week
    threshold: float = 0.05

    def score(self, item: MemoryItem, now: datetime | None = None) -> float:
        now = now or datetime.now()
        age_hours = max(0.0, (now - item.last_accessed).total_seconds() / 3600)
        recency = math.exp(-age_hours / self.half_life_hours)
        freq_boost = 1.0 + math.log1p(item.access_count) / 5.0
        return item.importance * recency * freq_boost

    def should_prune(self, item: MemoryItem, now: datetime | None = None) -> bool:
        return self.score(item, now) < self.threshold

    def prune(self, items: Iterable[MemoryItem], now: datetime | None = None) -> list[MemoryItem]:
        """Return items that should be kept (score >= threshold)."""
        return [it for it in items if not self.should_prune(it, now)]

    def rank(
        self, items: Iterable[MemoryItem], now: datetime | None = None
    ) -> list[tuple[MemoryItem, float]]:
        """Return ``(item, score)`` pairs ordered by descending score."""
        scored = [(it, self.score(it, now)) for it in items]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


__all__ = ["MemoryDecay", "MemoryItem"]
