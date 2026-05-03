"""Tests for nova.memory.provenance."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from nova.memory.provenance import ProvenanceLog, ProvenanceRecord


def test_record_and_explain() -> None:
    log = ProvenanceLog()
    log.record(
        memory_id="m1",
        source_text="my favourite drink is matcha",
        speaker="user",
        conversation_id="conv-1",
    )
    out = log.explain("m1")
    assert len(out) == 1
    assert out[0].source_text.startswith("my favourite drink")


def test_explain_unknown_returns_empty() -> None:
    log = ProvenanceLog()
    assert log.explain("ghost") == []


def test_latest_returns_most_recent() -> None:
    log = ProvenanceLog()
    log.record(memory_id="m1", source_text="v1")
    log.record(memory_id="m1", source_text="v2")
    latest = log.latest("m1")
    assert latest is not None
    assert latest.source_text == "v2"


def test_by_conversation() -> None:
    log = ProvenanceLog()
    log.record(memory_id="m1", source_text="a", conversation_id="c1")
    log.record(memory_id="m2", source_text="b", conversation_id="c2")
    log.record(memory_id="m3", source_text="c", conversation_id="c1")
    items = list(log.by_conversation("c1"))
    assert len(items) == 2


def test_persistence_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "prov.jsonl"
    log1 = ProvenanceLog(path=p)
    log1.record(memory_id="m1", source_text="hello", speaker="user")
    log1.record(memory_id="m2", source_text="world", speaker="agent")

    log2 = ProvenanceLog(path=p)
    assert "m1" in log2.memory_ids()
    assert log2.latest("m2").source_text == "world"  # type: ignore[union-attr]


def test_to_prompt_format() -> None:
    rec = ProvenanceRecord(
        memory_id="m1",
        source_text="I love jazz",
        speaker="user",
        conversation_id="c1",
        timestamp=datetime(2026, 4, 28, 10, 0),
    )
    out = rec.to_prompt()
    assert "user" in out
    assert "I love jazz" in out
    assert "2026-04-28" in out


def test_record_dict_roundtrip() -> None:
    rec = ProvenanceRecord(
        memory_id="m1",
        source_text="x",
        speaker="user",
        conversation_id="c1",
        timestamp=datetime(2026, 4, 28),
    )
    assert ProvenanceRecord.from_dict(rec.to_dict()) == rec


def test_memory_ids_sorted() -> None:
    log = ProvenanceLog()
    log.record(memory_id="b", source_text="x")
    log.record(memory_id="a", source_text="x")
    assert log.memory_ids() == ["a", "b"]
