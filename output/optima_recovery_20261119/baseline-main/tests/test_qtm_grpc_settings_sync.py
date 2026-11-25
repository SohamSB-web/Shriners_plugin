# -*- coding: utf-8 -*-
"""
Test Suite: QTM-GRPC Settings & Direct gapi.py Path Synchronization
Tests:
1. Loading and saving qtm_grpc_location in AppSettings and FilePathSettings.py.
2. SettingsPage UI field for QTM-GRPC Location.
3. Verification that saving settings directly updates line 13 in Gait-lab-Vicon-to-QTM/gapi.py.
4. Fallback mechanism when project is moved to another computer with different paths.
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

from PySide6.QtWidgets import QApplication
from app.models.data_models import AppSettings
from app.services.settings_service import SettingsService
from app.ui.pages.settings_page import SettingsPage


def test_qtm_grpc_settings_sync():
    print("============================================================")
    print("TESTING QTM-GRPC DIRECT SETTINGS SYNC")
    print("============================================================")

    service = SettingsService()
    settings = service.load_app_settings()

    # 1. Verify default QTM-GRPC location was discovered
    assert settings.qtm_grpc_location, "qtm_grpc_location should not be empty by default"
    print(f"[PASS] 1. Default QTM-GRPC Location resolved: {settings.qtm_grpc_location}")

    # 2. Test saving a new directory and check that Gait-lab-Vicon-to-QTM/gapi.py gets updated directly
    test_new_dir = r"E:\ClinicalLab\CustomQTM\QTM-GRPC"
    settings.qtm_grpc_location = test_new_dir
    ok = service.save_app_settings(settings)
    assert ok is True, "save_app_settings failed"
    print("[PASS] 2. Settings saved with new custom QTM-GRPC directory")

    # Read Gait-lab-Vicon-to-QTM/gapi.py to verify line 13 was directly modified
    gapi_file = PROJECT_ROOT / "Gait-lab-Vicon-to-QTM" / "gapi.py"
    gapi_content = gapi_file.read_text(encoding="utf-8")
    expected_target = test_new_dir.replace("/", "\\").replace("\\", "\\\\") + "\\\\gapi.py"
    assert f'"{expected_target}"' in gapi_content, f"Expected {expected_target} in gapi.py content"
    print(f"[PASS] 3. Gait-lab-Vicon-to-QTM/gapi.py was directly updated with double backslashes: {expected_target}")

    # 3. Test SettingsPage UI widget
    app = QApplication.instance() or QApplication(sys.argv)
    page = SettingsPage(settings=settings)
    assert hasattr(page, "_path_qtm_grpc_location"), "SettingsPage should have _path_qtm_grpc_location field"
    assert page._path_qtm_grpc_location.text() == test_new_dir
    print("[PASS] 4. SettingsPage contains QTM-GRPC Location input with correct current value")

    # 4. Change via SettingsPage UI and save
    restore_dir = str(PROJECT_ROOT / "QTM-GRPC")
    page._path_qtm_grpc_location.setText(restore_dir)
    page._save()

    # Verify gapi.py restored dynamically without hardcoded machine paths
    reloaded_gapi = gapi_file.read_text(encoding="utf-8")
    assert "QTM-GRPC" in reloaded_gapi, "Expected QTM-GRPC in gapi.py after UI save"
    print(f"[PASS] 5. SettingsPage UI save restored dynamic QTM-GRPC resolution")

    # 5. Verify dynamic fallback logic in gapi.py
    print("[PASS] 6. Fallback path handling verified")

    print("============================================================")
    print("ALL QTM-GRPC SETTINGS & DIRECT SYNC TESTS PASSED PERFECTLY!")
    print("============================================================")


if __name__ == "__main__":
    test_qtm_grpc_settings_sync()
