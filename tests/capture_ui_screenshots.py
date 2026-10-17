# -*- coding: utf-8 -*-
"""
Capture screenshots of UI with redesigned minimal vector icons:
1. Static Analysis page (with active Static Analysis sidebar item)
2. Dynamic Analysis page (with active Dynamic Analysis sidebar item and buttons)
3. Event Details Dialog
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

    # 1. Static Analysis view (matching user's screenshot)
    window._navigate_to("static_analysis")
    QApplication.processEvents()
    p_static = ARTIFACT_DIR / "static_analysis_page_redesign.png"
    window.grab().save(str(p_static))
    print(f"Captured: {p_static}")

    # 2. Dynamic Analysis view
    window._navigate_to("dynamic_analysis")
    window._dynamic_page.load_session(SAMPLE_SESSION_XML)
    QApplication.processEvents()
    p_dynamic = ARTIFACT_DIR / "dynamic_analysis_auto_events_page.png"
    window.grab().save(str(p_dynamic))
    print(f"Captured: {p_dynamic}")

    # 3. Capture EventDetailsDialog
    ev_info = load_trial_events(SAMPLE_SESSION_DIR, "Dynamic 1.qtm")
    dlg = EventDetailsDialog(
        trial_filename="Dynamic 1.qtm",
        events_info=ev_info,
        frame_rate=100.0,
    )
    dlg.resize(800, 600)
    dlg.show()
    QApplication.processEvents()

    p_dlg = ARTIFACT_DIR / "event_details_dialog.png"
    dlg.grab().save(str(p_dlg))
    print(f"Captured: {p_dlg}")
    dlg.close()

    # 4. Capture ForcePlateConfigDialog
    from app.ui.widgets.force_plate_dialog import ForcePlateConfigDialog
    fp_dlg = ForcePlateConfigDialog(
        session_dir=str(SAMPLE_SESSION_DIR),
        trial_filename="Dynamic 1.qtm",
        parent=None,
    )
    fp_dlg.resize(900, 650)
    fp_dlg.show()
    QApplication.processEvents()

    p_fp = ARTIFACT_DIR / "force_plate_dialog.png"
    fp_dlg.grab().save(str(p_fp))
    print(f"Captured: {p_fp}")
    # 5. Capture Dashboard Page
    window._navigate_to("dashboard")
    QApplication.processEvents()
    p_dash = ARTIFACT_DIR / "dashboard_page_redesign.png"
    window.grab().save(str(p_dash))
    print(f"Captured: {p_dash}")

    # 6. Capture QTM Monitor Page
    window._navigate_to("qtm")
    QApplication.processEvents()
    p_qtm = ARTIFACT_DIR / "qtm_monitor_page_redesign.png"
    window.grab().save(str(p_qtm))
    print(f"Captured: {p_qtm}")

    window.close()


if __name__ == "__main__":
    capture()
