"""
K-Means clustering on review embeddings to discover up to 5 themes.

Why K-Means and not HDBSCAN / topic models?
- Reviews are short; sparse topic models (LDA) need more text per doc.
- HDBSCAN's noise label complicates the "top 5 themes" UX.
- K-Means with a fixed K=5 gives the dashboard a stable contract: always 5 cards.

We pick a representative quote per cluster by taking the review closest to the
cluster centroid (the "medoid by centroid distance"). That's the line we show
in the Weekly Pulse summary.
"""
from __future__ import annotations

from collections import Counter
from typing import List, Dict, Any

import numpy as np
from sklearn.cluster import KMeans

# Heuristic labels — picked after eyeballing the data. The LLM can rename them
# during summarization, but having defaults means the dashboard never shows
# "Cluster #3".
THEME_NAMES = {
    "brokerage": "High Brokerage Fees",
    "stability": "App Stability Issues",
    "feature": "Feature Enhancement Requests",
    "ui": "User Friendly Interface",
    "nav": "Simple Navigation Experience",
    "order": "Order Execution Issues",
    "kyc": "KYC / Onboarding Friction",
    "support": "Customer Support",
    "fee": "Exit Load / Fee Confusion",
    "performance": "Performance / Load Time",
}

# Keyword -> theme key. The cluster gets the theme whose keywords appear most
# often in its top quotes. Cheap, deterministic, and explainable.
KEYWORD_MAP = {
    "brokerage": ["brokerage", "charge", "expensive", "commission", "demat", "high fee", "high charges"],
    "stability": ["crash", "hang", "freeze", "stuck", "lag", "not working", "issue", "problem", "error", "bug"],
    "feature": ["feature", "should add", "please add", "missing", "wish", "need", "want", "request", "suggest"],
    "ui": ["ui", "design", "clean", "easy", "interface", "looks", "beautiful", "user friendly", "simple to use"],
    "nav": ["navigate", "navigation", "find", "intuitive", "smooth"],
    "order": ["order", "limit", "market order", "stop loss", "executed", "execution", "trade"],
    "kyc": ["kyc", "verification", "aadhaar", "pan card", "verify", "onboarding", "account opening"],
    "support": ["support", "response", "ticket", "customer care", "no reply", "no response", "help"],
    "fee": ["exit load", "hidden", "fee", "deducted", "amc", "tax"],
    "performance": ["slow", "load", "loading", "open", "startup", "latency", "lag"],
    "positive": ["best", "awesome", "amazing", "excellent", "love", "great app", "very good", "super"],
    "negative": ["worst", "bad", "horrible", "terrible", "fraud", "cheat", "scam"],
}

PRETTY_NAMES = {
    "positive": "Positive Endorsements",
    "negative": "General Complaints",
}


def cluster(
    embeddings: np.ndarray,
    texts: List[str],
    ratings: List[int],
    k: int = 5,
    seed: int = 42,
    min_quote_len: int = 60,
) -> List[Dict[str, Any]]:
    """Cluster review embeddings; return one dict per cluster.

    Each cluster has: id, label, size, avg_rating, sample_quotes, indices.

    `min_quote_len` filters one-word reviews (e.g. "good", "best") from the
    representative quotes — they cluster strongly but tell us nothing.
    """
    if len(embeddings) < k:
        k = max(2, len(embeddings))

    km = KMeans(n_clusters=k, random_state=seed, n_init=10)
    labels = km.fit_predict(embeddings)

    clusters: List[Dict[str, Any]] = []
    for cid in range(k):
        member_idx = np.where(labels == cid)[0]
        if len(member_idx) == 0:
            continue

        # Rank the cluster's reviews by distance-to-centroid, then prefer
        # ones long enough to be informative when picking the rep quote.
        centroid = km.cluster_centers_[cid]
        dists = np.linalg.norm(embeddings[member_idx] - centroid, axis=1)
        ranked_idx = member_idx[np.argsort(dists)]

        long_quotes = [
            int(i) for i in ranked_idx if len(texts[i]) >= min_quote_len
        ][:6]
        # Fall back to the raw nearest list if the cluster is all-short.
        rep_idx = long_quotes if long_quotes else [int(i) for i in ranked_idx[:6]]
        top_quotes = [texts[i] for i in rep_idx]

        # `indices` is the **full** member list (used to colour-code the
        # entire cluster), but rep_idx[0] is the lead quote on the dashboard.
        ordered = rep_idx + [int(i) for i in ranked_idx if int(i) not in rep_idx]

        clusters.append(
            {
                "id": cid,
                "label": _label_cluster(top_quotes),
                "size": int(len(member_idx)),
                "avg_rating": float(np.mean([ratings[i] for i in member_idx])),
                "sample_quotes": top_quotes,
                "indices": ordered,
            }
        )

    # Sort by size desc (the dashboard wants biggest themes first)
    clusters.sort(key=lambda c: -c["size"])
    return clusters


def _label_cluster(top_quotes: List[str]) -> str:
    """Score keyword frequency across each theme; pick the winner."""
    blob = " ".join(q.lower() for q in top_quotes)
    scores: Counter = Counter()
    for key, words in KEYWORD_MAP.items():
        scores[key] = sum(blob.count(w) for w in words)
    best_key, best_score = scores.most_common(1)[0]
    if best_score == 0:
        return "General Feedback"
    return THEME_NAMES.get(best_key) or PRETTY_NAMES.get(best_key, "General Feedback")
