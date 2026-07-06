"""
Train the ML message classifier (pass 2) — with leak-proof discipline.

Training set is assembled from three sources, in order of trust:
  1. Hand labels — TRAIN SPLIT ONLY (data/labels.jsonl)   — highest quality
  2. Weak labels — rules over sample/scraped data           — free, noisy
  3. Synthetic data — generated, balanced                   — bootstraps volume

Crucially, every training example whose text collides with a HELD-OUT TEST
message is dropped, so the test set stays pristine and the accuracy reported by
`evaluate.py` is honest. The held-out test split (see labeling/dataset.py) never
enters training here.

Run:
    python -m narcoscope.train
    python -m narcoscope.train --synthetic 800

Prints a cross-validated report over the TRAINING data (an internal sanity
check). The number that actually matters for production is `evaluate.py` run
against the held-out real-label test set.
"""

from __future__ import annotations

import argparse

from .config import SAMPLE_DATA
from .ingestion import FileIngestor
from .labeling import generate_dataset, weak_label, LabelStore, LABEL_ABSTAIN
from .labeling.dataset import _key
from .model.ml import MLClassifier


def _weak_label_file(path) -> list:
    rows = []
    if path and path.exists():
        for acc in FileIngestor.load(path):
            for msg in acc.messages:
                lab = weak_label(msg.text)
                if lab != LABEL_ABSTAIN:
                    rows.append((msg.text, lab))
    return rows


def build_dataset(n_synthetic: int, weak_source) -> tuple:
    store = LabelStore()
    test_keys = store.test_keys()          # the leakage guard set

    hand_texts, hand_labels = store.train_set()      # TRAIN split only
    hand = list(zip(hand_texts, hand_labels))
    weak = _weak_label_file(weak_source)
    synth = [(r["text"], r["label"]) for r in generate_dataset(n_synthetic)]

    # Order matters: hand labels last so they win on dedup.
    combined = synth + weak + hand
    seen, dropped_leak = {}, 0
    for text, label in combined:
        k = _key(text)
        if k in test_keys:                 # never train on a held-out test message
            dropped_leak += 1
            continue
        seen[text] = label

    texts = list(seen.keys())
    labels = list(seen.values())

    print(f"Training set: {len(texts)} messages "
          f"({len(hand)} hand-train, {len(weak)} weak, {len(synth)} synthetic; "
          f"deduped, {dropped_leak} dropped to protect the test set)")
    print(f"  positives: {sum(labels)}  negatives: {len(labels) - sum(labels)}")
    if not hand:
        print("  NOTE: no hand labels yet — model is bootstrapped from synthetic "
              "data only. Run `python -m narcoscope.label_tool` and re-train.")
    return texts, labels


def main():
    ap = argparse.ArgumentParser(description="Train the NarcoScope ML classifier.")
    ap.add_argument("--synthetic", type=int, default=400,
                    help="synthetic messages per class (default 400)")
    ap.add_argument("--weak-source", default=str(SAMPLE_DATA),
                    help="accounts JSON to weak-label for extra training data")
    ap.add_argument("--no-cv", action="store_true", help="skip cross-validation report")
    args = ap.parse_args()

    from pathlib import Path
    texts, labels = build_dataset(args.synthetic, Path(args.weak_source))

    clf = MLClassifier()
    if not args.no_cv and len(set(labels)) > 1:
        print("\nCross-validating over TRAINING data (internal sanity check only)...")
        report = clf.cross_val_report(texts, labels)
        for k, v in report.items():
            print(f"  {k:12s}: {v}")
        print("  (For real accuracy, run `python -m narcoscope.evaluate`.)")

    print("\nFitting final model on all training data...")
    clf.fit(texts, labels)
    path = clf.save()
    print(f"Saved model -> {path}")


if __name__ == "__main__":
    main()
