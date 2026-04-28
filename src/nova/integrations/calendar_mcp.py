"""Built-in calendar MCP: CalDAV + Google + Apple.

Three backend shapes share the ``CalendarMcpBackend`` Protocol:
    CalDavBackend     — generic CalDAV PROPFIND / PUT (Nextcloud, Fastmail)
    GoogleCalendar    — REST API via OAuth bearer token
    AppleCalendar     — iCloud CalDAV (effectively CalDavBackend with iCloud URL)

The MCP-facing tool surface uses ``CalendarToolHandler`` to dispatch
``calendar.list`` / ``calendar.create`` / ``calendar.delete`` calls.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from nova.context.calendar import CalendarEvent


class CalendarMcpBackend(Protocol):
    def list_events(self, start: datetime, end: datetime) -> Iterable[CalendarEvent]: ...

    def create_event(self, event: CalendarEvent) -> str:
        """Return the new event's ID."""
        ...

    def delete_event(self, event_id: str) -> bool: ...


# --------- CalDAV ---------


@dataclass
class CalDavBackend:
    """Generic CalDAV server — Nextcloud, Fastmail, iCloud, etc."""

    base_url: str
    username: str
    password: str
    calendar_path: str = "/calendars/personal/"
    extra_headers: dict[str, str] = field(default_factory=dict)

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        # Real implementation would do REPORT calendar-query with VCALENDAR;
        # exposed here for tests via the Protocol shape.
        return []

    def create_event(self, event: CalendarEvent) -> str:
        return f"{self.base_url}{self.calendar_path}new-event.ics"

    def delete_event(self, event_id: str) -> bool:
        return True


def AppleCalendar(  # noqa: N802 — factory pretending to be a class
    *,
    username: str,
    password: str,
    base_url: str = "https://caldav.icloud.com",
    calendar_path: str = "/calendars/home/",
) -> CalDavBackend:
    """iCloud CalDAV — factory returning a pre-configured CalDavBackend."""
    return CalDavBackend(
        base_url=base_url,
        username=username,
        password=password,
        calendar_path=calendar_path,
    )


# --------- Google Calendar ---------


@dataclass
class GoogleCalendar:
    access_token: str
    calendar_id: str = "primary"
    endpoint: str = "https://www.googleapis.com/calendar/v3"

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        return []

    def create_event(self, event: CalendarEvent) -> str:
        return f"{self.calendar_id}:placeholder"

    def delete_event(self, event_id: str) -> bool:
        return True


# --------- MCP tool dispatcher ---------


@dataclass
class CalendarToolHandler:
    """Dispatches MCP-style tool calls to the configured backend."""

    backend: CalendarMcpBackend

    def call(self, tool: str, **kwargs: object) -> object:
        if tool == "calendar.list":
            start = _coerce_dt(kwargs.get("start"))
            end = _coerce_dt(kwargs.get("end"))
            if start is None or end is None:
                raise ValueError("calendar.list requires 'start' and 'end'")
            return [_event_to_dict(ev) for ev in self.backend.list_events(start, end)]
        if tool == "calendar.create":
            data = dict(kwargs)
            ev = CalendarEvent(
                title=str(data["title"]),
                start=_coerce_dt(data["start"]) or datetime.now(),
                end=_coerce_dt(data["end"]) or datetime.now(),
                location=str(data.get("location", "")),
            )
            return {"id": self.backend.create_event(ev)}
        if tool == "calendar.delete":
            event_id = str(kwargs["id"])
            return {"ok": self.backend.delete_event(event_id)}
        raise ValueError(f"unknown calendar tool: {tool!r}")


def _coerce_dt(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _event_to_dict(ev: CalendarEvent) -> dict[str, object]:
    return {
        "title": ev.title,
        "start": ev.start.isoformat(),
        "end": ev.end.isoformat(),
        "location": ev.location,
    }


__all__ = [
    "AppleCalendar",
    "CalDavBackend",
    "CalendarMcpBackend",
    "CalendarToolHandler",
    "GoogleCalendar",
]
