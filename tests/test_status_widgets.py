"""Tests for nova.ui.status_widgets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from nova.ui.status_widgets import StatusWidgets


@dataclass
class _FakeCost:
    spend_usd: float = 0.0
    tokens: int = 0


def test_cost_today_no_source() -> None:
    w = StatusWidgets()
    assert w.cost_today() == "$0.00"


def test_cost_today_with_source() -> None:
    w = StatusWidgets(cost=_FakeCost(spend_usd=0.456))
    assert w.cost_today() == "$0.46"


def test_requests_today_counter() -> None:
    w = StatusWidgets()
    w.record_request()
    w.record_request()
    assert w.requests_today() == "2 requests"


def test_requests_today_with_fn() -> None:
    w = StatusWidgets(requests_today_fn=lambda: 42)
    assert w.requests_today() == "42 requests"


def test_next_reminder_none() -> None:
    w = StatusWidgets()
    assert w.next_reminder() == "no reminders"


def test_next_reminder_minutes() -> None:
    when = datetime.now() + timedelta(minutes=30)
    w = StatusWidgets(next_reminder_fn=lambda: ("Standup", when))
    out = w.next_reminder()
    assert "Standup" in out
    assert "m" in out


def test_next_reminder_hours() -> None:
    when = datetime.now() + timedelta(hours=3)
    w = StatusWidgets(next_reminder_fn=lambda: ("Lunch", when))
    out = w.next_reminder()
    assert "Lunch" in out
    assert "h" in out


def test_last_command_empty() -> None:
    w = StatusWidgets()
    assert w.last_command_label() == "no recent command"


def test_last_command_short() -> None:
    w = StatusWidgets()
    w.set_last_command("hello world")
    assert w.last_command_label() == "hello world"


def test_last_command_truncated() -> None:
    w = StatusWidgets()
    w.set_last_command("a" * 80)
    out = w.last_command_label()
    assert out.endswith("...")
    assert len(out) == 40


def test_snapshot_aggregates_all_four() -> None:
    w = StatusWidgets(
        cost=_FakeCost(spend_usd=0.10),
        requests_today_fn=lambda: 3,
        next_reminder_fn=lambda: None,
    )
    w.set_last_command("open Spotify")
    snap = w.snapshot()
    assert snap.cost_today == "$0.10"
    assert snap.requests_today == "3 requests"
    assert snap.next_reminder == "no reminders"
    assert snap.last_command == "open Spotify"
