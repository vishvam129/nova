"""Tests for MCP server registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from nova.tools.registry import McpRegistry, McpServerEntry, registry_for


def _entry(name: str = "srv", kind: str = "stdio") -> McpServerEntry:
    return McpServerEntry(name=name, kind=kind, command=["python", "-m", name])  # type: ignore[arg-type]


def test_registry_empty_when_no_file(tmp_path: Path) -> None:
    reg = registry_for(tmp_path)
    assert reg.all() == []


def test_add_persists_across_load(tmp_path: Path) -> None:
    reg = registry_for(tmp_path)
    reg.add(_entry("foo"))
    fresh = registry_for(tmp_path)
    assert [e.name for e in fresh.all()] == ["foo"]


def test_duplicate_add_raises(tmp_path: Path) -> None:
    reg = registry_for(tmp_path)
    reg.add(_entry("foo"))
    with pytest.raises(ValueError):
        reg.add(_entry("foo"))


def test_remove_deletes_entry(tmp_path: Path) -> None:
    reg = registry_for(tmp_path)
    reg.add(_entry("foo"))
    reg.remove("foo")
    assert reg.all() == []


def test_enable_disable(tmp_path: Path) -> None:
    reg = registry_for(tmp_path)
    reg.add(_entry("foo"))
    reg.enable("foo", False)
    entry = reg.get("foo")
    assert entry is not None
    assert entry.enabled is False
    assert reg.enabled() == []


def test_update_replaces_entry(tmp_path: Path) -> None:
    reg = registry_for(tmp_path)
    reg.add(_entry("foo"))
    updated = McpServerEntry(
        name="foo",
        kind="stdio",
        command=["python", "-m", "bar"],  # type: ignore[arg-type]
    )
    reg.update(updated)
    assert reg.get("foo") is not None
    assert reg.get("foo").command == ["python", "-m", "bar"]  # type: ignore[union-attr]


def test_update_missing_raises(tmp_path: Path) -> None:
    reg = registry_for(tmp_path)
    with pytest.raises(ValueError):
        reg.update(_entry("ghost"))


def test_to_transport_dispatches_by_kind(tmp_path: Path) -> None:
    http = McpServerEntry(
        name="x",
        kind="streamable-http",
        url="https://ex.example/mcp",  # type: ignore[arg-type]
    )
    t = http.to_transport()
    assert t.kind == "streamable-http"


def test_registry_names(tmp_path: Path) -> None:
    reg = registry_for(tmp_path)
    reg.add(_entry("a"))
    reg.add(_entry("b"))
    assert set(reg.names()) == {"a", "b"}


def test_mcp_registry_accepts_direct_path(tmp_path: Path) -> None:
    reg = McpRegistry(path=tmp_path / "servers.json")
    reg.load()
    reg.add(_entry("direct"))
    assert (tmp_path / "servers.json").is_file()
