"""Tests for nova.quality.eval_harness."""

from __future__ import annotations

from nova.quality.eval_harness import (
    EvalHarness,
    TaskCase,
    default_suite,
)


class _ScriptedAgent:
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping
        self.calls = 0

    def run(self, prompt: str) -> str:
        self.calls += 1
        for key, val in self.mapping.items():
            if key in prompt:
                return val
        return ""


class _BoomAgent:
    def run(self, prompt: str) -> str:
        raise RuntimeError("oops")


def test_grade_pass_with_contains() -> None:
    case = TaskCase(id="t1", prompt="hi", expect_contains=("hello",))
    passed, reason = case.grade("Hello there")
    assert passed is True
    assert reason == "ok"


def test_grade_fail_missing_phrase() -> None:
    case = TaskCase(id="t2", prompt="hi", expect_contains=("hello",))
    passed, reason = case.grade("nope")
    assert passed is False
    assert "missing" in reason


def test_grade_fail_negative_phrase() -> None:
    case = TaskCase(id="t3", prompt="hi", expect_not_contains=("error",))
    passed, _ = case.grade("Got an error")
    assert passed is False


def test_grade_pass_with_regex() -> None:
    case = TaskCase(id="t4", prompt="time?", expect_regex=r"\d+:\d+")
    passed, _ = case.grade("It's 14:30 now")
    assert passed is True


def test_grade_fail_regex() -> None:
    case = TaskCase(id="t5", prompt="time?", expect_regex=r"\d+:\d+")
    passed, _ = case.grade("don't know")
    assert passed is False


def test_harness_runs_all_cases() -> None:
    harness = EvalHarness(
        cases=[
            TaskCase(id="a", prompt="say hi", expect_contains=("hello",)),
            TaskCase(id="b", prompt="say bye", expect_contains=("goodbye",)),
        ]
    )
    agent = _ScriptedAgent({"hi": "hello world", "bye": "goodbye"})
    report = harness.run(agent)
    assert report.total == 2
    assert report.passed == 2
    assert report.failed == 0


def test_harness_records_failures() -> None:
    harness = EvalHarness(cases=[TaskCase(id="a", prompt="say hi", expect_contains=("hello",))])
    agent = _ScriptedAgent({"hi": "wrong"})
    report = harness.run(agent)
    assert report.passed == 0
    assert report.failed == 1


def test_harness_handles_agent_exception() -> None:
    harness = EvalHarness(cases=[TaskCase(id="a", prompt="x")])
    report = harness.run(_BoomAgent())
    assert report.failed == 1
    assert "exception" in report.outcomes[0].reason


def test_pass_rate_zero_cases() -> None:
    harness = EvalHarness()
    report = harness.run(_ScriptedAgent({}))
    assert report.pass_rate == 0.0


def test_by_category() -> None:
    cases = [
        TaskCase(id="a", prompt="x", category="info"),
        TaskCase(id="b", prompt="x", category="info"),
        TaskCase(id="c", prompt="x", category="action"),
    ]
    harness = EvalHarness(cases=cases)
    report = harness.run(_ScriptedAgent({"x": "ok"}))
    by_cat = report.by_category(cases)
    assert by_cat["info"][1] == 2
    assert by_cat["action"][1] == 1


def test_default_suite_non_empty() -> None:
    suite = default_suite()
    assert len(suite) >= 5
    assert all(isinstance(c, TaskCase) for c in suite)


def test_summary_line_includes_counts() -> None:
    harness = EvalHarness(cases=[TaskCase(id="a", prompt="x", expect_contains=("yes",))])
    report = harness.run(_ScriptedAgent({"x": "yes"}))
    line = report.summary_line()
    assert "1/1" in line
    assert "100" in line
