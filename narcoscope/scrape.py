"""
Unified scraper CLI — pulls real data into the pipeline's account JSON format.

Examples:
    # Telegram (real, needs TELEGRAM_API_ID / TELEGRAM_API_HASH):
    python -m narcoscope.scrape telegram @channel1 @channel2 -o data/scraped_tg.json

    # Instagram (unofficial, ToS-risky, slow):
    python -m narcoscope.scrape instagram somehandle -o data/scraped_ig.json

    # WhatsApp (join-then-export only — pass an exported chat .txt):
    python -m narcoscope.scrape whatsapp "exports/Some Group.txt" -o data/scraped_wa.json

The output JSON drops straight into the pipeline:
    python -m narcoscope.pipeline data/scraped_tg.json
"""

from __future__ import annotations

import argparse
import json


def _dump(accounts, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump([a.to_dict() for a in accounts], f, indent=2, ensure_ascii=False)
    total = sum(len(a.messages) for a in accounts)
    print(f"Wrote {len(accounts)} accounts / {total} messages -> {path}")


def main():
    ap = argparse.ArgumentParser(description="Scrape real data for NarcoScope.")
    ap.add_argument("platform", choices=["telegram", "instagram", "whatsapp"])
    ap.add_argument("targets", nargs="+", help="channels / handles / export paths")
    ap.add_argument("-o", "--output", default="data/scraped.json")
    ap.add_argument("--limit", type=int, default=200, help="messages/posts per target")
    args = ap.parse_args()

    if args.platform == "telegram":
        from .ingestion.telegram_ingestor import TelegramIngestor
        accounts = TelegramIngestor().fetch(args.targets, limit=args.limit)
    elif args.platform == "instagram":
        from .ingestion.instagram_ingestor import InstagramIngestor
        accounts = InstagramIngestor().fetch(args.targets, max_posts=args.limit)
    else:
        from .ingestion.whatsapp_ingestor import WhatsAppIngestor
        accounts = WhatsAppIngestor().fetch(args.targets)

    _dump(accounts, args.output)


if __name__ == "__main__":
    main()
