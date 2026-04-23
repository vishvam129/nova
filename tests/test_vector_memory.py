"""Tests for InMemoryVectorStore."""

from __future__ import annotations

from nova.memory.vector import (
    InMemoryVectorStore,
    MemoryRecord,
    VectorStore,
    records_from_texts,
)


def _seed() -> InMemoryVectorStore:
    store = InMemoryVectorStore()
    store.add(MemoryRecord(id="1", text="user lives in Delhi", namespace="alice"))
    store.add(MemoryRecord(id="2", text="wife loves spicy food", namespace="alice"))
    store.add(MemoryRecord(id="3", text="secret club password is xyz", namespace="bob"))
    return store


def test_is_vector_store_protocol() -> None:
    assert isinstance(InMemoryVectorStore(), VectorStore)


def test_search_respects_namespace() -> None:
    store = _seed()
    alice = store.search("where do I live", namespace="alice")
    bob = store.search("where do I live", namespace="bob")
    assert all(r.namespace == "alice" for r in alice)
    assert all(r.namespace == "bob" for r in bob)


def test_search_returns_most_relevant_first() -> None:
    store = _seed()
    hits = store.search("user location city", namespace="alice", k=1)
    assert hits[0].id == "1"


def test_delete_removes_record() -> None:
    store = _seed()
    store.delete("1", namespace="alice")
    hits = store.search("where do I live", namespace="alice")
    assert all(r.id != "1" for r in hits)


def test_metadata_filter() -> None:
    store = InMemoryVectorStore()
    store.add(MemoryRecord(id="a", text="coffee notes", metadata={"kind": "note"}))
    store.add(MemoryRecord(id="b", text="coffee order", metadata={"kind": "order"}))
    hits = store.search("coffee", where={"kind": "note"}, k=5)
    assert [r.id for r in hits] == ["a"]


def test_len_counts_all_records() -> None:
    store = _seed()
    assert len(store) == 3


def test_records_from_texts_defaults_ids() -> None:
    recs = records_from_texts(["a", "b", "c"])
    assert [r.id for r in recs] == ["m-0", "m-1", "m-2"]


def test_records_from_texts_custom_ids_and_ns() -> None:
    recs = records_from_texts(["x", "y"], ids=["x1", "y1"], namespace="alice")
    assert recs[0].namespace == "alice"
    assert recs[1].id == "y1"
