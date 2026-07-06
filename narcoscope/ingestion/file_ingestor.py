"""
Loads accounts from a local JSON file (the original ``sample_data.json``
format, and anything the scrapers dump to disk).
"""

from __future__ import annotations

import json
from pathlib import Path

from .base import BaseIngestor, RawAccount


class FileIngestor(BaseIngestor):
    platform = "file"

    def fetch(self, targets: list) -> list:
        """``targets`` is a list of JSON file paths (or a single path)."""
        if isinstance(targets, (str, Path)):
            targets = [targets]
        accounts: list[RawAccount] = []
        for path in targets:
            accounts.extend(self.load(path))
        return accounts

    @staticmethod
    def load(path) -> list:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):          # allow {"accounts": [...]}
            raw = raw.get("accounts", [])
        return [RawAccount.from_dict(a) for a in raw]
