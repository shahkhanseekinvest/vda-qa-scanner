"""Tracker file loading utilities.

Extracted verbatim from notebook.
"""

import logging

import pandas as pd

logger = logging.getLogger("vdr_qa.orchestration.tracker_loader")


def load_tracker(path):
    """
    Load anonymization tracker Excel file.
    
    Searches all sheets for a column named "Before" (case-insensitive)
    and returns the unique values from that column.
    
    Args:
        path: Path to the Excel file
        
    Returns:
        tuple: (list of search terms, sheet name used)
        
    Raises:
        ValueError: If no sheet with a 'Before' column is found
    """
    xls = pd.ExcelFile(path)
    logger.info(f"Sheets found: {', '.join(xls.sheet_names)}")

    for name in xls.sheet_names:
        df = xls.parse(name)
        lower_cols = {c.lower(): c for c in df.columns}
        if "before" in lower_cols:
            col_name = lower_cols["before"]
            terms = df[col_name].dropna().unique().tolist()
            logger.info(f"Loaded {len(terms)} search terms from sheet: {name}")
            return terms, name

    raise ValueError("No sheet with a 'Before' column found. Please check the file.")
