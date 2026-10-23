# -*- coding: utf-8 -*-
"""
Application setup — QApplication creation, logging, and initialization.
"""

from __future__ import annotations

import logging
import os
import sys

# Register Conda Library/bin on Windows for DLL loading (MKL / LAPACK / PySide6 / Matplotlib)
if sys.platform == "win32":
    import ctypes
    _sys32_icu = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "icuuc.dll")
    if os.path.exists(_sys32_icu):
        try:
            ctypes.WinDLL(_sys32_icu)
        except Exception:
            pass

    _lib_bin = os.path.join(sys.prefix, "Library", "bin")
    if os.path.isdir(_lib_bin):
        if _lib_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = _lib_bin + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(_lib_bin)
            except Exception:
                pass

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from app.models.data_models import AppSettings
from app.services.settings_service import SettingsService
from app.ui.main_window import MainWindow
from app.ui.theme.design_tokens import FONT_FAMILY, FONT_SIZE_BODY
from app.ui.theme.theme_manager import get_light_qss

from app.ui.widgets.splash_screen import AppSplashScreen

logger = logging.getLogger(__name__)


def _register_custom_fonts() -> None:
    """Load bundled custom fonts into the application font database and matplotlib."""
    fonts_dir = Path(__file__).resolve().parent.parent / "resources" / "fonts"
    if fonts_dir.is_dir():
        for font_file in fonts_dir.glob("*.ttf"):
            font_path = str(font_file)
            QFontDatabase.addApplicationFont(font_path)
            try:
                import matplotlib.font_manager as fm
                fm.fontManager.addfont(font_path)
            except Exception:
                pass


def setup_logging() -> None:
    """Configure structured application logging."""
    log_format = (
        "%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s"
    )
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    # Suppress noisy libraries
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)


def create_application(show_splash: bool = True) -> tuple[QApplication, MainWindow]:
    """Create and configure the QApplication and MainWindow with startup loading screen."""

    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Shriners Gait Analysis Platform")
    app.setOrganizationName("Shriners Hospitals")
    app.setApplicationVersion("2.0.0")

    splash: Optional[AppSplashScreen] = None
    if show_splash:
        try:
            splash = AppSplashScreen()
            splash.show()
            splash.set_progress(15, "Initializing clinical workstation...", "Loading display & fonts")
        except Exception as e:
            logger.debug("Splash screen init note: %s", e)
            splash = None

    # Load custom application fonts (Inter)
    _register_custom_fonts()
    if splash:
        splash.set_progress(35, "Loading configuration...", "Reading system settings")

    # Set default font with subpixel anti-aliasing and quality rendering
    font = QFont(FONT_FAMILY, 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.PreferQuality)
    font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)
    app.setFont(font)

    # Load settings from existing configuration files
    settings_svc = SettingsService()
    app_settings = settings_svc.load_app_settings()

    if splash:
        splash.set_progress(55, "Applying theme...", "Configuring styling system")

    # Apply initial theme
    qss = get_light_qss()
    app.setStyleSheet(qss)

    if splash:
        splash.set_progress(75, "Building clinical modules...", "Rendering analysis workstations")

    # Create main window
    window = MainWindow(settings=app_settings, splash=splash)

    if splash:
        splash.set_progress(95, "Workstation ready.", "Rendering graphical layout")

    return app, window
