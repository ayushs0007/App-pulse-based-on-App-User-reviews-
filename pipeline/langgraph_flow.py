"""
LangGraph orchestration.

LangGraph models the pipeline as a state machine: each node mutates a shared
TypedDict and decides what runs next.

For this project the graph is:

  scrape -> slice -> embed -> cluster -> sentiment -> language -> rag ->
  fee -> anomalies -> decision -> persist -> gate_doc -> gate_email

The `slice` node optionally narrows the cached reviews to a date/index range
so we can run the pipeline twice — once for "this week" and once for "last
week" — to build the WoW baseline.

`anomalies` reads the previous week's persisted run (if any) and classifies
spikes/drops/emerging themes. `decision` picks the single "This Week's Move"
to surface on the dashboard.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, END

from . import (
    scraper, embeddings, clustering, sentiment, rag, fee_explainer,
    lang, anomalies as anomalies_mod, decision as decision_mod, confidence,
)


RUNS_DIR = Path(__file__).parent.parent / "api" / "data" / "runs"
SUBSTANTIVE_MIN_LEN = 30  # filter "good"/"best" one-word reviews from clustering


class PulseState(TypedDict, total=False):
    week_label: str
    baseline_week_label: Optional[str]
    slice_from: Optional[int]     # index range into the cache, [from, to)
    slice_to: Optional[int]
    reviews: List[Dict[str, Any]]
    reviews_full: List[Dict[str, Any]]
    embeddings: Any
    clusters: List[Dict[str, Any]]
    sentiment: Dict[str, float]
    avg_rating: float
    language_breakdown: Dict[str, int]
    pulse: Dict[str, Any]
    feedback: List[Dict[str, Any]]
    fee: Dict[str, Any]
    anomalies: List[Dict[str, Any]]
    decision: Dict[str, Any]
    run_id: str
    total_reviews: int
    approve_doc: bool
    approve_email: bool
    mcp_results: Dict[str, Any]
    _is_baseline_run: bool


# --- nodes ------------------------------------------------------------------

def node_scrape(state: PulseState) -> PulseState:
    cached = scraper.load_cache()
    if cached and len(cached) >= 300:
        state["reviews"] = cached
        return state
    state["reviews"] = scraper.fetch_reviews(count=1000)
    scraper.save_cache(state["reviews"])
    return state


def node_slice(state: PulseState) -> PulseState:
    """Optionally narrow the review set to an index slice.

    `slice_from` / `slice_to` index the cache as if it were one big list.
    Reviews from the scraper are NEWEST-first, so [0:500] = most recent and
    [500:1000] = older — that's how we synthesise a 'last week' baseline.
    """
    a = state.get("slice_from")
    b = state.get("slice_to")
    if a is None and b is None:
        return state
    state["reviews"] = state["reviews"][a or 0 : b or len(state["reviews"])]
    return state


def node_embed(state: PulseState) -> PulseState:
    texts = [r["text"] for r in state["reviews"] if r["text"]]
    state["embeddings"] = embeddings.embed(texts)
    return state


def node_cluster(state: PulseState) -> PulseState:
    """Cluster only substantive reviews (≥30 chars)."""
    full = [r for r in state["reviews"] if r["text"]]
    state["total_reviews"] = len(full)
    substantive_idx = [
        i for i, r in enumerate(full) if len(r["text"]) >= SUBSTANTIVE_MIN_LEN
    ]
    substantive = [full[i] for i in substantive_idx]
    sub_embeddings = embeddings.embed([r["text"] for r in substantive])
    texts = [r["text"] for r in substantive]
    ratings = [r["rating"] for r in substantive]
    state["clusters"] = clustering.cluster(sub_embeddings, texts, ratings, k=5)
    state["reviews_full"] = full
    state["reviews"] = substantive
    return state


def node_sentiment(state: PulseState) -> PulseState:
    full = state.get("reviews_full") or state["reviews"]
    ratings = [r["rating"] for r in full]
    state["sentiment"] = sentiment.sentiment_breakdown(ratings)
    state["avg_rating"] = sentiment.avg_score(ratings)
    return state


def node_language(state: PulseState) -> PulseState:
    """Tag each review with `lang` and stash the breakdown on state."""
    full = state.get("reviews_full") or state["reviews"]
    state["language_breakdown"] = lang.breakdown(full)
    # Also annotate substantive subset (used by drill-down view).
    lang.breakdown(state["reviews"])
    return state


def node_rag(state: PulseState) -> PulseState:
    state["pulse"] = rag.weekly_pulse(
        state["clusters"], state["sentiment"], len(state["reviews"]), state["week_label"]
    )
    state["feedback"] = rag.representative_feedback(state["clusters"], state["reviews"])
    return state


def node_fee(state: PulseState) -> PulseState:
    state["fee"] = fee_explainer.fee_explainer(state["reviews"])
    return state


def node_anomalies(state: PulseState) -> PulseState:
    """Compare current clusters to the persisted baseline run."""
    baseline = _load_baseline_clusters(state.get("baseline_week_label"))
    anomalies_mod.attach_wow_to_clusters(state["clusters"], baseline)
    # Attach confidence pill to each cluster.
    total = state.get("total_reviews") or len(state["reviews"])
    for c in state["clusters"]:
        c["confidence"] = confidence.score(c["size"], total)
    raw = anomalies_mod.compute(state["clusters"], baseline)
    state["anomalies"] = [a.to_dict() for a in raw]
    return state


def node_decision(state: PulseState) -> PulseState:
    total = state.get("total_reviews") or len(state["reviews"])
    raw_anoms = [anomalies_mod.Anomaly(**a) for a in state.get("anomalies", [])]
    state["decision"] = decision_mod.pick(state["clusters"], raw_anoms, total)
    return state


def node_persist(state: PulseState) -> PulseState:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    state["run_id"] = state["week_label"]
    full = state.get("reviews_full") or state["reviews"]
    payload = {
        "run_id": state["run_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "week_label": state["week_label"],
        "baseline_week_label": state.get("baseline_week_label"),
        "total": len(full),
        "sentiment": state["sentiment"],
        "avg_rating": state["avg_rating"],
        "language_breakdown": state.get("language_breakdown", {}),
        "clusters": [_serialise_cluster(c) for c in state["clusters"]],
        "pulse": state["pulse"],
        "feedback": state["feedback"],
        "fee": state["fee"],
        "anomalies": state.get("anomalies", []),
        "decision": state.get("decision", {}),
    }
    (RUNS_DIR / f"{state['week_label']}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    # Also keep `latest.json` only when this is the "real" current run.
    if not state.get("_is_baseline_run"):
        (RUNS_DIR / "latest.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    # Persist the per-review drill-down payload (substantive reviews only).
    drill = {
        "week_label": state["week_label"],
        "reviews": [
            {
                "id": r.get("id"),
                "user": r.get("user"),
                "rating": r.get("rating"),
                "text": r.get("text"),
                "lang": r.get("lang"),
            }
            for r in state["reviews"]
        ],
        "clusters": [
            {
                "id": c["id"],
                "label": c["label"],
                "indices": c.get("indices", []),
            }
            for c in state["clusters"]
        ],
    }
    (RUNS_DIR / f"{state['week_label']}.drill.json").write_text(
        json.dumps(drill, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return state


def node_gate_doc(state: PulseState) -> PulseState:
    if not state.get("approve_doc"):
        return state
    from mcp_server.client import append_to_doc
    res = append_to_doc(state["pulse"], state["week_label"])
    state.setdefault("mcp_results", {})["doc"] = res
    return state


def node_gate_email(state: PulseState) -> PulseState:
    if not state.get("approve_email"):
        return state
    from mcp_server.client import create_email_draft
    res = create_email_draft(state["pulse"], state["feedback"], state["week_label"])
    state.setdefault("mcp_results", {})["email"] = res
    return state


def _serialise_cluster(c: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in c.items() if k not in {"indices", "__kind"}}


def _load_baseline_clusters(week_label: Optional[str]) -> Optional[List[Dict[str, Any]]]:
    if not week_label:
        return None
    p = RUNS_DIR / f"{week_label}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("clusters")


# --- graph ------------------------------------------------------------------

def build_graph():
    g = StateGraph(PulseState)
    for name, fn in [
        ("scrape", node_scrape),
        ("slice", node_slice),
        ("embed", node_embed),
        ("cluster", node_cluster),
        ("sentiment", node_sentiment),
        ("language", node_language),
        ("rag", node_rag),
        ("fee", node_fee),
        ("anomalies", node_anomalies),
        ("decision", node_decision),
        ("persist", node_persist),
        ("gate_doc", node_gate_doc),
        ("gate_email", node_gate_email),
    ]:
        g.add_node(name, fn)
    g.set_entry_point("scrape")
    chain = ["scrape", "slice", "embed", "cluster", "sentiment", "language",
             "rag", "fee", "anomalies", "decision", "persist",
             "gate_doc", "gate_email"]
    for a, b in zip(chain, chain[1:]):
        g.add_edge(a, b)
    g.add_edge("gate_email", END)
    return g.compile()


def run(
    week_label: Optional[str] = None,
    baseline_week_label: Optional[str] = None,
    slice_from: Optional[int] = None,
    slice_to: Optional[int] = None,
    approve_doc: bool = False,
    approve_email: bool = False,
    _is_baseline_run: bool = False,
) -> Dict[str, Any]:
    if week_label is None:
        iso = datetime.now(timezone.utc).isocalendar()
        week_label = f"{iso.year}-W{iso.week:02d}"
    app = build_graph()
    initial: PulseState = {
        "week_label": week_label,
        "baseline_week_label": baseline_week_label,
        "slice_from": slice_from,
        "slice_to": slice_to,
        "approve_doc": approve_doc,
        "approve_email": approve_email,
    }
    if _is_baseline_run:
        initial["_is_baseline_run"] = True  # type: ignore[typeddict-unknown-key]
    return app.invoke(initial)
