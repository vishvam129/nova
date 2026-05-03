"""Tests for nova.integrations.composio."""

from __future__ import annotations

import json
from pathlib import Path

from nova.integrations.composio import ComposioCatalog, ComposioTool, merge


def _write_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "api_key": "abc",
                "tools": [
                    {"name": "send_message", "app": "slack", "description": "Slack DM"},
                    {"name": "create_page", "app": "notion", "description": "Page"},
                    {
                        "name": "create_issue",
                        "app": "linear",
                        "description": "issue",
                        "enabled": False,
                    },
                ],
            }
        )
    )


def test_qualified_name() -> None:
    t = ComposioTool(name="send", app="slack")
    assert t.qualified_name == "slack.send"


def test_load_from_config(tmp_path: Path) -> None:
    p = tmp_path / "composio.json"
    _write_config(p)
    cat = ComposioCatalog.from_config(p)
    assert cat.api_key == "abc"
    assert len(cat.tools) == 3


def test_enabled_filters_disabled(tmp_path: Path) -> None:
    p = tmp_path / "composio.json"
    _write_config(p)
    cat = ComposioCatalog.from_config(p)
    enabled = cat.enabled()
    assert len(enabled) == 2
    assert all(t.enabled for t in enabled)


def test_by_app(tmp_path: Path) -> None:
    p = tmp_path / "composio.json"
    _write_config(p)
    cat = ComposioCatalog.from_config(p)
    slack = cat.by_app("slack")
    assert len(slack) == 1
    assert slack[0].name == "send_message"


def test_apps_unique(tmp_path: Path) -> None:
    p = tmp_path / "composio.json"
    _write_config(p)
    cat = ComposioCatalog.from_config(p)
    apps = cat.apps()
    assert "slack" in apps
    assert "notion" in apps
    assert "linear" not in apps  # disabled


def test_search_matches_description(tmp_path: Path) -> None:
    p = tmp_path / "composio.json"
    _write_config(p)
    cat = ComposioCatalog.from_config(p)
    out = cat.search("page")
    assert len(out) == 1
    assert out[0].app == "notion"


def test_to_registry_payload(tmp_path: Path) -> None:
    p = tmp_path / "composio.json"
    _write_config(p)
    cat = ComposioCatalog.from_config(p)
    payload = cat.to_registry_payload()
    assert isinstance(payload, list)
    assert all("qualified_name" in item for item in payload)


def test_merge_dedupes() -> None:
    a = ComposioCatalog(
        api_key="x",
        tools=[ComposioTool(name="t", app="slack")],
    )
    b = ComposioCatalog(
        api_key="y",
        tools=[ComposioTool(name="t", app="slack"), ComposioTool(name="other", app="notion")],
    )
    out = merge([a, b])
    assert len(out) == 2  # slack.t deduped


def test_tool_to_dict() -> None:
    t = ComposioTool(name="send", app="slack", description="x")
    d = t.to_dict()
    assert d["qualified_name"] == "slack.send"
