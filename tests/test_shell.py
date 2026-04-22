"""Tests for run_shell and classify_command."""

from __future__ import annotations

import pytest

from nova.tools.builtin.shell import (
    DESTRUCTIVE_VERBS,
    RunShellResult,
    classify_command,
    run_shell,
)


def test_classify_safe_command() -> None:
    assert classify_command("ls -la") == "safe"
    assert classify_command("echo hi") == "safe"


def test_classify_destructive_rm() -> None:
    assert classify_command("rm -rf /tmp/x") == "destructive"


def test_classify_destructive_standalone_dd() -> None:
    assert classify_command("dd if=/dev/zero of=/dev/sda") == "destructive"


def test_classify_sudo() -> None:
    assert classify_command("sudo apt update") == "sudo"


def test_classify_network() -> None:
    assert classify_command("curl https://example.com") == "network"
    assert classify_command("ssh user@host") == "network"


def test_destructive_verbs_constant() -> None:
    assert "rm" in DESTRUCTIVE_VERBS
    assert "shutdown" in DESTRUCTIVE_VERBS


def test_run_shell_echo_succeeds() -> None:
    r = run_shell("echo hello-nova")
    assert isinstance(r, RunShellResult)
    assert r.exit_code == 0
    assert "hello-nova" in r.stdout


def test_run_shell_nonzero_exit_captured() -> None:
    r = run_shell("false")
    assert r.exit_code != 0


def test_run_shell_timeout_sets_flag() -> None:
    r = run_shell("sleep 5", timeout=0.2)
    assert r.timed_out is True
    assert r.exit_code == 124


def test_run_shell_allowlist_blocks() -> None:
    with pytest.raises(PermissionError):
        run_shell("rm -rf /tmp/x", allowlist=frozenset({"ls", "echo"}))


def test_run_shell_allowlist_allows() -> None:
    r = run_shell("echo ok", allowlist=frozenset({"echo"}))
    assert "ok" in r.stdout


def test_classify_unparseable_is_destructive() -> None:
    # Unclosed quote breaks shlex.split.
    assert classify_command("echo 'hi") == "destructive"
