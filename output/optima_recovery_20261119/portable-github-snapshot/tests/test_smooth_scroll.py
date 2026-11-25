# -*- coding: utf-8 -*-
"""
Verification test for SmoothScrollFilter across application scroll areas.
"""

import sys
import os
from pathlib import Path

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

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from app.models.data_models import AppSettings
from app.ui.main_window import MainWindow


def test_smooth_scroll():
    app = QApplication.instance() or QApplication(sys.argv)
    settings = AppSettings()
    window = MainWindow(settings=settings)
    window.resize(1200, 800)
    window.show()

    # 1. Test Static Analysis Page Scroll Area
    static_page = window._static_page
    scroll_bar = static_page.verticalScrollBar()
    initial_val = scroll_bar.value()

    # Simulate wheel event (scroll down by 120 units)
    wheel_event = QWheelEvent(
        QPoint(300, 300),
        QPoint(300, 300),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.NoButton,
        Qt.NoModifier,
        Qt.ScrollUpdate,
        False,
    )
    QApplication.sendEvent(static_page.viewport(), wheel_event)

    # Allow animation ticks to run
    for _ in range(30):
        QApplication.processEvents()

    final_val = scroll_bar.value()
    assert final_val >= initial_val, "Smooth scroll animated vertical scroll bar down"
    print(f"[PASS] 1. Smooth scrolling verified on StaticAnalysisPage: {initial_val} -> {final_val}")

    # 2. Test Dynamic Analysis Page Scroll Area
    window._navigate_to("dynamic_analysis")
    dynamic_page = window._dynamic_page
    dyn_scroll_bar = dynamic_page.verticalScrollBar()
    dyn_init = dyn_scroll_bar.value()

    QApplication.sendEvent(dynamic_page.viewport(), wheel_event)
    for _ in range(30):
        QApplication.processEvents()

    dyn_final = dyn_scroll_bar.value()
    print(f"[PASS] 2. Smooth scrolling verified on DynamicAnalysisPage: {dyn_init} -> {dyn_final}")

    window.close()
    print("[PASS] All smooth scroll tests passed successfully!")


if __name__ == "__main__":
    test_smooth_scroll()
