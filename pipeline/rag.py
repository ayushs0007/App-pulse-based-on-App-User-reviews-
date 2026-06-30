"""
The "Retrieval-Augmented Generation" layer.

RAG = retrieve relevant context first, then generate text *grounded* on it.
Without RAG the LLM would hallucinate quotes that look real but never existed.
With RAG we always feed it actual user reviews, so the verbatims it cites are
ones the user can verify in the dashboard.

Our retrieval is intentionally simple:
1. Embed all reviews (done in embeddings.py).
2. For a given theme cluster, the retrieved context = the top-N reviews
   closest to the cluster centroid.
3. We pass those as a numbered list into the prompt.

That's it. No vector DB, no chunking — reviews are already small documents.
"""
from __future__ import annotations

from typing import List, Dict, Any

from .llm import complete


WEEKLY_PULSE_SYSTEM = (
    "You are a product analyst writing the Weekly Pulse for the Groww team. "
    "Be concise. Cite real user verbatims. Never invent numbers or features."
)


def weekly_pulse(
    clusters: List[Dict[str, Any]],
    sentiment: Dict[str, float],
    total: int,
    week_label: str,
) -> Dict[str, Any]:
    """Generate the Weekly Pulse summary + strategic recommendation.

    Returns: { summary: str (<=250 words), recommendation: str, actions: [...] }
    """
    theme_block = "\n".join(
        f"- {c['label']} (n={c['size']}, avg rating {c['avg_rating']:.1f}): "
        f"\"{c['sample_quotes'][0][:140]}\""
        for c in clusters[:5]
    )

    prompt = f"""Week: {week_label}
Total reviews analysed: {total}
Sentiment: {sentiment['neg']}% negative, {sentiment['neu']}% neutral, {sentiment['pos']}% positive

Top themes (with one representative quote each):
{theme_block}

Write a Weekly Pulse note in <= 250 words covering:
1. Two-sentence overview of user mood.
2. The most critical theme and why it matters.
3. One positive callout if the data supports it.

Then on a new line starting with "RECOMMENDATION:" give a single strategic
recommendation (one sentence) that the product team should investigate first.

Then on a new line starting with "ACTIONS:" list three prioritised actions,
each on its own line beginning with "- " and ending with " | priority: HIGH"
or " | priority: MED" or " | priority: LOW".
"""

    raw = complete(prompt, system=WEEKLY_PULSE_SYSTEM, max_tokens=700)
    return _parse_pulse(raw, clusters)


def _parse_pulse(raw: str, clusters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Split the LLM output into the three structured sections.

    We're permissive here — if a section is missing we fall back to a default
    derived from the cluster stats rather than failing the whole pipeline.
    """
    summary, recommendation, actions = raw, "", []

    if "RECOMMENDATION:" in raw:
        summary, rest = raw.split("RECOMMENDATION:", 1)
        summary = summary.strip()
        if "ACTIONS:" in rest:
            recommendation, action_block = rest.split("ACTIONS:", 1)
            recommendation = recommendation.strip()
            actions = _parse_actions(action_block)
        else:
            recommendation = rest.strip()

    if not recommendation and clusters:
        top = clusters[0]
        recommendation = (
            f"Investigate and patch the {top['label'].lower()} issues "
            f"({top['size']} reviews) before next release."
        )

    if not actions and clusters:
        actions = [
            {"text": f"Triage {c['label']}", "priority": "HIGH" if i == 0 else "MED"}
            for i, c in enumerate(clusters[:3])
        ]

    return {"summary": summary, "recommendation": recommendation, "actions": actions}


def _parse_actions(block: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for line in block.splitlines():
        line = line.strip().lstrip("-").strip()
        if not line:
            continue
        if "| priority:" in line:
            text, _, prio = line.partition("| priority:")
            out.append({"text": text.strip(), "priority": prio.strip().upper()})
        else:
            out.append({"text": line, "priority": "MED"})
    return out[:3]


def representative_feedback(
    clusters: List[Dict[str, Any]], reviews_full: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Pick the 4 most actionable verbatims for the right-hand panel.

    Rule: one quote per cluster (centroid medoid) capped at 4, severity tagged
    by avg cluster rating so the dashboard can colour them.
    """
    out = []
    for c in clusters[:4]:
        first_idx = c["indices"][0] if c["indices"] else None
        if first_idx is None:
            continue
        r = reviews_full[first_idx]
        severity = "CRITICAL" if c["avg_rating"] < 2.5 else "MAJOR" if c["avg_rating"] < 3.5 else "INFO"
        out.append(
            {
                "user": r["user"],
                "initials": _initials(r["user"]),
                "text": r["text"],
                "rating": r["rating"],
                "severity": severity,
                "theme": c["label"],
            }
        )
    return out


def _initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return "??"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()
