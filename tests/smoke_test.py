#!/usr/bin/env python3
"""
Smoke test for VDR QA Scanner.

This script verifies that the refactored code produces the expected
results when scanning the test fixtures. It checks:

1. Module imports work correctly
2. Tracker loading works
3. Pattern compilation works
4. Each file type parser works
5. Results have the expected structure
6. Export produces valid CSV

Run this after any refactoring to verify behavioral parity.

Usage:
    python tests/smoke_test.py
"""

import json
import sys
import tempfile
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from src import __version__
        print(f"  ✅ src package (version {__version__})")
    except ImportError as e:
        print(f"  ❌ src package: {e}")
        return False
    
    try:
        from src.core import build_compiled_patterns, normalize_for_match
        from src.core import update_found_from_text, update_found_from_text_normalized
        print("  ✅ src.core")
    except ImportError as e:
        print(f"  ❌ src.core: {e}")
        return False
    
    try:
        from src.core.parsers import (
            search_in_pdf,
            search_in_word_doc,
            search_in_excel,
            search_in_csv,
            search_in_powerpoint,
            search_in_text_file,
        )
        print("  ✅ src.core.parsers")
    except ImportError as e:
        print(f"  ❌ src.core.parsers: {e}")
        return False
    
    try:
        from src.orchestration import load_tracker, scan_vdr_folder, get_search_function
        print("  ✅ src.orchestration")
    except ImportError as e:
        print(f"  ❌ src.orchestration: {e}")
        return False
    
    try:
        from src.export import flatten_results_to_dataframe, format_summary, export_results_to_csv
        print("  ✅ src.export")
    except ImportError as e:
        print(f"  ❌ src.export: {e}")
        return False
    
    return True


def test_pattern_compilation():
    """Test pattern compilation functions."""
    print("\nTesting pattern compilation...")
    
    from src.core import build_compiled_patterns, normalize_for_match
    
    # Test exact mode
    exact_patterns = build_compiled_patterns(["Acme", "Test Corp"], mode="exact")
    assert len(exact_patterns) == 2, f"Expected 2 patterns, got {len(exact_patterns)}"
    print("  ✅ Exact mode patterns")
    
    # Test priority_prefix mode
    prefix_patterns = build_compiled_patterns(["spirit", "test"], mode="priority_prefix")
    assert len(prefix_patterns) == 2, f"Expected 2 patterns, got {len(prefix_patterns)}"
    print("  ✅ Priority prefix mode patterns")
    
    # Test normalization
    assert normalize_for_match("(555) 123-4567") == "5551234567"
    assert normalize_for_match("test@email.com") == "testemailcom"
    assert normalize_for_match("Hello World") == "helloworld"
    assert normalize_for_match("") == ""
    print("  ✅ Normalization")
    
    return True


def test_matchers():
    """Test matching functions."""
    print("\nTesting matchers...")
    
    from src.core import build_compiled_patterns, normalize_for_match
    from src.core import update_found_from_text, update_found_from_text_normalized
    
    # Test exact matching
    patterns = build_compiled_patterns(["Acme"], mode="exact")
    found = {}
    update_found_from_text(found, "This is Acme Corporation", patterns, "TEST", "exact")
    assert "Acme" in found, "Expected to find 'Acme'"
    assert found["Acme"]["count"] == 1
    print("  ✅ Exact matching")
    
    # Test that partial doesn't match in exact mode
    found2 = {}
    update_found_from_text(found2, "This is AcmeCorp not Acme", patterns, "TEST", "exact")
    assert found2.get("Acme", {}).get("count", 0) == 1, "Should only match standalone Acme"
    print("  ✅ Exact mode boundary checking")
    
    # Test normalized matching
    normalized_terms = {"(555) 123-4567": normalize_for_match("(555) 123-4567")}
    found3 = {}
    update_found_from_text_normalized(found3, "Call 5551234567 now", normalized_terms, "TEST")
    assert "(555) 123-4567" in found3, "Expected normalized match"
    print("  ✅ Normalized matching")
    
    return True


def test_file_routing():
    """Test file type routing."""
    print("\nTesting file type routing...")
    
    from src.orchestration import get_search_function
    from src.core.parsers import (
        search_in_pdf,
        search_in_word_doc,
        search_in_excel,
        search_in_csv,
        search_in_powerpoint,
        search_in_text_file,
    )
    
    tests = [
        ("test.pdf", search_in_pdf),
        ("test.docx", search_in_word_doc),
        ("test.doc", search_in_word_doc),
        ("test.xlsx", search_in_excel),
        ("test.xls", search_in_excel),
        ("test.pptx", search_in_powerpoint),
        ("test.ppt", search_in_powerpoint),
        ("test.csv", search_in_csv),
        ("test.txt", search_in_text_file),
        ("test.jpg", None),  # Unsupported
        ("test.mp4", None),  # Unsupported
    ]
    
    for filename, expected_fn in tests:
        actual_fn = get_search_function(filename)
        if expected_fn is None:
            assert actual_fn is None, f"Expected None for {filename}, got {actual_fn}"
        else:
            assert actual_fn == expected_fn, f"Wrong function for {filename}"
    
    print("  ✅ All file types routed correctly")
    return True


def test_with_fixtures():
    """Test full scan with fixtures."""
    print("\nTesting with fixtures...")
    
    # First create fixtures
    from tests.create_fixtures import create_all_fixtures
    fixtures_dir, vdr_dir, tracker_path, priority_path = create_all_fixtures()
    
    # Load tracker
    from src.orchestration import load_tracker
    search_terms, sheet_name = load_tracker(tracker_path)
    assert len(search_terms) > 0, "Expected search terms from tracker"
    assert sheet_name == "List", f"Expected sheet 'List', got '{sheet_name}'"
    print(f"  ✅ Loaded {len(search_terms)} terms from tracker")
    
    # Load priority terms
    with open(priority_path) as f:
        priority_terms = [line.strip() for line in f if line.strip()]
    print(f"  ✅ Loaded {len(priority_terms)} priority terms")
    
    # Run scan
    from src.orchestration import scan_vdr_folder
    results, total_files = scan_vdr_folder(
        vdr_dir,
        search_terms,
        priority_terms=priority_terms,
        use_parallel=False,  # Sequential for determinism
        show_progress=False,
    )
    
    print(f"  ✅ Scanned {total_files} files, found issues in {len(results)} files")
    
    # Verify results structure
    assert total_files > 0, "Expected to scan some files"
    assert len(results) > 0, "Expected to find some issues"
    
    for result in results:
        assert "file_name" in result
        assert "file_path" in result
        assert "relative_path" in result
        assert "file_type" in result
        assert "found_terms" in result
        
        for term, info in result["found_terms"].items():
            assert "count" in info
            assert "locations" in info
            assert "term_flagged" in info
            assert "match_type" in info
            assert isinstance(info["count"], int)
            assert isinstance(info["locations"], list)
            assert isinstance(info["term_flagged"], list)
            assert isinstance(info["match_type"], list)
    
    print("  ✅ Results structure validated")
    
    # Test export
    from src.export import flatten_results_to_dataframe, format_summary, export_results_to_csv
    
    df = flatten_results_to_dataframe(results)
    expected_cols = ["file_name", "relative_path", "file_type", "anon_term", 
                     "term_flagged", "match_type", "count", "locations"]
    for col in expected_cols:
        assert col in df.columns, f"Missing column: {col}"
    print("  ✅ DataFrame export validated")
    
    summary = format_summary(results, total_files, df)
    assert summary["files_scanned"] == total_files
    assert summary["files_with_issues"] == len(results)
    print("  ✅ Summary generation validated")
    
    # Test CSV export
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        csv_path = f.name
    
    df_exported, num_rows = export_results_to_csv(results, csv_path)
    assert Path(csv_path).exists(), "CSV file should exist"
    assert num_rows == len(df), "Row count should match"
    Path(csv_path).unlink()  # Cleanup
    print("  ✅ CSV export validated")
    
    return True


def test_specific_matches():
    """Test that specific terms are found in the expected files."""
    print("\nTesting specific term matching...")
    
    from tests.create_fixtures import create_all_fixtures
    fixtures_dir, vdr_dir, tracker_path, priority_path = create_all_fixtures()
    
    from src.orchestration import load_tracker, scan_vdr_folder
    search_terms, _ = load_tracker(tracker_path)
    
    results, _ = scan_vdr_folder(
        vdr_dir,
        search_terms,
        priority_terms=[],
        use_parallel=False,
        show_progress=False,
    )
    
    # Collect all found terms across all files
    all_found = {}
    for result in results:
        for term, info in result["found_terms"].items():
            if term not in all_found:
                all_found[term] = {"files": [], "total_count": 0}
            all_found[term]["files"].append(result["file_name"])
            all_found[term]["total_count"] += info["count"]
    
    # Terms we expect to find
    expected_terms = ["Acme Corporation", "John Smith", "Confidential", "(555) 123-4567"]
    
    for term in expected_terms:
        assert term in all_found, f"Expected to find '{term}'"
        print(f"  ✅ Found '{term}' in {len(all_found[term]['files'])} file(s)")
    
    return True


def print_results_summary(results):
    """Print a summary of scan results for debugging."""
    print("\n  Results Summary:")
    for result in results:
        print(f"    {result['file_name']} ({result['file_type']}):")
        for term, info in result["found_terms"].items():
            print(f"      - '{term}': {info['count']}x in {info['locations']}")


def main():
    """Run all smoke tests."""
    print("=" * 60)
    print("VDR QA Scanner - Smoke Test")
    print("=" * 60)
    
    all_passed = True
    
    tests = [
        ("Imports", test_imports),
        ("Pattern Compilation", test_pattern_compilation),
        ("Matchers", test_matchers),
        ("File Routing", test_file_routing),
        ("Full Scan with Fixtures", test_with_fixtures),
        ("Specific Term Matching", test_specific_matches),
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
        print("✅ ALL SMOKE TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
