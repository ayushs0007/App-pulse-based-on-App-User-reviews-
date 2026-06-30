"""CLI entry point — `python -m pipeline.run_weekly`.

By default runs the current week's pipeline. Pass `--seed-baseline` to also
generate a synthesised previous-week run from the older half of the cached
reviews, so the WoW deltas have something to compare against.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone

from .langgraph_flow import run


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", default=None, help="ISO week label like 2026-W25")
    ap.add_argument("--approve-doc", action="store_true")
    ap.add_argument("--approve-email", action="store_true")
    ap.add_argument(
        "--seed-baseline",
        action="store_true",
        help="Also produce a synthetic previous-week run from older reviews.",
    )
    args = ap.parse_args()

    iso = datetime.now(timezone.utc).isocalendar()
    week_label = args.week or f"{iso.year}-W{iso.week:02d}"
    # Previous ISO week (works around year boundaries).
    last_dt = datetime.now(timezone.utc) - timedelta(days=7)
    last_iso = last_dt.isocalendar()
    last_week_label = f"{last_iso.year}-W{last_iso.week:02d}"

    if args.seed_baseline:
        print(f"Seeding baseline week {last_week_label} from older reviews ...")
        run(
            week_label=last_week_label,
            slice_from=500,
            slice_to=1000,
            _is_baseline_run=True,
        )

    print(f"Running current week {week_label} ...")
    out = run(
        week_label=week_label,
        baseline_week_label=last_week_label if args.seed_baseline else None,
        slice_to=500 if args.seed_baseline else None,
        approve_doc=args.approve_doc,
        approve_email=args.approve_email,
    )

    print(json.dumps({
        "run_id": out.get("run_id"),
        "themes": [c["label"] for c in out.get("clusters", [])],
        "anomalies": [a.get("label") + ":" + a.get("kind") for a in out.get("anomalies", [])],
        "decision": out.get("decision", {}).get("move"),
        "owner": out.get("decision", {}).get("owner"),
        "confidence": out.get("decision", {}).get("confidence"),
    }, indent=2))


if __name__ == "__main__":
    main()
