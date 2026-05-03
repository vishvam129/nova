"""Tests for nova.context.proactive."""

from __future__ import annotations

from datetime import datetime, timedelta

from nova.context.proactive import (
    EventKind,
    ProactiveEngine,
    Reminder,
    SystemEvent,
)


def test_reminder_fires_when_due() -> None:
    eng = ProactiveEngine()
    eng.add_reminder(Reminder(id="r1", text="call mom", fire_at=datetime(2026, 4, 28, 18)))
    out = eng.tick(now=datetime(2026, 4, 28, 18, 0, 1))
    assert len(out) == 1
    assert "mom" in out[0].text


def test_reminder_doesnt_fire_again() -> None:
    eng = ProactiveEngine()
    eng.add_reminder(Reminder(id="r1", text="x", fire_at=datetime(2026, 4, 28)))
    eng.tick(now=datetime(2026, 4, 28))
    out = eng.tick(now=datetime(2026, 4, 28))
    assert out == []


def test_reminder_not_due_yet() -> None:
    eng = ProactiveEngine()
    eng.add_reminder(Reminder(id="r1", text="x", fire_at=datetime(2026, 5, 1)))
    out = eng.tick(now=datetime(2026, 4, 28))
    assert out == []


def test_cancel_reminder() -> None:
    eng = ProactiveEngine()
    eng.add_reminder(Reminder(id="r1", text="x", fire_at=datetime(2026, 4, 28)))
    assert eng.cancel_reminder("r1") is True
    assert eng.cancel_reminder("ghost") is False


def test_battery_low_event_suggestion() -> None:
    eng = ProactiveEngine()
    out = eng.tick(
        now=datetime(2026, 4, 28),
        events=[SystemEvent(kind=EventKind.BATTERY_LOW, payload={"percent": "12"})],
    )
    assert len(out) == 1
    assert "12%" in out[0].text


def test_commute_start_suggestion() -> None:
    eng = ProactiveEngine()
    out = eng.tick(
        now=datetime(2026, 4, 28),
        events=[
            SystemEvent(
                kind=EventKind.COMMUTE_START,
                payload={"destination": "office", "traffic": "light"},
            )
        ],
    )
    assert "office" in out[0].text
    assert "light" in out[0].text


def test_calendar_warn_suggestion() -> None:
    eng = ProactiveEngine()
    out = eng.tick(
        now=datetime(2026, 4, 28),
        events=[
            SystemEvent(
                kind=EventKind.CALENDAR_WARN,
                payload={"title": "Standup", "minutes": "5"},
            )
        ],
    )
    assert "Standup" in out[0].text
    assert "5" in out[0].text


def test_dedupe_within_ttl() -> None:
    eng = ProactiveEngine(dedupe_ttl=timedelta(minutes=15))
    base = datetime(2026, 4, 28, 10)
    eng.tick(
        now=base,
        events=[SystemEvent(kind=EventKind.BATTERY_LOW, payload={"percent": "12"})],
    )
    out = eng.tick(
        now=base + timedelta(minutes=5),
        events=[SystemEvent(kind=EventKind.BATTERY_LOW, payload={"percent": "12"})],
    )
    assert out == []


def test_dedupe_expires_after_ttl() -> None:
    eng = ProactiveEngine(dedupe_ttl=timedelta(minutes=15))
    base = datetime(2026, 4, 28, 10)
    eng.tick(
        now=base,
        events=[SystemEvent(kind=EventKind.BATTERY_LOW, payload={"percent": "12"})],
    )
    out = eng.tick(
        now=base + timedelta(hours=1),
        events=[SystemEvent(kind=EventKind.BATTERY_LOW, payload={"percent": "12"})],
    )
    assert len(out) == 1


def test_custom_event_with_text() -> None:
    eng = ProactiveEngine()
    out = eng.tick(
        now=datetime.now(),
        events=[SystemEvent(kind=EventKind.CUSTOM, payload={"text": "hi"})],
    )
    assert out[0].text == "hi"


def test_custom_event_without_text_dropped() -> None:
    eng = ProactiveEngine()
    out = eng.tick(now=datetime.now(), events=[SystemEvent(kind=EventKind.CUSTOM)])
    assert out == []
