"""Main VDR folder scanning logic.

Extracted verbatim from notebook.
"""

import os
import re
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm.auto import tqdm

from ..core.patterns import build_compiled_patterns, normalize_for_match
from ..core.matchers import update_found_from_text, update_found_from_text_normalized
from ..core.parsers import (
    search_in_pdf,
    search_in_word_doc,
    search_in_excel,
    search_in_csv,
    search_in_powerpoint,
    search_in_text_file,
)

logger = logging.getLogger("vdr_qa.orchestration.scanner")


def get_search_function(file_path):
    """Route to correct search function based on file extension."""
    ext = Path(file_path).suffix.lower()

    # Legacy format warning
    if ext in [".doc", ".xls", ".ppt"]:
        logger.warning(
            f"Legacy format {ext} may not be fully supported for {file_path}. "
            f"Convert to a modern format (.docx/.xlsx/.pptx) for best results."
        )

    mapping = {
        ".pdf": search_in_pdf,
        ".docx": search_in_word_doc,
        ".doc": search_in_word_doc,
        ".xlsx": search_in_excel,
        ".xls": search_in_excel,
        ".pptx": search_in_powerpoint,
        ".ppt": search_in_powerpoint,
        ".csv": search_in_csv,
        ".txt": search_in_text_file,
    }

    return mapping.get(ext, None)


def scan_vdr_folder(vdr_path, search_terms, priority_terms=None, exclude_folders=None, use_parallel=True, max_workers=None, show_progress=True):
    """
    Recursively scan VDR folder for search terms.

    - Precompiles regex patterns once.
    - Scans filenames and file content.
    - Uses thread pool for parallelism by default (safe in notebooks).
    
    Args:
        vdr_path: Path to the VDR folder to scan
        search_terms: List of terms to search for (exact match)
        priority_terms: List of priority terms (prefix match)
        exclude_folders: Set of folder names to exclude
        use_parallel: Whether to use parallel processing
        max_workers: Maximum number of worker threads
        show_progress: Whether to show tqdm progress bar
        
    Returns:
        tuple: (list of result dicts, total files scanned)
    """
    vdr_path = Path(vdr_path)

    if exclude_folders is None:
        exclude_folders = {".git", "__pycache__", "node_modules", ".venv", "venv"}

    exact_patterns = build_compiled_patterns(search_terms, mode="exact")
    priority_patterns = build_compiled_patterns(priority_terms or [], mode="priority_prefix") if priority_terms else {}
    normalized_terms = {t: normalize_for_match(t) for t in (search_terms or []) if isinstance(t, str) and re.search(r"[^0-9A-Za-z]", t) and normalize_for_match(t)}
    normalized_priority_terms = {t: normalize_for_match(t) for t in (priority_terms or []) if isinstance(t, str) and re.search(r"[^0-9A-Za-z]", t) and normalize_for_match(t)}

    if not exact_patterns and not priority_patterns:
        logger.warning("No valid patterns compiled (exact or priority).")
        return [], 0

    # Discover files
    all_files = []
    for root, dirs, files in os.walk(vdr_path):
        dirs[:] = [d for d in dirs if d not in exclude_folders]
        for name in files:
            file_path = Path(root) / name
            if get_search_function(file_path) is not None:
                all_files.append(file_path)

    logger.info(f"Discovered {len(all_files)} files to scan.")

    def process_file(file_path: Path):
        found_terms = {}

        # 1) Filename scan (exact + priority prefix)
        if exact_patterns:
            update_found_from_text(found_terms, file_path.name, exact_patterns, location_label="FILENAME", match_type="exact")
        if priority_patterns:
            update_found_from_text(found_terms, file_path.name, priority_patterns, location_label="FILENAME", match_type="partial")
        if normalized_terms:
            update_found_from_text_normalized(found_terms, file_path.name, normalized_terms, location_label="FILENAME", match_type="partial")
        if normalized_priority_terms:
            update_found_from_text_normalized(found_terms, file_path.name, normalized_priority_terms, location_label="FILENAME", match_type="partial")

        # 2) Content scan (exact + priority prefix)
        search_fn = get_search_function(file_path)
        if search_fn is not None:
            content_found = {}
            for patterns, match_type, norm_terms in ((exact_patterns, "exact", normalized_terms), (priority_patterns, "partial", normalized_priority_terms)):
                if not patterns:
                    continue
                part_found = search_fn(file_path, patterns, match_type=match_type, normalized_terms=norm_terms)
                for term, info in part_found.items():
                    merged = content_found.setdefault(term, {"count": 0, "locations": [], "term_flagged": [], "match_type": []})
                    merged["count"] += info.get("count", 0)
                    for loc in info.get("locations", []):
                        if loc not in merged["locations"]:
                            merged["locations"].append(loc)
                    for flagged in info.get("term_flagged", []):
                        if flagged not in merged["term_flagged"]:
                            merged["term_flagged"].append(flagged)
                    for mt in info.get("match_type", []):
                        if mt not in merged["match_type"]:
                            merged["match_type"].append(mt)

            for term, info in content_found.items():
                entry = found_terms.setdefault(term, {"count": 0, "locations": [], "term_flagged": [], "match_type": []})
                entry["count"] += info.get("count", 0)
                for loc in info.get("locations", []):
                    if loc not in entry["locations"]:
                        entry["locations"].append(loc)
                for flagged in info.get("term_flagged", []):
                    if flagged not in entry["term_flagged"]:
                        entry["term_flagged"].append(flagged)
                for mt in info.get("match_type", []):
                    if mt not in entry["match_type"]:
                        entry["match_type"].append(mt)

        if not found_terms:
            return None

        try:
            rel_path = file_path.relative_to(vdr_path)
        except ValueError:
            rel_path = file_path

        return {
            "file_name": file_path.name,
            "file_path": str(file_path.absolute()),
            "relative_path": str(rel_path),
            "file_type": file_path.suffix[1:].lower(),  # strip dot
            "found_terms": found_terms,
        }

    results = []

    if use_parallel and all_files:
        max_workers = max_workers or min(8, os.cpu_count() or 4)
        logger.info(f"Scanning with ThreadPoolExecutor, max_workers={max_workers} ...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_file, fp): fp for fp in all_files}
            iterator = as_completed(futures)
            if show_progress:
                iterator = tqdm(iterator, total=len(futures), desc="Scanning files")
            for future in iterator:
                res = future.result()
                if res:
                    results.append(res)
    else:
        logger.info("Scanning sequentially ...")
        iterator = all_files
        if show_progress:
            iterator = tqdm(iterator, desc="Scanning files")
        for fp in iterator:
            res = process_file(fp)
            if res:
                results.append(res)

    return results, len(all_files)
