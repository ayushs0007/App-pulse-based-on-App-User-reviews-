# 04 · LangGraph Orchestration

> File: [`pipeline/langgraph_flow.py`](../pipeline/langgraph_flow.py)

## What is LangGraph?

LangGraph is a library from LangChain for building **stateful, multi-step
agent workflows**. You define your pipeline as a graph of nodes that mutate
a shared state object.

The three primitives:

| Primitive | What it is |
|---|---|
| **State** | A `TypedDict` that nodes read from and write into. |
| **Node** | A pure function `state -> state`. |
| **Edge** | A connection saying "after node A, run node B." Can be conditional. |

Compile the graph to get a runnable object: `app.invoke(initial_state)`.

## Why not just call functions in sequence?

Three things you get for free with LangGraph:

1. **Visible dependency graph.** You can render the graph as a Mermaid
   diagram and hand it to a stakeholder.
2. **Checkpointing.** Plug in a checkpointer and you can resume a failed
   run mid-pipeline.
3. **Conditional branches & cycles.** Easy to add things like "loop until
   the clusters are coherent" or "skip step X if state.flag is set".

For this project the killer feature is #3 — our **two human-approval
gates** are just nodes that early-return when an approval flag is missing.

## The graph

```
scrape -> embed -> cluster -> sentiment -> rag -> fee -> persist
                                                       \\-> gate_doc -> gate_email -> END
```

Code:

```python
g = StateGraph(PulseState)
g.add_node("scrape", node_scrape)
…
g.set_entry_point("scrape")
g.add_edge("scrape", "embed")
g.add_edge("embed", "cluster")
…
g.add_edge("gate_email", END)
```

## The state schema

```python
class PulseState(TypedDict, total=False):
    week_label: str
    reviews: List[Dict[str, Any]]
    embeddings: Any
    clusters: List[Dict[str, Any]]
    sentiment: Dict[str, float]
    pulse: Dict[str, Any]
    fee: Dict[str, Any]
    approve_doc: bool
    approve_email: bool
    mcp_results: Dict[str, Any]
```

`total=False` makes every field optional — useful while the pipeline is
still mutating values.

## How the approval gates work

```python
def node_gate_doc(state):
    if not state.get("approve_doc"):
        return state                # silent no-op
    from mcp_server.client import append_to_doc
    res = append_to_doc(state["pulse"], state["week_label"])
    state.setdefault("mcp_results", {})["doc"] = res
    return state
```

The pipeline always *passes through* the gate nodes, but they only act when
the corresponding flag is set. The Flask endpoint `/api/mcp/approve` is
what flips the flag — and the dashboard's modal is what calls that
endpoint. Real human-in-the-loop, no auto-fire.

## When to add a conditional edge instead

If you want the graph itself to branch (e.g. send to a "re-cluster" node
when cluster cohesion is low), use `add_conditional_edges`:

```python
g.add_conditional_edges(
    "cluster",
    lambda state: "recluster" if state["cohesion"] < 0.4 else "rag",
)
```

For this project we kept things linear because every step always runs.
