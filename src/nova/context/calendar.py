"""Calendar integration for brain context.

Reads today's events from a CalendarSource (Protocol) and renders them
as prompt context. Sources can be Google Calendar API, an .ics file,
or any custom adapter — the brain side only sees ``CalendarEvent`` records.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    title: str
    start: datetime
    end: datetime
    location: str = ""
    attendees: tuple[str, ...] = ()

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() / 60)

    def is_today(self, today: date | None = None) -> bool:
        d = today or date.today()
        return self.start.date() == d


class CalendarSource(Protocol):
    def events_in_range(self, start: datetime, end: datetime) -> Iterable[CalendarEvent]: ...


@dataclass
class StaticCalendarSource:
    """In-memory event store; useful for tests + manual entries."""

    events: list[CalendarEvent] = field(default_factory=list)

    def add(self, event: CalendarEvent) -> None:
        self.events.append(event)

    def events_in_range(self, start: datetime, end: datetime) -> Iterable[CalendarEvent]:
        return [ev for ev in self.events if start <= ev.start < end]


@dataclass
class IcsCalendarSource:
    """Minimal .ics reader (subset of RFC 5545)."""

    path: Path

    def events_in_range(self, start: datetime, end: datetime) -> Iterable[CalendarEvent]:
        if not self.path.exists():
            return []
        return [ev for ev in _parse_ics(self.path.read_text()) if start <= ev.start < end]


def _parse_ics(text: str) -> list[CalendarEvent]:
    """Parse a complete .ics document into a list of events."""
    out: list[CalendarEvent] = []
    current: dict[str, object] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if line == "BEGIN:VEVENT":
            current = {"title": "", "start": None, "end": None, "location": ""}
        elif current is None:
            continue
        elif line == "END:VEVENT":
            ev = _ics_event_from_fields(current)
            if ev is not None:
                out.append(ev)
            current = None
        else:
            _ics_apply_line(current, line)
    return out


def _ics_apply_line(fields: dict[str, object], line: str) -> None:
    if line.startswith("SUMMARY:"):
        fields["title"] = line[len("SUMMARY:") :]
    elif line.startswith("LOCATION:"):
        fields["location"] = line[len("LOCATION:") :]
    elif line.startswith("DTSTART"):
        fields["start"] = _parse_ics_dt(line.split(":", 1)[-1])
    elif line.startswith("DTEND"):
        fields["end"] = _parse_ics_dt(line.split(":", 1)[-1])


def _ics_event_from_fields(fields: dict[str, object]) -> CalendarEvent | None:
    start = fields.get("start")
    end = fields.get("end")
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        return None
    return CalendarEvent(
        title=str(fields.get("title", "")),
        start=start,
        end=end,
        location=str(fields.get("location", "")),
    )


def _parse_ics_dt(value: str) -> datetime | None:
    value = value.strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def todays_events(source: CalendarSource, today: date | None = None) -> list[CalendarEvent]:
    d = today or date.today()
    start = datetime(d.year, d.month, d.day)
    return list(source.events_in_range(start, start + timedelta(days=1)))


def upcoming(
    source: CalendarSource, *, hours: float = 24.0, now: datetime | None = None
) -> list[CalendarEvent]:
    n = now or datetime.now()
    return list(source.events_in_range(n, n + timedelta(hours=hours)))


def to_prompt(events: Iterable[CalendarEvent]) -> str:
    items = list(events)
    if not items:
        return "No upcoming events."
    lines = ["Upcoming events:"]
    for ev in items:
        when = ev.start.strftime("%H:%M")
        line = f"- {when}  {ev.title} ({ev.duration_minutes} min)"
        if ev.location:
            line += f" @ {ev.location}"
        lines.append(line)
    return "\n".join(lines)


__all__ = [
    "CalendarEvent",
    "CalendarSource",
    "IcsCalendarSource",
    "StaticCalendarSource",
    "to_prompt",
    "todays_events",
    "upcoming",
]
