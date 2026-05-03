"""Tests for nova.devops.telemetry."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from nova.devops.telemetry import ConsentWizard, TelemetryBuffer, event_total


def test_consent_default_no_decision(tmp_path: Path) -> None:
    w = ConsentWizard(state_path=tmp_path / "c.json")
    assert w.has_decided() is False
    assert w.consent() is False


def test_consent_records_yes(tmp_path: Path) -> None:
    w = ConsentWizard(state_path=tmp_path / "c.json")
    w.record_decision(opt_in=True)
    assert w.has_decided() is True
    assert w.consent() is True


def test_consent_records_no(tmp_path: Path) -> None:
    w = ConsentWizard(state_path=tmp_path / "c.json")
    w.record_decision(opt_in=False)
    assert w.consent() is False


def test_prompt_uses_callable(tmp_path: Path) -> None:
    w = ConsentWizard(state_path=tmp_path / "c.json")
    out = w.prompt(prompt_fn=lambda: True)
    assert out is True
    assert w.consent() is True


def test_prompt_skips_when_already_decided(tmp_path: Path) -> None:
    w = ConsentWizard(state_path=tmp_path / "c.json")
    w.record_decision(opt_in=True)
    out = w.prompt(prompt_fn=lambda: False)  # would say no, but already opted in
    assert out is True


def test_buffer_disabled_records_nothing(tmp_path: Path) -> None:
    b = TelemetryBuffer(enabled=False, aggregate_path=tmp_path / "t.json")
    b.record("wake")
    assert len(b) == 0
    assert b.flush() is None


def test_buffer_enabled_records(tmp_path: Path) -> None:
    b = TelemetryBuffer(enabled=True, aggregate_path=tmp_path / "t.json")
    b.record("wake", duration_ms=10)
    b.record("wake", duration_ms=20)
    assert len(b) == 2


def test_buffer_aggregates_per_day(tmp_path: Path) -> None:
    b = TelemetryBuffer(enabled=True, aggregate_path=tmp_path / "t.json")
    b.record("wake", duration_ms=5, when=date(2026, 4, 28))
    b.record("wake", duration_ms=15, when=date(2026, 4, 28))
    snap = b.snapshot()
    assert len(snap) == 1
    entry = snap[0]
    assert entry["count"] == 2
    assert entry["duration_min_ms"] == 5
    assert entry["duration_max_ms"] == 15
    assert entry["duration_sum_ms"] == 20


def test_buffer_flush_writes_file(tmp_path: Path) -> None:
    p = tmp_path / "t.json"
    b = TelemetryBuffer(enabled=True, aggregate_path=p)
    b.record("wake")
    out = b.flush()
    assert out == p
    data = json.loads(p.read_text())
    assert len(data) == 1
    assert len(b) == 0  # cleared after flush


def test_buffer_flush_appends(tmp_path: Path) -> None:
    p = tmp_path / "t.json"
    b1 = TelemetryBuffer(enabled=True, aggregate_path=p)
    b1.record("wake")
    b1.flush()
    b2 = TelemetryBuffer(enabled=True, aggregate_path=p)
    b2.record("reply")
    b2.flush()
    data = json.loads(p.read_text())
    assert len(data) == 2


def test_event_total_helper() -> None:
    snap = [
        {"event": "wake", "day": "2026-04-28", "count": 3},
        {"event": "wake", "day": "2026-04-29", "count": 5},
        {"event": "reply", "day": "2026-04-29", "count": 2},
    ]
    assert event_total(snap, "wake") == 8
    assert event_total(snap, "reply") == 2
    assert event_total(snap, "ghost") == 0
