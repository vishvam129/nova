"""``run_shell`` built-in tool.

Executes a shell command with a timeout. Destructive verbs (rm, dd,
mkfs, etc.) are classified as such so the caller can push the action
through an approval policy — this module does not prompt the user
itself.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from typing import Literal

DESTRUCTIVE_VERBS: frozenset[str] = frozenset(
    {
        "rm",
        "dd",
        "mkfs",
        "mkfs.ext4",
        "mkfs.xfs",
        "fdisk",
        "parted",
        "shred",
        "wipefs",
        "format",
        "kill",
        "killall",
        "pkill",
        "shutdown",
        "reboot",
        "halt",
    }
)

DANGEROUS_FLAGS: frozenset[str] = frozenset({"-rf", "--no-preserve-root", "-f"})

Classification = Literal["safe", "destructive", "network", "sudo"]


@dataclass(frozen=True, slots=True)
class RunShellResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False


def _first_nonflag(tokens: list[str]) -> str:
    for t in tokens:
        if not t.startswith("-") and "=" not in t:
            return t
    return tokens[0] if tokens else ""


def classify_command(command: str) -> Classification:
    """Classify the command for approval routing."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return "destructive"  # unparseable — be conservative
    if not tokens:
        return "safe"
    head = tokens[0]
    if head == "sudo":
        return "sudo"
    base = _first_nonflag(tokens).split("/")[-1]
    if base in DESTRUCTIVE_VERBS:
        return "destructive"
    if base == "rm" or ("rm" in tokens and any(f in DANGEROUS_FLAGS for f in tokens)):
        return "destructive"
    if base in {"curl", "wget", "ssh", "scp", "rsync"}:
        return "network"
    return "safe"


def run_shell(
    command: str,
    timeout: float = 30.0,
    cwd: str | None = None,
    allowlist: frozenset[str] | None = None,
) -> RunShellResult:
    """Execute ``command`` and return stdout/stderr/exit code.

    If ``allowlist`` is provided, the head command must be a member or
    the call raises ``PermissionError`` — this mirrors the ``run_shell``
    policy layer in the agent.
    """
    if allowlist is not None:
        tokens = shlex.split(command)
        head = tokens[0].split("/")[-1] if tokens else ""
        if head not in allowlist:
            raise PermissionError(f"command {head!r} not on allowlist")
    try:
        proc = subprocess.run(
            command,
            shell=True,  # noqa: S602 — intentional; caller has run through approval
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            check=False,
        )
        return RunShellResult(stdout=proc.stdout, stderr=proc.stderr, exit_code=proc.returncode)
    except subprocess.TimeoutExpired as e:
        partial = e.stdout
        if isinstance(partial, bytes):
            partial_str = partial.decode(errors="replace")
        else:
            partial_str = partial or ""
        return RunShellResult(
            stdout=partial_str,
            stderr=f"timed out after {timeout}s",
            exit_code=124,
            timed_out=True,
        )


__all__ = [
    "DESTRUCTIVE_VERBS",
    "RunShellResult",
    "classify_command",
    "run_shell",
]
