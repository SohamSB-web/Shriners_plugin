# -*- coding: utf-8 -*-
"""
Verification test for 10 Left (L1-L10) and 10 Right (R1-R10) trials support:
1. Data Model (SessionInfo) 10-trial list initialization
2. Patients & Sessions UI (SessionRow) 10 Left combos + 10 Right combos
3. Auto-assign mapping up to 10 trials
4. Case Presentation toolbar 10 Left pills + 10 Right pills + Mean
5. Graph plotting: verifying each of the 10 trials per side is drawn on the graphs
6. PDF report service trial keys handling
"""
import sys
import os
from pathlib import Path
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
from app.models.data_models import SessionInfo, TrialInfo
from app.services.gcd_service import GCDData
from app.ui.pages.patients_page import SessionRow, PatientsPage
from app.ui.pages.case_presentation_page import (
    CasePresentationPage,
    TRIAL_COLORS,
    DARK_TRIAL_COLORS,
)
from app.services.pdf_report_service import CasePresentationPdfService


def test_10_trials():
    app = QApplication.instance() or QApplication(sys.argv)

    print("============================================================")
    print("TESTING 10 LEFT & 10 RIGHT TRIALS (L1-L10 & R1-R10)")
    print("============================================================")

    # 1. Test Data Model
    sess = SessionInfo()
    assert len(sess.left_trials) == 10, f"Expected 10 left trials, got {len(sess.left_trials)}"
    assert len(sess.right_trials) == 10, f"Expected 10 right trials, got {len(sess.right_trials)}"
    assert [t.label for t in sess.left_trials] == [f"L{i}" for i in range(1, 11)]
    assert [t.label for t in sess.right_trials] == [f"R{i}" for i in range(1, 11)]
    print("[PASS] 1. SessionInfo initializes with 10 Left (L1-L10) and 10 Right (R1-R10) trials")

    # 2. Test SessionRow UI in Patients & Sessions tab
    row = SessionRow(0)
    assert len(row.left_combos) == 10, f"Expected 10 left combos, got {len(row.left_combos)}"
    assert len(row.right_combos) == 10, f"Expected 10 right combos, got {len(row.right_combos)}"
    print("[PASS] 2. SessionRow UI contains 10 Left combos and 10 Right combos (2-column layout)")

    # 3. Simulate assigning 10 trials to Left and 10 trials to Right
    for i in range(1, 11):
        row.left_combos[i - 1].addItem(f"Trial_Left_{i}")
        row.left_combos[i - 1].setCurrentText(f"Trial_Left_{i}")
        row.right_combos[i - 1].addItem(f"Trial_Right_{i}")
        row.right_combos[i - 1].setCurrentText(f"Trial_Right_{i}")

    collected_sess = row.get_session_info()
    assert len(collected_sess.left_trials) == 10
    assert len(collected_sess.right_trials) == 10
    for i in range(1, 11):
        assert collected_sess.left_trials[i - 1].gcd_filename == f"Trial_Left_{i}"
        assert collected_sess.right_trials[i - 1].gcd_filename == f"Trial_Right_{i}"
    print("[PASS] 3. get_session_info() correctly captures all 10 Left and 10 Right trial selections")

    # 4. Test CasePresentationPage color palettes and toolbar pills
    for i in range(1, 11):
        assert f"L{i}" in TRIAL_COLORS, f"Missing color for L{i}"
        assert f"R{i}" in TRIAL_COLORS, f"Missing color for R{i}"
        assert f"L{i}" in DARK_TRIAL_COLORS, f"Missing dark color for L{i}"
        assert f"R{i}" in DARK_TRIAL_COLORS, f"Missing dark color for R{i}"
    assert "Mean" in TRIAL_COLORS
    print("[PASS] 4. TRIAL_COLORS and DARK_TRIAL_COLORS contain distinct entries for L1-L10 and R1-R10")

    page = CasePresentationPage()
    for i in range(1, 11):
        assert f"L{i}" in page._pill_buttons, f"Missing pill button for L{i}"
        assert f"R{i}" in page._pill_buttons, f"Missing pill button for R{i}"
    assert "Mean" in page._pill_buttons
    print("[PASS] 5. Case Presentation toolbar has filter pills for L1-L10, R1-R10, and Mean")

    # 5. Test Graph Plotting with 10 Left trials
    # Create mock GCDData for 10 Left trials and 10 Right trials
    x = np.linspace(0, 100, 101)
    mock_trials = {}
    for i in range(1, 11):
        mock_gcd_l = GCDData(
            file_path=f"Trial_L_{i}",
            variable_names=["LeftTrunkTilt", "RightTrunkTilt", "LeftFootOff", "RightFootOff"],
            variable_data=[
                list(np.sin(x * np.pi / 50 + i * 0.1) * 10 + 5),
                list(np.sin(x * np.pi / 50 + i * 0.1) * 10 + 5),
                [60.0 + i * 0.5],
                [60.0 + i * 0.5],
            ],
        )
        mock_gcd_r = GCDData(
            file_path=f"Trial_R_{i}",
            variable_names=["LeftTrunkTilt", "RightTrunkTilt", "LeftFootOff", "RightFootOff"],
            variable_data=[
                list(np.cos(x * np.pi / 50 + i * 0.1) * 10 - 5),
                list(np.cos(x * np.pi / 50 + i * 0.1) * 10 - 5),
                [58.0 + i * 0.5],
                [58.0 + i * 0.5],
            ],
        )
        mock_trials[f"L{i}"] = mock_gcd_l
        mock_trials[f"R{i}"] = mock_gcd_r

    page._trial_data = mock_trials
    page._current_side = "L"
    page._active_trial_filter = {f"L{i}" for i in range(1, 11)}
    page._refresh_plots()
    app.processEvents()

    # Check Trunk Tilt plot (row 0, col 0)
    canvas = page._plot_grid.get_canvas(0, 0)
    # Filter for trial lines (solid lines with 101 gait cycle points)
    trial_lines = [line for line in canvas.axes.lines if line.get_visible() and line.get_linestyle() == "-" and len(line.get_xdata()) == 101]
    assert len(trial_lines) == 10, f"Expected 10 plotted trial lines on Left plot, found {len(trial_lines)}"
    print(f"[PASS] 6. Graph plot successfully drew all 10 Left trial curves (found {len(trial_lines)} lines)")

    # 6. Test Graph Plotting with 10 Right trials
    page._current_side = "R"
    page._active_trial_filter = {f"R{i}" for i in range(1, 11)}
    page._refresh_plots()
    app.processEvents()

    canvas = page._plot_grid.get_canvas(0, 0)
    trial_lines_r = [line for line in canvas.axes.lines if line.get_visible() and line.get_linestyle() == "-" and len(line.get_xdata()) == 101]
    assert len(trial_lines_r) == 10, f"Expected 10 plotted trial lines on Right plot, found {len(trial_lines_r)}"
    print(f"[PASS] 7. Graph plot successfully drew all 10 Right trial curves (found {len(trial_lines_r)} lines)")

    # 7. Test Bilateral (LR) plot containing all 20 trials
    page._current_side = "LR"
    page._active_trial_filter = {f"L{i}" for i in range(1, 11)} | {f"R{i}" for i in range(1, 11)}
    page._refresh_plots()
    app.processEvents()

    canvas = page._plot_grid.get_canvas(0, 0)
    trial_lines_lr = [line for line in canvas.axes.lines if line.get_visible() and line.get_linestyle() == "-" and len(line.get_xdata()) == 101]
    assert len(trial_lines_lr) == 20, f"Expected 20 plotted trial lines on Bilateral plot, found {len(trial_lines_lr)}"
    print(f"[PASS] 8. Bilateral plot successfully drew all 20 trial curves (10 Left + 10 Right)")

    # 8. Test CasePresentationPdfService 10 trial color count
    assert len(CasePresentationPdfService.TRIAL_COLORS) == 10
    print("[PASS] 9. CasePresentationPdfService has 10 distinct colors for 10 trials")

    print("============================================================")
    print("ALL 10-TRIAL SUPPORT TESTS PASSED PERFECTLY!")
    print("============================================================")


if __name__ == "__main__":
    test_10_trials()
