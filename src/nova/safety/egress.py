"""Network egress allow-list.

Wraps URL/host checks so tools that issue HTTP requests can be gated
by a sysadmin-controlled allow-list.  Supports exact hosts, suffix
wildcards (``*.example.com``), and IP-address allow.
"""

from __future__ import annotations

import ipaddress
import urllib.parse
from dataclasses import dataclass, field


class EgressBlocked(RuntimeError):
    """Raised by ``EgressPolicy.check`` when a destination is not allowed."""

    def __init__(self, host: str) -> None:
        super().__init__(f"egress to {host!r} blocked by policy")
        self.host = host


@dataclass
class EgressPolicy:
    """Allow-list of hostnames / suffix patterns / IPs."""

    allowed: set[str] = field(default_factory=set)
    default_deny: bool = True

    def add(self, pattern: str) -> None:
        self.allowed.add(pattern.lower().strip())

    def remove(self, pattern: str) -> None:
        self.allowed.discard(pattern.lower().strip())

    def is_allowed(self, host_or_url: str) -> bool:
        host = self._extract_host(host_or_url)
        if not host:
            return not self.default_deny
        host = host.lower()
        if host in self.allowed:
            return True
        for pattern in self.allowed:
            if pattern.startswith("*.") and host.endswith(pattern[1:]):
                return True
            if pattern == "*":
                return True
        if self._is_loopback(host):
            return "127.0.0.0/8" in self.allowed or "loopback" in self.allowed
        return not self.default_deny

    def check(self, host_or_url: str) -> None:
        if not self.is_allowed(host_or_url):
            raise EgressBlocked(self._extract_host(host_or_url) or host_or_url)

    @staticmethod
    def _extract_host(value: str) -> str:
        if "://" in value:
            parsed = urllib.parse.urlparse(value)
            return parsed.hostname or ""
        return value.split("/", 1)[0].split(":", 1)[0]

    @staticmethod
    def _is_loopback(host: str) -> bool:
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return host in {"localhost"}


__all__ = ["EgressBlocked", "EgressPolicy"]
