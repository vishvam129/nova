"""Curated default model set for Nova's brain.

Maps task categories (chat, tool calling, reasoning, coding) to
recommended local Ollama model tags plus minimum-RAM hints so the router
can pick a model that actually fits the user's hardware.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

Task = Literal["chat", "tools", "reasoning", "coding", "vision"]


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """Recommendation for a task on a given RAM tier."""

    tag: str
    task: Task
    min_ram_gb: int
    context_window: int
    params_b: float
    note: str = ""


DEFAULT_MODELS: tuple[ModelSpec, ...] = (
    # Light tier (8GB RAM): fast and cheap.
    ModelSpec("gemma3:4b", "tools", 8, 8192, 4.3, "Gemma 3 4B: native tool calling"),
    ModelSpec("qwen3:4b", "chat", 8, 32768, 4.0, "Qwen 3 4B: fast chat"),
    ModelSpec("qwen3-coder:7b", "coding", 12, 32768, 7.0, "Qwen 3 Coder 7B"),
    # Standard tier (16GB RAM): balanced quality.
    ModelSpec("phi4:14b", "reasoning", 16, 16384, 14.0, "Phi-4: strong on MATH/GPQA"),
    ModelSpec("qwen3:8b", "chat", 16, 32768, 8.0, "Qwen 3 8B: better coherence"),
    ModelSpec("gemma3:12b", "tools", 16, 128000, 12.0, "Gemma 3 12B: long context"),
    # Heavy tier (32GB+ RAM): maximum quality local.
    ModelSpec("qwen3:32b", "reasoning", 32, 32768, 32.0, "Qwen 3 32B"),
    ModelSpec("llama3.3:70b", "reasoning", 64, 128000, 70.0, "Llama 3.3 70B"),
    # Vision.
    ModelSpec("llama3.2-vision:11b", "vision", 16, 128000, 11.0, "Llama 3.2 Vision"),
)


def pick_model(task: Task, ram_gb: int, models: Iterable[ModelSpec] = DEFAULT_MODELS) -> ModelSpec:
    """Return the largest model for ``task`` that fits within ``ram_gb``.

    Falls back to the smallest model for the task if nothing fits
    (rare — only when ram_gb is unrealistically low).
    """
    candidates = [m for m in models if m.task == task]
    if not candidates:
        raise ValueError(f"no model registered for task {task!r}")
    fitting = [m for m in candidates if m.min_ram_gb <= ram_gb]
    if fitting:
        return max(fitting, key=lambda m: m.params_b)
    return min(candidates, key=lambda m: m.params_b)


def detect_ram_gb() -> int:
    """Return total system RAM in GB (best-effort, never raises)."""
    try:
        import psutil

        return max(1, int(psutil.virtual_memory().total // (1024**3)))
    except Exception:
        return 8


def recommended_for_host() -> dict[Task, ModelSpec]:
    ram = detect_ram_gb()
    return {
        "chat": pick_model("chat", ram),
        "tools": pick_model("tools", ram),
        "reasoning": pick_model("reasoning", ram),
        "coding": pick_model("coding", ram),
        "vision": pick_model("vision", ram),
    }
