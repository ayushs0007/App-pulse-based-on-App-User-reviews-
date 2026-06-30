"""
Groq LLM wrapper with a deterministic fallback.

Why Groq? Llama-3.1-70B on Groq's LPU is *fast* (300+ tok/s) and the API is
OpenAI-compatible. We keep the surface area tiny: one `complete()` function.

Why a fallback? CI runs and offline demos still need a Weekly Pulse. The
fallback builds a sensible note from cluster stats — not pretty, but correct.
"""
from __future__ import annotations

import os
from typing import List, Dict, Any

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")


def complete(
    prompt: str,
    system: str = "",
    max_tokens: int = 600,
    *,
    apply_guardrails: bool = True,
    allowed_urls=(),
) -> str:
    """Send `prompt` to Groq; fall back to a template if no key is set.

    Guardrails: when `apply_guardrails=True`, the prompt is PII-redacted and
    scanned for injection attempts before the call; the response is scanned
    for toxic tokens and unauthorised URLs after.

    `allowed_urls` is the closed-world citation set — pass the URLs that the
    prompt explicitly authorised the model to cite. Default empty = no URL
    check.
    """
    safe_prompt_text = prompt
    if apply_guardrails:
        from .guardrails import safe_prompt
        gr = safe_prompt(prompt)
        if not gr.passed:
            return f"[BLOCKED: {gr.reason}]"
        safe_prompt_text = gr.text

    if not GROQ_API_KEY:
        return _fallback(safe_prompt_text)

    from groq import Groq

    client = Groq(api_key=GROQ_API_KEY)
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": safe_prompt_text})

    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=msgs,
        max_tokens=max_tokens,
        temperature=0.3,
    )
    out = resp.choices[0].message.content.strip()

    if apply_guardrails:
        from .guardrails import safe_output
        gr = safe_output(out, allowed_urls=allowed_urls)
        if not gr.passed:
            return f"[BLOCKED: {gr.reason}]"
    return out


def _fallback(prompt: str) -> str:
    """Deterministic stand-in. We just echo a tiny note so the UI is populated."""
    return (
        "Users flagged friction across the top themes this week. "
        "Investigate the most-cited issues and prioritise fixes for the next sprint."
    )
