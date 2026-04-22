"""Tests for ContextWindow."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from nova.brain.context import ContextWindow, estimate_history_tokens, estimate_tokens
from nova.brain.llm import ChatMessage, ChatResponse


class FakeSummarizer:
    name = "fake"
    model = "fake-1"

    def __init__(self, reply: str = "[SUMMARY]") -> None:
        self.reply = reply
        self.calls = 0

    def chat(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        self.calls += 1
        return ChatResponse(message=ChatMessage(role="assistant", content=self.reply))

    def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> Iterable[str]:
        yield self.reply


def test_estimate_tokens_linear_in_length() -> None:
    assert estimate_tokens("") == 1
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 400) == 100


def test_estimate_history_tokens_sums() -> None:
    hist = [
        ChatMessage(role="user", content="a" * 400),
        ChatMessage(role="assistant", content="b" * 400),
    ]
    assert estimate_history_tokens(hist) == 200


def test_needs_compact_false_below_budget() -> None:
    ctx = ContextWindow(budget_tokens=1000)
    ctx.append(ChatMessage(role="user", content="hi"))
    assert ctx.needs_compact() is False


def test_needs_compact_true_over_budget() -> None:
    ctx = ContextWindow(budget_tokens=50)
    ctx.append(ChatMessage(role="user", content="x" * 1000))
    assert ctx.needs_compact() is True


def test_compact_replaces_old_turns_with_summary() -> None:
    ctx = ContextWindow(budget_tokens=50, keep_recent=2)
    ctx.append(ChatMessage(role="system", content="SYS"))
    for i in range(10):
        ctx.append(ChatMessage(role="user", content=f"old {i} " * 30))
        ctx.append(ChatMessage(role="assistant", content=f"reply {i} " * 30))
    llm = FakeSummarizer()
    summary = ctx.compact(llm)
    assert summary is not None
    assert summary.role == "system"
    history = ctx.history()
    # system + summary + keep_recent tail
    assert history[0].content == "SYS"
    assert "prior summary" in history[1].content
    assert len(history) == 1 + 1 + 2


def test_compact_is_noop_when_history_short() -> None:
    ctx = ContextWindow(budget_tokens=50, keep_recent=2)
    ctx.append(ChatMessage(role="system", content="SYS"))
    ctx.append(ChatMessage(role="user", content="hi"))
    llm = FakeSummarizer()
    assert ctx.compact(llm) is None
    assert llm.calls == 0


def test_maybe_compact_only_runs_when_over_budget() -> None:
    ctx = ContextWindow(budget_tokens=1000, keep_recent=2)
    ctx.append(ChatMessage(role="user", content="hi"))
    llm = FakeSummarizer()
    assert ctx.maybe_compact(llm) is None
    assert llm.calls == 0
