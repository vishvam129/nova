"""Built-in web search MCP: SearxNG default, Brave Search API optional.

Both backends share ``WebSearchBackend`` and return ``SearchResult``.
The MCP-facing surface is ``WebSearchToolHandler.call("search", query=...)``.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    score: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "score": self.score,
        }


class WebSearchBackend(Protocol):
    def search(self, query: str, *, limit: int = 10) -> Iterable[SearchResult]: ...


@dataclass
class SearxngBackend:
    """Self-hosted SearxNG instance (privacy-preserving meta-search)."""

    base_url: str = "https://searx.be"
    timeout_s: float = 5.0

    def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        params = urllib.parse.urlencode({"q": query, "format": "json"})
        url = f"{self.base_url.rstrip('/')}/search?{params}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            return []
        return _parse_searxng(payload, limit=limit)


@dataclass
class BraveSearchBackend:
    """Brave Search API (https://search.brave.com/api)."""

    api_key: str
    timeout_s: float = 5.0
    extra_headers: dict[str, str] = field(default_factory=dict)

    def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(
            {"q": query, "count": limit}
        )
        headers = {
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json",
            **self.extra_headers,
        }
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            return []
        return _parse_brave(payload, limit=limit)


def _parse_searxng(payload: dict[str, Any], *, limit: int) -> list[SearchResult]:
    results = payload.get("results", [])
    out: list[SearchResult] = []
    for r in results[:limit]:
        out.append(
            SearchResult(
                title=str(r.get("title", "")),
                url=str(r.get("url", "")),
                snippet=str(r.get("content", "")),
                score=float(r.get("score", 0.0)),
            )
        )
    return out


def _parse_brave(payload: dict[str, Any], *, limit: int) -> list[SearchResult]:
    web = payload.get("web", {})
    results = web.get("results", [])
    out: list[SearchResult] = []
    for r in results[:limit]:
        out.append(
            SearchResult(
                title=str(r.get("title", "")),
                url=str(r.get("url", "")),
                snippet=str(r.get("description", "")),
            )
        )
    return out


@dataclass
class WebSearchToolHandler:
    backend: WebSearchBackend

    def call(self, tool: str, **kwargs: Any) -> object:
        if tool != "search":
            raise ValueError(f"unknown web-search tool: {tool!r}")
        query = str(kwargs.get("query", ""))
        if not query:
            raise ValueError("search requires non-empty 'query'")
        limit = int(kwargs.get("limit", 10))
        return [r.to_dict() for r in self.backend.search(query, limit=limit)]


__all__ = [
    "BraveSearchBackend",
    "SearchResult",
    "SearxngBackend",
    "WebSearchBackend",
    "WebSearchToolHandler",
]
