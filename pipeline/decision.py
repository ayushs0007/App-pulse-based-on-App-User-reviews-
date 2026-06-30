"""
"This Week's Move" — the headline decision card.

This is the most opinionated module in the pipeline. It picks ONE move the
team should make next sprint, and stakes its reputation on the choice.

Selection heuristic (in order):
  1. The most-severe CRITICAL spike anomaly (a complaint theme that grew >30%).
  2. Failing that, the largest complaint cluster by size.
  3. Failing that, the highest-rated cluster (a "double down" recommendation).

For each move we generate the five things a PM actually needs:
  - the move (imperative one-liner)
  - the why (data evidence with numbers)
  - estimated impact (qualitative + addressable user count)
  - confidence pill (HIGH/MED/LOW from confidence.py)
  - owner suggestion (rule-based mapping from theme → team)

Owner mapping is deliberately rule-based, not LLM-generated, so the
recommendations are predictable across runs.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional

from .confidence import score as conf_score
from .anomalies import Anomaly

OWNER_BY_THEME = {
    "High Brokerage Fees":          "@growth-pricing",
    "App Stability Issues":         "@platform-eng",
    "User Friendly Interface":      "@design-systems",
    "Simple Navigation Experience": "@design-systems",
    "Order Execution Issues":       "@trading-platform",
    "KYC / Onboarding Friction":    "@onboarding",
    "Customer Support":             "@cx-ops",
    "Exit Load / Fee Confusion":    "@growth-pricing",
    "Performance / Load Time":      "@platform-eng",
    "Feature Enhancement Requests": "@product-roadmap",
    "Positive Endorsements":        "@marketing",
    "General Complaints":           "@cx-ops",
    "General Feedback":             "@product-roadmap",
}

MOVE_TEMPLATES = {
    "High Brokerage Fees":          "Ship a brokerage transparency banner inside the order flow",
    "App Stability Issues":         "Patch the crash hotspots before next release",
    "User Friendly Interface":      "Double-down — extract the UX patterns users love and apply across new screens",
    "Simple Navigation Experience": "Promote the most-discovered shortcuts into the primary nav",
    "Order Execution Issues":       "Investigate the limit-order-to-market-order fallback latency",
    "KYC / Onboarding Friction":    "Cut steps in the KYC funnel and add inline validation",
    "Customer Support":             "Add SLA breach alerting + auto-respond template for top complaint themes",
    "Exit Load / Fee Confusion":    "Embed the fee explainer in-app on the redemption screen",
    "Performance / Load Time":      "Profile the cold-start path and target sub-2s TTI",
    "Feature Enhancement Requests": "Triage the requests, ship the top vote-getter",
    "Positive Endorsements":        "Surface the testimonials in App Store creative for the next campaign",
    "General Complaints":           "Sweep the long tail of complaints for any high-frequency bug",
    "General Feedback":             "Sample 20 reviews manually — the AI couldn't theme them",
}


def pick(
    clusters: List[Dict[str, Any]],
    anomalies: List[Anomaly],
    total_reviews: int,
) -> Dict[str, Any]:
    """Return a decision card dict for the dashboard.

    Shape:
      move          str  imperative recommendation
      why           str  evidence sentence
      theme         str  theme label this targets
      impact        str  qualitative impact estimate
      addressable   int  number of users this move could help
      confidence    str  HIGH | MED | LOW
      owner         str  e.g. "@growth-pricing"
      kind          str  "spike" | "size" | "double-down"
    """
    target = _pick_target(clusters, anomalies)
    if target is None:
        return _empty()

    label = target["label"]
    n = target["size"]
    confidence = conf_score(n, total_reviews)
    move = MOVE_TEMPLATES.get(label, "Investigate and patch the top issue")
    owner = OWNER_BY_THEME.get(label, "@product-roadmap")
    why = _why_sentence(target, anomalies, total_reviews)

    impact_pct = round(100 * n / max(1, total_reviews))
    impact = f"Addresses ~{impact_pct}% of weekly review volume ({n} reviews) — projected NPS impact +{_npS_estimate(target):.1f}"

    return {
        "move": move,
        "why": why,
        "theme": label,
        "impact": impact,
        "addressable": n,
        "confidence": confidence,
        "owner": owner,
        "kind": target.get("__kind", "size"),
    }


def _pick_target(
    clusters: List[Dict[str, Any]],
    anomalies: List[Anomaly],
) -> Optional[Dict[str, Any]]:
    if not clusters:
        return None

    cluster_by_label = {c["label"]: c for c in clusters}

    # Rank: CRITICAL/MAJOR spikes first.
    spikes = [a for a in anomalies if a.kind == "spike" and a.severity in {"CRITICAL", "MAJOR"}]
    if spikes:
        target = cluster_by_label.get(spikes[0].label)
        if target:
            target["__kind"] = "spike"
            return target

    # Else: biggest complaint cluster.
    complaints = [c for c in clusters if c.get("avg_rating", 5) < 3.5]
    if complaints:
        complaints.sort(key=lambda c: -c["size"])
        complaints[0]["__kind"] = "size"
        return complaints[0]

    # Last resort: double-down on the best-loved theme.
    clusters_sorted = sorted(clusters, key=lambda c: (-c.get("avg_rating", 0), -c["size"]))
    clusters_sorted[0]["__kind"] = "double-down"
    return clusters_sorted[0]


def _why_sentence(cluster: Dict[str, Any], anomalies: List[Anomaly], total: int) -> str:
    """Build a single sentence the PM can copy into a Slack DM."""
    label = cluster["label"]
    n = cluster["size"]
    rating = cluster["avg_rating"]
    matching = next((a for a in anomalies if a.label == label), None)
    pct_of_volume = round(100 * n / max(1, total))

    if matching and matching.kind == "spike":
        return (
            f"\"{label}\" jumped {int(matching.delta_pct * 100)}% WoW "
            f"(n {matching.baseline_n} → {n}, avg ★{rating:.1f}). "
            f"It's {pct_of_volume}% of weekly review volume."
        )
    if matching and matching.kind == "emerging":
        return (
            f"\"{label}\" emerged this week (n={n}, avg ★{rating:.1f}). "
            f"First time it's appeared in the top themes."
        )
    return (
        f"\"{label}\" is the largest complaint cluster (n={n}, "
        f"avg ★{rating:.1f}, {pct_of_volume}% of weekly volume)."
    )


def _npS_estimate(cluster: Dict[str, Any]) -> float:
    """Tiny model: a critical issue resolved lifts NPS proportional to its
    share. Used only to give the PM a directional number, not a forecast."""
    return round(cluster["size"] * (5 - cluster["avg_rating"]) / 25.0, 1)


def _empty() -> Dict[str, Any]:
    return {
        "move": "Not enough data yet — run the pipeline again next week.",
        "why": "",
        "theme": "",
        "impact": "",
        "addressable": 0,
        "confidence": "LOW",
        "owner": "@product-roadmap",
        "kind": "none",
    }
