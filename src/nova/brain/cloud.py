"""Cloud LLM fallback configuration.

Defaults to Claude Opus 4.7 — the 2026 best-in-class choice for
computer-use and hard reasoning. If no API key is configured, the
``cloud_available`` flag is False and the router must fall back to a
local model.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from nova.brain.llm import LlmBackend, create_llm

CLAUDE_OPUS_MODEL = "claude-opus-4-7"
CLAUDE_HAIKU_MODEL = "claude-haiku-4-5"
OPENAI_FALLBACK_MODEL = "gpt-4o"


@dataclass(frozen=True, slots=True)
class CloudProvider:
    backend: str
    model: str
    env_var: str


DEFAULT_PROVIDERS: tuple[CloudProvider, ...] = (
    CloudProvider(backend="claude", model=CLAUDE_OPUS_MODEL, env_var="ANTHROPIC_API_KEY"),
    CloudProvider(backend="openai", model=OPENAI_FALLBACK_MODEL, env_var="OPENAI_API_KEY"),
    CloudProvider(backend="gemini", model="gemini-2.5-pro", env_var="GEMINI_API_KEY"),
)


def cloud_available(providers: tuple[CloudProvider, ...] = DEFAULT_PROVIDERS) -> bool:
    return any(os.environ.get(p.env_var) for p in providers)


def first_available_provider(
    providers: tuple[CloudProvider, ...] = DEFAULT_PROVIDERS,
) -> CloudProvider | None:
    for p in providers:
        if os.environ.get(p.env_var):
            return p
    return None


def create_cloud_backend(
    providers: tuple[CloudProvider, ...] = DEFAULT_PROVIDERS,
    model: str | None = None,
) -> LlmBackend:
    """Return a ready-to-use cloud LLM backend or raise if none configured."""
    p = first_available_provider(providers)
    if p is None:
        keys = ", ".join(prov.env_var for prov in providers)
        raise RuntimeError(f"no cloud LLM API key set; expected one of: {keys}")
    return create_llm(p.backend, model=model or p.model)


def create_claude_opus() -> LlmBackend:
    """Convenience constructor: Claude Opus 4.7. Raises if no API key."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return create_llm("claude", model=CLAUDE_OPUS_MODEL)
