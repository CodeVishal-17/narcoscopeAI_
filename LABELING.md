# Labeling & Accuracy Workflow

This is how NarcoScope goes from *bootstrapped* accuracy (synthetic data, not
trustworthy) to *measured* accuracy on real data — the prerequisite for any
production use.

## Why this exists

The ML model ships trained on synthetic + rule-bootstrapped data. The
cross-validation numbers `train.py` prints are **optimistic** — they measure how
well the model separates data it helped generate, not how it performs on real
messages. A production accuracy claim requires:

1. **Real labeled data** — a human deciding, per message, drug-sale vs. benign.
2. **No leakage** — the messages you *test* on must be disjoint from the ones you
   *train* on. This is the single most common way ML accuracy numbers lie.

Both are enforced structurally here, so you can't accidentally cheat.

## The leak-proof split

Every labeled message is assigned to the **train** or **test** split
*deterministically from a hash of its text* (`labeling/dataset.py`), not
randomly. Consequences:

- A given message always lands in the same split, no matter when you label it.
- The test set stays stable and disjoint as labels accumulate.
- `train.py` additionally **drops any training example whose text collides with a
  test message**, so synthetic/weak data can't leak in either.

You never have to manage the split yourself — the labeling tools show you which
split each message will go to, and that's it.

## The loop

```
                ┌─────────────────────────────────────────────┐
                │  1. get real data                           │
   scrape  ──▶  │     python -m narcoscope.scrape telegram …  │
                └───────────────┬─────────────────────────────┘
                                ▼
                ┌─────────────────────────────────────────────┐
                │  2. hand-label it                           │
   web UI  ──▶  │     python -m narcoscope.labeling.server    │  ← fast, keyboard-driven
   or CLI  ──▶  │     python -m narcoscope.label_tool data/…  │
                └───────────────┬─────────────────────────────┘
                                ▼
                ┌─────────────────────────────────────────────┐
                │  3. retrain (train split only)              │
                │     python -m narcoscope.train              │
                └───────────────┬─────────────────────────────┘
                                ▼
                ┌─────────────────────────────────────────────┐
                │  4. measure on the held-out real labels     │
                │     python -m narcoscope.evaluate           │  ← the number that counts
                └─────────────────────────────────────────────┘
```

Repeat 1–4 as you collect more labels. Accuracy climbs and the numbers become
trustworthy as the test set grows.

## The web labeler

```bash
pip install fastapi uvicorn         # already in requirements notes
python -m narcoscope.labeling.server --source data/tg.json
# open http://127.0.0.1:8100
```

- Shows one message at a time with the model's current prediction and the rule
  evidence, plus which split it will join.
- Keyboard: **`1`** = drug-sale, **`0`** = benign, **`S`** = skip.
- Live footer: how many labeled (train/test), how many remain, and — once you
  have test labels — the running test accuracy with a reliability flag.

Every label is stored with provenance (who, when, source) in
`data/labels.jsonl`, so the label set is auditable.

## Honest accuracy — the guardrail

`evaluate.py` grades the classifier **only on the held-out test split of real
hand labels**, and it refuses to over-claim:

- Below **50** test labels, it reports the numbers but flags them as *indicative,
  not a production accuracy claim*, and tells you how many more to label.
- It warns on class imbalance (want ≥15 of each class).
- It breaks results down per platform when that metadata is present.

```bash
python -m narcoscope.evaluate            # full hybrid, held-out real labels
python -m narcoscope.evaluate --ml-only  # raw ML stage only
```

## Rule of thumb for "production ready" accuracy

- **≥ 300–500 hand labels** total, with a healthy mix of both classes and all
  three platforms, gives a test split (~20%) big enough for numbers you can
  defend.
- Track precision **and** recall separately: in this domain a false negative
  (missed dealer) and a false positive (flagging an innocent account) have very
  different costs — decide your target per the investigation's tolerance, and
  tune the decision threshold accordingly.
