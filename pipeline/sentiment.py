"""
Rating-driven sentiment.

We bucket by star rating instead of running a sentiment model because:
- The user already told us their sentiment via rating.
- A model would just re-derive it (and disagree 5-10% of the time).
- Bucketing is O(n) and 100% reproducible.

1-2 stars  -> negative
3 stars    -> neutral
4-5 stars  -> positive
"""
from __future__ import annotations
from typing import List, Dict


def sentiment_breakdown(ratings: List[int]) -> Dict[str, float]:
    if not ratings:
        return {"neg": 0.0, "neu": 0.0, "pos": 0.0}
    n = len(ratings)
    neg = sum(1 for r in ratings if r <= 2)
    neu = sum(1 for r in ratings if r == 3)
    pos = sum(1 for r in ratings if r >= 4)
    return {
        "neg": round(100 * neg / n),
        "neu": round(100 * neu / n),
        "pos": round(100 * pos / n),
    }


def avg_score(ratings: List[int]) -> float:
    """Compress the rating-distribution to a single 1-5 sentiment score."""
    if not ratings:
        return 0.0
    return round(sum(ratings) / len(ratings), 1)
