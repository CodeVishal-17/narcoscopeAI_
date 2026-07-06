"""
Classification stages:

    rules  (pass 1)  fast, explainable keyword/behaviour scorer
    ml     (pass 2)  TF-IDF + gradient-boosting, trained on weak+hand labels
    llm    (pass 3)  Claude few-shot, only for messages the ML stage is unsure of
    hybrid           orchestrates the three and produces a final message verdict
"""

from .rules import score_message, MessageSignals

__all__ = ["score_message", "MessageSignals"]
