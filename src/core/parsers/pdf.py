"""PDF file parser.

Extracted verbatim from notebook.
"""

import logging

import PyPDF2

from ..matchers import update_found_from_text, update_found_from_text_normalized

logger = logging.getLogger("vdr_qa.core.parsers.pdf")


def search_in_pdf(file_path, compiled_patterns, match_type=None, normalized_terms=None):
    """Search in PDF files page by page."""
    found = {}
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page_idx, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                except Exception as e_page:
                    logger.warning(
                        f"Failed to extract page {page_idx + 1} from {file_path}: "
                        f"{type(e_page).__name__}: {e_page}"
                    )
                    continue

                if text.strip():
                    update_found_from_text(
                        found,
                        text,
                        compiled_patterns,
                        location_label=f"PAGE {page_idx + 1}",
                        match_type=match_type,
                    )
                    update_found_from_text_normalized(
                        found,
                        text,
                        normalized_terms,
                        location_label=f"PAGE {page_idx + 1}",
                        match_type="partial",
                    )
    except Exception as e:
        logger.warning(f"Failed to process PDF {file_path}: {type(e).__name__}: {e}")
    return found
