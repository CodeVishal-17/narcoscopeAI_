"""
Unicode / whitespace / casing normalization.

Sellers deliberately break up text to dodge naive keyword filters. The first
defense is aggressive, *lossless-for-detection* normalization: we keep the
original text for evidence, but detection runs on a normalized copy.
"""

from __future__ import annotations

import re
import unicodedata

# Zero-width and invisible characters used to split keywords (m<zwsp>dma).
_INVISIBLE = re.compile(r"[​‌‍⁠﻿­]")
# Repeated whitespace.
_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Return a normalized, lower-cased copy suitable for matching."""
    if not text:
        return ""
    # NFKC folds full-width / stylized unicode letters back to ASCII-ish forms
    # (e.g. mathematical bold "𝐌𝐃𝐌𝐀" -> "MDMA").
    text = unicodedata.normalize("NFKC", text)
    text = _INVISIBLE.sub("", text)
    text = text.lower()
    text = _WS.sub(" ", text).strip()
    return text
