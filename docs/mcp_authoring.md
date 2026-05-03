# Authoring an MCP server for Nova

Nova consumes any [Model Context Protocol](https://modelcontextprotocol.io)
server that speaks the `stdio`, `http`, or `websocket` transport.

## Minimal example

```python
# my_mcp_server.py
import json, sys

TOOLS = [
    {
        "name": "echo",
        "description": "Return the input string unchanged.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    }
]

def handle(req: dict) -> dict:
    if req["method"] == "tools/list":
        return {"id": req["id"], "result": {"tools": TOOLS}}
    if req["method"] == "tools/call":
        if req["params"]["name"] == "echo":
            return {"id": req["id"], "result": {
                "content": [{"type": "text", "text": req["params"]["arguments"]["text"]}]
            }}
    return {"id": req["id"], "error": {"code": -32601, "message": "method not found"}}

for line in sys.stdin:
    json.dump(handle(json.loads(line)), sys.stdout); sys.stdout.write("\n"); sys.stdout.flush()
```

Register it in `~/.config/nova/mcps.json`:

```json
{
  "echo": {
    "transport": "stdio",
    "command": ["python", "/path/to/my_mcp_server.py"]
  }
}
```

Restart Nova. The `echo` tool now appears in the registry; the brain
can call it via the regular tool-use loop.

## Where the contract lives

- `nova.tools.mcp` — three transports (stdio / http / websocket)
- `nova.tools.registry` — JSON-persisted registry the agent inspects
- `nova.tools.filter` — embedding-based subset selection so 200+ tools
  don't fill the context window
- `nova.tools.approval` — per-tool approval policy, persisted

## Tips

- Prefer one tool per discrete action; descriptions are what the
  embedding filter scores.
- Echo dangerous parameters back in the tool result so the audit log
  captures intent.
- Return `isError: true` rather than raising — the agent retries on
  unhandled exceptions.
- Ship a `nova.tools` entry point in your `pyproject.toml` so users
  can `pip install` your MCP and have Nova auto-discover it (see
  `nova.plugins`).
