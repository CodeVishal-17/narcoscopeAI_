"""
NarcoScope AI — cross-platform narcotics-sale detection pipeline.

This package upgrades the original single-file rule engine into a real,
staged pipeline:

    ingest -> process -> engineer features -> classify (rules -> ML -> LLM)
           -> correlate accounts -> report

Everything is runnable offline on synthetic data. The live scrapers
(Telegram / Instagram / WhatsApp) are real but require your own credentials
and are honest about each platform's legal/technical limits — see
``narcoscope/ingestion/``.
"""

__version__ = "0.2.0"
