"""
Telegram ingestor — REAL, via the official MTProto API (Telethon).

This is the one platform where "scraping" is legitimate and first-party:
public channels, public groups you join, and bots are readable through
Telegram's own API. You need free API credentials from https://my.telegram.org
(takes ~5 minutes).

Setup:
    pip install telethon
    export TELEGRAM_API_ID=123456
    export TELEGRAM_API_HASH=abcdef0123456789abcdef0123456789

Usage:
    from narcoscope.ingestion.telegram_ingestor import TelegramIngestor
    ing = TelegramIngestor()
    accounts = ing.fetch(["@somepublicchannel", "@another_channel"], limit=200)

Scope & legality: reads only PUBLIC content (or content of channels/groups your
own account has joined). It does NOT and cannot extract phone numbers, IPs, or
private data — that requires lawful process (see project README). Respect
Telegram's ToS and rate limits; Telethon handles flood-wait backoff.
"""

from __future__ import annotations

import os

from .base import BaseIngestor, RawAccount, RawMessage


class TelegramIngestor(BaseIngestor):
    platform = "telegram"

    def __init__(self, api_id: int | None = None, api_hash: str | None = None,
                 session: str | None = None):
        from ..config import TELEGRAM_SESSION
        self.api_id = api_id or os.getenv("TELEGRAM_API_ID")
        self.api_hash = api_hash or os.getenv("TELEGRAM_API_HASH")
        self.session = session or TELEGRAM_SESSION

    def _client(self):
        try:
            from telethon.sync import TelegramClient
        except ImportError as e:
            raise RuntimeError(
                "Telethon is not installed. Run `pip install telethon` and set "
                "TELEGRAM_API_ID / TELEGRAM_API_HASH from https://my.telegram.org"
            ) from e
        if not self.api_id or not self.api_hash:
            raise RuntimeError(
                "Missing Telegram credentials. Set TELEGRAM_API_ID and "
                "TELEGRAM_API_HASH (free from https://my.telegram.org)."
            )
        return TelegramClient(self.session, int(self.api_id), self.api_hash)

    def fetch(self, targets: list, limit: int = 200) -> list:
        """
        ``targets`` is a list of public channel/group usernames or t.me links.
        Returns one :class:`RawAccount` per target with up to ``limit`` messages.
        """
        accounts: list[RawAccount] = []
        with self._client() as client:
            for target in targets:
                accounts.append(self._fetch_one(client, target, limit))
        return accounts

    def _fetch_one(self, client, target: str, limit: int) -> RawAccount:
        entity = client.get_entity(target)
        account_type = "bot" if getattr(entity, "bot", False) else (
            "channel" if getattr(entity, "broadcast", False) else "group"
        )
        handle = f"@{getattr(entity, 'username', None) or target}"

        messages = []
        for msg in client.iter_messages(entity, limit=limit):
            if not msg.message:
                continue
            messages.append(RawMessage(
                text=msg.message,
                timestamp=msg.date.isoformat() if msg.date else None,
                message_id=str(msg.id),
                views=getattr(msg, "views", None),
            ))

        return RawAccount(
            account_id=f"tg_{getattr(entity, 'id', target)}",
            platform="telegram",
            handle=handle,
            account_type=account_type,
            bio=getattr(entity, "about", "") or "",
            messages=messages,
            source="telegram_live",
        )
