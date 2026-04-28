"""Tests for nova.brain.meta_router."""

from __future__ import annotations

from nova.brain.meta_router import MetaRouter, Strategy


def test_short_question_is_direct() -> None:
    r = MetaRouter()
    assert r.route("what is 2 plus 2?") is Strategy.DIRECT


def test_short_imperative_is_direct() -> None:
    r = MetaRouter()
    assert r.route("hello there") is Strategy.DIRECT


def test_tool_verb_is_react() -> None:
    r = MetaRouter()
    assert r.route("open spotify and play jazz") is Strategy.REACT


def test_send_command_is_react() -> None:
    r = MetaRouter()
    assert r.route("send a text to mom saying I'm late") is Strategy.REACT


def test_multi_step_is_plan() -> None:
    r = MetaRouter()
    prompt = "First read the spec, then summarize it, finally email the summary"
    assert r.route(prompt) is Strategy.PLAN


def test_plan_keyword_with_long_text_is_plan() -> None:
    r = MetaRouter()
    prompt = "Please draft a comprehensive multi-paragraph technical report "
    prompt += "covering all of the recent changes to our internal codebase "
    prompt += "including refactors, new features, bug fixes, performance work, "
    prompt += "documentation updates and any user-visible behavior changes."
    assert r.route(prompt) is Strategy.PLAN


def test_strategy_values() -> None:
    assert Strategy.DIRECT == "direct"
    assert Strategy.REACT == "react"
    assert Strategy.PLAN == "plan"


def test_long_non_tool_defaults_to_react() -> None:
    r = MetaRouter()
    prompt = "I was wondering about the meaning of strange events happening lately"
    assert r.route(prompt) is Strategy.REACT
