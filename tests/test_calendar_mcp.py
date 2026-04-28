"""Tests for nova.integrations.calendar_mcp."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from nova.context.calendar import CalendarEvent
from nova.integrations.calendar_mcp import (
    AppleCalendar,
    CalDavBackend,
    CalendarToolHandler,
    GoogleCalendar,
)


def _ev(title: str = "T") -> CalendarEvent:
    s = datetime(2026, 4, 28, 10)
    return CalendarEvent(title=title, start=s, end=s + timedelta(hours=1))


def test_caldav_construct() -> None:
    b = CalDavBackend(base_url="https://nc.example", username="u", password="p")
    assert b.calendar_path.endswith("/")


def test_apple_calendar_default_url() -> None:
    a = AppleCalendar(username="u", password="p")
    assert "icloud.com" in a.base_url


def test_google_calendar_defaults() -> None:
    g = GoogleCalendar(access_token="t")
    assert g.calendar_id == "primary"
    assert "googleapis.com" in g.endpoint


def test_handler_list() -> None:
    backend = CalDavBackend(base_url="x", username="u", password="p")
    h = CalendarToolHandler(backend=backend)
    out = h.call("calendar.list", start="2026-04-28T00:00:00", end="2026-04-29T00:00:00")
    assert isinstance(out, list)


def test_handler_list_requires_dates() -> None:
    backend = CalDavBackend(base_url="x", username="u", password="p")
    h = CalendarToolHandler(backend=backend)
    with pytest.raises(ValueError):
        h.call("calendar.list")


def test_handler_create() -> None:
    backend = CalDavBackend(base_url="x", username="u", password="p")
    h = CalendarToolHandler(backend=backend)
    out = h.call(
        "calendar.create",
        title="Meeting",
        start="2026-04-28T10:00:00",
        end="2026-04-28T11:00:00",
    )
    assert isinstance(out, dict)
    assert "id" in out


def test_handler_delete() -> None:
    backend = CalDavBackend(base_url="x", username="u", password="p")
    h = CalendarToolHandler(backend=backend)
    out = h.call("calendar.delete", id="evt-1")
    assert out == {"ok": True}


def test_handler_unknown_tool() -> None:
    backend = CalDavBackend(base_url="x", username="u", password="p")
    h = CalendarToolHandler(backend=backend)
    with pytest.raises(ValueError):
        h.call("calendar.bogus")


def test_handler_with_google_backend() -> None:
    h = CalendarToolHandler(backend=GoogleCalendar(access_token="t"))
    out = h.call("calendar.create", title="x", start=datetime.now(), end=datetime.now())
    assert "id" in out  # type: ignore[operator]
