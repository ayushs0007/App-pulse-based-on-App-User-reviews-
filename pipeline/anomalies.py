"""
WoW (week-over-week) anomaly detection.

The dashboard upgrade hinges on this module. We compare the current week's
themes against a baseline (last week or a rolling 4-week average) and
classify each into one of:

  - emerging  : appeared this week, wasn't in baseline top themes
  - spike     : +X% growth, X above threshold
  - drop      : -X% decline (good news if the theme is a complaint)
  - steady   : no significant change
  - resolved  : was in top themes, no longer present

The classification thresholds are deliberately conservative — false-positive
anomalies erode trust fast (this is the Sentry / PagerDuty design rule).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# Thresholds. >= 30% growth = spike, <= -30% decline = drop. These ride on top
# of an absolute floor so a 1-review-to-2-review jump isn't called "+100%".
SPIKE_PCT = 0.30
DROP_PCT = -0.30
MIN_ABS_DELTA = 8


@dataclass
class Anomaly:
    label: str
    kind: str
    current_n: int
    baseline_n: int
    delta_pct: float
    severity: str  # CRITICAL | MAJOR | INFO
    note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "kind": self.kind,
            "current_n": self.current_n,
            "baseline_n": self.baseline_n,
            "delta_pct": self.delta_pct,
            "severity": self.severity,
            "note": self.note,
        }


def compute(
    current: List[Dict[str, Any]],
    baseline: Optional[List[Dict[str, Any]]],
) -> List[Anomaly]:
    """Compare current vs baseline cluster lists. Returns ordered anomaly list.

    Cluster keys consumed: `label`, `size`, `avg_rating`.
    """
    out: List[Anomaly] = []
    baseline_by_label = {c["label"]: c for c in (baseline or [])}
    current_labels = {c["label"] for c in current}

    for c in current:
        b = baseline_by_label.get(c["label"])
        cur_n = c["size"]
        base_n = b["size"] if b else 0
        delta_pct = ((cur_n - base_n) / max(1, base_n)) if base_n else 1.0
        abs_delta = cur_n - base_n
        is_complaint = c["avg_rating"] < 3.5
        sev = (
            "CRITICAL" if is_complaint and cur_n >= 50
            else "MAJOR" if is_complaint
            else "INFO"
        )

        if not b:
            out.append(Anomaly(
                label=c["label"],
                kind="emerging",
                current_n=cur_n,
                baseline_n=0,
                delta_pct=delta_pct,
                severity=sev,
                note=f"First time in top themes (n={cur_n}).",
            ))
        elif abs_delta >= MIN_ABS_DELTA and delta_pct >= SPIKE_PCT:
            out.append(Anomaly(
                label=c["label"],
                kind="spike",
                current_n=cur_n,
                baseline_n=base_n,
                delta_pct=delta_pct,
                severity=sev,
                note=f"+{int(delta_pct * 100)}% WoW (n {base_n} → {cur_n}).",
            ))
        elif abs_delta <= -MIN_ABS_DELTA and delta_pct <= DROP_PCT:
            # A drop in complaints is good news.
            note = (
                f"{int(delta_pct * 100)}% WoW — likely fix from prior sprint working."
                if is_complaint else
                f"{int(delta_pct * 100)}% WoW. Engagement dipped."
            )
            out.append(Anomaly(
                label=c["label"],
                kind="drop",
                current_n=cur_n,
                baseline_n=base_n,
                delta_pct=delta_pct,
                severity="INFO",
                note=note,
            ))

    # Resolved themes: present in baseline, missing from current.
    if baseline:
        for b in baseline:
            if b["label"] not in current_labels:
                out.append(Anomaly(
                    label=b["label"],
                    kind="resolved",
                    current_n=0,
                    baseline_n=b["size"],
                    delta_pct=-1.0,
                    severity="INFO",
                    note=f"Dropped out of top themes (was n={b['size']} last week).",
                ))

    # Sort: emerging + spikes for complaint themes first, then everything else.
    rank = {"CRITICAL": 0, "MAJOR": 1, "INFO": 2}
    out.sort(key=lambda a: (rank.get(a.severity, 9), -a.current_n))
    return out


def attach_wow_to_clusters(
    current: List[Dict[str, Any]],
    baseline: Optional[List[Dict[str, Any]]],
) -> None:
    """Mutate `current` clusters to add `wow_pct` and `wow_kind` fields."""
    base_by_label = {c["label"]: c for c in (baseline or [])}
    for c in current:
        b = base_by_label.get(c["label"])
        if not b:
            c["wow_pct"] = None
            c["wow_kind"] = "emerging"
            continue
        delta = (c["size"] - b["size"]) / max(1, b["size"])
        c["wow_pct"] = round(delta * 100)
        if c["size"] - b["size"] >= MIN_ABS_DELTA and delta >= SPIKE_PCT:
            c["wow_kind"] = "spike"
        elif c["size"] - b["size"] <= -MIN_ABS_DELTA and delta <= DROP_PCT:
            c["wow_kind"] = "drop"
        else:
            c["wow_kind"] = "steady"
