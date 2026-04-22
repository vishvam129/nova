"""Per-tool approval policy.

Each tool is assigned one of four policies:
  * ``AUTO``             — run without asking (safe reads)
  * ``QUIET_CONFIRM``    — show a 1s cancellable toast, run if no cancel
  * ``REQUIRE_CONFIRM``  — block until the user explicitly confirms
  * ``DENIED``           — never run

The UI plugs in a ``Confirmer`` callback so the core agent stays
platform-agnostic. A tiny ``in_memory_confirmer`` helper is provided
for tests.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Policy(StrEnum):
    AUTO = "auto"
    QUIET_CONFIRM = "quiet"
    REQUIRE_CONFIRM = "confirm"
    DENIED = "denied"


@dataclass(frozen=True, slots=True)
class ConfirmRequest:
    tool: str
    arguments: dict[str, object]
    policy: Policy


Confirmer = Callable[[ConfirmRequest], bool]


def in_memory_confirmer(decisions: dict[str, bool]) -> Confirmer:
    """Build a Confirmer that looks up decisions by tool name."""

    def _confirm(req: ConfirmRequest) -> bool:
        return decisions.get(req.tool, False)

    return _confirm


@dataclass
class ApprovalManager:
    default: Policy = Policy.QUIET_CONFIRM
    policies: dict[str, Policy] = field(default_factory=dict)
    quiet_timeout_ms: int = 1000

    def set(self, tool: str, policy: Policy) -> None:
        self.policies[tool] = policy

    def get(self, tool: str) -> Policy:
        return self.policies.get(tool, self.default)

    def authorize(
        self,
        tool: str,
        arguments: dict[str, object],
        confirmer: Confirmer,
        sleep: Callable[[float], None] = time.sleep,
    ) -> bool:
        policy = self.get(tool)
        req = ConfirmRequest(tool=tool, arguments=arguments, policy=policy)
        if policy is Policy.AUTO:
            return True
        if policy is Policy.DENIED:
            return False
        if policy is Policy.QUIET_CONFIRM:
            # Give the user a moment to cancel; confirmer returns True to cancel.
            sleep(self.quiet_timeout_ms / 1000.0)
            cancelled = confirmer(req)
            return not cancelled
        # REQUIRE_CONFIRM — confirmer returns True to approve.
        return confirmer(req)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "default": self.default.value,
                    "quiet_timeout_ms": self.quiet_timeout_ms,
                    "policies": {k: v.value for k, v in self.policies.items()},
                },
                indent=2,
            )
        )

    def load(self, path: Path) -> None:
        if not path.is_file():
            return
        data = json.loads(path.read_text())
        self.default = Policy(data.get("default", self.default.value))
        self.quiet_timeout_ms = int(data.get("quiet_timeout_ms", self.quiet_timeout_ms))
        self.policies = {k: Policy(v) for k, v in data.get("policies", {}).items()}


__all__ = [
    "ApprovalManager",
    "ConfirmRequest",
    "Confirmer",
    "Policy",
    "in_memory_confirmer",
]
