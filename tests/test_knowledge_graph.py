"""Tests for nova.memory.knowledge_graph."""

from __future__ import annotations

from nova.memory.knowledge_graph import (
    Entity,
    InMemoryKG,
    Relation,
    extract_triples,
    populate,
)


def test_add_entity() -> None:
    kg = InMemoryKG()
    kg.add_entity(Entity(name="alice", type="Person"))
    assert kg.entity_count() == 1


def test_add_relation_autocreates_endpoints() -> None:
    kg = InMemoryKG()
    kg.add_relation(Relation("alice", "likes", "jazz"))
    assert kg.entity_count() == 2
    assert kg.relation_count() == 1


def test_neighbors_includes_source_and_target() -> None:
    kg = InMemoryKG()
    kg.add_relation(Relation("alice", "likes", "jazz"))
    n_alice = kg.neighbors("alice")
    n_jazz = kg.neighbors("jazz")
    assert len(n_alice) == 1
    assert len(n_jazz) == 1


def test_find_by_type() -> None:
    kg = InMemoryKG()
    kg.add_entity(Entity("alice", "Person"))
    kg.add_entity(Entity("jazz", "Genre"))
    persons = kg.find(type="Person")
    assert len(persons) == 1
    assert persons[0].name == "alice"


def test_find_all() -> None:
    kg = InMemoryKG()
    kg.add_entity(Entity("alice"))
    kg.add_entity(Entity("bob"))
    assert len(kg.find()) == 2


def test_query_with_predicate() -> None:
    kg = InMemoryKG()
    kg.add_relation(Relation("alice", "likes", "jazz"))
    kg.add_relation(Relation("alice", "knows", "bob"))
    likes = kg.query("alice", predicate="likes")
    assert len(likes) == 1
    assert likes[0].target == "jazz"


def test_query_without_predicate() -> None:
    kg = InMemoryKG()
    kg.add_relation(Relation("alice", "likes", "jazz"))
    kg.add_relation(Relation("alice", "knows", "bob"))
    all_alice = kg.query("alice")
    assert len(all_alice) == 2


def test_extract_triples_simple() -> None:
    triples = extract_triples("alice likes jazz. bob knows alice")
    assert len(triples) == 2
    assert triples[0] == Relation("alice", "likes", "jazz")
    assert triples[1] == Relation("bob", "knows", "alice")


def test_extract_triples_skips_short_sentences() -> None:
    assert extract_triples("hi. ok") == []


def test_populate_helper() -> None:
    kg = InMemoryKG()
    populate(kg, extract_triples("alice likes jazz. nova helps user"))
    assert kg.relation_count() == 2
