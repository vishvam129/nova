"""Tests for nova.quality.metrics."""

from __future__ import annotations

from pathlib import Path

from nova.quality.metrics import (
    MetricEvent,
    MetricsStore,
    aggregate,
    render_dashboard,
)


def test_disabled_records_nothing(tmp_path: Path) -> None:
    s = MetricsStore(path=tmp_path / "m.jsonl", enabled=False)
    s.record_latency(100)
    s.record_cost(0.5)
    assert len(s) == 0


def test_enabled_records_events(tmp_path: Path) -> None:
    s = MetricsStore(path=tmp_path / "m.jsonl", enabled=True)
    s.record_latency(100)
    s.record_latency(200)
    assert len(s) == 2


def test_latency_p50_p95() -> None:
    import pytest as _p

    s = MetricsStore(enabled=True)
    for v in (100, 200, 300, 400, 500):
        s.record_latency(v)
    assert s.latency_p50() == _p.approx(300)
    assert s.latency_p95() == _p.approx(480)


def test_total_cost_sums() -> None:
    import pytest as _p

    s = MetricsStore(enabled=True)
    s.record_cost(0.10, model="opus")
    s.record_cost(0.05, model="sonnet")
    assert s.total_cost() == _p.approx(0.15)


def test_tool_counts() -> None:
    s = MetricsStore(enabled=True)
    s.record_tool("send_sms")
    s.record_tool("send_sms")
    s.record_tool("open_app")
    assert s.tool_counts() == {"send_sms": 2, "open_app": 1}


def test_false_wake_rate() -> None:
    s = MetricsStore(enabled=True)
    s.record_wake(real=True)
    s.record_wake(real=True)
    s.record_wake(real=False)
    s.record_wake(real=False)
    assert s.false_wake_rate() == 0.5


def test_snapshot_keys() -> None:
    s = MetricsStore(enabled=True)
    s.record_latency(100)
    snap = s.snapshot()
    for key in ("latency_p50_ms", "latency_p95_ms", "total_cost_usd", "false_wake_rate"):
        assert key in snap


def test_persistence_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "m.jsonl"
    s1 = MetricsStore(path=p, enabled=True)
    s1.record_latency(100)
    s1.record_cost(0.05, model="opus")
    s2 = MetricsStore(path=p, enabled=True)
    assert len(s2) == 2


def test_reset_clears(tmp_path: Path) -> None:
    s = MetricsStore(path=tmp_path / "m.jsonl", enabled=True)
    s.record_latency(100)
    s.reset()
    assert len(s) == 0


def test_render_dashboard_strings() -> None:
    s = MetricsStore(enabled=True)
    s.record_latency(100)
    s.record_tool("open_app")
    s.record_cost(0.10)
    out = render_dashboard(s)
    assert "Nova metrics" in out
    assert "open_app" in out
    assert "p50" in out


def test_aggregate_helper() -> None:
    events = [
        MetricEvent(kind="latency", value=1),
        MetricEvent(kind="latency", value=2),
        MetricEvent(kind="cost", value=0.1),
    ]
    out = aggregate(events)
    assert out == {"latency": 2, "cost": 1}
