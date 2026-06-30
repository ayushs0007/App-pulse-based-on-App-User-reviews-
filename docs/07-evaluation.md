# 07 · Evaluation Framework

> Files: [`pipeline/evals.py`](../pipeline/evals.py)

## Why evaluate at all?

LLM outputs drift silently. A prompt that worked last month produces subtly
different output today because the model was retrained, the temperature
changed, or your prompt template grew an extra line. Without evals you only
notice the drift when a user complains.

Evals are the **regression test suite for non-deterministic code**.

## The three techniques worth knowing

| Technique | What it catches | Cost | When to use |
|---|---|---|---|
| **Golden-set checks** | Shape/schema bugs, contract drift | Free (no LLM) | On every commit |
| **LLM-as-judge** | Quality drift, tone, groundedness | One LLM call per case | Nightly |
| **Heuristic metrics** | Length blowups, missing fields | Free | On every run |

This module implements all three.

## 1. Golden-set checks

You write small assertions on known inputs:

```python
Case(
    name="weekly_pulse: summary <= 250 words",
    input={"week": "test"},
    asserts=[lambda out: len(out["summary"].split()) <= 260],
)
```

Then run them in CI. If the new prompt suddenly outputs 400 words, the
case fails and the PR is blocked. These are cheap and you should write
~20 of them.

**Pattern names you'll see in the wild:**

- **OpenAI Evals**: YAML-defined cases + a registry of "completion" or
  "match" assertions.
- **Anthropic Inspect**: Python-native dataset / scorer / solver triplet.
- **LangSmith eval**: hosted, with traces and aggregation.

What we have is Inspect-shaped, kept minimal.

### Tuning knobs
- Add more cases to `golden_cases()`. Each case = one assertion.
- For weak assertions, use `assertAlmostEqual`-style tolerances.
- Store the input fixtures under `evals/golden/` (the directory is
  referenced but currently empty — easy place to add real review JSONs).

## 2. LLM-as-judge

Use a *stronger* model to score the *weaker* model's output. The judge sees
the output (not the reference) and rates it on a fixed rubric. Key rules
from the literature:

1. **Score on a numeric scale** (1-5 or 0-1). Free-text scores don't
   aggregate.
2. **Define the rubric in the prompt**. "Score groundedness" means nothing
   to an LLM — explain what groundedness means in this task.
3. **Output JSON** so you can parse and aggregate.
4. **Pick a judge ≥ 1 tier above the runtime model**. We're running Llama
   3.1 70B; the judge should be GPT-4o / Opus 4 / similar.
5. **Watch for position bias** in pairwise judging — randomise A vs B.

Our judge prompt template lives in `JUDGE_PROMPT_TMPL`. Edit it to add
criteria like `concision` or `cultural-appropriateness` for Indian users.

### Tuning knobs
- Change the model in `pipeline/llm.py::GROQ_MODEL` for the runner,
  but the judge should ideally call a *different* provider — e.g. Anthropic
  Claude — to avoid the same model judging itself. Add a `GROQ_JUDGE_MODEL`
  env var.
- Add a "rubric" file under `evals/rubrics/` and load by name.
- Calibrate the judge by running 20 cases manually scored, comparing.

## 3. Heuristic metrics

The unsexy but high-leverage signals:

```python
{
    "word_count": len(summary.split()),
    "has_recommendation": bool(pulse.get("recommendation")),
    "action_count": len(pulse.get("actions", [])),
    ...
}
```

These run in microseconds and catch 80% of regressions. The word-count
metric alone has saved my bacon multiple times when a prompt change made
the summary balloon.

## Wire it into CI

```yaml
# .github/workflows/evals.yml
- name: Run evals
  run: python -m pipeline.evals
  env:
    GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
```

Set the job to fail if any golden case fails or if a judge score drops > 1
point from the last commit.

## Going deeper

- **Pairwise preference**: instead of absolute scores, ask the judge "which
  of A or B is better?" Then run an Elo / Bradley-Terry rating across
  prompt variants. This is how the LMSYS chatbot arena works.
- **Faithfulness eval**: extract claims from the summary, check each
  against the source reviews. Tools: `ragas`, `deepeval`.
- **Drift dashboard**: store every eval run's scores in a SQLite, plot
  trends. Streamlit gives you this in 50 lines.
