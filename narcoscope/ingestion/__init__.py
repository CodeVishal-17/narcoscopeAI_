"""
Ingestion layer.

Every ingestor returns a list of :class:`RawAccount` objects with the same
shape, regardless of platform, so the rest of the pipeline never needs to know
where the data came from.

Capability boundaries (be honest about these — they are legal/technical, not
laziness):

* ``FileIngestor``      — loads local JSON. Always works. Used for demo + tests.
* ``TelegramIngestor``  — REAL. Official MTProto API (Telethon). Public channels,
                          joined groups, bots. Needs api_id/api_hash.
* ``InstagramIngestor`` — unofficial. Public profiles/captions only, ToS-risky,
                          ban-prone, heavily rate-limited.
* ``WhatsAppIngestor``  — NOT true scraping. Exports messages an investigator's
                          own logged-in account already received from public
                          groups/channels it has joined. No discovery, no
                          reading anything you didn't join. Groups/chats are
                          end-to-end encrypted otherwise.
"""

from .base import RawAccount, RawMessage
from .file_ingestor import FileIngestor

__all__ = ["RawAccount", "RawMessage", "FileIngestor"]
