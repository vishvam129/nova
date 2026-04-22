"""Embedding-based tool filtering.

Keeps only the top-K tools most semantically relevant to the current
user query in the LLM's context window. Critical once the MCP plane
has hundreds of tools — sending every schema every turn wastes tokens
and degrades tool selection accuracy.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from nova.brain.agent import Tool
from nova.tools.mcp import McpTool


@runtime_checkable
class Embedder(Protocol):
    dim: int

    def embed(self, text: str) -> list[float]: ...


class HashingEmbedder:
    """Zero-dependency bag-of-tokens embedder using the hashing trick.

    Cheap, deterministic, and lossy — useful as a fallback or for tests.
    Real deployments should register ``sentence-transformers`` or a
    cloud embedder (OpenAI, Voyage, Cohere).
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in text.lower().split():
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)  # noqa: S324
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("vector length mismatch")
    return sum(x * y for x, y in zip(a, b, strict=True))


def _describe(tool: Tool | McpTool | dict[str, Any]) -> tuple[str, str]:
    if isinstance(tool, (Tool, McpTool)):
        return tool.name, tool.description
    return tool["name"], tool.get("description", "")


@dataclass
class ToolFilter:
    embedder: Embedder
    _index: list[tuple[str, list[float], Any]] = field(default_factory=list)

    def index(self, tools: Sequence[Tool | McpTool | dict[str, Any]]) -> None:
        self._index = []
        for t in tools:
            name, desc = _describe(t)
            vec = self.embedder.embed(f"{name}: {desc}")
            self._index.append((name, vec, t))

    def top_k(self, query: str, k: int = 20) -> list[Any]:
        if not self._index:
            return []
        q_vec = self.embedder.embed(query)
        scored = sorted(self._index, key=lambda row: cosine(q_vec, row[1]), reverse=True)
        return [row[2] for row in scored[:k]]


__all__ = [
    "Embedder",
    "HashingEmbedder",
    "ToolFilter",
    "cosine",
]
