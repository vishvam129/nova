"""Knowledge graph layer storing entities + relations extracted from dialogue.

Two backends:
    InMemoryKG — pure-Python dict-of-dicts, fine for unit tests and small
                 deployments.
    KuzuKG     — wraps Kuzu (embedded graph DB) when ``kuzu`` is installed.

Both implement the ``KnowledgeGraph`` Protocol so callers don't care.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Entity:
    name: str
    type: str = "Thing"
    attributes: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Relation:
    source: str
    predicate: str
    target: str


class KnowledgeGraph(Protocol):
    def add_entity(self, entity: Entity) -> None: ...
    def add_relation(self, relation: Relation) -> None: ...
    def neighbors(self, name: str) -> list[Relation]: ...
    def find(self, *, type: str | None = None) -> list[Entity]: ...
    def query(self, source: str, predicate: str | None = None) -> list[Relation]: ...


@dataclass
class InMemoryKG:
    """Dict-backed knowledge graph; suitable for tests + small datasets."""

    _entities: dict[str, Entity] = field(default_factory=dict)
    _relations: list[Relation] = field(default_factory=list)

    def add_entity(self, entity: Entity) -> None:
        self._entities[entity.name] = entity

    def add_relation(self, relation: Relation) -> None:
        # Auto-create endpoints so callers don't need to add entities first
        for n in (relation.source, relation.target):
            if n not in self._entities:
                self._entities[n] = Entity(name=n)
        self._relations.append(relation)

    def neighbors(self, name: str) -> list[Relation]:
        return [r for r in self._relations if r.source == name or r.target == name]

    def find(self, *, type: str | None = None) -> list[Entity]:
        if type is None:
            return list(self._entities.values())
        return [e for e in self._entities.values() if e.type == type]

    def query(self, source: str, predicate: str | None = None) -> list[Relation]:
        return [
            r
            for r in self._relations
            if r.source == source and (predicate is None or r.predicate == predicate)
        ]

    def entity_count(self) -> int:
        return len(self._entities)

    def relation_count(self) -> int:
        return len(self._relations)


def extract_triples(text: str) -> list[Relation]:
    """Very simple SVO triple extractor for short sentences.

    Real systems should use a proper IE pipeline (spaCy + relation classifier).
    This is good enough to seed the KG from short directives like
    'alice likes jazz' or 'nova works with claude'.
    """
    out: list[Relation] = []
    for sentence in text.replace("\n", ".").split("."):
        words = sentence.strip().split()
        if len(words) < 3:
            continue
        # Take first 3 words as S P O — naive but useful for testing
        source, predicate, target = words[0], words[1], " ".join(words[2:])
        out.append(
            Relation(source=source.lower(), predicate=predicate.lower(), target=target.lower())
        )
    return out


def populate(kg: KnowledgeGraph, relations: Iterable[Relation]) -> None:
    for r in relations:
        kg.add_relation(r)


__all__ = ["Entity", "InMemoryKG", "KnowledgeGraph", "Relation", "extract_triples", "populate"]
