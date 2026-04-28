"""Meta-router: picks the right agent strategy per request.

Three strategies:
    direct    — single LLM call, no tools (e.g. "what's 2+2?")
    react     — tool-using ReAct loop (e.g. "open spotify and play jazz")
    plan      — Plan-and-Execute for multi-step plans (e.g. "draft a report
                from these 5 docs and email it to alice")

Selection is heuristic: keyword + length + tool-name presence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Strategy(StrEnum):
    DIRECT = "direct"
    REACT = "react"
    PLAN = "plan"


_PLAN_KEYWORDS = (
    "first",
    "then",
    "after that",
    "finally",
    "step",
    "plan",
    "draft",
    "summarize then",
)
_TOOL_HINTS = (
    "open ",
    "send ",
    "call ",
    "search ",
    "play ",
    "schedule ",
    "find ",
    "browse ",
    "navigate ",
    "remind ",
    "set alarm",
    "type ",
    "click ",
)


@dataclass
class MetaRouter:
    """Heuristic strategy picker."""

    plan_min_words: int = 25
    plan_min_steps: int = 2
    keywords_plan: tuple[str, ...] = field(default_factory=lambda: _PLAN_KEYWORDS)
    keywords_tool: tuple[str, ...] = field(default_factory=lambda: _TOOL_HINTS)

    def route(self, prompt: str) -> Strategy:
        p = prompt.lower().strip()
        words = len(p.split())

        # Multi-step indicators → PLAN
        step_count = sum(1 for kw in self.keywords_plan if kw in p)
        if step_count >= self.plan_min_steps or (step_count >= 1 and words >= self.plan_min_words):
            return Strategy.PLAN

        # Tool-action verbs → REACT
        if any(hint in p for hint in self.keywords_tool):
            return Strategy.REACT

        # Question marks alone → DIRECT
        if p.endswith("?") and words < 30:
            return Strategy.DIRECT

        # Short imperative no tools → DIRECT
        if words < 8:
            return Strategy.DIRECT

        # Default to ReAct so the brain has tools available
        return Strategy.REACT


__all__ = ["MetaRouter", "Strategy"]
