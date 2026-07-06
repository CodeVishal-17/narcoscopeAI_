"""
Weak supervision (distant supervision).

We have no hand-labeled data to start with, so the rule engine becomes a set of
*labeling functions*: each looks at a message and votes POSITIVE (drug-sale),
NEGATIVE (benign), or ABSTAIN. Their combined vote produces noisy training
labels for the ML model, which then learns to generalize *beyond* the rules
(catching slang the rules miss) — the whole point of the hybrid design.

This is deliberately conservative: it only emits a confident label when signals
are strong, and abstains in the middle so the ML model isn't trained on garbage.
"""

from __future__ import annotations

from ..model.rules import score_message

LABEL_POS = 1
LABEL_NEG = 0
LABEL_ABSTAIN = -1

# Rule-score thresholds for confident weak labels.
POS_THRESHOLD = 3.0     # strong combined evidence -> positive
NEG_CEILING = 0.0       # no signal at all -> negative


def lf_high_rule_score(sig) -> int:
    return LABEL_POS if sig.score >= POS_THRESHOLD else LABEL_ABSTAIN


def lf_substance_plus_behaviour(sig) -> int:
    if sig.matched_terms and (sig.matched_phrases or sig.has_price_pattern):
        return LABEL_POS
    return LABEL_ABSTAIN


def lf_bot_storefront(sig) -> int:
    if sig.has_bot_command and sig.has_price_pattern:
        return LABEL_POS
    return LABEL_ABSTAIN


def lf_clearly_benign(sig) -> int:
    if sig.score <= NEG_CEILING and not sig.matched_emoji and not sig.external_links:
        return LABEL_NEG
    return LABEL_ABSTAIN


LABELING_FUNCTIONS = [
    lf_high_rule_score,
    lf_substance_plus_behaviour,
    lf_bot_storefront,
    lf_clearly_benign,
]


def weak_label(text: str) -> int:
    """
    Combine labeling-function votes into a single weak label.

    Any confident POSITIVE vote wins (recall-oriented: better to train on a
    borderline positive than miss the pattern). Otherwise, if a benign LF fires
    and nothing votes positive, label NEGATIVE. Else ABSTAIN.
    """
    sig = score_message(text)
    votes = [lf(sig) for lf in LABELING_FUNCTIONS]
    if LABEL_POS in votes:
        return LABEL_POS
    if LABEL_NEG in votes:
        return LABEL_NEG
    return LABEL_ABSTAIN
