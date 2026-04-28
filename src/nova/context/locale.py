"""Time / locale / language awareness for the system prompt.

The brain wants to know:
    - what time it is now (local)
    - what timezone the user is in (and DST status)
    - language + region
    - 12h vs 24h time preference
    - metric vs imperial units
"""

from __future__ import annotations

import locale
import time
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class LocaleProfile:
    timezone_name: str
    utc_offset_minutes: int
    is_dst: bool
    language: str  # e.g. "en"
    region: str  # e.g. "US"
    use_24h: bool
    metric: bool

    def now_local(self) -> datetime:
        return datetime.now()

    def to_prompt(self) -> str:
        now = self.now_local()
        time_fmt = "%H:%M" if self.use_24h else "%I:%M %p"
        units = "metric" if self.metric else "imperial"
        dst = " (DST)" if self.is_dst else ""
        return (
            f"Local time: {now.strftime('%Y-%m-%d ' + time_fmt)} "
            f"in {self.timezone_name}{dst}. "
            f"Language: {self.language}-{self.region}. Units: {units}."
        )


def detect_profile() -> LocaleProfile:
    """Best-effort autodetect from the OS."""
    is_dst = bool(time.daylight and time.localtime().tm_isdst)
    tz_name = time.tzname[1 if is_dst else 0] or "UTC"
    offset_seconds = -time.altzone if is_dst else -time.timezone
    offset_minutes = offset_seconds // 60

    lang_code, _enc = locale.getlocale()
    if lang_code and "_" in lang_code:
        lang, region = lang_code.split("_", 1)
    else:
        lang, region = (lang_code or "en"), "US"

    use_24h = _detect_24h(region)
    metric = region not in {"US", "LR", "MM"}

    return LocaleProfile(
        timezone_name=tz_name,
        utc_offset_minutes=offset_minutes,
        is_dst=is_dst,
        language=lang.lower(),
        region=region.upper(),
        use_24h=use_24h,
        metric=metric,
    )


def _detect_24h(region: str) -> bool:
    # Regions that use 12-hour clock by default
    region_12h = {"US", "CA", "AU", "NZ", "PH", "EG", "MX", "CO"}
    return region.upper() not in region_12h


def utc_now() -> datetime:
    return datetime.now(UTC)


__all__ = ["LocaleProfile", "detect_profile", "utc_now"]
