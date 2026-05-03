"""Tests for nova.context.location."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from nova.context.location import (
    IpGeoProvider,
    Location,
    LocationGate,
    PhoneGpsProvider,
)


def test_to_prompt_with_city() -> None:
    loc = Location(latitude=37.77, longitude=-122.41, city="SF", country="USA")
    assert "SF" in loc.to_prompt()
    assert "USA" in loc.to_prompt()


def test_to_prompt_without_city() -> None:
    loc = Location(latitude=37.7, longitude=-122.4)
    out = loc.to_prompt()
    assert "37.7" in out
    assert "-122.4" in out


def test_phone_gps_returns_pushed() -> None:
    p = PhoneGpsProvider()
    loc = Location(latitude=1.0, longitude=2.0, source="gps")
    p.push(loc)
    assert p.location() == loc


def test_phone_gps_expires_after_max_age() -> None:
    p = PhoneGpsProvider(max_age=timedelta(minutes=10))
    p.push(
        Location(
            latitude=1.0,
            longitude=2.0,
            captured_at=datetime.now() - timedelta(hours=1),
        )
    )
    assert p.location() is None


def test_phone_gps_empty() -> None:
    assert PhoneGpsProvider().location() is None


def test_ip_geo_handles_network_error() -> None:
    p = IpGeoProvider()
    with patch("nova.context.location.urllib.request.urlopen", side_effect=OSError):
        assert p.location() is None


def test_ip_geo_parses_response() -> None:
    p = IpGeoProvider()
    fake = MagicMock()
    fake.read.return_value = (
        b'{"latitude":37.77,"longitude":-122.41,"city":"SF","country_name":"USA"}'
    )
    fake.__enter__ = MagicMock(return_value=fake)
    fake.__exit__ = MagicMock(return_value=False)
    with patch("nova.context.location.urllib.request.urlopen", return_value=fake):
        loc = p.location()
    assert loc is not None
    assert loc.city == "SF"
    assert loc.country == "USA"


def test_gate_blocks_without_opt_in() -> None:
    inner = PhoneGpsProvider()
    inner.push(Location(latitude=1.0, longitude=2.0))
    gate = LocationGate(provider=inner)
    assert gate.location() is None


def test_gate_passes_through_after_opt_in() -> None:
    inner = PhoneGpsProvider()
    inner.push(Location(latitude=1.0, longitude=2.0))
    gate = LocationGate(provider=inner)
    gate.opt_in()
    assert gate.location() is not None


def test_gate_opt_out_blocks() -> None:
    inner = PhoneGpsProvider()
    inner.push(Location(latitude=1.0, longitude=2.0))
    gate = LocationGate(provider=inner, opted_in=True)
    gate.opt_out()
    assert gate.location() is None
