# 05 · Model Context Protocol (MCP)

> Files: [`mcp_server/server.py`](../mcp_server/server.py),
> [`mcp_server/client.py`](../mcp_server/client.py)

## What is MCP?

[Model Context Protocol](https://modelcontextprotocol.io) is an open
protocol from Anthropic for connecting LLMs to external tools and data
sources. Think of it like LSP (Language Server Protocol) but for AI
agents — instead of every editor implementing every language, and every
agent implementing every integration, both speak MCP and meet in the
middle.

```
┌─────────────┐    JSON-RPC over stdio    ┌────────────────┐
│ Host        │ ◄────────────────────────►│ MCP Server     │
│ (Claude,    │                            │ (your code)    │
│  agent, …)  │   tools/list, tools/call   │ google-docs,   │
└─────────────┘                            │  gmail, ...    │
                                           └────────────────┘
```

The server **declares tools** (`tools/list`) and the host **invokes them**
(`tools/call`). That's the whole protocol.

## What we expose

```python
@server.list_tools()
async def list_tools():
    return [
        Tool(name="append_weekly_pulse",
             description="Append the Weekly Pulse summary to a shared Google Doc.",
             inputSchema={...}),
        Tool(name="create_gmail_draft",
             description="Create a Gmail draft. Never sends.",
             inputSchema={...}),
    ]
```

Two tools. Both **idempotent** and **non-sending**:

- `append_weekly_pulse`: before writing, scans the doc for a heading with
  the same `week_label`. Already there? Skip. Otherwise append a new
  section.
- `create_gmail_draft`: uses Gmail's `drafts.create` endpoint, which never
  triggers a send.

Idempotency + draft-only = safe to retry or run accidentally.

## The approval pattern

The Flask API and LangGraph nodes are wired up so that the side effect
**only fires** when both:

1. The dashboard user clicked the button.
2. The server received a POST to `/api/mcp/approve` with the right gate.

This maps cleanly onto MCP's design philosophy: the host (you, the human)
explicitly approves tool calls. We just made the approval visible in the
product UI.

## Running it as a real MCP server

```bash
# Add to your MCP host config (e.g. Claude Desktop's claude_desktop_config.json):
{
  "mcpServers": {
    "groww-pulse": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/absolute/path/to/groww-pulse"
    }
  }
}
```

Now you can chat with Claude Desktop, ask for the weekly pulse, and the
agent can call your tools — same code path the Flask API uses.

## Why `client.py` bypasses the protocol

Inside `langgraph_flow.py` we don't want to spawn a subprocess just to
append to a doc. `mcp_server/client.py` imports the tool functions
directly:

```python
from .server import append_to_doc_sync, create_email_draft_sync
```

Same business logic, no transport. The MCP server **wraps** the same
functions for external hosts. One source of truth, two consumers.

## Setting up Google credentials

`mcp_server/server.py::_google_creds` uses the standard
`google-auth-oauthlib` Installed-App flow:

1. Create a project at https://console.cloud.google.com
2. Enable Google Docs API + Gmail API
3. Configure OAuth consent screen (External, just your test users)
4. Create OAuth Client ID (Desktop application), download `credentials.json`
5. Drop `credentials.json` next to `server.py`
6. First call opens a browser for consent; subsequent calls reuse `token.json`

Without the file the tools return `{"status": "dry_run", ...}` so the
pipeline still works for demos.
