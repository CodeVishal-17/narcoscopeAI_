"""
Pass 3 — LLM adjudication for ambiguous messages.

Only messages the ML stage is unsure about (probability in the escalation band)
reach this stage, so cost stays bounded. Uses Claude via the official
``anthropic`` SDK to classify slang / Hinglish / novel phrasing the rules and
the ML model may miss.

Model choice: Claude Haiku 4.5 (``claude-haiku-4-5``) — this is a high-volume,
latency- and cost-sensitive binary classification, exactly Haiku's niche. Set
``NARCOSCOPE_LLM_MODEL`` to override (e.g. a larger model for a spot audit).

Enable by setting env ``NARCOSCOPE_LLM=1`` and providing ``ANTHROPIC_API_KEY``.
If the SDK is missing or no key is configured, this stage disables itself and
the hybrid pipeline falls back to the ML probability — nothing crashes.
"""

from __future__ import annotations

import json
import re

from ..config import LLM_ENABLED, LLM_MODEL, ANTHROPIC_API_KEY

_SYSTEM = (
    "You are a content-safety classifier assisting a lawful, analyst-reviewed "
    "investigation into narcotics sales on Indian social platforms (Telegram, "
    "WhatsApp, Instagram). Decide whether a single public message is advertising "
    "or arranging the SALE of illegal drugs. Consider Hindi/Hinglish slang, coded "
    "emoji, and obfuscation. Benign mentions (news, recovery, harm-reduction, "
    "jokes) are NOT sales. Respond ONLY with a compact JSON object: "
    '{"label": 0 or 1, "confidence": 0.0-1.0, "reason": "<short>"}. '
    "label 1 = likely drug-sale, 0 = not."
)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMClassifier:
    """Thin wrapper around the Anthropic Messages API. Safe to construct always."""

    def __init__(self, enabled: bool | None = None, model: str | None = None):
        self.model = model or LLM_MODEL
        self._client = None
        self.enabled = LLM_ENABLED if enabled is None else enabled
        if self.enabled:
            self._client = self._make_client()
            self.enabled = self._client is not None

    @staticmethod
    def _make_client():
        if not ANTHROPIC_API_KEY:
            return None
        try:
            import anthropic
        except ImportError:
            return None
        try:
            return anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        except Exception:
            return None

    def classify(self, text: str) -> dict | None:
        """
        Return ``{"label": int, "confidence": float, "reason": str}`` or None if
        the stage is disabled or the call fails (caller then keeps the ML score).
        """
        if not self.enabled or self._client is None:
            return None
        try:
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=256,
                system=_SYSTEM,
                messages=[{"role": "user", "content": f"Message: {text!r}"}],
            )
        except Exception:
            return None

        blob = next((b.text for b in resp.content if b.type == "text"), "")
        return self._parse(blob)

    @staticmethod
    def _parse(blob: str) -> dict | None:
        m = _JSON_RE.search(blob or "")
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
        try:
            return {
                "label": int(data.get("label", 0)),
                "confidence": float(data.get("confidence", 0.5)),
                "reason": str(data.get("reason", ""))[:200],
            }
        except (TypeError, ValueError):
            return None
