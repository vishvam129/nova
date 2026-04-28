"""Clipboard tools: read/write + history ring buffer.

Cross-platform via xclip/wl-paste/pbpaste/clip; falls back to a pure
in-process clipboard so unit tests work in headless CI.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections import deque
from dataclasses import dataclass, field

_INPROC: list[str] = [""]


def _capture(cmd: list[str]) -> str | None:
    if not shutil.which(cmd[0]):
        return None
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode(errors="replace")


def _read_native() -> str | None:
    if sys.platform.startswith("linux"):
        out = _capture(["wl-paste", "-n"])
        if out is not None:
            return out
        return _capture(["xclip", "-selection", "clipboard", "-o"])
    if sys.platform == "darwin":
        return _capture(["pbpaste"])
    if sys.platform == "win32":
        out = _capture(["powershell", "-Command", "Get-Clipboard"])
        return out.rstrip("\r\n") if out is not None else None
    return None


def _write_native(text: str) -> bool:
    if sys.platform.startswith("linux"):
        if shutil.which("wl-copy"):
            return _pipe(["wl-copy"], text)
        if shutil.which("xclip"):
            return _pipe(["xclip", "-selection", "clipboard"], text)
    if sys.platform == "darwin" and shutil.which("pbcopy"):
        return _pipe(["pbcopy"], text)
    if sys.platform == "win32" and shutil.which("clip"):
        return _pipe(["clip"], text)
    return False


def _pipe(cmd: list[str], text: str) -> bool:
    try:
        r = subprocess.run(cmd, input=text.encode(), capture_output=True, timeout=2)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def clipboard_read() -> str:
    """Return the current clipboard text (empty string if unavailable)."""
    text = _read_native()
    if text is None:
        return _INPROC[0]
    return text


def clipboard_write(text: str) -> bool:
    """Set the clipboard text. Falls back to an in-process value."""
    if _write_native(text):
        _INPROC[0] = text
        return True
    _INPROC[0] = text
    return False


@dataclass
class ClipboardHistory:
    """Ring buffer of recent clipboard contents (newest at end)."""

    capacity: int = 50
    _items: deque[str] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        self._items = deque(maxlen=self.capacity)

    def push(self, text: str) -> None:
        if not text:
            return
        if self._items and self._items[-1] == text:
            return
        self._items.append(text)

    def items(self) -> list[str]:
        return list(self._items)

    def latest(self) -> str:
        return self._items[-1] if self._items else ""

    def __len__(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()


__all__ = ["ClipboardHistory", "clipboard_read", "clipboard_write"]
