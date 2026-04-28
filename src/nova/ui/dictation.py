"""Dictation mode: hold hotkey, release pastes transcript at cursor.

The flow:
    1. Hotkey press → start recording
    2. Audio chunks stream into a buffered transcriber
    3. Hotkey release → finalize transcript
    4. Insert the text at the cursor (clipboard paste fallback)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol


class DictationTranscriber(Protocol):
    def transcribe(self, pcm: bytes) -> str: ...


class TextInjector(Protocol):
    """Pastes / types text wherever the cursor is."""

    def inject(self, text: str) -> bool: ...


@dataclass
class ClipboardInjector:
    """Inject text by writing to the clipboard then sending Ctrl+V via xdotool."""

    paste_command: list[str] = field(default_factory=lambda: ["xdotool", "key", "ctrl+v"])

    def inject(self, text: str) -> bool:
        from nova.tools.builtin.clipboard import clipboard_write

        if not clipboard_write(text):
            return False
        try:
            import shutil
            import subprocess

            if shutil.which(self.paste_command[0]):
                subprocess.run(self.paste_command, capture_output=True, timeout=2)
        except (OSError, subprocess.SubprocessError):
            return False
        return True


@dataclass
class DictationSession:
    """Tracks press/release cycle and emits the final text via the injector."""

    transcriber: DictationTranscriber
    injector: TextInjector
    on_text: Callable[[str], None] | None = None

    _buffer: bytearray = field(default_factory=bytearray, init=False)
    _active: bool = field(default=False, init=False)
    _last_text: str = field(default="", init=False)

    @property
    def active(self) -> bool:
        return self._active

    def start(self) -> None:
        self._buffer.clear()
        self._active = True
        self._last_text = ""

    def feed(self, pcm: bytes) -> None:
        if not self._active:
            return
        self._buffer.extend(pcm)

    def stop(self) -> str:
        if not self._active:
            return ""
        self._active = False
        text = self.transcriber.transcribe(bytes(self._buffer)).strip()
        self._last_text = text
        if text:
            self.injector.inject(text)
            if self.on_text:
                self.on_text(text)
        self._buffer.clear()
        return text

    @property
    def last_text(self) -> str:
        return self._last_text


__all__ = [
    "ClipboardInjector",
    "DictationSession",
    "DictationTranscriber",
    "TextInjector",
]
