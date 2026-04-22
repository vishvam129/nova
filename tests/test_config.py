"""Tests for nova.config."""

from __future__ import annotations

from pathlib import Path

from nova.config import Config, load_config


def test_defaults_when_no_file(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    missing = tmp_path / "nope.toml"
    monkeypatch.delenv("NOVA_BRAIN__LOCAL_MODEL", raising=False)
    cfg = load_config(missing)
    assert isinstance(cfg, Config)
    assert cfg.voice.wake_word == "hey_nova"
    assert cfg.brain.local_backend == "ollama"
    assert cfg.server.port == 8765


def test_toml_overrides_defaults(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("NOVA_BRAIN__LOCAL_MODEL", raising=False)
    toml = tmp_path / "config.toml"
    toml.write_text(
        """
[voice]
wake_word = "nova"

[brain]
local_model = "phi4:14b"

[server]
port = 9000
"""
    )
    cfg = load_config(toml)
    assert cfg.voice.wake_word == "nova"
    assert cfg.brain.local_model == "phi4:14b"
    assert cfg.server.port == 9000


def test_env_overrides_toml(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    toml = tmp_path / "config.toml"
    toml.write_text('[brain]\nlocal_model = "phi4:14b"\n')
    monkeypatch.setenv("NOVA_BRAIN__LOCAL_MODEL", "qwen3:8b")
    cfg = load_config(toml)
    assert cfg.brain.local_model == "qwen3:8b"
