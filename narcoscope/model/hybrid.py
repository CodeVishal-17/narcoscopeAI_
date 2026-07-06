"""
Hybrid orchestrator: rules (fast) -> ML (volume) -> LLM (ambiguous only).

Per message:
  1. Rule engine always runs — cheap, explainable, gives structured evidence.
  2. ML classifier gives a probability (if a trained model is available).
  3. If the ML probability is ambiguous (config band) AND the LLM stage is
     enabled, escalate that one message to the LLM for adjudication.

The final probability is whichever stage had the last, most-informed say, and
each verdict records which stage decided it so the dashboard can show why.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import LLM_ESCALATE_LOW, LLM_ESCALATE_HIGH
from .rules import score_message, MessageSignals
from .ml import MLClassifier
from .llm import LLMClassifier


@dataclass
class MessageVerdict:
    text: str
    final_prob: float
    is_flagged: bool
    decided_by: str                 # "rules" | "ml" | "llm"
    rule_score: float
    ml_prob: float | None = None
    llm: dict | None = None
    signals: MessageSignals | None = field(default=None, repr=False)


class HybridClassifier:
    def __init__(self, ml: MLClassifier | None = None, llm: LLMClassifier | None = None):
        # ML is optional — if no trained model exists yet, fall back to rules.
        if ml is None and MLClassifier.exists():
            try:
                ml = MLClassifier.load()
            except Exception:
                ml = None
        self.ml = ml
        self.llm = llm if llm is not None else LLMClassifier()

    def classify_message(self, text: str) -> MessageVerdict:
        sig = score_message(text)
        rule_prob = min(sig.score / 7.0, 1.0)   # map rule score onto [0,1]

        decided_by = "rules"
        final = rule_prob
        ml_prob = None

        if self.ml is not None:
            ml_prob = float(self.ml.predict_proba(text))
            final = ml_prob
            decided_by = "ml"
            # The ML model is trained mostly on English; a strong, transparent
            # rule hit (e.g. Hindi/Hinglish slang the model hasn't learned yet)
            # must not be silently overridden by a weaker ML score. Rules act as
            # a high-precision safety net: take the higher of the two.
            if rule_prob > final:
                final = rule_prob
                decided_by = "rules"

        llm_result = None
        base = ml_prob if ml_prob is not None else rule_prob
        if self.llm.enabled and LLM_ESCALATE_LOW <= base <= LLM_ESCALATE_HIGH:
            llm_result = self.llm.classify(text)
            if llm_result is not None:
                conf = llm_result["confidence"]
                final = conf if llm_result["label"] == 1 else 1.0 - conf
                decided_by = "llm"

        return MessageVerdict(
            text=text,
            final_prob=round(final, 3),
            is_flagged=final >= 0.5,
            decided_by=decided_by,
            rule_score=sig.score,
            ml_prob=None if ml_prob is None else round(ml_prob, 3),
            llm=llm_result,
            signals=sig,
        )
