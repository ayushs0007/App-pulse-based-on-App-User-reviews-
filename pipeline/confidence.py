"""
Confidence pill (HIGH / MED / LOW) for a metric or theme.

Why we need it: PMs chase noise. A theme with n=3 doesn't justify a roadmap
decision. A theme with n=120 absolutely does. We bake this judgement into
the data so the dashboard can show it explicitly.

Heuristic — Wilson-score lower bound at 95% on the proportion-of-total
metric. Simple, well-known, hard to game. For the full math see
https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval

For a theme:
  n   = reviews in that theme
  N   = total reviews this week
  p̂   = n / N

We compute the Wilson lower bound. If `n` itself is below 10 we hard-cap to
LOW regardless of the proportion — small sample, no claim.
"""
from __future__ import annotations

from math import sqrt
from typing import Literal

Confidence = Literal["HIGH", "MED", "LOW"]


def score(n: int, total: int, z: float = 1.96) -> Confidence:
    if n < 10:
        return "LOW"
    if total <= 0:
        return "LOW"
    p = n / total
    denom = 1 + (z * z) / total
    centre = (p + (z * z) / (2 * total)) / denom
    margin = (z * sqrt((p * (1 - p) + (z * z) / (4 * total)) / total)) / denom
    lower = max(0.0, centre - margin)
    if lower >= 0.08:
        return "HIGH"
    if lower >= 0.03:
        return "MED"
    return "LOW"
