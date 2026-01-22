"""Word document parser.

Extracted verbatim from notebook.
"""

import logging

import docx

from ..matchers import update_found_from_text, update_found_from_text_normalized

logger = logging.getLogger("vdr_qa.core.parsers.word")


def search_in_word_doc(file_path, compiled_patterns, match_type=None, normalized_terms=None):
    """Search in Word documents (.docx, .doc), including headers/footers."""
    found = {}
    try:
        doc = docx.Document(file_path)

        def scan_text(text, location_label):
            if not text:
                return
            update_found_from_text(
                found,
                text,
                compiled_patterns,
                location_label=location_label,
                match_type=match_type,
            )
            update_found_from_text_normalized(
                found,
                text,
                normalized_terms,
                location_label=location_label,
                match_type="partial",
            )

        # Body paragraphs
        for p in doc.paragraphs:
            if p.text:
                scan_text(p.text, "BODY")

        # Body tables
        for t_idx, table in enumerate(doc.tables):
            for row in table.rows:
                for cell in row.cells:
                    if cell.text:
                        scan_text(cell.text, f"TABLE {t_idx + 1}")

        # Headers & footers (best-effort, including textboxes via XML)
        seen_part_elements = set()

        def scan_part(part, label):
            elem = getattr(part, "_element", None)
            if elem is None:
                return
            key = id(elem)
            if key in seen_part_elements:
                return
            seen_part_elements.add(key)

            texts = []
            for el in elem.iter():
                if getattr(el, "text", None) and str(getattr(el, "tag", "")).endswith("}t"):
                    texts.append(el.text)
            scan_text(" ".join(texts), label)

        for s_idx, section in enumerate(doc.sections, 1):
            scan_part(section.header, f"HEADER {s_idx}")
            scan_part(section.footer, f"FOOTER {s_idx}")
            scan_part(section.first_page_header, f"FIRST_PAGE_HEADER {s_idx}")
            scan_part(section.first_page_footer, f"FIRST_PAGE_FOOTER {s_idx}")
            scan_part(section.even_page_header, f"EVEN_PAGE_HEADER {s_idx}")
            scan_part(section.even_page_footer, f"EVEN_PAGE_FOOTER {s_idx}")
    except Exception as e:
        logger.warning(f"Failed to process Word doc {file_path}: {type(e).__name__}: {e}")
    return found
