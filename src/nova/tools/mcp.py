"""Model Context Protocol (MCP) client.

Supports three transports:
  * ``stdio``           — spawn an MCP server as a subprocess
  * ``http-sse``        — legacy server-sent-events transport
  * ``streamable-http`` — 2025+ Streamable HTTP transport (recommended)

The MCP SDK (``mcp`` on PyPI) is imported lazily so the hard dependency
is only required at connect time.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

TransportKind = Literal["stdio", "http-sse", "streamable-http"]


@dataclass(frozen=True, slots=True)
class McpTool:
    name: str
    description: str
    input_schema: dict[str, Any]


@runtime_checkable
class McpTransport(Protocol):
    kind: TransportKind

    async def connect(self) -> None: ...

    async def call(self, method: str, params: dict[str, Any]) -> Any: ...

    async def close(self) -> None: ...


@dataclass
class StdioTransport:
    command: list[str]
    kind: TransportKind = "stdio"
    env: dict[str, str] = field(default_factory=dict)
    _session: Any = field(default=None, init=False, repr=False)

    async def connect(self) -> None:
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        params = StdioServerParameters(command=self.command[0], args=self.command[1:], env=self.env)
        self._session = stdio_client(params)
        read, write = await self._session.__aenter__()
        client = ClientSession(read, write)
        await client.__aenter__()
        await client.initialize()
        self._session = client

    async def call(self, method: str, params: dict[str, Any]) -> Any:
        return await self._session.send_request(method, params)

    async def close(self) -> None:
        if self._session is not None:
            await self._session.__aexit__(None, None, None)
            self._session = None


@dataclass
class HttpSseTransport:
    url: str
    kind: TransportKind = "http-sse"
    _session: Any = field(default=None, init=False, repr=False)

    async def connect(self) -> None:
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        cm = sse_client(self.url)
        read, write = await cm.__aenter__()
        client = ClientSession(read, write)
        await client.__aenter__()
        await client.initialize()
        self._session = client

    async def call(self, method: str, params: dict[str, Any]) -> Any:
        return await self._session.send_request(method, params)

    async def close(self) -> None:
        if self._session is not None:
            await self._session.__aexit__(None, None, None)
            self._session = None


@dataclass
class StreamableHttpTransport:
    url: str
    kind: TransportKind = "streamable-http"
    headers: dict[str, str] = field(default_factory=dict)
    _session: Any = field(default=None, init=False, repr=False)

    async def connect(self) -> None:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        cm = streamablehttp_client(self.url, headers=self.headers)
        read, write, _ = await cm.__aenter__()
        client = ClientSession(read, write)
        await client.__aenter__()
        await client.initialize()
        self._session = client

    async def call(self, method: str, params: dict[str, Any]) -> Any:
        return await self._session.send_request(method, params)

    async def close(self) -> None:
        if self._session is not None:
            await self._session.__aexit__(None, None, None)
            self._session = None


@dataclass
class McpClient:
    """High-level wrapper over any ``McpTransport``."""

    transport: McpTransport
    _tools: list[McpTool] = field(default_factory=list, init=False)

    async def connect(self) -> None:
        await self.transport.connect()

    async def list_tools(self) -> list[McpTool]:
        raw = await self.transport.call("tools/list", {})
        items = raw if isinstance(raw, list) else raw.get("tools", [])
        self._tools = [
            McpTool(
                name=item["name"],
                description=item.get("description", ""),
                input_schema=item.get("inputSchema", {"type": "object"}),
            )
            for item in items
        ]
        return list(self._tools)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return await self.transport.call("tools/call", {"name": name, "arguments": arguments})

    async def close(self) -> None:
        await self.transport.close()


_TRANSPORT_BUILDERS: dict[str, Callable[..., McpTransport]] = {
    "stdio": lambda **kw: StdioTransport(**kw),
    "http-sse": lambda **kw: HttpSseTransport(**kw),
    "streamable-http": lambda **kw: StreamableHttpTransport(**kw),
}


def create_transport(kind: TransportKind, **kwargs: object) -> McpTransport:
    if kind not in _TRANSPORT_BUILDERS:
        raise ValueError(f"unknown MCP transport: {kind!r}")
    return _TRANSPORT_BUILDERS[kind](**kwargs)
