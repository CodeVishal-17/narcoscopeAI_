"""
End-to-end pipeline: ingest -> process/classify (hybrid) -> features -> account
risk rollup -> cross-account correlation -> flagged_output.json.

Run:
    python -m narcoscope.pipeline                      # uses sample data
    python -m narcoscope.pipeline path/to/accounts.json

Output schema matches (and extends) the original flagged_output.json so the
existing dashboard keeps working, while adding ML/LLM detail per message.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone

from .config import SAMPLE_DATA, FLAGGED_OUTPUT, risk_band
from .ingestion import FileIngestor
from .features.engineer import account_features
from .model.hybrid import HybridClassifier


def _payment_index(accounts: list) -> dict:
    idx = defaultdict(set)
    for acc in accounts:
        for h in acc.payment_handles:
            idx[h].add(acc.account_id)
    return idx


def _account_risk(verdicts: list, is_bot: bool) -> float:
    probs = [v.final_prob for v in verdicts]
    if not probs:
        return 0.0
    mx = max(probs)
    mean = sum(probs) / len(probs)
    flagged_ratio = sum(1 for p in probs if p >= 0.5) / len(probs)
    # Blend intensity (worst message), prevalence (mean), and spread (ratio),
    # scaled to the 0-10 band range the dashboard expects.
    score = (mx * 0.4 + mean * 0.35 + flagged_ratio * 0.25) * 10
    if is_bot:
        score += 1.0
    return round(score, 2)


def analyze(accounts: list, clf: HybridClassifier) -> dict:
    pay_idx = _payment_index(accounts)
    reports = []

    for acc in accounts:
        verdicts = [clf.classify_message(m.text) for m in acc.messages]
        signals = [v.signals for v in verdicts]

        bot_cmd_ratio = (
            sum(1 for s in signals if s.has_bot_command) / len(signals)
            if signals else 0.0
        )
        is_bot = acc.account_type == "bot" or bot_cmd_ratio > 0.3

        feats = account_features(acc, signals, pay_idx)
        risk = _account_risk(verdicts, is_bot)

        flagged = sorted(
            [v for v in verdicts if v.is_flagged], key=lambda v: -v.final_prob
        )
        evidence = [
            {
                "text": v.text,
                "final_prob": v.final_prob,
                "decided_by": v.decided_by,
                "rule_score": v.rule_score,
                "ml_prob": v.ml_prob,
                "llm": v.llm,
                "matched_terms": v.signals.matched_terms,
                "matched_phrases": v.signals.matched_phrases,
                "matched_emoji": v.signals.matched_emoji,
            }
            for v in flagged[:3]
        ]

        reports.append({
            "account_id": acc.account_id,
            "platform": acc.platform,
            "handle": acc.handle,
            "account_type": acc.account_type,
            "source": acc.source,
            "is_probable_bot": is_bot,
            "risk_score": risk,
            "risk_band": risk_band(risk),
            "flagged_message_count": len(flagged),
            "total_messages_seen": len(verdicts),
            "features": feats,
            "evidence_sample": evidence,
            "message_verdicts": [
                {"text": v.text, "final_prob": v.final_prob, "decided_by": v.decided_by}
                for v in verdicts
            ],
        })

    reports.sort(key=lambda r: -r["risk_score"])
    clusters = {h: sorted(ids) for h, ids in pay_idx.items() if len(ids) > 1}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "accounts_analyzed": len(reports),
        "flagged_accounts": sum(1 for r in reports if r["risk_band"] in ("HIGH", "CRITICAL")),
        "model_stages": {
            "rules": True,
            "ml": clf.ml is not None,
            "llm": clf.llm.enabled,
        },
        "reports": reports,
        "linked_account_clusters": clusters,
    }


def main():
    ap = argparse.ArgumentParser(description="Run the NarcoScope detection pipeline.")
    ap.add_argument("data", nargs="?", default=str(SAMPLE_DATA),
                    help="path to accounts JSON (default: sample data)")
    ap.add_argument("-o", "--output", default=str(FLAGGED_OUTPUT),
                    help="output path (default: flagged_output.json)")
    args = ap.parse_args()

    accounts = FileIngestor.load(args.data)
    clf = HybridClassifier()
    print(f"Stages active -> rules: yes | ml: {clf.ml is not None} | llm: {clf.llm.enabled}")

    output = analyze(accounts, clf)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nAnalyzed {output['accounts_analyzed']} accounts. "
          f"HIGH/CRITICAL: {output['flagged_accounts']}")
    print("Top by risk:")
    for r in output["reports"][:5]:
        print(f"  [{r['risk_band']:8s}] {r['platform']:10s} {r['handle']:24s} "
              f"score={r['risk_score']}")
    if output["linked_account_clusters"]:
        print("\nLinked clusters (shared payment handle):")
        for h, ids in output["linked_account_clusters"].items():
            print(f"  {h} -> {ids}")
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
