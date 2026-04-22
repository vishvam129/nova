"""Plan-and-Execute agent.

Two-phase loop cheaper than ReAct for multi-step tasks with a clear
structure (Google Cloud 2026 design doc: ~3–4 LLM calls vs 5–7 for
ReAct). The planner LLM emits a numbered plan; the executor runs each
step through a sub-agent. On step failure, the planner is asked to
replan from the failure point up to ``max_replans`` times.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from nova.brain.agent import ReactAgent
from nova.brain.llm import ChatMessage, LlmBackend

PLAN_SYSTEM_PROMPT = (
    "You are Nova's planner. Given the user's goal, output a short JSON "
    'array of steps like ["step 1", "step 2"]. Keep it to 2-6 atomic '
    "steps. Reply with ONLY the JSON array."
)


@dataclass(frozen=True, slots=True)
class StepResult:
    step: str
    output: str
    ok: bool


@dataclass(frozen=True, slots=True)
class PlanResult:
    goal: str
    plan: tuple[str, ...]
    steps: tuple[StepResult, ...]
    final: str


@dataclass
class PlanExecuteAgent:
    llm: LlmBackend
    executor: ReactAgent
    max_replans: int = 1
    _history: list[PlanResult] = field(default_factory=list)

    def _plan(self, goal: str, prior_failure: str | None = None) -> list[str]:
        system = PLAN_SYSTEM_PROMPT
        user = goal if not prior_failure else f"{goal}\n\nPrevious attempt failed: {prior_failure}"
        resp = self.llm.chat(
            [ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)]
        )
        return parse_plan(resp.message.content)

    def run(self, goal: str) -> PlanResult:
        plan: list[str] = self._plan(goal)
        step_results: list[StepResult] = []
        replans = 0
        while True:
            failed_step: str | None = None
            for step in plan[len(step_results) :]:
                result = self.executor.run(step)
                ok = not result.final.content.lower().startswith(("error:", "failed"))
                step_results.append(StepResult(step=step, output=result.final.content, ok=ok))
                if not ok:
                    failed_step = step
                    break
            if failed_step is None or replans >= self.max_replans:
                break
            replans += 1
            plan = list(plan[: len(step_results) - 1])
            plan.extend(self._plan(goal, prior_failure=failed_step))
            step_results = step_results[:-1]
        final_text = step_results[-1].output if step_results else "no steps produced"
        outcome = PlanResult(
            goal=goal, plan=tuple(plan), steps=tuple(step_results), final=final_text
        )
        self._history.append(outcome)
        return outcome


_PLAN_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


def parse_plan(text: str) -> list[str]:
    """Extract a JSON list of strings from possibly-messy LLM output."""
    match = _PLAN_ARRAY_RE.search(text)
    if not match:
        # Fall back to line-splitting for free-form output.
        lines = [
            re.sub(r"^\s*[\d\-\*\.]+\s*", "", line).strip()
            for line in text.splitlines()
            if line.strip()
        ]
        return [line for line in lines if line]
    try:
        data: Any = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(x) for x in data]
