"""PowerPoint file parser.

Extracted verbatim from notebook.
"""

import logging

from pptx import Presentation

from ..matchers import update_found_from_text, update_found_from_text_normalized

logger = logging.getLogger("vdr_qa.core.parsers.powerpoint")


def search_in_powerpoint(file_path, compiled_patterns, match_type=None, normalized_terms=None):
    """Search in PowerPoint files (.pptx, .ppt), including layout/master and notes."""
    found = {}
    try:
        prs = Presentation(file_path)

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

        def scan_shapes(shapes, location_label):
            for shape in shapes:
                try:
                    if hasattr(shape, "text") and shape.text:
                        scan_text(shape.text, location_label)

                    if hasattr(shape, "has_table") and shape.has_table:
                        table = shape.table
                        for row in table.rows:
                            for cell in row.cells:
                                if cell.text:
                                    scan_text(cell.text, f"{location_label} TABLE")
                except Exception as e_shape:
                    logger.debug(
                        f"Shape parse issue in {file_path} at {location_label}: "
                        f"{type(e_shape).__name__}: {e_shape}"
                    )

        scanned_layouts = set()
        scanned_masters = set()

        for slide_idx, slide in enumerate(prs.slides):
            slide_label = f"SLIDE {slide_idx + 1}"

            # Slide shapes
            scan_shapes(slide.shapes, slide_label)

            # Speaker notes
            try:
                if getattr(slide, "has_notes_slide", False) and slide.notes_slide:
                    scan_shapes(slide.notes_slide.shapes, f"{slide_label} NOTES")
            except Exception:
                pass

            # Layout & master shapes: dedupe across slides for speed
            try:
                layout = slide.slide_layout
                layout_key = str(layout.part.partname)
                if layout_key not in scanned_layouts:
                    scanned_layouts.add(layout_key)
                    scan_shapes(layout.shapes, f"LAYOUT {layout_key}")
            except Exception:
                pass
            try:
                master = slide.slide_master
                master_key = str(master.part.partname)
                if master_key not in scanned_masters:
                    scanned_masters.add(master_key)
                    scan_shapes(master.shapes, f"MASTER {master_key}")
            except Exception:
                pass
    except Exception as e:
        logger.warning(
            f"Failed to process PowerPoint file {file_path}: {type(e).__name__}: {e}"
        )
    return found
