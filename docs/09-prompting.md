# 09 · Prompting (Theory + Practice)

> Files: [`pipeline/rag.py`](../pipeline/rag.py),
> [`pipeline/fee_explainer.py`](../pipeline/fee_explainer.py),
> [`pipeline/decision.py`](../pipeline/decision.py),
> [`pipeline/evals.py`](../pipeline/evals.py) (the judge prompt)

## The mental model

A prompt is **three things stitched together**:

```
┌────────────────┐
│ system message │  ← who you are, your role, hard rules
├────────────────┤
│ context/facts  │  ← retrieved data, examples, constraints
├────────────────┤
│ user instruct  │  ← the actual ask
└────────────────┘
```

Modern chat APIs accept these as separate `messages`. The model treats the
**system** message with higher trust than the **user** message — that's
where you put policy ("Never make up URLs", "Output 6 bullets").

## How our pipeline uses it

### RAG.weekly_pulse

```python
WEEKLY_PULSE_SYSTEM = (
    "You are a product analyst writing the Weekly Pulse for the Groww team. "
    "Be concise. Cite real user verbatims. Never invent numbers or features."
)

prompt = f"""Week: {week_label}
Total reviews: {total}
Sentiment: {sentiment['neg']}% neg, {sentiment['neu']}% neu, {sentiment['pos']}% pos

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
```

What's working here:

1. **Persona in system** — "product analyst" anchors tone.
2. **Explicit budget** — "<= 250 words" is enforceable; the judge will
   reject if exceeded.
3. **Numbered output structure** — the model knows there are 3 parts.
4. **Section markers** (`RECOMMENDATION:`, `ACTIONS:`) make parsing
   trivial. This is **poor-man's structured output**.
5. **Hard format** for actions (`- … | priority: HIGH`) — a regex can
   trust this.

## The big knobs

| Knob | Effect | Where to change |
|---|---|---|
| **Temperature** | Higher = creative, lower = consistent | `pipeline/llm.py::complete` |
| **Max tokens** | Caps output length | Same |
| **System message** | Sets behaviour boundary | Per-call: `WEEKLY_PULSE_SYSTEM`, `SYSTEM` in fee_explainer |
| **Examples (few-shot)** | Teach a format by showing 2-3 examples | Add to prompt before "Write a Weekly Pulse note..." |
| **Structured output** | JSON mode / tool-use for guaranteed shape | Swap markers for JSON schema |
| **Model size** | 8B vs 70B vs 405B | `GROQ_MODEL` in `.env` |

### Why we picked these

- **Temperature 0.3** — we want consistency week-to-week. Higher and the
  same data would produce different "Weekly Pulses".
- **No few-shot examples** — Llama 3.1 70B follows numbered instructions
  well. Few-shot would help an 8B model.
- **Marker-based parsing** (not JSON) — markers degrade gracefully when the
  model drops a section. JSON mode is all-or-nothing.

## Tuning prompts for *your* users

This is the meat of customisation. A few moves:

### 1. Change the persona

```diff
- "You are a product analyst writing the Weekly Pulse for the Groww team."
+ "You are a fintech support lead writing a daily customer brief."
```

The persona controls vocabulary, urgency, and what gets prioritised.

### 2. Constrain the audience

```diff
+ "Audience: a non-technical leadership team in India. Avoid jargon."
```

This single line measurably changes output complexity. Test with the
heuristic `flesch_kincaid_grade(summary)` if you want a number.

### 3. Add few-shot examples

```python
EXAMPLES = """Example output:
Users felt the recent revamp left fees opaque. Brokerage complaints
grew 40% week-over-week, driven by intraday traders confused by ...
RECOMMENDATION: Ship a brokerage tooltip in the order flow.
ACTIONS:
- Add a brokerage tooltip | priority: HIGH
- Run a help-centre campaign | priority: MED
- Update charging schedule on the website | priority: LOW
"""

prompt = EXAMPLES + actual_prompt
```

Few-shot dominates instruction-following for smaller models and for niche
domains (legal, medical, regional language).

### 4. Switch to JSON mode

If you trust your model's structured output (Groq's Llama supports
`response_format={"type": "json_object"}`), redesign the prompt to demand
a JSON shape. Trade-off: parser is simpler but the model occasionally
returns invalid JSON, breaking the whole call.

### 5. Bind a tool (function calling)

Instead of "write a summary", define:

```python
tools = [{
    "type": "function",
    "function": {
        "name": "emit_weekly_pulse",
        "parameters": {
            "type": "object",
            "properties": {
                "summary":        {"type": "string", "maxLength": 1200},
                "recommendation": {"type": "string"},
                "actions":        {"type": "array", "items": {...}}
            },
            "required": ["summary", "recommendation"]
        }
    }
}]
```

Now the model *can't* return free text. It returns the function call with
typed arguments. This is the modern best practice for structured tasks.

## The Fee Explainer prompt — closed-world citations

```python
SYSTEM = (
    "You are explaining Indian broking fees neutrally. Use ONLY the sources "
    "provided. If unsure, say so. Output 6 bullet points, no marketing."
)

prompt = f"""Users are confused about Groww's fees. Real complaints:

{quoted}

Official sources you may cite:
[1] {SOURCES[0]['title']} — {SOURCES[0]['url']}
[2] ...

Write exactly 6 short bullet points (max 20 words each) that:
- Explain the specific fees users are confused about
- Are neutral and factual (no marketing language)
- Cite a source by number in square brackets at the end, e.g. [1]
"""
```

Key moves:

1. **"Use ONLY the sources provided"** — sets the closed-world boundary.
2. **Numbered allowlist** — the prompt itself defines what [1], [2], [3]
   mean. No room for the model to invent [4].
3. **Citation check guardrail** ([08-guardrails.md](08-guardrails.md)) is
   the safety net under this prompt.

## Decision-card prompts → still rule-based (intentional)

`pipeline/decision.py` uses templated strings, not the LLM, for the
recommendation. Why?

- **Predictability**: a PM expects "Patch the crash hotspots" every time
  App Stability spikes. LLM variation here would be a bug.
- **Owner mapping** is policy, not creative work.
- **Speed**: zero LLM calls per dashboard load.

If you want LLM-generated recommendations later, the entry point is
`MOVE_TEMPLATES`. Replace the dict lookup with a `complete()` call that
takes `{theme, n, baseline_n, avg_rating}` and returns the imperative move
sentence. Keep the owner mapping rule-based.

## Common prompting mistakes (and the fixes)

| Mistake | Symptom | Fix |
|---|---|---|
| Vague persona | Generic, marketing-y output | Add a specific role + audience |
| No budget | Variable, sometimes very long output | "Output ≤ N words" |
| No format | Different shape every call | Section markers OR JSON mode |
| Stuffing context | Slow + the model ignores middle | RAG: retrieve only the relevant N |
| Trusting the model on facts | Hallucinated numbers, URLs | Closed-world allowlist + citation guard |
| Temperature too high | Inconsistent regression-style bugs | Drop to 0.2-0.4 for analytical tasks |
| Skipping evals | Silent drift | [07-evaluation.md](07-evaluation.md) |
