"""Tests for RollingBuffer."""

from __future__ import annotations

from nova.memory.short_term import MemoryTurn, RollingBuffer


def test_appends_preserve_turns() -> None:
    buf = RollingBuffer(capacity=10, token_budget=10_000)
    buf.append("user", "hi")
    buf.append("assistant", "hello")
    turns = buf.turns()
    assert [t.role for t in turns] == ["user", "assistant"]
    assert all(isinstance(t, MemoryTurn) for t in turns)


def test_capacity_drops_oldest() -> None:
    buf = RollingBuffer(capacity=3, token_budget=10_000)
    for i in range(5):
        buf.append("user", f"msg {i}")
    assert len(buf) == 3
    assert buf.turns()[0].content == "msg 2"


def test_fold_when_over_token_budget() -> None:
    buf = RollingBuffer(capacity=100, token_budget=10)
    for i in range(8):
        buf.append("user", f"long content number {i} " * 5)
    # folding should have happened; summary non-empty.
    assert buf.summary


def test_custom_summarizer_runs() -> None:
    calls: list[int] = []

    def summ(turns: list[MemoryTurn]) -> str:
        calls.append(len(turns))
        return f"SUM({len(turns)})"

    buf = RollingBuffer(capacity=100, token_budget=5, summarizer=summ)
    for i in range(6):
        buf.append("user", f"content {i} " * 10)
    assert calls, "summarizer should have been called at least once"
    assert "SUM(" in buf.summary


def test_iter_yields_turns_in_order() -> None:
    buf = RollingBuffer(capacity=5, token_budget=10_000)
    for i in range(3):
        buf.append("user", str(i))
    assert [t.content for t in buf] == ["0", "1", "2"]


def test_len_matches_visible_turns() -> None:
    buf = RollingBuffer(capacity=5, token_budget=10_000)
    buf.append("user", "a")
    buf.append("assistant", "b")
    assert len(buf) == 2
