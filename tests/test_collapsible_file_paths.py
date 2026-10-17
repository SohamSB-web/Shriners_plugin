# -*- coding: utf-8 -*-
"""
Tests for CollapsibleSectionCard and SettingsPage's collapsible File Paths section.
"""

import sys
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication

from app.models.data_models import AppSettings
from app.ui.pages.settings_page import SettingsPage
from app.ui.widgets.components import CollapsibleSectionCard


class TestCollapsibleFilePaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_collapsible_section_card_behavior(self):
        """Verify CollapsibleSectionCard expands, collapses, and emits signals."""
        card = CollapsibleSectionCard(
            title="Advanced Laboratory Configuration (Optional)",
            subtitle="Default paths are automatically detected from the workspace.",
            collapsed=True,
            expand_text="Show Paths ▾",
            collapse_text="Hide Paths ▴",
        )
        self.assertTrue(card.is_collapsed())
        self.assertTrue(card._container.isHidden())
        self.assertEqual(card._toggle_btn.text(), "Show Paths ▾")

        # Track signals
        emitted_states = []
        card.toggled.connect(lambda state: emitted_states.append(state))

        # Toggle to expand
        card.toggle()
        self.assertFalse(card.is_collapsed())
        self.assertFalse(card._container.isHidden())
        self.assertEqual(card._toggle_btn.text(), "Hide Paths ▴")
        self.assertEqual(emitted_states, [True])

        # Toggle back to collapse
        card.toggle()
        self.assertTrue(card.is_collapsed())
        self.assertTrue(card._container.isHidden())
        self.assertEqual(card._toggle_btn.text(), "Show Paths ▾")
        self.assertEqual(emitted_states, [True, False])

    def test_settings_page_file_paths_collapsible(self):
        """Verify SettingsPage has collapsible paths card defaulting to collapsed."""
        settings = AppSettings()
        page = SettingsPage(settings=settings)

        self.assertTrue(hasattr(page, "_paths_card"), "SettingsPage should expose _paths_card")
        self.assertIsInstance(page._paths_card, CollapsibleSectionCard)
        self.assertTrue(page._paths_card.is_collapsed(), "File paths should default to collapsed")

        # Verify all 7 path edits exist and have proper values
        expected_attrs = [
            "patients_data_location",
            "vicon_files_location",
            "display_settings_location",
            "qtm_grpc_location",
            "initial_path_for_pdf",
            "norm_ave_gcd_filename",
            "norm_run_ave_gcd_filename",
        ]
        for attr in expected_attrs:
            field_name = f"_path_{attr}"
            self.assertTrue(hasattr(page, field_name), f"Missing {field_name}")
            val = getattr(page, field_name).text()
            self.assertEqual(val, str(getattr(settings, attr, "")))

        # Verify saving while collapsed works perfectly
        page._path_initial_path_for_pdf.setText("C:/Custom/PDF/Output")
        page._save()
        self.assertEqual(page._settings.initial_path_for_pdf, "C:/Custom/PDF/Output")

        # Verify expanding and collapsing UI
        page._paths_card.toggle()
        self.assertFalse(page._paths_card.is_collapsed())
        self.assertFalse(page._paths_card._container.isHidden())
        self.assertEqual(page._paths_card._toggle_btn.text(), "Hide File Paths ▴")


if __name__ == "__main__":
    unittest.main()
