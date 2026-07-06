"""
De-obfuscation: undo the common tricks used to evade keyword matching so the
downstream matcher and ML model see the "canonical" form of a message.

Techniques handled:
  * leetspeak / character substitution   m3ph3dr0n3  -> mephedrone-ish
  * letter-spacing                        m d m a     -> mdma
  * dotted / punctuated splitting         m.d.m.a     -> mdma
  * repeated characters                   weeeed      -> weed (capped)

We always work on a normalized copy (see :mod:`.normalize`) and never mutate the
original evidence text.
"""

from __future__ import annotations

import re

from .normalize import normalize

# Map of common leet substitutions -> letter. Conservative on purpose: only the
# substitutions that overwhelmingly mean a letter in this context.
_LEET = {
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t",
    "@": "a", "$": "s", "!": "i",
}

_LEET_RE = re.compile("|".join(re.escape(k) for k in _LEET))
# runs of a single letter separated by spaces/dots: "m d m a" or "m.d.m.a"
_SPACED = re.compile(r"\b(?:[a-z][\s._-]){2,}[a-z]\b")
# 3+ repeats of the same char -> 2
_REPEAT = re.compile(r"(.)\1{2,}")


def _collapse_spaced(text: str) -> str:
    def repl(m: re.Match) -> str:
        return re.sub(r"[\s._-]", "", m.group(0))
    return _SPACED.sub(repl, text)


def _leet(text: str) -> str:
    return _LEET_RE.sub(lambda m: _LEET[m.group(0)], text)


def deobfuscate(text: str) -> str:
    """
    Return a de-obfuscated, normalized copy of ``text``.

    Note this can create false letters (any "0" becomes "o"), so callers should
    match against BOTH the normalized and de-obfuscated forms and treat a hit on
    the de-obfuscated-only form as a (still useful) weaker signal.
    """
    t = normalize(text)
    t = _collapse_spaced(t)
    t = _REPEAT.sub(r"\1\1", t)
    t = _leet(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def obfuscation_score(text: str) -> float:
    """
    How much did de-obfuscation change the text? A high value is itself a
    suspicion signal — benign messages rarely need heavy de-obfuscation.
    Returns a value roughly in [0, 1].
    """
    norm = normalize(text)
    deob = deobfuscate(text)
    if not norm:
        return 0.0
    # character-level edit distance ratio, cheap version: fraction of positions
    # that differ up to the shorter length + length delta.
    shorter = min(len(norm), len(deob))
    diff = sum(1 for i in range(shorter) if norm[i] != deob[i])
    diff += abs(len(norm) - len(deob))
    return round(min(diff / max(len(norm), 1), 1.0), 3)
