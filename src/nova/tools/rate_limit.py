"""Per-tool rate limiting to prevent runaway agents.

Token-bucket-ish: each tool gets a sliding 60-second window of timestamps;
if the window has more than ``per_minute`` entries, ``check()`` returns
False.  ``acquire()`` raises ``RateLimited`` instead.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


class RateLimited(RuntimeError):
    """Raised by ``acquire()`` when the tool's per-minute cap is reached."""

    def __init__(self, tool: str, per_minute: int) -> None:
        super().__init__(f"tool {tool!r} rate-limited at {per_minute}/min")
        self.tool = tool
        self.per_minute = per_minute


@dataclass
class RateLimiter:
    """Per-tool sliding-window rate limiter."""

    per_minute: int = 30
    window_s: float = 60.0
    overrides: dict[str, int] = field(default_factory=dict)
    _windows: dict[str, deque[float]] = field(default_factory=dict, init=False)

    def _limit_for(self, tool: str) -> int:
        return self.overrides.get(tool, self.per_minute)

    def _prune(self, tool: str, now: float) -> deque[float]:
        window = self._windows.setdefault(tool, deque())
        cutoff = now - self.window_s
        while window and window[0] < cutoff:
            window.popleft()
        return window

    def check(self, tool: str) -> bool:
        now = time.monotonic()
        window = self._prune(tool, now)
        return len(window) < self._limit_for(tool)

    def acquire(self, tool: str) -> None:
        now = time.monotonic()
        window = self._prune(tool, now)
        if len(window) >= self._limit_for(tool):
            raise RateLimited(tool, self._limit_for(tool))
        window.append(now)

    def usage(self, tool: str) -> int:
        return len(self._prune(tool, time.monotonic()))

    def reset(self, tool: str | None = None) -> None:
        if tool is None:
            self._windows.clear()
        else:
            self._windows.pop(tool, None)


__all__ = ["RateLimited", "RateLimiter"]
