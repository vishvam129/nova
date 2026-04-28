"""Tool sandbox: wrap a shell command in bubblewrap or firejail.

Picks the first available sandbox binary on PATH. Falls back to
``allow_unsandboxed=True`` (caller's choice) or raises if no sandbox is
available and the caller demands one.

Sandbox profile (defaults):
    - read-only /usr, /etc
    - private /tmp
    - no network
    - no /home access except an explicit allow-list
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

_BWRAP_BASE = [
    "bwrap",
    "--ro-bind",
    "/usr",
    "/usr",
    "--ro-bind",
    "/etc",
    "/etc",
    "--ro-bind",
    "/lib",
    "/lib",
    "--ro-bind",
    "/lib64",
    "/lib64",
    "--ro-bind",
    "/bin",
    "/bin",
    "--proc",
    "/proc",
    "--dev",
    "/dev",
    "--tmpfs",
    "/tmp",
    "--unshare-all",
    "--die-with-parent",
]

_FIREJAIL_BASE = [
    "firejail",
    "--quiet",
    "--noprofile",
    "--private-tmp",
    "--net=none",
    "--seccomp",
]


class SandboxUnavailable(RuntimeError):
    """Raised when no sandbox tool is on PATH and one is required."""


@dataclass
class SandboxConfig:
    """Configuration for the sandbox wrapper."""

    allow_network: bool = False
    allow_paths: list[Path] = field(default_factory=list)
    require_sandbox: bool = True


def detect_backend() -> str | None:
    """Return 'bwrap', 'firejail', or None."""
    if shutil.which("bwrap"):
        return "bwrap"
    if shutil.which("firejail"):
        return "firejail"
    return None


def wrap_command(cmd: list[str], config: SandboxConfig | None = None) -> list[str]:
    """Wrap *cmd* in the available sandbox.

    Returns the wrapped argv. Raises ``SandboxUnavailable`` when no backend
    is found and ``config.require_sandbox`` is True.
    """
    cfg = config or SandboxConfig()
    backend = detect_backend()
    if backend is None:
        if cfg.require_sandbox:
            raise SandboxUnavailable(
                "no sandbox backend (bwrap/firejail) on PATH; "
                "install one or set require_sandbox=False"
            )
        return list(cmd)

    if backend == "bwrap":
        argv = list(_BWRAP_BASE)
        if cfg.allow_network:
            argv.append("--share-net")
        for p in cfg.allow_paths:
            argv += ["--bind", str(p), str(p)]
        argv += ["--", *cmd]
        return argv

    # firejail
    argv = list(_FIREJAIL_BASE)
    if cfg.allow_network:
        argv = [a for a in argv if a != "--net=none"]
    for p in cfg.allow_paths:
        argv += [f"--whitelist={p}"]
    argv.append("--")
    argv += cmd
    return argv


__all__ = ["SandboxConfig", "SandboxUnavailable", "detect_backend", "wrap_command"]
