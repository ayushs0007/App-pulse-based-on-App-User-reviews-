# 01 · The Scraper

> File: [`pipeline/scraper.py`](../pipeline/scraper.py)

## Goal
Pull recent Google Play reviews for the Groww app and hand them to the
analysis pipeline as a clean list of dicts.

## Why a library, not requests?

Google Play's review endpoint isn't a documented REST API — it returns
protobuf-ish JSON-RPC that's a pain to parse. The
[`google-play-scraper`](https://pypi.org/project/google-play-scraper/) package
handles:

- Continuation tokens (the page cursor)
- Sort modes (NEWEST / RATING / MOST_RELEVANT)
- Country & language localisation

We just call `reviews(app_id, …)` and get back Python dicts.

## Anatomy of `fetch_reviews`

```python
result, _continuation = reviews(
    app_id,
    lang="en",
    country="in",
    sort=Sort.NEWEST,
    count=1000,
)
```

The function returns two things — the page of reviews and a continuation
token. We throw the token away because for the weekly pulse 1000 newest
reviews is plenty. If you want a longer history, loop:

```python
batch, cont = reviews(app_id, count=200)
while cont and len(all_reviews) < target:
    batch, cont = reviews(app_id, count=200, continuation_token=cont)
    all_reviews.extend(batch)
```

## The `_normalise` step

Why not just pass the raw scraper output around?

Because the rest of the pipeline (embeddings, clustering, RAG) reads
`r["text"]` and `r["rating"]`. If we let scraper-specific keys
(`reviewId`, `userName`, `score`) bleed into the pipeline, every downstream
file has to know about the scraper's idiosyncrasies. The normaliser is a
**boundary** — one place to change if we ever swap the scraper.

## Caching to disk

We persist results to `api/data/sample_reviews.json`. Reasons:

1. **Offline dev**: you can rebuild the UI without hitting Google.
2. **Reproducibility**: the LangGraph run is idempotent for a given cache.
3. **Politeness**: don't hammer Google when iterating on prompts.

The cache check lives in `node_scrape` inside
[`pipeline/langgraph_flow.py`](../pipeline/langgraph_flow.py) — if the cache
has ≥ 300 reviews, we skip the network call.

## Try it

```bash
python -m pipeline.scraper      # scrapes + writes cache
```
