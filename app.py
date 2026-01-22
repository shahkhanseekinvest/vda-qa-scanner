#!/usr/bin/env python3
"""
VDR QA Scanner - Streamlit Application

A thin UI layer over the existing scan logic in src/.
This app does not modify or duplicate any core logic.
"""

import io
import os
import tempfile
import zipfile
import logging
import warnings
from pathlib import Path

import streamlit as st

# Suppress noisy library warnings (matching run_scan.py behavior)
warnings.filterwarnings("ignore")
logging.getLogger("PyPDF2").setLevel(logging.ERROR)

# Configure app logger
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger("vdr_qa.app")

# Import from existing package - NO logic duplication
from src.orchestration import load_tracker, scan_vdr_folder
from src.export import flatten_results_to_dataframe, format_summary

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="VDR QA Scanner",
    page_icon="🔍",
    layout="wide",
)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Initialize session state variables."""
    defaults = {
        "search_terms": None,
        "tracker_sheet_name": None,
        "tracker_filename": None,
        "vdr_zip_filename": None,
        "priority_terms_text": "",
        "results": None,
        "total_files": None,
        "df_export": None,
        "summary": None,
        "scan_completed": False,
        "error_message": None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


init_session_state()

# =============================================================================
# FILE HANDLING UTILITIES
# =============================================================================

def save_uploaded_file_to_temp(uploaded_file, suffix=None):
    """
    Save a Streamlit UploadedFile to a temporary file.
    
    Returns the path to the temp file.
    The caller is responsible for cleanup.
    """
    if suffix is None:
        suffix = Path(uploaded_file.name).suffix
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file.write(uploaded_file.getvalue())
    temp_file.close()
    return temp_file.name


def extract_zip_to_temp_dir(uploaded_zip):
    """
    Extract a ZIP file to a temporary directory.
    
    Returns the path to the temp directory.
    The caller is responsible for cleanup.
    """
    temp_dir = tempfile.mkdtemp(prefix="vdr_scan_")
    
    with zipfile.ZipFile(io.BytesIO(uploaded_zip.getvalue()), 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    return temp_dir


def cleanup_temp_path(path):
    """Clean up a temporary file or directory."""
    import shutil
    path = Path(path)
    try:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()
    except Exception as e:
        logger.warning(f"Failed to clean up temp path {path}: {e}")


def parse_priority_terms(text):
    """Parse priority terms from newline-separated text."""
    if not text:
        return []
    terms = []
    for line in text.strip().split("\n"):
        term = line.strip()
        if term and not term.startswith("#"):
            terms.append(term)
    return terms

# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_header():
    """Render the app header."""
    st.title("🔍 VDR QA Scanner")
    st.markdown(
        "Scan documents for anonymization issues. "
        "Upload your tracker and VDR folder to find terms that should have been anonymized."
    )
    st.divider()


def render_sidebar():
    """Render the sidebar with file uploads and configuration."""
    with st.sidebar:
        st.header("📁 Input Files")
        
        # Tracker file upload
        st.subheader("1. Anonymization Tracker")
        tracker_file = st.file_uploader(
            "Upload Excel tracker file",
            type=["xlsx", "xls"],
            help="Excel file with a 'Before' column containing terms to search for",
            key="tracker_uploader",
        )
        
        if tracker_file is not None:
            # Only reload if it's a different file
            if st.session_state.tracker_filename != tracker_file.name:
                load_tracker_file(tracker_file)
        
        # Show tracker status
        if st.session_state.search_terms:
            st.success(
                f"✅ Loaded {len(st.session_state.search_terms)} terms "
                f"from sheet: {st.session_state.tracker_sheet_name}"
            )
        
        st.divider()
        
        # VDR folder upload
        st.subheader("2. VDR Folder (ZIP)")
        vdr_zip = st.file_uploader(
            "Upload VDR folder as ZIP",
            type=["zip"],
            help="ZIP archive containing the documents to scan",
            key="vdr_uploader",
        )
        
        if vdr_zip is not None:
            if st.session_state.vdr_zip_filename != vdr_zip.name:
                st.session_state.vdr_zip_filename = vdr_zip.name
                # Reset scan state when new files are uploaded
                st.session_state.scan_completed = False
                st.session_state.results = None
        
        if st.session_state.vdr_zip_filename:
            st.success(f"✅ Ready: {st.session_state.vdr_zip_filename}")
        
        st.divider()
        
        # Priority terms
        st.subheader("3. Priority Terms (Optional)")
        priority_text = st.text_area(
            "Enter priority terms (one per line)",
            value=st.session_state.priority_terms_text,
            height=150,
            help="These terms use prefix matching. E.g., 'spirit' matches 'SpiritAirlines'",
            key="priority_input",
        )
        st.session_state.priority_terms_text = priority_text
        
        priority_terms = parse_priority_terms(priority_text)
        if priority_terms:
            st.info(f"📋 {len(priority_terms)} priority term(s)")
        
        st.divider()
        
        # Scan button
        can_scan = (
            st.session_state.search_terms is not None 
            and vdr_zip is not None
        )
        
        if st.button(
            "🚀 Run Scan",
            type="primary",
            disabled=not can_scan,
            use_container_width=True,
        ):
            run_scan(vdr_zip, priority_terms)
        
        if not can_scan:
            if st.session_state.search_terms is None:
                st.warning("⚠️ Please upload a tracker file")
            elif vdr_zip is None:
                st.warning("⚠️ Please upload a VDR ZIP file")
        
        return vdr_zip, priority_terms


def load_tracker_file(tracker_file):
    """Load and process the tracker file."""
    temp_path = None
    try:
        temp_path = save_uploaded_file_to_temp(tracker_file)
        search_terms, sheet_name = load_tracker(temp_path)
        
        st.session_state.search_terms = search_terms
        st.session_state.tracker_sheet_name = sheet_name
        st.session_state.tracker_filename = tracker_file.name
        st.session_state.error_message = None
        
        # Reset scan state when tracker changes
        st.session_state.scan_completed = False
        st.session_state.results = None
        
    except Exception as e:
        st.session_state.error_message = f"Failed to load tracker: {type(e).__name__}: {e}"
        st.session_state.search_terms = None
        st.session_state.tracker_sheet_name = None
        logger.error(st.session_state.error_message)
    finally:
        if temp_path:
            cleanup_temp_path(temp_path)


def run_scan(vdr_zip, priority_terms):
    """Execute the scan operation with clear stage-by-stage progress."""
    temp_dir = None
    
    # Define scan stages with weights (approximate time proportion)
    stages = [
        {"name": "Extracting ZIP archive", "icon": "📦", "weight": 10},
        {"name": "Discovering files", "icon": "🔍", "weight": 5},
        {"name": "Scanning documents", "icon": "🔎", "weight": 75},
        {"name": "Processing results", "icon": "📊", "weight": 10},
    ]
    total_weight = sum(s["weight"] for s in stages)
    
    try:
        # Create a container for progress UI in the sidebar
        progress_container = st.container()
        
        with progress_container:
            st.markdown("---")
            st.markdown("##### 🔄 Scan Progress")
            
            # Overall progress bar
            progress_bar = st.progress(0, text="Starting scan...")
            
            # Stage status placeholders
            stage_placeholders = []
            for stage in stages:
                placeholder = st.empty()
                placeholder.markdown(f"⬜ {stage['icon']} {stage['name']}")
                stage_placeholders.append(placeholder)
            
            # Stats placeholder
            stats_placeholder = st.empty()
            
            current_progress = 0
            
            # ─────────────────────────────────────────────────────────────
            # STAGE 1: Extract ZIP
            # ─────────────────────────────────────────────────────────────
            stage_placeholders[0].markdown(f"🔄 {stages[0]['icon']} **{stages[0]['name']}...**")
            progress_bar.progress(
                current_progress / total_weight,
                text=f"Stage 1/4: {stages[0]['name']}..."
            )
            
            temp_dir = extract_zip_to_temp_dir(vdr_zip)
            
            current_progress += stages[0]["weight"]
            stage_placeholders[0].markdown(f"✅ {stages[0]['icon']} {stages[0]['name']}")
            
            # ─────────────────────────────────────────────────────────────
            # STAGE 2: Discover files (quick count before scan)
            # ─────────────────────────────────────────────────────────────
            stage_placeholders[1].markdown(f"🔄 {stages[1]['icon']} **{stages[1]['name']}...**")
            progress_bar.progress(
                current_progress / total_weight,
                text=f"Stage 2/4: {stages[1]['name']}..."
            )
            
            # Quick file discovery for stats display
            from src.orchestration.scanner import get_search_function
            discovered_files = []
            for root, dirs, files in os.walk(temp_dir):
                # Apply same exclusions as scanner
                dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "venv"}]
                for name in files:
                    file_path = Path(root) / name
                    if get_search_function(file_path) is not None:
                        discovered_files.append(file_path)
            
            file_count = len(discovered_files)
            current_progress += stages[1]["weight"]
            stage_placeholders[1].markdown(f"✅ {stages[1]['icon']} {stages[1]['name']} — **{file_count} files**")
            
            # Show scan configuration
            stats_placeholder.info(
                f"📋 **Scan Configuration**\n\n"
                f"- Files to scan: **{file_count}**\n"
                f"- Search terms: **{len(st.session_state.search_terms)}**\n"
                f"- Priority terms: **{len(priority_terms)}**"
            )
            
            # ─────────────────────────────────────────────────────────────
            # STAGE 3: Run the actual scan
            # ─────────────────────────────────────────────────────────────
            stage_placeholders[2].markdown(f"🔄 {stages[2]['icon']} **{stages[2]['name']}...**")
            progress_bar.progress(
                current_progress / total_weight,
                text=f"Stage 3/4: {stages[2]['name']} ({file_count} files)..."
            )
            
            # This is the main scan - we can't track internal progress
            # but we show it's running
            results, total_files = scan_vdr_folder(
                temp_dir,
                st.session_state.search_terms,
                priority_terms=priority_terms,
                use_parallel=True,
                show_progress=False,
            )
            
            current_progress += stages[2]["weight"]
            issues_found = len(results)
            stage_placeholders[2].markdown(
                f"✅ {stages[2]['icon']} {stages[2]['name']} — "
                f"**{issues_found} file{'s' if issues_found != 1 else ''} with issues**"
            )
            
            # ─────────────────────────────────────────────────────────────
            # STAGE 4: Process results
            # ─────────────────────────────────────────────────────────────
            stage_placeholders[3].markdown(f"🔄 {stages[3]['icon']} **{stages[3]['name']}...**")
            progress_bar.progress(
                current_progress / total_weight,
                text=f"Stage 4/4: {stages[3]['name']}..."
            )
            
            df_export = flatten_results_to_dataframe(results)
            summary = format_summary(results, total_files, df_export)
            
            current_progress += stages[3]["weight"]
            stage_placeholders[3].markdown(
                f"✅ {stages[3]['icon']} {stages[3]['name']} — "
                f"**{summary['total_occurrences']} occurrences**"
            )
            
            # ─────────────────────────────────────────────────────────────
            # COMPLETE
            # ─────────────────────────────────────────────────────────────
            progress_bar.progress(1.0, text="✅ Scan complete!")
            
            # Update stats placeholder with final summary
            if issues_found > 0:
                stats_placeholder.warning(
                    f"⚠️ **Scan Complete**\n\n"
                    f"- Files scanned: **{total_files}**\n"
                    f"- Files with issues: **{issues_found}**\n"
                    f"- Total occurrences: **{summary['total_occurrences']}**\n"
                    f"- Unique terms found: **{summary['unique_terms_found']}**"
                )
            else:
                stats_placeholder.success(
                    f"✅ **Scan Complete — No Issues Found**\n\n"
                    f"- Files scanned: **{total_files}**\n"
                    f"- All documents appear properly anonymized!"
                )
            
            # Store in session state
            st.session_state.results = results
            st.session_state.total_files = total_files
            st.session_state.df_export = df_export
            st.session_state.summary = summary
            st.session_state.scan_completed = True
            st.session_state.error_message = None
            
    except Exception as e:
        st.session_state.error_message = f"Scan failed: {type(e).__name__}: {e}"
        st.session_state.scan_completed = False
        logger.error(st.session_state.error_message)
        
        # Show error in progress area
        if 'progress_bar' in locals():
            progress_bar.progress(0, text="❌ Scan failed")
        st.error(f"❌ {st.session_state.error_message}")
        
    finally:
        if temp_dir:
            cleanup_temp_path(temp_dir)


def render_results():
    """Render the results section."""
    if st.session_state.error_message:
        st.error(st.session_state.error_message)
        return
    
    if not st.session_state.scan_completed:
        st.info(
            "👈 Upload your files in the sidebar and click **Run Scan** to begin."
        )
        return
    
    summary = st.session_state.summary
    results = st.session_state.results
    df_export = st.session_state.df_export
    
    # Summary metrics
    st.header("📊 Scan Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Files Scanned", summary["files_scanned"])
    
    with col2:
        st.metric("Files with Issues", summary["files_with_issues"])
    
    with col3:
        st.metric("Total Occurrences", summary["total_occurrences"])
    
    with col4:
        st.metric("Unique Terms Found", summary["unique_terms_found"])
    
    st.divider()
    
    # Status message
    if not results:
        st.success("✅ **NO ISSUES FOUND!** All documents appear to be properly anonymized.")
        return
    
    st.warning(f"⚠️ **Found potential issues in {len(results)} file(s)**")
    
    # Download button
    st.header("💾 Export Results")
    
    csv_data = df_export.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Results as CSV",
        data=csv_data,
        file_name="vdr_qa_results.csv",
        mime="text/csv",
        type="primary",
    )
    
    st.divider()
    
    # Results table
    st.header("📋 Detailed Results")
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        file_filter = st.multiselect(
            "Filter by file",
            options=sorted(df_export["file_name"].unique()),
            default=[],
        )
    
    with col2:
        type_filter = st.multiselect(
            "Filter by file type",
            options=sorted(df_export["file_type"].unique()),
            default=[],
        )
    
    with col3:
        match_filter = st.multiselect(
            "Filter by match type",
            options=sorted(df_export["match_type"].unique()),
            default=[],
        )
    
    # Apply filters
    filtered_df = df_export.copy()
    if file_filter:
        filtered_df = filtered_df[filtered_df["file_name"].isin(file_filter)]
    if type_filter:
        filtered_df = filtered_df[filtered_df["file_type"].isin(type_filter)]
    if match_filter:
        filtered_df = filtered_df[filtered_df["match_type"].isin(match_filter)]
    
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "file_name": st.column_config.TextColumn("File Name", width="medium"),
            "relative_path": st.column_config.TextColumn("Path", width="large"),
            "file_type": st.column_config.TextColumn("Type", width="small"),
            "anon_term": st.column_config.TextColumn("Search Term", width="medium"),
            "term_flagged": st.column_config.TextColumn("Matched Text", width="medium"),
            "match_type": st.column_config.TextColumn("Match Type", width="small"),
            "count": st.column_config.NumberColumn("Count", width="small"),
            "locations": st.column_config.TextColumn("Locations", width="large"),
        },
    )
    
    st.caption(f"Showing {len(filtered_df)} of {len(df_export)} results")
    
    st.divider()
    
    # File-by-file breakdown (expandable)
    st.header("📄 File Details")
    
    for idx, result in enumerate(results):
        # Skip if filtered out
        if file_filter and result["file_name"] not in file_filter:
            continue
        if type_filter and result["file_type"] not in type_filter:
            continue
        
        with st.expander(f"**{result['file_name']}** ({result['file_type'].upper()})"):
            st.text(f"Path: {result['relative_path']}")
            
            for term, info in result["found_terms"].items():
                match_types = info.get("match_type", [])
                # Skip if filtered by match type
                if match_filter:
                    if "partial" in match_types and "partial" not in match_filter:
                        if "exact" not in match_types:
                            continue
                    elif "exact" in match_types and "exact" not in match_filter:
                        if "partial" not in match_types:
                            continue
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{term}**")
                    flagged = info.get("term_flagged", [])
                    if flagged and flagged != [term]:
                        st.caption(f"Matched: {', '.join(flagged)}")
                with col2:
                    st.metric("Count", info.get("count", 0), label_visibility="collapsed")
                
                locations = info.get("locations", [])
                if locations:
                    st.caption(f"📍 {', '.join(locations)}")
                
                st.divider()


# =============================================================================
# MAIN APP
# =============================================================================

def main():
    """Main application entry point."""
    render_header()
    render_sidebar()
    render_results()


if __name__ == "__main__":
    main()
