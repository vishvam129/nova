"""Cross-platform system control: volume, brightness, lock, sleep, wake.

Each platform has a different toolchain; this module dispatches to the
appropriate CLI per ``sys.platform``.  Methods are no-ops + return False
when the underlying tool is missing — never raise on a best-effort call.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class SystemControl:
    """Best-effort cross-platform system actions."""

    platform: str = ""

    def __post_init__(self) -> None:
        if not self.platform:
            self.platform = sys.platform

    # ---------------- volume ----------------

    def set_volume(self, percent: int) -> bool:
        """Set master output volume to *percent* (0-100)."""
        pct = max(0, min(100, percent))
        if self.platform.startswith("linux"):
            if shutil.which("pactl"):
                return _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{pct}%"])
            if shutil.which("amixer"):
                return _run(["amixer", "-q", "sset", "Master", f"{pct}%"])
        if self.platform == "darwin":
            return _run(["osascript", "-e", f"set volume output volume {pct}"])
        if self.platform == "win32":
            return _run(
                [
                    "powershell",
                    "-Command",
                    "(New-Object -ComObject WScript.Shell).SendKeys([char]173)",
                ]
            )
        return False

    # ---------------- brightness ----------------

    def set_brightness(self, percent: int) -> bool:
        pct = max(1, min(100, percent))
        if self.platform.startswith("linux"):
            if shutil.which("brightnessctl"):
                return _run(["brightnessctl", "set", f"{pct}%"])
            if shutil.which("xbacklight"):
                return _run(["xbacklight", "-set", str(pct)])
        if self.platform == "darwin" and shutil.which("brightness"):
            return _run(["brightness", str(pct / 100)])
        if self.platform == "win32":
            ps = (
                "(Get-WmiObject -Namespace root/WMI -Class "
                f"WmiMonitorBrightnessMethods).WmiSetBrightness(1,{pct})"
            )
            return _run(["powershell", "-Command", ps])
        return False

    # ---------------- lock ----------------

    def lock(self) -> bool:
        if self.platform.startswith("linux"):
            for cmd in (
                ["loginctl", "lock-session"],
                ["xdg-screensaver", "lock"],
                ["gnome-screensaver-command", "-l"],
            ):
                if shutil.which(cmd[0]) and _run(cmd):
                    return True
            return False
        if self.platform == "darwin":
            script = (
                'tell application "System Events" to keystroke "q" '
                "using {control down, command down}"
            )
            return _run(["osascript", "-e", script])
        if self.platform == "win32":
            return _run(["rundll32.exe", "user32.dll,LockWorkStation"])
        return False

    # ---------------- sleep ----------------

    def sleep(self) -> bool:
        if self.platform.startswith("linux"):
            return _run(["systemctl", "suspend"])
        if self.platform == "darwin":
            return _run(["pmset", "sleepnow"])
        if self.platform == "win32":
            return _run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        return False

    # ---------------- wake (best-effort) ----------------

    def wake(self) -> bool:
        """Move the mouse / send a no-op keypress to wake the display."""
        if self.platform.startswith("linux") and shutil.which("xdotool"):
            return _run(["xdotool", "mousemove_relative", "1", "0"])
        if self.platform == "darwin":
            return _run(["caffeinate", "-u", "-t", "1"])
        if self.platform == "win32":
            return _run(
                [
                    "powershell",
                    "-Command",
                    "(New-Object -ComObject WScript.Shell).SendKeys(' ')",
                ]
            )
        return False


def _run(cmd: list[str]) -> bool:
    if not shutil.which(cmd[0]):
        return False
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=5)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


__all__ = ["SystemControl"]
