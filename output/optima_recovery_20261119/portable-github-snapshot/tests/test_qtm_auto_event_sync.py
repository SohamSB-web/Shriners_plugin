# -*- coding: utf-8 -*-
"""
Test Suite: Live Automatic QTM Timeline Event Synchronization to Dynamic Analysis Page.

Tests:
1. Label normalization for QTM event variants (R_STRIKE, Right Foot Off, etc.).
2. Signature detection and automated synchronization in sync_qtm_events_to_session().
3. DynamicAnalysisPage live sync integration (timer, file watcher, trial row update, events badge).
4. Prevention of unnecessary disk writes when QTM events are already identical.
5. Trial matching and isolation logic between QTM active measurement and session trials.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

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

from PySide6.QtWidgets import QApplication
from app.services.event_service import (
    normalize_qtm_event_label,
    fetch_events_from_qtm,
    sync_qtm_events_to_session,
    save_trial_events,
    load_trial_events,
)
from app.ui.pages.dynamic_analysis_page import DynamicAnalysisPage


def test_qtm_label_normalization():
    print("--- 1. Testing normalize_qtm_event_label ---")
    assert normalize_qtm_event_label("Right Foot Strike") == "RSTRIKE"
    assert normalize_qtm_event_label("R_Strike") == "RSTRIKE"
    assert normalize_qtm_event_label("AUTO_RHS") == "RSTRIKE"
    assert normalize_qtm_event_label("RHS") == "RSTRIKE"
    assert normalize_qtm_event_label("RSTRIKE") == "RSTRIKE"

    assert normalize_qtm_event_label("Right Foot Off") == "ROFF"
    assert normalize_qtm_event_label("R_Off") == "ROFF"
    assert normalize_qtm_event_label("AUTO_ROF") == "ROFF"
    assert normalize_qtm_event_label("ROF") == "ROFF"
    assert normalize_qtm_event_label("ROFF") == "ROFF"

    assert normalize_qtm_event_label("Left Foot Strike") == "LSTRIKE"
    assert normalize_qtm_event_label("L_Strike") == "LSTRIKE"
    assert normalize_qtm_event_label("AUTO_LHS") == "LSTRIKE"
    assert normalize_qtm_event_label("LHS") == "LSTRIKE"
    assert normalize_qtm_event_label("LSTRIKE") == "LSTRIKE"

    assert normalize_qtm_event_label("Left Foot Off") == "LOFF"
    assert normalize_qtm_event_label("L_Off") == "LOFF"
    assert normalize_qtm_event_label("AUTO_LOF") == "LOFF"
    assert normalize_qtm_event_label("LOF") == "LOFF"
    assert normalize_qtm_event_label("LOFF") == "LOFF"

    print("✓ All QTM event label variations normalized successfully.")


def test_sync_qtm_events_to_session_detection():
    print("--- 2. Testing sync_qtm_events_to_session Detection & Update ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        s_dir = Path(tmpdir)
        trial_fname = "Dynamic 1.qtm"

        # Initially save 2 events for Dynamic 1
        initial_events = [
            {"frame": 100, "label": "RSTRIKE"},
            {"frame": 150, "label": "LOFF"},
        ]
        save_trial_events(s_dir, trial_fname, initial_events)

        # Mock fetch_events_from_qtm returning 4 events for Dynamic 1 (user added events in QTM)
        mock_qtm_events = [
            {"frame": 100, "label": "RSTRIKE", "time": 1.0, "relative_frame": 100, "side": "R", "type": "STRIKE"},
            {"frame": 150, "label": "LOFF", "time": 1.5, "relative_frame": 150, "side": "L", "type": "OFF"},
            {"frame": 200, "label": "LSTRIKE", "time": 2.0, "relative_frame": 200, "side": "L", "type": "STRIKE"},
            {"frame": 250, "label": "ROFF", "time": 2.5, "relative_frame": 250, "side": "R", "type": "OFF"},
        ]
        mock_meta = {"source": "qtm_timeline", "frame_rate": 100.0, "active_trial": "Dynamic 1"}

        with patch("app.services.event_service.fetch_events_from_qtm") as mock_fetch:
            mock_fetch.return_value = (True, "Retrieved 4 events", "Dynamic 1.qtm", mock_qtm_events, mock_meta)

            # Sync check (force=False): should detect change and update!
            updated, msg, matched, events, ev_info = sync_qtm_events_to_session(
                session_dir=s_dir,
                trial_filenames=["Dynamic 1.qtm", "Dynamic 2.qtm"],
                force=False,
            )

            assert updated is True, "Expected updated=True since QTM had 4 events and session had 2"
            assert matched == "Dynamic 1.qtm"
            assert len(events) == 4
            assert ev_info["total_events"] == 4

            # Verify saved on disk
            reloaded = load_trial_events(s_dir, trial_fname)
            assert reloaded is not None
            assert reloaded["total_events"] == 4
            assert reloaded["r_hs"] == 1
            assert reloaded["l_hs"] == 1
            assert reloaded["r_to"] == 1
            assert reloaded["l_to"] == 1

            # Run again with same events: should NOT update because signatures match!
            updated_again, msg_again, _, _, _ = sync_qtm_events_to_session(
                session_dir=s_dir,
                trial_filenames=["Dynamic 1.qtm", "Dynamic 2.qtm"],
                force=False,
            )
            assert updated_again is False, "Expected updated=False because events are already in sync"
            assert "already in sync" in msg_again

            # With force=True, should update anyway
            updated_forced, _, _, _, _ = sync_qtm_events_to_session(
                session_dir=s_dir,
                trial_filenames=["Dynamic 1.qtm", "Dynamic 2.qtm"],
                force=True,
            )
            assert updated_forced is True, "Expected updated=True when force=True"

    print("✓ sync_qtm_events_to_session signature detection and conditional saving passed.")


def test_dynamic_page_live_sync_integration():
    print("--- 3. Testing DynamicAnalysisPage Live QTM Sync Integration ---")
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    with tempfile.TemporaryDirectory() as tmpdir:
        s_dir = Path(tmpdir)
        session_xml = s_dir / "session.xml"
        session_xml.write_text("<Session></Session>", encoding="utf-8")

        # Create dummy trial files
        (s_dir / "Dynamic 1.qtm").write_bytes(b"dummy")
        (s_dir / "Dynamic 2.qtm").write_bytes(b"dummy")

        page = DynamicAnalysisPage()
        page.load_session(str(session_xml))

        # Check UI components
        assert hasattr(page, "_sync_qtm_btn"), "DynamicAnalysisPage must have _sync_qtm_btn"
        assert hasattr(page, "_qtm_sync_timer"), "DynamicAnalysisPage must have _qtm_sync_timer"
        assert hasattr(page, "_fs_watcher"), "DynamicAnalysisPage must have _fs_watcher"
        assert page._qtm_sync_timer.interval() == 1200, "Sync timer interval should be 1200ms"

        # Check rows created
        assert "Dynamic 1.qtm" in page._trial_rows
        assert "Dynamic 2.qtm" in page._trial_rows

        row1 = page._trial_rows["Dynamic 1.qtm"]
        assert row1._status == "READY"

        # Now simulate a QTM event change detected by _poll_qtm_events_sync
        mock_qtm_events = [
            {"frame": 120, "label": "RSTRIKE", "time": 1.2, "relative_frame": 120, "side": "R", "type": "STRIKE"},
            {"frame": 180, "label": "ROFF", "time": 1.8, "relative_frame": 180, "side": "R", "type": "OFF"},
        ]
        mock_meta = {"source": "qtm_timeline", "frame_rate": 100.0, "active_trial": "Dynamic 1"}

        with patch("app.services.event_service.fetch_events_from_qtm") as mock_fetch:
            mock_fetch.return_value = (True, "Retrieved 2 events", "Dynamic 1.qtm", mock_qtm_events, mock_meta)

            # Trigger poll
            page._poll_qtm_events_sync()

            # Dynamic 1 row should now have events and status "EVENTS LABELED"
            assert row1._events_info is not None, "Row 1 should have events_info populated"
            assert row1._events_info["total_events"] == 2
            assert row1._status == "EVENTS LABELED", f"Row 1 status should be EVENTS LABELED, got {row1._status}"
            assert "1/2 Labeled" in page._events_badge.text(), f"Events badge should reflect 1/2 labeled: {page._events_badge.text()}"

        page._qtm_sync_timer.stop()

    print("✓ DynamicAnalysisPage live sync integration passed.")


def test_no_active_measurement_handling():
    print("--- 4. Testing No Active Measurement Graceful Handling ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        s_dir = Path(tmpdir)
        # Mock fetch_events_from_qtm returning failure / no active trial
        with patch("app.services.event_service.fetch_events_from_qtm") as mock_fetch:
            mock_fetch.return_value = (False, "No measurement currently open in QTM.", None, [], {})
            updated, msg, matched, events, ev_info = sync_qtm_events_to_session(
                session_dir=s_dir,
                trial_filenames=["Dynamic 1.qtm"],
            )
            assert updated is False
            assert matched is None
            assert events == []
            assert ev_info is None
    print("✓ Graceful handling of no active measurement passed.")


def test_successful_empty_read_replaces_cached_events():
    with tempfile.TemporaryDirectory() as tmpdir:
        events = [{"frame": 120, "label": "RSTRIKE"}]
        save_trial_events(tmpdir, "Dynamic 2.qtm", events)
        with patch("app.services.event_service.fetch_events_from_qtm",
                   return_value=(True, "OK", "Dynamic 2.qtm", [], {"frame_rate": 100.0})), \
             patch("app.services.event_service.send_events_to_qtm") as send:
            updated, _, _, synced, info = sync_qtm_events_to_session(
                tmpdir, ["Dynamic 2.qtm"], force=False)
            assert updated and synced == [] and info["total_events"] == 0
            assert load_trial_events(tmpdir, "Dynamic 2.qtm")["total_events"] == 0
            send.assert_not_called()

if __name__ == "__main__":
    test_qtm_label_normalization()
    test_sync_qtm_events_to_session_detection()
    test_dynamic_page_live_sync_integration()
    test_no_active_measurement_handling()
    test_successful_empty_read_replaces_cached_events()
    print("\n✅ ALL QTM LIVE AUTO EVENT SYNC TESTS PASSED SUCCESSFULLY!")
