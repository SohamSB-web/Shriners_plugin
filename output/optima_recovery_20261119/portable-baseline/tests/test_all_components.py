# -*- coding: utf-8 -*-
"""
End-to-End Verification Test for Shriners Gait Analysis Platform
Tests UI components, Sidebar icons, WorkflowBar, Force Plate Dialog,
Dynamic Analysis execution pipeline, Case Presentation loading, and signal wiring.
"""

import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Register Conda Library/bin on Windows for DLLs
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

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from app.models.data_models import AppSettings
from app.services.settings_service import SettingsService
from app.ui.main_window import MainWindow
from app.ui.widgets.force_plate_dialog import ForcePlateConfigDialog

SAMPLE_DIR = (
    PROJECT_ROOT
    / "Shriners_Gait_Model_PAF_v1.0"
    / "Shriners_Gait_Model_PAF_v1.0"
    / "Data"
    / "Shriners_test_002"
    / "2025-02-21_0003"
)
SAMPLE_SESSION_XML = str(SAMPLE_DIR / "session.xml")
SAMPLE_C3D_FILE = str(SAMPLE_DIR / "Dynamic 1.c3d")


def run_all_tests():
    print("=" * 70)
    print("  RUNNING COMPREHENSIVE SHRINERS PLATFORM E2E VERIFICATION")
    print("=" * 70)

    # 1. QApplication instance
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    settings = SettingsService().load_app_settings()
    window = MainWindow(settings=settings)
    assert window is not None, "Failed to create MainWindow"
    print("[PASS] 1. MainWindow initialized successfully")

    # 2. Sidebar Navigation Tests
    pages_to_test = [
        "static_analysis",
        "dynamic_analysis",
        "case_presentation",
        "dashboard",
        "patients",
        "qtm",
        "settings",
    ]
    for page_key in pages_to_test:
        window._navigate_to(page_key)
        curr = window._pages.currentWidget()
        expected = window._page_map[page_key]
        assert curr == expected, f"Navigation to {page_key} failed"
        assert window._sidebar._buttons[page_key].property("active") is True, f"Sidebar button for {page_key} not active"
    print(f"[PASS] 2. Sidebar navigation verified for all {len(pages_to_test)} pages")

    # 3. WorkflowBar Navigation & Styling Tests
    wf = window._workflow_bar
    wf.set_active_stage("static_analysis")
    assert wf._current_stage == "static_analysis"
    wf.mark_completed("static_analysis")
    assert "static_analysis" in wf._completed_stages

    wf.set_active_stage("dynamic_analysis")
    assert wf._current_stage == "dynamic_analysis"
    assert "2" in wf._buttons["dynamic_analysis"].text()
    assert "✓" in wf._buttons["static_analysis"].text()
    print("[PASS] 3. WorkflowBar stage progression and visual checkmarks verified")

    # 4. Force Plate Configuration Dialog Tests
    assert os.path.exists(SAMPLE_C3D_FILE), f"C3D sample not found: {SAMPLE_C3D_FILE}"
    fp_dialog = ForcePlateConfigDialog(
        session_dir=str(SAMPLE_DIR),
        trial_filename="Dynamic 1.qtm",
        current_left="FP0",
        current_right="0",
        parent=window,
    )
    assert fp_dialog is not None
    left_p, right_p, pdata = fp_dialog.get_assignment()
    assert left_p == "FP0"
    assert "FP0" in pdata
    print(f"[PASS] 4. ForcePlateConfigDialog loaded C3D platforms: {list(pdata.keys())}, Left={left_p}, Right={right_p}")

    # 5. Dynamic Analysis Page Tests with Force Plate Integration
    dyn_page = window._dynamic_page
    assert os.path.exists(SAMPLE_SESSION_XML), f"Session XML not found: {SAMPLE_SESSION_XML}"
    dyn_page.load_session(SAMPLE_SESSION_XML)
    trial_count = len(dyn_page._trial_rows)
    assert trial_count > 0, f"Expected trials to load, found {trial_count}"
    print(f"[PASS] 5a. DynamicAnalysisPage loaded {trial_count} dynamic trials")

    # Apply force plate config to DynamicAnalysisPage
    cfg = {
        "left_plate": "FP0",
        "right_plate": "0",
        "payload": pdata,
        "apply_to_all": True,
    }
    dyn_page._on_fp_config_saved("Dynamic 1.qtm", cfg)
    assert dyn_page._force_plate_configs.get("Dynamic 1.qtm") == cfg
    assert "Left=FP0" in dyn_page._fp_badge.text()
    print(f"[PASS] 5b. Force plate configuration applied to DynamicAnalysisPage (badge: {dyn_page._fp_badge.text()})")

    # Verify interactive force plate toggle
    dyn_page._opt_interactive_fp.setChecked(True)
    assert dyn_page._opt_interactive_fp.isChecked() is True
    dyn_page._opt_interactive_fp.setChecked(False)
    assert dyn_page._opt_interactive_fp.isChecked() is False
    print("[PASS] 5c. Force plate interactive prompt toggle verified")

    # 6. Pipeline Transitions
    # Static -> Dynamic transition
    window._on_static_to_dynamic(str(SAMPLE_DIR), "Static 1.c3d")
    assert window._pages.currentWidget() == window._dynamic_page
    assert "static_analysis" in window._workflow_bar._completed_stages
    print("[PASS] 6a. Static -> Dynamic pipeline transition verified")

    # Dynamic -> Presentation transition
    window._on_dynamic_to_presentation(str(SAMPLE_DIR))
    assert window._pages.currentWidget() == window._presentation_page
    assert "dynamic_analysis" in window._workflow_bar._completed_stages
    print("[PASS] 6b. Dynamic -> Case Presentation pipeline transition verified")

    # 7. Case Presentation Page Trials & Plot Rendering
    pres_page = window._presentation_page
    assert len(pres_page._trial_data) > 0, "Presentation page failed to load trials"
    print(f"[PASS] 7a. CasePresentationPage loaded {len(pres_page._trial_data)} trials: {list(pres_page._trial_data.keys())}")

    # Switch categories to ensure no rendering exceptions
    category_keys = [
        "kinematics",
        "sagittal_kinetics",
        "coronal_kinetics",
        "emg",
        "foot_kinematics",
        "muscle_length",
        "muscle_velocity",
    ]
    for cat in category_keys:
        pres_page._sidebar._on_cat_clicked(cat)
        assert pres_page._current_category == cat
    print(f"[PASS] 7b. CasePresentationPage plot category switching verified for all {len(category_keys)} categories")

    # Test Bilateral / Left / Right side toggles
    for side in ["L", "R", "LR"]:
        pres_page._on_side_changed(side)
        assert pres_page._current_side == side
    print("[PASS] 7c. CasePresentationPage limb display toggling (L, R, LR) verified")

    # 8. Settings & Theme Toggle Tests
    settings_page = window._settings_page
    assert settings_page is not None
    # Toggle Dark Mode
    window._apply_theme(True)
    assert window._settings.dark_mode is True
    # Toggle Light Mode
    window._apply_theme(False)
    assert window._settings.dark_mode is False
    print("[PASS] 8. Settings and live theme switching verified (Dark/Light)")

    # 9. QTM Bridge Status Update Tests
    window._on_qtm_connection(True)
    assert window._header._connection._status == "connected"
    window._on_qtm_connection(False)
    assert window._header._connection._status == "disconnected"
    print("[PASS] 9. QTM Bridge connection indicators and signal wiring verified")

    print("=" * 70)
    print("  ALL E2E VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
