"""Tool plane: MCP client + built-in tools."""

from nova.tools import approval as _approval
from nova.tools import filter as _filter
from nova.tools import mcp as _mcp
from nova.tools import registry as _registry

ApprovalManager = _approval.ApprovalManager
ConfirmRequest = _approval.ConfirmRequest
Policy = _approval.Policy
in_memory_confirmer = _approval.in_memory_confirmer

Embedder = _filter.Embedder
HashingEmbedder = _filter.HashingEmbedder
ToolFilter = _filter.ToolFilter

McpRegistry = _registry.McpRegistry
McpServerEntry = _registry.McpServerEntry
registry_for = _registry.registry_for

McpClient = _mcp.McpClient
McpTool = _mcp.McpTool
McpTransport = _mcp.McpTransport
StdioTransport = _mcp.StdioTransport
HttpSseTransport = _mcp.HttpSseTransport
StreamableHttpTransport = _mcp.StreamableHttpTransport
create_transport = _mcp.create_transport

__all__ = [
    "HttpSseTransport",
    "McpClient",
    "McpTool",
    "McpTransport",
    "StdioTransport",
    "StreamableHttpTransport",
    "create_transport",
]
