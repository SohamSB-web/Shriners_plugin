# -*- coding: utf-8 -*-
"""
Shriners Gait Analysis Platform — Startup Loading & Splash Screen.

Provides a modern, high-DPI clinical splash screen displayed during application startup
while all heavy modules, matplotlib graphs, and UI components are loaded and rendered.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme.design_tokens import (
    COLOR_BORDER,
    COLOR_MUTED,
    COLOR_PRIMARY,
    COLOR_SURFACE,
    COLOR_TEXT,
    FONT_FAMILY,
    FONT_FAMILY_MONO,
    FONT_SIZE_BODY,
    FONT_SIZE_CAPTION,
    FONT_SIZE_H2,
    FONT_SIZE_H3,
    FONT_SIZE_SMALL,
    FONT_WEIGHT_BOLD,
    FONT_WEIGHT_MEDIUM,
    FONT_WEIGHT_SEMIBOLD,
    RADIUS_LG,
    RADIUS_MD,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
)
from app.ui.widgets.components import create_tinted_icon


class AppSplashScreen(QWidget):
    """
    Modern, clinical frameless startup loading screen with Shriners branding,
    real-time loading progress bar, and status messages.
    """

    def __init__(self, is_dark: bool = False, parent: QWidget | None = None):
        super().__init__(parent, Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._is_dark = is_dark
        self.setFixedSize(540, 310)

        self._init_ui()
        self._center_on_screen()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)

    def _init_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        # Elevated card container
        self._card = QFrame(self)
        self._card.setObjectName("splashCard")

        bg_col = "#0F172A" if self._is_dark else "#FFFFFF"
        border_col = "#334155" if self._is_dark else "#CBD5E1"
        text_col = "#F8FAFC" if self._is_dark else "#0F172A"
        muted_col = "#94A3B8" if self._is_dark else "#64748B"

        self._card.setStyleSheet(f"""
            QFrame#splashCard {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: {RADIUS_LG}px;
            }}
        """)

        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        card_layout.setSpacing(SPACE_MD)

        # ── Header with Emblem & Titles ──
        header_row = QHBoxLayout()
        header_row.setSpacing(SPACE_MD)

        icons_dir = Path(__file__).resolve().parent.parent.parent.parent / "resources" / "icons"
        emblem_path = icons_dir / "shriners_emblem.svg"
        if not emblem_path.is_file():
            emblem_path = icons_dir / "shriners_logo.png"

        self._logo_label = QLabel()
        self._logo_label.setFixedSize(48, 48)
        self._logo_label.setStyleSheet("background: transparent; border: none;")
        if emblem_path.is_file():
            ico = create_tinted_icon("shriners_emblem.svg", COLOR_PRIMARY, 48)
            self._logo_label.setPixmap(ico.pixmap(48, 48))
        header_row.addWidget(self._logo_label)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title_lbl = QLabel("SHRINERS HOSPITALS")
        title_lbl.setFont(QFont(FONT_FAMILY, 15, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {COLOR_PRIMARY}; background: transparent; border: none; letter-spacing: 0.5px;")
        title_box.addWidget(title_lbl)

        sub_lbl = QLabel("Gait Analysis Platform — Motion Analysis Center")
        sub_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, FONT_WEIGHT_SEMIBOLD))
        sub_lbl.setStyleSheet(f"color: {muted_col}; background: transparent; border: none;")
        title_box.addWidget(sub_lbl)

        header_row.addLayout(title_box, 1)

        # Version Pill Badge
        ver_lbl = QLabel("v2.0")
        ver_lbl.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_CAPTION, QFont.Bold))
        ver_lbl.setStyleSheet(f"""
            background-color: rgba(15, 118, 110, 0.12);
            color: {COLOR_PRIMARY};
            border: 1px solid rgba(15, 118, 110, 0.25);
            border-radius: 8px;
            padding: 3px 10px;
        """)
        header_row.addWidget(ver_lbl, 0, Qt.AlignTop)

        card_layout.addLayout(header_row)
        card_layout.addSpacing(4)

        # ── Status and Activity Message ──
        self._status_label = QLabel("Initializing clinical workstation...")
        self._status_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_MEDIUM))
        self._status_label.setStyleSheet(f"color: {text_col}; background: transparent; border: none;")
        card_layout.addWidget(self._status_label)

        # ── Progress Bar ──
        self._progress = QProgressBar()
        self._progress.setFixedHeight(8)
        self._progress.setRange(0, 100)
        self._progress.setValue(10)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {"#334155" if self._is_dark else "#E2E8F0"};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_PRIMARY};
                border-radius: 4px;
            }}
        """)
        card_layout.addWidget(self._progress)

        # ── Detail caption / percentage row ──
        detail_row = QHBoxLayout()
        self._detail_label = QLabel("Loading components...")
        self._detail_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION))
        self._detail_label.setStyleSheet(f"color: {muted_col}; background: transparent; border: none;")
        detail_row.addWidget(self._detail_label, 1)

        self._pct_label = QLabel("10%")
        self._pct_label.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_CAPTION, QFont.Bold))
        self._pct_label.setStyleSheet(f"color: {COLOR_PRIMARY}; background: transparent; border: none;")
        detail_row.addWidget(self._pct_label)

        card_layout.addLayout(detail_row)
        outer.addWidget(self._card)

    def set_progress(self, percent: int, message: str = "", detail: str = "") -> None:
        """Update loading progress, status text, and force Qt event dispatch."""
        self._progress.setValue(max(0, min(100, percent)))
        self._pct_label.setText(f"{percent}%")
        if message:
            self._status_label.setText(message)
        if detail:
            self._detail_label.setText(detail)
        QApplication.processEvents()

    def finish(self, window: QWidget) -> None:
        """Finish splash screen and transition cleanly to main window."""
        self.set_progress(100, "Workstation ready.", "Rendering completed.")
        QApplication.processEvents()
        self.close()
        self.deleteLater()
