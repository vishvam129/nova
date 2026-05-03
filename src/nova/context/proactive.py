"""Proactive engine: scheduled reminders + event-driven suggestions.

Two surfaces feed the engine:
    - explicit Reminder objects with a fire_at time
    - SystemEvent inputs (battery_low, commute_start, calendar_15m_warn)

``ProactiveEngine.tick(now, events)`` returns the list of Suggestions to
push to the user this tick.  Suggestions are dedupe'd within a TTL so
"battery low" doesn't fire 60 times in 60 minutes.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum


class EventKind(StrEnum):
    BATTERY_LOW = "battery_low"
    COMMUTE_START = "commute_start"
    CALENDAR_WARN = "calendar_warn"
    HEALTH_NUDGE = "health_nudge"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class SystemEvent:
    kind: EventKind
    payload: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Reminder:
    id: str
    text: str
    fire_at: datetime
    fired: bool = False


@dataclass(frozen=True, slots=True)
class Suggestion:
    text: str
    source: str  # 'reminder' or event kind
    urgency: str = "normal"


@dataclass
class ProactiveEngine:
    reminders: list[Reminder] = field(default_factory=list)
    dedupe_ttl: timedelta = timedelta(minutes=15)
    _last_fired: dict[str, datetime] = field(default_factory=dict, init=False)

    # ---- reminder API ----

    def add_reminder(self, reminder: Reminder) -> None:
        self.reminders.append(reminder)

    def cancel_reminder(self, reminder_id: str) -> bool:
        before = len(self.reminders)
        self.reminders = [r for r in self.reminders if r.id != reminder_id]
        return len(self.reminders) < before

    # ---- main tick ----

    def tick(self, now: datetime, events: Iterable[SystemEvent] | None = None) -> list[Suggestion]:
        out: list[Suggestion] = []

        for r in self.reminders:
            if r.fired or r.fire_at > now:
                continue
            r.fired = True
            out.append(Suggestion(text=r.text, source="reminder"))

        for ev in events or ():
            sugg = self._suggestion_for(ev)
            if sugg is None:
                continue
            key = f"{ev.kind}:{sugg.text}"
            last = self._last_fired.get(key)
            if last and now - last < self.dedupe_ttl:
                continue
            self._last_fired[key] = now
            out.append(sugg)

        return out

    # ---- event → suggestion mapping ----

    def _suggestion_for(self, ev: SystemEvent) -> Suggestion | None:
        if ev.kind is EventKind.BATTERY_LOW:
            pct = ev.payload.get("percent", "?")
            return Suggestion(
                text=f"Battery at {pct}% — want me to enable power-save?",
                source=str(ev.kind),
                urgency="normal",
            )
        if ev.kind is EventKind.COMMUTE_START:
            dest = ev.payload.get("destination", "your destination")
            return Suggestion(
                text=f"Heading to {dest}? Traffic is {ev.payload.get('traffic', 'normal')}.",
                source=str(ev.kind),
            )
        if ev.kind is EventKind.CALENDAR_WARN:
            title = ev.payload.get("title", "your meeting")
            mins = ev.payload.get("minutes", "soon")
            return Suggestion(text=f"{title} starts in {mins} minutes.", source=str(ev.kind))
        if ev.kind is EventKind.HEALTH_NUDGE:
            return Suggestion(
                text=ev.payload.get("text", "time for a quick stretch."),
                source=str(ev.kind),
                urgency="low",
            )
        if ev.kind is EventKind.CUSTOM:
            text = ev.payload.get("text", "")
            return Suggestion(text=text, source=str(ev.kind)) if text else None
        return None


__all__ = ["EventKind", "ProactiveEngine", "Reminder", "Suggestion", "SystemEvent"]
