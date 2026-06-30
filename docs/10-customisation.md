# 10 · Customisation — Point this at any product

The pipeline is generic. Most of what looks "Groww-specific" is one of:
- a Play Store app id
- a list of keywords (clustering, fee detection)
- a couple of prompt templates

Here's how to swap each piece.

## 1. Point at a different app

`pipeline/scraper.py:13`:

```python
GROWW_APP_ID = "com.nextbillion.groww"
```

Replace with any Google Play package id. To find one: open the app's Play
Store URL, the id is the `?id=` querystring (e.g. `?id=in.zerodha.kite`).

Also change `country` and `lang` to match the target user base:

```python
fetch_reviews(app_id="in.zerodha.kite", country="in", lang="en", count=2000)
```

## 2. Re-keyword the clusters

`pipeline/clustering.py:27` — `KEYWORD_MAP`. The dict keys are theme slugs;
the values are the keywords that vote each cluster into that theme.

For a food-delivery app you might:

```python
KEYWORD_MAP = {
    "delivery": ["delivery", "late", "delivered", "rider", "delayed"],
    "food_quality": ["cold", "stale", "spoiled", "fresh", "tasty"],
    "pricing": ["price", "expensive", "cost", "charged", "fee"],
    "app_bugs": ["crash", "loading", "freeze", "bug"],
    "support": ["support", "reply", "ticket", "refund"],
}
THEME_NAMES = {
    "delivery": "Delivery / Logistics",
    "food_quality": "Food Quality",
    "pricing": "Pricing Complaints",
    "app_bugs": "App Stability",
    "support": "Customer Support",
}
```

## 3. Re-keyword the fee detector

`pipeline/fee_explainer.py:67` — `FEE_KEYWORDS`. For a delivery app this
becomes "delivery fees, surge, charge". For a SaaS app maybe
"subscription, billing, refund".

Same file: `SOURCES` is the URL allowlist. Pin to YOUR product's official
help pages. The citation-check guardrail enforces this.

## 4. Reword the prompt templates

The prompts that drive output are in three places:

| Prompt | File | Variable |
|---|---|---|
| Weekly Pulse system | `pipeline/rag.py` | `WEEKLY_PULSE_SYSTEM` |
| Weekly Pulse user | `pipeline/rag.py::weekly_pulse` | inline `prompt` |
| Fee Explainer system | `pipeline/fee_explainer.py` | `SYSTEM` |
| Fee Explainer user | `pipeline/fee_explainer.py::fee_explainer` | inline `prompt` |
| LLM judge | `pipeline/evals.py` | `JUDGE_PROMPT_TMPL` |

See [09-prompting.md](09-prompting.md) for what to change.

## 5. Re-template the decision card

`pipeline/decision.py:24-50` — `MOVE_TEMPLATES` and `OWNER_BY_THEME`. Make
sure your theme labels (from clustering) match the keys here.

Example for a delivery product:

```python
MOVE_TEMPLATES = {
    "Delivery / Logistics": "Investigate the rider routing model for the city with the biggest spike",
    "Food Quality":         "Audit the top-3 restaurants by complaint volume",
    ...
}
OWNER_BY_THEME = {
    "Delivery / Logistics": "@logistics-ops",
    "Food Quality":         "@partner-success",
    ...
}
```

## 6. Switch the LLM

`.env`:

```bash
GROQ_API_KEY=...
GROQ_MODEL=llama-3.1-70b-versatile     # default
# GROQ_MODEL=llama-3.1-8b-instant      # cheaper, faster, dumber
# GROQ_MODEL=llama-3.3-70b-versatile   # newer
```

To use a different provider, replace `pipeline/llm.py::complete`. The
function's external contract is `(prompt, system, max_tokens) -> str` — so
you can swap to OpenAI, Anthropic, Together, or self-hosted vLLM without
changing any caller.

```python
# OpenAI example
from openai import OpenAI
client = OpenAI()
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
    temperature=0.3,
    max_tokens=max_tokens,
)
return resp.choices[0].message.content.strip()
```

## 7. Add a language

`pipeline/lang.py` — extend `HINGLISH_TOKENS` or add new buckets. For
Tamil reviews you'd add a `ta` bucket with a Devanagari-equivalent regex
for Tamil Unicode (`[஀-௿]`).

## 8. Add a new MCP integration (e.g. Slack, Linear, Notion)

The MCP server in `mcp_server/server.py` is one file. Steps to add Slack:

1. Define a new `Tool` in `list_tools`:

```python
Tool(
    name="post_to_slack",
    description="Post the weekly pulse to a Slack channel. Idempotent on week_label.",
    inputSchema={
        "type": "object",
        "required": ["week_label", "summary", "channel"],
        "properties": {...}
    },
)
```

2. Add the handler in `call_tool`:

```python
elif name == "post_to_slack":
    res = post_to_slack_sync(arguments)
```

3. Implement `post_to_slack_sync` using `slack_sdk.WebClient`.

4. Add a `node_gate_slack` in `pipeline/langgraph_flow.py` mirroring
   `node_gate_doc` / `node_gate_email`. Wire it after the existing gates.

5. Add a button in `dashboard/src/components/DecisionCard.jsx` calling
   `api.approveGate('slack', week)`.

The pattern is: **one tool → one node → one gate → one button**. Always
approval-gated.

## 9. Change the dashboard layout

Most layout lives in
[`dashboard/src/components/WeeklyPulse.jsx`](../dashboard/src/components/WeeklyPulse.jsx).
The components are:

- `<HeroStrip />` — top dark banner with what-changed
- `<DecisionCard />` — "This Week's Move"
- `<AnomalyInbox />` — what changed since last week
- `<ConfidencePill />` — small pills
- `<ThemeDrilldown />` — modal for inspecting a theme

Tailwind classes do the visual styling. The two custom colours are in
`tailwind.config.js`:

```js
colors: {
  ink:   { 900: '#0e1729', 800: '#16213a' },
  groww: { 500: '#00d09c' },
}
```

Change `groww.500` to rebrand for any product.

## 10. Set up Gmail / Google Docs auth

Step-by-step in [05-mcp.md](05-mcp.md). Summary:

1. Cloud Console → create project
2. Enable Docs API + Gmail API
3. OAuth consent screen → External, add yourself as a test user
4. Credentials → OAuth Client ID → Desktop app → download
5. Save as `mcp_server/credentials.json`
6. First run opens a browser to consent; subsequent runs reuse `token.json`

Until you do this, the gates return `{"status": "dry_run"}` so the
pipeline still works.

## 11. Schedule it

```cron
0 9 * * 1   cd /repo && python -m pipeline.run_weekly
```

That fires every Monday at 9am. Add `--approve-doc --approve-email` if you
trust the pipeline enough to auto-fire MCP — usually you don't; you keep
the approval gates and click them from the dashboard.

## What's intentionally NOT customisable

- **The decision-card structure** (move, why, impact, confidence, owner) —
  removing any field weakens the recommendation. Add new fields if needed.
- **Confidence pill thresholds** (Wilson 0.08 / 0.03) — they're set to
  cap false-positives. Loosening them produces noisy alerts.
- **The "n ≥ 30 chars" substantive filter** — relaxing it brings back
  the "good"/"best" cluster problem.

All three are tunable but the defaults exist for good reasons. Move them
and re-run the eval suite ([07-evaluation.md](07-evaluation.md)).
