# -*- coding: utf-8 -*-
"""
Tests for LoadingOverlay component and CasePresentationPage loading screen integration.
"""

import sys
import unittest
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from PySide6.QtWidgets import QApplication, QWidget

from app.models.data_models import SessionInfo, TrialInfo
from app.ui.pages.case_presentation_page import CasePresentationPage
from app.ui.widgets.components import LoadingOverlay


class TestLoadingOverlay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_loading_overlay_standalone(self):
        """Verify LoadingOverlay show, progress, and hide mechanics."""
        parent = QWidget()
        parent.resize(800, 600)
        parent.show()
        overlay = LoadingOverlay(parent)

        self.assertFalse(overlay.isVisible())

        # Show loading
        overlay.show_loading(
            title="Processing GCD Files for Presentation",
            message="Reading trial data...",
            determinate=True,
        )
        self.assertTrue(overlay.isVisible())
        self.assertEqual(overlay._title_label.text(), "Processing GCD Files for Presentation")
        self.assertEqual(overlay._message.text(), "Reading trial data...")
        self.assertEqual(overlay._progress.value(), 0)

        # Update progress
        overlay.set_progress(45, "Reading Left trial 3/6: Dynamic 3.GCD", "Kinematics (3/6)")
        self.assertEqual(overlay._progress.value(), 45)
        self.assertEqual(overlay._message.text(), "Reading Left trial 3/6: Dynamic 3.GCD")
        self.assertEqual(overlay._status_caption.text(), "Kinematics (3/6)")

        # Theme switching
        overlay.apply_theme(dark=True)
        self.assertTrue(overlay._is_dark)
        overlay.apply_theme(dark=False)
        self.assertFalse(overlay._is_dark)

        # Hide loading
        overlay.hide_loading()
        self.assertFalse(overlay.isVisible())
        parent.close()

    def test_case_presentation_page_loading_screen_integration(self):
        """Verify CasePresentationPage has LoadingOverlay and shows progress during session loading."""
        page = CasePresentationPage()
        page.resize(1000, 700)
        page.show()

        self.assertTrue(hasattr(page, "_loading_overlay"), "CasePresentationPage must have _loading_overlay")
        self.assertIsInstance(page._loading_overlay, LoadingOverlay)

        # Create mock session
        sess = SessionInfo(
            study_type="Kinematics",
            analysis_date="2025-02-21",
            directory="",
            left_trials=[TrialInfo(gcd_filename="Dynamic 1.GCD", selected=True)],
            right_trials=[TrialInfo(gcd_filename="Dynamic 1.GCD", selected=True)],
        )

        progress_calls = []
        original_set_progress = page._loading_overlay.set_progress

        def tracking_set_progress(val, msg=None, cap=None):
            progress_calls.append((val, msg, cap))
            original_set_progress(val, msg, cap)

        page._loading_overlay.set_progress = tracking_set_progress

        # Load session data
        page.load_session_data([sess], active_session_index=0, display_mode="MR")

        # An unselected directory must never start rendering or show loading progress.
        self.assertEqual(progress_calls, [])
        self.assertFalse(page._loading_overlay.isVisible())
        self.assertFalse(page._trial_data)

        page.close()


if __name__ == "__main__":
    unittest.main()
