"""
MCP server exposing two tools the pipeline can call:

  - append_weekly_pulse : appends the Weekly Pulse to a shared Google Doc.
  - create_gmail_draft  : creates a Gmail draft (not sent) for the team.

MCP (Model Context Protocol) is Anthropic's open protocol for connecting LLMs
to external tools/data. The server speaks JSON-RPC 2.0 over stdio (or
WebSocket); the client (e.g. Claude Desktop, your own agent) discovers tools
via `tools/list` and invokes them via `tools/call`.

Why use MCP here? Two reasons:
1. We get authentication / approval boundaries for free — the user explicitly
   wires the server into their host app.
2. We can reuse the same server from any MCP-compatible client (Claude
   Desktop, a custom agent, our Flask API).

For the live LinkedIn demo the auth gates are *idempotent*:
- "Append to doc" produces no duplicate H2 if the same week_label already exists.
- "Create draft" creates a draft (never sends).
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

# We import lazily inside the tool functions because google-api-python-client
# is heavy and CI doesn't need it to import the module.


# -- MCP boilerplate ---------------------------------------------------------

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:  # pragma: no cover - mcp not installed yet
    Server = None  # type: ignore


def build_server():
    if Server is None:
        raise RuntimeError("Install the 'mcp' package: pip install mcp")
    server = Server("groww-pulse-mcp")

    @server.list_tools()
    async def list_tools() -> list:
        return [
            Tool(
                name="append_weekly_pulse",
                description=(
                    "Append the Weekly Pulse summary to a shared Google Doc. "
                    "Idempotent — calling twice with the same week_label is a no-op."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["week_label", "summary"],
                    "properties": {
                        "week_label": {"type": "string"},
                        "summary": {"type": "string"},
                        "recommendation": {"type": "string"},
                        "actions": {"type": "array"},
                    },
                },
            ),
            Tool(
                name="create_gmail_draft",
                description=(
                    "Create a Gmail draft addressed to the product team. Never sends."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["subject", "html"],
                    "properties": {
                        "subject": {"type": "string"},
                        "html": {"type": "string"},
                        "to": {"type": "string"},
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> list:
        if name == "append_weekly_pulse":
            res = append_to_doc_sync(arguments)
        elif name == "create_gmail_draft":
            res = create_email_draft_sync(arguments)
        else:
            return [TextContent(type="text", text=f"unknown tool {name}")]
        return [TextContent(type="text", text=str(res))]

    return server


async def main() -> None:
    server = build_server()
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


# -- side-effect implementations --------------------------------------------
# Split out so the Flask API can call the same code path without MCP framing.

def append_to_doc_sync(args: Dict[str, Any]) -> Dict[str, Any]:
    """Append a section to the shared Google Doc. Returns dict for callers."""
    doc_id = os.getenv("GOOGLE_DOC_ID")
    if not doc_id:
        return {"status": "dry_run", "reason": "GOOGLE_DOC_ID not set", "echo": args}

    from googleapiclient.discovery import build  # noqa: WPS433  lazy import
    from googleapiclient.errors import HttpError
    creds = _google_creds(["https://www.googleapis.com/auth/documents"])
    docs = build("docs", "v1", credentials=creds)

    # Idempotency: scan the doc for an existing heading with this week's label.
    try:
        body = docs.documents().get(documentId=doc_id).execute()
    except HttpError as e:
        return {"status": "error", "error": str(e)}

    heading_marker = f"Weekly Pulse — {args['week_label']}"
    text_dump = "".join(
        run.get("textRun", {}).get("content", "")
        for el in body.get("body", {}).get("content", [])
        for run in el.get("paragraph", {}).get("elements", [])
    )
    if heading_marker in text_dump:
        return {"status": "skipped", "reason": "section already present"}

    requests_body = [
        {
            "insertText": {
                "endOfSegmentLocation": {},
                "text": (
                    f"\n{heading_marker}\n{args.get('summary', '')}\n\n"
                    f"Recommendation: {args.get('recommendation', '')}\n\n"
                ),
            }
        }
    ]
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": requests_body}).execute()
    return {"status": "appended", "doc_id": doc_id}


def create_email_draft_sync(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create a Gmail draft (never sent)."""
    import base64
    from email.mime.text import MIMEText
    from googleapiclient.discovery import build  # noqa: WPS433
    from googleapiclient.errors import HttpError

    to = args.get("to") or os.getenv("GMAIL_TO")
    if not to:
        return {"status": "dry_run", "reason": "GMAIL_TO not set", "echo": args}

    creds = _google_creds(["https://www.googleapis.com/auth/gmail.compose"])
    gmail = build("gmail", "v1", credentials=creds)

    msg = MIMEText(args.get("html", ""), "html")
    msg["to"] = to
    msg["subject"] = args.get("subject", "Weekly Pulse")
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    try:
        draft = gmail.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        return {"status": "draft_created", "draft_id": draft["id"]}
    except HttpError as e:
        return {"status": "error", "error": str(e)}


def _google_creds(scopes):
    """Cache-aware OAuth flow for Google APIs.

    Looks for credentials.json next to this file, persists the token to
    token.json. Hand-off is one-time browser approval.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    here = os.path.dirname(__file__)
    token_path = os.path.join(here, "token.json")
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(here, "credentials.json"), scopes
            )
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as fh:
            fh.write(creds.to_json())
    return creds


if __name__ == "__main__":
    asyncio.run(main())
