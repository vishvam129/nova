"""Active-window tracker.

Reports which app + document/title is currently focused so the brain can
ground replies in what the user is looking at.

Three platform backends:
    Linux   — AT-SPI / xdotool fallback
    macOS   — NSAccessibility via osascript
    Windows — UIAutomation via PowerShell

Each backend is best-effort; failures yield ``ActiveWindow(...)`` with
empty fields so downstream code doesn't need to special-case absence.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActiveWindow:
    app: str = ""
    title: str = ""
    pid: int = 0

    def is_known(self) -> bool:
        return bool(self.app or self.title)

    def to_prompt(self) -> str:
        if not self.is_known():
            return ""
        if self.title:
            return f"User is in {self.app}: '{self.title}'."
        return f"User is in {self.app}."


def _run(cmd: list[str], timeout: float = 1.0) -> str:
    if not shutil.which(cmd[0]):
        return ""
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return ""
    if r.returncode != 0:
        return ""
    return r.stdout.decode(errors="replace").strip()


def _linux_active_window() -> ActiveWindow:
    title = _run(["xdotool", "getactivewindow", "getwindowname"])
    pid_str = _run(["xdotool", "getactivewindow", "getwindowpid"])
    app = _run(["xdotool", "getactivewindow", "getwindowclassname"])
    pid = int(pid_str) if pid_str.isdigit() else 0
    return ActiveWindow(app=app, title=title, pid=pid)


def _macos_active_window() -> ActiveWindow:
    script = (
        'tell application "System Events" '
        "to get {name, title} of (first process whose frontmost is true)"
    )
    out = _run(["osascript", "-e", script])
    if not out:
        return ActiveWindow()
    parts = [p.strip() for p in out.split(",", 1)]
    app = parts[0]
    title = parts[1] if len(parts) > 1 else ""
    return ActiveWindow(app=app, title=title)


def _windows_active_window() -> ActiveWindow:
    ps = (
        "Add-Type -AssemblyName UIAutomationClient; "
        "$el = [System.Windows.Automation.AutomationElement]::FocusedElement; "
        'if ($el) { Write-Output "$($el.Current.Name)"; '
        'Write-Output "$($el.Current.ProcessId)" }'
    )
    out = _run(["powershell", "-Command", ps])
    if not out:
        return ActiveWindow()
    lines = out.splitlines()
    title = lines[0] if lines else ""
    pid = 0
    if len(lines) > 1 and lines[1].strip().isdigit():
        pid = int(lines[1].strip())
    return ActiveWindow(app="", title=title, pid=pid)


def get_active_window() -> ActiveWindow:
    """Return the currently focused window/app for this platform."""
    if sys.platform.startswith("linux"):
        return _linux_active_window()
    if sys.platform == "darwin":
        return _macos_active_window()
    if sys.platform == "win32":
        return _windows_active_window()
    return ActiveWindow()


__all__ = ["ActiveWindow", "get_active_window"]
