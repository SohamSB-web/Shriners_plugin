# -*- coding: utf-8 -*-
"""
Test Suite: Dynamic Clinical Plot Y-Axis Scaling.

Verifies that:
1. Gait curves whose peaks exceed the default clinical upper limits (e.g. Hip/Knee Flexion > 60/80 deg)
   dynamically expand the visible plot area so the apex is fully visible without clipping.
2. Curves whose troughs plunge below the default lower limits (e.g. Knee Rotation < -60 deg)
   dynamically expand the lower visible area.
3. Curves within standard clinical ranges preserve the canonical limits and tick marks.
4. Ticks remain evenly spaced, cleanly aligned, and legible without overcrowding.
5. ClinicalPlotCanvas renders the expanded range on both axes and stores it in _last_plot_kwargs.
"""

import os
import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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

from PySide6.QtWidgets import QApplication
from app.ui.charts.clinical_plots import (
    ClinicalPlotCanvas,
    ClinicalPlotDetailDialog,
    calculate_dynamic_y_limits,
    compute_nice_ticks,
    get_data_y_extents,
)


def test_calculate_dynamic_y_limits_nominal():
    """Verify nominal curves within limits retain canonical limits and ticks."""
    y_normal = [np.array([0.0, 15.0, 35.0, 50.0, 20.0, 0.0])]
    ymin, ymax, ticks = calculate_dynamic_y_limits(
        y_data=y_normal,
        y_min=-15,
        y_max=60,
        y_ticks=[-15, 0, 15, 30, 45, 60],
    )
    assert ymin == -15.0, f"Expected -15.0, got {ymin}"
    assert ymax == 60.0, f"Expected 60.0, got {ymax}"
    assert ticks == [-15, 0, 15, 30, 45, 60]
    print("[PASS] 1. Nominal data within limits retains canonical range and ticks.")


def test_calculate_dynamic_y_limits_peak_exceeded():
    """Verify Hip Flexion peak exceeding 60 deg expands upper limit."""
    # Peak at 78 deg
    y_peak = [np.array([0.0, 25.0, 55.0, 78.0, 40.0, 5.0])]
    ymin, ymax, ticks = calculate_dynamic_y_limits(
        y_data=y_peak,
        y_min=-15,
        y_max=60,
        y_ticks=[-15, 0, 15, 30, 45, 60],
    )
    assert ymin == -15, f"Expected lower limit -15, got {ymin}"
    assert ymax >= 78, f"Expected upper limit >= 78, got {ymax}"
    assert ymax == 90, f"Expected 90 with step 15, got {ymax}"
    assert 75 in ticks and 90 in ticks
    print(f"[PASS] 2. Peak at 78 deg expanded ymax to {ymax} with ticks {ticks}.")


def test_calculate_dynamic_y_limits_trough_exceeded():
    """Verify Knee Rotation dropping below -60 deg expands lower limit."""
    # Trough at -72 deg
    y_trough = [np.array([10.0, -15.0, -45.0, -72.0, -30.0, 0.0])]
    ymin, ymax, ticks = calculate_dynamic_y_limits(
        y_data=y_trough,
        y_min=-60,
        y_max=15,
        y_ticks=[-60, -45, -30, -15, 0, 15],
    )
    assert ymin <= -72, f"Expected lower limit <= -72, got {ymin}"
    assert ymin == -75, f"Expected -75 with step 15, got {ymin}"
    assert ymax == 15
    assert -75 in ticks
    print(f"[PASS] 3. Trough at -72 deg expanded ymin to {ymin} with ticks {ticks}.")


def test_calculate_dynamic_y_limits_both_exceeded():
    """Verify Hip Rotation exceeding both top (+45) and bottom (-30)."""
    y_both = [np.array([-42.0, -10.0, 20.0, 52.0, 10.0, -20.0])]
    ymin, ymax, ticks = calculate_dynamic_y_limits(
        y_data=y_both,
        y_min=-30,
        y_max=45,
        y_ticks=[-30, -15, 0, 15, 30, 45],
    )
    assert ymin <= -42 and ymin == -45
    assert ymax >= 52 and ymax == 60
    assert ticks == [-45, -30, -15, 0, 15, 30, 45, 60]
    print(f"[PASS] 4. Both limits expanded to [{ymin}, {ymax}] with ticks {ticks}.")


def test_clinical_plot_canvas_live_rendering():
    """Verify ClinicalPlotCanvas renders with dynamic limits and stores them in kwargs."""
    app = QApplication.instance() or QApplication(sys.argv)

    canvas = ClinicalPlotCanvas(width=3.2, height=2.2, dpi=100)
    x = np.linspace(0, 100, 101)
    # Peak goes up to 88 deg (exceeds default 60)
    y = np.sin(np.linspace(0, np.pi, 101)) * 88.0

    canvas.plot_gait_data(
        x_data=[x],
        y_data=[y],
        colors=["#2563EB"],
        y_min=-15,
        y_max=60,
        y_ticks=[-15, 0, 15, 30, 45, 60],
        title="Hip Flexion-Extension",
    )

    rendered_ymin, rendered_ymax = canvas.axes.get_ylim()
    assert rendered_ymax >= 88.0, f"Rendered ymax {rendered_ymax} did not contain peak 88.0"
    assert rendered_ymax == 90.0, f"Expected 90.0, got {rendered_ymax}"

    last_kw = getattr(canvas, "_last_plot_kwargs", {})
    assert last_kw.get("y_max") == 90.0
    assert 90 in last_kw.get("y_ticks", [])
    print(f"[PASS] 5. ClinicalPlotCanvas rendered axes ylim: [{rendered_ymin}, {rendered_ymax}] with no peak clipping.")


def test_cursor_coordinates_formatting():
    """Verify x and y coordinates are properly formatted and never blank on hover."""
    from app.ui.charts.clinical_plots import format_clinical_coords

    canvas = ClinicalPlotCanvas(width=8.0, height=5.0, dpi=100)
    canvas.plot_gait_data(
        x_data=[np.linspace(0, 100, 101)],
        y_data=[np.full(101, -63.4)],
        colors=["#2563EB"],
        show_x_labels=True,
        title="Knee Flexion-Extension",
    )

    coord_str = canvas.axes.format_coord(52.4, -63.4)
    assert "(, " not in coord_str, f"x coordinate was blank: {coord_str}"
    assert coord_str == "(x, y) = (52.4, -63.4)", f"Unexpected coordinate string: {coord_str}"

    # Also verify when show_x_labels is False
    canvas.plot_gait_data(
        x_data=[np.linspace(0, 100, 101)],
        y_data=[np.full(101, 15.0)],
        colors=["#10B981"],
        show_x_labels=False,
    )
    coord_str_hidden = canvas.axes.format_coord(25.0, 15.0)
    assert coord_str_hidden == "(x, y) = (25.0, 15.0)"
    print(f"[PASS] 6. Cursor coordinate formatting verified: {coord_str} (no blank x coordinates).")


def test_detail_dialog_range_adjustment():
    """Verify popup ClinicalPlotDetailDialog ensures headroom and provides range adjustment."""
    app = QApplication.instance() or QApplication(sys.argv)

    x = np.linspace(0, 100, 101)
    y = np.sin(np.linspace(0, np.pi, 101)) * 30.0  # curve touching 30.0
    kw = {
        "x_data": [x],
        "y_data": [y],
        "colors": ["#2563EB"],
        "y_min": -30.0,
        "y_max": 30.0,
        "title": "Knee Flexion Detail",
    }

    dlg = ClinicalPlotDetailDialog(kw, is_dark=False)
    dlg.show()
    app.processEvents()

    # 1. Dialog opens with adequate headroom (never cutting the peak)
    rendered_ymin, rendered_ymax = dlg.canvas.axes.get_ylim()
    assert rendered_ymax > 30.0, f"Expected headroom above peak 30.0, got {rendered_ymax}"

    # 2. Manual range adjustment via spinboxes
    dlg._spin_ymin.setValue(-50.0)
    dlg._spin_ymax.setValue(100.0)
    dlg._apply_custom_range()
    app.processEvents()
    cur_min, cur_max = dlg.canvas.axes.get_ylim()
    assert cur_min == -50.0 and cur_max == 100.0, f"Expected [-50, 100], got [{cur_min}, {cur_max}]"

    # 3. Auto-fit full graph
    dlg._autofit_range()
    app.processEvents()
    af_min, af_max = dlg.canvas.axes.get_ylim()
    assert af_max >= 30.0 and af_min <= 0.0

    # 4. Expand range (+15%)
    before_span = af_max - af_min
    dlg._expand_range()
    app.processEvents()
    exp_min, exp_max = dlg.canvas.axes.get_ylim()
    assert (exp_max - exp_min) > before_span

    # 5. Reset range
    dlg._reset_range()
    app.processEvents()
    res_min, res_max = dlg.canvas.axes.get_ylim()
    assert res_min == -30.0 and res_max == 30.0

    # 6. Two-way sync when axes limits change (e.g. pan/zoom toolbar)
    dlg.canvas.axes.set_ylim(-40.0, 80.0)
    app.processEvents()
    assert dlg._spin_ymin.value() == -40.0
    assert dlg._spin_ymax.value() == 80.0

    dlg.close()
    print("[PASS] 7. ClinicalPlotDetailDialog range adjustments (manual, auto-fit, expand, reset, sync) verified.")


def test_detail_dialog_never_cramps_baseline():
    """Verify dialog never shrinks baseline Y-axis into a narrow data subrange (e.g. Knee Flexion data [20, 58])."""
    app = QApplication.instance() or QApplication(sys.argv)

    x = np.linspace(0, 100, 101)
    # Knee flexion curve ranging from 20 to 58 deg (never goes negative, but nominal is [-15, 60])
    y = 20.0 + 38.0 * np.sin(np.linspace(0, np.pi, 101))
    kw = {
        "x_data": [x],
        "y_data": [y],
        "colors": ["#2563EB"],
        "y_min": -15.0,
        "y_max": 60.0,
        "y_ticks": [-15, 0, 15, 30, 45, 60],
        "title": "Knee Flexion-Extension",
    }

    dlg = ClinicalPlotDetailDialog(kw, is_dark=False)
    dlg.show()
    app.processEvents()

    ymin, ymax = dlg.canvas.axes.get_ylim()
    # ymin MUST NOT be shrunk up to 15 or 20 deg! It must preserve the nominal -15.0 baseline!
    assert ymin == -15.0, f"Expected baseline -15.0, but ymin was cramped to {ymin}"
    assert ymax >= 60.0, f"Expected ymax >= 60.0, got {ymax}"

    # Auto-fit must also preserve the nominal baseline
    dlg._autofit_range()
    app.processEvents()
    af_min, af_max = dlg.canvas.axes.get_ylim()
    assert af_min == -15.0, f"Auto-fit cramped ymin to {af_min} instead of preserving -15.0 baseline"
    assert af_max >= 60.0

    dlg.close()
    print("[PASS] 8. Detail dialog preserves canonical clinical baseline without cramping or shrinking Y-axis.")


def test_expand_range_thins_ticks_no_overlap():
    """Verify that expanding the range in the dialog or grid never produces overlapping ticks (<= 8 ticks)."""
    app = QApplication.instance() or QApplication(sys.argv)

    x = np.linspace(0, 100, 101)
    y = np.sin(np.linspace(0, np.pi, 101)) * 50.0
    source_canvas = ClinicalPlotCanvas(width=3.2, height=2.2, dpi=100)
    source_canvas.plot_gait_data(
        x_data=[x],
        y_data=[y],
        colors=["#2563EB"],
        y_min=-15.0,
        y_max=60.0,
        y_ticks=[-15, 0, 15, 30, 45, 60],
        title="Hip Flexion-Extension",
    )

    dlg = ClinicalPlotDetailDialog(source_canvas._last_plot_kwargs, is_dark=False, source_canvas=source_canvas)
    dlg.show()
    app.processEvents()

    # 1. Expand range multiple times outward
    for _ in range(12):
        dlg._expand_range()
        app.processEvents()
        ticks = list(dlg.canvas.axes.get_yticks())
        src_ticks = list(source_canvas.axes.get_yticks())
        assert len(ticks) <= 8, f"Too many ticks in dialog! Overcrowding: {ticks}"
        assert len(src_ticks) <= 8, f"Too many ticks in source canvas! Overcrowding: {src_ticks}"
        assert 0 in ticks, f"0 reference tick missing in dialog ticks: {ticks}"
        assert 0 in src_ticks, f"0 reference tick missing in source ticks: {src_ticks}"

    # 2. Specifically test user's exact case [-195, 195]
    dlg._spin_ymin.setValue(-195.0)
    dlg._spin_ymax.setValue(195.0)
    dlg._apply_custom_range()
    app.processEvents()

    dlg_ticks = list(dlg.canvas.axes.get_yticks())
    src_ticks = list(source_canvas.axes.get_yticks())
    assert len(dlg_ticks) <= 8, f"Expected <= 8 ticks at [-195, 195], got {len(dlg_ticks)}: {dlg_ticks}"
    assert len(src_ticks) <= 8, f"Expected <= 8 ticks in source canvas, got {len(src_ticks)}: {src_ticks}"
    assert dlg_ticks == [-180, -120, -60, 0, 60, 120, 180], f"Unexpected ticks for [-195, 195]: {dlg_ticks}"
    assert src_ticks == [-180, -120, -60, 0, 60, 120, 180], f"Unexpected source ticks: {src_ticks}"

    dlg.close()
    print("[PASS] 9. Expand range dynamically thins ticks, preventing tick label overlap (<= 8 ticks).")


def test_dynamic_plot_scaling_all():
    print("=" * 60)
    print("RUNNING DYNAMIC PLOT SCALING TEST SUITE")
    print("=" * 60)
    test_calculate_dynamic_y_limits_nominal()
    test_calculate_dynamic_y_limits_peak_exceeded()
    test_calculate_dynamic_y_limits_trough_exceeded()
    test_calculate_dynamic_y_limits_both_exceeded()
    test_clinical_plot_canvas_live_rendering()
    test_cursor_coordinates_formatting()
    test_detail_dialog_range_adjustment()
    test_detail_dialog_never_cramps_baseline()
    test_expand_range_thins_ticks_no_overlap()
    print("=" * 60)
    print("ALL DYNAMIC PLOT SCALING TESTS PASSED SUCCESSFULLY! [OK]")
    print("=" * 60)


if __name__ == "__main__":
    test_dynamic_plot_scaling_all()

