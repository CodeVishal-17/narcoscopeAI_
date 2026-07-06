"""
Hand-labeling CLI — the bridge from "prototype accuracy" to "real accuracy".

Reads messages from an accounts JSON (sample or scraped), shows each with the
model's current prediction and the rule evidence, and records your label with
full provenance via the leak-proof LabelStore (labeling/dataset.py). Each label
is auto-assigned to the train or test split deterministically, so you never have
to think about leakage.

Run:
    python -m narcoscope.label_tool                 # label the sample data
    python -m narcoscope.label_tool data/tg.json    # label scraped Telegram data
    python -m narcoscope.label_tool --limit 50

Keys per message:  1 = drug-sale   0 = benign   s = skip   q = save & quit

Prefer the web UI for volume:  python -m narcoscope.labeling.server
"""

from __future__ import annotations

import argparse

from .config import SAMPLE_DATA
from .ingestion import FileIngestor
from .labeling import LabelStore, split_of
from .model.hybrid import HybridClassifier


def main():
    ap = argparse.ArgumentParser(description="Hand-label messages for training/eval.")
    ap.add_argument("data", nargs="?", default=str(SAMPLE_DATA))
    ap.add_argument("--limit", type=int, default=0, help="max messages to show (0 = all)")
    ap.add_argument("--by", default="cli", help="annotator name (recorded as provenance)")
    args = ap.parse_args()

    accounts = FileIngestor.load(args.data)
    clf = HybridClassifier()
    store = LabelStore()
    seen = store.labeled_keys()
    from .labeling.dataset import _key

    queue = [
        (acc, m.text) for acc in accounts for m in acc.messages
        if _key(m.text) not in seen
    ]
    if args.limit:
        queue = queue[: args.limit]

    if not queue:
        print("Nothing new to label. Current label stats:")
        for k, v in store.stats().items():
            print(f"  {k}: {v}")
        return

    print(f"{len(queue)} messages to label. Keys: 1=drug-sale  0=benign  s=skip  q=quit\n")
    labeled = 0
    for acc, text in queue:
        v = clf.classify_message(text)
        dest = split_of(text)
        print("-" * 70)
        print(f"[{acc.platform}/{acc.handle}]  model={v.final_prob:.2f} ({v.decided_by})  "
              f"-> {dest} split")
        if v.signals.matched_terms or v.signals.matched_phrases:
            print(f"  evidence: terms={v.signals.matched_terms} "
                  f"phrases={v.signals.matched_phrases}")
        print(f"  > {text}")
        try:
            choice = input("  label [1/0/s/q]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = "q"
        if choice == "q":
            break
        if choice in ("1", "0"):
            store.add(text, int(choice), platform=acc.platform,
                      handle=acc.handle, labeled_by=args.by, source="cli")
            labeled += 1

    print(f"\nSaved {labeled} labels. Stats now:")
    for k, v in store.stats().items():
        print(f"  {k}: {v}")
    print("\nRe-run `python -m narcoscope.train` then `python -m narcoscope.evaluate`.")


if __name__ == "__main__":
    main()
