"""Persistent registry of MCP servers.

Stores a list of server entries in ``<data_dir>/mcp_servers.json``.
CLI and GUI both mutate the registry through this module so the
on-disk format stays a single source of truth.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from nova.tools.mcp import McpTransport, TransportKind, create_transport


@dataclass(slots=True)
class McpServerEntry:
    name: str
    kind: TransportKind
    enabled: bool = True
    command: list[str] = field(default_factory=list)
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)

    def to_transport(self) -> McpTransport:
        if self.kind == "stdio":
            return create_transport("stdio", command=self.command, env=self.env)
        if self.kind == "http-sse":
            assert self.url is not None
            return create_transport("http-sse", url=self.url)
        if self.kind == "streamable-http":
            assert self.url is not None
            return create_transport("streamable-http", url=self.url, headers=self.headers)
        raise ValueError(f"unsupported kind: {self.kind!r}")


@dataclass
class McpRegistry:
    path: Path
    _servers: dict[str, McpServerEntry] = field(default_factory=dict)

    def load(self) -> None:
        if not self.path.is_file():
            self._servers = {}
            return
        data = json.loads(self.path.read_text())
        self._servers = {e["name"]: McpServerEntry(**e) for e in data.get("servers", [])}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {"servers": [asdict(e) for e in self._servers.values()]},
                indent=2,
            )
        )

    def add(self, entry: McpServerEntry) -> None:
        if entry.name in self._servers:
            raise ValueError(f"server {entry.name!r} already exists")
        self._servers[entry.name] = entry
        self.save()

    def remove(self, name: str) -> None:
        self._servers.pop(name, None)
        self.save()

    def update(self, entry: McpServerEntry) -> None:
        if entry.name not in self._servers:
            raise ValueError(f"server {entry.name!r} not found")
        self._servers[entry.name] = entry
        self.save()

    def enable(self, name: str, on: bool = True) -> None:
        if name not in self._servers:
            raise ValueError(f"server {name!r} not found")
        self._servers[name].enabled = on
        self.save()

    def get(self, name: str) -> McpServerEntry | None:
        return self._servers.get(name)

    def all(self) -> list[McpServerEntry]:
        return list(self._servers.values())

    def enabled(self) -> list[McpServerEntry]:
        return [e for e in self._servers.values() if e.enabled]

    def names(self) -> Iterable[str]:
        return tuple(self._servers)


def registry_for(data_dir: Path) -> McpRegistry:
    reg = McpRegistry(path=data_dir / "mcp_servers.json")
    reg.load()
    return reg


__all__ = ["McpRegistry", "McpServerEntry", "registry_for"]
