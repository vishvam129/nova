"""Tests for MCP client (transport-free, using a fake transport)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from nova.tools.mcp import McpClient, McpTool, create_transport


class FakeTransport:
    kind = "stdio"

    def __init__(self, tools: list[dict[str, Any]]) -> None:
        self.tools = tools
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.connected = False
        self.closed = False

    async def connect(self) -> None:
        self.connected = True

    async def call(self, method: str, params: dict[str, Any]) -> Any:
        self.calls.append((method, params))
        if method == "tools/list":
            return {"tools": self.tools}
        if method == "tools/call":
            return {"result": f"called {params['name']} with {params['arguments']}"}
        return None

    async def close(self) -> None:
        self.closed = True


def test_list_tools_parses_tool_specs() -> None:
    transport = FakeTransport(
        [
            {"name": "echo", "description": "Echoes text", "inputSchema": {"type": "object"}},
            {"name": "add", "description": "Adds numbers"},
        ]
    )
    client = McpClient(transport=transport)
    asyncio.run(client.connect())
    tools = asyncio.run(client.list_tools())
    assert len(tools) == 2
    assert all(isinstance(t, McpTool) for t in tools)
    assert tools[0].name == "echo"
    assert tools[1].input_schema == {"type": "object"}


def test_call_tool_forwards_arguments() -> None:
    transport = FakeTransport([])
    client = McpClient(transport=transport)
    asyncio.run(client.connect())
    result = asyncio.run(client.call_tool("echo", {"text": "hi"}))
    assert transport.calls[0] == ("tools/call", {"name": "echo", "arguments": {"text": "hi"}})
    assert "called echo" in result["result"]


def test_create_transport_unknown_kind_raises() -> None:
    with pytest.raises(ValueError):
        create_transport("carrier-pigeon")  # type: ignore[arg-type]


def test_create_transport_stdio_returns_right_kind() -> None:
    t = create_transport("stdio", command=["echo", "hi"])
    assert t.kind == "stdio"


def test_create_transport_streamable_http_returns_right_kind() -> None:
    t = create_transport("streamable-http", url="https://example.com/mcp")
    assert t.kind == "streamable-http"


def test_close_propagates_to_transport() -> None:
    transport = FakeTransport([])
    client = McpClient(transport=transport)
    asyncio.run(client.connect())
    asyncio.run(client.close())
    assert transport.closed is True
