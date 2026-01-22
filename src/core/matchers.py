"""Text matching utilities.

This module contains functions for finding pattern matches in text
and accumulating results. Extracted verbatim from notebook.
"""

import re


def update_found_from_text(found, text, compiled_patterns, location_label=None, match_type=None):
    """
    Update `found` dict with matches from `text` for all compiled patterns.

    found structure:
      {
        term: {
          "count": int,
          "locations": [str, ...],
          "term_flagged": [str, ...],
          "match_type": ["exact"|"partial", ...]
        },
        ...
      }
    
    Note: This was named _update_found_from_text in the notebook.
    Renamed to remove leading underscore for public API.
    """
    if not text:
        return

    for term, pattern in compiled_patterns.items():
        matches = pattern.findall(text)
        if matches:
            entry = found.setdefault(term, {"count": 0, "locations": [], "term_flagged": [], "match_type": []})
            entry["count"] += len(matches)
            for m in matches:
                if m not in entry["term_flagged"]:
                    entry["term_flagged"].append(m)
            if match_type and match_type not in entry["match_type"]:
                entry["match_type"].append(match_type)
            if location_label and location_label not in entry["locations"]:
                entry["locations"].append(location_label)


def update_found_from_text_normalized(found, text, normalized_terms, location_label=None, match_type="partial"):
    """Token-level normalized scan: token_norm.startswith(term_norm).
    
    Note: This was named _update_found_from_text_normalized in the notebook.
    Renamed to remove leading underscore for public API.
    """
    if not text or not normalized_terms:
        return

    # Tokenize from original text to keep token boundaries.
    tokens = [m.group(0) for m in re.finditer(r"[0-9A-Za-z]+", text)]
    if not tokens:
        return

    for token in tokens:
        token_norm = token.lower()
        for term, term_norm in normalized_terms.items():
            if not term_norm:
                continue
            if token_norm.startswith(term_norm):
                entry = found.setdefault(term, {"count": 0, "locations": [], "term_flagged": [], "match_type": []})
                entry["count"] += 1
                if token not in entry["term_flagged"]:
                    entry["term_flagged"].append(token)
                if match_type and match_type not in entry["match_type"]:
                    entry["match_type"].append(match_type)
                if location_label and location_label not in entry["locations"]:
                    entry["locations"].append(location_label)
