# -*- coding: utf-8 -*-
"""
Tests for Patients Data Location configuration and global data access.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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

import unittest
from PySide6.QtWidgets import QApplication

from app.models.data_models import AppSettings
from app.services.settings_service import SettingsService
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.patients_page import PatientsPage
from app.ui.main_window import MainWindow


class TestPatientsDataLocation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.svc = SettingsService()
        self.settings = self.svc.load_app_settings()

    def test_patients_data_location_loaded(self):
        """Verify patients_data_location is populated with the workspace Data folder."""
        self.assertTrue(bool(self.settings.patients_data_location))
        self.assertTrue(os.path.isdir(self.settings.patients_data_location))
        self.assertTrue(self.settings.patients_data_location.endswith("Data"))

    def test_settings_page_has_file_path(self):
        """Verify SettingsPage displays Patients Data Location field with browse handler."""
        page = SettingsPage(self.settings)
        self.assertTrue(hasattr(page, "_path_patients_data_location"))
        self.assertEqual(
            page._path_patients_data_location.text(),
            self.settings.patients_data_location,
        )

    def test_patients_page_discovery_and_auto_assign(self):
        """Verify PatientsPage discovers patients from data root and auto-populates sessions."""
        page = PatientsPage()
        page.set_patients_data_root(self.settings.patients_data_location)

        expected_patient = "test_002" if "test_002" in page._discovered_patients else "Shriners_test_002"
        self.assertIn(expected_patient, page._discovered_patients)

        # Select the discovered patient
        idx = page.patient_combo.findText(expected_patient)
        self.assertGreater(idx, 0)
        page.patient_combo.setCurrentIndex(idx)

        # Verify MRN and session directory auto-population
        self.assertEqual(page.get_mrn(), expected_patient)
        s1 = page.session_rows[0].get_session_info()
        self.assertTrue(bool(s1.directory))
        self.assertTrue("2025-02-21_3" in s1.directory or "2025-02-21_0003" in s1.directory)
        self.assertEqual(s1.analysis_date, "02/21/2025")
        self.assertIsNotNone(s1.mr_left)
        self.assertIsNotNone(s1.mr_right)

    def test_main_window_wires_patients_data_root(self):
        """Verify MainWindow initializes PatientsPage and StaticAnalysisPage with patients_data_location."""
        window = MainWindow(settings=self.settings)
        self.assertEqual(
            window._patients._patients_data_root,
            self.settings.patients_data_location,
        )
        self.assertEqual(
            window._static_page._data_root,
            self.settings.patients_data_location,
        )
        self.assertIn("Data Root:", window._static_page._data_root_label.text())
        self.assertGreater(len(window._patients._discovered_patients), 0)

    def test_static_analysis_page_data_root_auto_direct(self):
        """Verify StaticAnalysisPage set_data_root updates display and browse target."""
        from app.ui.pages.static_analysis_page import StaticAnalysisPage
        page = StaticAnalysisPage()
        page.set_data_root(self.settings.patients_data_location)
        self.assertEqual(page._data_root, self.settings.patients_data_location)
        self.assertIn(self.settings.patients_data_location, page._data_root_label.text())


if __name__ == "__main__":
    unittest.main()
