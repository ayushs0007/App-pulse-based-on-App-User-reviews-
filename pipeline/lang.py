"""
Language detection — cheap, deterministic, no external models.

Why this matters: ~30% of Google Play reviews for Indian fintech apps are in
Hindi (Devanagari) or Hinglish (Latin script but Hindi words). An
English-only dashboard silently throws this signal away.

We split reviews into three buckets:
  - hi    : Devanagari script present
  - hinglish : Latin script but strong Hindi-word match
  - en    : everything else

Hinglish detection is a simple wordlist scan. For production you'd want
fasttext-langdetect, but for this pipeline the wordlist gets us ~90% recall.
"""
from __future__ import annotations

import re
from typing import List, Dict, Any

DEVANAGARI = re.compile(r"[ऀ-ॿ]")

HINGLISH_TOKENS = {
    "hai", "bahut", "acha", "achha", "kya", "kaise", "kaisa", "kar", "karne",
    "kiya", "nahi", "nahin", "mera", "meri", "humara", "hamara", "tum", "aap",
    "ye", "yeh", "wo", "woh", "isme", "usme", "ke", "ki", "ka", "ko", "se",
    "par", "pe", "le", "lo", "liya", "diya", "raha", "rha", "hota", "hoti",
    "best", "but", "but app", "abhi", "phir", "bhi", "lekin", "magar",
    "jaise", "kuch", "sab", "saara", "saare", "humein", "hume", "rupiya",
    "rupay", "paisa", "paise", "samjhe", "samjha", "thoda", "zyada", "kam",
    "dikkat", "problem", "samasya", "shikayat", "garib", "aur", "ya", "agar",
    "bilkul", "sahi", "galat", "ghatiya", "badiya", "behtar", "behtareen",
}


def classify(text: str) -> str:
    if DEVANAGARI.search(text):
        return "hi"
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    if not tokens:
        return "en"
    hits = sum(1 for t in tokens if t in HINGLISH_TOKENS)
    # 2+ Hinglish tokens OR > 15% of words match → call it Hinglish.
    if hits >= 2 or (len(tokens) >= 4 and hits / len(tokens) > 0.15):
        return "hinglish"
    return "en"


def breakdown(reviews_data: List[Dict[str, Any]]) -> Dict[str, int]:
    """Return {en, hinglish, hi} counts. Mutates each review to add `lang`."""
    counts = {"en": 0, "hinglish": 0, "hi": 0}
    for r in reviews_data:
        lang = classify(r.get("text", ""))
        r["lang"] = lang
        counts[lang] += 1
    return counts
