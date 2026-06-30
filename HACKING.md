# HACKING.md — Where to edit what

A jump table for the impatient. **"Where do I change X?" → here.**

## I want to change the model / output style

| I want to … | File:line | Change |
|---|---|---|
| Use a different LLM provider | [`pipeline/llm.py:24`](pipeline/llm.py) | Replace `complete()` body |
| Switch Groq model | `.env` | `GROQ_MODEL=llama-3.1-8b-instant` |
| Make output more creative | [`pipeline/llm.py:55`](pipeline/llm.py) | `temperature=0.7` |
| Cap summary at 150 words | [`pipeline/rag.py:43`](pipeline/rag.py) | "≤ 250 words" → "≤ 150 words" |
| Reword the persona | [`pipeline/rag.py:14`](pipeline/rag.py) | `WEEKLY_PULSE_SYSTEM` |
| Disable guardrails for testing | call `complete(..., apply_guardrails=False)` | Per-call kwarg |

## I want to change what gets clustered

| I want to … | File:line |
|---|---|
| Cluster more / fewer themes | [`pipeline/clustering.py::cluster(..., k=5)`](pipeline/clustering.py) |
| Add a new theme keyword | [`pipeline/clustering.py:21`](pipeline/clustering.py) — `KEYWORD_MAP` |
| Filter shorter / longer reviews | [`pipeline/langgraph_flow.py:37`](pipeline/langgraph_flow.py) — `SUBSTANTIVE_MIN_LEN` |
| Use a different embedding model | [`pipeline/embeddings.py:15`](pipeline/embeddings.py) — `MODEL_NAME` |
| Switch K-Means → HDBSCAN | [`pipeline/clustering.py::cluster`](pipeline/clustering.py) — replace `KMeans` |

## I want to change the dashboard

| I want to … | File |
|---|---|
| Reword the "This Week's Move" copy | [`pipeline/decision.py:46`](pipeline/decision.py) — `MOVE_TEMPLATES` |
| Reassign owners | [`pipeline/decision.py:32`](pipeline/decision.py) — `OWNER_BY_THEME` |
| Add a new tab | [`dashboard/src/components/Sidebar.jsx`](dashboard/src/components/Sidebar.jsx) + a new component |
| Change brand color | [`dashboard/tailwind.config.js`](dashboard/tailwind.config.js) — `groww.500` |
| Adjust the WoW thresholds | [`pipeline/anomalies.py:24`](pipeline/anomalies.py) — `SPIKE_PCT`, `DROP_PCT`, `MIN_ABS_DELTA` |
| Change confidence cut-offs | [`pipeline/confidence.py:30`](pipeline/confidence.py) — Wilson `0.08` / `0.03` |

## I want to add a new MCP tool (Slack, Linear, Notion, …)

Five edits, one pattern:

1. **Tool declaration**: [`mcp_server/server.py::list_tools`](mcp_server/server.py)
2. **Tool handler**: [`mcp_server/server.py::call_tool`](mcp_server/server.py)
3. **Side-effect function**: e.g. `post_to_slack_sync` next to `append_to_doc_sync`
4. **Pipeline node**: [`pipeline/langgraph_flow.py::node_gate_*`](pipeline/langgraph_flow.py) — add `node_gate_slack`
5. **Dashboard button**: [`dashboard/src/components/DecisionCard.jsx`](dashboard/src/components/DecisionCard.jsx) — add a button that calls `api.approveGate('slack', week)`

See [10-customisation.md](docs/10-customisation.md) §8 for the full walkthrough.

## I want to change how reports are sent

| I want to … | File |
|---|---|
| Change Gmail recipient | `.env` — `GMAIL_TO` |
| Change Google Doc target | `.env` — `GOOGLE_DOC_ID` |
| Edit email HTML template | [`api/app.py::_render_email_html`](api/app.py) |
| Edit Google Doc append format | [`mcp_server/server.py::append_to_doc_sync`](mcp_server/server.py) |
| Add a Slack post step | See "add a new MCP tool" above |

## I want to evaluate / regression-test prompts

| I want to … | File |
|---|---|
| Add a golden-set case | [`pipeline/evals.py::golden_cases`](pipeline/evals.py) |
| Change the LLM-judge rubric | [`pipeline/evals.py::JUDGE_PROMPT_TMPL`](pipeline/evals.py) |
| Run the suite | `python -m pipeline.evals` |

## I want to change a guardrail

| I want to … | File |
|---|---|
| Add a PII pattern | [`pipeline/guardrails.py:30`](pipeline/guardrails.py) |
| Add an injection phrase | [`pipeline/guardrails.py:50`](pipeline/guardrails.py) — `INJECTION_PHRASES` |
| Swap toxicity list for a model | [`pipeline/guardrails.py::content_filter`](pipeline/guardrails.py) |
| Pin a new allowed URL | [`pipeline/fee_explainer.py:15`](pipeline/fee_explainer.py) — `SOURCES` |

## I want to point this at a different app

See [docs/10-customisation.md](docs/10-customisation.md) §1-3.

## I want to learn the theory

Read in order:

1. [`docs/01-scraper.md`](docs/01-scraper.md) — Google Play scraping
2. [`docs/02-embeddings-clustering.md`](docs/02-embeddings-clustering.md) — sentence embeddings, K-Means
3. [`docs/03-rag.md`](docs/03-rag.md) — RAG, Groq, prompt parsing
4. [`docs/04-langgraph.md`](docs/04-langgraph.md) — state machines, gates
5. [`docs/05-mcp.md`](docs/05-mcp.md) — Model Context Protocol, OAuth setup
6. [`docs/06-dashboard.md`](docs/06-dashboard.md) — Vite + React + Flask proxy
7. [`docs/07-evaluation.md`](docs/07-evaluation.md) — golden sets, LLM judge
8. [`docs/08-guardrails.md`](docs/08-guardrails.md) — PII, injection, citation
9. [`docs/09-prompting.md`](docs/09-prompting.md) — system/user/assistant, few-shot, tools
10. [`docs/10-customisation.md`](docs/10-customisation.md) — point this at any product

## Daily ops

```bash
# Refresh the cache + rebuild this week's run (uses last week as baseline)
python -m pipeline.run_weekly --seed-baseline

# Quick eval
python -m pipeline.evals

# Run the dashboard
python -m api.app           # terminal 1
cd dashboard && npm run dev # terminal 2 → http://localhost:5173
```

## Where files live

```
pipeline/        ← all backend logic
  scraper.py        Google Play fetcher (lines: 79)
  embeddings.py     sentence-transformer wrapper (45)
  clustering.py     K-Means + keyword labels (105)
  sentiment.py      rating-bucket sentiment (32)
  rag.py            Weekly Pulse generation (140)
  fee_explainer.py  fee-related RAG (85)
  lang.py           Hindi / Hinglish detection (60)
  anomalies.py      WoW delta + spike/drop detection (115)
  decision.py       This-Week's-Move generator (140)
  confidence.py     Wilson-score pill (32)
  evals.py          golden-set + judge + heuristics (170)
  guardrails.py     PII + injection + content + citation (115)
  llm.py            Groq client + fallback (85)
  langgraph_flow.py LangGraph state machine (220)
  run_weekly.py     CLI entry (60)

api/
  app.py            Flask serving the dashboard (155)
  data/runs/        Persisted per-week JSON
  data/sample_reviews.json  Cached scrape

mcp_server/
  server.py         MCP server with Google Docs + Gmail tools
  client.py         In-process bypass for the pipeline

dashboard/        ← React UI (Vite + Tailwind)
  src/App.jsx
  src/components/*  WeeklyPulse, Sidebar, DecisionCard, AnomalyInbox, ...

docs/             ← per-layer learning lessons (01-10)
```
