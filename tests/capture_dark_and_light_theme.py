# -*- coding: utf-8 -*-
"""
Automated Capture of Dark & Light Mode Workspaces for Shriners Gait Workstation:
1. Static Analysis in Dark Mode
2. Dynamic Analysis in Dark Mode
3. Case Presentation in Dark Mode
4. Dashboard in Dark Mode
5. Event Details Dialog in Dark Mode
6. Force Plate Config Dialog in Dark Mode
7. Static Analysis in Light Mode
8. Dynamic Analysis in Light Mode
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
from app.ui.widgets.force_plate_dialog import ForcePlateConfigDialog
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


def capture_all():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)

    settings = SettingsService().load_app_settings()
    settings.dark_mode = True  # start with dark mode
    window = MainWindow(settings=settings)
    window.resize(1500, 920)
    window.show()

    # ── 1. DARK MODE: Static Analysis
    window._apply_theme(dark=True)
    window._navigate_to("static_analysis")
    QApplication.processEvents()
    p_dark_static = ARTIFACT_DIR / "dark_static_analysis.png"
    window.grab().save(str(p_dark_static))
    print(f"Captured: {p_dark_static}")

    # ── 2. DARK MODE: Dynamic Analysis
    window._navigate_to("dynamic_analysis")
    window._dynamic_page.load_session(SAMPLE_SESSION_XML)
    QApplication.processEvents()
    p_dark_dynamic = ARTIFACT_DIR / "dark_dynamic_analysis.png"
    window.grab().save(str(p_dark_dynamic))
    print(f"Captured: {p_dark_dynamic}")

    # ── 3. DARK MODE: Case Presentation
    window._navigate_to("case_presentation")
    window._presentation_page.load_folder(str(SAMPLE_SESSION_DIR))
    QApplication.processEvents()
    p_dark_pres = ARTIFACT_DIR / "dark_case_presentation.png"
    window.grab().save(str(p_dark_pres))
    print(f"Captured: {p_dark_pres}")

    # ── 4. DARK MODE: Dashboard
    window._navigate_to("dashboard")
    QApplication.processEvents()
    p_dark_dash = ARTIFACT_DIR / "dark_dashboard.png"
    window.grab().save(str(p_dark_dash))
    print(f"Captured: {p_dark_dash}")

    # ── 5. DARK MODE: Event Details Dialog
    ev_info = load_trial_events(SAMPLE_SESSION_DIR, "Dynamic 1.qtm")
    dlg = EventDetailsDialog(
        trial_filename="Dynamic 1.qtm",
        events_info=ev_info,
        frame_rate=100.0,
        is_dark=True,
    )
    dlg.resize(800, 600)
    dlg.show()
    QApplication.processEvents()
    p_dark_dlg = ARTIFACT_DIR / "dark_event_details_dialog.png"
    dlg.grab().save(str(p_dark_dlg))
    print(f"Captured: {p_dark_dlg}")
    dlg.close()

    # ── 6. DARK MODE: Force Plate Config Dialog
    fp_dlg = ForcePlateConfigDialog(
        session_dir=str(SAMPLE_SESSION_DIR),
        trial_filename="Dynamic 1.qtm",
        parent=None,
        is_dark=True,
    )
    fp_dlg.resize(900, 650)
    fp_dlg.show()
    QApplication.processEvents()
    p_dark_fp = ARTIFACT_DIR / "dark_force_plate_dialog.png"
    fp_dlg.grab().save(str(p_dark_fp))
    print(f"Captured: {p_dark_fp}")
    fp_dlg.close()

    # ── 7. SWITCH TO LIGHT MODE: Static Analysis
    window._apply_theme(dark=False)
    window._navigate_to("static_analysis")
    QApplication.processEvents()
    p_light_static = ARTIFACT_DIR / "light_static_analysis.png"
    window.grab().save(str(p_light_static))
    print(f"Captured: {p_light_static}")

    # ── 8. LIGHT MODE: Dynamic Analysis
    window._navigate_to("dynamic_analysis")
    QApplication.processEvents()
    p_light_dynamic = ARTIFACT_DIR / "light_dynamic_analysis.png"
    window.grab().save(str(p_light_dynamic))
    print(f"Captured: {p_light_dynamic}")

    # ── 9. LIGHT MODE: Case Presentation
    window._navigate_to("case_presentation")
    QApplication.processEvents()
    p_light_pres = ARTIFACT_DIR / "light_case_presentation.png"
    window.grab().save(str(p_light_pres))
    print(f"Captured: {p_light_pres}")

    # ── 10. LIGHT MODE: Dashboard
    window._navigate_to("dashboard")
    QApplication.processEvents()
    p_light_dash = ARTIFACT_DIR / "light_dashboard.png"
    window.grab().save(str(p_light_dash))
    print(f"Captured: {p_light_dash}")

    # ── 11. LIGHT MODE: Force Plate Config Dialog
    fp_dlg_light = ForcePlateConfigDialog(
        session_dir=str(SAMPLE_SESSION_DIR),
        trial_filename="Dynamic 1.qtm",
        parent=None,
        is_dark=False,
    )
    fp_dlg_light.resize(900, 650)
    fp_dlg_light.show()
    QApplication.processEvents()
    p_light_fp = ARTIFACT_DIR / "light_force_plate_dialog.png"
    fp_dlg_light.grab().save(str(p_light_fp))
    print(f"Captured: {p_light_fp}")
    fp_dlg_light.close()

    window.close()
    print("ALL SCREENSHOTS CAPTURED SUCCESSFULLY!")


if __name__ == "__main__":
    capture_all()
