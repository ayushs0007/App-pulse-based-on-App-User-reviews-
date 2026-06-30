# 11 · Agentic AI — Concepts, Patterns, and How This Repo Embodies Them

This lesson is the "zoom out". Once you've read 01-10 you've seen the
parts. Now you'll see the *category*: what makes a system "agentic", what
patterns work, what's snake oil, and how every layer of this repo maps to
a named concept in the literature.

## 1. What "agentic" actually means

A regular LLM call:
```
user → LLM → answer
```

An agent:
```
goal → LLM → plan → take action → observe result → think again → ...
                       ↑                                            │
                       └────────────────────────────────────────────┘
                                    (loops until done)
```

Three things differentiate an agent from a chatbot:

1. **Tools** — it can take actions in the world (call APIs, write files,
   query DBs), not just generate text.
2. **Iteration** — it loops, refining its plan as observations come in.
3. **Autonomy** — it decides what to do next, you don't pre-script every
   step.

Anthropic's definition is sharper: an agent is **"a model that uses tools
in a loop"**. Hold that mental image.

## 2. Levels of agency (from least to most "agentic")

| Level | Pattern | Example in this repo |
|---|---|---|
| 0 | **Single LLM call** | A judge call in `evals.py::judge_pulse` |
| 1 | **Prompt chain** | `weekly_pulse` → `_parse_pulse` (deterministic post-process) |
| 2 | **Routing** | `decision.py::_pick_target` (rule-based; an LLM could choose instead) |
| 3 | **Tool use** | MCP server exposing `append_weekly_pulse` / `create_gmail_draft` |
| 4 | **Loop with state** | LangGraph orchestrating 13 nodes with shared state |
| 5 | **Autonomous multi-step** | (we don't do this) — agent decides which nodes to run, possibly cycling |

This repo lives at **level 4**: a stateful, deterministic graph that calls
LLMs + tools. We don't cross into level 5 because:

- The workflow is well-known (it's a weekly report, not exploration).
- Predictability + auditability matter more than autonomy.
- HITL (human in the loop) gates are stronger than agent self-judgement.

That's a deliberate architectural choice. Don't over-agentify if the
workflow is fixed.

## 3. The core building blocks

### 3.1 Tools (a.k.a. function calling)

The model is given a *menu* of callable functions and decides which to
call with what arguments. Two implementations:

- **OpenAI / Anthropic function calling** — provider-specific API, model
  emits a structured tool call instead of free text.
- **MCP** — protocol-level, provider-agnostic. The host (Claude Desktop /
  Cursor / your agent) discovers tools via `tools/list` and calls them
  via `tools/call`. See [05-mcp.md](05-mcp.md).

This repo uses MCP because:
- Same tools work in Claude Desktop AND in our Flask pipeline.
- The auth/approval boundary is at the protocol layer, not in app code.

### 3.2 Memory

Agents need three flavours:

| Memory | Lifespan | Implementation here |
|---|---|---|
| **Working / scratchpad** | One run | `PulseState` TypedDict in LangGraph |
| **Short-term episodic** | Recent runs | `api/data/runs/*.json` (weekly history) |
| **Long-term semantic** | Forever | (we don't have one — would be a vector DB of all reviews) |

Production agents add a **vector memory** for "things I learned" that
survive across runs. We didn't need it because the work is bounded
(weekly).

### 3.3 Planning

Three reasoning patterns named in the literature:

| Pattern | Idea | When to use |
|---|---|---|
| **ReAct** | Reason → Act → Observe → repeat | Open-ended exploration |
| **Plan-and-Execute** | Generate full plan upfront, then execute | Known multi-step workflows |
| **Reflexion** | After failure, re-plan with the error as context | Self-correcting agents |
| **Tree of Thoughts** | Branch the reasoning, score each branch | Hard problems with multiple paths |

This repo is **Plan-and-Execute**, hard-coded in LangGraph. The plan
(`scrape → embed → cluster → ...`) is fixed at compile time. If the order
needed to be dynamic, we'd switch to ReAct.

### 3.4 The agent loop

The canonical agent loop is six steps:

```python
while not done:
    observation = environment.observe()
    thought = llm("Given observation O, what should I do?")
    action = llm("Call tool X with args Y")
    result = tool.execute(action)
    memory.append((thought, action, result))
    done = llm("Are we done? yes/no")
```

LangGraph's `compile()` is this loop, but constrained by the explicit
edges you defined. That's the win — you keep the loop's flexibility
without giving up the safety of a known graph.

## 4. Multi-agent systems

When one agent isn't enough, you compose:

- **Specialist agents** — researcher, writer, critic, executor.
- **Orchestrator agent** — picks who runs next based on the work.
- **Message-passing** — agents communicate via shared state or a queue.

Famous examples:
- **AutoGPT** (2023) — naive autonomous loop, ran out of context fast.
- **AutoGen** (Microsoft) — multi-agent conversation framework.
- **CrewAI** — role-based teams with hand-offs.
- **LangGraph** — explicit graph; multi-agent is "just" more nodes.

For this repo: we could split the LangGraph into a *scraper agent* and a
*summariser agent*. Wouldn't add value — the work is fixed. Multi-agent
shines when the sub-tasks are heterogeneous and dynamically chosen.

## 5. Human-in-the-loop (HITL)

The most underrated part of building agents. Five places to put a human:

| Stage | Pattern | Where in this repo |
|---|---|---|
| Before the agent runs | "Should I run at all?" | (none — pipeline is scheduled) |
| Mid-plan | "Approve this plan?" | (none — plan is fixed) |
| Before a destructive tool call | "Approve this action?" | `node_gate_doc`, `node_gate_email` |
| After the run | "Was the output OK?" | Eval suite + manual review |
| On failure | "Override and continue?" | (none — we fail closed) |

Gates 3 are the ones that matter. **Never** let an agent auto-send email
or modify shared docs without a human approval, especially in v1.

## 6. Evaluations for agents (different from chat evals)

Chat evals score the *output*. Agent evals score *trajectories*:

- Did the agent pick the right tool?
- Was the tool called with the right arguments?
- Did the agent recover from a tool-call error?
- How many steps did it take? (lower is usually better)

Frameworks: `langsmith`, `wandb traces`, `inspect_ai`. For this repo our
eval suite (`pipeline/evals.py`) scores LLM outputs because the graph
itself is deterministic — there's no agentic decision to evaluate.

## 7. Guardrails for agents

In addition to LLM-output guards ([08-guardrails.md](08-guardrails.md)),
agentic systems need:

- **Tool-call allow-listing**: agent may only call tools in a set.
- **Argument validation**: e.g. agent can't email to a non-corp domain.
- **Step budget**: max N tool calls per task; abort if exceeded.
- **Cost budget**: max $ per run.
- **Rollback**: every tool call should be reversible OR gated.

This repo enforces all five via LangGraph's fixed graph + MCP's approval
gates. A free-running agent would need them at the framework level.

## 8. Where this repo maps onto the agentic stack

```
┌────────────────────────────────────────────────────────────┐
│                   AGENT LAYERS                              │
├────────────────────────────────────────────────────────────┤
│ Orchestration   →  pipeline/langgraph_flow.py              │
│ Planning        →  hardcoded graph + decision.py rules     │
│ Reasoning       →  rag.py (LLM call) + fee_explainer.py    │
│ Tool use        →  mcp_server/server.py (Docs + Gmail)     │
│ Memory          →  api/data/runs/*.json (episodic)         │
│ Guardrails      →  pipeline/guardrails.py + MCP gates      │
│ Evaluation      →  pipeline/evals.py                       │
│ HITL            →  dashboard buttons -> /api/mcp/approve   │
│ Observability   →  Flask logs + Sentry (would go here)     │
└────────────────────────────────────────────────────────────┘
```

If you understand each row + its file, you understand the agentic stack.

## 9. The trap: when NOT to build agents

Don't build an agent if:

- The workflow is **fully known** — use a plain script (faster, cheaper).
- The cost of a wrong action is **high and irreversible** — use a form.
- Latency matters — agents loop, loops take time.
- You can't write a good eval — you'll regress silently.

The strongest test: can you write the workflow as a flowchart? If yes,
build the flowchart (this repo). If no, you might need an agent — but
budget 5-10× the development time vs the deterministic version.

## 10. Recommended reading (in order)

### Foundational papers
1. **ReAct: Synergizing Reasoning and Acting in Language Models** (Yao et al.,
   2023) — defines the reason-act-observe loop.
2. **Toolformer: Language Models Can Teach Themselves to Use Tools** (Schick
   et al., 2023) — pre-MCP function calling.
3. **Reflexion: Language Agents with Verbal Reinforcement Learning**
   (Shinn et al., 2023) — self-critique pattern.
4. **Voyager** (Wang et al., 2023) — lifelong-learning agent that plays
   Minecraft; great case study in skill libraries.

### Anthropic-specific
- [Building effective agents](https://www.anthropic.com/research/building-effective-agents) — the canonical post.
- [Tool use with Claude](https://docs.anthropic.com/claude/docs/tool-use) — function calling docs.
- [Model Context Protocol spec](https://modelcontextprotocol.io) — the protocol underneath this repo's MCP server.

### Practical
- **LangChain Academy** (free course) — hands-on agents.
- **DeepLearning.AI: Functions, Tools and Agents with LangChain** (Harrison
  Chase / Andrew Ng) — short and good.
- **The 12-factor agent** ([github.com/humanloop/12-factor-agent](https://github.com/humanloop/12-factor-agent)) — production checklist.

### Frameworks worth knowing
- **LangGraph** — what this repo uses. Graph-based, stateful.
- **CrewAI** — role-based multi-agent.
- **AutoGen** (Microsoft) — conversation between specialists.
- **Inspect** (Anthropic / AISI) — eval-first agent framework.
- **DSPy** — programmatic prompts; learn the prompts as parameters.

## 11. Where to take this repo next (agent-ifying it)

Three concrete extensions that turn this from a pipeline into an agent:

1. **Self-deciding scrape frequency.** Currently fixed (weekly). Add a
   node that reads recent run history and decides: "high anomaly week →
   run again Wednesday." This is the simplest agentic loop.

2. **Cross-app comparator agent.** Give an agent the tool `scrape_app(id)`
   and the goal "compare Groww to Zerodha and Upstox; surface where Groww
   is doing better/worse". The agent chooses which apps to scrape and
   when to stop. Classic ReAct.

3. **Recommendation-execution agent.** Today the dashboard shows a
   recommendation; a human clicks the gate. Replace with an agent that
   drafts the ticket/email/Slack post and presents 3 variants. Human
   picks one. This is HITL agent design.

Each adds about 200-400 lines. Each could be its own learning project.

---

## Quick map: agentic concepts → files in this repo

| Concept | File |
|---|---|
| State machine | [`pipeline/langgraph_flow.py`](../pipeline/langgraph_flow.py) |
| Tool definition | [`mcp_server/server.py::list_tools`](../mcp_server/server.py) |
| Tool execution | [`mcp_server/server.py::call_tool`](../mcp_server/server.py) |
| RAG retrieval | [`pipeline/rag.py::weekly_pulse`](../pipeline/rag.py) |
| LLM call | [`pipeline/llm.py::complete`](../pipeline/llm.py) |
| HITL gate | [`pipeline/langgraph_flow.py::node_gate_doc`](../pipeline/langgraph_flow.py) |
| Eval harness | [`pipeline/evals.py`](../pipeline/evals.py) |
| Guardrails | [`pipeline/guardrails.py`](../pipeline/guardrails.py) |
| Episodic memory | [`api/data/runs/`](../api/data/runs/) |

Read each in turn with the [HACKING.md](../HACKING.md) jump table on the
side. By the time you've poked at every one, you'll have an internal
working model of how agentic systems are built.
