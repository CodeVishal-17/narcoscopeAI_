"""
Lightweight language handling for Indian-context content.

Trafficking chatter is frequently Hinglish (Hindi written in Latin script) or
mixes Devanagari with English. Full language ID / transliteration needs heavy
models; here we ship dependency-free heuristics plus optional hooks for
``langdetect`` and ``indic-transliteration`` if the user installs them.
"""

from __future__ import annotations

import re

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")

# A tiny, high-precision set of romanized-Hindi function words. Presence of
# several of these alongside Latin script strongly suggests Hinglish.
_HINGLISH_MARKERS = {
    "hai", "kya", "nahi", "milega", "chahiye", "bhai", "kitne", "kitna",
    "rate", "quality", "wala", "kar", "ke", "ka", "ki", "aur", "mein",
}

try:  # optional dependency, used only if present
    from langdetect import detect as _ld_detect  # type: ignore
except Exception:  # pragma: no cover - optional
    _ld_detect = None


def detect_language(text: str) -> str:
    """Best-effort language tag: 'hi', 'hi-Latn' (Hinglish), 'en', or 'und'."""
    if not text or not text.strip():
        return "und"
    if _DEVANAGARI.search(text):
        return "hi"
    if looks_hinglish(text):
        return "hi-Latn"
    if _ld_detect is not None:
        try:
            return _ld_detect(text)
        except Exception:
            pass
    return "en"


def looks_hinglish(text: str) -> bool:
    tokens = re.findall(r"[a-z]+", text.lower())
    if not tokens:
        return False
    hits = sum(1 for t in tokens if t in _HINGLISH_MARKERS)
    return hits >= 2
