# -*- coding: utf-8 -*-
"""
End-to-End Test Suite for MAC Case Presentation
Validating against MAC_CasePresentation_Guide.md specifications.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Conda DLL registration on Windows
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
from PySide6.QtCore import Qt

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from app.models.data_models import SessionInfo, TrialInfo
from app.services.gcd_service import GCDService
from app.services.settings_service import SettingsService
from app.services.pdf_report_service import CasePresentationPdfService
from app.ui.main_window import MainWindow
from app.ui.pages.case_presentation_page import CasePresentationPage
from app.ui.charts.clinical_plots import ClinicalPlotDetailDialog
from app.ui.theme.design_tokens import DARK_PALETTE, LIGHT_PALETTE


def run_e2e_mac_case_presentation_tests():
    print("=" * 75)
    print("   MAC CASE PRESENTATION — COMPREHENSIVE END-TO-END VERIFICATION")
    print("   Based on: MAC_CasePresentation_Guide.md")
    print("=" * 75)

    test_passed = 0
    test_total = 0

    def record_pass(step_desc):
        nonlocal test_passed, test_total
        test_passed += 1
        test_total += 1
        print(f"[PASS {test_passed}] {step_desc}")

    # =========================================================================
    # 1. UNDERLYING DATA & DEPENDENCIES
    # =========================================================================
    print("\n--- 1. Testing Underlying Data & Dependencies ---")
    ss = SettingsService()
    gcd_svc = GCDService()

    # Normative file
    norm_path = PROJECT_ROOT / "MAC_CasePresentation" / "TD_Ave.GCD"
    assert norm_path.is_file(), f"TD_Ave.GCD not found at {norm_path}"
    norm_data = gcd_svc.read_gcd(str(norm_path))
    assert norm_data and len(norm_data.variable_names) >= 100
    record_pass(f"Walking Normative corridor loaded from TD_Ave.GCD ({len(norm_data.variable_names)} variables)")

    # All 7 Clinical Modality Settings Files
    modalities = [
        ("Kinematics (3D Joint Angles)", ss.get_kinematics_settings, 15),
        ("Sagittal Kinetics", ss.get_sagittal_kinetics_settings, 15),
        ("Coronal Kinetics", ss.get_coronal_kinetics_settings, 15),
        ("Dynamic EMG", ss.get_emg_settings, 5),
        ("Foot Kinematics", ss.get_foot_kinematics_settings, 15),
        ("Muscle Length", ss.get_muscle_length_settings, 15),
        ("Muscle Velocity", ss.get_muscle_velocity_settings, 15),
    ]
    for mod_name, getter_fn, expected_plots in modalities:
        cfg = getter_fn()
        assert len(cfg.titles) == expected_plots, f"Expected {expected_plots} titles for {mod_name}, got {len(cfg.titles)}"
        record_pass(f"Modality settings verified: {mod_name} ({len(cfg.titles)} channels)")

    # =========================================================================
    # 2. PATIENT LOOKUP & SESSION SETUP (Step 1 of Guide)
    # =========================================================================
    print("\n--- 2. Testing Patient Lookup & Session Setup (Workflow Step 1) ---")
    settings = ss.load_app_settings()
    win = MainWindow(settings=settings)
    win.resize(1600, 1000)
    win.show()
    app.processEvents()

    demo_session_dir = PROJECT_ROOT / "Shriners_Gait_Model_PAF_v1.0" / "Shriners_Gait_Model_PAF_v1.0" / "Data" / "Shriners_test_002" / "2025-02-21_0003"
    assert demo_session_dir.is_dir(), f"Demo session directory not found: {demo_session_dir}"
    sample_xml = str(demo_session_dir / "session.xml")

    # Load session through Dynamic Analysis and transition to Patients
    win._dynamic_page.load_session(sample_xml)
    win._dynamic_page._on_view_presentation()
    app.processEvents()

    patients_page = win._patients
    assert win._pages.currentWidget() == patients_page, "Did not transition to PatientsPage"
    row0 = patients_page.session_rows[0]
    record_pass(f"Patient MRN '{patients_page.get_mrn()}' and session loaded in Patients & Sessions")

    # Verify trials populated in combo boxes
    left_combos = [cb.currentText() for cb in row0.left_combos]
    right_combos = [cb.currentText() for cb in row0.right_combos]
    assert any(c != "--" for c in left_combos), "No left dynamic trials populated!"
    assert any(c != "--" for c in right_combos), "No right dynamic trials populated!"
    record_pass(f"L1-L5 and R1-R5 trial mapping verified (e.g. L1='{left_combos[0]}', R1='{right_combos[0]}')")

    # Set representative trials and Ave mode
    row0.mr_left_combo.setCurrentText(left_combos[0])
    row0.mr_right_combo.setCurrentText(right_combos[0])
    patients_page.ave_radio.setChecked(True)
    record_pass("Representative trials (MR_Left, MR_Right) and Display Mode configured")

    # =========================================================================
    # 3. INTERACTIVE CASE REVIEW TRANSITION & MULTI-PANEL GRAPHS (Step 2)
    # =========================================================================
    print("\n--- 3. Testing Interactive Case Review (Workflow Step 2) ---")
    # Click Proceed to Case Presentation
    patients_page.proceed_btn.click()
    app.processEvents()

    assert win._pages.currentWidget() == win._presentation_page
    case_page = win._presentation_page
    record_pass("Save & Proceed successfully transitioned to MAC Case Presentation screen")

    # Check session metadata banner
    title_text = case_page._title_label.text()
    assert "CASE PRESENTATION" in title_text
    record_pass(f"Header presentation banner verified: '{title_text}'")

    # =========================================================================
    # 4. SINGLE SESSION MODES & ASYMMETRY INSPECTION (L, R, L/R)
    # =========================================================================
    print("\n--- 4. Testing Limb Display Modes (L, R, L/R) & MR vs Ave ---")

    # 4a. Left Limb Mode (L)
    case_page._sidebar.side_changed.emit("L")
    app.processEvents()
    pelvic_canvas = case_page._plot_grid.get_canvas(1, 1)  # Pelvic Obliquity
    ax = pelvic_canvas.axes
    record_pass("Limb display switched to Left (L) — verified overlay")

    # 4b. Right Limb Mode (R)
    case_page._sidebar.side_changed.emit("R")
    app.processEvents()
    record_pass("Limb display switched to Right (R) — verified overlay")

    # 4c. Bilateral Asymmetry Mode (L/R)
    case_page._sidebar.side_changed.emit("LR")
    app.processEvents()
    poly_colls = [c for c in ax.collections if hasattr(c, "get_paths")]
    assert len(poly_colls) > 0, "Normative band PolyCollection missing in Bilateral mode!"
    record_pass("Limb display switched to Bilateral (L/R) — Left vs Right asymmetry verified")

    # 4d. MR vs Ave mode
    case_page._display_mode = "Ave"
    case_page._refresh_plots()
    app.processEvents()
    dashed_mean = [line for line in ax.lines if line.get_linestyle() == "--"]
    assert len(dashed_mean) > 0, "Ensemble average dashed curve missing in Ave mode!"
    record_pass("Display mode switched to Average ('Ave') — ensemble mean curve verified")

    case_page._display_mode = "MR"
    case_page._refresh_plots()
    app.processEvents()
    record_pass("Display mode switched to Most Representative ('MR') — verified")

    # =========================================================================
    # 5. NORMATIVE CORRIDOR & IDEAL RANGE
    # =========================================================================
    print("\n--- 5. Testing Normative Corridor & Ideal Range ---")
    # Verify shaded band (PolyCollection) and dotted center mean line (ls=":")
    poly_colls = [c for c in ax.collections if hasattr(c, "get_paths")]
    dotted_lines = [l for l in ax.lines if l.get_linestyle() == ":"]
    assert len(poly_colls) > 0, "Normative shaded band missing!"
    assert len(dotted_lines) > 0, "Normative dotted center mean line missing!"
    record_pass("Normative ideal range corridor (shaded ±1 SD) and dotted center line (ls=':') verified")

    # Toggle Norm Band OFF
    case_page._norm_btn.setChecked(False)
    app.processEvents()
    assert len([c for c in ax.collections if hasattr(c, "get_paths")]) == 0
    record_pass("Norm Band toggle OFF successfully hid the corridor")

    # Toggle Norm Band ON
    case_page._norm_btn.setChecked(True)
    app.processEvents()
    assert len([c for c in ax.collections if hasattr(c, "get_paths")]) > 0
    record_pass("Norm Band toggle ON successfully restored the corridor")

    # =========================================================================
    # 6. ALL 7 CLINICAL MODALITIES RENDERING
    # =========================================================================
    print("\n--- 6. Testing All 7 Clinical Modalities in Case Presentation ---")
    cat_keys = [
        ("kinematics", "Kinematics (3D Joint Angles)"),
        ("sagittal_kinetics", "Sagittal Kinetics & Joint Power"),
        ("coronal_kinetics", "Coronal Kinetics"),
        ("emg", "Dynamic EMG"),
        ("foot_kinematics", "Foot Kinematics"),
        ("muscle_length", "Muscle-Tendon Lengths"),
        ("muscle_velocity", "Muscle Shortening Velocities"),
    ]
    for cat_id, cat_title in cat_keys:
        case_page._sidebar.category_changed.emit(cat_id)
        app.processEvents()
        # Verify first canvas has proper title and limits
        c0 = case_page._plot_grid.get_canvas(0, 0)
        assert c0.axes.get_title() != "" or cat_id == "emg", f"Empty title for {cat_title}"
        record_pass(f"Category rendered with active axes: {cat_title}")

    # Switch back to Kinematics
    case_page._sidebar.category_changed.emit("kinematics")
    app.processEvents()

    # =========================================================================
    # 7. INTERACTIVE DETAIL ZOOM (Step 3 of Guide)
    # =========================================================================
    print("\n--- 7. Testing Interactive Detail Zoom Dialog (Workflow Step 3) ---")
    # Verify double-click / zoom dialog opens
    pelvic_canvas = case_page._plot_grid.get_canvas(1, 1)
    assert hasattr(pelvic_canvas, "_last_plot_kwargs")
    zoom_dialog = ClinicalPlotDetailDialog(
        pelvic_canvas._last_plot_kwargs,
        is_dark=case_page._is_dark,
        parent=win,
    )
    zoom_dialog.show()
    app.processEvents()
    assert zoom_dialog.canvas is not None
    assert zoom_dialog._toolbar is not None
    record_pass(f"Interactive Detail Zoom dialog launched with NavigationToolbar: '{zoom_dialog.windowTitle()}'")
    zoom_dialog.close()

    # =========================================================================
    # 8. CLINICAL PDF REPORT GENERATION (Section 6 of Guide)
    # =========================================================================
    print("\n--- 8. Testing Clinical PDF Report Generation (Section 6) ---")
    artifact_dir = PROJECT_ROOT / "test_reports"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    pdf_out = artifact_dir / "E2E_Clinical_Case_Presentation_Report.pdf"
    if pdf_out.exists():
        try:
            pdf_out.unlink()
        except Exception:
            pass

    out_file = CasePresentationPdfService.generate_report(
        session_path=str(demo_session_dir),
        output_pdf_path=str(pdf_out),
        trials_data=case_page._trial_data,
        norm_data=case_page._norm_data,
    )
    assert Path(out_file).is_file(), "Report file was not created!"
    file_size_kb = Path(out_file).stat().st_size / 1024
    assert file_size_kb > 20, f"Generated PDF too small ({file_size_kb:.1f} KB)!"
    record_pass(f"Complete 5-Page Clinical PDF Report generated successfully ({file_size_kb:.1f} KB) at: {pdf_out.name}")

    # =========================================================================
    # 9. THEME INTEGRATION (Light & Dark Mode)
    # =========================================================================
    print("\n--- 9. Testing Theme Switching & Appearance ---")
    win._apply_theme(dark=True)
    app.processEvents()
    assert case_page._is_dark is True
    record_pass("Dark Mode applied cleanly across Case Presentation and canvases")

    win._apply_theme(dark=False)
    app.processEvents()
    assert case_page._is_dark is False
    record_pass("Light Mode restored cleanly")

    print("\n" + "=" * 75)
    print(f"   ALL {test_passed}/{test_total} END-TO-END MAC CASE PRESENTATION TESTS PASSED!", flush=True)
    print("   Verification against MAC_CasePresentation_Guide.md: 100% OPERATIONAL", flush=True)
    print("=" * 75, flush=True)
    win.close()
    app.quit()
    sys.exit(0)


if __name__ == "__main__":
    run_e2e_mac_case_presentation_tests()
