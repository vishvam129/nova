"""Tests for nova.tools.builtin.system_control."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from nova.tools.builtin.system_control import SystemControl


def _ok() -> MagicMock:
    return MagicMock(returncode=0)


def test_set_volume_clamped_high() -> None:
    sc = SystemControl(platform="linux")
    with (
        patch("nova.tools.builtin.system_control.shutil.which", return_value="/usr/bin/pactl"),
        patch("nova.tools.builtin.system_control.subprocess.run", return_value=_ok()) as run,
    ):
        assert sc.set_volume(200) is True
        cmd = run.call_args[0][0]
        assert cmd[-1] == "100%"


def test_set_volume_clamped_low() -> None:
    sc = SystemControl(platform="linux")
    with (
        patch("nova.tools.builtin.system_control.shutil.which", return_value="/usr/bin/pactl"),
        patch("nova.tools.builtin.system_control.subprocess.run", return_value=_ok()) as run,
    ):
        sc.set_volume(-50)
        assert run.call_args[0][0][-1] == "0%"


def test_set_volume_no_tool_returns_false() -> None:
    sc = SystemControl(platform="linux")
    with patch("nova.tools.builtin.system_control.shutil.which", return_value=None):
        assert sc.set_volume(50) is False


def test_set_volume_macos_uses_osascript() -> None:
    sc = SystemControl(platform="darwin")
    with (
        patch("nova.tools.builtin.system_control.shutil.which", return_value="/usr/bin/osascript"),
        patch("nova.tools.builtin.system_control.subprocess.run", return_value=_ok()) as run,
    ):
        sc.set_volume(50)
        assert run.call_args[0][0][0] == "osascript"


def test_set_brightness_uses_brightnessctl() -> None:
    sc = SystemControl(platform="linux")

    def which(name: str) -> str | None:
        return "/usr/bin/brightnessctl" if name == "brightnessctl" else None

    with (
        patch("nova.tools.builtin.system_control.shutil.which", side_effect=which),
        patch("nova.tools.builtin.system_control.subprocess.run", return_value=_ok()) as run,
    ):
        assert sc.set_brightness(50) is True
        assert run.call_args[0][0][0] == "brightnessctl"


def test_lock_linux_loginctl() -> None:
    sc = SystemControl(platform="linux")
    with (
        patch("nova.tools.builtin.system_control.shutil.which", return_value="/usr/bin/loginctl"),
        patch("nova.tools.builtin.system_control.subprocess.run", return_value=_ok()) as run,
    ):
        assert sc.lock() is True
        assert run.call_args[0][0][0] == "loginctl"


def test_sleep_linux_systemctl() -> None:
    sc = SystemControl(platform="linux")
    with (
        patch("nova.tools.builtin.system_control.shutil.which", return_value="/bin/systemctl"),
        patch("nova.tools.builtin.system_control.subprocess.run", return_value=_ok()) as run,
    ):
        assert sc.sleep() is True
        assert run.call_args[0][0] == ["systemctl", "suspend"]


def test_unknown_platform_returns_false() -> None:
    sc = SystemControl(platform="haiku")
    assert sc.set_volume(50) is False
    assert sc.set_brightness(50) is False
    assert sc.lock() is False
    assert sc.sleep() is False
    assert sc.wake() is False


def test_run_returns_false_on_subprocess_error() -> None:
    sc = SystemControl(platform="linux")
    with (
        patch("nova.tools.builtin.system_control.shutil.which", return_value="/x"),
        patch("nova.tools.builtin.system_control.subprocess.run", side_effect=OSError),
    ):
        assert sc.set_volume(50) is False
