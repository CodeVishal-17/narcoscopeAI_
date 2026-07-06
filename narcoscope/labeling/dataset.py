"""
Label store with LEAK-PROOF train/test discipline — the core of trustworthy
accuracy.

The single most common way ML accuracy numbers lie is data leakage: the same
message (or a near-duplicate) ends up in both the training set and the test set,
so the model is graded on examples it effectively memorized. In a production
tool whose output may support a legal request, an inflated accuracy number is
worse than no number.

This module prevents that structurally:

* Every message is assigned to ``train`` or ``test`` **deterministically from a
  hash of its normalized text** — not randomly. A given message therefore always
  lands in the same split, no matter when it was labeled. The test set stays
  stable and disjoint from training as labels accumulate.
* Training code excludes any example whose normalized text collides with a test
  message (see ``test_keys``), so synthetic/weak data can't leak in either.
* Every label carries provenance (who, when, source) so the label set is
  auditable — a production requirement, not a nicety.

Labels live in ``data/labels.jsonl`` (one JSON object per line, append-only;
re-labeling the same text appends a new row and the latest wins).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone

from ..config import LABELS_FILE, DATA_DIR, TEST_FRACTION
from ..processing import normalize

_BUCKETS = 1000


def _key(text: str) -> str:
    """Canonical identity of a message for dedup + split assignment."""
    return normalize(text)


def split_of(text: str) -> str:
    """
    Deterministic split assignment. Same text -> same split, always.

    We hash the normalized text to a stable bucket in [0, 1000) and send the
    lowest ``TEST_FRACTION`` of buckets to the test set. Because it's a pure
    function of content, re-running, re-labeling, or adding data never moves a
    message across the train/test boundary.
    """
    h = hashlib.sha256(_key(text).encode("utf-8")).hexdigest()
    bucket = int(h[:8], 16) % _BUCKETS
    return "test" if bucket < TEST_FRACTION * _BUCKETS else "train"


class LabelStore:
    def __init__(self, path=LABELS_FILE):
        self.path = path

    # -- reading --------------------------------------------------------------
    def load(self) -> list:
        """Return deduped label records (latest label per unique text wins)."""
        by_key = {}
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    rec["split"] = split_of(rec["text"])   # always recompute
                    by_key[_key(rec["text"])] = rec
        return list(by_key.values())

    def labeled_keys(self) -> set:
        return {_key(r["text"]) for r in self.load()}

    def split(self, which: str) -> tuple:
        """Return (texts, labels) for split ``which`` ('train' or 'test')."""
        recs = [r for r in self.load() if r["split"] == which]
        return [r["text"] for r in recs], [int(r["label"]) for r in recs]

    def train_set(self) -> tuple:
        return self.split("train")

    def test_set(self) -> tuple:
        return self.split("test")

    def test_keys(self) -> set:
        """Normalized texts held out for testing — exclude these from training."""
        return {_key(t) for t in self.test_set()[0]}

    # -- writing --------------------------------------------------------------
    def add(self, text: str, label: int, *, platform: str = "", handle: str = "",
            labeled_by: str = "cli", source: str = "manual") -> dict:
        rec = {
            "text": text,
            "label": int(label),
            "platform": platform,
            "handle": handle,
            "labeled_by": labeled_by,
            "labeled_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
        }
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        rec["split"] = split_of(text)
        return rec

    # -- reporting ------------------------------------------------------------
    def stats(self) -> dict:
        recs = self.load()
        out = {"total": len(recs), "train": {}, "test": {}, "by_platform": {}}
        for which in ("train", "test"):
            sub = [r for r in recs if r["split"] == which]
            c = Counter(int(r["label"]) for r in sub)
            out[which] = {"n": len(sub), "positive": c.get(1, 0), "negative": c.get(0, 0)}
        out["by_platform"] = dict(Counter(r.get("platform", "") or "?" for r in recs))
        return out
