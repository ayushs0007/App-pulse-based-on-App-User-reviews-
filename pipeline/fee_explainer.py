"""
Fee Explainer — surfaces fee-related confusion from real reviews and turns it
into a neutral 6-bullet explanation with sources.

This is RAG with a specific filter: only reviews that talk about fees/charges.
We feed the matching reviews into the LLM and ask for a fact-checked answer
with citations to official Groww help-centre pages.
"""
from __future__ import annotations

from typing import List, Dict, Any

from .llm import complete

# Pinned official sources. Hardcoding these keeps the "facts" pillar reliable —
# the LLM cannot make up URLs.
SOURCES = [
    {
        "title": "Brokerage charges on stock investments",
        "url": "https://groww.in/p/brokerage-charges",
    },
    {
        "title": "Mutual fund exit load explained",
        "url": "https://groww.in/p/mutual-funds-exit-load",
    },
    {
        "title": "All charges on Groww (official)",
        "url": "https://groww.in/blog/charges-on-groww",
    },
]

SYSTEM = (
    "You are explaining Indian broking fees neutrally. Use ONLY the sources "
    "provided. If unsure, say so. Output 6 bullet points, no marketing."
)


def fee_explainer(reviews_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    matched = [r for r in reviews_data if _is_fee_related(r["text"])]
    if not matched:
        return {"bullets": [], "sources": SOURCES, "matched": 0}

    sample = [r["text"][:280] for r in matched[:8]]
    quoted = "\n".join(f"{i+1}. \"{t}\"" for i, t in enumerate(sample))

    prompt = f"""Users are confused about Groww's fees. Here are real complaints:

{quoted}

Official sources you may cite:
{chr(10).join(f"[{i+1}] {s['title']} — {s['url']}" for i, s in enumerate(SOURCES))}

Write exactly 6 short bullet points (max 20 words each) that:
- Explain the specific fees users are confused about
- Are neutral and factual (no marketing language)
- Cite a source by number in square brackets at the end, e.g. [1]

Begin each line with "- ".
"""

    raw = complete(prompt, system=SYSTEM, max_tokens=500)
    bullets = [
        line.strip().lstrip("-").strip()
        for line in raw.splitlines()
        if line.strip().startswith("-")
    ][:6]
    if not bullets:
        # No LLM available — fall back to a static, neutral explainer that
        # still answers the most common confusion points referenced in [1]–[3].
        bullets = [
            "Stock delivery trades on Groww incur Rs 20 or 0.1% (whichever is lower) per executed order. [1]",
            "Intraday and F&O trades are charged Rs 20 per executed order, plus statutory levies. [3]",
            "Mutual funds direct plans on Groww have zero commission and no transaction fees. [2]",
            "Exit load is a mutual-fund-house charge for redeeming units inside the lock-in window — Groww does not earn this. [2]",
            "Demat AMC for stock investors is billed annually after the first year, separate from per-trade brokerage. [3]",
            "GST, SEBI turnover fee, STT and stamp duty are statutory levies passed through unchanged on every trade. [3]",
        ]
    return {"bullets": bullets, "sources": SOURCES, "matched": len(matched)}


FEE_KEYWORDS = (
    "brokerage", "charge", "fee", "amc", "demat", "exit load", "deducted",
    "hidden", "commission",
)


def _is_fee_related(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in FEE_KEYWORDS)
