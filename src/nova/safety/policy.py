"""Unified allowlist/denylist engine.

Supports four resource kinds out of the box — paths (fnmatch), domains
(suffix match), commands (first-token match), and MCP tools (exact
match). A single ``PolicyEngine`` holds the rules for each kind so the
core agent has one place to consult before executing anything.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urlparse


class Verdict(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    UNKNOWN = "unknown"


@dataclass
class Rules:
    allow: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)


def _path_match(pattern: str, target: str) -> bool:
    return fnmatch.fnmatchcase(target, pattern)


def _domain_match(pattern: str, target: str) -> bool:
    pattern = pattern.lstrip(".").lower()
    target = target.lower()
    return target == pattern or target.endswith("." + pattern)


def _command_match(pattern: str, target: str) -> bool:
    head = target.split()[0] if target.strip() else ""
    head = head.split("/")[-1]
    return fnmatch.fnmatchcase(head, pattern)


def _tool_match(pattern: str, target: str) -> bool:
    return pattern == "*" or pattern == target


_MATCHERS = {
    "path": _path_match,
    "domain": _domain_match,
    "command": _command_match,
    "tool": _tool_match,
}


@dataclass
class PolicyEngine:
    paths: Rules = field(default_factory=Rules)
    domains: Rules = field(default_factory=Rules)
    commands: Rules = field(default_factory=Rules)
    tools: Rules = field(default_factory=Rules)
    default: Verdict = Verdict.UNKNOWN

    def _rules_for(self, kind: str) -> Rules:
        return {
            "path": self.paths,
            "domain": self.domains,
            "command": self.commands,
            "tool": self.tools,
        }[kind]

    def _matcher(self, kind: str):  # type: ignore[no-untyped-def]
        return _MATCHERS[kind]

    def _resource(self, kind: str, resource: str) -> str:
        if kind == "domain":
            parsed = urlparse(resource if "://" in resource else f"//{resource}", scheme="")
            return (parsed.hostname or resource).lower()
        return resource

    def check(self, kind: str, resource: str) -> Verdict:
        rules = self._rules_for(kind)
        match = self._matcher(kind)
        target = self._resource(kind, resource)
        for pattern in rules.deny:
            if match(pattern, target):
                return Verdict.DENY
        for pattern in rules.allow:
            if match(pattern, target):
                return Verdict.ALLOW
        return self.default

    def allow(self, kind: str, pattern: str) -> None:
        self._rules_for(kind).allow.append(pattern)

    def deny(self, kind: str, pattern: str) -> None:
        self._rules_for(kind).deny.append(pattern)


__all__ = ["PolicyEngine", "Rules", "Verdict"]
