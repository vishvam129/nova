"""``open_app`` built-in tool — cross-platform app/URL launcher."""

from __future__ import annotations

import platform
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpenResult:
    ok: bool
    command: list[str]
    error: str | None = None


def _launcher(system: str) -> list[str]:
    if system == "Darwin":
        return ["open"]
    if system == "Windows":
        return ["cmd", "/c", "start", ""]
    # Linux / BSD / everything else.
    return ["xdg-open"]


def open_app(
    target: str,
    system: str | None = None,
    runner: Callable[[list[str]], object] | None = None,
) -> OpenResult:
    """Launch an application or open a URL/path in the default handler.

    ``target`` may be an app name (``"firefox"``), a URL, or a file path.
    ``system`` overrides the host OS for testing. ``runner`` is the
    callable used to spawn the command — defaults to ``subprocess.Popen``.
    """
    system = system or platform.system()
    cmd = _launcher(system) + [target]
    if runner is None:
        head = cmd[0]
        if shutil.which(head) is None and head not in {"cmd", "start"}:
            return OpenResult(ok=False, command=cmd, error=f"{head!r} not found on PATH")
        try:
            subprocess.Popen(  # noqa: S603 — caller has run through approval
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as e:
            return OpenResult(ok=False, command=cmd, error=str(e))
        return OpenResult(ok=True, command=cmd)
    try:
        runner(cmd)
    except OSError as e:
        return OpenResult(ok=False, command=cmd, error=str(e))
    return OpenResult(ok=True, command=cmd)


__all__ = ["OpenResult", "open_app"]
