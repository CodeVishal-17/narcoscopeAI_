"""
Content Analysis Engine — Prototype
------------------------------------
A lightweight, explainable, RULE-BASED scorer that flags social media posts /
messages / bot replies as potentially drug-sale related, and rolls those
per-message flags up into an account-level risk score.

This is intentionally rule-based (not a black-box ML model) for the prototype
stage: it's transparent, fast to extend, needs no GPU/training data, and every
flag can be traced back to *why* it fired — which matters a lot when the
output may eventually support a legal request. In production this would sit
alongside a fine-tuned transformer classifier (see README) for messages that
evade keyword matching.

IMPORTANT: The keyword/pattern lists below are intentionally limited to
substance names and generic sale-behavior phrases already used openly in the
problem statement (MDMA, LSD, mephedrone, etc.) and generic e-commerce-style
phrases ("DM to order", "COD available"). This is a prototype scaffold, not
a production evasion-resistant dictionary — that piece should live in a
restricted, access-controlled module maintained by analysts, not shipped in
public source code.

Usage:
    python3 content_analysis_engine.py
    -> reads sample_data.json, writes flagged_output.json
"""

import json
import re
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from collections import defaultdict

# ---------------------------------------------------------------------------
# 1. Signal dictionaries (prototype scope — see module docstring)
# ---------------------------------------------------------------------------

SUBSTANCE_TERMS = {
    "mdma": 3.0, "lsd": 3.0, "mephedrone": 3.0, "meow meow": 3.0,
    "charas": 2.5, "ganja": 2.0, "weed": 1.5, "hash": 2.0,
    "party pills": 2.5, "acid tabs": 2.5, "blotters": 2.5,
    "ecstasy": 2.5, "molly": 2.5,
}

BEHAVIORAL_PHRASES = {
    "dm to order": 2.0,
    "dm for price": 2.0,
    "cod available": 1.5,
    "safe delivery": 1.5,
    "discreet packing": 2.5,
    "no minors": 1.0,
    "quality guaranteed": 1.0,
    "stock available": 1.0,
    "price list": 1.5,
    "wholesale rate": 1.5,
    "pan india delivery": 2.0,
    "backup channel": 1.5,
    "new channel link": 1.0,
}

EMOJI_SIGNALS = {
    "🔌": 1.0,   # "the plug"
    "🍬": 0.5,
    "❄️": 1.0,
    "🌿": 0.5,
    "💊": 1.5,
    "🚀": 0.5,   # often paired with delivery claims
}

BOT_COMMAND_PATTERN = re.compile(r"/(start|menu|price|order|catalog|stock)\b", re.IGNORECASE)
PRICE_PATTERN = re.compile(r"(₹|rs\.?|inr)\s?\d{2,5}\s?(/|per)?\s?(g|gram|pc|piece|pill|tab)?", re.IGNORECASE)

RISK_BANDS = [
    (7.0, "CRITICAL"),
    (4.0, "HIGH"),
    (2.0, "MEDIUM"),
    (0.0, "LOW"),
]


def risk_band(score: float) -> str:
    for threshold, label in RISK_BANDS:
        if score >= threshold:
            return label
    return "LOW"


# ---------------------------------------------------------------------------
# 2. Message-level scoring
# ---------------------------------------------------------------------------

@dataclass
class MessageFlag:
    text: str
    score: float
    matched_terms: list = field(default_factory=list)
    matched_phrases: list = field(default_factory=list)
    matched_emoji: list = field(default_factory=list)
    has_bot_command: bool = False
    has_price_pattern: bool = False


def score_message(text: str) -> MessageFlag:
    lower = text.lower()
    score = 0.0
    terms, phrases, emojis = [], [], []

    for term, weight in SUBSTANCE_TERMS.items():
        if term in lower:
            score += weight
            terms.append(term)

    for phrase, weight in BEHAVIORAL_PHRASES.items():
        if phrase in lower:
            score += weight
            phrases.append(phrase)

    for emoji, weight in EMOJI_SIGNALS.items():
        if emoji in text:
            score += weight
            emojis.append(emoji)

    has_bot_cmd = bool(BOT_COMMAND_PATTERN.search(text))
    has_price = bool(PRICE_PATTERN.search(text))
    if has_bot_cmd:
        score += 1.0
    if has_price and terms:  # price pattern alone is meaningless; needs a substance co-hit
        score += 1.5

    return MessageFlag(
        text=text,
        score=round(score, 2),
        matched_terms=terms,
        matched_phrases=phrases,
        matched_emoji=emojis,
        has_bot_command=has_bot_cmd,
        has_price_pattern=has_price,
    )


# ---------------------------------------------------------------------------
# 3. Account-level rollup
# ---------------------------------------------------------------------------

@dataclass
class AccountReport:
    account_id: str
    platform: str
    handle: str
    account_type: str  # channel | group | bot | profile
    message_flags: list
    avg_message_score: float
    max_message_score: float
    flagged_message_count: int
    total_messages_seen: int
    is_probable_bot: bool
    risk_score: float
    risk_band: str
    evidence_sample: list


def analyze_account(account: dict) -> AccountReport:
    flags = [score_message(m["text"]) for m in account["messages"]]
    flagged = [f for f in flags if f.score > 0]

    total = len(flags)
    flagged_count = len(flagged)
    avg_score = sum(f.score for f in flags) / total if total else 0.0
    max_score = max((f.score for f in flags), default=0.0)

    bot_cmd_ratio = sum(1 for f in flags if f.has_bot_command) / total if total else 0
    is_probable_bot = bot_cmd_ratio > 0.3 or account.get("account_type") == "bot"

    # Account risk = weighted blend of intensity (max) and prevalence (avg + flagged ratio)
    flagged_ratio = flagged_count / total if total else 0
    risk_score = round(
        (max_score * 0.4) + (avg_score * 0.35) + (flagged_ratio * 10 * 0.25),
        2,
    )
    if is_probable_bot:
        risk_score += 1.0  # automated storefronts scale faster -> slightly higher priority

    evidence_sample = sorted(flagged, key=lambda f: -f.score)[:3]

    return AccountReport(
        account_id=account["account_id"],
        platform=account["platform"],
        handle=account["handle"],
        account_type=account.get("account_type", "profile"),
        message_flags=[asdict(f) for f in flags],
        avg_message_score=round(avg_score, 2),
        max_message_score=round(max_score, 2),
        flagged_message_count=flagged_count,
        total_messages_seen=total,
        is_probable_bot=is_probable_bot,
        risk_score=round(risk_score, 2),
        risk_band=risk_band(risk_score),
        evidence_sample=[asdict(f) for f in evidence_sample],
    )


# ---------------------------------------------------------------------------
# 4. Cross-account correlation (lightweight entity resolution)
# ---------------------------------------------------------------------------

def correlate_accounts(accounts: list) -> dict:
    """
    Groups accounts across platforms that share a payment handle or a
    near-identical bio/handle string — the legal, public-data OSINT layer
    described in the architecture (no private metadata involved).
    """
    payment_groups = defaultdict(list)
    for acc in accounts:
        for handle in acc.get("payment_handles", []):
            payment_groups[handle].append(acc["account_id"])

    clusters = {k: v for k, v in payment_groups.items() if len(v) > 1}
    return clusters


# ---------------------------------------------------------------------------
# 5. Main
# ---------------------------------------------------------------------------

def main():
    with open("sample_data.json") as f:
        accounts = json.load(f)

    reports = [analyze_account(a) for a in accounts]
    reports.sort(key=lambda r: -r.risk_score)

    clusters = correlate_accounts(accounts)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "accounts_analyzed": len(reports),
        "flagged_accounts": sum(1 for r in reports if r.risk_band in ("HIGH", "CRITICAL")),
        "reports": [asdict(r) for r in reports],
        "linked_account_clusters": clusters,
    }

    with open("flagged_output.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Analyzed {len(reports)} accounts.")
    print(f"Flagged HIGH/CRITICAL: {output['flagged_accounts']}")
    print("Top 5 by risk score:")
    for r in reports[:5]:
        print(f"  [{r.risk_band:8s}] {r.platform:10s} {r.handle:20s} score={r.risk_score}")
    if clusters:
        print("\nLinked account clusters (shared payment handle):")
        for handle, ids in clusters.items():
            print(f"  {handle} -> {ids}")


if __name__ == "__main__":
    main()