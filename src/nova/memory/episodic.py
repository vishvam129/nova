"""Episodic memory: time-indexed event log.

Records what the user / agent did, when, and a free-text description.
Queries are date-range or natural-language phrases like 'yesterday'.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Episode:
    timestamp: datetime
    actor: str  # 'user' / 'agent' / 'system'
    description: str
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "description": self.description,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> Episode:
        return cls(
            timestamp=datetime.fromisoformat(str(d["timestamp"])),
            actor=str(d["actor"]),
            description=str(d["description"]),
            tags=tuple(d.get("tags", []) or []),  # type: ignore[arg-type]
        )


@dataclass
class EpisodicMemory:
    """JSONL-backed time-indexed log."""

    path: Path | None = None
    _episodes: list[Episode] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.path and self.path.exists():
            for line in self.path.read_text().splitlines():
                if not line.strip():
                    continue
                self._episodes.append(Episode.from_dict(json.loads(line)))

    def record(
        self,
        actor: str,
        description: str,
        *,
        tags: Iterable[str] = (),
        when: datetime | None = None,
    ) -> Episode:
        ep = Episode(
            timestamp=when or datetime.now(),
            actor=actor,
            description=description,
            tags=tuple(tags),
        )
        self._episodes.append(ep)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as f:
                f.write(json.dumps(ep.to_dict()) + "\n")
        return ep

    def all(self) -> list[Episode]:
        return list(self._episodes)

    def in_range(self, start: datetime, end: datetime) -> list[Episode]:
        return [ep for ep in self._episodes if start <= ep.timestamp < end]

    def on_day(self, day: date) -> list[Episode]:
        start = datetime(day.year, day.month, day.day)
        return self.in_range(start, start + timedelta(days=1))

    def yesterday(self) -> list[Episode]:
        return self.on_day(date.today() - timedelta(days=1))

    def today(self) -> list[Episode]:
        return self.on_day(date.today())

    def search(self, query: str) -> list[Episode]:
        q = query.lower()
        return [ep for ep in self._episodes if q in ep.description.lower()]

    def by_tag(self, tag: str) -> list[Episode]:
        return [ep for ep in self._episodes if tag in ep.tags]

    def __len__(self) -> int:
        return len(self._episodes)


__all__ = ["Episode", "EpisodicMemory"]
