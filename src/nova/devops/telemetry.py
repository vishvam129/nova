"""Opt-in telemetry: locally aggregated, with first-run consent wizard.

Default: collection is OFF.  ``ConsentWizard.prompt`` returns the user's
choice the first time the app runs.  Telemetry buffers events into
``TelemetryBuffer`` (no PII, no per-user identifiers — only counts and
durations) and ``flush()`` writes a daily aggregate file.

Aggregate-only writes mean the on-disk file never contains an event
sequence — it's a Counter of (event_name, day) → count + sum/min/max
of durations.  No upload by default.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

_DEFAULT_CONSENT = Path("~/.config/nova/telemetry_consent.json").expanduser()
_DEFAULT_AGGREGATE = Path("~/.local/share/nova/telemetry.json").expanduser()


@dataclass
class ConsentWizard:
    """First-run y/n prompt; persists the answer."""

    state_path: Path = field(default_factory=lambda: _DEFAULT_CONSENT)

    def has_decided(self) -> bool:
        return self.state_path.exists()

    def consent(self) -> bool:
        if not self.state_path.exists():
            return False
        try:
            data = json.loads(self.state_path.read_text())
            return bool(data.get("opt_in", False))
        except (OSError, json.JSONDecodeError):
            return False

    def record_decision(self, *, opt_in: bool) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps({"opt_in": opt_in, "at": datetime.now().isoformat()}))

    def prompt(self, prompt_fn: object | None = None) -> bool:
        """Run the wizard.  ``prompt_fn`` is for tests; real run uses input()."""
        if self.has_decided():
            return self.consent()
        if callable(prompt_fn):
            answer = bool(prompt_fn())
        else:
            answer = input(  # noqa: S322 — interactive prompt
                "Send anonymous local telemetry to Nova maintainers? [y/N]: "
            ).strip().lower() in {"y", "yes"}
        self.record_decision(opt_in=answer)
        return answer


@dataclass
class _Bucket:
    count: int = 0
    duration_sum_ms: float = 0.0
    duration_min_ms: float = 0.0
    duration_max_ms: float = 0.0

    def add(self, duration_ms: float) -> None:
        if self.count == 0:
            self.duration_min_ms = duration_ms
            self.duration_max_ms = duration_ms
        else:
            self.duration_min_ms = min(self.duration_min_ms, duration_ms)
            self.duration_max_ms = max(self.duration_max_ms, duration_ms)
        self.duration_sum_ms += duration_ms
        self.count += 1


@dataclass
class TelemetryBuffer:
    """In-memory aggregator.  Nothing is recorded unless ``enabled=True``."""

    enabled: bool = False
    aggregate_path: Path = field(default_factory=lambda: _DEFAULT_AGGREGATE)
    _buckets: dict[tuple[str, str], _Bucket] = field(default_factory=dict, init=False)

    def record(self, event: str, *, duration_ms: float = 0.0, when: date | None = None) -> None:
        if not self.enabled:
            return
        day = (when or date.today()).isoformat()
        key = (event, day)
        bucket = self._buckets.setdefault(key, _Bucket())
        bucket.add(duration_ms)

    def snapshot(self) -> list[dict[str, object]]:
        return [
            {
                "event": event,
                "day": day,
                "count": b.count,
                "duration_sum_ms": b.duration_sum_ms,
                "duration_min_ms": b.duration_min_ms,
                "duration_max_ms": b.duration_max_ms,
            }
            for (event, day), b in sorted(self._buckets.items())
        ]

    def flush(self) -> Path | None:
        if not self.enabled or not self._buckets:
            return None
        self.aggregate_path.parent.mkdir(parents=True, exist_ok=True)
        existing: list[dict[str, object]] = []
        if self.aggregate_path.exists():
            try:
                existing = json.loads(self.aggregate_path.read_text())
            except (OSError, json.JSONDecodeError):
                existing = []
        existing.extend(self.snapshot())
        self.aggregate_path.write_text(json.dumps(existing, indent=2))
        self._buckets.clear()
        return self.aggregate_path

    def __len__(self) -> int:
        return sum(b.count for b in self._buckets.values())


def event_total(snapshot: Iterable[dict[str, object]], event: str) -> int:
    return sum(int(s["count"]) for s in snapshot if s["event"] == event)


__all__ = ["ConsentWizard", "TelemetryBuffer", "event_total"]
