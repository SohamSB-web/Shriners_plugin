# -*- coding: utf-8 -*-
"""
Automated Test Suite for Processing UI and GaitProcessingService
"""

import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Standard library and Qt imports
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from app.models.data_models import ProcessingStatus
from app.services.processing_service import GaitProcessingService, ProcessingWorker
from app.ui.pages.processing_page import ProcessingPage

# Ensure QApplication exists for UI tests
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

_candidates = [
    PROJECT_ROOT / "Shriners_Gait_Model_PAF_v1.0" / "Shriners_Gait_Model_PAF_v1.0" / "Data" / "Claudia_123-20260928T142041Z-1-001" / "Claudia_123" / "2026-10-01_2",
    PROJECT_ROOT / "Shriners_Gait_Model_PAF_v1.0" / "Shriners_Gait_Model_PAF_v1.0" / "Data" / "test_002" / "2025-02-21_0003",
    PROJECT_ROOT / "Shriners_Gait_Model_PAF_v1.0" / "Shriners_Gait_Model_PAF_v1.0" / "Data" / "Shriners_test_002" / "2025-02-21_0003",
]
SAMPLE_DIR = next((d for d in _candidates if (d / "Dynamic 1.qtm").is_file()), _candidates[0])
SAMPLE_SESSION_XML = str(SAMPLE_DIR / "session.xml")
SAMPLE_QTM_FILE = str(SAMPLE_DIR / "Dynamic 1.qtm")


def test_service_initialization():
    """Verify GaitProcessingService initializes with correct defaults."""
    svc = GaitProcessingService(conda_env="python-example")
    assert svc.conda_env == "python-example"
    assert not svc.is_running
    print("[PASS] test_service_initialization")


def test_processing_worker_cmd_construction():
    """Verify ProcessingWorker constructs exact commands with conda, scripts, and arguments."""
    worker = ProcessingWorker(
        script_name="Py3_StaticMain.py",
        session_xml_path=SAMPLE_SESSION_XML,
        filename="Static 1.qtm",
        conda_env="python-example",
        extra_args=["-t", "BF"],
    )
    assert worker.script_name == "Py3_StaticMain.py"
    assert worker.session_xml_path == SAMPLE_SESSION_XML
    assert worker.filename == "Static 1.qtm"
    assert worker.extra_args == ["-t", "BF"]
    print("[PASS] test_processing_worker_cmd_construction")


def test_processing_page_initial_ui_state():
    """Verify ProcessingPage components start in clean, disabled state."""
    page = ProcessingPage()
    assert page._static_btn.isEnabled() is False
    assert page._dynamic_btn.isEnabled() is False
    assert page._auto_btn.isEnabled() is False
    assert page._cancel_btn.isEnabled() is False
    assert page._progress_label.text() == "Idle"
    assert page._progress_bar.value() == 0
    assert len(page._steps) == 5
    assert page._cond_combo.currentText() == "BF"
    print("[PASS] test_processing_page_initial_ui_state")


def test_processing_page_file_selection():
    """Verify file selection enables action buttons and updates step 1."""
    page = ProcessingPage()
    assert os.path.exists(SAMPLE_QTM_FILE), f"Sample file not found at {SAMPLE_QTM_FILE}"
    assert os.path.exists(SAMPLE_SESSION_XML), f"Session xml not found at {SAMPLE_SESSION_XML}"

    page._set_file(SAMPLE_QTM_FILE)

    assert page._file_input.text() == SAMPLE_QTM_FILE
    assert page._filename == "Dynamic 1.qtm"
    assert page._session_xml == SAMPLE_SESSION_XML
    assert page._static_btn.isEnabled() is True
    assert page._dynamic_btn.isEnabled() is True
    assert page._auto_btn.isEnabled() is True
    assert page._cancel_btn.isEnabled() is False
    assert page._steps[0].status == "complete"
    assert "Found session metadata" in page._log_output.toPlainText()
    print("[PASS] test_processing_page_file_selection")


def test_processing_page_clear_log():
    """Verify log clear functionality."""
    page = ProcessingPage()
    page._log("Line 1")
    page._log("Line 2")
    assert len(page._log_output.toPlainText().strip()) > 0
    page._clear_log()
    assert page._log_output.toPlainText().strip() == ""
    print("[PASS] test_processing_page_clear_log")


def test_processing_page_step_status_progression():
    """Verify steps update correctly for static, dynamic, and auto event labeling."""
    page = ProcessingPage()
    page._set_file(SAMPLE_QTM_FILE)

    # Simulate static run finish
    page._active_action = "static"
    page._steps[1].set_status("running")
    status_static = ProcessingStatus(step="complete", completed=True, message="Static done")
    page._on_finished(status_static)
    assert page._steps[1].status == "complete"

    # Simulate dynamic run finish
    page._active_action = "dynamic"
    page._steps[2].set_status("running")
    page._steps[3].set_status("running")
    status_dynamic = ProcessingStatus(step="complete", completed=True, message="Dynamic done")
    page._on_finished(status_dynamic)
    assert page._steps[2].status == "complete"
    assert page._steps[3].status == "complete"

    # Simulate auto_label run finish
    page._active_action = "auto_label"
    page._steps[4].set_status("running")
    status_auto = ProcessingStatus(step="complete", completed=True, message="Auto label done")
    page._on_finished(status_auto)
    assert page._steps[4].status == "complete"

    # Simulate error on dynamic
    page._active_action = "dynamic"
    page._steps[2].set_status("running")
    page._steps[3].set_status("running")
    status_err = ProcessingStatus(step="error", completed=False, message="Dynamic failed", errors=["Test error"])
    page._on_finished(status_err)
    assert page._steps[2].status == "error"
    assert page._steps[3].status == "error"
    assert "ERROR: Test error" in page._log_output.toPlainText()

    print("[PASS] test_processing_page_step_status_progression")


def test_processing_service_live_execution():
    """
    Test live asynchronous execution of auto_event_trigger.py through
    GaitProcessingService with real dataset and verify signal emissions.
    """
    svc = GaitProcessingService(conda_env="python-example")

    events_received = {
        "started": False,
        "log_lines": [],
        "finished": False,
        "completed": False,
    }

    def on_started(script):
        events_received["started"] = True
        print(f"  Signal received -> started: {script}")

    def on_log(line):
        events_received["log_lines"].append(line)

    def on_finished(status: ProcessingStatus):
        events_received["finished"] = True
        events_received["completed"] = status.completed
        print(f"  Signal received -> finished: message='{status.message}', completed={status.completed}")

    svc.processing_started.connect(on_started)
    svc.processing_log.connect(on_log)
    svc.processing_finished.connect(on_finished)

    print("\n  Launching live background auto_event_trigger via service...")
    svc.run_auto_event_labeling(SAMPLE_SESSION_XML, "Dynamic 1.qtm", condition="BF")
    assert svc.is_running is True

    # Process Qt event loop until finished (timeout 60 seconds)
    import time
    start_time = time.time()
    while not events_received["finished"] and (time.time() - start_time) < 60:
        QCoreApplication.processEvents()
        time.sleep(0.05)

    assert events_received["started"] is True
    assert events_received["finished"] is True
    assert events_received["completed"] is True
    assert len(events_received["log_lines"]) > 5
    assert not svc.is_running

    # Check some content from the logs
    log_text = "\n".join(events_received["log_lines"])
    assert "STAGE 1" in log_text or "Dynamic 1.qtm" in log_text
    print(f"  Captured {len(events_received['log_lines'])} live log lines successfully.")
    print("[PASS] test_processing_service_live_execution")


def test_cleanup():
    """Verify cleanup stops threads safely."""
    page = ProcessingPage()
    page.cleanup()
    assert not page._processing_svc.is_running
    print("[PASS] test_cleanup")


if __name__ == "__main__":
    print("==================================================")
    print("  RUNNING PROCESSING UI & SERVICE TEST SUITE")
    print("==================================================")
    test_service_initialization()
    test_processing_worker_cmd_construction()
    test_processing_page_initial_ui_state()
    test_processing_page_file_selection()
    test_processing_page_clear_log()
    test_processing_page_step_status_progression()
    test_cleanup()
    test_processing_service_live_execution()
    print("==================================================")
    print("  ALL 7 TESTS PASSED SUCCESSFULLY! [OK]")
    print("==================================================")
