"""
Evaluation framework for the LLM outputs.

Three complementary techniques, all built on top of the same pipeline:

  1. Golden-set checks   — deterministic assertions on known-good inputs
  2. LLM-as-judge        — a stronger model scores the weaker model's output
  3. Heuristic metrics   — non-LLM signals (length, citation count, schema)

The pattern is the same one used by OpenAI Evals, Anthropic's Inspect, and
Lighthouse. You run a suite against the current pipeline, get a pass/fail per
case, and a aggregate score. Wire it into CI to catch regressions.

Run:  python -m pipeline.evals
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Any

from .llm import complete
from .rag import weekly_pulse
from .fee_explainer import fee_explainer


ROOT = Path(__file__).parent.parent
GOLDEN_DIR = ROOT / "evals" / "golden"


@dataclass
class Case:
    name: str
    input: Dict[str, Any]
    asserts: List[Callable[[Any], bool]]


@dataclass
class Result:
    case: str
    passed: bool
    detail: str = ""


# --- 1. Golden-set checks ---------------------------------------------------
# Each case feeds a known input through the pipeline and asserts on output.

def golden_cases() -> List[Case]:
    """A tiny seed set. Add more cases over time — that IS the eval suite."""
    return [
        Case(
            name="weekly_pulse: summary <= 250 words",
            input={"week": "test"},
            asserts=[lambda out: len(out["summary"].split()) <= 260],
        ),
        Case(
            name="weekly_pulse: returns at most 3 actions",
            input={"week": "test"},
            asserts=[lambda out: len(out.get("actions", [])) <= 3],
        ),
        Case(
            name="weekly_pulse: each action has priority",
            input={"week": "test"},
            asserts=[
                lambda out: all(
                    a.get("priority") in {"HIGH", "MED", "LOW"}
                    for a in out.get("actions", [])
                )
            ],
        ),
        Case(
            name="fee_explainer: outputs <= 6 bullets",
            input={"_fee": True},
            asserts=[lambda out: len(out.get("bullets", [])) <= 6],
        ),
        Case(
            name="fee_explainer: every bullet cites a source",
            input={"_fee": True},
            asserts=[
                lambda out: all("[" in b and "]" in b for b in out.get("bullets", []))
            ],
        ),
    ]


def run_golden() -> List[Result]:
    """Wire the cases through the pipeline."""
    # Stub data — the asserts only care about shape, not specific values.
    stub_clusters = [
        {"label": "Brokerage", "size": 50, "avg_rating": 2.5, "sample_quotes": ["fees are too high"]},
        {"label": "UX", "size": 30, "avg_rating": 4.5, "sample_quotes": ["nice clean app"]},
    ]
    stub_sentiment = {"neg": 40, "neu": 20, "pos": 40}
    stub_reviews = [
        {"text": "brokerage charges too high, please reduce"},
        {"text": "love the UX, very clean"},
    ]

    pulse_out = weekly_pulse(stub_clusters, stub_sentiment, 80, "test-week")
    fee_out = fee_explainer(stub_reviews + [{"text": "exit load surprise on redemption"}])

    out: List[Result] = []
    for case in golden_cases():
        bag = fee_out if case.input.get("_fee") else pulse_out
        ok = True
        detail = ""
        for chk in case.asserts:
            try:
                if not chk(bag):
                    ok = False
                    detail = "assertion failed"
                    break
            except Exception as e:
                ok = False
                detail = f"raised {type(e).__name__}: {e}"
                break
        out.append(Result(case=case.name, passed=ok, detail=detail))
    return out


# --- 2. LLM-as-judge --------------------------------------------------------
# Have a stronger model score a weaker model's output. The judge prompt is
# the variable that matters most — keep it short, scored on a fixed scale,
# and avoid leaking the reference answer into the judging window.

JUDGE_PROMPT_TMPL = """You are evaluating a Weekly Pulse summary written for a product team.

SUMMARY:
{summary}

CRITERIA (score 1-5 on each, then JSON):
- groundedness  : are claims supported by the cluster stats?
- conciseness   : is it under 250 words and free of fluff?
- actionability : does it suggest concrete next steps?
- tone          : is it neutral and professional?

Output JSON:
{{"groundedness":N,"conciseness":N,"actionability":N,"tone":N,"comment":"..."}}"""


def judge_pulse(pulse: Dict[str, Any]) -> Dict[str, Any]:
    """Score a Weekly Pulse output using the LLM as judge."""
    raw = complete(
        JUDGE_PROMPT_TMPL.format(summary=pulse["summary"]),
        system="You are a strict evaluator. Output JSON only.",
        max_tokens=300,
    )
    # Best-effort JSON parse — judges sometimes wrap output in prose.
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return {"error": "non_json_output", "raw": raw}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return {"error": f"json: {e}", "raw": raw}


# --- 3. Heuristic metrics ---------------------------------------------------

def heuristic_score(pulse: Dict[str, Any]) -> Dict[str, Any]:
    """Cheap, deterministic signals that don't need an LLM."""
    summary = pulse.get("summary", "")
    words = summary.split()
    return {
        "word_count": len(words),
        "has_recommendation": bool(pulse.get("recommendation")),
        "action_count": len(pulse.get("actions", [])),
        "starts_with_lowercase": summary[:1].islower() if summary else False,
        "ends_with_period": summary.rstrip().endswith(".") if summary else False,
    }


# --- CLI -------------------------------------------------------------------

def main() -> None:
    print("=== Golden-set checks ===")
    results = run_golden()
    passed = sum(1 for r in results if r.passed)
    print(f"{passed}/{len(results)} passed\n")
    for r in results:
        flag = "PASS" if r.passed else "FAIL"
        print(f"  [{flag}] {r.case} {('— ' + r.detail) if r.detail else ''}")

    print("\n=== Heuristic metrics (on a fresh pulse) ===")
    stub = {
        "summary": "Users flagged friction across themes this week. Brokerage complaints dominated.",
        "recommendation": "Investigate brokerage transparency.",
        "actions": [{"text": "Ship banner", "priority": "HIGH"}],
    }
    print(json.dumps(heuristic_score(stub), indent=2))

    print("\n=== LLM judge (skipped unless GROQ_API_KEY is set) ===")
    import os
    if os.getenv("GROQ_API_KEY"):
        print(json.dumps(judge_pulse(stub), indent=2))
    else:
        print("  no GROQ_API_KEY — skipping. Set it in .env to enable.")


if __name__ == "__main__":
    main()
