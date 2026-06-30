# 03 · RAG (Retrieval-Augmented Generation)

> Files: [`pipeline/rag.py`](../pipeline/rag.py),
> [`pipeline/fee_explainer.py`](../pipeline/fee_explainer.py),
> [`pipeline/llm.py`](../pipeline/llm.py)

## What RAG actually is

LLMs are good at generating fluent text, terrible at remembering specific
facts. RAG fixes that by **retrieving** the relevant facts first, then
**generating** the text grounded on what was retrieved.

```
question --> retriever --> [docs] --> LLM(question + docs) --> answer
```

Without RAG, an LLM asked "what are users complaining about this week?" will
make up plausible-sounding quotes. With RAG, you hand it the actual quotes
and tell it to summarise — it can no longer invent them.

## Retrieval in this project

Most RAG tutorials show you a vector database (Pinecone, Chroma, FAISS).
We don't need one — reviews are tiny and we've already clustered them. The
retrieval step is:

> For each of the 5 theme clusters, pick the top 6 reviews closest to the
> centroid. Pass them to the LLM as numbered context.

```python
theme_block = "\n".join(
    f"- {c['label']} (n={c['size']}): \"{c['sample_quotes'][0][:140]}\""
    for c in clusters[:5]
)
prompt = f"""Top themes:\n{theme_block}\n\nWrite a Weekly Pulse..."""
```

The result is a 250-word note that **cites real user verbatims** because
the verbatims are literally in the prompt.

## Generation: the Groq wrapper

The LLM client lives in `llm.py`:

```python
def complete(prompt, system="", max_tokens=600):
    if not GROQ_API_KEY:
        return _fallback(prompt)        # deterministic stand-in
    client = Groq(api_key=GROQ_API_KEY)
    resp = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[{"role":"system","content":system},
                  {"role":"user","content":prompt}],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()
```

Why **Groq**? Their LPU runs Llama-3.1-70B at ~300 tokens/sec — fast enough
to feel synchronous on a dashboard.

Why **temperature 0.3**? Weekly Pulse needs to be reliable, not creative.
Low temperature = fewer surprise re-phrasings between runs.

## The fee explainer is RAG with a filter

`fee_explainer.py` is a great example of how to scope RAG:

1. **Filter**: keep only reviews containing fee keywords ("brokerage",
   "exit load", "deducted", etc.). This is your retriever.
2. **Generate**: feed those reviews + an allow-list of official Groww
   help-centre URLs into a prompt that says *"cite only the sources I just
   gave you"*.

This is sometimes called **grounded generation** — the LLM is constrained
to information you actually trust. Hallucinated URLs become impossible
because the LLM only sees URLs you pre-vetted.

## Parsing the LLM output

`_parse_pulse` splits the response into `summary`, `recommendation`, and
`actions` using literal markers (`RECOMMENDATION:`, `ACTIONS:`). The
markers are part of the prompt:

```
Then on a new line starting with "RECOMMENDATION:" give...
Then on a new line starting with "ACTIONS:" list three...
```

This is a deliberate alternative to structured-output features
(JSON mode, tool-use). For a 3-section output, markers are simpler and the
parser degrades gracefully — if the LLM forgets a section we use defaults
derived from cluster stats.
