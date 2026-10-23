# -*- coding: utf-8 -*-
"""
Capture screenshot of ForcePlateConfigDialog.
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

from PySide6.QtWidgets import QApplication
from app.ui.widgets.force_plate_dialog import ForcePlateConfigDialog

SAMPLE_DIR = (
    PROJECT_ROOT
    / "Shriners_Gait_Model_PAF_v1.0"
    / "Shriners_Gait_Model_PAF_v1.0"
    / "Data"
    / "Shriners_test_002"
    / "2025-02-21_0003"
)
ARTIFACT_DIR = PROJECT_ROOT / "test_reports"


def capture_fp_dialog():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    dlg = ForcePlateConfigDialog(
        session_dir=str(SAMPLE_DIR),
        trial_filename="Dynamic 1.qtm",
        current_left="FP0",
        current_right="0",
    )
    dlg.resize(900, 700)
    dlg.show()
    QApplication.processEvents()

    p = ARTIFACT_DIR / "force_plate_dialog_view.png"
    dlg.grab().save(str(p))
    print(f"Captured: {p}")
    dlg.close()


if __name__ == "__main__":
    capture_fp_dialog()
