"""Browser extension MCP: in-page DOM access with per-site permission.

The browser extension speaks the WebSocket transport defined here.  It
ships per-site permissions so a tool call to ``dom.query`` on
``mail.google.com`` does *not* automatically work on ``bank.com``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urlparse


class Grant(StrEnum):
    DENIED = "denied"
    READ = "read"
    READ_WRITE = "read_write"


@dataclass
class SitePermissions:
    """Per-origin DOM access policy."""

    grants: dict[str, Grant] = field(default_factory=dict)

    def set(self, origin: str, grant: Grant) -> None:
        self.grants[_normalize(origin)] = grant

    def grant(self, origin: str) -> Grant:
        return self.grants.get(_normalize(origin), Grant.DENIED)

    def can_read(self, origin: str) -> bool:
        return self.grant(origin) in (Grant.READ, Grant.READ_WRITE)

    def can_write(self, origin: str) -> bool:
        return self.grant(origin) is Grant.READ_WRITE

    def revoke(self, origin: str) -> bool:
        return self.grants.pop(_normalize(origin), None) is not None

    def origins(self) -> Iterable[str]:
        return sorted(self.grants.keys())


def _normalize(value: str) -> str:
    if "://" in value:
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        if parsed.port and parsed.port not in (80, 443):
            return f"{host}:{parsed.port}"
        return host
    return value.lower().split("/", 1)[0]


@dataclass(frozen=True, slots=True)
class DomCall:
    tool: str  # 'dom.query' | 'dom.click' | 'dom.fill' | 'dom.screenshot'
    origin: str
    args: dict[str, object] = field(default_factory=dict)
    call_id: str = ""

    def encode(self) -> str:
        return json.dumps(
            {
                "type": "browser_dom_call",
                "tool": self.tool,
                "origin": self.origin,
                "args": dict(self.args),
                "call_id": self.call_id,
            }
        )


class PermissionDenied(RuntimeError):
    def __init__(self, origin: str, tool: str) -> None:
        super().__init__(f"{tool!r} on {origin!r} not permitted")
        self.origin = origin
        self.tool = tool


_WRITE_TOOLS = frozenset({"dom.click", "dom.fill", "dom.set_attr"})
_READ_TOOLS = frozenset({"dom.query", "dom.screenshot", "dom.text"})


@dataclass
class BrowserExtensionGate:
    """Validates DomCall requests against the SitePermissions policy."""

    permissions: SitePermissions

    def check(self, call: DomCall) -> None:
        origin = call.origin
        if call.tool in _WRITE_TOOLS:
            if not self.permissions.can_write(origin):
                raise PermissionDenied(origin, call.tool)
            return
        if call.tool in _READ_TOOLS:
            if not self.permissions.can_read(origin):
                raise PermissionDenied(origin, call.tool)
            return
        raise PermissionDenied(origin, call.tool)


__all__ = [
    "BrowserExtensionGate",
    "DomCall",
    "Grant",
    "PermissionDenied",
    "SitePermissions",
]
