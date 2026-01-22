"""CSV file parser.

Extracted verbatim from notebook.
Note: Named csv_parser.py to avoid conflict with stdlib csv module.
"""

import logging

import pandas as pd

from ..matchers import update_found_from_text, update_found_from_text_normalized

logger = logging.getLogger("vdr_qa.core.parsers.csv_parser")


def search_in_csv(file_path, compiled_patterns, match_type=None, normalized_terms=None):
    """Search in CSV files via pandas."""
    found = {}
    try:
        df = pd.read_csv(file_path, dtype=str, encoding_errors="ignore")
        text = " ".join(df.astype(str).fillna("").values.ravel().tolist())
        update_found_from_text(found, text, compiled_patterns, location_label="CONTENT", match_type=match_type)
        update_found_from_text_normalized(found, text, normalized_terms, location_label="CONTENT", match_type="partial")
    except Exception as e:
        logger.warning(f"Failed to process CSV file {file_path}: {type(e).__name__}: {e}")
    return found
