"""Tests for embedding-based tool filtering."""

from __future__ import annotations

from nova.brain.agent import Tool
from nova.tools.filter import HashingEmbedder, ToolFilter, cosine
from nova.tools.mcp import McpTool


def _tool(name: str, desc: str) -> Tool:
    return Tool(name=name, description=desc, schema={"type": "object"}, handler=lambda _a: "ok")


def test_cosine_identity() -> None:
    v = HashingEmbedder(dim=32).embed("hello world")
    assert abs(cosine(v, v) - 1.0) < 1e-9


def test_cosine_rejects_length_mismatch() -> None:
    import pytest

    with pytest.raises(ValueError):
        cosine([1.0], [1.0, 0.0])


def test_hashing_embedder_is_deterministic() -> None:
    e = HashingEmbedder(dim=64)
    assert e.embed("hello there") == e.embed("hello there")


def test_top_k_picks_most_relevant() -> None:
    tools = [
        _tool("send_sms", "send a text message to a phone contact"),
        _tool("play_music", "start playing songs in a music app"),
        _tool("set_volume", "change the audio output volume"),
        _tool("open_browser", "open a URL in the default web browser"),
    ]
    f = ToolFilter(embedder=HashingEmbedder(dim=512))
    f.index(tools)
    picks = f.top_k("message contact phone text", k=1)
    assert picks[0].name == "send_sms"


def test_top_k_respects_k() -> None:
    tools = [_tool(f"t{i}", f"tool number {i} does things") for i in range(10)]
    f = ToolFilter(embedder=HashingEmbedder(dim=256))
    f.index(tools)
    assert len(f.top_k("anything", k=3)) == 3


def test_top_k_empty_when_not_indexed() -> None:
    f = ToolFilter(embedder=HashingEmbedder(dim=16))
    assert f.top_k("hi", k=5) == []


def test_filter_accepts_mcp_tools() -> None:
    tools = [
        McpTool(name="weather", description="get current weather", input_schema={}),
        McpTool(name="alarm", description="set a morning alarm clock", input_schema={}),
    ]
    f = ToolFilter(embedder=HashingEmbedder(dim=256))
    f.index(tools)
    picks = f.top_k("what is the weather", k=1)
    assert picks[0].name == "weather"


def test_filter_accepts_dict_tools() -> None:
    raw = [
        {"name": "note_add", "description": "create a new note in obsidian vault"},
        {"name": "run_shell", "description": "execute a shell command on the host"},
    ]
    f = ToolFilter(embedder=HashingEmbedder(dim=256))
    f.index(raw)
    picks = f.top_k("write a note about my day", k=1)
    assert picks[0]["name"] == "note_add"
