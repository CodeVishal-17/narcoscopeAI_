"""
Metadata extraction from raw text — Indian mobile numbers, email IDs,
UPI payment handles (which often embed mobile numbers), cryptocurrency
addresses, and Telegram/Instagram/WhatsApp cross-links.

All regex are compile-time constants for performance.
Results are structured so they appear in the evidence dossier.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field

# ---------- compiled patterns ----------

# Indian mobile: starts with 6-9, 10 digits total, word-boundary protected
MOBILE_RE = re.compile(
    r"(?<![\d\-+])([6-9]\d{9})(?![\d\-])",
    re.IGNORECASE,
)

# Email
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

# UPI VPA: <something>@<provider> — many embed phone numbers
UPI_RE = re.compile(
    r"[a-zA-Z0-9.\-_+]{3,}@(?:upi|paytm|gpay|oksbi|okicici|okaxis|okhdfcbank"
    r"|ybl|ibl|axl|apl|juspay|airtel|fbl|kotak|federal|indus|pnb|barodampay"
    r"|waicici|waaxis|wahdfc|wicici|wisbi|utbi|icici|sbi|hdfc|axis|phonepe"
    r"|bhim|razor|amazonpay|freecharge|mobikwik|jiomoney)[a-zA-Z0-9]*",
    re.IGNORECASE,
)

# Telegram links
TELEGRAM_RE = re.compile(
    r"(?:https?://)?t\.me/([\w+]+)",
    re.IGNORECASE,
)

# Instagram handles/links
INSTAGRAM_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/([\w.]+)/?|@([\w.]{3,30})",
    re.IGNORECASE,
)

# WhatsApp links
WHATSAPP_RE = re.compile(
    r"(?:https?://)?(?:chat\.whatsapp\.com|wa\.me)/([\w/\-]+)",
    re.IGNORECASE,
)

# Crypto: Bitcoin, Ethereum, USDT addresses (simplified)
CRYPTO_BTC_RE = re.compile(r"\b(bc1[a-zA-HJ-NP-Z0-9]{25,39}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")
CRYPTO_ETH_RE = re.compile(r"\b0x[a-fA-F0-9]{40}\b")


@dataclass
class ExtractedMetadata:
    mobile_numbers: list = field(default_factory=list)      # raw strings
    emails: list = field(default_factory=list)
    upi_ids: list = field(default_factory=list)
    telegram_links: list = field(default_factory=list)
    instagram_links: list = field(default_factory=list)
    whatsapp_links: list = field(default_factory=list)
    crypto_addresses: list = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any([
            self.mobile_numbers, self.emails, self.upi_ids,
            self.telegram_links, self.instagram_links,
            self.whatsapp_links, self.crypto_addresses,
        ])

    def to_dict(self) -> dict:
        return {
            "mobile_numbers": self.mobile_numbers,
            "emails": self.emails,
            "upi_ids": self.upi_ids,
            "telegram_links": self.telegram_links,
            "instagram_links": self.instagram_links,
            "whatsapp_links": self.whatsapp_links,
            "crypto_addresses": self.crypto_addresses,
        }


def extract_metadata(text: str) -> ExtractedMetadata:
    """Extract all identifiable metadata from a single text string."""
    mobiles = list(dict.fromkeys(MOBILE_RE.findall(text)))
    emails = list(dict.fromkeys(EMAIL_RE.findall(text)))
    upis = list(dict.fromkeys(UPI_RE.findall(text)))
    tg_links = list(dict.fromkeys(TELEGRAM_RE.findall(text)))
    ig_links = list(dict.fromkeys(
        h for h in [
            m[0] or m[1] for m in INSTAGRAM_RE.findall(text)
        ] if h
    ))
    wa_links = list(dict.fromkeys(WHATSAPP_RE.findall(text)))
    crypto = list(dict.fromkeys(
        CRYPTO_BTC_RE.findall(text) + CRYPTO_ETH_RE.findall(text)
    ))

    # UPI IDs that embed mobile numbers -> surface the mobile
    for upi in upis:
        m = re.match(r'^([6-9]\d{9})@', upi)
        if m and m.group(1) not in mobiles:
            mobiles.append(m.group(1))

    return ExtractedMetadata(
        mobile_numbers=mobiles,
        emails=emails,
        upi_ids=upis,
        telegram_links=tg_links,
        instagram_links=ig_links,
        whatsapp_links=wa_links,
        crypto_addresses=crypto,
    )


def aggregate_account_metadata(texts: list, bio: str = "") -> ExtractedMetadata:
    """Extract and deduplicate metadata across all messages + bio for one account."""
    combined = ExtractedMetadata()
    all_texts = [bio] + list(texts)
    for text in all_texts:
        m = extract_metadata(text)
        combined.mobile_numbers = list(dict.fromkeys(combined.mobile_numbers + m.mobile_numbers))
        combined.emails = list(dict.fromkeys(combined.emails + m.emails))
        combined.upi_ids = list(dict.fromkeys(combined.upi_ids + m.upi_ids))
        combined.telegram_links = list(dict.fromkeys(combined.telegram_links + m.telegram_links))
        combined.instagram_links = list(dict.fromkeys(combined.instagram_links + m.instagram_links))
        combined.whatsapp_links = list(dict.fromkeys(combined.whatsapp_links + m.whatsapp_links))
        combined.crypto_addresses = list(dict.fromkeys(combined.crypto_addresses + m.crypto_addresses))
    return combined
