"""Tests for nova.cli."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from nova.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "nova" in result.stdout


def test_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for sub in ("run", "eval", "devices", "mcp", "memory", "config"):
        assert sub in result.stdout


def test_config_show_outputs_json(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "voice" in data and "brain" in data and "server" in data


def test_devices_list_empty(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    result = runner.invoke(app, ["devices", "list"])
    assert result.exit_code == 0
    assert "no paired devices" in result.stdout
