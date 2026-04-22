"""Tests for open_app."""

from __future__ import annotations

from nova.tools.builtin.open_app import OpenResult, open_app


def test_open_app_uses_xdg_open_on_linux() -> None:
    seen: list[list[str]] = []
    result = open_app("firefox", system="Linux", runner=seen.append)
    assert result.ok is True
    assert seen == [["xdg-open", "firefox"]]


def test_open_app_uses_open_on_macos() -> None:
    seen: list[list[str]] = []
    result = open_app("https://ex.example", system="Darwin", runner=seen.append)
    assert result.ok is True
    assert seen[0][0] == "open"


def test_open_app_uses_cmd_start_on_windows() -> None:
    seen: list[list[str]] = []
    result = open_app("notepad.exe", system="Windows", runner=seen.append)
    assert result.ok is True
    assert seen[0][:3] == ["cmd", "/c", "start"]


def test_open_app_propagates_oserror() -> None:
    def explode(_cmd: list[str]) -> None:
        raise OSError("no display")

    result = open_app("firefox", system="Linux", runner=explode)
    assert result.ok is False
    assert "no display" in (result.error or "")


def test_open_result_is_immutable() -> None:
    import pytest

    r = OpenResult(ok=True, command=["xdg-open", "x"])
    with pytest.raises(AttributeError):
        r.ok = False  # type: ignore[misc]
