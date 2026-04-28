"""Eval harness: personal task suite with pass/fail scoring.

A ``TaskCase`` describes one common user request and the criteria for
"the agent did the right thing".  ``EvalHarness`` runs an Agent (Protocol)
across all cases and produces a ``Report`` with per-case + aggregate stats.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


class Agent(Protocol):
    """Anything that turns a prompt into a final reply text."""

    def run(self, prompt: str) -> str: ...


@dataclass(frozen=True, slots=True)
class TaskCase:
    """One scored request."""

    id: str
    prompt: str
    expect_contains: tuple[str, ...] = ()
    expect_regex: str = ""
    expect_not_contains: tuple[str, ...] = ()
    category: str = "general"

    def grade(self, response: str) -> tuple[bool, str]:
        """Return ``(passed, reason)`` for *response*."""
        text = response.lower()
        for needle in self.expect_contains:
            if needle.lower() not in text:
                return False, f"missing required phrase {needle!r}"
        for negative in self.expect_not_contains:
            if negative.lower() in text:
                return False, f"contains forbidden phrase {negative!r}"
        if self.expect_regex and not re.search(self.expect_regex, response, re.I | re.S):
            return False, f"regex {self.expect_regex!r} did not match"
        return True, "ok"


@dataclass(frozen=True, slots=True)
class Outcome:
    case_id: str
    passed: bool
    response: str
    reason: str
    duration_s: float


@dataclass(frozen=True, slots=True)
class Report:
    outcomes: tuple[Outcome, ...]
    started_at: datetime

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def passed(self) -> int:
        return sum(1 for o in self.outcomes if o.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def by_category(self, cases: Iterable[TaskCase]) -> dict[str, tuple[int, int]]:
        cat_for: dict[str, str] = {c.id: c.category for c in cases}
        counts: dict[str, list[int]] = {}
        for o in self.outcomes:
            cat = cat_for.get(o.case_id, "general")
            bucket = counts.setdefault(cat, [0, 0])
            bucket[0] += int(o.passed)
            bucket[1] += 1
        return {k: (v[0], v[1]) for k, v in counts.items()}

    def summary_line(self) -> str:
        return (
            f"{self.passed}/{self.total} passed "
            f"({self.pass_rate * 100:.1f}%) "
            f"started {self.started_at.isoformat()}"
        )


@dataclass
class EvalHarness:
    """Runs an Agent across a TaskCase suite."""

    cases: list[TaskCase] = field(default_factory=list)

    def add(self, case: TaskCase) -> None:
        self.cases.append(case)

    def run(self, agent: Agent) -> Report:
        import time

        outcomes: list[Outcome] = []
        started = datetime.now()
        for case in self.cases:
            t0 = time.monotonic()
            try:
                response = agent.run(case.prompt)
            except Exception as exc:  # noqa: BLE001
                outcomes.append(
                    Outcome(
                        case_id=case.id,
                        passed=False,
                        response="",
                        reason=f"exception: {exc!r}",
                        duration_s=time.monotonic() - t0,
                    )
                )
                continue
            passed, reason = case.grade(response)
            outcomes.append(
                Outcome(
                    case_id=case.id,
                    passed=passed,
                    response=response,
                    reason=reason,
                    duration_s=time.monotonic() - t0,
                )
            )
        return Report(outcomes=tuple(outcomes), started_at=started)


def default_suite() -> list[TaskCase]:
    """A starter set of common-request cases (subset; real suite is 50+)."""
    return [
        TaskCase(
            id="time-now",
            prompt="What time is it right now?",
            expect_regex=r"\d{1,2}",
            category="info",
        ),
        TaskCase(
            id="weather",
            prompt="What's the weather like today?",
            expect_contains=("weather",),
            category="info",
        ),
        TaskCase(
            id="open-spotify",
            prompt="Open Spotify and play some jazz",
            expect_contains=("spotify",),
            category="action",
        ),
        TaskCase(
            id="reminder",
            prompt="Remind me to call mom at 6pm",
            expect_contains=("remind",),
            expect_not_contains=("can't",),
            category="action",
        ),
        TaskCase(
            id="email-summary",
            prompt="Summarize my unread emails",
            expect_contains=("email",),
            category="info",
        ),
    ]


__all__ = ["Agent", "EvalHarness", "Outcome", "Report", "TaskCase", "default_suite"]
