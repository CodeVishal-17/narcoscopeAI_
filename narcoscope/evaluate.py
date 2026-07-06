"""
Evaluation harness — the number that actually decides "production ready".

By default this grades the classifier against the HELD-OUT TEST SPLIT of your
real hand labels (see labeling/dataset.py) — messages the model was never
trained on. That disjointness is enforced structurally in train.py, so this
number is honest, not inflated by leakage.

Run:
    python -m narcoscope.evaluate                 # grade on held-out real labels
    python -m narcoscope.evaluate --ml-only       # raw ML stage, not full hybrid
    python -m narcoscope.evaluate --file some.jsonl   # grade on an explicit set

It refuses to over-claim: below a minimum test-set size it reports the numbers
but flags them as not-yet-reliable and tells you how many more labels you need.
"""

from __future__ import annotations

import argparse
import json

from .labeling import LabelStore
from .model.hybrid import HybridClassifier
from .model.ml import MLClassifier

# Below this many test labels, precision/recall are too noisy to trust as a
# production accuracy claim (a single flip moves F1 by several points).
MIN_RELIABLE_TEST = 50
# And you want a reasonable number of each class, or per-class metrics are moot.
MIN_PER_CLASS = 15


def _load_file(path: str) -> tuple:
    texts, labels, platforms = [], [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            texts.append(d["text"])
            labels.append(int(d["label"]))
            platforms.append(d.get("platform", "?"))
    return texts, labels, platforms


def metrics(y_true: list, y_pred: list) -> dict:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    acc = (tp + tn) / len(y_true) if y_true else 0.0
    return {
        "n": len(y_true), "positives": sum(y_true),
        "precision": round(prec, 3), "recall": round(rec, 3),
        "f1": round(f1, 3), "accuracy": round(acc, 3),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    }


def _predict(texts: list, ml_only: bool) -> list:
    if ml_only:
        model = MLClassifier.load()
        return [int(p >= 0.5) for p in model.predict_proba(texts)]
    clf = HybridClassifier()
    return [int(clf.classify_message(t).is_flagged) for t in texts]


def main():
    ap = argparse.ArgumentParser(description="Evaluate NarcoScope on held-out real labels.")
    ap.add_argument("--file", help="explicit JSONL of {text,label[,platform]} to grade on")
    ap.add_argument("--ml-only", action="store_true",
                    help="grade the raw ML stage instead of the full hybrid")
    args = ap.parse_args()

    if args.file:
        texts, labels, platforms = _load_file(args.file)
        source = args.file
    else:
        texts, labels = LabelStore().test_set()
        platforms = ["?"] * len(texts)
        source = "held-out test split of real hand labels"

    if not texts:
        print("No test data. Hand-label some messages first:")
        print("    python -m narcoscope.label_tool        (CLI)")
        print("    python -m narcoscope.labeling.server    (web UI)")
        return

    preds = _predict(texts, args.ml_only)
    m = metrics(labels, preds)
    stage = "ML-only" if args.ml_only else "hybrid"

    print(f"Evaluated {m['n']} messages ({stage}) on {source}\n")
    for k in ("precision", "recall", "f1", "accuracy"):
        print(f"  {k:10s}: {m[k]}")
    print(f"\n  confusion:  TP={m['tp']}  FP={m['fp']}  TN={m['tn']}  FN={m['fn']}")

    # per-platform breakdown when available
    if any(p != "?" for p in platforms):
        print("\n  per-platform:")
        for plat in sorted(set(platforms)):
            idx = [i for i, p in enumerate(platforms) if p == plat]
            pm = metrics([labels[i] for i in idx], [preds[i] for i in idx])
            print(f"    {plat:10s} n={pm['n']:3d}  P={pm['precision']}  "
                  f"R={pm['recall']}  F1={pm['f1']}")

    # honesty guardrails — refuse to let a tiny test set masquerade as production accuracy
    pos, neg = m["positives"], m["n"] - m["positives"]
    warnings = []
    if m["n"] < MIN_RELIABLE_TEST:
        warnings.append(
            f"test set is small ({m['n']} < {MIN_RELIABLE_TEST}); these numbers "
            f"are indicative, NOT a production accuracy claim. Label "
            f"~{MIN_RELIABLE_TEST - m['n']} more messages.")
    if pos < MIN_PER_CLASS or neg < MIN_PER_CLASS:
        warnings.append(
            f"class imbalance in test set (pos={pos}, neg={neg}); want ≥"
            f"{MIN_PER_CLASS} of each for trustworthy precision/recall.")
    if warnings:
        print("\n  ⚠ RELIABILITY:")
        for w in warnings:
            print(f"    - {w}")
    else:
        print("\n  ✓ test set is large and balanced enough to treat these as real numbers.")


if __name__ == "__main__":
    main()
