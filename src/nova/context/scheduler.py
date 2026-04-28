"""Cron/trigger engine for scheduled agent tasks.

Lightweight cron with a 5-field syntax (minute hour day-of-month month
day-of-week) plus convenience aliases like @daily / @hourly / weekday.

Usage::

    sched = CronScheduler()
    sched.add(CronJob("morning_brief", "0 8 * * 1-5", lambda: brain.brief()))
    while running:
        sched.tick(datetime.now())
        time.sleep(30)
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

_ALIASES = {
    "@hourly": "0 * * * *",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@noon": "0 12 * * *",
    "@weekday": "0 9 * * 1-5",
    "@weekly": "0 0 * * 0",
}


@dataclass(frozen=True, slots=True)
class CronExpr:
    minute: frozenset[int]
    hour: frozenset[int]
    dom: frozenset[int]
    month: frozenset[int]
    dow: frozenset[int]

    def matches(self, dt: datetime) -> bool:
        # cron uses Sunday=0 .. Saturday=6
        weekday = (dt.weekday() + 1) % 7
        return (
            dt.minute in self.minute
            and dt.hour in self.hour
            and dt.day in self.dom
            and dt.month in self.month
            and weekday in self.dow
        )


def parse_cron(spec: str) -> CronExpr:
    """Parse 5-field cron syntax (minute hour dom month dow)."""
    spec = spec.strip()
    if spec in _ALIASES:
        spec = _ALIASES[spec]
    fields = re.split(r"\s+", spec)
    if len(fields) != 5:
        raise ValueError(f"cron expression must have 5 fields: {spec!r}")
    return CronExpr(
        minute=_parse_field(fields[0], 0, 59),
        hour=_parse_field(fields[1], 0, 23),
        dom=_parse_field(fields[2], 1, 31),
        month=_parse_field(fields[3], 1, 12),
        dow=_parse_field(fields[4], 0, 6),
    )


def _parse_field(value: str, lo: int, hi: int) -> frozenset[int]:
    if value == "*":
        return frozenset(range(lo, hi + 1))
    out: set[int] = set()
    for token in value.split(","):
        if "/" in token:
            range_part, step_part = token.split("/", 1)
            step = int(step_part)
            base = _parse_field(range_part, lo, hi)
            out.update(v for v in base if (v - lo) % step == 0)
        elif "-" in token:
            a, b = token.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(token))
    if not out:
        raise ValueError(f"empty cron field: {value!r}")
    if any(v < lo or v > hi for v in out):
        raise ValueError(f"cron field out of range: {value!r}")
    return frozenset(out)


@dataclass
class CronJob:
    name: str
    schedule: str
    callback: Callable[[], None]
    expr: CronExpr = field(init=False)
    last_fired_minute: tuple[int, int, int, int, int] | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.expr = parse_cron(self.schedule)

    def fire_if_due(self, now: datetime) -> bool:
        if not self.expr.matches(now):
            return False
        key = (now.year, now.month, now.day, now.hour, now.minute)
        if self.last_fired_minute == key:
            return False
        self.last_fired_minute = key
        self.callback()
        return True


@dataclass
class CronScheduler:
    """Holds jobs and ticks them on each ``tick(now)`` call."""

    jobs: list[CronJob] = field(default_factory=list)

    def add(self, job: CronJob) -> None:
        self.jobs.append(job)

    def remove(self, name: str) -> bool:
        before = len(self.jobs)
        self.jobs = [j for j in self.jobs if j.name != name]
        return len(self.jobs) < before

    def tick(self, now: datetime) -> list[str]:
        fired: list[str] = []
        for job in self.jobs:
            if job.fire_if_due(now):
                fired.append(job.name)
        return fired

    def __len__(self) -> int:
        return len(self.jobs)


__all__ = ["CronExpr", "CronJob", "CronScheduler", "parse_cron"]
