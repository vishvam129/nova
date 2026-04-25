"""Tests for nova.plugins — entry_point plugin discovery."""

from __future__ import annotations

import importlib.metadata
from unittest.mock import MagicMock, patch

from nova.plugins import (
    AGENT_GROUP,
    MCP_GROUP,
    TOOL_GROUP,
    PluginRegistry,
)


def _make_ep(name: str, group: str, value: str = "os:getcwd") -> MagicMock:
    ep = MagicMock(spec=importlib.metadata.EntryPoint)
    ep.name = name
    ep.group = group
    ep.dist = MagicMock()
    ep.dist.name = "fake-package"
    ep.dist.version = "1.0.0"
    ep.load.return_value = object()
    return ep


def _patch_eps(eps: list[MagicMock]):
    """Patch importlib.metadata.entry_points to return the given list."""

    def fake_entry_points(*, group: str):
        return [ep for ep in eps if ep.group == group]

    return patch("nova.plugins.importlib.metadata.entry_points", side_effect=fake_entry_points)


def test_discover_empty() -> None:
    reg = PluginRegistry()
    with _patch_eps([]):
        reg.discover()
    assert reg.tool_plugins == []
    assert reg.mcp_plugins == []
    assert reg.agent_plugins == []


def test_discover_tool_plugin() -> None:
    ep = _make_ep("my_tool", TOOL_GROUP)
    reg = PluginRegistry()
    with _patch_eps([ep]):
        reg.discover()
    tools = reg.tool_plugins
    assert len(tools) == 1
    assert tools[0].name == "my_tool"
    assert tools[0].group == TOOL_GROUP
    assert tools[0].dist_name == "fake-package"


def test_discover_multiple_groups() -> None:
    eps = [
        _make_ep("tool_a", TOOL_GROUP),
        _make_ep("mcp_b", MCP_GROUP),
        _make_ep("agent_c", AGENT_GROUP),
    ]
    reg = PluginRegistry()
    with _patch_eps(eps):
        reg.discover()
    assert len(reg.tool_plugins) == 1
    assert len(reg.mcp_plugins) == 1
    assert len(reg.agent_plugins) == 1


def test_get_by_name() -> None:
    ep = _make_ep("searcher", TOOL_GROUP)
    reg = PluginRegistry()
    with _patch_eps([ep]):
        reg.discover()
    found = reg.get(TOOL_GROUP, "searcher")
    assert found is not None
    assert found.name == "searcher"


def test_get_missing_returns_none() -> None:
    reg = PluginRegistry()
    with _patch_eps([]):
        reg.discover()
    assert reg.get(TOOL_GROUP, "ghost") is None


def test_load_all_skips_broken() -> None:
    good_ep = _make_ep("good", TOOL_GROUP)
    bad_ep = _make_ep("bad", TOOL_GROUP)
    bad_ep.load.side_effect = ImportError("broken")
    reg = PluginRegistry()
    with _patch_eps([good_ep, bad_ep]):
        reg.discover()
    results = reg.load_all(TOOL_GROUP)
    assert len(results) == 1
    assert results[0][0].name == "good"


def test_qualified_name() -> None:
    ep = _make_ep("my_tool", TOOL_GROUP)
    reg = PluginRegistry()
    with _patch_eps([ep]):
        reg.discover()
    entry = reg.tool_plugins[0]
    assert entry.qualified_name == f"{TOOL_GROUP}:my_tool"


def test_discover_clears_previous() -> None:
    ep = _make_ep("tool_a", TOOL_GROUP)
    reg = PluginRegistry()
    with _patch_eps([ep]):
        reg.discover()
    assert len(reg.tool_plugins) == 1
    with _patch_eps([]):
        reg.discover()
    assert len(reg.tool_plugins) == 0


def test_extra_groups() -> None:
    ep = MagicMock(spec=importlib.metadata.EntryPoint)
    ep.name = "custom"
    ep.group = "nova.custom"
    ep.dist = MagicMock()
    ep.dist.name = "pkg"
    ep.dist.version = "0.1"

    reg = PluginRegistry()

    def fake_entry_points(*, group: str):
        return [ep] if group == "nova.custom" else []

    with patch("nova.plugins.importlib.metadata.entry_points", side_effect=fake_entry_points):
        reg.discover(extra_groups=["nova.custom"])
    assert len(reg.list("nova.custom")) == 1
