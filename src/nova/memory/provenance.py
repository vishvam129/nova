"""Memory explainability: 'why do you know X' returns source turn + timestamp.

Every memory write goes through ``ProvenanceLog`` which records the
source utterance, conversation id, and timestamp.  ``explain(memory_id)``
returns the originating record so the user can audit any claim Nova makes.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    memory_id: str
    source_text: str
    speaker: str
    conversation_id: str
    timestamp: datetime
    confidence: float = 1.0

    def to_dict(self) -> dict[str, object]:
        return {
            "memory_id": self.memory_id,
            "source_text": self.source_text,
            "speaker": self.speaker,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> ProvenanceRecord:
        return cls(
            memory_id=str(d["memory_id"]),
            source_text=str(d["source_text"]),
            speaker=str(d["speaker"]),
            conversation_id=str(d["conversation_id"]),
            timestamp=datetime.fromisoformat(str(d["timestamp"])),
            confidence=float(d.get("confidence", 1.0)),  # type: ignore[arg-type]
        )

    def to_prompt(self) -> str:
        when = self.timestamp.strftime("%Y-%m-%d %H:%M")
        return f'I know this because {self.speaker} said "{self.source_text}" on {when}.'


@dataclass
class ProvenanceLog:
    """Append-only JSONL store of provenance records, indexed by memory_id."""

    path: Path | None = None
    _records: dict[str, list[ProvenanceRecord]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.path and self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    rec = ProvenanceRecord.from_dict(json.loads(line))
                    self._records.setdefault(rec.memory_id, []).append(rec)

    def record(
        self,
        *,
        memory_id: str,
        source_text: str,
        speaker: str = "user",
        conversation_id: str = "",
        confidence: float = 1.0,
        when: datetime | None = None,
    ) -> ProvenanceRecord:
        rec = ProvenanceRecord(
            memory_id=memory_id,
            source_text=source_text,
            speaker=speaker,
            conversation_id=conversation_id,
            timestamp=when or datetime.now(),
            confidence=confidence,
        )
        self._records.setdefault(memory_id, []).append(rec)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as f:
                f.write(json.dumps(rec.to_dict()) + "\n")
        return rec

    def explain(self, memory_id: str) -> list[ProvenanceRecord]:
        return list(self._records.get(memory_id, []))

    def latest(self, memory_id: str) -> ProvenanceRecord | None:
        items = self._records.get(memory_id) or []
        return items[-1] if items else None

    def by_conversation(self, conversation_id: str) -> Iterable[ProvenanceRecord]:
        for items in self._records.values():
            yield from (r for r in items if r.conversation_id == conversation_id)

    def memory_ids(self) -> list[str]:
        return sorted(self._records.keys())


__all__ = ["ProvenanceLog", "ProvenanceRecord"]
