"""Tests for default model picker."""

from __future__ import annotations

from nova.brain.models import (
    DEFAULT_MODELS,
    ModelSpec,
    detect_ram_gb,
    pick_model,
    recommended_for_host,
)


def test_pick_model_at_8gb_picks_small_tools_model() -> None:
    m = pick_model("tools", 8)
    assert m.min_ram_gb <= 8
    assert m.tag == "gemma3:4b"


def test_pick_model_at_16gb_upgrades_tools_model() -> None:
    m = pick_model("tools", 16)
    assert m.params_b >= 12.0  # gemma3:12b


def test_pick_model_at_64gb_picks_largest_reasoning() -> None:
    m = pick_model("reasoning", 64)
    assert m.tag == "llama3.3:70b"


def test_pick_model_unknown_task_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        pick_model("unknown", 16)  # type: ignore[arg-type]


def test_pick_model_falls_back_when_nothing_fits() -> None:
    # 2GB RAM — nothing fits, should return smallest for task.
    m = pick_model("reasoning", 2)
    assert m.min_ram_gb > 2  # doesn't fit, but smallest of the category


def test_detect_ram_gb_positive() -> None:
    assert detect_ram_gb() >= 1


def test_recommended_for_host_covers_all_tasks() -> None:
    rec = recommended_for_host()
    for task in ("chat", "tools", "reasoning", "coding", "vision"):
        assert task in rec
        assert isinstance(rec[task], ModelSpec)


def test_default_models_immutable_tuple() -> None:
    assert isinstance(DEFAULT_MODELS, tuple)
    assert len(DEFAULT_MODELS) >= 6
