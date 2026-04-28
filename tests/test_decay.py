"""Tests for nova.memory.decay."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from nova.memory.decay import MemoryDecay, MemoryItem


def test_invalid_importance_raises() -> None:
    with pytest.raises(ValueError):
        MemoryItem(content="x", importance=1.5)


def test_score_fresh_item_is_high() -> None:
    item = MemoryItem(content="x", importance=1.0)
    decay = MemoryDecay(half_life_hours=168)
    assert decay.score(item) > 0.99


def test_score_decays_with_age() -> None:
    base = datetime(2026, 4, 25, 10, 0, 0)
    item = MemoryItem(content="x", importance=1.0, last_accessed=base)
    decay = MemoryDecay(half_life_hours=24)
    later = base + timedelta(hours=24)
    s = decay.score(item, now=later)
    # at 24h half-life, after 24h the score should be ~exp(-1) ≈ 0.368
    assert 0.3 < s < 0.5


def test_high_importance_outranks_low() -> None:
    base = datetime.now()
    high = MemoryItem(content="hi", importance=0.9, last_accessed=base)
    low = MemoryItem(content="lo", importance=0.1, last_accessed=base)
    decay = MemoryDecay()
    assert decay.score(high) > decay.score(low)


def test_access_count_boosts_score() -> None:
    base = datetime(2026, 4, 25)
    accessed = MemoryItem(content="x", importance=0.5, access_count=20, last_accessed=base)
    fresh = MemoryItem(content="x", importance=0.5, access_count=0, last_accessed=base)
    decay = MemoryDecay()
    assert decay.score(accessed) > decay.score(fresh)


def test_should_prune_old_low_importance() -> None:
    base = datetime(2026, 1, 1)
    item = MemoryItem(content="x", importance=0.1, last_accessed=base)
    decay = MemoryDecay(half_life_hours=24, threshold=0.05)
    assert decay.should_prune(item, now=base + timedelta(days=30)) is True


def test_prune_filters_items() -> None:
    now = datetime.now()
    items = [
        MemoryItem(content="keep", importance=1.0, last_accessed=now),
        MemoryItem(content="drop", importance=0.05, last_accessed=now),
    ]
    decay = MemoryDecay(threshold=0.5)
    kept = decay.prune(items)
    assert len(kept) == 1
    assert kept[0].content == "keep"


def test_rank_ordered_descending() -> None:
    base = datetime.now()
    a = MemoryItem(content="a", importance=0.3, last_accessed=base)
    b = MemoryItem(content="b", importance=0.9, last_accessed=base)
    c = MemoryItem(content="c", importance=0.6, last_accessed=base)
    decay = MemoryDecay()
    ranked = decay.rank([a, b, c])
    contents = [it.content for it, _ in ranked]
    assert contents == ["b", "c", "a"]


def test_touch_updates_last_accessed() -> None:
    item = MemoryItem(content="x")
    before = item.access_count
    item.touch()
    assert item.access_count == before + 1
