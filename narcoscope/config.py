"""
Central configuration: paths, thresholds, and signal dictionaries.

The signal dictionaries here are intentionally the same limited, public-scope
lists from the original prototype (substance names + generic sale phrases
already named in the problem statement). A production deployment's
evasion-resistant slang dictionary should live in a restricted,
analyst-maintained module — not in public source — because publishing it is
itself a how-to-evade-detection guide.
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent

# Load repo_root/.env (TELEGRAM_API_ID, TELEGRAM_API_HASH, etc.) into the
# process environment. Every entry point (Django, login_telegram.py, CLI
# scripts) imports this module first, so this is the one place credentials
# get loaded — no need to `set`/`$env:` them in every terminal you use.
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "models"

# The repo ships these with spaces in the filenames; keep working with them
# but prefer the underscore names if present.
SAMPLE_DATA = ROOT / "sample_data.json"
for _candidate in (DATA_DIR / "sample_data.json", ROOT / "sample_data.json", ROOT / "sample data.json"):
    if _candidate.exists():
        SAMPLE_DATA = _candidate
        break

FLAGGED_OUTPUT = ROOT / "flagged_output.json"
LABELS_FILE = DATA_DIR / "labels.jsonl"

# Fraction of hand labels held out as a locked test set. The split is assigned
# DETERMINISTICALLY per message (by content hash) so a given message always
# lands in the same split — this is what keeps the test set leak-proof as labels
# accumulate. Changing this value re-buckets existing labels; don't change it
# once you've reported accuracy against a test set.
TEST_FRACTION = 0.2
SYNTHETIC_FILE = DATA_DIR / "synthetic_messages.jsonl"
ML_MODEL_FILE = MODEL_DIR / "message_classifier.joblib"

# Telegram (Telethon) — absolute session path so the interactive login and the
# headless scraper share ONE authenticated session regardless of working dir.
# Telethon appends ".session" to this stem.
TELEGRAM_SESSION = str(ROOT / "telegram")
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")

# --------------------------------------------------------------------------
# Risk bands (account-level score -> label)
# --------------------------------------------------------------------------
RISK_BANDS = [
    (7.0, "CRITICAL"),
    (4.0, "HIGH"),
    (2.0, "MEDIUM"),
    (0.0, "LOW"),
]

# --------------------------------------------------------------------------
# Hybrid routing thresholds (probability from the ML stage)
# --------------------------------------------------------------------------
# Messages whose ML probability lands in this ambiguous band get escalated to
# the LLM stage (if enabled). Confident predictions skip the LLM to save cost.
LLM_ESCALATE_LOW = 0.35
LLM_ESCALATE_HIGH = 0.75

# --------------------------------------------------------------------------
# LLM stage
# --------------------------------------------------------------------------
LLM_ENABLED = os.getenv("NARCOSCOPE_LLM", "0") == "1"
LLM_MODEL = os.getenv("NARCOSCOPE_LLM_MODEL", "claude-haiku-4-5-20251001")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# --------------------------------------------------------------------------
# Signal dictionaries (prototype public scope — see module docstring)
# --------------------------------------------------------------------------
SUBSTANCE_TERMS = {
    "mdma": 3.0, "lsd": 3.0, "mephedrone": 3.0, "meow meow": 3.0,
    "charas": 2.5, "ganja": 2.0, "weed": 1.5, "hash": 2.0,
    "party pills": 2.5, "acid tabs": 2.5, "blotters": 2.5,
    "ecstasy": 2.5, "molly": 2.5,
    # --- Hindi / Hinglish substance terms (Devanagari + romanized) ---
    # Tuned for the North/Central-India (incl. MP) context: "chitta"/"garda"
    # (heroin), "afeem" (opium), "maal"/"nasha" are coded/ambiguous so they
    # carry low weight and only matter alongside sale behavior.
    "चरस": 2.5, "गांजा": 2.0, "गाँजा": 2.0, "अफीम": 3.0, "अफ़ीम": 3.0,
    "भांग": 1.5, "भाँग": 1.5, "चिट्टा": 3.0, "स्मैक": 3.0, "गर्दा": 2.5,
    "नशा": 1.0, "माल": 1.0,
    "chitta": 3.0, "garda": 2.5, "afeem": 3.0, "smack": 3.0, "bhang": 1.5,
    "sulfa": 2.0, "brown sugar": 2.5, "nasha": 1.0,
    # Additional synthetic drugs
    "cocaine": 3.0, "heroin": 3.0, "crystal meth": 3.0, "methamphetamine": 3.0,
    "ketamine": 2.5, "tramadol": 2.0, "alprazolam": 2.0, "xanax": 2.5,
    "coke": 2.0, "crack": 2.5, "snow": 1.5, "ice": 1.5, "glass": 1.5,
    "dope": 2.0, "gear": 1.5, "powder": 1.0, "pills": 1.5,
    "opioids": 2.5, "fentanyl": 3.0, "morphine": 2.5, "codeine": 2.0,
    "nitrazepam": 2.0, "clonazepam": 2.0, "diazepam": 2.0,
    "psychedelics": 2.5, "shrooms": 2.0, "psilocybin": 3.0,
    "dmt": 3.0, "2cb": 3.0, "mda": 3.0, "ghb": 3.0, "gbl": 3.0,
    # Hinglish/regional
    "bhaang": 1.5, "charas chacha": 2.5, "gaddi": 2.0, "ticker": 2.0,
    "mephe": 3.0, "m cat": 3.0, "drone": 2.0, "bubbles": 2.0,
}

BEHAVIORAL_PHRASES = {
    "dm to order": 2.0,
    "dm for price": 2.0,
    "cod available": 1.5,
    "safe delivery": 1.5,
    "discreet packing": 2.5,
    "no minors": 1.0,
    "quality guaranteed": 1.0,
    "stock available": 1.0,
    "price list": 1.5,
    "wholesale rate": 1.5,
    "pan india delivery": 2.0,
    "backup channel": 1.5,
    "new channel link": 1.0,
    # --- Hindi / Hinglish sale-behavior phrases ---
    "होम डिलीवरी": 1.5, "डिलीवरी उपलब्ध": 1.5, "रेट पूछो": 2.0,
    "डीएम करो": 2.0, "माल है": 2.0, "माल चाहिए": 1.5, "स्टॉक है": 1.0,
    "सेटिंग हो जाएगी": 1.5, "छुपा के": 1.5,
    "rate pucho": 2.0, "dm karo": 2.0, "maal hai": 2.0, "maal chahiye": 1.5,
    "setting ho jayegi": 1.5, "home delivery": 1.0, "delivery available": 1.0,
    "cash on delivery": 1.0, "discreet delivery": 1.5,
    # Additional behavioral signals
    "order now": 1.5, "contact us": 1.0, "bulk order": 2.0,
    "minimum order": 1.5, "free sample": 1.5, "test delivery": 1.5,
    "trusted seller": 1.5, "verified seller": 1.5, "100% pure": 2.0,
    "guaranteed quality": 1.5, "no risk delivery": 2.0,
    "door delivery": 1.5, "doorstep delivery": 1.5,
    "express delivery": 1.0, "same day delivery": 1.5,
    "signal me": 2.0, "wickr": 2.5, "telegram only": 2.0,
    "crypto payment": 2.0, "btc accepted": 2.5, "usdt": 2.0,
    "no advance": 1.5, "advance payment": 1.5,
    "all india": 1.5, "across india": 1.5,
    # Hindi additions
    "bulk maal": 2.0, "thok bhav": 2.0, "seedha contact": 2.0,
    "guarantee ke sath": 1.5, "pakka maal": 2.0,
}

EMOJI_SIGNALS = {
    "🔌": 1.0,   # "the plug"
    "🍬": 0.5,
    "❄️": 1.0,
    "🌿": 0.5,
    "💊": 1.5,
    "🚀": 0.5,
    "💎": 1.0,  # premium/quality signal
    "🤝": 0.5,  # deal
    "📦": 1.0,  # delivery
    "🚚": 1.0,  # delivery
    "💰": 1.0,  # money/payment
    "📲": 0.5,  # contact via phone
    "🔒": 0.5,  # secure/discreet
    "⚡": 0.5,  # fast delivery
    "🧊": 1.5,  # ice/meth slang
    "🍄": 1.5,  # shrooms
    "🥦": 1.0,  # weed
    "🌱": 0.5,  # weed
}

BACKUP_CHANNEL_PHRASES = [
    "backup channel", "new channel link", "if this gets banned",
    "if this group gets removed", "in case this one gets banned",
    "join our new group", "join backup", "alternative channel",
    "channel got banned", "group got banned",
]


def risk_band(score: float) -> str:
    for threshold, label in RISK_BANDS:
        if score >= threshold:
            return label
    return "LOW"
