"""Opt-in local metrics dashboard.

Tracks latency p50/p95, cost, tool usage, and false-wake rate.  The store
is in-process and persists to JSONL; the dashboard reads it for charts.

Strictly opt-in: ``MetricsStore.enabled`` defaults to False so nothing
is recorded unless the user turned it on in Settings.
"""

from __future__ import annotations

import json
from collections import Counter, deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MetricEvent:
    kind: str  # 'latency' | 'cost' | 'tool' | 'wake'
    value: float
    label: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "value": self.value,
            "label": self.label,
            "timestamp": self.timestamp.isoformat(),
        }


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    k = (len(ordered) - 1) * (pct / 100)
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    frac = k - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


@dataclass
class MetricsStore:
    """Opt-in append-only metric store with simple rollups."""

    path: Path | None = None
    enabled: bool = False
    capacity: int = 5000
    _events: deque[MetricEvent] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        self._events = deque(maxlen=self.capacity)
        if self.path and self.path.exists():
            for line in self.path.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                    self._events.append(
                        MetricEvent(
                            kind=str(d["kind"]),
                            value=float(d["value"]),
                            label=str(d.get("label", "")),
                            timestamp=datetime.fromisoformat(str(d["timestamp"])),
                        )
                    )
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

    # ---- writes ----

    def record_latency(self, ms: float, *, label: str = "") -> None:
        self._record(MetricEvent(kind="latency", value=ms, label=label))

    def record_cost(self, usd: float, *, model: str = "") -> None:
        self._record(MetricEvent(kind="cost", value=usd, label=model))

    def record_tool(self, name: str) -> None:
        self._record(MetricEvent(kind="tool", value=1.0, label=name))

    def record_wake(self, *, real: bool) -> None:
        self._record(MetricEvent(kind="wake", value=1.0 if real else 0.0))

    # ---- reads ----

    def latency_p50(self) -> float:
        return _percentile([e.value for e in self._events if e.kind == "latency"], 50)

    def latency_p95(self) -> float:
        return _percentile([e.value for e in self._events if e.kind == "latency"], 95)

    def total_cost(self) -> float:
        return sum(e.value for e in self._events if e.kind == "cost")

    def tool_counts(self) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for e in self._events:
            if e.kind == "tool":
                counter[e.label or "unknown"] += 1
        return dict(counter)

    def false_wake_rate(self) -> float:
        wakes = [e for e in self._events if e.kind == "wake"]
        if not wakes:
            return 0.0
        false = sum(1 for w in wakes if w.value == 0.0)
        return false / len(wakes)

    def snapshot(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "events": len(self._events),
            "latency_p50_ms": self.latency_p50(),
            "latency_p95_ms": self.latency_p95(),
            "total_cost_usd": self.total_cost(),
            "tool_counts": self.tool_counts(),
            "false_wake_rate": self.false_wake_rate(),
        }

    def __len__(self) -> int:
        return len(self._events)

    def reset(self) -> None:
        self._events.clear()
        if self.path and self.path.exists():
            self.path.write_text("")

    # ---- internals ----

    def _record(self, event: MetricEvent) -> None:
        if not self.enabled:
            return
        self._events.append(event)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")


def render_dashboard(store: MetricsStore) -> str:
    """Tiny ASCII dashboard the tray menu can show."""
    snap = store.snapshot()
    lines = [
        "Nova metrics",
        "=" * 32,
        f"events:        {snap['events']}",
        f"latency p50:   {snap['latency_p50_ms']:.0f} ms",
        f"latency p95:   {snap['latency_p95_ms']:.0f} ms",
        f"total cost:    ${snap['total_cost_usd']:.2f}",
        f"false-wake:    {snap['false_wake_rate'] * 100:.1f}%",
        "tools:",
    ]
    for tool, count in sorted(store.tool_counts().items(), key=lambda kv: kv[1], reverse=True):
        lines.append(f"  {tool}: {count}")
    return "\n".join(lines)


def aggregate(events: Iterable[MetricEvent]) -> dict[str, float]:
    """Aggregate counts by kind for quick CLI reports."""
    counter: Counter[str] = Counter()
    for e in events:
        counter[e.kind] += 1
    return dict(counter)


__all__ = ["MetricEvent", "MetricsStore", "aggregate", "render_dashboard"]
