# -*- coding: utf-8 -*-
"""
Test Suite for Auto Event Labeling in PySide6 Dynamic Analysis GUI.
Tests:
- Event service results parser (load_trial_events, get_session_events_summary)
- EventDetailsDialog table and metric cards display
- TrialRowWidget event badges and button signals
- DynamicAnalysisPage auto-label toolbar button, badge, option toggle, and execution queue
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure Windows cp1252 doesn't fail on unicode console print
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Conda library bin path for Windows DLLs
if sys.platform == "win32":
    conda_lib = os.path.join(sys.prefix, "Library", "bin")
    if os.path.isdir(conda_lib):
        if conda_lib not in os.environ.get("PATH", ""):
            os.environ["PATH"] = conda_lib + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(conda_lib)
            except Exception:
                pass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.services.event_service import get_session_events_summary, load_trial_events
from app.ui.dialogs.event_details_dialog import EventDetailsDialog
from app.ui.pages.dynamic_analysis_page import DynamicAnalysisPage
from app.ui.widgets.trial_row import TrialRowWidget

CANDIDATE_DIRS = [
    PROJECT_ROOT / "Shriners_Gait_Model_PAF_v1.0" / "Shriners_Gait_Model_PAF_v1.0" / "Data" / "Claudia_123-20260928T142041Z-1-001" / "Claudia_123" / "2026-10-01_2",
    PROJECT_ROOT / "Shriners_Gait_Model_PAF_v1.0" / "Shriners_Gait_Model_PAF_v1.0" / "Data" / "Shriners_test_002" / "2025-02-21_0003",
    PROJECT_ROOT / "Shriners_Gait_Model_PAF_v1.0" / "Shriners_Gait_Model_PAF_v1.0" / "Data" / "test_002" / "2025-02-21_0003",
]
SAMPLE_SESSION_DIR = next((d for d in CANDIDATE_DIRS if (d / "auto_event_Dynamic 1_results.json").is_file()), CANDIDATE_DIRS[0])
SAMPLE_SESSION_XML = str(SAMPLE_SESSION_DIR / "session.xml")


def test_event_service_loading():
    """Verify load_trial_events parses auto_event results properly."""
    events_info = load_trial_events(SAMPLE_SESSION_DIR, "Dynamic 1.qtm")
    assert events_info is not None, "Failed to load events for Dynamic 1.qtm"
    assert events_info["total_events"] > 0
    assert "events" in events_info
    assert "r_hs" in events_info
    assert "l_hs" in events_info
    assert events_info["pairing_valid"] is True
    print(f"[PASS] 1. Event service loaded Dynamic 1: {events_info['total_events']} events, pairing={events_info['pairing_valid']}")

    # Test summary for multiple trials
    trials = ["Dynamic 1.qtm", "Dynamic 2.qtm", "Dynamic 3.qtm"]
    summary = get_session_events_summary(SAMPLE_SESSION_DIR, trials)
    assert summary["total_trials"] == 3
    assert summary["labeled_trials"] >= 1
    assert summary["total_events"] > 0
    print(f"[PASS] 2. Session event summary: {summary['labeled_trials']}/{summary['total_trials']} trials labeled ({summary['total_events']} total events)")


def test_event_details_dialog():
    """Verify EventDetailsDialog displays metrics and table rows properly."""
    app = QApplication.instance() or QApplication(sys.argv)

    events_info = load_trial_events(SAMPLE_SESSION_DIR, "Dynamic 1.qtm")
    dlg = EventDetailsDialog(
        trial_filename="Dynamic 1.qtm",
        events_info=events_info,
        frame_rate=100.0,
    )
    assert dlg is not None
    assert dlg._table.rowCount() == events_info["total_events"]
    assert dlg._table.columnCount() == 6

    # Check first row
    first_frame_item = dlg._table.item(0, 1)
    assert first_frame_item is not None
    assert int(first_frame_item.text()) >= 0

    print(f"[PASS] 3. EventDetailsDialog initialized with {dlg._table.rowCount()} rows in chronology table")


def test_trial_row_event_widget():
    """Verify TrialRowWidget handles event data, badges, and button interactions."""
    app = QApplication.instance() or QApplication(sys.argv)

    row = TrialRowWidget(
        trial_id="L1",
        name="Dynamic 1.qtm",
        metadata="315 frames • 100 Hz",
        status="READY",
    )
    # Initially without events
    assert "Auto-Label" in row._events_btn.text()

    # Apply event info
    events_info = load_trial_events(SAMPLE_SESSION_DIR, "Dynamic 1.qtm")
    row.set_events_info(events_info)
    assert f"{events_info['total_events']}" in row._events_btn.text()

    # Test signal emission
    clicked_files = []
    row.view_events_clicked.connect(lambda f: clicked_files.append(f))
    row._events_btn.click()
    assert len(clicked_files) == 1
    assert clicked_files[0] == "Dynamic 1.qtm"

    print(f"[PASS] 4. TrialRowWidget event button and view_events_clicked signal verified")


def test_dynamic_analysis_page_auto_events():
    """Verify DynamicAnalysisPage has all auto event labeling controls and integrates them."""
    app = QApplication.instance() or QApplication(sys.argv)

    page = DynamicAnalysisPage()
    assert os.path.exists(SAMPLE_SESSION_XML), f"Session XML not found: {SAMPLE_SESSION_XML}"
    page.load_session(SAMPLE_SESSION_XML)

    # 1. Header controls
    assert hasattr(page, "_auto_event_btn"), "Missing _auto_event_btn in DynamicAnalysisPage"
    assert hasattr(page, "_events_badge"), "Missing _events_badge in DynamicAnalysisPage"
    assert "Events:" in page._events_badge.text()
    assert page._auto_event_btn.text().strip() != ""
    print(f"[PASS] 5a. DynamicAnalysisPage header controls present (badge: {page._events_badge.text()})")

    # 2. Options checkbox
    assert hasattr(page, "_opt_auto_events"), "Missing _opt_auto_events in DynamicAnalysisPage"
    assert page._opt_auto_events.isChecked() is True
    print("[PASS] 5b. DynamicAnalysisPage auto-detect gait events checkbox verified")

    # 3. Bottom action button
    assert hasattr(page, "_auto_label_action_btn"), "Missing _auto_label_action_btn in DynamicAnalysisPage"
    assert page._auto_label_action_btn.text().strip() != ""
    print(f"[PASS] 5c. DynamicAnalysisPage bottom action button verified ({page._auto_label_action_btn.text()})")

    # 4. Trial rows loaded with event info
    row = page._trial_rows.get("Dynamic 1.qtm")
    assert row is not None
    assert row.events_info is not None
    assert row.events_info["total_events"] > 0
    print(f"[PASS] 5d. TrialRowWidget in DynamicAnalysisPage loaded events: {row._events_btn.text()}")

    # 5. Test queue construction for Auto-Labeling
    page._deselect_all_trials()
    page._trial_rows["Dynamic 1.qtm"].set_selected(True)
    page._trial_rows["Dynamic 2.qtm"].set_selected(True)
    page._on_auto_label_clicked()
    assert len(page._processing_queue) == 1  # 1 remaining because 1 popped immediately
    assert page._current_task_type == "auto_event"
    assert not page._proc_panel.isHidden()
    assert page._process_btn.isEnabled() is False
    assert page._auto_label_action_btn.isEnabled() is False

    # Cancel to cleanup
    page._on_cancel_processing()
    assert not page._processing_queue
    assert page._process_btn.isEnabled() is True
    assert page._auto_label_action_btn.isEnabled() is True
    print("[PASS] 5e. DynamicAnalysisPage auto-label queue execution and cancellation verified")


if __name__ == "__main__":
    print("=" * 70)
    print("  RUNNING AUTO EVENT LABELING GUI TEST SUITE")
    print("=" * 70)
    test_event_service_loading()
    test_event_details_dialog()
    test_trial_row_event_widget()
    test_dynamic_analysis_page_auto_events()
    print("=" * 70)
    print("  ALL AUTO EVENT GUI TESTS PASSED SUCCESSFULLY! [OK]")
    print("=" * 70)
    os._exit(0)
