"""Tests for nova.context.scheduler."""

from __future__ import annotations

from datetime import datetime

import pytest

from nova.context.scheduler import CronJob, CronScheduler, parse_cron


def test_parse_basic() -> None:
    e = parse_cron("0 8 * * 1-5")
    assert 0 in e.minute
    assert 8 in e.hour
    assert e.dow == frozenset({1, 2, 3, 4, 5})


def test_parse_alias_daily() -> None:
    e = parse_cron("@daily")
    assert e.minute == frozenset({0})
    assert e.hour == frozenset({0})


def test_parse_alias_weekday() -> None:
    e = parse_cron("@weekday")
    assert e.dow == frozenset({1, 2, 3, 4, 5})


def test_parse_step() -> None:
    e = parse_cron("*/15 * * * *")
    assert e.minute == frozenset({0, 15, 30, 45})


def test_parse_invalid_field_count() -> None:
    with pytest.raises(ValueError):
        parse_cron("0 8 * *")


def test_parse_out_of_range() -> None:
    with pytest.raises(ValueError):
        parse_cron("0 25 * * *")


def test_matches_specific_time() -> None:
    e = parse_cron("0 8 * * 1-5")  # weekday 8 AM
    monday = datetime(2026, 4, 27, 8, 0)  # Monday
    saturday = datetime(2026, 5, 2, 8, 0)  # Saturday
    assert e.matches(monday) is True
    assert e.matches(saturday) is False


def test_cron_job_fires_once_per_minute() -> None:
    fired = []
    job = CronJob("brief", "0 8 * * *", lambda: fired.append(1))
    now = datetime(2026, 4, 28, 8, 0)
    assert job.fire_if_due(now) is True
    # Same minute, should not fire again
    assert job.fire_if_due(now) is False
    assert len(fired) == 1


def test_cron_job_fires_again_next_day() -> None:
    fired = []
    job = CronJob("brief", "0 8 * * *", lambda: fired.append(1))
    job.fire_if_due(datetime(2026, 4, 28, 8, 0))
    job.fire_if_due(datetime(2026, 4, 29, 8, 0))
    assert len(fired) == 2


def test_scheduler_tick_runs_due_jobs() -> None:
    sched = CronScheduler()
    fired = []
    sched.add(CronJob("a", "0 8 * * *", lambda: fired.append("a")))
    sched.add(CronJob("b", "0 9 * * *", lambda: fired.append("b")))
    out = sched.tick(datetime(2026, 4, 28, 8, 0))
    assert out == ["a"]
    assert fired == ["a"]


def test_scheduler_remove() -> None:
    sched = CronScheduler()
    sched.add(CronJob("a", "* * * * *", lambda: None))
    assert sched.remove("a") is True
    assert sched.remove("ghost") is False
