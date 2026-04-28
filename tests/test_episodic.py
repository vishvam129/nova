"""Tests for nova.memory.episodic."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from nova.memory.episodic import Episode, EpisodicMemory


def test_record_and_retrieve() -> None:
    m = EpisodicMemory()
    ep = m.record("user", "asked about weather", tags=["weather"])
    assert ep in m.all()
    assert len(m) == 1


def test_in_range_filter() -> None:
    m = EpisodicMemory()
    base = datetime(2026, 4, 25, 10, 0, 0)
    m.record("user", "early", when=base)
    m.record("user", "late", when=base + timedelta(hours=2))

    out = m.in_range(base + timedelta(hours=1), base + timedelta(hours=3))
    assert len(out) == 1
    assert out[0].description == "late"


def test_on_day() -> None:
    m = EpisodicMemory()
    today = datetime(2026, 4, 25, 9, 0)
    m.record("user", "today1", when=today)
    m.record("user", "today2", when=today.replace(hour=18))
    m.record("user", "yesterday", when=today - timedelta(days=1))

    out = m.on_day(date(2026, 4, 25))
    assert len(out) == 2


def test_search() -> None:
    m = EpisodicMemory()
    m.record("user", "Played some jazz on spotify")
    m.record("user", "Sent a text to mom")
    assert len(m.search("jazz")) == 1
    assert len(m.search("text")) == 1
    assert m.search("nothing") == []


def test_by_tag() -> None:
    m = EpisodicMemory()
    m.record("user", "a", tags=["work"])
    m.record("user", "b", tags=["personal"])
    assert len(m.by_tag("work")) == 1


def test_persistence_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "episodes.jsonl"
    m = EpisodicMemory(path=p)
    m.record("user", "first")
    m.record("agent", "second")

    m2 = EpisodicMemory(path=p)
    assert len(m2) == 2
    assert m2.all()[0].description == "first"
    assert m2.all()[1].actor == "agent"


def test_episode_dict_roundtrip() -> None:
    ep = Episode(
        timestamp=datetime(2026, 4, 25, 10, 0),
        actor="user",
        description="hello",
        tags=("test",),
    )
    d = ep.to_dict()
    assert Episode.from_dict(d) == ep


def test_today_and_yesterday() -> None:
    m = EpisodicMemory()
    now = datetime.now()
    m.record("user", "now", when=now)
    m.record("user", "yest", when=now - timedelta(days=1))
    assert any(e.description == "now" for e in m.today())
    assert any(e.description == "yest" for e in m.yesterday())
