# 02 · Embeddings + Clustering

> Files: [`pipeline/embeddings.py`](../pipeline/embeddings.py),
> [`pipeline/clustering.py`](../pipeline/clustering.py)

This is where raw text becomes something we can do math on.

## Step 1: Embed each review

A **sentence embedding** is a fixed-length vector that captures the meaning
of a sentence. Two reviews with the same gripe ("app crashes on launch" and
"keeps freezing when I open it") end up close together in vector space even
though they share no keywords.

We use `sentence-transformers/all-MiniLM-L6-v2`:

| Property | Value |
|---|---|
| Dimensions | 384 |
| Size | ~80 MB |
| Speed (CPU) | ~5000 sentences/sec |
| Trained on | 1B sentence pairs (MS MARCO, Reddit, etc.) |

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
vectors = model.encode(texts, normalize_embeddings=True)
```

`normalize_embeddings=True` puts every vector on the unit sphere. Cosine
similarity then collapses to a dot product — faster to compute and
mathematically equivalent for K-Means.

## Step 2: K-Means cluster

[K-Means](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html)
is the simplest clustering algorithm:

1. Pick K random centroids in vector space.
2. Assign each point to its nearest centroid.
3. Move each centroid to the mean of its members.
4. Repeat until centroids stop moving.

We fix K=5 because the dashboard always wants 5 theme cards. If you let K
vary (using e.g. silhouette score), your UI has to handle 3-card and 12-card
states — needless complexity for the demo.

## Step 3: Label the clusters

K-Means gives you cluster IDs (0, 1, 2…) — not names. We label clusters by
keyword frequency over the *representative quotes*:

```python
KEYWORD_MAP = {
  "brokerage": ["brokerage", "charge", "expensive", …],
  "stability": ["crash", "hang", "freeze", "lag", …],
  …
}

for key, words in KEYWORD_MAP.items():
    scores[key] = sum(blob.count(w) for w in words)
best_key = scores.most_common(1)[0][0]
```

The winner becomes the cluster's label. This is intentionally a *cheap,
deterministic* fallback so the dashboard never shows "Cluster #3". The LLM
can also rename clusters during summarisation, but we don't depend on it.

## Step 4: Pick a representative quote

For each cluster we want the *one* review that best represents the group.
The math: find the review whose embedding is closest to the cluster
centroid (the **medoid by centroid distance**).

```python
centroid = km.cluster_centers_[cid]
dists = np.linalg.norm(embeddings[member_idx] - centroid, axis=1)
top_quote = texts[member_idx[np.argmin(dists)]]
```

This quote is what appears on the dashboard's "Representative Feedback"
panel and in the Weekly Pulse summary prompt.

## Why not topic models (LDA, BERTopic)?

- LDA needs longer documents. Reviews are too short.
- BERTopic with HDBSCAN gives you a "noise" cluster, which complicates UX.
- K-Means is boring, fast, and the result is good enough for a weekly
  product summary. Boring is a feature here.
