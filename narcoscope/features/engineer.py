"""
Feature engineering.

Two levels:

* **message features** — lexical/behavioural/structural signals for one message.
  These become the numeric side-channel that rides alongside TF-IDF text in the
  ML model, and are exposed for inspection/evidence.

* **account features** — aggregates of a whole account plus network signals
  (shared payment handles). Used for account-level risk scoring.

Everything here is deterministic and explainable — each number traces back to a
concrete property of the text, which matters when output may support a legal
request.
"""

from __future__ import annotations

import math
import re
from datetime import datetime

from ..model.rules import score_message, MessageSignals
from ..processing import obfuscation_score, detect_language

# Order matters — the ML model relies on a stable feature vector layout.
MESSAGE_NUMERIC_FEATURES = [
    "rule_score",
    "char_len",
    "token_count",
    "num_substances",
    "num_phrases",
    "num_emoji_signals",
    "has_bot_command",
    "has_price_pattern",
    "has_backup_phrase",
    "num_links",
    "digit_ratio",
    "upper_ratio",
    "obfuscation_score",
    "is_hinglish",
]

_TOKEN = re.compile(r"\S+")


def message_features(text: str, signals: MessageSignals | None = None) -> dict:
    """Return a flat dict of numeric features + carried-through signal detail."""
    sig = signals or score_message(text)
    n = max(len(text), 1)
    digits = sum(c.isdigit() for c in text)
    uppers = sum(c.isupper() for c in text)
    lang = detect_language(text)

    feats = {
        "rule_score": float(sig.score),
        "char_len": float(len(text)),
        "token_count": float(len(_TOKEN.findall(text))),
        "num_substances": float(len(sig.matched_terms)),
        "num_phrases": float(len(sig.matched_phrases)),
        "num_emoji_signals": float(len(sig.matched_emoji)),
        "has_bot_command": float(sig.has_bot_command),
        "has_price_pattern": float(sig.has_price_pattern),
        "has_backup_phrase": float(sig.has_backup_phrase),
        "num_links": float(len(sig.external_links)),
        "digit_ratio": round(digits / n, 3),
        "upper_ratio": round(uppers / n, 3),
        "obfuscation_score": obfuscation_score(text),
        "is_hinglish": float(lang == "hi-Latn"),
    }
    return feats


def numeric_vector(feats: dict) -> list:
    """Feature dict -> ordered numeric list for the ML model."""
    return [float(feats.get(name, 0.0)) for name in MESSAGE_NUMERIC_FEATURES]


def _parse_ts(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def account_features(account, message_signals: list, payment_index: dict | None = None) -> dict:
    """
    Aggregate features for one account.

    ``message_signals`` is the list of :class:`MessageSignals` for the account's
    messages. ``payment_index`` maps payment_handle -> set(account_id) across the
    whole corpus, used for the network degree feature.
    """
    scores = [s.score for s in message_signals]
    total = len(scores) or 1
    flagged = [s for s in scores if s > 0]

    max_score = max(scores, default=0.0)
    mean_score = sum(scores) / total
    var = sum((s - mean_score) ** 2 for s in scores) / total
    std_score = math.sqrt(var)

    bot_cmd_ratio = sum(1 for s in message_signals if s.has_bot_command) / total
    link_count = sum(len(s.external_links) for s in message_signals)
    backup_count = sum(1 for s in message_signals if s.has_backup_phrase)
    unique_substances = len({t for s in message_signals for t in s.matched_terms})

    # Network signal: how many *other* accounts share a payment handle.
    shared_degree = 0
    if payment_index:
        peers = set()
        for h in getattr(account, "payment_handles", []):
            peers |= payment_index.get(h, set())
        peers.discard(account.account_id)
        shared_degree = len(peers)

    # Posting cadence (burstiness) if timestamps exist.
    times = sorted(t for t in (_parse_ts(m.timestamp) for m in account.messages) if t)
    burst = 0.0
    if len(times) >= 2:
        gaps = [(times[i + 1] - times[i]).total_seconds() for i in range(len(times) - 1)]
        median_gap = sorted(gaps)[len(gaps) // 2]
        burst = 1.0 if median_gap < 60 else 0.0   # many posts <1min apart => automated

    return {
        "max_message_score": round(max_score, 2),
        "mean_message_score": round(mean_score, 2),
        "std_message_score": round(std_score, 2),
        "flagged_ratio": round(len(flagged) / total, 3),
        "bot_command_ratio": round(bot_cmd_ratio, 3),
        "link_count": link_count,
        "backup_link_count": backup_count,
        "unique_substances": unique_substances,
        "shared_payment_degree": shared_degree,
        "burstiness": burst,
        "total_messages": len(scores),
    }
