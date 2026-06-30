"""
Google Play scraper for Groww app reviews.

Why a dedicated module?
- Keeps network I/O isolated from analysis logic.
- Provides a stable shape (`Review` dict) the rest of the pipeline can rely on.
- Lets us cache to disk so we don't re-hit Google Play on every run.

The `google-play-scraper` package talks to Google Play's public review endpoint.
No auth, but be polite: keep `count` reasonable and add a retry guard.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

from google_play_scraper import reviews, Sort

GROWW_APP_ID = "com.nextbillion.groww"
CACHE_PATH = Path(__file__).parent.parent / "api" / "data" / "sample_reviews.json"


def fetch_reviews(
    app_id: str = GROWW_APP_ID,
    count: int = 1000,
    lang: str = "en",
    country: str = "in",
) -> List[Dict[str, Any]]:
    """Pull `count` most-recent reviews for the given Play Store app.

    Returns a list of dicts with: id, user, rating, text, ts (iso), thumbs.
    """
    result, _continuation = reviews(
        app_id,
        lang=lang,
        country=country,
        sort=Sort.NEWEST,
        count=count,
    )
    return [_normalise(r) for r in result]


def _normalise(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten the scraper's response into the shape the pipeline expects."""
    ts = raw.get("at") or datetime.now(timezone.utc)
    return {
        "id": raw.get("reviewId"),
        "user": raw.get("userName", "Anonymous"),
        "rating": int(raw.get("score", 0)),
        "text": (raw.get("content") or "").strip(),
        "ts": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
        "thumbs": int(raw.get("thumbsUpCount", 0)),
    }


def save_cache(reviews_data: List[Dict[str, Any]], path: Path = CACHE_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "app_id": GROWW_APP_ID,
        "count": len(reviews_data),
        "reviews": reviews_data,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_cache(path: Path = CACHE_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("reviews", [])


if __name__ == "__main__":
    print(f"Scraping {GROWW_APP_ID} ...")
    started = time.time()
    data = fetch_reviews(count=1000)
    print(f"Got {len(data)} reviews in {time.time() - started:.1f}s")
    out = save_cache(data)
    print(f"Cached -> {out}")
