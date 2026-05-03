"""Composio MCP bundle integration: 500+ SaaS tools in one config.

Composio exposes a unified registry of tools across SaaS apps (Slack,
Notion, Linear, etc.).  This module loads a Composio config file and
filters/normalises the tool catalogue into a list Nova's plugin
registry can consume.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ComposioTool:
    name: str
    app: str
    description: str = ""
    enabled: bool = True
    auth_required: bool = True

    @property
    def qualified_name(self) -> str:
        return f"{self.app}.{self.name}"

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "app": self.app,
            "description": self.description,
            "enabled": self.enabled,
            "auth_required": self.auth_required,
            "qualified_name": self.qualified_name,
        }


@dataclass
class ComposioCatalog:
    """Loads Composio's tool list and exposes filters Nova needs."""

    api_key: str
    tools: list[ComposioTool] = field(default_factory=list)

    @classmethod
    def from_config(cls, path: Path) -> ComposioCatalog:
        data: dict[str, Any] = json.loads(path.read_text())
        api_key = str(data.get("api_key", ""))
        items: list[ComposioTool] = []
        for entry in data.get("tools", []):
            items.append(_tool_from_entry(entry))
        return cls(api_key=api_key, tools=items)

    def enabled(self) -> list[ComposioTool]:
        return [t for t in self.tools if t.enabled]

    def by_app(self, app: str) -> list[ComposioTool]:
        return [t for t in self.tools if t.app.lower() == app.lower() and t.enabled]

    def apps(self) -> list[str]:
        return sorted({t.app for t in self.tools if t.enabled})

    def search(self, query: str) -> list[ComposioTool]:
        q = query.lower().strip()
        return [
            t
            for t in self.enabled()
            if q in t.name.lower() or q in t.app.lower() or q in t.description.lower()
        ]

    def to_registry_payload(self) -> list[dict[str, object]]:
        return [t.to_dict() for t in self.enabled()]


def _tool_from_entry(entry: dict[str, Any]) -> ComposioTool:
    return ComposioTool(
        name=str(entry["name"]),
        app=str(entry.get("app", "")),
        description=str(entry.get("description", "")),
        enabled=bool(entry.get("enabled", True)),
        auth_required=bool(entry.get("auth_required", True)),
    )


def merge(catalogs: Iterable[ComposioCatalog]) -> list[ComposioTool]:
    """Merge multiple catalogs, deduping on qualified_name."""
    seen: dict[str, ComposioTool] = {}
    for cat in catalogs:
        for t in cat.enabled():
            seen.setdefault(t.qualified_name, t)
    return list(seen.values())


__all__ = ["ComposioCatalog", "ComposioTool", "merge"]
