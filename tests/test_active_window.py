"""Tests for nova.context.active_window."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from nova.context.active_window import ActiveWindow, get_active_window


def test_active_window_to_prompt_known() -> None:
    w = ActiveWindow(app="VS Code", title="main.py — nova")
    p = w.to_prompt()
    assert "VS Code" in p
    assert "main.py" in p


def test_active_window_to_prompt_app_only() -> None:
    w = ActiveWindow(app="Spotify")
    assert "Spotify" in w.to_prompt()


def test_active_window_to_prompt_unknown() -> None:
    assert ActiveWindow().to_prompt() == ""


def test_is_known() -> None:
    assert ActiveWindow().is_known() is False
    assert ActiveWindow(app="x").is_known() is True


def test_get_active_window_linux() -> None:
    def which(name: str) -> str | None:
        return "/usr/bin/xdotool" if name == "xdotool" else None

    def fake_run(cmd: list[str], **_kw: object) -> MagicMock:
        last = cmd[-1]
        out = {
            "getwindowname": b"My Doc",
            "getwindowpid": b"4242",
            "getwindowclassname": b"firefox",
        }.get(last, b"")
        return MagicMock(returncode=0, stdout=out)

    with (
        patch("nova.context.active_window.sys.platform", "linux"),
        patch("nova.context.active_window.shutil.which", side_effect=which),
        patch("nova.context.active_window.subprocess.run", side_effect=fake_run),
    ):
        w = get_active_window()
    assert w.app == "firefox"
    assert w.title == "My Doc"
    assert w.pid == 4242


def test_get_active_window_unsupported_platform() -> None:
    with patch("nova.context.active_window.sys.platform", "haiku"):
        w = get_active_window()
    assert w.is_known() is False


def test_get_active_window_linux_no_xdotool() -> None:
    with (
        patch("nova.context.active_window.sys.platform", "linux"),
        patch("nova.context.active_window.shutil.which", return_value=None),
    ):
        w = get_active_window()
    assert w.is_known() is False
