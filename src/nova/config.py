"""Typed configuration loader with TOML + env var overrides."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_config_path() -> Path:
    """Resolve ~/.config/nova/config.toml respecting XDG_CONFIG_HOME."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "nova" / "config.toml"


def default_data_dir() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "nova"


class VoiceConfig(BaseModel):
    wake_word: str = "hey_nova"
    stt_backend: str = "moonshine"
    tts_backend: str = "kokoro"
    tts_voice: str = "af_sky"
    tts_ttfs_budget_ms: int = 300


class BrainConfig(BaseModel):
    local_backend: str = "ollama"
    local_model: str = "gemma3:4b"
    cloud_backend: str | None = None
    cloud_model: str | None = None
    daily_cost_cap_usd: float = 1.0


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765


class Config(BaseSettings):
    """Top-level Nova config.

    Load precedence (highest first): env vars, TOML file, defaults.
    Env vars use the prefix ``NOVA_`` and ``__`` as nested delimiter,
    e.g. ``NOVA_BRAIN__LOCAL_MODEL=phi4:14b``.
    """

    model_config = SettingsConfigDict(
        env_prefix="NOVA_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    data_dir: Path = Field(default_factory=default_data_dir)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    brain: BrainConfig = Field(default_factory=BrainConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        return tomllib.load(f)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _env_overrides(prefix: str = "NOVA_", delim: str = "__") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in os.environ.items():
        if not key.startswith(prefix):
            continue
        parts = key[len(prefix) :].lower().split(delim)
        cursor = out
        for p in parts[:-1]:
            cursor = cursor.setdefault(p, {})
        cursor[parts[-1]] = val
    return out


def load_config(path: Path | None = None) -> Config:
    """Load config from TOML if present, then apply env overrides.

    Missing file falls back to defaults. Env vars always take precedence.
    """
    toml_path = path or default_config_path()
    file_data: dict[str, Any] = {}
    if toml_path.is_file():
        file_data = _read_toml(toml_path)
    merged = _deep_merge(file_data, _env_overrides())
    return Config(**merged)
