"""
One-time interactive Telegram login.

Telethon's first login is interactive — Telegram sends a code to your app/SMS,
and you may have a 2FA password. That handshake can only happen in YOUR
terminal, not inside a web request, so run this once:

    # 1. get free credentials from https://my.telegram.org  (API development tools)
    set TELEGRAM_API_ID=123456                 (PowerShell: $env:TELEGRAM_API_ID=...)
    set TELEGRAM_API_HASH=abcdef0123456789abcdef0123456789
    python login_telegram.py

It creates telegram.session at the repo root. After that, the Django backend
(and the CLI scraper) authenticate headlessly using that file — no more prompts.
"""

import os
import sys

from narcoscope.config import TELEGRAM_SESSION


def main():
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    if not api_id or not api_hash:
        print("Set TELEGRAM_API_ID and TELEGRAM_API_HASH first "
              "(free from https://my.telegram.org).")
        sys.exit(1)

    try:
        from telethon.sync import TelegramClient
    except ImportError:
        print("Telethon missing. Run: pip install telethon")
        sys.exit(1)

    print("Starting Telegram login (you'll be prompted for phone + code)...")
    with TelegramClient(TELEGRAM_SESSION, int(api_id), api_hash) as client:
        me = client.get_me()
        who = me.username or me.first_name or str(me.id)
        print(f"\n✅ Logged in as {who}.")
        print(f"Session saved: {TELEGRAM_SESSION}.session")
        print("You can now scrape headlessly from the app or CLI:")
        print("   python -m narcoscope.scrape telegram @somechannel -o data/tg.json")


if __name__ == "__main__":
    main()
