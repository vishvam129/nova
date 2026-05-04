"""Automatic fact extraction from dialogue with confidence + corrections.

Three pieces:
    extract_facts(text)      — heuristic extractor, returns Fact list with
                               a confidence score in [0, 1]
    FactStore                — persists facts as JSONL, supports user
                               corrections (override / delete)
    deduplicate()            — folds equal facts, keeps highest confidence
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Fact:
    subject: str
    predicate: str
    object: str
    confidence: float = 0.5
    source: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Fact:
        return cls(
            subject=str(d["subject"]),
            predicate=str(d["predicate"]),
            object=str(d["object"]),
            confidence=float(d.get("confidence", 0.5)),
            source=str(d.get("source", "")),
            timestamp=str(d.get("timestamp", "")),
        )


# Patterns ranked roughly by reliability — first match wins
_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"my name is (\w+)", re.I), "user.name", 0.95),
    (re.compile(r"i am (\d+) years old", re.I), "user.age", 0.95),
    (re.compile(r"i live in ([^.\n]+)", re.I), "user.location", 0.85),
    (re.compile(r"i work at ([^.\n]+)", re.I), "user.employer", 0.85),
    (re.compile(r"i (?:like|love|enjoy) ([^.\n]+)", re.I), "user.likes", 0.7),
    (re.compile(r"i (?:hate|dislike) ([^.\n]+)", re.I), "user.dislikes", 0.7),
    (re.compile(r"my (\w+) is ([^.\n]+)", re.I), "user.attribute", 0.6),
]


def extract_facts(text: str, source: str = "dialogue") -> list[Fact]:
    """Pull facts out of free-form text with confidence scores."""
    out: list[Fact] = []
    now = datetime.now().isoformat()
    for pat, predicate, conf in _PATTERNS:
        for m in pat.finditer(text):
            groups = m.groups()
            if predicate == "user.attribute" and len(groups) == 2:
                pred = f"user.{groups[0].lower()}"
                obj = groups[1].strip()
            else:
                pred = predicate
                obj = groups[0].strip()
            out.append(
                Fact(
                    subject="user",
                    predicate=pred,
                    object=obj,
                    confidence=conf,
                    source=source,
                    timestamp=now,
                )
            )
    return deduplicate(out)


def deduplicate(facts: list[Fact]) -> list[Fact]:
    """Fold facts with the same (subject, predicate, object) keeping max confidence."""
    by_key: dict[tuple[str, str, str], Fact] = {}
    for f in facts:
        key = (f.subject, f.predicate, f.object)
        existing = by_key.get(key)
        if existing is None or f.confidence > existing.confidence:
            by_key[key] = f
    return list(by_key.values())


@dataclass
class FactStore:
    """JSONL-backed fact store with user-correction support."""

    path: Path | None = None
    _facts: list[Fact] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.path and self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    self._facts.append(Fact.from_dict(json.loads(line)))

    def add(self, fact: Fact) -> None:
        self._facts.append(fact)
        self._persist(fact)

    def add_many(self, facts: list[Fact]) -> None:
        for f in facts:
            self.add(f)

    def correct(self, subject: str, predicate: str, new_object: str) -> Fact:
        """Replace any existing facts matching (subject, predicate)."""
        self._facts = [
            f for f in self._facts if not (f.subject == subject and f.predicate == predicate)
        ]
        corrected = Fact(
            subject=subject,
            predicate=predicate,
            object=new_object,
            confidence=1.0,
            source="user_correction",
            timestamp=datetime.now().isoformat(),
        )
        self._facts.append(corrected)
        self._rewrite()
        return corrected

    def delete(self, subject: str, predicate: str) -> int:
        before = len(self._facts)
        self._facts = [
            f for f in self._facts if not (f.subject == subject and f.predicate == predicate)
        ]
        removed = before - len(self._facts)
        self._rewrite()
        return removed

    def get(self, subject: str, predicate: str) -> list[Fact]:
        return [f for f in self._facts if f.subject == subject and f.predicate == predicate]

    def all(self) -> list[Fact]:
        return list(self._facts)

    def __len__(self) -> int:
        return len(self._facts)

    def _persist(self, fact: Fact) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(fact.to_dict()) + "\n")

    def _rewrite(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w") as f:
            for fact in self._facts:
                f.write(json.dumps(fact.to_dict()) + "\n")


__all__ = ["Fact", "FactStore", "deduplicate", "extract_facts"]
