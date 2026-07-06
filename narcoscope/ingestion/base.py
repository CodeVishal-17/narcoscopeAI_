"""
Common data schema shared by every ingestor and the rest of the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class RawMessage:
    text: str
    timestamp: Optional[str] = None          # ISO-8601 string if known
    message_id: Optional[str] = None
    views: Optional[int] = None              # e.g. Telegram channel post views

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RawAccount:
    account_id: str
    platform: str                            # telegram | instagram | whatsapp
    handle: str
    account_type: str = "profile"            # channel | group | bot | profile
    bio: str = ""
    payment_handles: list = field(default_factory=list)
    external_links: list = field(default_factory=list)
    messages: list = field(default_factory=list)   # list[RawMessage]
    source: str = "file"                     # which ingestor produced this

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "RawAccount":
        msgs = [
            RawMessage(**m) if isinstance(m, dict) else RawMessage(text=str(m))
            for m in d.get("messages", [])
        ]
        return cls(
            account_id=d["account_id"],
            platform=d.get("platform", "unknown"),
            handle=d.get("handle", d["account_id"]),
            account_type=d.get("account_type", "profile"),
            bio=d.get("bio", ""),
            payment_handles=list(d.get("payment_handles", [])),
            external_links=list(d.get("external_links", [])),
            messages=msgs,
            source=d.get("source", "file"),
        )


class BaseIngestor:
    """Interface every platform ingestor implements."""

    platform: str = "unknown"

    def fetch(self, targets: list) -> list:
        """Return ``list[RawAccount]`` for the given target identifiers."""
        raise NotImplementedError
