"""Location provider with explicit opt-in.

Two backends:
    PhoneGpsProvider — phone pushes GPS coords over the WS each time
    IpGeoProvider    — IP-based geolocation (city-grade), used on laptop

``LocationGate`` enforces the opt-in flag and TTL — if the user hasn't
accepted location sharing, providers return None regardless.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Location:
    latitude: float
    longitude: float
    accuracy_m: float = 0.0
    source: str = "unknown"
    captured_at: datetime = field(default_factory=datetime.now)
    city: str = ""
    country: str = ""

    def to_prompt(self) -> str:
        if self.city and self.country:
            return f"User is in {self.city}, {self.country}."
        return f"User is at {self.latitude:.3f}, {self.longitude:.3f}."


class LocationProvider(Protocol):
    def location(self) -> Location | None: ...


@dataclass
class PhoneGpsProvider:
    """Caches the most recent GPS reading the phone pushed."""

    latest: Location | None = None
    max_age: timedelta = timedelta(minutes=10)

    def push(self, location: Location) -> None:
        self.latest = location

    def location(self) -> Location | None:
        if self.latest is None:
            return None
        if datetime.now() - self.latest.captured_at > self.max_age:
            return None
        return self.latest


@dataclass
class IpGeoProvider:
    """Calls ipapi.co for a coarse city-level fix."""

    timeout_s: float = 3.0
    endpoint: str = "https://ipapi.co/json/"

    def location(self) -> Location | None:
        try:
            with urllib.request.urlopen(self.endpoint, timeout=self.timeout_s) as resp:
                data = json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            return None
        try:
            return Location(
                latitude=float(data["latitude"]),
                longitude=float(data["longitude"]),
                accuracy_m=float(data.get("accuracy", 5_000)),
                source="ipgeo",
                city=str(data.get("city", "")),
                country=str(data.get("country_name", "")),
            )
        except (KeyError, ValueError, TypeError):
            return None


@dataclass
class LocationGate:
    """Enforces opt-in + delegates to the configured provider."""

    provider: LocationProvider
    opted_in: bool = False

    def opt_in(self) -> None:
        self.opted_in = True

    def opt_out(self) -> None:
        self.opted_in = False

    def location(self) -> Location | None:
        if not self.opted_in:
            return None
        return self.provider.location()


__all__ = ["IpGeoProvider", "Location", "LocationGate", "LocationProvider", "PhoneGpsProvider"]
