"""Tests for nova.context.calendar."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from nova.context.calendar import (
    CalendarEvent,
    IcsCalendarSource,
    StaticCalendarSource,
    to_prompt,
    todays_events,
    upcoming,
)


def _ev(title: str, start: datetime, minutes: int = 30, **kw: object) -> CalendarEvent:
    return CalendarEvent(
        title=title,
        start=start,
        end=start + timedelta(minutes=minutes),
        **kw,  # type: ignore[arg-type]
    )


def test_event_duration() -> None:
    s = datetime(2026, 4, 28, 10)
    ev = _ev("test", s, minutes=45)
    assert ev.duration_minutes == 45


def test_event_is_today() -> None:
    today = date(2026, 4, 28)
    ev = _ev("x", datetime(2026, 4, 28, 9))
    assert ev.is_today(today) is True
    assert ev.is_today(date(2026, 4, 27)) is False


def test_static_source_filters_range() -> None:
    src = StaticCalendarSource()
    src.add(_ev("inside", datetime(2026, 4, 28, 10)))
    src.add(_ev("outside", datetime(2026, 4, 30, 10)))
    out = list(src.events_in_range(datetime(2026, 4, 28), datetime(2026, 4, 29)))
    assert [e.title for e in out] == ["inside"]


def test_todays_events() -> None:
    src = StaticCalendarSource()
    today = date(2026, 4, 28)
    src.add(_ev("today", datetime(2026, 4, 28, 12)))
    src.add(_ev("yest", datetime(2026, 4, 27, 12)))
    out = todays_events(src, today=today)
    assert len(out) == 1
    assert out[0].title == "today"


def test_upcoming() -> None:
    src = StaticCalendarSource()
    now = datetime(2026, 4, 28, 10)
    src.add(_ev("soon", now + timedelta(hours=1)))
    src.add(_ev("later", now + timedelta(hours=48)))
    out = upcoming(src, hours=24, now=now)
    assert len(out) == 1


def test_to_prompt_empty() -> None:
    assert "No upcoming" in to_prompt([])


def test_to_prompt_with_events() -> None:
    out = to_prompt(
        [
            _ev("Standup", datetime(2026, 4, 28, 9, 30), location="Zoom"),
            _ev("Lunch", datetime(2026, 4, 28, 12), minutes=60),
        ]
    )
    assert "Standup" in out
    assert "09:30" in out
    assert "Zoom" in out
    assert "Lunch" in out


def test_ics_source_parses_events(tmp_path: Path) -> None:
    p = tmp_path / "cal.ics"
    p.write_text(
        "BEGIN:VCALENDAR\n"
        "BEGIN:VEVENT\n"
        "SUMMARY:Standup\n"
        "DTSTART:20260428T093000Z\n"
        "DTEND:20260428T100000Z\n"
        "LOCATION:Zoom\n"
        "END:VEVENT\n"
        "BEGIN:VEVENT\n"
        "SUMMARY:Outside\n"
        "DTSTART:20260501T100000Z\n"
        "DTEND:20260501T110000Z\n"
        "END:VEVENT\n"
        "END:VCALENDAR\n"
    )
    src = IcsCalendarSource(path=p)
    out = list(src.events_in_range(datetime(2026, 4, 28), datetime(2026, 4, 29)))
    assert len(out) == 1
    assert out[0].title == "Standup"
    assert out[0].location == "Zoom"


def test_ics_source_missing_file(tmp_path: Path) -> None:
    src = IcsCalendarSource(path=tmp_path / "missing.ics")
    out = list(src.events_in_range(datetime.now(), datetime.now() + timedelta(days=1)))
    assert out == []
