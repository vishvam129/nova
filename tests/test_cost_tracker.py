"""Tests for nova.brain.cost_tracker."""

from __future__ import annotations

from pathlib import Path

from nova.brain.cost_tracker import CostTracker


def test_starts_empty(tmp_path: Path) -> None:
    t = CostTracker(daily_cap_usd=1.0, state_path=tmp_path / "c.json")
    assert t.spend_usd == 0.0
    assert t.check() is True


def test_records_cost(tmp_path: Path) -> None:
    t = CostTracker(daily_cap_usd=10.0, state_path=tmp_path / "c.json")
    t.record("claude-opus-4-7", 1000)
    assert t.spend_usd == 0.020
    assert t.tokens == 1000


def test_unknown_model_zero_cost(tmp_path: Path) -> None:
    t = CostTracker(daily_cap_usd=1.0, state_path=tmp_path / "c.json")
    t.record("unknown-model", 1000)
    assert t.spend_usd == 0.0


def test_check_blocks_when_capped(tmp_path: Path) -> None:
    t = CostTracker(daily_cap_usd=0.01, state_path=tmp_path / "c.json")
    t.record("claude-opus-4-7", 1000)  # $0.02 > $0.01 cap
    assert t.check() is False


def test_remaining_usd(tmp_path: Path) -> None:
    t = CostTracker(daily_cap_usd=1.0, state_path=tmp_path / "c.json")
    t.record("gpt-4o", 1000)  # $0.01
    assert t.remaining_usd() == 0.99


def test_persistence(tmp_path: Path) -> None:
    state = tmp_path / "c.json"
    t1 = CostTracker(daily_cap_usd=1.0, state_path=state)
    t1.record("claude-opus-4-7", 500)
    t2 = CostTracker(daily_cap_usd=1.0, state_path=state)
    assert t2.spend_usd == t1.spend_usd
    assert t2.tokens == 500


def test_reset(tmp_path: Path) -> None:
    t = CostTracker(daily_cap_usd=1.0, state_path=tmp_path / "c.json")
    t.record("claude-opus-4-7", 1000)
    t.reset()
    assert t.spend_usd == 0.0
    assert t.tokens == 0


def test_remaining_clamped_at_zero(tmp_path: Path) -> None:
    t = CostTracker(daily_cap_usd=0.001, state_path=tmp_path / "c.json")
    t.record("claude-opus-4-7", 10000)
    assert t.remaining_usd() == 0.0
