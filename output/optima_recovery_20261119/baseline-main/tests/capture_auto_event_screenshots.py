# -*- coding: utf-8 -*-
"""
Capture screenshots of Dynamic Analysis Page with Auto Event Labeling controls
and the EventDetailsDialog.
"""

import os
import sys
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

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.models.data_models import AppSettings
from app.services.event_service import load_trial_events
from app.services.settings_service import SettingsService
from app.ui.dialogs.event_details_dialog import EventDetailsDialog
from app.ui.main_window import MainWindow

SAMPLE_SESSION_DIR = (
    PROJECT_ROOT
    / "Shriners_Gait_Model_PAF_v1.0"
    / "Shriners_Gait_Model_PAF_v1.0"
    / "Data"
    / "Shriners_test_002"
    / "2025-02-21_0003"
)
SAMPLE_SESSION_XML = str(SAMPLE_SESSION_DIR / "session.xml")
ARTIFACT_DIR = PROJECT_ROOT / "test_reports"


def capture():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)

    settings = SettingsService().load_app_settings()
    window = MainWindow(settings=settings)
    window.resize(1500, 920)
    window.show()
    window._navigate_to("dynamic_analysis")
    window._dynamic_page.load_session(SAMPLE_SESSION_XML)
    QApplication.processEvents()

    # Capture main window with Dynamic Analysis page
    p1 = ARTIFACT_DIR / "dynamic_analysis_auto_events_page.png"
    window.grab().save(str(p1))
    print(f"Captured: {p1}")

    # Capture EventDetailsDialog
    ev_info = load_trial_events(SAMPLE_SESSION_DIR, "Dynamic 1.qtm")
    dlg = EventDetailsDialog(
        trial_filename="Dynamic 1.qtm",
        events_info=ev_info,
        frame_rate=100.0,
    )
    dlg.resize(800, 600)
    dlg.show()
    QApplication.processEvents()

    p2 = ARTIFACT_DIR / "event_details_dialog.png"
    dlg.grab().save(str(p2))
    print(f"Captured: {p2}")

    dlg.close()
    window.close()


if __name__ == "__main__":
    capture()
