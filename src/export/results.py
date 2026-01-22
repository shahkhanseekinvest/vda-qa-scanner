"""Results formatting and export utilities.

Extracted verbatim from notebook's display/export cell.
"""

import pandas as pd


def flatten_results_to_dataframe(results):
    """
    Flatten hierarchical results into a flat DataFrame suitable for CSV export.
    
    This matches the exact export format from the notebook.
    
    Args:
        results: List of result dicts from scan_vdr_folder
        
    Returns:
        pandas.DataFrame with columns:
            file_name, relative_path, file_type, anon_term,
            term_flagged, match_type, count, locations
    """
    export_rows = []
    for result in results:
        for term, info in result["found_terms"].items():
            export_rows.append(
                {
                    "file_name": result["file_name"],
                    "relative_path": result["relative_path"],
                    "file_type": result["file_type"],
                    "anon_term": term,
                    "term_flagged": "; ".join(info.get("term_flagged", [])),
                    "match_type": "partial" if "partial" in info.get("match_type", []) else "exact",
                    "count": info.get("count", 0),
                    "locations": "; ".join(info.get("locations", [])),
                }
            )
    return pd.DataFrame(export_rows)


def format_summary(results, total_files, df_export=None):
    """
    Generate summary statistics matching the notebook output.
    
    Args:
        results: List of result dicts from scan_vdr_folder
        total_files: Total number of files scanned
        df_export: Optional DataFrame from flatten_results_to_dataframe
        
    Returns:
        dict with summary statistics
    """
    if df_export is None:
        df_export = flatten_results_to_dataframe(results)
    
    total_occurrences = df_export["count"].sum() if len(df_export) > 0 else 0
    unique_terms = sorted(df_export["anon_term"].unique().tolist()) if len(df_export) > 0 else []
    
    return {
        "files_scanned": total_files,
        "files_with_issues": len(results),
        "total_occurrences": int(total_occurrences),
        "unique_terms_found": len(unique_terms),
        "unique_terms": unique_terms,
    }


def export_results_to_csv(results, output_path):
    """
    Export results to CSV file.
    
    Args:
        results: List of result dicts from scan_vdr_folder
        output_path: Path for the output CSV file
        
    Returns:
        tuple: (DataFrame, number of rows exported)
    """
    df_export = flatten_results_to_dataframe(results)
    df_export.to_csv(output_path, index=False)
    return df_export, len(df_export)
