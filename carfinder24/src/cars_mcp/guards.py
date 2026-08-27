"""Input/output guards for everything the model can reach.

Two directions of defence:

* **Inbound** — `clean_enum` / `clean_text` keep model-supplied values inside a
  known vocabulary before they ever reach SQL. Values are always *bound* as
  DuckDB parameters as well; this layer exists so a nonsense value fails loudly
  and cheaply instead of silently returning nothing.
* **Outbound** — `safe_snippet` scrubs seller-written free text (the ``description``
  column) before it is handed to the LLM. Listing descriptions are user-generated
  content from a third party: the classic indirect prompt-injection vector.
  We strip instruction-shaped lines, contact details and URLs, and cap length.

See docs/SECURITY.md for the threat model.
"""

from __future__ import annotations

import re

# Lines that try to talk to the model rather than describe the car.
# Word boundaries matter: German listings are full of compounds like
# "Navigationssystem:" and "Assistenzsystem:" that would otherwise read as fake
# chat turns. Every alternative below is anchored with \b for that reason.
_INJECTION_PATTERNS = re.compile(
    r"""
    \bignore\s+(all\s+)?(previous|prior|above|these)   # "ignore previous instructions"
    | \bdisregard\s+(the\s+)?(above|previous|prior)
    | ^\s*(system|assistant|developer)\s*[:>]          # a fake chat turn, at line start
    | </?\s*(system|instructions?|prompt)\s*>          # fake tags
    | \bnew\s+instructions?\b
    | \byou\s+are\s+now\b
    | \bact\s+as\s+(an?\s+)?(ai|assistant|agent|advisor)\b
    | \bsend\s+(the\s+|this\s+)?(email|offer|quote)\s+to\b
    | \bforward\s+(the\s+|this\s+)?\w{0,12}\s*to\s+\S+@
    | \breveal\s+(your|the)\s+\w{0,12}\s*(prompt|instructions?|key)
    | \bapi[_\s-]?key\b
    | \bsystem\s+prompt\b
    """,
    re.IGNORECASE | re.VERBOSE | re.MULTILINE,
)
_HTML = re.compile(r"<[^>]{1,80}>")  # listings are stored with markup (<br />, <strong>)
_URL = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(\+?\d[\d\s/()-]{7,}\d)")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def safe_snippet(text: str | None, limit: int = 220) -> str:
    """Scrub a seller-written description before showing it to the model.

    Removes instruction-shaped sentences, URLs, emails and phone numbers, then
    truncates. The result is descriptive prose only — nothing that reads as a
    command and no channel to exfiltrate to.
    """
    if not text:
        return ""
    text = _CONTROL.sub(" ", text)
    text = _HTML.sub(" ", text)  # seller text arrives as HTML fragments
    text = _URL.sub("[link removed]", text)
    text = _EMAIL.sub("[contact removed]", text)
    text = _PHONE.sub("[contact removed]", text)
    # Drop whole sentences that look like instructions rather than description.
    kept = [s for s in re.split(r"(?<=[.!?\n])\s+", text) if not _INJECTION_PATTERNS.search(s)]
    cleaned = " ".join(" ".join(kept).split())
    if len(cleaned) > limit:
        cleaned = cleaned[:limit].rsplit(" ", 1)[0] + "…"
    return cleaned


def looks_injected(text: str | None) -> bool:
    """True when a description contained instruction-shaped content (for logging)."""
    return bool(text) and bool(_INJECTION_PATTERNS.search(text or ""))


def clean_text(value: str | None, limit: int = 60) -> str | None:
    """Trim a free-text filter (make, model, city) to something SQL-shaped.

    The value is still bound as a parameter; this only removes junk that would
    otherwise produce confusing empty result sets.
    """
    if value is None:
        return None
    value = _CONTROL.sub("", value).strip()
    value = re.sub(r"[%_\\]", "", value)  # LIKE wildcards are ours, not the caller's
    return value[:limit] or None


def clean_enum(value: str | None, allowed: dict[str, object], label: str) -> object | None:
    """Resolve a caller-supplied category against a synonym table.

    Raises ValueError naming the accepted values, so the model gets a usable
    correction instead of an empty result set.
    """
    if value is None:
        return None
    key = value.strip().lower()
    if key in allowed:
        return allowed[key]
    raise ValueError(f"unknown {label} '{value}' — use one of: {', '.join(sorted(allowed))}")
