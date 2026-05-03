"""Git MCP: clone / commit / push / PR with safe-branch policy.

Safe-branch policy: agent commits are only ever made on a branch matching
the configured prefix (default ``nova/``).  Direct commits to ``main``,
``master``, ``develop``, or ``release/*`` are blocked.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

_PROTECTED_BRANCHES = ("main", "master", "develop")
_PROTECTED_PREFIXES = ("release/", "hotfix/")


class UnsafeBranch(RuntimeError):
    def __init__(self, branch: str) -> None:
        super().__init__(f"refuse to commit on protected branch {branch!r}")
        self.branch = branch


@dataclass
class SafeBranchPolicy:
    """Decides whether a branch is OK to commit on."""

    allowed_prefix: str = "nova/"
    protected: tuple[str, ...] = field(default_factory=lambda: _PROTECTED_BRANCHES)
    protected_prefixes: tuple[str, ...] = field(default_factory=lambda: _PROTECTED_PREFIXES)

    def is_safe(self, branch: str) -> bool:
        if branch in self.protected:
            return False
        if any(branch.startswith(p) for p in self.protected_prefixes):
            return False
        return branch.startswith(self.allowed_prefix)

    def assert_safe(self, branch: str) -> None:
        if not self.is_safe(branch):
            raise UnsafeBranch(branch)


@dataclass
class GitOps:
    """Thin subprocess wrapper for the supported operations."""

    repo: Path
    policy: SafeBranchPolicy = field(default_factory=SafeBranchPolicy)
    git_bin: str = "git"

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [self.git_bin, "-C", str(self.repo), *args],
            capture_output=True,
            check=check,
        )

    def current_branch(self) -> str:
        r = self._run("rev-parse", "--abbrev-ref", "HEAD")
        return r.stdout.decode().strip()

    def clone(self, url: str, *, depth: int | None = None) -> bool:
        cmd = [self.git_bin, "clone"]
        if depth:
            cmd += ["--depth", str(depth)]
        cmd += [url, str(self.repo)]
        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except (OSError, subprocess.SubprocessError):
            return False
        return True

    def checkout_safe_branch(self, name: str) -> str:
        if not name.startswith(self.policy.allowed_prefix):
            name = f"{self.policy.allowed_prefix}{name}"
        self.policy.assert_safe(name)
        self._run("checkout", "-B", name)
        return name

    def commit(self, message: str, *, paths: Iterable[str] | None = None) -> str:
        branch = self.current_branch()
        self.policy.assert_safe(branch)
        if paths:
            self._run("add", *paths)
        else:
            self._run("add", "-A")
        self._run("commit", "-m", message)
        return self._run("rev-parse", "HEAD").stdout.decode().strip()

    def push(self, *, set_upstream: bool = True) -> bool:
        branch = self.current_branch()
        self.policy.assert_safe(branch)
        args = ["push"]
        if set_upstream:
            args += ["-u", "origin", branch]
        try:
            self._run(*args)
        except subprocess.CalledProcessError:
            return False
        return True

    def open_pr(self, *, title: str, body: str = "", base: str = "main") -> str | None:
        branch = self.current_branch()
        self.policy.assert_safe(branch)
        cmd = [
            "gh",
            "pr",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--base",
            base,
            "--head",
            branch,
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, cwd=self.repo, check=True)
        except (OSError, subprocess.SubprocessError):
            return None
        match = re.search(r"https?://\S+/pull/\d+", r.stdout.decode())
        return match.group(0) if match else None


__all__ = ["GitOps", "SafeBranchPolicy", "UnsafeBranch"]
