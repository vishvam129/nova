"""Tests for LLM backend abstraction."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import pytest

from nova.brain.llm import (
    ChatMessage,
    ChatResponse,
    LlmBackend,
    ToolCall,
    available_llms,
    create_llm,
    register_llm,
)


class FakeLlm:
    name = "fake"
    model = "fake-1"

    def __init__(self, reply: str = "pong", model: str = "fake-1") -> None:
        self.reply = reply
        self.model = model
        self.seen: list[Sequence[ChatMessage]] = []

    def chat(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        self.seen.append(messages)
        return ChatResponse(
            message=ChatMessage(role="assistant", content=self.reply),
            input_tokens=10,
            output_tokens=5,
        )

    def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> Iterable[str]:
        yield from self.reply.split(" ")


def test_builtin_backends_registered() -> None:
    names = available_llms()
    for n in ("ollama", "llama.cpp", "vllm", "claude", "openai", "gemini"):
        assert n in names


def test_unknown_backend_raises() -> None:
    with pytest.raises(ValueError):
        create_llm("no-such-llm")


def test_register_and_create_custom_backend() -> None:
    register_llm("fake", lambda **kw: FakeLlm(**kw))  # type: ignore[arg-type]
    llm = create_llm("fake")
    assert isinstance(llm, LlmBackend)
    resp = llm.chat([ChatMessage(role="user", content="ping")])
    assert resp.message.content == "pong"
    assert resp.input_tokens == 10


def test_stream_yields_tokens() -> None:
    register_llm("fake", lambda **kw: FakeLlm(reply="hello world", **kw))  # type: ignore[arg-type]
    llm = create_llm("fake")
    toks = list(llm.stream([ChatMessage(role="user", content="hi")]))
    assert toks == ["hello", "world"]


def test_chat_message_is_frozen() -> None:
    m = ChatMessage(role="user", content="hi")
    with pytest.raises(AttributeError):
        m.content = "nope"  # type: ignore[misc]


def test_tool_call_dataclass() -> None:
    tc = ToolCall(id="t1", name="run_shell", arguments={"cmd": "ls"})
    assert tc.arguments["cmd"] == "ls"
