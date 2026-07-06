"""
Pass 1 — rule-based scorer.

This is the original prototype logic, refactored to run on normalized +
de-obfuscated text so evasion tricks no longer defeat it, and to expose its
matches as structured signals the feature engineer and weak-labeler can reuse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..config import (
    SUBSTANCE_TERMS,
    BEHAVIORAL_PHRASES,
    EMOJI_SIGNALS,
    BACKUP_CHANNEL_PHRASES,
)
from ..processing import normalize, deobfuscate
from ..processing.metadata import extract_metadata

BOT_COMMAND_PATTERN = re.compile(r"/(start|menu|price|order|catalog|stock)\b", re.IGNORECASE)
PRICE_PATTERN = re.compile(
    r"(₹|rs\.?|inr)\s?\d{2,5}\s?(/|per)?\s?(g|gram|pc|piece|pill|tab)?",
    re.IGNORECASE,
)
LINK_PATTERN = re.compile(r"(?:https?://|t\.me/|wa\.me/|instagram\.com/|bit\.ly/)\S+", re.IGNORECASE)


@dataclass
class MessageSignals:
    text: str
    score: float = 0.0
    matched_terms: list = field(default_factory=list)
    matched_phrases: list = field(default_factory=list)
    matched_emoji: list = field(default_factory=list)
    has_bot_command: bool = False
    has_price_pattern: bool = False
    has_backup_phrase: bool = False
    external_links: list = field(default_factory=list)
    extracted_metadata: dict = field(default_factory=dict)


def score_message(text: str) -> MessageSignals:
    # Match against both the normalized and de-obfuscated forms so "m3ph3dr0n3"
    # and "m d m a" still fire, without losing the original evidence text.
    norm = normalize(text)
    deob = deobfuscate(text)
    haystacks = {norm, deob}

    score = 0.0
    terms, phrases, emojis = [], [], []

    for term, weight in SUBSTANCE_TERMS.items():
        pattern = r'\b' + re.escape(term) + r'\b'
        if any(re.search(pattern, h) for h in haystacks):
            score += weight
            terms.append(term)

    for phrase, weight in BEHAVIORAL_PHRASES.items():
        pattern = r'\b' + re.escape(phrase) + r'\b'
        if any(re.search(pattern, h) for h in haystacks):
            score += weight
            phrases.append(phrase)

    for emoji, weight in EMOJI_SIGNALS.items():
        if emoji in text:
            score += weight
            emojis.append(emoji)

    has_bot_cmd = bool(BOT_COMMAND_PATTERN.search(text))
    has_price = bool(PRICE_PATTERN.search(norm))
    has_backup = any(p in norm for p in BACKUP_CHANNEL_PHRASES)
    links = LINK_PATTERN.findall(text)

    if has_bot_cmd:
        score += 1.0
    if has_price and terms:      # a price alone is meaningless; needs a substance co-hit
        score += 1.5
    if has_backup:
        score += 1.0

    meta = extract_metadata(text)
    if not meta.is_empty():
        # Boost score if mobile/UPI found alongside drug terms
        if terms and (meta.mobile_numbers or meta.upi_ids):
            score += 1.0
        if meta.crypto_addresses:
            score += 1.5

    return MessageSignals(
        text=text,
        score=round(score, 2),
        matched_terms=terms,
        matched_phrases=phrases,
        matched_emoji=emojis,
        has_bot_command=has_bot_cmd,
        has_price_pattern=has_price,
        has_backup_phrase=has_backup,
        external_links=links,
        extracted_metadata=meta.to_dict(),
    )
