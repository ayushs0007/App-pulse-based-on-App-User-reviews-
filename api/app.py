"""
Flask API that serves the React dashboard.

Endpoints:
  GET  /api/weekly?week=YYYY-Www   -> Weekly Pulse run JSON
  GET  /api/runs                   -> list of available run_ids
  GET  /api/fee-explainer          -> latest fee explainer
  GET  /api/email-snapshot         -> rendered HTML of the email draft
  POST /api/run                    -> trigger a fresh pipeline run
  POST /api/mcp/approve            -> human-approval gate (doc | email)

Why Flask and not FastAPI? The API surface is small and synchronous, the
pipeline is the heavy lifter, and Flask's footprint keeps the demo light.
"""
from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, request, abort
from flask_cors import CORS

from pipeline.langgraph_flow import run as run_pipeline

ROOT = Path(__file__).parent.parent
RUNS_DIR = ROOT / "api" / "data" / "runs"

app = Flask(__name__)
CORS(app)


def _load_run(week: str | None):
    target = RUNS_DIR / (f"{week}.json" if week else "latest.json")
    if not target.exists():
        return None
    return json.loads(target.read_text(encoding="utf-8"))


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/weekly")
def weekly():
    data = _load_run(request.args.get("week"))
    if data is None:
        abort(404, description="no run for that week")
    return jsonify(data)


@app.get("/api/runs")
def runs():
    if not RUNS_DIR.exists():
        return jsonify([])
    items = []
    for p in sorted(RUNS_DIR.glob("*.json")):
        if p.stem == "latest" or p.name.endswith(".drill.json"):
            continue
        meta = json.loads(p.read_text(encoding="utf-8"))
        items.append(
            {
                "week_label": meta["week_label"],
                "generated_at": meta["generated_at"],
                "total": meta["total"],
                "themes": [c["label"] for c in meta["clusters"]],
            }
        )
    items.sort(key=lambda x: x["week_label"], reverse=True)
    return jsonify(items)


@app.get("/api/fee-explainer")
def fee():
    data = _load_run(request.args.get("week"))
    if data is None:
        abort(404)
    return jsonify(data.get("fee", {}))


@app.get("/api/anomalies")
def anomalies():
    data = _load_run(request.args.get("week"))
    if data is None:
        abort(404)
    return jsonify(data.get("anomalies", []))


@app.get("/api/decision")
def decision():
    data = _load_run(request.args.get("week"))
    if data is None:
        abort(404)
    return jsonify(data.get("decision", {}))


@app.get("/api/theme/<int:cluster_id>")
def theme_drilldown(cluster_id: int):
    """Drill into a single theme — returns all reviews in it.

    Used by the dashboard modal so a PM can verify the AI's grouping before
    signing off on a recommendation. Supports `?week=`, `?lang=`, `?max=`.
    """
    week = request.args.get("week")
    drill_path = RUNS_DIR / (f"{week}.drill.json" if week else "latest.drill.json")
    if not drill_path.exists():
        # `latest.drill.json` isn't written; fall back to the persisted run.
        latest = _load_run(None)
        if latest is None:
            abort(404)
        drill_path = RUNS_DIR / f"{latest['week_label']}.drill.json"
        if not drill_path.exists():
            abort(404)
    drill = json.loads(drill_path.read_text(encoding="utf-8"))
    cluster = next((c for c in drill["clusters"] if c["id"] == cluster_id), None)
    if cluster is None:
        abort(404)
    lang_filter = request.args.get("lang")
    max_n = int(request.args.get("max", 50))
    reviews_idx = cluster.get("indices", [])
    items = [drill["reviews"][i] for i in reviews_idx if i < len(drill["reviews"])]
    if lang_filter:
        items = [r for r in items if r.get("lang") == lang_filter]
    return jsonify({
        "label": cluster["label"],
        "id": cluster["id"],
        "total_in_cluster": len(reviews_idx),
        "reviews": items[:max_n],
    })


@app.get("/api/email-snapshot")
def email_snapshot():
    data = _load_run(request.args.get("week"))
    if data is None:
        abort(404)
    return jsonify(
        {
            "to": "product-team@groww.in",
            "subject": f"Weekly Pulse — {data['week_label']}",
            "html": _render_email_html(data),
        }
    )


@app.post("/api/run")
def trigger_run():
    body = request.get_json(silent=True) or {}
    out = run_pipeline(
        week_label=body.get("week"),
        approve_doc=False,
        approve_email=False,
    )
    return jsonify({"run_id": out.get("run_id")})


@app.post("/api/mcp/approve")
def mcp_approve():
    """Human-in-the-loop endpoint. The dashboard POSTs here when the user clicks
    'Append to Google Doc' or 'Create Gmail draft'. The actual side effect is
    performed by the MCP server — see mcp_server/server.py."""
    body = request.get_json() or {}
    gate = body.get("gate")
    week = body.get("week")
    if gate not in {"doc", "email"}:
        abort(400, "gate must be doc or email")

    out = run_pipeline(
        week_label=week,
        approve_doc=(gate == "doc"),
        approve_email=(gate == "email"),
    )
    return jsonify({"gate": gate, "result": out.get("mcp_results", {})})


def _render_email_html(data: dict) -> str:
    """Tiny mailer template — kept in code so the snapshot endpoint is honest
    about exactly what would land in the Gmail draft."""
    pulse = data.get("pulse", {})
    clusters = data.get("clusters", [])
    bullets = "".join(
        f"<li><b>{c['label']}</b> — {c['size']} reviews "
        f"(avg ★{c['avg_rating']:.1f})</li>"
        for c in clusters[:5]
    )
    actions = "".join(
        f"<li>[{a['priority']}] {a['text']}</li>"
        for a in pulse.get("actions", [])
    )
    return f"""<div style="font-family:-apple-system,Segoe UI,sans-serif">
  <h2>Weekly Pulse — {data['week_label']}</h2>
  <p>{pulse.get('summary', '')}</p>
  <h3>Top themes</h3>
  <ul>{bullets}</ul>
  <h3>Strategic recommendation</h3>
  <blockquote>{pulse.get('recommendation', '')}</blockquote>
  <h3>Prioritised actions</h3>
  <ol>{actions}</ol>
</div>"""


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
