#!/usr/bin/env python3
"""
CLI entry point for VDR QA Scanner.

This script mirrors the notebook's main execution flow, providing
the same inputs (tracker path, VDR folder, priority terms) and
producing the same outputs (console display + CSV export).

Usage:
    python run_scan.py --tracker path/to/tracker.xlsx --folder path/to/vdr --output results.csv
    
    # With priority terms from a file (one per line):
    python run_scan.py --tracker tracker.xlsx --folder vdr/ --priority-file priority.txt
    
    # With inline priority terms:
    python run_scan.py --tracker tracker.xlsx --folder vdr/ --priority "spirit,airlines,savers"
"""

import argparse
import logging
import sys
import warnings
from pathlib import Path

# Suppress noisy library warnings (matching notebook behavior)
warnings.filterwarnings("ignore")
logging.getLogger("PyPDF2").setLevel(logging.ERROR)

from src.orchestration import load_tracker, scan_vdr_folder
from src.export import flatten_results_to_dataframe, format_summary, export_results_to_csv


def setup_logging(verbose=False):
    """Configure logging to match notebook behavior."""
    logger = logging.getLogger("vdr_qa")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        logger.addHandler(handler)
    return logger


def parse_priority_terms(priority_arg=None, priority_file=None):
    """Parse priority terms from command line or file."""
    terms = []
    
    if priority_arg:
        # Comma-separated inline terms
        terms.extend([t.strip() for t in priority_arg.split(",") if t.strip()])
    
    if priority_file:
        path = Path(priority_file)
        if path.exists():
            with open(path, "r") as f:
                for line in f:
                    term = line.strip()
                    if term and not term.startswith("#"):
                        terms.append(term)
    
    return terms


def display_results(results, total_files):
    """Display results to console, matching notebook output format."""
    if not results:
        print("\n✅ NO ISSUES FOUND! All documents properly anonymized.")
        return
    
    print(f"\n⚠️ FOUND {len(results)} FILES WITH POTENTIAL ISSUES:\n")

    # Pretty-print to console
    for idx, result in enumerate(results, 1):
        print("\n" + "=" * 60)
        print(f"[{idx}] {result['file_name']}")
        print("=" * 60)
        print(f"Path: {result['relative_path']}")
        print(f"Type: {result['file_type']}")
        print("Issues:")
        for term, info in result["found_terms"].items():
            count = info.get("count", 0)
            locations = info.get("locations", [])
            print(f"  • '{term}': {count} occurrence(s)")
            if locations:
                print(f"      Locations: {', '.join(locations)}")


def main():
    parser = argparse.ArgumentParser(
        description="VDR QA Scanner - Scan documents for anonymization issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--tracker", "-t",
        required=True,
        help="Path to the anonymization tracker Excel file"
    )
    parser.add_argument(
        "--folder", "-f",
        required=True,
        help="Path to the VDR folder to scan"
    )
    parser.add_argument(
        "--output", "-o",
        default="vdr_qa_results.csv",
        help="Output CSV file path (default: vdr_qa_results.csv)"
    )
    parser.add_argument(
        "--priority", "-p",
        help="Comma-separated priority terms for prefix matching"
    )
    parser.add_argument(
        "--priority-file",
        help="File containing priority terms (one per line)"
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Disable parallel processing"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=None,
        help="Number of worker threads (default: auto)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    # Validate inputs
    tracker_path = Path(args.tracker)
    if not tracker_path.exists():
        print(f"❌ Tracker file not found: {tracker_path}")
        sys.exit(1)
    
    vdr_folder = Path(args.folder)
    if not vdr_folder.exists():
        print(f"❌ VDR folder not found: {vdr_folder}")
        sys.exit(1)
    
    # Load tracker
    print(f"📂 Loading tracker: {tracker_path}")
    try:
        search_terms, sheet_used = load_tracker(tracker_path)
        print(f"✅ Loaded {len(search_terms)} search terms from sheet: {sheet_used}")
        if args.verbose:
            print(f"   First 10 terms: {search_terms[:10]}")
    except Exception as e:
        print(f"❌ Could not load tracker: {type(e).__name__}: {e}")
        sys.exit(1)
    
    # Parse priority terms
    priority_terms = parse_priority_terms(args.priority, args.priority_file)
    print(f"✅ Priority terms loaded: {len(priority_terms)}")
    if args.verbose and priority_terms:
        print(f"   Priority terms: {priority_terms}")
    
    # Run scan
    print("\n" + "=" * 60)
    print("🚀 STARTING QA SEARCH")
    print("=" * 60)
    print(f"VDR Folder: {vdr_folder.name}")
    print(f"Search terms: {len(search_terms)}")
    print(f"Priority prefix terms: {len(priority_terms)}")
    print("=" * 60)
    
    results, total_files = scan_vdr_folder(
        vdr_folder,
        search_terms,
        priority_terms=priority_terms,
        use_parallel=not args.sequential,
        max_workers=args.workers,
        show_progress=not args.no_progress,
    )
    
    print("\n" + "=" * 60)
    print("✅ SCAN COMPLETE")
    print("=" * 60)
    print(f"Files scanned: {total_files}")
    print(f"Files with issues: {len(results)}")
    print("=" * 60)
    
    # Display results
    display_results(results, total_files)
    
    # Export to CSV
    if results:
        df_export, num_rows = export_results_to_csv(results, args.output)
        
        print("\n" + "=" * 60)
        print(f"💾 Exported {num_rows} term hits to: {args.output}")
        print(f"📂 Location: {Path(args.output).absolute()}")
        print("=" * 60)
        
        # Summary
        summary = format_summary(results, total_files, df_export)
        print("\n📊 Summary")
        print(f"   Files scanned: {summary['files_scanned']}")
        print(f"   Files with issues: {summary['files_with_issues']}")
        print(f"   Total term occurrences: {summary['total_occurrences']}")
        print(f"   Unique terms found: {summary['unique_terms_found']}")


if __name__ == "__main__":
    main()
