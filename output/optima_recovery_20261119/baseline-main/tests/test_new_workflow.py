# -*- coding: utf-8 -*-
"""
Verification test for the newly updated clinical workflow:
Dynamic Analysis -> Patients & Sessions (curate trials, import GCDs, set MR/Ave mode) -> MAC Case Presentation (generate custom graphs).
"""

import os
import shutil
import sys
from pathlib import Path

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

from PySide6.QtWidgets import QApplication
from app.models.data_models import AppSettings
from app.services.settings_service import SettingsService
from app.ui.main_window import MainWindow

SAMPLE_DIR = (
    PROJECT_ROOT
    / "Shriners_Gait_Model_PAF_v1.0"
    / "Shriners_Gait_Model_PAF_v1.0"
    / "Data"
    / "Claudia_123-20260928T142041Z-1-001"
    / "Claudia_123"
    / "2026-10-01_2"
)
SAMPLE_SESSION_XML = str(SAMPLE_DIR / "session.xml")


def test_full_new_workflow():
    print("=" * 70)
    print("  TESTING COMPLETE UPDATED WORKFLOW:")
    print("  Dynamic Analysis -> Patients & Sessions -> MAC Case Presentation")
    print("=" * 70)

    app = QApplication.instance() or QApplication(sys.argv)
    settings = SettingsService().load_app_settings()
    window = MainWindow(settings=settings)

    # 1. Load dynamic session in DynamicAnalysisPage
    dyn_page = window._dynamic_page
    dyn_page.load_session(SAMPLE_SESSION_XML)
    print("[PASS] 1. Dynamic session loaded")

    # 2. Simulate proceeding to Patients & Sessions
    dyn_page._on_view_presentation()
    assert window._pages.currentWidget() == window._patients, "Did not navigate to PatientsPage"
    assert "dynamic_analysis" in window._workflow_bar._completed_stages, "dynamic_analysis not marked completed"
    print("[PASS] 2. Transition from Dynamic Analysis to Patients & Sessions verified")

    # 3. Verify PatientsPage has session pre-loaded
    patients_page = window._patients
    assert patients_page.get_mrn() != "", f"MRN was not extracted: '{patients_page.get_mrn()}'"
    row0 = patients_page.session_rows[0]
    assert row0.session_info.directory != "", "Session directory was not set"
    print(f"[PASS] 3. PatientsPage auto-loaded MRN '{patients_page.get_mrn()}' and directory: {row0.session_info.directory}")

    # Verify GCD trial combos populated
    l1_text = row0.left_combos[0].currentText()
    r1_text = row0.right_combos[0].currentText()
    mr_l_text = row0.mr_left_combo.currentText()
    mr_r_text = row0.mr_right_combo.currentText()
    print(f"       Combos: L1='{l1_text}', R1='{r1_text}', MR_L='{mr_l_text}', MR_R='{mr_r_text}'")
    assert l1_text != "--", "L1 combo was not populated with GCD files"
    assert r1_text != "--", "R1 combo was not populated with GCD files"

    # 4. Test GCD import capability into session folder
    # Create a temporary GCD file to simulate external import
    temp_dir = PROJECT_ROOT / "scratch"
    temp_dir.mkdir(exist_ok=True)
    temp_gcd = temp_dir / "ImportedTest_Trial.GCD"
    # Copy from an existing GCD
    from app.services.session_organizer import find_all_gcd_files, get_gcd_dir
    gcds = find_all_gcd_files(SAMPLE_DIR)
    sample_gcd = gcds[0]
    shutil.copy2(sample_gcd, temp_gcd)

    # Directly verify import logic into GCD subfolder
    dest_path = get_gcd_dir(row0.session_info.directory) / temp_gcd.name
    shutil.copy2(temp_gcd, dest_path)
    row0._refresh_gcds()
    # Check that the new GCD file is in the combo options
    all_items = [row0.left_combos[0].itemText(i) for i in range(row0.left_combos[0].count())]
    assert "ImportedTest_Trial" in all_items, f"Imported trial not found in combo items: {all_items}"
    print("[PASS] 4. GCD file addition and directory refresh verified")

    # Clean up temp files
    if dest_path.exists():
        dest_path.unlink()
    if temp_gcd.exists():
        temp_gcd.unlink()

    # 5. Set session metadata and display mode (Average)
    row0.date_edit.setText("02/21/2025")
    row0.study_combo.setCurrentText("Follow-up")
    row0.activity_combo.setCurrentText("Walk")
    row0.orthosis_edit.setText("AFO")
    row0.assist_edit.setText("None")
    patients_page.ave_radio.setChecked(True)
    assert patients_page.get_display_mode() == "Ave"
    print("[PASS] 5. Metadata and Display Mode ('Ave') configured")

    # 6. Click 'Save & Proceed to Presentation'
    patients_page.proceed_btn.click()
    assert window._pages.currentWidget() == window._presentation_page, "Did not navigate to CasePresentationPage"
    assert "patients" in window._workflow_bar._completed_stages, "patients not marked completed"
    print("[PASS] 6. Save & Proceed navigated to CasePresentationPage")

    # 7. Verify Case Presentation graphs populated according to PatientsPage data
    pres_page = window._presentation_page
    assert pres_page._display_mode == "Ave", f"Expected display_mode 'Ave', got {pres_page._display_mode}"
    assert "Mean" in pres_page._active_trial_filter, "'Mean' pill should be active in Ave mode"
    assert len(pres_page._trial_data) > 0, "No trials loaded in Case Presentation"
    print(f"[PASS] 7. CasePresentationPage generated graphs with {len(pres_page._trial_data)} trials in Ave mode!")

    # 8. Test MR mode
    patients_page.mr_radio.setChecked(True)
    patients_page.proceed_btn.click()
    assert pres_page._display_mode == "MR"
    assert pres_page._mr_left_key is not None
    print(f"[PASS] 8. MR mode verified with MR Left key: {pres_page._mr_left_key}")

    print("=" * 70)
    print("  ALL WORKFLOW TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    test_full_new_workflow()
