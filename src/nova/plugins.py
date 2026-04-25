"""Plugin discovery via Python entry_points.

Third-party packages register Nova plugins in their ``pyproject.toml``::

    [project.entry-points."nova.tools"]
    my_tool = "my_package.nova_plugin:MyTool"

    [project.entry-points."nova.mcp_servers"]
    my_mcp = "my_package.nova_plugin:MyMCPFactory"

    [project.entry-points."nova.agents"]
    my_agent = "my_package.nova_plugin:MyAgent"

Nova discovers them at startup via ``PluginRegistry.discover()``.  Plugins
are loaded lazily — the entry point object is stored and the actual import
happens only when ``.load()`` is called, so a broken plugin can't crash the
whole process on startup.
"""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass, field
from typing import Any

# Entry-point group names Nova recognises
TOOL_GROUP = "nova.tools"
MCP_GROUP = "nova.mcp_servers"
AGENT_GROUP = "nova.agents"

_ALL_GROUPS = (TOOL_GROUP, MCP_GROUP, AGENT_GROUP)


@dataclass
class PluginEntry:
    """Metadata for a single discovered plugin (not yet loaded)."""

    name: str
    group: str
    dist_name: str
    dist_version: str
    _ep: importlib.metadata.EntryPoint = field(repr=False)

    def load(self) -> Any:
        """Import and return the plugin class/factory.

        Raises ``ImportError`` or ``AttributeError`` if the entry point is
        broken — callers should catch and log, not crash.
        """
        return self._ep.load()

    @property
    def qualified_name(self) -> str:
        return f"{self.group}:{self.name}"


class PluginRegistry:
    """Discovers and caches Nova plugins from installed packages."""

    def __init__(self) -> None:
        self._entries: dict[str, list[PluginEntry]] = {g: [] for g in _ALL_GROUPS}

    def discover(self, extra_groups: list[str] | None = None) -> None:
        """Scan installed entry points and populate the registry.

        Call once at process start.  Safe to call again — clears previous
        results so hot-reloading dev workflows work.

        Args:
            extra_groups: Additional group names to scan beyond the built-ins.
        """
        self._entries = {g: [] for g in _ALL_GROUPS}
        groups = list(_ALL_GROUPS) + (extra_groups or [])
        for group in groups:
            if group not in self._entries:
                self._entries[group] = []
            for ep in importlib.metadata.entry_points(group=group):
                dist = ep.dist
                dist_name = dist.name if dist else "unknown"
                dist_version = dist.version if dist else "0.0.0"
                self._entries[group].append(
                    PluginEntry(
                        name=ep.name,
                        group=group,
                        dist_name=dist_name,
                        dist_version=dist_version,
                        _ep=ep,
                    )
                )

    def list(self, group: str) -> list[PluginEntry]:
        """Return all discovered plugins for *group*."""
        return list(self._entries.get(group, []))

    def get(self, group: str, name: str) -> PluginEntry | None:
        """Look up a plugin by group + name."""
        for entry in self._entries.get(group, []):
            if entry.name == name:
                return entry
        return None

    def load_all(self, group: str) -> list[tuple[PluginEntry, Any]]:
        """Load every plugin in *group*, skipping broken ones.

        Returns a list of ``(entry, loaded_object)`` pairs.
        Broken entries are silently skipped; callers that need to know about
        failures should iterate ``list()`` and call ``entry.load()`` manually.
        """
        results: list[tuple[PluginEntry, Any]] = []
        for entry in self.list(group):
            try:
                obj = entry.load()
            except Exception:  # noqa: BLE001
                continue
            results.append((entry, obj))
        return results

    @property
    def tool_plugins(self) -> list[PluginEntry]:
        return self.list(TOOL_GROUP)

    @property
    def mcp_plugins(self) -> list[PluginEntry]:
        return self.list(MCP_GROUP)

    @property
    def agent_plugins(self) -> list[PluginEntry]:
        return self.list(AGENT_GROUP)


# Module-level singleton — importers can use this directly
registry = PluginRegistry()


__all__ = [
    "AGENT_GROUP",
    "MCP_GROUP",
    "TOOL_GROUP",
    "PluginEntry",
    "PluginRegistry",
    "registry",
]
