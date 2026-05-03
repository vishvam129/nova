"""Tests for nova.integrations.git_ops."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nova.integrations.git_ops import GitOps, SafeBranchPolicy, UnsafeBranch


def test_policy_blocks_main() -> None:
    p = SafeBranchPolicy()
    assert p.is_safe("main") is False
    assert p.is_safe("master") is False
    assert p.is_safe("develop") is False


def test_policy_blocks_release_prefix() -> None:
    p = SafeBranchPolicy()
    assert p.is_safe("release/2026.04") is False
    assert p.is_safe("hotfix/critical") is False


def test_policy_allows_nova_prefix() -> None:
    p = SafeBranchPolicy()
    assert p.is_safe("nova/feature-x") is True


def test_policy_blocks_other_branches() -> None:
    p = SafeBranchPolicy()
    assert p.is_safe("user/something") is False


def test_assert_safe_raises() -> None:
    p = SafeBranchPolicy()
    with pytest.raises(UnsafeBranch):
        p.assert_safe("main")


def test_checkout_auto_prefixes(tmp_path: Path) -> None:
    g = GitOps(repo=tmp_path)
    with patch.object(GitOps, "_run", return_value=MagicMock(stdout=b"")):
        out = g.checkout_safe_branch("my-feature")
    assert out == "nova/my-feature"


def test_checkout_keeps_existing_prefix(tmp_path: Path) -> None:
    g = GitOps(repo=tmp_path)
    with patch.object(GitOps, "_run", return_value=MagicMock(stdout=b"")):
        out = g.checkout_safe_branch("nova/x")
    assert out == "nova/x"


def test_commit_blocked_on_main(tmp_path: Path) -> None:
    g = GitOps(repo=tmp_path)
    with (
        patch.object(GitOps, "current_branch", return_value="main"),
        pytest.raises(UnsafeBranch),
    ):
        g.commit("hi")


def test_commit_returns_hash(tmp_path: Path) -> None:
    g = GitOps(repo=tmp_path)
    runs = {"rev-parse": MagicMock(stdout=b"abc1234\n"), "default": MagicMock(stdout=b"")}

    def run(*args, check: bool = True):
        return runs["rev-parse"] if "rev-parse" in args else runs["default"]

    with (
        patch.object(GitOps, "current_branch", return_value="nova/feat"),
        patch.object(GitOps, "_run", side_effect=run),
    ):
        sha = g.commit("msg")
    assert sha == "abc1234"


def test_push_blocked_on_main(tmp_path: Path) -> None:
    g = GitOps(repo=tmp_path)
    with (
        patch.object(GitOps, "current_branch", return_value="main"),
        pytest.raises(UnsafeBranch),
    ):
        g.push()


def test_clone_handles_failure(tmp_path: Path) -> None:
    g = GitOps(repo=tmp_path / "out")
    with patch("nova.integrations.git_ops.subprocess.run", side_effect=OSError):
        assert g.clone("git@x:y.git") is False
