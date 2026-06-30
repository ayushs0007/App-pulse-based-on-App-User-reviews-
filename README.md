# Groww Pulse

> End-to-end AI workflow that turns raw Groww app reviews into a structured
> Weekly Pulse — scraper → embeddings → K-Means clusters → RAG summary →
> MCP-gated delivery to Google Docs + Gmail → React dashboard.

![Weekly Review screenshot](docs/screenshot.png)

This repo is **also a tutorial**. Every layer has a markdown lesson under
[`docs/`](./docs) explaining the *why* alongside the code:

| # | Lesson | What you learn |
|---|---|---|
| 01 | [The Scraper](docs/01-scraper.md) | Pulling reviews from Google Play, normalising, caching |
| 02 | [Embeddings + Clustering](docs/02-embeddings-clustering.md) | Sentence embeddings, K-Means, medoid quotes |
| 03 | [RAG](docs/03-rag.md) | Grounded generation, Groq, structured output via markers |
| 04 | [LangGraph](docs/04-langgraph.md) | State graphs, nodes, approval gates |
| 05 | [MCP](docs/05-mcp.md) | Model Context Protocol, Google Docs + Gmail tools |
| 06 | [Dashboard](docs/06-dashboard.md) | Vite + React + Tailwind, Flask proxy, email snapshot |
| 07 | [Evaluation Framework](docs/07-evaluation.md) | Golden sets, LLM-as-judge, heuristic metrics |
| 08 | [Guardrails](docs/08-guardrails.md) | PII redaction, prompt-injection, citation enforcement |
| 09 | [Prompting](docs/09-prompting.md) | System/user/assistant, few-shot, structured output, tuning |
| 10 | [Customisation](docs/10-customisation.md) | Point this pipeline at any app / language / region |

**Looking to change something?** See [`HACKING.md`](HACKING.md) — a single
jump table: "I want to change X → edit file Y line Z".

## Architecture

```
       ┌─ Google Play scraper ──┐
       │                        ▼
       │              ┌────────────────────────┐
       │              │  LangGraph pipeline    │
       │              │  scrape → embed →      │
       │              │  cluster → sentiment → │
       │              │  rag → fee → persist   │
       │              │     │                  │
       │              │     ▼  (gates)         │
       │              │  MCP: append to doc    │
       │              │  MCP: gmail draft      │
       │              └──────────┬─────────────┘
       │                         │
       │                JSON  ◄──┘
       │                  │
       │            ┌─────▼─────┐
       └────────────┤   Flask   │◄── React dashboard
                    │  /api/*   │
                    └───────────┘
```

## Quick start

```bash
# 1. Install Python deps
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\Activate on Windows
pip install -r requirements.txt

# 2. (Optional) Add a Groq key — without it, a fallback summariser is used
cp .env.example .env
# edit .env, set GROQ_API_KEY=...

# 3. Seed one run
python -m pipeline.run_weekly

# 4. Serve API
python -m api.app                # http://127.0.0.1:5050

# 5. Run dashboard
cd dashboard
npm install
npm run dev                      # http://127.0.0.1:5173
```

## Repo layout

```
groww-pulse/
├── pipeline/         # Python pipeline (scraper, embeddings, RAG, LangGraph)
├── api/              # Flask API serving the dashboard
│   └── data/runs/    # one JSON per weekly run + latest.json pointer
├── mcp_server/       # MCP server (Google Docs + Gmail)
├── dashboard/        # Vite + React UI
├── docs/             # Learning companion (per-layer markdown)
├── requirements.txt
└── .env.example
```

## Running with MCP

The pipeline calls `mcp_server/client.py` directly for in-process use. To
expose the same tools to a real MCP host (Claude Desktop, an agent, etc.),
add this to your host config:

```json
{
  "mcpServers": {
    "groww-pulse": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/absolute/path/to/groww-pulse"
    }
  }
}
```

See [`docs/05-mcp.md`](docs/05-mcp.md) for the Google OAuth setup.

## Approval gates

Two side-effecting actions exist behind explicit human-approval gates:

| Gate | Where | What happens |
|---|---|---|
| `gate_doc` | "Append to Doc" button in the email modal | Idempotent append to a shared Google Doc |
| `gate_email` | "Create Gmail Draft" button | Creates a Gmail draft (never sends) |

Nothing fires automatically. See `node_gate_doc` / `node_gate_email` in
[`pipeline/langgraph_flow.py`](pipeline/langgraph_flow.py).

## Licence

MIT.
