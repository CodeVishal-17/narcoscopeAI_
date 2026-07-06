"""Text processing: normalization, de-obfuscation, and language handling."""

from .normalize import normalize
from .deobfuscate import deobfuscate, obfuscation_score
from .language import detect_language, looks_hinglish
from .metadata import extract_metadata, aggregate_account_metadata, ExtractedMetadata

__all__ = [
    "normalize",
    "deobfuscate",
    "obfuscation_score",
    "detect_language",
    "looks_hinglish",
    "extract_metadata",
    "aggregate_account_metadata",
    "ExtractedMetadata",
]
