# Groww Pulse

I built this over a weekend after realising how much time product teams
spend manually reading app-store reviews. The idea: point a pipeline at
Groww's Google Play reviews, cluster the noise into themes, generate a
Weekly Pulse the team can actually act on, and surface it in a dashboard
that reads like a Sentry inbox rather than a wall of text.

**Live dashboard:** https://ayushs0007.github.io/App-pulse-based-on-App-User-reviews-/

_(The live version reads from static JSON I baked into the build — no
backend, no LLM calls. Approval-gated actions are dry-run only in static
mode. Clone the repo to run the full pipeline yourself.)_

![Weekly review dashboard](docs/screenshot.png)

---

## What it does

- **Scrapes 1000 newest Groww reviews** from Google Play and caches them.
- **Clusters them into 5 themes** using MiniLM sentence embeddings + K-Means,
  with keyword-driven labels ("High Brokerage Fees", "App Stability", …).
- **Compares this week vs last** — every theme gets a WoW delta, and I
  classify each into `spike`, `emerging`, `drop`, or `resolved`.
- **Generates a Weekly Pulse** (≤250 words, 3 prioritised actions) using
  Groq Llama-3.1-70B with a RAG prompt that cites real user quotes.
- **Picks "This Week's Move"** — a decision card with move, evidence,
  impact, confidence pill (Wilson-score), and suggested owner.
- **Delivers the report** via an MCP server that can append to a Google
  Doc and create a Gmail draft — both behind explicit approval gates.

## What I learned building it

Every layer has a short markdown lesson under [`docs/`](./docs) — that's
where I wrote down the theory + the specific tuning knobs I found while
iterating.

| # | Lesson | Topic |
|---|---|---|
| 01 | [Scraper](docs/01-scraper.md) | Google Play reviews, cache boundary |
| 02 | [Embeddings + Clustering](docs/02-embeddings-clustering.md) | Sentence embeddings, K-Means, medoid quotes |
| 03 | [RAG](docs/03-rag.md) | Grounded generation, Groq, marker-based parsing |
| 04 | [LangGraph](docs/04-langgraph.md) | State graphs, approval gates |
| 05 | [MCP](docs/05-mcp.md) | Model Context Protocol, Google Docs + Gmail |
| 06 | [Dashboard](docs/06-dashboard.md) | Vite + React + Tailwind, Flask proxy |
| 07 | [Evaluation](docs/07-evaluation.md) | Golden sets, LLM-as-judge, heuristics |
| 08 | [Guardrails](docs/08-guardrails.md) | PII, prompt injection, citation policing |
| 09 | [Prompting](docs/09-prompting.md) | System/user, few-shot, structured output |
| 10 | [Customisation](docs/10-customisation.md) | Point this at any product |
| 11 | [Agentic AI](docs/11-agentic-ai.md) | Where this repo sits on the agentic stack |

If you want to change something specific, [`HACKING.md`](HACKING.md) is a
jump table: *"I want to change X → file Y, line Z."*

## Running it locally

```bash
# 1. Install
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt

# 2. Optional — add a Groq key (a fallback works without one)
cp .env.example .env
# edit .env, set GROQ_API_KEY=...

# 3. Seed a run (also generates a synthetic baseline week for WoW deltas)
python -m pipeline.run_weekly --seed-baseline

# 4. Serve the API
python -m api.app                 # http://127.0.0.1:5050

# 5. Run the dashboard
cd dashboard
npm install
npm run dev                       # http://localhost:5173
```

## The architecture I ended up with

```
       ┌─ Google Play scraper ──┐
       │                        ▼
       │              ┌─────────────────────────┐
       │              │  LangGraph pipeline     │
       │              │  scrape → slice →       │
       │              │  embed → cluster →      │
       │              │  sentiment → language → │
       │              │  rag → fee →            │
       │              │  anomalies → decision → │
       │              │  persist                │
       │              │     │                   │
       │              │     ▼  (approval gates) │
       │              │  MCP: Google Docs       │
       │              │  MCP: Gmail draft       │
       │              └──────────┬──────────────┘
       │                         │
       │                JSON  ◄──┘
       │                  │
       │            ┌─────▼─────┐
       └────────────┤   Flask   │◄── React dashboard
                    │  /api/*   │
                    └───────────┘
```

## Repo layout

```
groww-pulse/
├── pipeline/          Python pipeline (14 modules)
├── api/               Flask API + persisted weekly runs
├── mcp_server/        MCP server (Google Docs + Gmail)
├── dashboard/         Vite + React + Tailwind UI
├── docs/              Per-layer learning lessons (01-11)
├── HACKING.md         "I want to change X → edit file Y line Z"
├── requirements.txt
└── .env.example
```

## Wiring MCP into a host (Claude Desktop, agents, etc.)

The pipeline calls the MCP tools in-process via
[`mcp_server/client.py`](mcp_server/client.py). To expose the same tools to
an external host, add this to `claude_desktop_config.json` (or your host's
equivalent):

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

The OAuth setup for Google Docs / Gmail is walked through in
[`docs/05-mcp.md`](docs/05-mcp.md).

## Approval gates (nothing auto-sends)

Two side-effecting actions live behind explicit human-approval gates:

| Gate | Triggered from | What happens |
|---|---|---|
| `gate_doc` | "Append to Doc" in the dashboard | Idempotent append to a shared Google Doc |
| `gate_email` | "Create Gmail Draft" in the dashboard | Creates a Gmail draft (never sends) |

Every side-effect is opt-in. See `node_gate_doc` / `node_gate_email` in
[`pipeline/langgraph_flow.py`](pipeline/langgraph_flow.py).

## Licence

MIT.
