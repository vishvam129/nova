"""Active-device detection.

Multiple devices may hear the same wake word.  Pick exactly one to
respond — the one whose audio has the highest combined score:

    score = wake_confidence * proximity_factor * recency_factor

Devices report ``WakeReport`` candidates within a short coalescing window.
After the window closes, the picker returns the winning device.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class WakeReport:
    """A single device's report of hearing the wake word."""

    device_id: str
    wake_confidence: float  # [0, 1]
    proximity_db: float = 0.0  # higher = louder = closer
    timestamp: float = 0.0


@dataclass
class ActiveDevicePicker:
    """Coalesces concurrent wake reports and picks one device."""

    coalesce_window_s: float = 0.4
    proximity_weight: float = 0.4
    confidence_weight: float = 0.6

    _reports: list[WakeReport] = field(default_factory=list, init=False)
    _window_start: float = field(default=0.0, init=False)

    def submit(self, report: WakeReport) -> None:
        now = report.timestamp or time.monotonic()
        if not self._reports:
            self._window_start = now
        self._reports.append(report)

    def is_window_open(self, now: float | None = None) -> bool:
        if not self._reports:
            return False
        elapsed = (now if now is not None else time.monotonic()) - self._window_start
        return elapsed < self.coalesce_window_s

    def pick(self, now: float | None = None) -> WakeReport | None:
        """Return the winning report and clear the window."""
        if not self._reports:
            return None
        if self.is_window_open(now):
            return None  # still collecting

        max_db = max((r.proximity_db for r in self._reports), default=0.0) or 1.0
        best: WakeReport | None = None
        best_score = -1.0
        for r in self._reports:
            score = self.confidence_weight * r.wake_confidence + self.proximity_weight * (
                r.proximity_db / max_db
            )
            if score > best_score:
                best = r
                best_score = score

        self._reports.clear()
        return best

    def reports(self) -> list[WakeReport]:
        return list(self._reports)


__all__ = ["ActiveDevicePicker", "WakeReport"]
