# VDR QA Scanner

A document anonymization verification tool that scans a folder of documents (a "Virtual Data Room") looking for terms that should have been anonymized but weren't.

## Overview

The VDR QA Scanner:
- Loads search terms from an anonymization tracker Excel file (terms in the "Before" column)
- Accepts priority terms for prefix-based matching
- Scans documents in multiple formats (PDF, Word, Excel, PowerPoint, CSV, TXT)
- Reports exact matches and partial/prefix matches
- Exports findings to CSV for review

## Project Structure

```
vda-qa-scanner/
├── run_scan.py                  # CLI entry point
├── requirements.txt             # Python dependencies
├── vdr_qa_local_fixed_V2.ipynb  # Original notebook (reference)
│
├── src/                         # Main package
│   ├── core/                    # Core logic (pattern matching, text extraction)
│   │   ├── patterns.py          # Pattern compilation and normalization
│   │   ├── matchers.py          # Text matching functions
│   │   └── parsers/             # File-type specific parsers
│   │       ├── pdf.py
│   │       ├── word.py
│   │       ├── excel.py
│   │       ├── csv_parser.py
│   │       ├── powerpoint.py
│   │       └── text.py
│   ├── orchestration/           # High-level scanning workflow
│   │   ├── scanner.py           # Main scan_vdr_folder function
│   │   └── tracker_loader.py    # Excel tracker loading
│   └── export/                  # Results formatting and export
│       └── results.py
│
└── tests/                       # Tests and fixtures
    ├── smoke_test.py            # Verification tests
    └── create_fixtures.py       # Test data generator
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/shahkhanseekinvest/vda-qa-scanner.git
   cd vda-qa-scanner
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Streamlit Web App

The easiest way to use the scanner is through the Streamlit web interface:

```bash
streamlit run app.py
```

This opens a browser with a UI that allows you to:
1. **Upload** your anonymization tracker (.xlsx)
2. **Upload** your VDR folder as a ZIP file
3. **Enter** priority terms (optional)
4. **Run** the scan and view results
5. **Download** results as CSV

### Command Line Interface

```bash
# Basic usage
python run_scan.py --tracker path/to/tracker.xlsx --folder path/to/vdr

# With priority terms from a file (one per line)
python run_scan.py --tracker tracker.xlsx --folder vdr/ --priority-file priority.txt

# With inline priority terms
python run_scan.py --tracker tracker.xlsx --folder vdr/ --priority "spirit,airlines,savers"

# Specify output file
python run_scan.py --tracker tracker.xlsx --folder vdr/ --output results.csv

# Verbose mode
python run_scan.py --tracker tracker.xlsx --folder vdr/ --verbose
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--tracker, -t` | Path to the anonymization tracker Excel file (required) |
| `--folder, -f` | Path to the VDR folder to scan (required) |
| `--output, -o` | Output CSV file path (default: vdr_qa_results.csv) |
| `--priority, -p` | Comma-separated priority terms for prefix matching |
| `--priority-file` | File containing priority terms (one per line) |
| `--sequential` | Disable parallel processing |
| `--workers, -w` | Number of worker threads (default: auto) |
| `--verbose, -v` | Enable verbose logging |
| `--no-progress` | Disable progress bar |

### Programmatic Usage

```python
from src.orchestration import load_tracker, scan_vdr_folder
from src.export import export_results_to_csv, format_summary

# Load search terms from tracker
search_terms, sheet_name = load_tracker("tracker.xlsx")

# Define priority terms (prefix matching)
priority_terms = ["spirit", "airlines", "acme"]

# Run scan
results, total_files = scan_vdr_folder(
    "path/to/vdr",
    search_terms,
    priority_terms=priority_terms,
)

# Export results
df, num_rows = export_results_to_csv(results, "output.csv")

# Get summary
summary = format_summary(results, total_files)
print(f"Found issues in {summary['files_with_issues']} of {summary['files_scanned']} files")
```

## Matching Modes

### Exact Matching
Terms from the tracker are matched as whole tokens using non-alphanumeric boundaries:
- `"Acme Corporation"` matches `"Contact Acme Corporation today"`
- `"Acme Corporation"` does NOT match `"AcmeCorporation"` (no boundary)

### Priority Prefix Matching
Priority terms match when they appear at the start of a token with additional characters:
- `"spirit"` matches `"SpiritAirlines"` (prefix with extra chars)
- `"spirit"` does NOT match `"MySpirit"` (not at start)
- `"spirit"` does NOT match `"spirit"` alone (must have extra chars)

### Normalized Matching
For terms with special characters (phone numbers, emails, etc.), matching ignores non-alphanumeric characters:
- `"(555) 123-4567"` matches `"5551234567"` in the document

## Supported File Types

| Extension | Parser | Notes |
|-----------|--------|-------|
| `.pdf` | PyPDF2 | Page-by-page extraction |
| `.docx` | python-docx | Body, tables, headers, footers |
| `.doc` | python-docx | Legacy format, limited support |
| `.xlsx` | pandas + openpyxl | All sheets, string columns only |
| `.xls` | pandas + openpyxl | Legacy format, limited support |
| `.pptx` | python-pptx | Slides, notes, tables, layouts, masters |
| `.ppt` | python-pptx | Legacy format, limited support |
| `.csv` | pandas | All cells as strings |
| `.txt` | built-in | Chunked reading for large files |

## Verification

Run the smoke tests to verify the installation:

```bash
python tests/smoke_test.py
```

This will:
1. Test all module imports
2. Test pattern compilation
3. Test matching functions
4. Test file type routing
5. Create fixtures and run a full scan
6. Verify specific term matching

## Output Format

The CSV export contains:

| Column | Description |
|--------|-------------|
| `file_name` | Base filename |
| `relative_path` | Path relative to VDR folder |
| `file_type` | File extension (without dot) |
| `anon_term` | The search term that was matched |
| `term_flagged` | Actual text that matched (may differ for prefix matches) |
| `match_type` | "exact" or "partial" |
| `count` | Number of occurrences |
| `locations` | Where found (e.g., "PAGE 1; HEADER 2") |

## Original Notebook

The original notebook `vdr_qa_local_fixed_V2.ipynb` is preserved for reference. The modular code in `src/` is a direct extraction of the notebook's logic with identical behavior.
