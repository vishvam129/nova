"""Tests for nova.server.home_brain."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from nova.server.home_brain import HomeBrainMode


def test_initial_status_disabled() -> None:
    h = HomeBrainMode()
    assert h.status.enabled is False


def test_enable_linux_with_inhibitor() -> None:
    h = HomeBrainMode()
    fake_proc = MagicMock(pid=12345)
    with (
        patch("nova.server.home_brain.sys.platform", "linux"),
        patch("nova.server.home_brain.shutil.which", return_value="/usr/bin/systemd-inhibit"),
        patch("nova.server.home_brain.subprocess.Popen", return_value=fake_proc),
    ):
        ok = h.enable()
    assert ok is True
    assert h.status.enabled is True
    assert h.status.backend == "linux"
    assert "12345" in h.status.detail


def test_enable_linux_missing_inhibitor() -> None:
    h = HomeBrainMode()
    with (
        patch("nova.server.home_brain.sys.platform", "linux"),
        patch("nova.server.home_brain.shutil.which", return_value=None),
    ):
        ok = h.enable()
    assert ok is False
    assert h.status.enabled is False


def test_enable_macos() -> None:
    h = HomeBrainMode()
    with (
        patch("nova.server.home_brain.sys.platform", "darwin"),
        patch("nova.server.home_brain.shutil.which", return_value="/usr/bin/pmset"),
        patch(
            "nova.server.home_brain.subprocess.run",
            return_value=MagicMock(returncode=0),
        ),
    ):
        ok = h.enable()
    assert ok is True
    assert h.status.backend == "macos"


def test_enable_unsupported_platform() -> None:
    h = HomeBrainMode()
    with patch("nova.server.home_brain.sys.platform", "haiku"):
        ok = h.enable()
    assert ok is False
    assert h.status.backend == "unsupported"


def test_disable_when_not_enabled_is_noop() -> None:
    h = HomeBrainMode()
    assert h.disable() is True


def test_disable_terminates_inhibitor() -> None:
    h = HomeBrainMode()
    fake_proc = MagicMock(pid=42)
    with (
        patch("nova.server.home_brain.sys.platform", "linux"),
        patch("nova.server.home_brain.shutil.which", return_value="/usr/bin/systemd-inhibit"),
        patch("nova.server.home_brain.subprocess.Popen", return_value=fake_proc),
    ):
        h.enable()
    with patch("nova.server.home_brain.sys.platform", "linux"):
        h.disable()
    fake_proc.terminate.assert_called_once()
    assert h.status.enabled is False


def test_enable_idempotent() -> None:
    h = HomeBrainMode()
    fake_proc = MagicMock(pid=1)
    with (
        patch("nova.server.home_brain.sys.platform", "linux"),
        patch("nova.server.home_brain.shutil.which", return_value="/x"),
        patch("nova.server.home_brain.subprocess.Popen", return_value=fake_proc) as popen,
    ):
        h.enable()
        h.enable()
    assert popen.call_count == 1
