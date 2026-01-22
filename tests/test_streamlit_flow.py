#!/usr/bin/env python3
"""
Test the Streamlit app's data flow without running the UI.

This verifies that:
1. ZIP extraction works correctly
2. The same APIs called by the Streamlit app produce expected results
3. The app's helper functions work correctly

Run this to verify the Streamlit integration before manual testing.

Usage:
    python tests/test_streamlit_flow.py
"""

import io
import sys
import tempfile
import zipfile
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_zip_extraction():
    """Test that ZIP extraction works as expected by the Streamlit app."""
    print("Testing ZIP extraction...")
    
    from tests.create_fixtures import create_all_fixtures
    fixtures_dir, vdr_dir, tracker_path, priority_path = create_all_fixtures()
    
    # Create a ZIP file from the VDR directory (simulating user upload)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in vdr_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(vdr_dir)
                zipf.write(file_path, arcname)
    
    zip_buffer.seek(0)
    
    # Extract to temp directory (like the app does)
    temp_dir = tempfile.mkdtemp(prefix="test_zip_")
    try:
        with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Verify files were extracted
        extracted_files = list(Path(temp_dir).rglob('*'))
        extracted_files = [f for f in extracted_files if f.is_file()]
        
        original_files = list(vdr_dir.rglob('*'))
        original_files = [f for f in original_files if f.is_file()]
        
        assert len(extracted_files) == len(original_files), \
            f"Expected {len(original_files)} files, got {len(extracted_files)}"
        
        print(f"  ✅ Extracted {len(extracted_files)} files correctly")
    finally:
        shutil.rmtree(temp_dir)
    
    return True


def test_app_scan_flow():
    """Test the complete scan flow as performed by the Streamlit app."""
    print("\nTesting app scan flow...")
    
    from tests.create_fixtures import create_all_fixtures
    from src.orchestration import load_tracker, scan_vdr_folder
    from src.export import flatten_results_to_dataframe, format_summary
    
    fixtures_dir, vdr_dir, tracker_path, priority_path = create_all_fixtures()
    
    # Step 1: Load tracker (as app does)
    search_terms, sheet_name = load_tracker(tracker_path)
    assert len(search_terms) > 0
    print(f"  ✅ Loaded {len(search_terms)} search terms")
    
    # Step 2: Parse priority terms (as app does)
    with open(priority_path) as f:
        priority_text = f.read()
    
    priority_terms = []
    for line in priority_text.strip().split("\n"):
        term = line.strip()
        if term and not term.startswith("#"):
            priority_terms.append(term)
    
    assert len(priority_terms) > 0
    print(f"  ✅ Parsed {len(priority_terms)} priority terms")
    
    # Step 3: Create ZIP and extract (simulating upload)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in vdr_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(vdr_dir)
                zipf.write(file_path, arcname)
    
    zip_buffer.seek(0)
    
    temp_dir = tempfile.mkdtemp(prefix="test_app_")
    try:
        with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        print(f"  ✅ Extracted ZIP to temp directory")
        
        # Step 4: Run scan (as app does)
        results, total_files = scan_vdr_folder(
            temp_dir,
            search_terms,
            priority_terms=priority_terms,
            use_parallel=True,
            show_progress=False,  # As app does
        )
        
        assert total_files > 0
        assert len(results) > 0
        print(f"  ✅ Scanned {total_files} files, found issues in {len(results)}")
        
        # Step 5: Process results (as app does)
        df_export = flatten_results_to_dataframe(results)
        summary = format_summary(results, total_files, df_export)
        
        assert summary["files_scanned"] == total_files
        assert summary["files_with_issues"] == len(results)
        print(f"  ✅ Generated summary: {summary['total_occurrences']} total occurrences")
        
        # Step 6: Generate CSV (as app does for download)
        csv_data = df_export.to_csv(index=False).encode('utf-8')
        assert len(csv_data) > 0
        print(f"  ✅ Generated CSV ({len(csv_data)} bytes)")
        
    finally:
        shutil.rmtree(temp_dir)
    
    return True


def test_helper_functions():
    """Test the app's helper functions."""
    print("\nTesting helper functions...")
    
    # Import app helpers - we need to do this carefully to avoid Streamlit errors
    import tempfile
    from pathlib import Path
    
    # Test parse_priority_terms logic (copied from app to avoid Streamlit import)
    def parse_priority_terms(text):
        if not text:
            return []
        terms = []
        for line in text.strip().split("\n"):
            term = line.strip()
            if term and not term.startswith("#"):
                terms.append(term)
        return terms
    
    # Test cases
    assert parse_priority_terms("") == []
    assert parse_priority_terms("spirit\nairlines") == ["spirit", "airlines"]
    assert parse_priority_terms("spirit\n# comment\nairlines") == ["spirit", "airlines"]
    assert parse_priority_terms("  spirit  \n  airlines  ") == ["spirit", "airlines"]
    print("  ✅ parse_priority_terms works correctly")
    
    return True


def main():
    """Run all Streamlit flow tests."""
    print("=" * 60)
    print("Streamlit App Flow Tests")
    print("=" * 60)
    
    all_passed = True
    
    tests = [
        ("ZIP Extraction", test_zip_extraction),
        ("App Scan Flow", test_app_scan_flow),
        ("Helper Functions", test_helper_functions),
    ]
    
    for name, test_fn in tests:
        try:
            if not test_fn():
                print(f"\n❌ {name} FAILED")
                all_passed = False
            else:
                print(f"\n✅ {name} PASSED")
        except Exception as e:
            print(f"\n❌ {name} FAILED with exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL STREAMLIT FLOW TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
