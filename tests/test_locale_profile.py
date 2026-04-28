"""Tests for nova.context.locale."""

from __future__ import annotations

from nova.context.locale import LocaleProfile, _detect_24h, detect_profile, utc_now


def test_detect_24h_us_is_false() -> None:
    assert _detect_24h("US") is False


def test_detect_24h_other_is_true() -> None:
    assert _detect_24h("FR") is True
    assert _detect_24h("JP") is True


def test_locale_profile_to_prompt_24h() -> None:
    p = LocaleProfile(
        timezone_name="UTC",
        utc_offset_minutes=0,
        is_dst=False,
        language="en",
        region="GB",
        use_24h=True,
        metric=True,
    )
    out = p.to_prompt()
    assert "UTC" in out
    assert "metric" in out
    assert "en-GB" in out


def test_locale_profile_to_prompt_imperial_12h() -> None:
    p = LocaleProfile(
        timezone_name="EST",
        utc_offset_minutes=-300,
        is_dst=False,
        language="en",
        region="US",
        use_24h=False,
        metric=False,
    )
    out = p.to_prompt()
    assert "imperial" in out
    assert "en-US" in out


def test_locale_profile_dst_marker() -> None:
    p = LocaleProfile(
        timezone_name="EDT",
        utc_offset_minutes=-240,
        is_dst=True,
        language="en",
        region="US",
        use_24h=False,
        metric=False,
    )
    assert "(DST)" in p.to_prompt()


def test_detect_profile_returns_profile() -> None:
    p = detect_profile()
    assert isinstance(p, LocaleProfile)
    assert p.language != ""
    assert p.region != ""


def test_utc_now_has_utc_tz() -> None:
    n = utc_now()
    assert n.tzinfo is not None
    assert n.utcoffset().total_seconds() == 0  # type: ignore[union-attr]
