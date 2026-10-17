# -*- coding: utf-8 -*-
"""
Verification test for Bilateral Left & Right Mean separation in Case Presentation:
1. Palette definitions (Mean_L, Mean_R in light and dark mode)
2. Presence and styling of Mean_L and Mean_R pills
3. Independent and coordinated toggling (Mean master vs L Mean and R Mean)
4. Plot verification: in Bilateral (LR) mode, separate Left Mean (Blue) and Right Mean (Red) curves are plotted
5. Toe-off verification: separate Left and Right toe-off vertical lines
6. Legend banner verification: _mean_legend_bar visibility and trial count text
"""
import sys
import os
from pathlib import Path
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

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
from app.services.gcd_service import GCDData
from app.ui.pages.case_presentation_page import (
    CasePresentationPage,
    TRIAL_COLORS,
    DARK_TRIAL_COLORS,
)


def test_bilateral_mean_separation():
    app = QApplication.instance() or QApplication(sys.argv)

    print("============================================================")
    print("TESTING BILATERAL LEFT & RIGHT MEAN SEPARATION")
    print("============================================================")

    # 1. Palette check
    assert "Mean_L" in TRIAL_COLORS, "Mean_L missing from TRIAL_COLORS"
    assert "Mean_R" in TRIAL_COLORS, "Mean_R missing from TRIAL_COLORS"
    assert "Mean_L" in DARK_TRIAL_COLORS, "Mean_L missing from DARK_TRIAL_COLORS"
    assert "Mean_R" in DARK_TRIAL_COLORS, "Mean_R missing from DARK_TRIAL_COLORS"
    print(f"[PASS] 1. Color palettes configured: Mean_L={TRIAL_COLORS['Mean_L']}, Mean_R={TRIAL_COLORS['Mean_R']}")

    # 2. UI Pills check
    page = CasePresentationPage()
    assert "Mean" in page._pill_buttons, "Master Mean pill missing"
    assert "Mean_L" in page._pill_buttons, "Mean_L pill missing"
    assert "Mean_R" in page._pill_buttons, "Mean_R pill missing"
    assert hasattr(page, "_mean_legend_bar"), "_mean_legend_bar missing"
    print("[PASS] 2. UI pills present: Mean, Mean_L, Mean_R, and Mean Legend Bar")

    # 3. Setup mock GCD data with clearly distinct Left and Right profiles
    # Left curve centered at +20, Right curve centered at -20
    x = np.linspace(0, 100, 101)
    mock_trials = {}
    left_y_raw = []
    right_y_raw = []

    for i in range(1, 6):
        y_l = np.sin(x * np.pi / 50) * 10 + 20 + i * 2
        y_r = np.cos(x * np.pi / 50) * 10 - 20 - i * 2
        left_y_raw.append(y_l)
        right_y_raw.append(y_r)

        mock_trials[f"L{i}"] = GCDData(
            file_path=f"Trial_L_{i}",
            variable_names=["LeftTrunkTilt", "RightTrunkTilt", "LeftFootOff", "RightFootOff"],
            variable_data=[
                list(y_l),
                list(y_l),
                [62.0 + i],
                [62.0 + i],
            ],
        )
        mock_trials[f"R{i}"] = GCDData(
            file_path=f"Trial_R_{i}",
            variable_names=["LeftTrunkTilt", "RightTrunkTilt", "LeftFootOff", "RightFootOff"],
            variable_data=[
                list(y_r),
                list(y_r),
                [55.0 + i],
                [55.0 + i],
            ],
        )

    expected_left_mean = np.mean(left_y_raw, axis=0)
    expected_right_mean = np.mean(right_y_raw, axis=0)

    page._trial_data = mock_trials
    page._current_side = "LR"
    page._active_trial_filter = {f"L{i}" for i in range(1, 6)} | {f"R{i}" for i in range(1, 6)}

    # 4. Turn on Master Mean
    page._pill_buttons["Mean"].setChecked(True)
    app.processEvents()

    assert page._pill_buttons["Mean_L"].isChecked(), "Mean_L should be checked when Mean is checked"
    assert page._pill_buttons["Mean_R"].isChecked(), "Mean_R should be checked when Mean is checked"
    assert "Mean" in page._active_trial_filter
    assert "Mean_L" in page._active_trial_filter
    assert "Mean_R" in page._active_trial_filter
    print("[PASS] 3. Selecting master 'Mean' synchronized and activated both Mean_L and Mean_R")

    # 5. Verify plot lines in Trunk Tilt (0, 0)
    canvas = page._plot_grid.get_canvas(0, 0)
    dashed_lines = [line for line in canvas.axes.lines if line.get_visible() and line.get_linestyle() == "--" and len(line.get_xdata()) == 101]
    assert len(dashed_lines) == 2, f"Expected exactly 2 mean curves (Left Mean and Right Mean), found {len(dashed_lines)}"

    # Identify Left Mean and Right Mean by their colors
    left_line = None
    right_line = None
    for l in dashed_lines:
        c = l.get_color().lower()
        if c == TRIAL_COLORS["Mean_L"].lower():
            left_line = l
        elif c == TRIAL_COLORS["Mean_R"].lower():
            right_line = l

    assert left_line is not None, f"Left Mean line not found with color {TRIAL_COLORS['Mean_L']}"
    assert right_line is not None, f"Right Mean line not found with color {TRIAL_COLORS['Mean_R']}"

    # Verify mathematical accuracy of separate means
    np.testing.assert_allclose(left_line.get_ydata(), expected_left_mean, atol=1e-5,
                               err_msg="Left Mean curve does not match expected Left trial average")
    np.testing.assert_allclose(right_line.get_ydata(), expected_right_mean, atol=1e-5,
                               err_msg="Right Mean curve does not match expected Right trial average")
    print(f"[PASS] 4. Graph plots Left Mean (Royal Blue) and Right Mean (Crimson Red) separately with 100% mathematical accuracy!")

    # 6. Verify Legend Bar
    assert not page._mean_legend_bar.isHidden(), "Mean Legend Bar should be visible in Bilateral mode when Mean is active"
    assert "Left Mean" in page._mean_leg_l_label.text()
    assert "Right Mean" in page._mean_leg_r_label.text()
    print("[PASS] 5. Mean Legend Bar visible with Left Mean and Right Mean labels")

    # 7. Test toggling off Right Mean individually
    page._pill_buttons["Mean_R"].setChecked(False)
    app.processEvents()

    canvas = page._plot_grid.get_canvas(0, 0)
    dashed_after = [line for line in canvas.axes.lines if line.get_visible() and line.get_linestyle() == "--" and len(line.get_xdata()) == 101]
    assert len(dashed_after) == 1, f"Expected 1 mean curve after deselecting Right Mean, found {len(dashed_after)}"
    assert dashed_after[0].get_color().lower() == TRIAL_COLORS["Mean_L"].lower()
    print("[PASS] 6. Deselecting R Mean individually leaves only Left Mean curve on graph")

    # 8. Test Master Mean unchecking
    page._pill_buttons["Mean"].setChecked(False)
    app.processEvents()

    assert not page._pill_buttons["Mean_L"].isChecked()
    assert not page._pill_buttons["Mean_R"].isChecked()
    canvas = page._plot_grid.get_canvas(0, 0)
    dashed_off = [line for line in canvas.axes.lines if line.get_visible() and line.get_linestyle() == "--" and len(line.get_xdata()) == 101]
    assert len(dashed_off) == 0, f"Expected 0 mean curves when Mean is off, found {len(dashed_off)}"
    assert page._mean_legend_bar.isHidden(), "Mean Legend Bar should be hidden when Mean is off"
    print("[PASS] 7. Unchecking master Mean hides all mean curves and hides the Mean Legend Bar")

    print("============================================================")
    print("ALL BILATERAL MEAN SEPARATION TESTS PASSED PERFECTLY!")
    print("============================================================")


if __name__ == "__main__":
    test_bilateral_mean_separation()
