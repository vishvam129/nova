"""Hybrid local/cloud LLM router.

Scores each request on four axes — difficulty, required tools, privacy,
cost headroom — and sends it to the cheapest backend that can handle
it. Decisions are logged (with reason) so cost and latency regressions
are debuggable after the fact.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from nova.brain.llm import ChatMessage, LlmBackend

logger = logging.getLogger(__name__)


class Privacy(StrEnum):
    PUBLIC = "public"  # ok to send to cloud
    PERSONAL = "personal"  # local-first
    SECRET = "secret"  # never leaves device


Difficulty = Literal["trivial", "easy", "medium", "hard"]


@dataclass(frozen=True, slots=True)
class RouteRequest:
    messages: Sequence[ChatMessage]
    difficulty: Difficulty = "easy"
    tools_required: tuple[str, ...] = ()
    privacy: Privacy = Privacy.PERSONAL
    needs_vision: bool = False
    needs_computer_use: bool = False


@dataclass(frozen=True, slots=True)
class RouteDecision:
    target: Literal["local", "cloud"]
    reason: str
    score: float


@dataclass
class HybridRouter:
    local: LlmBackend
    cloud: LlmBackend | None = None
    daily_cost_cap_usd: float = 1.0
    spend_today_usd: float = 0.0
    decisions: list[RouteDecision] = field(default_factory=list)

    def _force_local(self, req: RouteRequest) -> str | None:
        if self.cloud is None:
            return "no cloud backend configured"
        if req.privacy == Privacy.SECRET:
            return "privacy=secret"
        if self.spend_today_usd >= self.daily_cost_cap_usd:
            return f"cost cap ${self.daily_cost_cap_usd:.2f} reached"
        return None

    def _force_cloud(self, req: RouteRequest) -> str | None:
        if req.needs_computer_use:
            return "computer-use requires cloud vision model"
        if req.difficulty == "hard":
            return "difficulty=hard"
        if req.needs_vision:
            return "vision request"
        return None

    def decide(self, req: RouteRequest) -> RouteDecision:
        forced_local = self._force_local(req)
        forced_cloud = None if forced_local else self._force_cloud(req)
        if forced_local:
            dec = RouteDecision(target="local", reason=forced_local, score=0.0)
        elif forced_cloud:
            dec = RouteDecision(target="cloud", reason=forced_cloud, score=1.0)
        else:
            score = _score(req)
            if score >= 0.5 and self.cloud is not None:
                dec = RouteDecision(target="cloud", reason=f"score={score:.2f}", score=score)
            else:
                dec = RouteDecision(
                    target="local", reason=f"score={score:.2f} within local budget", score=score
                )
        logger.info(
            "route %s: %s (privacy=%s difficulty=%s tools=%d)",
            dec.target,
            dec.reason,
            req.privacy,
            req.difficulty,
            len(req.tools_required),
        )
        self.decisions.append(dec)
        return dec

    def pick(self, req: RouteRequest) -> LlmBackend:
        dec = self.decide(req)
        if dec.target == "cloud" and self.cloud is not None:
            return self.cloud
        return self.local


def _score(req: RouteRequest) -> float:
    difficulty_weight = {"trivial": 0.0, "easy": 0.1, "medium": 0.5, "hard": 0.9}[req.difficulty]
    tools_weight = min(0.3, 0.05 * len(req.tools_required))
    privacy_penalty = 0.4 if req.privacy == Privacy.PERSONAL else 0.0
    vision_bonus = 0.4 if req.needs_vision else 0.0
    raw = difficulty_weight + tools_weight + vision_bonus - privacy_penalty
    return max(0.0, min(1.0, raw))
