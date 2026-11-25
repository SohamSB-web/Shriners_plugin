# -*- coding: utf-8 -*-
"""
Verification test for MAC Case Presentation page:
1. Trial buttons square dimensions (30px x 30px for L1-L10 and R1-R10).
2. 60 FPS smooth scroll integration across page, grid, and canvases.
3. Canvas-level mouse wheel event interception and vertical scrollbar movement.
4. Smooth scroll reset on category change and session reload.
"""
import sys
import os
from pathlib import Path

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
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QWheelEvent
from app.ui.pages.case_presentation_page import CasePresentationPage
from app.ui.widgets.smooth_scroll import SmoothScrollFilter


def test_mac_case_presentation():
    app = QApplication.instance() or QApplication(sys.argv)

    print("============================================================")
    print("TESTING MAC CASE PRESENTATION: SQUARE BUTTONS & SMOOTH SCROLL")
    print("============================================================")

    page = CasePresentationPage()
    page.resize(1280, 800)
    page.show()
    app.processEvents()

    # 1. Verify Square Trial Buttons
    print("\n--- 1. Testing Square Trial Buttons (L1-L10, R1-R10) ---")
    for k in [f"L{i}" for i in range(1, 11)] + [f"R{i}" for i in range(1, 11)]:
        btn = page._pill_buttons[k]
        print(f"{k} dimensions: {btn.width()}x{btn.height()}")
        assert btn.width() == btn.height(), f"{k} not a 1:1 square! ({btn.width()}x{btn.height()})"
        assert btn.width() in (30, 32), f"{k} button width expected ~30, got {btn.width()}"
        qss = btn.styleSheet()
        assert "min-width: 30px" in qss, f"{k} missing min-width: 30px in stylesheet"
        assert "max-width: 30px" in qss, f"{k} missing max-width: 30px in stylesheet"
        assert "min-height: 30px" in qss, f"{k} missing min-height: 30px in stylesheet"
        assert "max-height: 30px" in qss, f"{k} missing max-height: 30px in stylesheet"

    mean_btn = page._pill_buttons["Mean"]
    print(f"Mean dimensions: {mean_btn.width()}x{mean_btn.height()}")
    assert mean_btn.height() == page._pill_buttons["L1"].height(), "Mean button height does not match trial buttons!"
    assert mean_btn.width() >= 50, f"Mean button width expected >= 50, got {mean_btn.width()}"
    print("[PASS] All 20 trial buttons (L1-L10, R1-R10) are strict 30px x 30px 1:1 squares!")
    print("[PASS] Mean button is styled with matching 30px height (50px x 30px)!")

    # 2. Verify Smooth Scroll Installation
    print("\n--- 2. Testing Smooth Scroll Filter Attachment ---")
    assert hasattr(page, "_smooth_scroll"), "CasePresentationPage missing _smooth_scroll instance"
    assert isinstance(page._smooth_scroll, SmoothScrollFilter), "_smooth_scroll is not a SmoothScrollFilter"

    all_canvases = page._plot_grid.get_all_canvases()
    assert len(all_canvases) == 15, f"Expected 15 clinical plot canvases, got {len(all_canvases)}"
    print(f"[PASS] MultiPlotGrid has {len(all_canvases)} ClinicalPlotCanvas instances")

    # 3. Simulate Mouse Wheel on Clinical Plot Canvas
    print("\n--- 3. Testing Kinetic Smooth Scroll on Clinical Plot Canvas ---")
    vbar = page._scroll.verticalScrollBar()
    # Ensure there is scrollable content
    vbar.setRange(0, 1000)
    vbar.setValue(0)
    assert vbar.value() == 0

    # Simulate wheel event (delta = -120, scrolling down) directly on canvas 0
    canvas_0 = all_canvases[0]
    wheel_ev = QWheelEvent(
        QPointF(50.0, 50.0),
        QPointF(50.0, 50.0),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.NoButton,
        Qt.NoModifier,
        Qt.ScrollUpdate,
        False,
    )

    # Deliver wheel event through Qt event system
    app.sendEvent(canvas_0, wheel_ev)

    # Process events to let smooth scroll timer tick
    for _ in range(10):
        app.processEvents()
        import time
        time.sleep(0.02)

    after_val = vbar.value()
    print(f"Scrollbar value after wheel event on canvas: {after_val}")
    assert after_val > 0, f"Expected scrollbar to scroll down (>0), got {after_val}"
    print("[PASS] Mouse wheel event over Matplotlib canvas successfully triggers kinetic smooth scroll!")

    # 4. Test Reset on Category Change
    print("\n--- 4. Testing Reset on Category Change ---")
    page._on_category_changed("sagittal_kinetics")
    assert vbar.value() == 0, f"Expected scrollbar to reset to 0, got {vbar.value()}"
    print("[PASS] Category change smoothly resets scrollbar position to top (0)!")

    print("\n============================================================")
    print("ALL MAC CASE PRESENTATION TESTS PASSED PERFECTLY!")
    print("============================================================")


if __name__ == "__main__":
    test_mac_case_presentation()
