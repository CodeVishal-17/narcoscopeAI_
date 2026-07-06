"""
WhatsApp ingestor — NOT true scraping. "Join-then-export" only.

⚠️ Read this before expecting more than it does:
  * Regular WhatsApp chats and groups are END-TO-END ENCRYPTED. There is no API
    to read messages your account did not receive. You cannot enumerate or
    discover groups/channels.
  * The only defensible workflow is: an investigator's OWN account joins a
    public group / channel, and this tool exports what that account legitimately
    received. That's it — no discovery, no reading anything you didn't join.

Two supported input paths (pick whichever fits your setup):

1. **Chat export file** (simplest, no automation): in WhatsApp, open the group
   → "Export chat" (without media) → you get a .txt. Point this ingestor at it.
       ing = WhatsAppIngestor()
       accounts = ing.fetch(["exports/Weekend Vibes Group.txt"])

2. **Live session bridge** (advanced): drive your own logged-in WhatsApp Web
   session via a Node.js library (Baileys / whatsapp-web.js) that dumps received
   messages to JSON, then load that JSON. That automation lives OUTSIDE Python
   (see README "WhatsApp bridge"); this class just ingests its JSON output.
   Automating your own number risks a ban — that is a WhatsApp ToS consequence,
   not a bug here.
"""

from __future__ import annotations

import json
import os
import re

from .base import BaseIngestor, RawAccount, RawMessage

# Matches the standard WhatsApp export line:
#   "12/07/24, 9:41 PM - Sender Name: message text"
# (formats vary slightly by locale/version; this covers the common ones).
_EXPORT_LINE = re.compile(
    r"^\[?(\d{1,2}[/.]\d{1,2}[/.]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s?(?:[AaPp][Mm])?)\]?"
    r"\s*[-–]\s*(?:([^:]{1,60}):\s*)?(.*)$"
)


class WhatsAppIngestor(BaseIngestor):
    platform = "whatsapp"

    def fetch(self, targets: list) -> list:
        """
        ``targets`` = list of paths. ``.txt`` files are parsed as WhatsApp chat
        exports; ``.json`` files are treated as output from the live-session
        bridge (a list of {handle, messages:[{text, timestamp}]} groups).
        """
        accounts: list[RawAccount] = []
        for path in targets:
            if str(path).lower().endswith(".json"):
                accounts.extend(self._from_bridge_json(path))
            else:
                accounts.append(self._from_export_txt(path))
        return accounts

    @staticmethod
    def _from_export_txt(path) -> RawAccount:
        name = os.path.splitext(os.path.basename(path))[0]
        messages = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = _EXPORT_LINE.match(line.rstrip("\n"))
                if not m:
                    # continuation of a multi-line message — append to previous
                    if messages and line.strip():
                        messages[-1].text += "\n" + line.rstrip("\n")
                    continue
                ts, _sender, body = m.groups()
                if body and not body.startswith("‎"):  # skip system notices
                    messages.append(RawMessage(text=body, timestamp=ts))
        return RawAccount(
            account_id=f"wa_{abs(hash(name)) % 10**8}",
            platform="whatsapp", handle=name, account_type="group",
            messages=messages, source="whatsapp_export",
        )

    @staticmethod
    def _from_bridge_json(path) -> list:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        groups = data if isinstance(data, list) else data.get("groups", [])
        out = []
        for g in groups:
            msgs = [
                RawMessage(text=m["text"], timestamp=m.get("timestamp"))
                for m in g.get("messages", []) if m.get("text")
            ]
            out.append(RawAccount(
                account_id=g.get("account_id", f"wa_{abs(hash(g.get('handle',''))) % 10**8}"),
                platform="whatsapp", handle=g.get("handle", "unknown group"),
                account_type=g.get("account_type", "group"),
                messages=msgs, source="whatsapp_bridge",
            ))
        return out
