"""Persistent shell session MCP via tmux.

Long-running commands (build, training, server) shouldn't block the
brain.  This wraps tmux to provide named sessions the agent can attach
to, send keystrokes into, and read pane output from.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


class TmuxUnavailable(RuntimeError):
    pass


def _tmux(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    if not shutil.which("tmux"):
        raise TmuxUnavailable("tmux not on PATH")
    return subprocess.run(["tmux", *args], capture_output=True, check=check)


@dataclass
class PersistentShell:
    """One named tmux session the agent can drive."""

    name: str

    def exists(self) -> bool:
        try:
            r = _tmux("has-session", "-t", self.name, check=False)
        except TmuxUnavailable:
            return False
        return r.returncode == 0

    def start(self, *, command: str | None = None) -> bool:
        if self.exists():
            return True
        args = ["new-session", "-d", "-s", self.name]
        if command:
            args.append(command)
        try:
            r = _tmux(*args, check=False)
        except TmuxUnavailable:
            return False
        return r.returncode == 0

    def send(self, text: str, *, enter: bool = True) -> bool:
        keys = [text, "Enter"] if enter else [text]
        try:
            _tmux("send-keys", "-t", self.name, *keys)
        except (TmuxUnavailable, subprocess.CalledProcessError):
            return False
        return True

    def capture(self, *, lines: int = 100) -> str:
        try:
            r = _tmux("capture-pane", "-t", self.name, "-p", "-S", f"-{lines}", check=False)
        except TmuxUnavailable:
            return ""
        return r.stdout.decode(errors="replace") if r.returncode == 0 else ""

    def kill(self) -> bool:
        if not self.exists():
            return False
        try:
            _tmux("kill-session", "-t", self.name)
        except (TmuxUnavailable, subprocess.CalledProcessError):
            return False
        return True


@dataclass
class PersistentShellHandler:
    """MCP-facing dispatcher.

    tools:
        shell.start    { name, command? }
        shell.send     { name, text }
        shell.capture  { name, lines? }
        shell.kill     { name }
        shell.exists   { name }
    """

    def call(self, tool: str, **kwargs: object) -> object:
        name = str(kwargs["name"])
        sess = PersistentShell(name=name)
        if tool == "shell.start":
            cmd = kwargs.get("command")
            return {"ok": sess.start(command=str(cmd) if cmd else None)}
        if tool == "shell.send":
            return {"ok": sess.send(str(kwargs["text"]))}
        if tool == "shell.capture":
            return {"output": sess.capture(lines=int(kwargs.get("lines", 100)))}  # type: ignore[arg-type]
        if tool == "shell.kill":
            return {"ok": sess.kill()}
        if tool == "shell.exists":
            return {"exists": sess.exists()}
        raise ValueError(f"unknown shell.* tool: {tool!r}")


__all__ = ["PersistentShell", "PersistentShellHandler", "TmuxUnavailable"]
