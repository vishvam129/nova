"""Tests for nova.integrations.persistent_shell."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nova.integrations.persistent_shell import (
    PersistentShell,
    PersistentShellHandler,
)


def _ok_run(returncode: int = 0, stdout: bytes = b"") -> MagicMock:
    return MagicMock(returncode=returncode, stdout=stdout)


def test_exists_returns_true_when_tmux_says_so() -> None:
    s = PersistentShell(name="nova")
    with (
        patch("nova.integrations.persistent_shell.shutil.which", return_value="/usr/bin/tmux"),
        patch("nova.integrations.persistent_shell.subprocess.run", return_value=_ok_run(0)),
    ):
        assert s.exists() is True


def test_exists_returns_false_when_no_tmux() -> None:
    s = PersistentShell(name="nova")
    with patch("nova.integrations.persistent_shell.shutil.which", return_value=None):
        assert s.exists() is False


def test_start_creates_session() -> None:
    s = PersistentShell(name="nova")
    with (
        patch("nova.integrations.persistent_shell.shutil.which", return_value="/usr/bin/tmux"),
        patch.object(PersistentShell, "exists", return_value=False),
        patch("nova.integrations.persistent_shell.subprocess.run", return_value=_ok_run(0)) as run,
    ):
        assert s.start(command="bash") is True
    cmd = run.call_args[0][0]
    assert "new-session" in cmd
    assert "bash" in cmd


def test_start_idempotent_when_session_exists() -> None:
    s = PersistentShell(name="nova")
    with patch.object(PersistentShell, "exists", return_value=True):
        assert s.start() is True


def test_send_dispatches_keys() -> None:
    s = PersistentShell(name="nova")
    with (
        patch("nova.integrations.persistent_shell.shutil.which", return_value="/usr/bin/tmux"),
        patch("nova.integrations.persistent_shell.subprocess.run", return_value=_ok_run(0)) as run,
    ):
        assert s.send("ls -la") is True
    cmd = run.call_args[0][0]
    assert "send-keys" in cmd
    assert "Enter" in cmd


def test_capture_returns_pane_output() -> None:
    s = PersistentShell(name="nova")
    with (
        patch("nova.integrations.persistent_shell.shutil.which", return_value="/usr/bin/tmux"),
        patch(
            "nova.integrations.persistent_shell.subprocess.run",
            return_value=_ok_run(0, b"hello world"),
        ),
    ):
        assert s.capture() == "hello world"


def test_kill_when_session_missing_returns_false() -> None:
    s = PersistentShell(name="nova")
    with patch.object(PersistentShell, "exists", return_value=False):
        assert s.kill() is False


def test_handler_dispatches_commands() -> None:
    h = PersistentShellHandler()
    with (
        patch.object(PersistentShell, "exists", return_value=False),
        patch("nova.integrations.persistent_shell.shutil.which", return_value="/usr/bin/tmux"),
        patch("nova.integrations.persistent_shell.subprocess.run", return_value=_ok_run(0)),
    ):
        out = h.call("shell.start", name="nova", command="bash")
    assert out == {"ok": True}


def test_handler_unknown_tool() -> None:
    h = PersistentShellHandler()
    with pytest.raises(ValueError):
        h.call("shell.bogus", name="x")
