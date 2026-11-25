import sys
import os
from pathlib import Path
import unittest

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Register Conda Library/bin on Windows for DLLs
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
from app.ui.main_window import MainWindow


class TestThemeToggle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_theme_toggle(self):
        win = MainWindow()
        win.show()

        initial_mode = win._settings.dark_mode
        win._apply_theme(True)
        self.assertTrue(win._settings.dark_mode)

        win._apply_theme(False)
        self.assertFalse(win._settings.dark_mode)

        win._apply_theme(True)
        self.assertTrue(win._settings.dark_mode)

        settings_page = win._settings_page
        settings_page._light_radio.setChecked(True)
        self.assertFalse(win._settings.dark_mode)

        settings_page._dark_radio.setChecked(True)
        self.assertTrue(win._settings.dark_mode)

        win.close()


if __name__ == "__main__":
    unittest.main()
