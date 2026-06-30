"""
Guardrails — input and output filters for the LLM layer.

A guardrail is a deterministic check that wraps the LLM call. The pattern:

    text → [pre-call guards] → LLM → [post-call guards] → text

Pre-call guards block things going IN that could harm the model or leak info.
Post-call guards block things coming OUT that could harm the user or violate
policy. We implement four guardrails here, each tiny but illustrative:

  1. redact_pii            — phone, email, PAN, Aadhaar masked from prompts
  2. detect_prompt_injection — "ignore previous instructions"-style attacks
  3. content_filter        — toxic / profane output rejected
  4. citation_check        — refuses output that cites a URL we never gave

Each guardrail returns a `GuardResult(passed, redacted_text, reason)`. Calling
code decides whether to retry, escalate, or fail open.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass
class GuardResult:
    passed: bool
    text: str
    reason: Optional[str] = None


# --- 1. PII redaction --------------------------------------------------------
PHONE = re.compile(r"(?:\+?91[-\s]?)?[6-9]\d{9}")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
AADHAAR = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
CARD = re.compile(r"\b(?:\d[ -]*?){13,16}\b")


def redact_pii(text: str) -> GuardResult:
    """Mask Indian-context PII before the text touches the LLM."""
    redacted = text
    redacted = PHONE.sub("[PHONE]", redacted)
    redacted = EMAIL.sub("[EMAIL]", redacted)
    redacted = PAN.sub("[PAN]", redacted)
    redacted = AADHAAR.sub("[AADHAAR]", redacted)
    redacted = CARD.sub("[CARD]", redacted)
    return GuardResult(
        passed=True,
        text=redacted,
        reason="pii_redacted" if redacted != text else None,
    )


# --- 2. Prompt injection detection ------------------------------------------
INJECTION_PHRASES = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard the above",
    "system prompt",
    "you are now",
    "act as",
    "jailbreak",
    "DAN mode",
    "do anything now",
)


def detect_prompt_injection(text: str) -> GuardResult:
    """Block obvious prompt-injection attempts in user-supplied review text.

    This is a substring scanner — it catches the lazy attacks, not the
    sophisticated ones. For production, layer in:
      - Model-graded injection detector (e.g. Lakera Guard, Prompt Armor)
      - Content classifier specifically trained on jailbreak prompts
    """
    lower = text.lower()
    for phrase in INJECTION_PHRASES:
        if phrase in lower:
            return GuardResult(
                passed=False,
                text=text,
                reason=f"injection_pattern: {phrase}",
            )
    return GuardResult(passed=True, text=text)


# --- 3. Toxic / profane output filter ---------------------------------------
# Tiny English list; for production wire in Perspective API or a toxicity model.
TOXIC_TOKENS = {
    "fuck", "shit", "bastard", "asshole", "stupid", "idiot",
    "racist", "sexist", "kill yourself",
}


def content_filter(text: str) -> GuardResult:
    """Refuse output that contains toxic language."""
    lower = text.lower()
    hits = [tok for tok in TOXIC_TOKENS if tok in lower]
    if hits:
        return GuardResult(passed=False, text=text, reason=f"toxic_tokens: {hits}")
    return GuardResult(passed=True, text=text)


# --- 4. Citation check (RAG-specific) ---------------------------------------
URL_RE = re.compile(r"https?://[^\s\)\]]+", re.IGNORECASE)


def citation_check(text: str, allowed_urls: Iterable[str]) -> GuardResult:
    """Reject output that links to URLs that weren't in the retrieved context.

    Hallucinated URLs are a top-3 LLM failure mode in RAG systems. This guard
    enforces a closed-world citation policy: the model may only cite what we
    explicitly handed it.
    """
    allowed_set = set(allowed_urls)
    found = URL_RE.findall(text)
    bad = [u for u in found if u not in allowed_set]
    if bad:
        return GuardResult(
            passed=False,
            text=text,
            reason=f"unauthorised_urls: {bad}",
        )
    return GuardResult(passed=True, text=text)


# --- composite ---------------------------------------------------------------

def safe_prompt(prompt: str) -> GuardResult:
    """Compose the input guards. Call this BEFORE sending to the LLM."""
    pii = redact_pii(prompt)
    inj = detect_prompt_injection(pii.text)
    if not inj.passed:
        return inj
    return GuardResult(passed=True, text=pii.text, reason=pii.reason)


def safe_output(text: str, allowed_urls: Iterable[str] = ()) -> GuardResult:
    """Compose the output guards. Call this AFTER receiving from the LLM."""
    flt = content_filter(text)
    if not flt.passed:
        return flt
    if allowed_urls:
        cite = citation_check(text, allowed_urls)
        if not cite.passed:
            return cite
    return GuardResult(passed=True, text=text)
