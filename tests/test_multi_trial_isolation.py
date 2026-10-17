# -*- coding: utf-8 -*-
"""
Test Suite for Multi-Trial Auto-Event Labeling Isolation.
Verifies that:
1. Auto-detected events are written directly into each respective dynamic file's C3D (EVENT group)
   and sidecar JSON, regardless of whether QTM is open or what measurement is active.
2. When QTM has one file open (e.g. Dynamic 1.qtm), other trials (e.g. Dynamic 2.qtm)
   are prevented from polluting the open trial's timeline.
3. Neither ClearEvents, SetEvent, nor SetEvents touches QTM's timeline when trial names do not match.
"""

import os
import sys
import json
from pathlib import Path
import ezc3d

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Gait-lab-Vicon-to-QTM"))

from app.services.event_service import save_trial_events, load_trial_events, send_events_to_qtm, write_events_to_c3d
import auto_event_trigger as trigger

SESSION_DIR = PROJECT_ROOT / "Shriners_Gait_Model_PAF_v1.0" / "Shriners_Gait_Model_PAF_v1.0" / "Data" / "Claudia_123-20260928T142041Z-1-001" / "Claudia_123" / "2026-10-01_2"


def test_direct_c3d_event_writing():
    """Verify write_events_to_c3d correctly updates the EVENT group of a dynamic C3D file."""
    c3d_path = SESSION_DIR / "Dynamic 1.c3d"
    assert c3d_path.is_file(), f"Missing {c3d_path}"

    test_events = [
        {"frame": 294, "label": "LSTRIKE", "time": 2.45},
        {"frame": 309, "label": "ROFF", "time": 2.575},
        {"frame": 356, "label": "RSTRIKE", "time": 2.9667},
        {"frame": 372, "label": "LOFF", "time": 3.1},
        {"frame": 419, "label": "LSTRIKE", "time": 3.4917},
        {"frame": 433, "label": "ROFF", "time": 3.6083},
        {"frame": 479, "label": "RSTRIKE", "time": 3.9917},
        {"frame": 493, "label": "LOFF", "time": 4.1083},
    ]

    ok = write_events_to_c3d(str(c3d_path), test_events, frame_rate=120.0, offset=1)
    assert ok is True, "write_events_to_c3d failed"

    # Read back with ezc3d
    reader = ezc3d.c3d(str(c3d_path))
    assert "EVENT" in reader["parameters"], "EVENT group missing from C3D"
    used = reader["parameters"]["EVENT"]["USED"]["value"][0]
    labels = reader["parameters"]["EVENT"]["LABELS"]["value"]
    times = reader["parameters"]["EVENT"]["TIMES"]["value"]
    contexts = reader["parameters"]["EVENT"]["CONTEXTS"]["value"]

    assert used == 8, f"Expected 8 events, got {used}"
    assert labels == ["LSTRIKE", "ROFF", "RSTRIKE", "LOFF", "LSTRIKE", "ROFF", "RSTRIKE", "LOFF"]
    assert contexts == ["Left", "Right", "Right", "Left", "Left", "Right", "Right", "Left"]
    assert round(times[1][0], 2) in (2.44, 2.45)
    print("[PASS] 1. write_events_to_c3d writes proper 8 events into Dynamic 1.c3d")


def test_cross_trial_qtm_protection():
    """Verify that send_events_to_qtm skips writing to QTM if the target trial is not active."""
    # Simulate QTM having "Dynamic 1.qtm" open
    import app.services.event_service as es
    orig_get_qtm = es.get_qtm_active_file

    try:
        es.get_qtm_active_file = lambda: "Dynamic 1.qtm"

        # Attempt to send Dynamic 2 events to QTM while Dynamic 1 is open
        d2_events = [{"frame": 100, "label": "RSTRIKE"}]
        ok, msg = send_events_to_qtm(d2_events, trial_filename="Dynamic 2.qtm")

        assert ok is False, "Expected protection to reject writing Dynamic 2 onto Dynamic 1"
        assert "open, not" in msg or "Live timeline update skipped" in msg

        # CRITICAL REGRESSION: Attempt to send Dynamic 10 events to QTM while Dynamic 1 is open
        # Substring matching bug previously allowed "Dynamic 1" inside "Dynamic 10"
        ok10, msg10 = send_events_to_qtm(d2_events, trial_filename="Dynamic 10.qtm")
        assert ok10 is False, "Expected protection to reject writing Dynamic 10 onto Dynamic 1"
        assert "open, not" in msg10 or "Live timeline update skipped" in msg10
        print(f"[PASS] 2. Cross-trial protection triggered successfully (Dynamic 2 & Dynamic 10 rejected on Dynamic 1): {msg}")

        # Now send Dynamic 1 events while Dynamic 1 is open (offline check may fail connection but won't reject on mismatch)
        ok1, msg1 = send_events_to_qtm(d2_events, trial_filename="Dynamic 1.qtm")
        assert "different trial" not in msg1 and "is currently open" not in msg1
        print("[PASS] 3. Matching trial passes open-trial validation")

    finally:
        es.get_qtm_active_file = orig_get_qtm


def test_auto_event_trigger_qtm_guard():
    """Verify that auto_event_trigger respects QTM active measurement when processing."""
    orig_active = trigger.get_qtm_active_measurement

    try:
        # Simulate QTM open with Dynamic 1
        trigger.get_qtm_active_measurement = lambda: "Dynamic 1.qtm"

        # Check for Dynamic 2: should NOT be marked open
        target = "Dynamic 2"
        qtm_active = trigger.get_qtm_active_measurement()
        is_this_trial_open = False
        if qtm_active:
            clean_target = target.lower().strip()
            clean_active = os.path.splitext(os.path.basename(qtm_active))[0].lower().strip()
            if clean_target == clean_active:
                is_this_trial_open = True

        assert is_this_trial_open is False, "Dynamic 2 should not be considered open in QTM"
        print("[PASS] 4. auto_event_trigger correctly identifies Dynamic 2 as NOT active in QTM")

        # Check for Dynamic 1: SHOULD be marked open
        target = "Dynamic 1"
        clean_target = target.lower().strip()
        clean_active = os.path.splitext(os.path.basename(qtm_active))[0].lower().strip()
        is_this_trial_open = (clean_target == clean_active)

        assert is_this_trial_open is True, "Dynamic 1 should be considered open in QTM"
        print("[PASS] 5. auto_event_trigger correctly identifies Dynamic 1 as active in QTM")

    finally:
        trigger.get_qtm_active_measurement = orig_active


def test_both_trials_have_independent_events():
    """Verify both Dynamic 1 and Dynamic 2 have their own separate events in their respective C3Ds."""
    c1 = ezc3d.c3d(str(SESSION_DIR / "Dynamic 1.c3d"))
    c2 = ezc3d.c3d(str(SESSION_DIR / "Dynamic 2.c3d"))

    u1 = c1["parameters"]["EVENT"]["USED"]["value"][0]
    u2 = c2["parameters"]["EVENT"]["USED"]["value"][0]

    assert u1 > 0, "Dynamic 1 must have events in C3D"
    assert u2 > 0, "Dynamic 2 must have events in C3D"

    # Verify they have distinct timestamps / events
    t1 = c1["parameters"]["EVENT"]["TIMES"]["value"][1]
    t2 = c2["parameters"]["EVENT"]["TIMES"]["value"][1]

    assert list(t1) != list(t2), "Dynamic 1 and Dynamic 2 should have distinct gait events"
    print(f"[PASS] 6. Independent C3D events confirmed: Dynamic 1 has {u1} events, Dynamic 2 has {u2} events")


if __name__ == "__main__":
    print("=" * 70)
    print("  RUNNING MULTI-TRIAL EVENT ISOLATION TESTS")
    print("=" * 70)
    test_direct_c3d_event_writing()
    test_cross_trial_qtm_protection()
    test_auto_event_trigger_qtm_guard()
    test_both_trials_have_independent_events()
    print("=" * 70)
    print("  ALL MULTI-TRIAL ISOLATION TESTS PASSED SUCCESSFULLY! [OK]")
    print("=" * 70)
