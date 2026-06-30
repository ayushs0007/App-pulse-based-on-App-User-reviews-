"""
Turn review text into dense vectors using sentence-transformers.

We use `all-MiniLM-L6-v2`:
- 384 dimensions (cheap to cluster)
- 22M parameters (runs on CPU in seconds)
- Trained for semantic similarity on 1B sentence pairs

The model gets downloaded once on first call and cached under ~/.cache/torch.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    """Lazy-load + cache the model. lru_cache makes this idempotent."""
    return SentenceTransformer(MODEL_NAME)


def embed(texts: List[str], batch_size: int = 64) -> np.ndarray:
    """Encode a list of strings to an (n, 384) numpy array.

    `normalize_embeddings=True` makes downstream cosine similarity equivalent
    to a simple dot product, which speeds up clustering and reduces drift.
    """
    if not texts:
        return np.zeros((0, 384), dtype="float32")
    model = _model()
    return model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
