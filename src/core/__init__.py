"""Core logic for pattern matching and text extraction."""

from .patterns import build_compiled_patterns, normalize_for_match
from .matchers import update_found_from_text, update_found_from_text_normalized

__all__ = [
    "build_compiled_patterns",
    "normalize_for_match",
    "update_found_from_text",
    "update_found_from_text_normalized",
]
