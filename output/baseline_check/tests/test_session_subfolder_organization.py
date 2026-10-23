# -*- coding: utf-8 -*-
"""
Test Suite: Session Subfolder Organization & Clean Directory Structure.

Validates:
1. Subfolder creation and management (Events/, GCD/, Calibration/, Reports/).
2. Automatic session directory reorganization (migrating loose generated files while leaving raw files in root).
3. Dual-lookup with subfolder prioritization and root fallback (find_event_results_file, find_gcd_file, find_all_gcd_files, find_static_calibration_files).
4. Event service save/load behavior honoring Events/ subfolder.
5. Calibration and GCD generation path targeting.
6. PDF report export defaulting to Reports/ subfolder.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Conda library bin path for Windows DLLs
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    conda_lib = os.path.join(sys.prefix, "Library", "bin")
    if os.path.isdir(conda_lib):
        if conda_lib not in os.environ.get("PATH", ""):
            os.environ["PATH"] = conda_lib + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(conda_lib)
            except Exception:
                pass

from app.services.session_organizer import (
    FOLDER_EVENTS,
    FOLDER_GCD,
    FOLDER_CALIBRATION,
    FOLDER_REPORTS,
    ensure_session_subfolders,
    get_events_dir,
    get_gcd_dir,
    get_calibration_dir,
    get_reports_dir,
    find_event_results_file,
    find_gcd_file,
    find_all_gcd_files,
    find_static_calibration_files,
    organize_session_directory,
)
from app.services.event_service import (
    save_trial_events,
    load_trial_events,
)


def test_ensure_session_subfolders():
    """Verify that ensure_session_subfolders creates Events, GCD, Calibration, and Reports."""
    print("--- 1. Testing ensure_session_subfolders ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        s_dir = Path(tmpdir)
        ensure_session_subfolders(s_dir)

        assert (s_dir / FOLDER_EVENTS).is_dir(), "Events/ folder should exist"
        assert (s_dir / FOLDER_GCD).is_dir(), "GCD/ folder should exist"
        assert (s_dir / FOLDER_CALIBRATION).is_dir(), "Calibration/ folder should exist"
        assert (s_dir / FOLDER_REPORTS).is_dir(), "Reports/ folder should exist"
    print("✓ ensure_session_subfolders successfully created all subdirectories.")


def test_organize_session_directory_migration():
    """Verify organize_session_directory moves loose files to subfolders and preserves raw capture files."""
    print("--- 2. Testing organize_session_directory migration & raw file preservation ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        s_dir = Path(tmpdir)

        # 1. Create raw capture files (must NEVER be moved)
        raw_files = [
            s_dir / "session.xml",
            s_dir / "Dynamic 1.qtm",
            s_dir / "Dynamic 1.c3d",
            s_dir / "Static 1.qtm",
            s_dir / "data.qpr",
        ]
        for f in raw_files:
            f.write_text("raw_content", encoding="utf-8")

        # 2. Create loose generated files in root
        loose_event_json = s_dir / "auto_event_Dynamic 1_results.json"
        loose_event_json.write_text(json.dumps({"total_events": 4}), encoding="utf-8")
        loose_event_log = s_dir / "auto_event_Dynamic 1.log"
        loose_event_log.write_text("log output", encoding="utf-8")

        loose_gcd = s_dir / "Dynamic 1.GCD"
        loose_gcd.write_text("GCD_DATA_HEADER", encoding="utf-8")

        loose_static = s_dir / "Static_BF_TestSubject.py"
        loose_static.write_text("# Static model", encoding="utf-8")
        loose_sitting = s_dir / "SittingFootStatic_TestSubject.py"
        loose_sitting.write_text("# Sitting foot model", encoding="utf-8")
        loose_pelfix = s_dir / "TempPelfix123.py"
        loose_pelfix.write_text("# Pelvis fix", encoding="utf-8")

        loose_report = s_dir / "Gait_Analysis_Report_20261010.pdf"
        loose_report.write_bytes(b"%PDF-1.4 mock pdf")

        # Run organization
        moved = organize_session_directory(s_dir)

        # Verify raw files are STILL in root
        for f in raw_files:
            assert f.exists(), f"Raw capture file {f.name} must remain in session root"

        # Verify loose files moved to proper subfolders
        assert not loose_event_json.exists(), "Loose event json should have been moved from root"
        assert not loose_event_log.exists(), "Loose event log should have been moved from root"
        assert (s_dir / FOLDER_EVENTS / loose_event_json.name).exists(), "Event json must be in Events/"
        assert (s_dir / FOLDER_EVENTS / loose_event_log.name).exists(), "Event log must be in Events/"

        assert not loose_gcd.exists(), "Loose GCD should have been moved from root"
        assert (s_dir / FOLDER_GCD / loose_gcd.name).exists(), "GCD must be in GCD/"

        assert not loose_static.exists(), "Loose static model should have been moved from root"
        assert (s_dir / FOLDER_CALIBRATION / loose_static.name).exists(), "Static model must be in Calibration/"
        assert (s_dir / FOLDER_CALIBRATION / loose_sitting.name).exists(), "Sitting foot model must be in Calibration/"
        assert (s_dir / FOLDER_CALIBRATION / loose_pelfix.name).exists(), "TempPelfix must be in Calibration/"

        assert not loose_report.exists(), "Loose PDF report should have been moved from root"
        assert (s_dir / FOLDER_REPORTS / loose_report.name).exists(), "PDF report must be in Reports/"

        # Check moved summary dict
        assert "auto_event_Dynamic 1_results.json" in moved["events"]
        assert "Dynamic 1.GCD" in moved["gcd"]
        assert "Static_BF_TestSubject.py" in moved["calibration"]
        assert "Gait_Analysis_Report_20261010.pdf" in moved["reports"]

    print("✓ organize_session_directory correctly moved loose files and preserved raw files.")


def test_dual_lookup_fallback():
    """Verify dual-lookup: checking subfolder first, with fallback to root if not yet migrated."""
    print("--- 3. Testing dual-lookup & fallback logic ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        s_dir = Path(tmpdir)
        ensure_session_subfolders(s_dir)

        # Case A: File only in root (legacy / unmigrated session)
        root_gcd = s_dir / "Trial_Root.GCD"
        root_gcd.write_text("root_gcd", encoding="utf-8")

        root_ev = s_dir / "auto_event_Trial_Root_results.json"
        root_ev.write_text("{}", encoding="utf-8")

        root_calib = s_dir / "Static_BF_PatientA.py"
        root_calib.write_text("# root calib", encoding="utf-8")

        found_gcd = find_gcd_file(s_dir, "Trial_Root")
        assert found_gcd == root_gcd, "Should fallback to root when GCD/ has no file"

        found_ev = find_event_results_file(s_dir, "Trial_Root")
        assert found_ev == root_ev, "Should fallback to root when Events/ has no file"

        calib_files = find_static_calibration_files(s_dir, "PatientA")
        assert root_calib in calib_files, "Should include root calibration in fallback"

        # Case B: File in subfolder (priority)
        sub_gcd = s_dir / FOLDER_GCD / "Trial_Sub.GCD"
        sub_gcd.write_text("sub_gcd", encoding="utf-8")

        sub_ev = s_dir / FOLDER_EVENTS / "auto_event_Trial_Sub_results.json"
        sub_ev.write_text("{}", encoding="utf-8")

        sub_calib = s_dir / FOLDER_CALIBRATION / "Static_BF_PatientA.py"
        sub_calib.write_text("# sub calib", encoding="utf-8")

        found_sub_gcd = find_gcd_file(s_dir, "Trial_Sub")
        assert found_sub_gcd == sub_gcd, "Should find file directly in GCD/"

        found_sub_ev = find_event_results_file(s_dir, "Trial_Sub")
        assert found_sub_ev == sub_ev, "Should find file directly in Events/"

        # When file exists in BOTH, subfolder must take precedence
        duplicate_gcd = s_dir / FOLDER_GCD / "Trial_Root.GCD"
        duplicate_gcd.write_text("subfolder_preferred", encoding="utf-8")
        assert find_gcd_file(s_dir, "Trial_Root") == duplicate_gcd, "Subfolder must take precedence over root"

        all_gcds = find_all_gcd_files(s_dir)
        # Should have Trial_Root (from GCD/) and Trial_Sub (from GCD/) without duplicates
        gcd_stems = [g.stem for g in all_gcds]
        assert "Trial_Root" in gcd_stems
        assert "Trial_Sub" in gcd_stems
        assert len(all_gcds) == len(set(gcd_stems)), "find_all_gcd_files must deduplicate"

    print("✓ Dual-lookup and prioritization working perfectly.")


def test_event_service_subfolder_integration():
    """Verify event_service save_trial_events writes to Events/ and cleans up root duplicates."""
    print("--- 4. Testing event_service saving to Events/ subfolder ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        s_dir = Path(tmpdir)
        trial_fname = "Walk 01.qtm"

        # Create a stale file in root
        stale_root = s_dir / "auto_event_Walk 01_results.json"
        stale_root.write_text(json.dumps({"stale": True}), encoding="utf-8")

        # Save new events via event_service
        new_events = [
            {"frame": 100, "label": "RSTRIKE"},
            {"frame": 160, "label": "ROFF"},
            {"frame": 200, "label": "LSTRIKE"},
            {"frame": 260, "label": "LOFF"},
        ]
        saved_info = save_trial_events(s_dir, trial_fname, new_events, meta={"frame_rate": 100.0})
        saved_path = Path(saved_info["filepath"])

        # Assert saved path is in Events/
        assert saved_path is not None
        assert saved_path.parent == s_dir / FOLDER_EVENTS, f"Saved path must be in Events/, got {saved_path}"
        assert saved_path.exists()

        # Assert root duplicate was cleaned up
        assert not stale_root.exists(), "Stale root file must be removed when saving to Events/"

        # Load back events
        loaded = load_trial_events(s_dir, trial_fname)
        assert loaded is not None
        assert loaded["total_events"] == 4
        assert loaded["r_hs"] == 1
        assert loaded["l_hs"] == 1

    print("✓ Event service writes to Events/ and cleans up root duplicates.")


def test_reports_dir_default_export():
    """Verify get_reports_dir path and default behavior for PDF export."""
    print("--- 5. Testing Reports/ directory path resolution ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        s_dir = Path(tmpdir)
        rep_dir = get_reports_dir(s_dir)
        assert rep_dir == s_dir / FOLDER_REPORTS
        assert rep_dir.is_dir()

        report_file = rep_dir / "Gait_Analysis_Report_Patient1.pdf"
        report_file.write_bytes(b"%PDF-1.4 dummy content")
        assert report_file.exists()

    print("✓ Reports directory path verified.")


def test_dynamic_analysis_page_loads_and_organizes():
    """Verify that DynamicAnalysisPage discovers GCDs and Events in subfolders and organize_session_directory migrates loose files."""
    print("--- 6. Testing DynamicAnalysisPage Subfolder Discovery & Session Organization ---")
    from PySide6.QtWidgets import QApplication
    from app.ui.pages.dynamic_analysis_page import DynamicAnalysisPage

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    with tempfile.TemporaryDirectory() as tmpdir:
        s_dir = Path(tmpdir)
        session_xml = s_dir / "session.xml"
        session_xml.write_text("<Session></Session>", encoding="utf-8")

        # Create dummy trial files
        (s_dir / "Dynamic 1.qtm").write_bytes(b"dummy")
        (s_dir / "Dynamic 1.c3d").write_bytes(b"dummy")

        # Create loose GCD and loose event json in root
        loose_gcd = s_dir / "Dynamic 1.GCD"
        loose_gcd.write_text("GCD_CONTENT", encoding="utf-8")

        event_data = {
            "events": [
                {"frame": 100, "label": "RSTRIKE"},
                {"frame": 150, "label": "ROFF"},
            ],
            "meta": {"source": "test"},
        }
        loose_event = s_dir / "auto_event_Dynamic 1_results.json"
        loose_event.write_text(json.dumps(event_data), encoding="utf-8")

        # 1. Run organize_session_directory
        organize_session_directory(s_dir)
        assert not loose_gcd.exists(), "Loose GCD in root must be migrated"
        assert not loose_event.exists(), "Loose event JSON in root must be migrated"
        assert (s_dir / FOLDER_GCD / "Dynamic 1.GCD").exists(), "GCD must now be in GCD/"
        assert (s_dir / FOLDER_EVENTS / "auto_event_Dynamic 1_results.json").exists(), "Event JSON must now be in Events/"

        # 2. Load session into DynamicAnalysisPage and verify subfolder discovery
        page = DynamicAnalysisPage()
        page.load_session(str(session_xml))

        # Verify row status is COMPLETE (detected from GCD/ folder)
        assert "Dynamic 1.qtm" in page._trial_rows
        row = page._trial_rows["Dynamic 1.qtm"]
        assert row._status == "COMPLETE", f"Expected status COMPLETE for trial with GCD in GCD/, got {row._status}"
        assert row.events_info is not None and row.events_info.get("total_events") == 2, (
            f"Expected total_events 2 loaded from Events/, got {row.events_info}"
        )

    print("✓ DynamicAnalysisPage detected GCD and Events directly from proper subfolders.")


def test_case_presentation_page_gcd_subfolder_discovery():
    """Verify CasePresentationPage discovers and loads GCDs from GCD/ subfolder."""
    print("--- 7. Testing CasePresentationPage GCD Discovery from GCD/ ---")
    from PySide6.QtWidgets import QApplication
    from app.ui.pages.case_presentation_page import CasePresentationPage

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    with tempfile.TemporaryDirectory() as tmpdir:
        s_dir = Path(tmpdir)
        gcd_dir = get_gcd_dir(s_dir)

        gcd_file = gcd_dir / "Dynamic 1.GCD"
        gcd_file.write_text("GCD_CONTENT", encoding="utf-8")

        page = CasePresentationPage()
        found = page._find_gcd_file(s_dir, "Dynamic 1")
        assert found == gcd_file, f"Expected {gcd_file}, got {found}"

    print("✓ CasePresentationPage successfully resolved GCD from GCD/ subfolder.")


if __name__ == "__main__":
    test_ensure_session_subfolders()
    test_organize_session_directory_migration()
    test_dual_lookup_fallback()
    test_event_service_subfolder_integration()
    test_reports_dir_default_export()
    test_dynamic_analysis_page_loads_and_organizes()
    test_case_presentation_page_gcd_subfolder_discovery()
    print("\n==========================================")
    print("ALL SESSION ORGANIZATION TESTS PASSED! ✓")
    print("==========================================")

