"""
Convenience client used by the LangGraph pipeline. Bypasses the MCP transport
and calls the side-effect functions directly so the dashboard can keep
working without a separate MCP host.

If you want the real MCP transport, point an MCP host (e.g. Claude Desktop)
at `mcp_server.server` and call the tools via JSON-RPC instead.
"""
from __future__ import annotations
from typing import Dict, Any

from .server import append_to_doc_sync, create_email_draft_sync


def append_to_doc(pulse: Dict[str, Any], week_label: str) -> Dict[str, Any]:
    return append_to_doc_sync(
        {
            "week_label": week_label,
            "summary": pulse.get("summary", ""),
            "recommendation": pulse.get("recommendation", ""),
            "actions": pulse.get("actions", []),
        }
    )


def create_email_draft(
    pulse: Dict[str, Any], feedback, week_label: str
) -> Dict[str, Any]:
    html = (
        f"<h2>Weekly Pulse — {week_label}</h2>"
        f"<p>{pulse.get('summary', '')}</p>"
        f"<p><b>Recommendation:</b> {pulse.get('recommendation', '')}</p>"
    )
    return create_email_draft_sync(
        {"subject": f"Weekly Pulse — {week_label}", "html": html}
    )
