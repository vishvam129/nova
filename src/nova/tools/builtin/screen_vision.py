"""Stream screen frames to a vision LLM for grounded Q&A.

Captures the screen at a configurable interval, base64-encodes the PNG,
and asks the bound vision model the supplied question.  The vision client
is injected so we can swap Claude / Gemini / mock implementations.
"""

from __future__ import annotations

import base64
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from nova.tools.builtin.screenshot import Region, capture


class VisionClient(Protocol):
    """Anything that can answer a question about a screenshot."""

    def ask(self, question: str, image_b64: str, mime: str = "image/png") -> str: ...


@dataclass
class ScreenVision:
    """Single-shot or streaming screen → vision-LLM bridge."""

    client: VisionClient
    interval_s: float = 1.0
    region: Region | None = None
    _frames: list[str] = field(default_factory=list, init=False)

    def ask_about_screen(self, question: str, *, tmp_path: Path | None = None) -> str:
        """Capture once and ask the vision model."""
        path = tmp_path or _temp_png()
        try:
            capture(path, self.region)
            b64 = base64.b64encode(path.read_bytes()).decode()
            self._frames.append(b64)
            return self.client.ask(question, b64)
        finally:
            if tmp_path is None:
                path.unlink(missing_ok=True)

    def stream(self, question: str, frames: int = 5) -> Iterator[str]:
        """Yield the model's answer for *frames* successive captures."""
        for _ in range(frames):
            yield self.ask_about_screen(question)
            time.sleep(self.interval_s)

    @property
    def frame_count(self) -> int:
        return len(self._frames)


def _temp_png() -> Path:
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        return Path(f.name)


__all__ = ["ScreenVision", "VisionClient"]
