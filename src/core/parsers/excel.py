"""Excel file parser.

Extracted verbatim from notebook.
"""

import logging

import pandas as pd

from ..matchers import update_found_from_text, update_found_from_text_normalized

logger = logging.getLogger("vdr_qa.core.parsers.excel")


def search_in_excel(file_path, compiled_patterns, match_type=None, normalized_terms=None):
    """Search in Excel files (.xlsx, .xls) using only string-like columns."""
    found = {}
    try:
        df_dict = pd.read_excel(file_path, sheet_name=None)
        for sheet_name, df in df_dict.items():
            # Only string/object columns
            obj_cols = df.select_dtypes(include=["object"]).columns
            if not len(obj_cols):
                continue

            # Flatten object columns into a single string
            try:
                sub = df[obj_cols].astype(str).fillna("")
                sheet_text = " ".join(sub.values.ravel().tolist())
            except Exception as e_sheet:
                logger.warning(
                    f"Failed to build text for sheet {sheet_name} "
                    f"in {file_path}: {type(e_sheet).__name__}: {e_sheet}"
                )
                continue

            if not sheet_text.strip():
                continue

            update_found_from_text(found, sheet_text, compiled_patterns, location_label=sheet_name, match_type=match_type)
            update_found_from_text_normalized(found, sheet_text, normalized_terms, location_label=sheet_name, match_type="partial")
    except Exception as e:
        logger.warning(f"Failed to process Excel file {file_path}: {type(e).__name__}: {e}")
    return found
