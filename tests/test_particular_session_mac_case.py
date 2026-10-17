# -*- coding: utf-8 -*-
"""
Verification test for Opening MAC Case for Particular Sessions:
1. SessionRow 'View MAC Case ↗' button presence and signal emission
2. PatientsPage signal forwarding (open_session_presentation)
3. MainWindow slot integration (_on_open_single_session_presentation)
4. CasePresentationPage Session Switcher dropdown and per-session loading
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Register Conda Library/bin on Windows for DLLs
if sys.platform == "win32":
    import ctypes
    _sys32_icu = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "icuuc.dll")
    if os.path.exists(_sys32_icu):
        try:
            ctypes.WinDLL(_sys32_icu)
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
from app.models.data_models import SessionInfo
from app.ui.pages.patients_page import SessionRow, PatientsPage
from app.ui.pages.case_presentation_page import CasePresentationPage
from app.ui.main_window import MainWindow


def test_particular_session_workflow():
    app = QApplication.instance() or QApplication(sys.argv)

    print("============================================================")
    print("TESTING PARTICULAR SESSION OPENING IN MAC CASE PRESENTATION")
    print("============================================================")

    # 1. Test SessionRow 'View MAC Case' button & signal
    print("\n--- 1. Testing SessionRow 'View MAC Case' button ---")
    row_0 = SessionRow(0)
    row_1 = SessionRow(1)
    assert hasattr(row_0, "view_case_btn"), "SessionRow missing view_case_btn"
    assert "View MAC Case" in row_0.view_case_btn.text()

    captured_row = []
    row_1.open_presentation_requested.connect(lambda idx: captured_row.append(idx))
    row_1.view_case_btn.click()
    assert len(captured_row) == 1 and captured_row[0] == 1, f"Expected row 1, got {captured_row}"
    print("[PASS] SessionRow 1 emitted open_presentation_requested(1) on click!")

    # 2. Test PatientsPage signal forwarding
    print("\n--- 2. Testing PatientsPage signal forwarding ---")
    patients_page = PatientsPage()
    assert hasattr(patients_page, "open_session_presentation")

    captured_page_signal = []
    patients_page.open_session_presentation.connect(lambda idx: captured_page_signal.append(idx))

    # Click view_case_btn on Session 2 (index 1)
    patients_page.session_rows[1].view_case_btn.click()
    assert len(captured_page_signal) == 1 and captured_page_signal[0] == 1
    print("[PASS] PatientsPage successfully forwarded open_session_presentation(1)!")

    # Add a 3rd session row and test its button
    patients_page._add_session_row()
    assert len(patients_page.session_rows) == 3
    patients_page.session_rows[2].view_case_btn.click()
    assert len(captured_page_signal) == 2 and captured_page_signal[1] == 2
    print("[PASS] Newly added Session 3 also connects and emits open_session_presentation(2)!")

    # 3. Test CasePresentationPage multi-session handling & dropdown
    print("\n--- 3. Testing CasePresentationPage Session Switcher ---")
    pres_page = CasePresentationPage()
    pres_page.show()
    app.processEvents()
    assert hasattr(pres_page, "_session_combo")

    sess1 = SessionInfo(
        directory=r"C:\Mock\Session1",
        analysis_date="2026-10-01",
        study_type="Pre-Op",
        activity_type="Barefoot",
    )
    sess2 = SessionInfo(
        directory=r"C:\Mock\Session2",
        analysis_date="2026-10-15",
        study_type="Post-Op",
        activity_type="Orthosis",
    )
    sess3 = SessionInfo(
        directory=r"C:\Mock\Session3",
        analysis_date="2026-11-01",
        study_type="Follow-Up",
        activity_type="Barefoot",
    )

    # 3a. Single session -> dropdown should be hidden
    pres_page.load_session_data([sess1], active_session_index=0)
    app.processEvents()
    assert pres_page._session_combo.isHidden(), "Dropdown should be hidden for single session"
    assert pres_page._session_date == "2026-10-01"
    assert pres_page._study_type == "Pre-Op"
    print("[PASS] Single session: Session switcher dropdown is hidden cleanly.")

    # 3b. Multiple sessions, open Session 2 directly (index 1)
    pres_page.load_session_data([sess1, sess2, sess3], active_session_index=1)
    app.processEvents()
    assert not pres_page._session_combo.isHidden(), "Dropdown should be visible for multiple sessions"
    assert pres_page._session_combo.count() == 3
    assert pres_page._session_combo.currentIndex() == 1
    assert pres_page._session_date == "2026-10-15"
    assert pres_page._study_type == "Post-Op"
    assert pres_page._activity_type == "Orthosis"
    print("[PASS] Multiple sessions: Direct open of Session 2 loaded Session 2 metadata & selected item 1.")

    # 3c. Switch to Session 3 via in-page dropdown
    pres_page._session_combo.setCurrentIndex(2)
    app.processEvents()
    assert pres_page._session_date == "2026-11-01"
    assert pres_page._study_type == "Follow-Up"
    assert pres_page._activity_type == "Barefoot"
    print("[PASS] Switching in-page dropdown to Session 3 dynamically loaded Session 3 data!")

    # 4. Test MainWindow full integration
    print("\n--- 4. Testing MainWindow integration ---")
    main_win = MainWindow()
    main_win.show()
    app.processEvents()
    # Mock sessions in main_win._patients
    main_win._patients.session_rows[0].date_edit.setText("2026-10-01")
    main_win._patients.session_rows[0].study_combo.setCurrentText("Pre-op")
    main_win._patients.session_rows[1].date_edit.setText("2026-10-15")
    main_win._patients.session_rows[1].study_combo.setCurrentText("Post-op")

    # Click 'View MAC Case' on Session 2 (row 1)
    main_win._patients.session_rows[1].view_case_btn.click()
    app.processEvents()

    # Verify that Case Presentation page is now the active stacked widget
    assert main_win._pages.currentWidget() == main_win._presentation_page
    assert not main_win._presentation_page._session_combo.isHidden()
    assert main_win._presentation_page._session_combo.currentIndex() == 1
    assert main_win._presentation_page._study_type == "Post-op"
    print("[PASS] Clicking 'View MAC Case' on Session 2 seamlessly navigated to MAC Case Presentation with Session 2 active!")

    print("\n============================================================")
    print("ALL PARTICULAR SESSION TESTS PASSED PERFECTLY!")
    print("============================================================")
    main_win.close()


if __name__ == "__main__":
    test_particular_session_workflow()
    sys.exit(0)
