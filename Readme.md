# Cyber Watch — Prototype (SIH-style: Detecting drug-sale activity on Telegram/WhatsApp/Instagram)

This is a working slice of the full solution: the **content analysis / risk-scoring engine**
plus an **investigator dashboard** to visualize its output. It runs entirely on synthetic
sample data — no real scraping, no live platform connections — so it's safe to demo and easy
to extend.

> **v0.2 — real-data pipeline.** The original single-file rule engine
> (`content_analysis_engine.py`) still works and is kept for reference. A new
> staged pipeline under [`narcoscope/`](narcoscope/) adds real ingestion,
> proper text processing, feature engineering, and a **hybrid classifier
> (rules → ML → LLM)**. See **[The `narcoscope/` pipeline](#the-narcoscope-pipeline-real-data--ml)**
> below.

## Files

| File | What it is |
|---|---|
| `content_analysis_engine.py` | Rule-based NLP/behavior scorer. Reads `sample_data.json`, scores each message, rolls scores up to an account-level risk score and band (LOW/MEDIUM/HIGH/CRITICAL), and detects likely bots and cross-account links via shared payment handles. Writes `flagged_output.json`. |
| `sample_data.json` | Synthetic multi-platform dataset (Telegram channels/bots, WhatsApp groups, Instagram profiles) — a mix of drug-sale-like and clearly benign accounts, so the engine's discrimination is visible. |
| `flagged_output.json` | Output of the last run — this is what feeds the dashboard. |
| `dashboard.html` | Self-contained investigator dashboard (open directly in a browser, no server needed). Filter by risk band/platform, click a row to see evidence and linked accounts, and a "Generate legal-request dossier" button that demonstrates the intended workflow. |

## Run it

```
python3 content_analysis_engine.py
```

No dependencies beyond the Python standard library. Edit `sample_data.json` to add your own
test messages/accounts and re-run — `dashboard.html` currently has the *last generated*
`flagged_output.json` embedded directly in it for portability; regenerate that embed if you
change the data (see "Wiring it together" below).

## How the scoring works

Each message gets points for:
- Known substance names (MDMA, LSD, mephedrone, etc.)
- Sale-behavior phrases ("DM to order", "COD available", "discreet packing"...)
- Suspicious emoji combinations
- Telegram bot commands (`/menu`, `/order`...) combined with a price pattern

Message scores roll up into an account score using a blend of the *worst single message*
(catches a one-off but serious post) and the *overall pattern* (catches accounts that are
persistently suspicious even if no single message is damning). Bots get a small additional
weight since an automated storefront scales faster than a manual seller.

Cross-account correlation currently checks for shared payment handles (UPI IDs) across
accounts — a legal, public-data OSINT signal that's often the strongest lead for showing the
same operator runs multiple storefronts across platforms.

## What this prototype deliberately does NOT do (and why)

- **It doesn't scrape live Telegram/WhatsApp/Instagram.** Wiring up real ingestion (Telethon
  for Telegram, Meta Graph API for Instagram, invite-link discovery for WhatsApp) is
  straightforward to add but was left out of this prototype to keep it runnable anywhere
  without API keys or ToS/legal review.
- **It doesn't claim to extract IP addresses, phone numbers, or emails from public content**
  — because that data isn't exposed by these platforms to begin with. The "Generate
  legal-request dossier" button in the dashboard reflects the real workflow: the system
  packages evidence, and a human investigator submits that evidence to the platform under
  Indian legal process (CrPC/BNSS Section 91, or MLAT for foreign platforms) to obtain
  subscriber records. Any tool claiming to bypass this step would require illegal
  interception or hacking.
- **The keyword/slang dictionary here is intentionally minimal** — limited to substance
  names and generic sale-behavior phrases already public in the problem statement. A real
  deployment's evasion-resistant slang dictionary should live in a restricted,
  analyst-maintained module, not in public source code, since publishing it is itself a
  how-to-evade-detection guide.

## Extending toward the full solution

1. **Swap the rule-based scorer for a hybrid**: keep this engine as a fast first-pass filter,
   add a fine-tuned transformer (IndicBERT/XLM-R) behind it for messages that use slang not
   yet in the dictionary — the rule-based flags become training labels over time.
2. **Add real ingestion** per platform (see architecture notes above).
3. **Add a human-review queue** before anything reaches the "legal-request" stage — no
   autonomous action should ever fire off a report or referral without analyst sign-off.
4. **Add audit logging + Section 65B-compliant evidence export** (hashes, timestamps, chain
   of custody) so flagged content can actually be used in court.

## Wiring the dashboard to fresh data (optional)

`dashboard.html` embeds a JSON snapshot directly in a `<script>` tag for portability (works
by double-clicking the file, no server required). To refresh it after changing
`sample_data.json`:

```
python3 content_analysis_engine.py
python3 -c "import json; print(json.dumps(json.load(open('flagged_output.json'))))"
```

Paste that single-line JSON output in place of the `const DATA = {...}` value in
`dashboard.html`.

---

# The `narcoscope/` pipeline (real data + ML)

The v0.2 upgrade turns the prototype into a real, staged pipeline that can
ingest live data, process and feature-engineer it properly, and classify with a
hybrid of rules, machine learning, and (optionally) an LLM.

```
ingest ─▶ process ─▶ engineer features ─▶ classify (rules ─▶ ML ─▶ LLM)
       ─▶ account risk rollup ─▶ cross-account correlation ─▶ flagged_output.json
```

## Layout

| Module | What it does |
|---|---|
| `narcoscope/ingestion/` | Common account schema + `file`, `telegram`, `instagram`, `whatsapp` ingestors |
| `narcoscope/processing/` | Normalization, **de-obfuscation** (leetspeak/spacing/dotting), Hinglish detection |
| `narcoscope/features/` | Message- and account-level feature engineering (lexical, behavioral, structural, network) |
| `narcoscope/labeling/` | Weak-supervision labeling functions + synthetic data generation (bootstrap from zero) |
| `narcoscope/model/` | `rules` (pass 1) → `ml` (pass 2) → `llm` (pass 3) → `hybrid` orchestrator |
| `narcoscope/train.py` | Train the ML classifier; prints a cross-validated report |
| `narcoscope/evaluate.py` | Measure precision/recall/F1 against a hand-labeled test set |
| `narcoscope/label_tool.py` | CLI to hand-label real messages into ground truth |
| `narcoscope/pipeline.py` | End-to-end runner → writes `flagged_output.json` |
| `narcoscope/scrape.py` | Unified scraper CLI for the three platforms |

## Quick start (runs offline, no keys)

```bash
pip install -r requirements.txt          # scikit-learn, numpy, joblib
python -m narcoscope.train               # bootstrap + train the ML model
python -m narcoscope.pipeline            # analyze sample data → flagged_output.json
```

The trained model and the existing `dashboard.html` need nothing else — the
pipeline writes the same (extended) output schema the dashboard reads.

## The three classification stages (hybrid)

1. **Rules (pass 1)** — the original keyword/emoji/behavior scorer, now running
   on *de-obfuscated* text so `m3ph3dr0n3` and `m d m a` no longer slip through.
   Fast and fully explainable; also acts as a **weak labeler** to bootstrap
   training data.
2. **ML (pass 2)** — TF-IDF (word + char n-grams) on de-obfuscated text, fused
   with engineered numeric features, classified by logistic regression. Runs on
   CPU, trains in seconds, generalizes beyond the hand-written rules to slang and
   Hinglish the rules miss.
3. **LLM (pass 3)** — only messages the ML stage is *unsure* about (probability
   in an ambiguous band) escalate to Claude (**Haiku 4.5** by default) for
   adjudication, keeping cost bounded. Enable with:
   ```bash
   pip install anthropic
   export ANTHROPIC_API_KEY=sk-ant-...
   export NARCOSCOPE_LLM=1
   ```
   If disabled, the pipeline simply uses the ML probability — nothing breaks.

## Real scraping — what each platform can honestly do

| Platform | Reality | How |
|---|---|---|
| **Telegram** | ✅ Real & legitimate — official MTProto API | `pip install telethon`, get free `api_id`/`api_hash` from [my.telegram.org](https://my.telegram.org), then `python -m narcoscope.scrape telegram @channel -o data/tg.json` |
| **Instagram** | ⚠️ Unofficial, ToS-violating, ban-prone, brittle | `pip install instaloader`, then `python -m narcoscope.scrape instagram handle -o data/ig.json` (public bios/captions only, heavily throttled) |
| **WhatsApp** | ⛔ No true scraping — groups are end-to-end encrypted | "Join-then-export" only: an investigator's own account joins a public group, then WhatsApp → *Export chat* → `python -m narcoscope.scrape whatsapp "Group.txt" -o data/wa.json`. A live-session bridge (Baileys/whatsapp-web.js) can dump joined-group messages to JSON, but it automates your own number and risks a ban. |

Any scraped JSON drops straight into the pipeline:
`python -m narcoscope.pipeline data/tg.json`.

## Reaching *real* accuracy (important)

The training set is bootstrapped from the rule engine + synthetic data, so the
cross-validation numbers `train.py` prints are **optimistic** — they measure
separability on data the model helped generate, not real-world accuracy. To get
a number you can trust:

1. Scrape (or assemble) a few hundred **real** messages.
2. Hand-label them: `python -m narcoscope.label_tool data/tg.json`
   (writes `data/labels.jsonl`).
3. Retrain — hand labels override weak/synthetic ones: `python -m narcoscope.train`
4. Hold some labels back as a test set and measure honestly:
   `python -m narcoscope.evaluate data/testset.jsonl`

Only step 4 produces a defensible accuracy figure. The whole workflow — the
leak-proof train/test split, the web labeling UI, and the honest accuracy
report — is documented in **[LABELING.md](LABELING.md)**.

Fast labeling UI (keyboard-driven, shows model prediction + evidence + live accuracy):

```bash
python -m narcoscope.labeling.server        # open http://127.0.0.1:8100
```

## Scope & ethics (unchanged, and load-bearing)

This tool builds an **evidence dossier for human analyst review** — it does not
scrape private data, extract phone/IP/email, or take any autonomous action.
Obtaining subscriber records still requires lawful process (Section 91 CrPC/BNSS,
or MLAT for foreign platforms). The evasion-resistant slang dictionary is kept
intentionally minimal in public source; a real deployment's should live in a
restricted, analyst-maintained module.