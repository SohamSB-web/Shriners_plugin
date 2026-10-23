import sys
import os
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication, QMainWindow, QDialog
from app.ui.theme.theme_manager import apply_native_titlebar_theme
from app.ui.theme.design_tokens import LIGHT_PALETTE, DARK_PALETTE
from app.ui.main_window import MainWindow


class TestTitlebarTheme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_apply_native_titlebar_theme_direct(self):
        """Test apply_native_titlebar_theme on dummy QMainWindow in both light and dark."""
        win = QMainWindow()
        win.show()
        # Should execute safely on all platforms without raising
        apply_native_titlebar_theme(win, dark=False, bg_color="#FFFFFF", fg_color="#0F172A")
        apply_native_titlebar_theme(win, dark=True, bg_color="#0F172A", fg_color="#F8FAFC")
        win.close()

    def test_main_window_titlebar_sync(self):
        """Test MainWindow initializes with matching title bar theme and icon."""
        win = MainWindow()
        win.show()
        self.assertFalse(win.windowIcon().isNull(), "Window icon should be set and non-null")

        # Test theme toggle updates title bar
        win._apply_theme(True)
        self.assertTrue(win._settings.dark_mode)

        win._apply_theme(False)
        self.assertFalse(win._settings.dark_mode)

        win.close()


if __name__ == "__main__":
    unittest.main()
