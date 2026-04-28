"""Tests for nova.integrations.web_search."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nova.integrations.web_search import (
    BraveSearchBackend,
    SearchResult,
    SearxngBackend,
    WebSearchToolHandler,
    _parse_brave,
    _parse_searxng,
)


class _FakeBackend:
    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results
        self.last_query = ""
        self.last_limit = 0

    def search(self, query: str, *, limit: int = 10):
        self.last_query = query
        self.last_limit = limit
        return self.results


def _searxng_payload() -> dict[str, object]:
    return {
        "results": [
            {"title": "Result 1", "url": "https://a.com", "content": "first", "score": 0.9},
            {"title": "Result 2", "url": "https://b.com", "content": "second", "score": 0.5},
        ]
    }


def _brave_payload() -> dict[str, object]:
    return {
        "web": {
            "results": [
                {"title": "Brave 1", "url": "https://x.com", "description": "first"},
            ]
        }
    }


def test_search_result_dict() -> None:
    r = SearchResult(title="t", url="u", snippet="s", score=0.5)
    assert r.to_dict()["title"] == "t"


def test_parse_searxng_limits() -> None:
    out = _parse_searxng(_searxng_payload(), limit=1)
    assert len(out) == 1
    assert out[0].title == "Result 1"


def test_parse_searxng_score() -> None:
    out = _parse_searxng(_searxng_payload(), limit=10)
    assert out[0].score == 0.9


def test_parse_brave() -> None:
    out = _parse_brave(_brave_payload(), limit=10)
    assert len(out) == 1
    assert out[0].title == "Brave 1"


def test_parse_brave_empty() -> None:
    assert _parse_brave({}, limit=10) == []


def test_searxng_backend_handles_network_error() -> None:
    b = SearxngBackend(base_url="https://x")
    with patch("nova.integrations.web_search.urllib.request.urlopen", side_effect=OSError):
        assert b.search("foo") == []


def test_searxng_backend_parses_response() -> None:
    b = SearxngBackend(base_url="https://x")
    fake = MagicMock()
    fake.read.return_value = b'{"results":[{"title":"T","url":"U","content":"C","score":1.0}]}'
    fake.__enter__ = MagicMock(return_value=fake)
    fake.__exit__ = MagicMock(return_value=False)
    with patch("nova.integrations.web_search.urllib.request.urlopen", return_value=fake):
        out = b.search("foo")
    assert len(out) == 1
    assert out[0].title == "T"


def test_brave_backend_handles_error() -> None:
    b = BraveSearchBackend(api_key="k")
    with patch("nova.integrations.web_search.urllib.request.urlopen", side_effect=OSError):
        assert b.search("foo") == []


def test_handler_dispatches_search() -> None:
    backend = _FakeBackend([SearchResult(title="t", url="u")])
    h = WebSearchToolHandler(backend=backend)
    out = h.call("search", query="hello", limit=5)
    assert isinstance(out, list)
    assert backend.last_query == "hello"
    assert backend.last_limit == 5


def test_handler_empty_query_raises() -> None:
    h = WebSearchToolHandler(backend=_FakeBackend([]))
    with pytest.raises(ValueError):
        h.call("search", query="")


def test_handler_unknown_tool() -> None:
    h = WebSearchToolHandler(backend=_FakeBackend([]))
    with pytest.raises(ValueError):
        h.call("bogus")
