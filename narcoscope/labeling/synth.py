"""
Synthetic data generation.

Seven demo accounts is nowhere near enough to train a classifier. This module
templates a larger, balanced, *labeled* dataset covering the ways drug-sale
messages actually vary — obfuscation, Hinglish, bot storefronts, coded emoji —
plus a wide range of benign messages so the model learns real discrimination
rather than "contains a drug word."

It is a bootstrap, NOT a substitute for hand-labeled real data. Use it to get a
working model on day one, then replace/augment with ``label_tool.py`` output as
you collect real examples. See README "Reaching real accuracy".
"""

from __future__ import annotations

import json
import random

from ..config import SYNTHETIC_FILE, DATA_DIR

_SUBSTANCES = [
    "mdma", "lsd", "mephedrone", "meow meow", "charas", "ganja", "weed",
    "hash", "party pills", "acid tabs", "blotters", "ecstasy", "molly",
]
_SALE = [
    "dm to order", "dm for price", "cod available", "safe delivery",
    "discreet packing", "quality guaranteed", "stock available", "price list",
    "wholesale rate", "pan india delivery",
]
_CITIES = ["mumbai", "pune", "delhi", "bangalore", "goa", "indore", "hyderabad"]
_EMOJI = ["🔌", "🍬", "❄️", "🌿", "💊", "🚀"]
_HINGLISH_POS = [
    "bhai {sub} milega kya, rate batao",
    "{sub} available hai, dm karo price ke liye",
    "best quality {sub}, discreet delivery pura india",
    "{sub} ka stock aa gaya, dm for price",
]

# Benign messages spanning news, fitness, community, commerce, chit-chat — some
# deliberately contain price patterns or emoji so the model can't cheat.
_BENIGN = [
    "morning workout routine, 30 min hiit session today",
    "protein shake recipe for post-workout recovery",
    "breaking: city traffic police announce new odd-even rules",
    "weather update: heavy rainfall expected this weekend",
    "reminder: society meeting tomorrow at 6pm in the clubhouse",
    "water supply interrupted from 10am to 2pm, please store water",
    "new bakery opening downtown, fresh bread ₹50 per loaf 🍞",
    "selling my old iphone, ₹15000, dm if interested",
    "happy diwali to all our loyal customers and their families",
    "join our channel for the daily news digest and analysis",
    "gym membership offer: ₹1200 per month, quality equipment guaranteed",
    "book club meets sunday, we're reading a new novel this month",
    "fresh vegetables home delivery available, safe and hygienic packing",
    "temple festival this weekend, all are welcome 🌿",
    "coding bootcamp registrations open, pan india online classes",
    "handmade candles for sale, discreet gift packing available 🍬",
    "cricket match live tonight, don't miss the action 🚀",
    "please keep the parking area clear for emergency vehicles",
]


def _obfuscate(term: str) -> str:
    """Apply a random evasion transform to a substance term."""
    choice = random.random()
    if choice < 0.3:                          # letter spacing
        return " ".join(term)
    if choice < 0.55:                         # leetspeak
        table = str.maketrans({"o": "0", "e": "3", "i": "1", "a": "4", "s": "5"})
        return term.translate(table)
    if choice < 0.7:                          # dotted
        return ".".join(term)
    return term                               # plain


def _make_positive() -> str:
    sub = random.choice(_SUBSTANCES)
    if random.random() < 0.25:
        return random.choice(_HINGLISH_POS).format(sub=sub)
    parts = []
    term = _obfuscate(sub) if random.random() < 0.5 else sub
    parts.append(random.choice([
        f"new stock {term}", f"{term} back in stock", f"fresh drop {term}",
        f"premium {term} available",
    ]))
    if random.random() < 0.7:
        parts.append(random.choice(_SALE))
    if random.random() < 0.4:
        parts.append(f"cod available in {random.choice(_CITIES)}")
    if random.random() < 0.5:
        parts.append(random.choice(_EMOJI))
    if random.random() < 0.3:
        parts.append(f"₹{random.choice([800, 1500, 2000, 2500])}/g")
    random.shuffle(parts)
    return ", ".join(parts)


def _make_bot_positive() -> str:
    sub = random.choice(_SUBSTANCES)
    cmd = random.choice(["/menu", "/price", "/order", "/catalog"])
    return f"{cmd} {sub} - ₹{random.choice([800, 2000, 2500])}/{random.choice(['g', 'pc', 'pill'])}, pan india delivery"


def generate_dataset(n_per_class: int = 400, seed: int = 42, save: bool = True) -> list:
    """
    Generate a balanced labeled dataset.

    Returns a list of ``{"text": ..., "label": 0|1, "source": "synthetic"}``.
    Writes JSONL to ``data/synthetic_messages.jsonl`` when ``save`` is True.
    """
    random.seed(seed)
    rows = []
    for _ in range(n_per_class):
        maker = _make_bot_positive if random.random() < 0.25 else _make_positive
        rows.append({"text": maker(), "label": 1, "source": "synthetic"})
    for i in range(n_per_class):
        base = _BENIGN[i % len(_BENIGN)]
        # light variation so we don't just memorize 18 strings
        if random.random() < 0.3:
            base = base + " " + random.choice(["thanks", "please share", "stay safe", "cheers"])
        rows.append({"text": base, "label": 0, "source": "synthetic"})
    random.shuffle(rows)

    if save:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SYNTHETIC_FILE, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows
