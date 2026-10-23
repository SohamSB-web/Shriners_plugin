# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
from app.ui.dialogs.event_details_dialog import EventDetailsDialog
from app.services.event_service import load_trial_events

SAMPLE_SESSION_DIR = (
    PROJECT_ROOT
    / "Shriners_Gait_Model_PAF_v1.0"
    / "Shriners_Gait_Model_PAF_v1.0"
    / "Data"
    / "2026-10-01_2-20261004T101228Z-1-001"
    / "2026-10-01_2"
)
ARTIFACT_DIR = PROJECT_ROOT / "test_reports"


def capture():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)

    ev_info = load_trial_events(SAMPLE_SESSION_DIR, "Dynamic 1.qtm")

    # Light mode dialog (select row 0 to show active editing state)
    dlg_light = EventDetailsDialog(
        trial_filename="Dynamic 1.qtm",
        events_info=ev_info,
        frame_rate=100.0,
        session_dir=SAMPLE_SESSION_DIR,
        is_dark=False,
    )
    dlg_light.resize(960, 820)
    dlg_light.show()
    dlg_light._table.selectRow(0)
    QApplication.processEvents()

    p_light = ARTIFACT_DIR / "event_details_dialog_light.png"
    dlg_light.grab().save(str(p_light))
    print(f"Captured light: {p_light}")
    dlg_light.close()

    # Dark mode dialog (select row 1 to show LOFF selection)
    dlg_dark = EventDetailsDialog(
        trial_filename="Dynamic 1.qtm",
        events_info=ev_info,
        frame_rate=100.0,
        session_dir=SAMPLE_SESSION_DIR,
        is_dark=True,
    )
    dlg_dark.resize(960, 820)
    dlg_dark.show()
    dlg_dark._table.selectRow(1)
    QApplication.processEvents()

    p_dark = ARTIFACT_DIR / "event_details_dialog_dark.png"
    dlg_dark.grab().save(str(p_dark))
    print(f"Captured dark: {p_dark}")
    dlg_dark.close()


if __name__ == "__main__":
    capture()
