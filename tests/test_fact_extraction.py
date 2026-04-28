"""Tests for nova.memory.fact_extraction."""

from __future__ import annotations

from pathlib import Path

from nova.memory.fact_extraction import (
    Fact,
    FactStore,
    deduplicate,
    extract_facts,
)


def test_extract_name() -> None:
    facts = extract_facts("My name is Vishvam")
    assert any(f.predicate == "user.name" and f.object == "Vishvam" for f in facts)


def test_extract_age() -> None:
    facts = extract_facts("I am 24 years old")
    assert any(f.predicate == "user.age" and f.object == "24" for f in facts)


def test_extract_location() -> None:
    facts = extract_facts("I live in San Francisco")
    assert any(f.predicate == "user.location" for f in facts)


def test_extract_likes() -> None:
    facts = extract_facts("I love jazz music")
    assert any(f.predicate == "user.likes" for f in facts)


def test_confidence_assigned() -> None:
    facts = extract_facts("My name is Alice")
    assert all(0.0 <= f.confidence <= 1.0 for f in facts)
    name_facts = [f for f in facts if f.predicate == "user.name"]
    assert name_facts[0].confidence >= 0.9


def test_extract_no_facts() -> None:
    assert extract_facts("hello world") == []


def test_deduplicate_keeps_highest_confidence() -> None:
    a = Fact("user", "user.name", "Vishvam", confidence=0.5)
    b = Fact("user", "user.name", "Vishvam", confidence=0.95)
    out = deduplicate([a, b])
    assert len(out) == 1
    assert out[0].confidence == 0.95


def test_factstore_add_and_get(tmp_path: Path) -> None:
    store = FactStore(path=tmp_path / "facts.jsonl")
    store.add_many(extract_facts("My name is Bob"))
    found = store.get("user", "user.name")
    assert len(found) == 1
    assert found[0].object == "Bob"


def test_factstore_correction(tmp_path: Path) -> None:
    store = FactStore(path=tmp_path / "f.jsonl")
    store.add(Fact("user", "user.name", "Bobby", confidence=0.7))
    store.correct("user", "user.name", "Robert")
    facts = store.get("user", "user.name")
    assert len(facts) == 1
    assert facts[0].object == "Robert"
    assert facts[0].confidence == 1.0
    assert facts[0].source == "user_correction"


def test_factstore_delete(tmp_path: Path) -> None:
    store = FactStore(path=tmp_path / "f.jsonl")
    store.add(Fact("user", "user.name", "X"))
    removed = store.delete("user", "user.name")
    assert removed == 1
    assert store.get("user", "user.name") == []


def test_factstore_persistence(tmp_path: Path) -> None:
    p = tmp_path / "f.jsonl"
    s1 = FactStore(path=p)
    s1.add(Fact("user", "user.name", "Bob"))
    s2 = FactStore(path=p)
    assert len(s2) == 1


def test_factstore_correction_persists(tmp_path: Path) -> None:
    p = tmp_path / "f.jsonl"
    s1 = FactStore(path=p)
    s1.add(Fact("user", "user.name", "Bobby"))
    s1.correct("user", "user.name", "Robert")
    s2 = FactStore(path=p)
    assert s2.get("user", "user.name")[0].object == "Robert"
    assert len(s2) == 1
