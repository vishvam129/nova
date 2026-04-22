"""Tests for cloud fallback configuration."""

from __future__ import annotations

import pytest

from nova.brain.cloud import (
    CLAUDE_OPUS_MODEL,
    DEFAULT_PROVIDERS,
    cloud_available,
    create_claude_opus,
    create_cloud_backend,
    first_available_provider,
)


def _clear(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    for p in DEFAULT_PROVIDERS:
        monkeypatch.delenv(p.env_var, raising=False)


def test_cloud_available_false_without_keys(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear(monkeypatch)
    assert cloud_available() is False


def test_cloud_available_true_with_anthropic(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert cloud_available() is True


def test_first_available_picks_claude_first(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("OPENAI_API_KEY", "y")
    p = first_available_provider()
    assert p is not None
    assert p.backend == "claude"


def test_create_cloud_backend_raises_when_no_keys(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear(monkeypatch)
    with pytest.raises(RuntimeError, match="no cloud LLM API key"):
        create_cloud_backend()


def test_create_claude_opus_requires_key(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear(monkeypatch)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        create_claude_opus()


def test_claude_opus_model_is_default() -> None:
    assert CLAUDE_OPUS_MODEL == "claude-opus-4-7"


def test_create_cloud_backend_returns_llm_when_key_present(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    # Don't actually call the network; just verify construction succeeds.
    backend = create_cloud_backend()
    assert backend.model == CLAUDE_OPUS_MODEL
