# -*- coding: utf-8 -*-
"""
Render screenshots of the Shriners Workstation UI for visual verification.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Conda Library bin for DLLs
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

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.models.data_models import AppSettings
from app.services.settings_service import SettingsService
from app.ui.main_window import MainWindow

ARTIFACT_DIR = PROJECT_ROOT / "test_reports"


def capture_screenshots():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    settings = SettingsService().load_app_settings()
    window = MainWindow(settings=settings)
    window.resize(1500, 900)
    window.show()
    QApplication.processEvents()

    # Capture 1: Static Analysis
    window._navigate_to("static_analysis")
    QApplication.processEvents()
    p1 = ARTIFACT_DIR / "static_analysis_view.png"
    window.grab().save(str(p1))
    print(f"Captured: {p1}")

    # Capture 2: Dynamic Analysis with Force Plate badge and adjust button
    window._navigate_to("dynamic_analysis")
    QApplication.processEvents()
    p2 = ARTIFACT_DIR / "dynamic_analysis_view.png"
    window.grab().save(str(p2))
    print(f"Captured: {p2}")

    # Capture 3: Case Presentation
    sample_dir = (
        PROJECT_ROOT
        / "Shriners_Gait_Model_PAF_v1.0"
        / "Shriners_Gait_Model_PAF_v1.0"
        / "Data"
        / "Shriners_test_002"
        / "2025-02-21_0003"
    )
    window._presentation_page.load_folder(str(sample_dir))
    window._navigate_to("case_presentation")
    QApplication.processEvents()
    p3 = ARTIFACT_DIR / "case_presentation_view.png"
    window.grab().save(str(p3))
    print(f"Captured: {p3}")


if __name__ == "__main__":
    capture_screenshots()
