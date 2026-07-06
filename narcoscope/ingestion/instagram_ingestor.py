"""
Instagram ingestor — UNOFFICIAL and best-effort (via instaloader).

⚠️ Honesty first: there is NO official API that returns arbitrary accounts'
content. This uses instaloader to read PUBLIC profile bios and post captions for
handles you specify. It:
  * violates Instagram's Terms of Service,
  * is aggressively rate-limited and will get IPs / burner logins banned,
  * breaks whenever Instagram changes its private endpoints.

Use it only for authorized investigation on public data, sparingly, with long
delays. For anything production or legally sensitive, prefer manual analyst
review over automated scraping.

Setup:
    pip install instaloader

Usage:
    from narcoscope.ingestion.instagram_ingestor import InstagramIngestor
    ing = InstagramIngestor()
    accounts = ing.fetch(["somehandle"], max_posts=20)
"""

from __future__ import annotations

import time

from .base import BaseIngestor, RawAccount, RawMessage


class InstagramIngestor(BaseIngestor):
    platform = "instagram"

    def __init__(self, throttle_seconds: float = 6.0):
        # Deliberately slow — hammering Instagram gets you banned fast.
        self.throttle = throttle_seconds

    def _loader(self):
        try:
            import instaloader
        except ImportError as e:
            raise RuntimeError(
                "instaloader is not installed. Run `pip install instaloader`. "
                "Note: Instagram scraping violates ToS and is ban-prone — use "
                "only for authorized public-data investigation."
            ) from e
        return instaloader.Instaloader(
            download_pictures=False, download_videos=False,
            download_comments=False, save_metadata=False, quiet=True,
        )

    def fetch(self, targets: list, max_posts: int = 20) -> list:
        """``targets`` = list of public Instagram usernames (no '@')."""
        import instaloader
        loader = self._loader()
        accounts: list[RawAccount] = []

        for username in targets:
            username = username.lstrip("@")
            try:
                profile = instaloader.Profile.from_username(loader.context, username)
            except Exception as e:
                accounts.append(RawAccount(
                    account_id=f"ig_{username}", platform="instagram",
                    handle=f"@{username}", account_type="profile",
                    bio=f"[fetch failed: {e}]", source="instagram_live",
                ))
                continue

            messages = []
            if profile.biography:
                messages.append(RawMessage(text=profile.biography, message_id="bio"))

            count = 0
            for post in profile.get_posts():
                if count >= max_posts:
                    break
                if post.caption:
                    messages.append(RawMessage(
                        text=post.caption,
                        timestamp=post.date_utc.isoformat() if post.date_utc else None,
                        message_id=post.shortcode,
                    ))
                count += 1
                time.sleep(self.throttle)   # be gentle or get banned

            accounts.append(RawAccount(
                account_id=f"ig_{profile.userid}", platform="instagram",
                handle=f"@{username}", account_type="profile",
                bio=profile.biography or "", messages=messages,
                source="instagram_live",
            ))
        return accounts
