"""Text file parser.

Extracted verbatim from notebook.
"""

import logging

from ..matchers import update_found_from_text, update_found_from_text_normalized

logger = logging.getLogger("vdr_qa.core.parsers.text")


def search_in_text_file(file_path, compiled_patterns, match_type=None, normalized_terms=None, chunk_size=1024 * 1024):
    """Search in .txt files using chunked reading."""
    found = {}
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                update_found_from_text(found, chunk, compiled_patterns, location_label="CONTENT", match_type=match_type)
                update_found_from_text_normalized(found, chunk, normalized_terms, location_label="CONTENT", match_type="partial")
    except Exception as e:
        logger.warning(f"Failed to process text file {file_path}: {type(e).__name__}: {e}")
    return found
