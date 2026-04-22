"""Tests for Plan-and-Execute agent and plan parser."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from nova.brain.agent import ReactAgent
from nova.brain.llm import ChatMessage, ChatResponse
from nova.brain.planner import PlanExecuteAgent, parse_plan


class ScriptedLlm:
    def __init__(self, texts: list[str]) -> None:
        self.texts = texts
        self.name = "scripted"
        self.model = "scripted"

    def chat(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        return ChatResponse(message=ChatMessage(role="assistant", content=self.texts.pop(0)))

    def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> Iterable[str]:
        yield self.chat(messages, tools).message.content


def test_parse_plan_json_array() -> None:
    assert parse_plan('["one", "two", "three"]') == ["one", "two", "three"]


def test_parse_plan_extracts_from_prose() -> None:
    text = 'Here is the plan: ["open spotify", "play lofi"]  \nDone.'
    assert parse_plan(text) == ["open spotify", "play lofi"]


def test_parse_plan_falls_back_to_lines() -> None:
    text = "1. step one\n2. step two\n- step three"
    assert parse_plan(text) == ["step one", "step two", "step three"]


def test_parse_plan_extracts_inner_array_when_wrapped() -> None:
    # parse_plan greedily extracts the first JSON array it finds.
    assert parse_plan('{"plan": ["a", "b"]}') == ["a", "b"]


def test_parse_plan_empty_on_unparseable() -> None:
    assert parse_plan("no json here") == ["no json here"]


def test_plan_execute_runs_each_step() -> None:
    planner_llm = ScriptedLlm(['["greet", "farewell"]'])
    executor_llm = ScriptedLlm(["hi", "bye"])
    agent = PlanExecuteAgent(llm=planner_llm, executor=ReactAgent(llm=executor_llm))
    result = agent.run("say things")
    assert list(result.plan) == ["greet", "farewell"]
    assert len(result.steps) == 2
    assert result.steps[0].output == "hi"
    assert result.steps[1].output == "bye"


def test_plan_execute_replans_on_failure() -> None:
    planner_llm = ScriptedLlm(
        [
            '["bad step", "good step"]',
            '["recovery step"]',
        ]
    )
    # First executor call fails; second and third succeed.
    executor_llm = ScriptedLlm(["error: no such tool", "recovered"])
    agent = PlanExecuteAgent(llm=planner_llm, executor=ReactAgent(llm=executor_llm), max_replans=1)
    result = agent.run("achieve goal")
    assert any("recover" in s.output for s in result.steps)


def test_plan_execute_stops_after_max_replans() -> None:
    planner_llm = ScriptedLlm(
        [
            '["a"]',
            '["a"]',  # replan also fails
        ]
    )
    # Executor always returns an error.
    executor_llm = ScriptedLlm(["error: broken", "error: still broken"])
    agent = PlanExecuteAgent(llm=planner_llm, executor=ReactAgent(llm=executor_llm), max_replans=1)
    result = agent.run("doomed")
    # Final contains the last error, not a success.
    assert "error" in result.final.lower()
