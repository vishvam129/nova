"""Tests for nova.tools.sandbox."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from nova.tools.sandbox import (
    SandboxConfig,
    SandboxUnavailable,
    detect_backend,
    wrap_command,
)


def test_detect_backend_none() -> None:
    with patch("nova.tools.sandbox.shutil.which", return_value=None):
        assert detect_backend() is None


def test_detect_backend_bwrap() -> None:
    with patch(
        "nova.tools.sandbox.shutil.which",
        side_effect=lambda b: "/usr/bin/bwrap" if b == "bwrap" else None,
    ):
        assert detect_backend() == "bwrap"


def test_detect_backend_firejail() -> None:
    def which(name: str) -> str | None:
        return "/usr/bin/firejail" if name == "firejail" else None

    with patch("nova.tools.sandbox.shutil.which", side_effect=which):
        assert detect_backend() == "firejail"


def test_wrap_no_backend_raises() -> None:
    with (
        patch("nova.tools.sandbox.detect_backend", return_value=None),
        pytest.raises(SandboxUnavailable),
    ):
        wrap_command(["echo", "hi"], SandboxConfig(require_sandbox=True))


def test_wrap_no_backend_passthrough() -> None:
    with patch("nova.tools.sandbox.detect_backend", return_value=None):
        out = wrap_command(["echo", "hi"], SandboxConfig(require_sandbox=False))
    assert out == ["echo", "hi"]


def test_wrap_bwrap() -> None:
    with patch("nova.tools.sandbox.detect_backend", return_value="bwrap"):
        out = wrap_command(["echo", "hi"])
    assert out[0] == "bwrap"
    assert "--unshare-all" in out
    assert out[-2:] == ["echo", "hi"]


def test_wrap_bwrap_with_network() -> None:
    cfg = SandboxConfig(allow_network=True)
    with patch("nova.tools.sandbox.detect_backend", return_value="bwrap"):
        out = wrap_command(["curl", "x"], cfg)
    assert "--share-net" in out


def test_wrap_bwrap_with_allow_paths(tmp_path: Path) -> None:
    cfg = SandboxConfig(allow_paths=[tmp_path])
    with patch("nova.tools.sandbox.detect_backend", return_value="bwrap"):
        out = wrap_command(["ls"], cfg)
    assert str(tmp_path) in out


def test_wrap_firejail() -> None:
    with patch("nova.tools.sandbox.detect_backend", return_value="firejail"):
        out = wrap_command(["echo", "hi"])
    assert out[0] == "firejail"
    assert "--net=none" in out
    assert "--" in out
    assert out[-2:] == ["echo", "hi"]


def test_wrap_firejail_network_removes_net_none() -> None:
    with patch("nova.tools.sandbox.detect_backend", return_value="firejail"):
        out = wrap_command(["curl", "x"], SandboxConfig(allow_network=True))
    assert "--net=none" not in out
