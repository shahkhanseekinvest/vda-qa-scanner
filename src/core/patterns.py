"""Pattern compilation and normalization utilities.

This module contains functions for building compiled regex patterns
and normalizing text for matching. Extracted verbatim from notebook.
"""

import re
import logging

logger = logging.getLogger("vdr_qa.core.patterns")


def build_compiled_patterns(terms, mode="exact"):
    """
    Build compiled regex patterns.

    mode:
      - exact: whole-token match using non-alphanumeric boundaries
      - priority_prefix: token starts with term and has at least 1 extra token char
        Example: term 'Planet' flags 'PlanetFitness' but NOT 'MyPlanetFitness' or 'Planet'
    """
    patterns = {}
    for term in terms:
        if not isinstance(term, str):
            continue
        t = term.strip()
        if not t:
            continue

        if mode == "exact":
            pattern_str = r"(?<![0-9a-zA-Z])" + re.escape(t) + r"(?![0-9a-zA-Z])"
        elif mode == "priority_prefix":
            pattern_str = r"(?<![0-9a-zA-Z])" + re.escape(t) + r"[0-9a-zA-Z_]+"
        else:
            raise ValueError(f"Unknown mode: {mode}")

        patterns[t] = re.compile(pattern_str, flags=re.IGNORECASE)

    logger.info(f"Compiled {len(patterns)} patterns (mode={mode}).")
    return patterns


def normalize_for_match(value: str) -> str:
    """Lowercase and drop all non-alphanumerics (A-Z, a-z, 0-9).
    
    Note: This was named _normalize_for_match in the notebook.
    Renamed to remove leading underscore for public API.
    """
    if not value:
        return ""
    return re.sub(r"[^0-9a-zA-Z]+", "", value).lower()
