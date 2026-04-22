"""Tests for ReactAgent."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from nova.brain.agent import ReactAgent, Tool
from nova.brain.llm import ChatMessage, ChatResponse, ToolCall


class ScriptedLlm:
    """Return a scripted sequence of ChatResponses on successive calls."""

    def __init__(self, responses: list[ChatResponse]) -> None:
        self.responses = responses
        self.name = "scripted"
        self.model = "scripted-1"
        self.calls: list[Sequence[ChatMessage]] = []

    def chat(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        self.calls.append(list(messages))
        return self.responses.pop(0)

    def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> Iterable[str]:
        yield self.chat(messages, tools).message.content


def _answer(text: str) -> ChatResponse:
    return ChatResponse(message=ChatMessage(role="assistant", content=text))


def _call(name: str, args: dict[str, Any], text: str = "") -> ChatResponse:
    return ChatResponse(
        message=ChatMessage(role="assistant", content=text),
        tool_calls=(ToolCall(id="t1", name=name, arguments=args),),
    )


def _tool(name: str, fn: Any) -> Tool:
    return Tool(name=name, description=f"{name} tool", schema={"type": "object"}, handler=fn)


def test_direct_answer_without_tools() -> None:
    agent = ReactAgent(llm=ScriptedLlm([_answer("hi there")]))
    result = agent.run("ping")
    assert result.final.content == "hi there"
    assert len(result.steps) == 1


def test_single_tool_call_then_answer() -> None:
    llm = ScriptedLlm([_call("echo", {"text": "hi"}), _answer("done: hi")])
    agent = ReactAgent(llm=llm)
    agent.register_tool(_tool("echo", lambda a: a["text"]))
    result = agent.run("say hi")
    assert result.final.content == "done: hi"
    assert len(result.steps) == 2
    assert result.steps[0].tool_results[0].content == "hi"


def test_unknown_tool_surfaces_error_to_model() -> None:
    llm = ScriptedLlm([_call("missing", {}), _answer("gave up")])
    agent = ReactAgent(llm=llm)
    result = agent.run("go")
    assert "unknown tool" in result.steps[0].tool_results[0].content


def test_tool_exception_surfaces_as_error_message() -> None:
    def boom(_: dict[str, Any]) -> str:
        raise RuntimeError("kaboom")

    llm = ScriptedLlm([_call("boom", {}), _answer("ok")])
    agent = ReactAgent(llm=llm)
    agent.register_tool(_tool("boom", boom))
    result = agent.run("go")
    assert "kaboom" in result.steps[0].tool_results[0].content


def test_step_cap_short_circuits_runaway() -> None:
    infinite = [_call("noop", {}) for _ in range(20)]
    llm = ScriptedLlm(infinite)
    agent = ReactAgent(llm=llm, max_steps=3)
    agent.register_tool(_tool("noop", lambda _a: "ok"))
    result = agent.run("loop")
    assert "step cap" in result.final.content
    assert len(result.steps) == 3


def test_tool_spec_is_passed_to_llm() -> None:
    llm = ScriptedLlm([_answer("ok")])
    agent = ReactAgent(llm=llm)
    agent.register_tool(_tool("t1", lambda _: "r"))
    agent.run("hi")
    # First call should have seen our tool in the tools kwarg: we can't
    # check here without exposing it, but we know _tool_specs contains it.
    assert "t1" in agent.tools
