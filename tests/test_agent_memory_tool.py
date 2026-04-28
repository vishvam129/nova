"""Tests for nova.memory.agent_memory_tool."""

from __future__ import annotations

from pathlib import Path

from nova.memory.agent_memory_tool import AgentMemoryTool


def test_add_returns_id_and_increases_count() -> None:
    m = AgentMemoryTool()
    mid = m.add("user likes jazz")
    assert isinstance(mid, str) and len(mid) > 0
    assert len(m) == 1


def test_get_returns_content() -> None:
    m = AgentMemoryTool()
    mid = m.add("hello")
    item = m.get(mid)
    assert item is not None
    assert item.content == "hello"


def test_get_unknown_returns_none() -> None:
    m = AgentMemoryTool()
    assert m.get("ghost") is None


def test_get_increments_access_count() -> None:
    m = AgentMemoryTool()
    mid = m.add("x")
    item = m.get(mid)
    assert item is not None
    assert item.access_count == 1
    m.get(mid)
    assert m.get(mid) is not None
    item2 = m.get(mid)
    assert item2 is not None
    assert item2.access_count >= 2


def test_edit_updates_content() -> None:
    m = AgentMemoryTool()
    mid = m.add("old")
    assert m.edit(mid, "new") is True
    item = m.get(mid)
    assert item is not None
    assert item.content == "new"


def test_edit_unknown_returns_false() -> None:
    m = AgentMemoryTool()
    assert m.edit("ghost", "x") is False


def test_forget_removes() -> None:
    m = AgentMemoryTool()
    mid = m.add("forget me")
    assert m.forget(mid) is True
    assert m.get(mid) is None
    assert len(m) == 0


def test_forget_unknown_returns_false() -> None:
    m = AgentMemoryTool()
    assert m.forget("ghost") is False


def test_list_with_query() -> None:
    m = AgentMemoryTool()
    m.add("alice likes jazz", importance=0.9)
    m.add("bob hates olives", importance=0.5)
    results = m.list(query="jazz")
    assert len(results) == 1
    assert "jazz" in results[0][1].content


def test_list_top_k_limits() -> None:
    m = AgentMemoryTool()
    for i in range(5):
        m.add(f"fact {i}", importance=0.5)
    results = m.list(top_k=2)
    assert len(results) == 2


def test_persistence_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "mem.json"
    m1 = AgentMemoryTool(path=p)
    mid = m1.add("persist me", importance=0.8)
    m2 = AgentMemoryTool(path=p)
    item = m2.get(mid)
    assert item is not None
    assert item.content == "persist me"
    assert item.importance == 0.8
