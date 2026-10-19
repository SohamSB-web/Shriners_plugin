# -*- coding: utf-8 -*-
"""
MAC Case Presentation Page — Redesigned in PySide6 for Shriners Gait Analysis.

Modern clinical presentation workspace:
- Category sidebar: Kinematics, Sagittal Kinetics, Coronal Kinetics, EMG, Foot, Muscle Length/Velocity
- Side selector: Left / Right / Bilateral
- Trial selection filter pills (L1-L5, R1-R5, Mean, Norm band)
- 5x3 clinical plot grid with minimal axes, custom palettes, shaded norm bands
- Multi-session comparison and ReportLab PDF export.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set

import numpy as np

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.models.data_models import GCDData, PageSettings, SessionInfo
from app.services.gcd_service import GCDService
from app.services.pdf_report_service import CasePresentationPdfService
from app.services.settings_service import SettingsService
from app.ui.charts.clinical_plots import MultiPlotGrid
from app.ui.theme.design_tokens import (
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
    RADIUS_MD,
    RADIUS_ROUND,
    RADIUS_SM,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
    LIGHT_PALETTE,
    DARK_PALETTE,
)
from app.ui.widgets.components import LoadingOverlay
from app.ui.widgets.smooth_scroll import apply_smooth_scroll

logger = logging.getLogger(__name__)

# ── Clinical Trial Color Palettes ─────────────────────────────────
# Distinct, high-contrast colors differentiating each trial trace and its toe-off line
TRIAL_COLORS: Dict[str, str] = {
    # Left trials (cool/distinct palette: Blue, Green, Orange, Purple, Teal, Indigo, Olive, Deep Teal, Sky Blue, Magenta)
    "L1": "#2563EB",  # Royal Blue
    "L2": "#16A34A",  # Emerald Green
    "L3": "#EA580C",  # Vibrant Orange
    "L4": "#9333EA",  # Purple
    "L5": "#0891B2",  # Cyan / Teal
    "L6": "#4F46E5",  # Indigo
    "L7": "#65A30D",  # Lime / Olive
    "L8": "#0D9488",  # Deep Teal
    "L9": "#0284C7",  # Deep Sky Blue
    "L10": "#C026D3", # Magenta

    # Right trials (warm/distinct palette: Red, Amber, Rose, Violet, Bronze, Crimson, Burnt Orange, Ruby, Gold Brown, Raspberry)
    "R1": "#DC2626",  # Crimson Red
    "R2": "#D97706",  # Amber / Gold
    "R3": "#DB2777",  # Deep Rose
    "R4": "#7C3AED",  # Violet
    "R5": "#92400E",  # Warm Bronze
    "R6": "#E11D48",  # Bright Crimson
    "R7": "#C2410C",  # Burnt Orange
    "R8": "#BE123C",  # Ruby Red
    "R9": "#A16207",  # Golden Brown
    "R10": "#9F1239", # Dark Raspberry

    # Mean curves
    "Mean": "#0F172A",  # Slate 900 (User Text)
    "Mean_L": "#2563EB",  # Royal Blue (Clinical Left standard)
    "Mean_R": "#DC2626",  # Crimson Red (Clinical Right standard)
}

DARK_TRIAL_COLORS: Dict[str, str] = {
    # Left trials (brightened for high contrast against dark backgrounds)
    "L1": "#3B82F6",  # Light Royal Blue
    "L2": "#22C55E",  # Light Emerald Green
    "L3": "#FB923C",  # Light Vibrant Orange
    "L4": "#A855F7",  # Light Purple
    "L5": "#06B6D4",  # Light Cyan
    "L6": "#818CF8",  # Light Indigo
    "L7": "#A3E635",  # Light Lime
    "L8": "#2DD4BF",  # Light Teal
    "L9": "#38BDF8",  # Sky Blue
    "L10": "#E879F9", # Light Magenta

    # Right trials (brightened for high contrast against dark backgrounds)
    "R1": "#EF4444",  # Light Crimson Red
    "R2": "#FBBF24",  # Light Amber
    "R3": "#F472B6",  # Light Rose
    "R4": "#A78BFA",  # Light Violet
    "R5": "#F59E0B",  # Light Warm Bronze
    "R6": "#FB7185",  # Light Rose Red
    "R7": "#FB923C",  # Light Red Orange
    "R8": "#FDA4AF",  # Light Ruby
    "R9": "#FDE047",  # Light Gold
    "R10": "#F43F5E", # Light Raspberry

    # Mean curves
    "Mean": "#FAFAFA",  # White
    "Mean_L": "#38BDF8",  # Bright Sky Blue / Cyan (Clinical Left dark standard)
    "Mean_R": "#F87171",  # Vibrant Coral / Light Red (Clinical Right dark standard)
}


class PresentationSidebar(QFrame):
    """Left category navigation for MAC Case Presentation."""

    category_changed = Signal(str)
    side_changed = Signal(str)

    CATEGORIES = [
        ("Kinematics", "kinematics"),
        ("Sagittal Kinetics", "sagittal_kinetics"),
        ("Coronal Kinetics", "coronal_kinetics"),
        ("Dynamic EMG", "emg"),
        ("Foot Kinematics", "foot_kinematics"),
        ("Muscle Length", "muscle_length"),
        ("Muscle Velocity", "muscle_velocity"),
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setObjectName("presentationSidebar")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        layout.setSpacing(SPACE_SM)

        # Title
        self._title_lbl = QLabel("ANALYSIS")
        self._title_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        layout.addWidget(self._title_lbl)

        # Category buttons
        self._buttons: Dict[str, QPushButton] = {}
        for label, key in self.CATEGORIES:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_MEDIUM))
            btn.clicked.connect(lambda checked, k=key: self._on_cat_clicked(k))
            layout.addWidget(btn)
            self._buttons[key] = btn

        layout.addSpacing(SPACE_LG)

        # Side selector
        self._side_lbl = QLabel("LIMB DISPLAY")
        self._side_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        layout.addWidget(self._side_lbl)

        side_row = QHBoxLayout()
        side_row.setSpacing(4)
        self._side_buttons: Dict[str, QPushButton] = {}
        for label, key in [("Left", "L"), ("Right", "R"), ("L / R", "LR")]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, FONT_WEIGHT_MEDIUM))
            btn.clicked.connect(lambda checked, k=key: self._on_side_clicked(k))
            side_row.addWidget(btn)
            self._side_buttons[key] = btn

        layout.addLayout(side_row)
        layout.addStretch()

        self._active_category = "kinematics"
        self._active_side = "LR"
        self._is_dark = False
        self.apply_theme(dark=False)

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        self._is_dark = dark
        bg = "#141414" if dark else "#FFFFFF"
        border = "#27272A" if dark else (palette.border if palette else LIGHT_PALETTE.border)
        border_focus = "#FAFAFA" if dark else (palette.border_focus if palette else LIGHT_PALETTE.border_focus)
        label_col = "#A1A1AA" if dark else "#808080"

        self.setStyleSheet(
            f"QFrame#presentationSidebar {{"
            f"  background-color: {bg};"
            f"  border: 1px solid {border};"
            f"  border-radius: {RADIUS_MD}px;"
            f"}}"
            f"QFrame#presentationSidebar:hover {{"
            f"  border-color: {border_focus};"
            f"}}"
        )
        self._title_lbl.setStyleSheet(f"color: {label_col}; letter-spacing: 1.5px; border: none;")
        self._side_lbl.setStyleSheet(f"color: {label_col}; letter-spacing: 1px; border: none;")

        # Category buttons style
        if dark:
            cat_qss = (
                "QPushButton {"
                "  text-align: left; padding: 8px 12px; border: none; border-radius: 6px;"
                "  color: #CBD5E1; background: transparent;"
                "}"
                "QPushButton:hover { background-color: #1E293B; color: #FFFFFF; }"
                "QPushButton[active='true'] {"
                "  background-color: #0F766E; color: #FFFFFF; font-weight: 600;"
                "}"
            )
            side_qss = (
                "QPushButton {"
                "  padding: 6px 10px; border: 1px solid #334155; border-radius: 4px;"
                "  color: #CBD5E1; background: #0F172A;"
                "}"
                "QPushButton:hover { background: #1E293B; }"
                "QPushButton[active='true'] {"
                "  background-color: #0F766E; color: #FFFFFF; border-color: #14B8A6; font-weight: 600;"
                "}"
            )
        else:
            cat_qss = (
                "QPushButton {"
                "  text-align: left; padding: 8px 12px; border: none; border-radius: 6px;"
                "  color: #0F172A; background: transparent;"
                "}"
                "QPushButton:hover { background-color: #F8FAFC; color: #0F766E; }"
                "QPushButton[active='true'] {"
                "  background-color: #F0FDFA; color: #0F766E; font-weight: 600;"
                "}"
            )
            side_qss = (
                "QPushButton {"
                "  padding: 6px 10px; border: 1px solid #E2E8F0; border-radius: 4px;"
                "  color: #0F172A; background: #FFFFFF;"
                "}"
                "QPushButton:hover { background: #F8FAFC; }"
                "QPushButton[active='true'] {"
                "  background-color: #0F766E; color: #FFFFFF; border-color: #0F766E; font-weight: 600;"
                "}"
            )

        for btn in self._buttons.values():
            btn.setStyleSheet(cat_qss)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        for btn in self._side_buttons.values():
            btn.setStyleSheet(side_qss)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_cat_clicked(self, key: str) -> None:
        self._active_category = key
        for k, btn in self._buttons.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.category_changed.emit(key)

    def _on_side_clicked(self, key: str) -> None:
        self._active_side = key
        for k, btn in self._side_buttons.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.side_changed.emit(key)

    def select_default(self) -> None:
        self._on_cat_clicked("kinematics")
        self._on_side_clicked("LR")


class CasePresentationPage(QWidget):
    """
    Unified MAC Case Presentation Workspace.
    Connects static calibration, dynamic trials, and comprehensive gait analysis.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._settings_svc = SettingsService()
        self._gcd_svc = GCDService()

        # Data state
        self._current_category = "kinematics"
        self._current_side = "LR"
        self._trial_data: Dict[str, GCDData] = {}
        self._norm_data: Optional[GCDData] = None
        self._active_trial_filter: Set[str] = {
            f"L{i}" for i in range(1, 11)
        } | {
            f"R{i}" for i in range(1, 11)
        }
        self._show_norm_band: bool = True
        self._is_dark: bool = False
        self._session_path: str = ""
        self._display_mode: str = "MR"
        self._sessions: List[SessionInfo] = []
        self._current_session_idx: int = 0
        self._mr_left_key: Optional[str] = None
        self._mr_right_key: Optional[str] = None
        self._session_date: str = ""
        self._study_type: str = ""
        self._activity_type: str = ""
        self._orthosis: str = ""
        self._assist: str = ""

        self._init_ui()
        self._update_pill_visibility()
        self._load_default_norm()
        self._refresh_plots(show_overlay=False)

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Category Sidebar
        self._sidebar = PresentationSidebar()
        self._sidebar.category_changed.connect(self._on_category_changed)
        self._sidebar.side_changed.connect(self._on_side_changed)
        main_layout.addWidget(self._sidebar)

        # 2. Right Analytical Area
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        right_layout.setSpacing(SPACE_SM)

        self._header_card = QFrame()
        self._header_card.setObjectName("headerCard")
        self._header_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header_card_layout = QVBoxLayout(self._header_card)
        header_card_layout.setContentsMargins(16, 12, 16, 14)
        header_card_layout.setSpacing(8)
        header_card_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)

        # ── Row 1: Title, Clinical Badges & Action Buttons ─────────
        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.setAlignment(Qt.AlignVCenter)

        self._title_label = QLabel("CASE PRESENTATION")
        self._title_label.setFont(QFont(FONT_FAMILY, 15, QFont.Bold))
        self._title_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._title_label.setFixedHeight(34)
        top_row.addWidget(self._title_label)

        self._badges_container = QWidget()
        self._badges_container.setFixedHeight(34)
        self._badges_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        badges_layout = QHBoxLayout(self._badges_container)
        badges_layout.setContentsMargins(0, 2, 0, 2)
        badges_layout.setSpacing(6)
        badges_layout.setAlignment(Qt.AlignVCenter)

        self._category_badge = QLabel("Kinematics")
        self._category_badge.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        self._category_badge.setFixedHeight(30)
        self._category_badge.setAlignment(Qt.AlignCenter)
        badges_layout.addWidget(self._category_badge)

        self._side_badge = QLabel("Left Limb")
        self._side_badge.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        self._side_badge.setFixedHeight(30)
        self._side_badge.setAlignment(Qt.AlignCenter)
        badges_layout.addWidget(self._side_badge)

        self._mode_badge = QLabel("MR Mode")
        self._mode_badge.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Medium))
        self._mode_badge.setFixedHeight(30)
        self._mode_badge.setAlignment(Qt.AlignCenter)
        badges_layout.addWidget(self._mode_badge)

        # Session Switcher Dropdown (visible when multiple sessions exist)
        self._session_combo = QComboBox()
        self._session_combo.setObjectName("sessionSelectorCombo")
        self._session_combo.setFixedHeight(30)
        self._session_combo.setMinimumWidth(220)
        self._session_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self._session_combo.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        self._session_combo.setCursor(Qt.PointingHandCursor)
        self._session_combo.setToolTip("Switch active session to display in Case Presentation")
        self._session_combo.setVisible(False)
        self._session_combo.currentIndexChanged.connect(self._on_session_combo_changed)
        badges_layout.addWidget(self._session_combo)

        self._meta_badge = QLabel("")
        self._meta_badge.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Medium))
        self._meta_badge.setFixedHeight(30)
        self._meta_badge.setAlignment(Qt.AlignCenter)
        badges_layout.addWidget(self._meta_badge)

        top_row.addWidget(self._badges_container, 0, Qt.AlignVCenter)
        top_row.addStretch()

        # Action Buttons on Right with Fixed Sizing & Uncompromised Widths
        self._norm_btn = QPushButton("Norm Band")
        self._norm_btn.setCheckable(True)
        self._norm_btn.setChecked(True)
        self._norm_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Medium))
        self._norm_btn.setFixedHeight(30)
        self._norm_btn.setMinimumWidth(95)
        self._norm_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._norm_btn.setCursor(Qt.PointingHandCursor)
        self._norm_btn.toggled.connect(self._on_norm_toggled)
        top_row.addWidget(self._norm_btn)

        self._open_btn = QPushButton("Open Session…")
        self._open_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Medium))
        self._open_btn.setFixedHeight(30)
        self._open_btn.setMinimumWidth(115)
        self._open_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._open_btn.setCursor(Qt.PointingHandCursor)
        self._open_btn.clicked.connect(self._on_open_folder_clicked)
        top_row.addWidget(self._open_btn)
        self._open_btn.hide()

        self._pdf_btn = QPushButton("Export PDF")
        self._pdf_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        self._pdf_btn.setFixedHeight(30)
        self._pdf_btn.setMinimumWidth(105)
        self._pdf_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._pdf_btn.setCursor(Qt.PointingHandCursor)
        self._pdf_btn.clicked.connect(self._on_export_pdf_clicked)
        top_row.addWidget(self._pdf_btn)

        header_card_layout.addLayout(top_row)

        # ── Trial Filter Pills & Batch Controls ───────────────────
        self._pill_buttons: Dict[str, QPushButton] = {}

        # Row 2 (Primary trial row: Left trials by default, or Right when in R mode)
        self._row_left = QWidget()
        self._row_left.setFixedHeight(40)
        self._row_left_layout = QHBoxLayout(self._row_left)
        self._row_left_layout.setContentsMargins(0, 0, 0, 0)
        self._row_left_layout.setSpacing(8)

        # Left Limb Trials Container
        self._left_container = QWidget()
        self._left_container.setFixedHeight(40)
        left_pills_layout = QHBoxLayout(self._left_container)
        left_pills_layout.setContentsMargins(0, 5, 0, 5)
        left_pills_layout.setSpacing(3)

        self._left_label = QLabel("LEFT")
        self._left_label.setFixedSize(48, 30)
        self._left_label.setAlignment(Qt.AlignCenter)
        self._left_label.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        self._left_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        left_pills_layout.addWidget(self._left_label)

        for i in range(1, 11):
            k = f"L{i}"
            btn = QPushButton(k)
            btn.setCheckable(True)
            btn.setChecked(True)
            btn.setFixedSize(30, 30)
            btn.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
            btn.setCursor(Qt.PointingHandCursor)
            self._style_pill_button(btn, k, checked=True)
            btn.toggled.connect(lambda checked, tk=k: self._on_filter_toggled(tk, checked))
            left_pills_layout.addWidget(btn)
            self._pill_buttons[k] = btn

        # Divider before Left Mean
        self._sep_l_mean = QFrame()
        self._sep_l_mean.setFrameShape(QFrame.VLine)
        self._sep_l_mean.setFixedWidth(1)
        self._sep_l_mean.setFixedHeight(22)
        left_pills_layout.addWidget(self._sep_l_mean)

        # Left Mean curve pill
        mean_l_btn = QPushButton("L Mean")
        mean_l_btn.setCheckable(True)
        mean_l_btn.setChecked(False)
        mean_l_btn.setFixedSize(62, 30)
        mean_l_btn.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        mean_l_btn.setCursor(Qt.PointingHandCursor)
        mean_l_btn.setToolTip("Toggle Left Limb Mean curve (averaged over active Left trials L1-L10)")
        self._style_pill_button(mean_l_btn, "Mean_L", checked=False)
        mean_l_btn.toggled.connect(lambda checked: self._on_filter_toggled("Mean_L", checked))
        left_pills_layout.addWidget(mean_l_btn)
        self._pill_buttons["Mean_L"] = mean_l_btn

        self._row_left_layout.addWidget(self._left_container)

        # Actions Container: Mean pill + Batch actions ([All], [Clear], [MR Only])
        self._actions_container = QWidget()
        self._actions_container.setFixedHeight(40)
        actions_layout = QHBoxLayout(self._actions_container)
        actions_layout.setContentsMargins(0, 5, 0, 5)
        actions_layout.setSpacing(4)

        # Divider between Trials and Actions
        self._sep_actions = QFrame()
        self._sep_actions.setFrameShape(QFrame.VLine)
        self._sep_actions.setFixedWidth(1)
        self._sep_actions.setFixedHeight(24)
        actions_layout.addWidget(self._sep_actions)

        # Master Mean curve pill
        mean_btn = QPushButton("Mean")
        mean_btn.setCheckable(True)
        mean_btn.setChecked(False)
        mean_btn.setFixedSize(50, 30)
        mean_btn.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        mean_btn.setCursor(Qt.PointingHandCursor)
        mean_btn.setToolTip("Toggle Mean curve (shows Left and Right limb means separately in Bilateral mode)")
        self._style_pill_button(mean_btn, "Mean", checked=False)
        mean_btn.toggled.connect(lambda checked: self._on_filter_toggled("Mean", checked))
        actions_layout.addWidget(mean_btn)
        self._pill_buttons["Mean"] = mean_btn

        # Quick batch actions
        self._quick_all_btn = QPushButton("All")
        self._quick_all_btn.setFont(QFont(FONT_FAMILY, 8, QFont.Medium))
        self._quick_all_btn.setFixedSize(36, 30)
        self._quick_all_btn.setCursor(Qt.PointingHandCursor)
        self._quick_all_btn.clicked.connect(self._select_all_trials)
        actions_layout.addWidget(self._quick_all_btn)

        self._quick_none_btn = QPushButton("Clear")
        self._quick_none_btn.setFont(QFont(FONT_FAMILY, 8, QFont.Medium))
        self._quick_none_btn.setFixedSize(44, 30)
        self._quick_none_btn.setCursor(Qt.PointingHandCursor)
        self._quick_none_btn.clicked.connect(self._clear_all_trials)
        actions_layout.addWidget(self._quick_none_btn)

        self._quick_mr_btn = QPushButton("MR Only")
        self._quick_mr_btn.setFont(QFont(FONT_FAMILY, 8, QFont.Medium))
        self._quick_mr_btn.setFixedSize(68, 30)
        self._quick_mr_btn.setCursor(Qt.PointingHandCursor)
        self._quick_mr_btn.clicked.connect(self._select_mr_only)
        actions_layout.addWidget(self._quick_mr_btn)

        self._row_left_layout.addWidget(self._actions_container)
        self._row_left_layout.addStretch()
        header_card_layout.addWidget(self._row_left)

        # Row 3 (Secondary trial row: Right trials when in Bilateral mode)
        self._row_right = QWidget()
        self._row_right.setFixedHeight(40)
        self._row_right_layout = QHBoxLayout(self._row_right)
        self._row_right_layout.setContentsMargins(0, 0, 0, 0)
        self._row_right_layout.setSpacing(8)

        # Right Limb Trials Container
        self._right_container = QWidget()
        self._right_container.setFixedHeight(40)
        right_pills_layout = QHBoxLayout(self._right_container)
        right_pills_layout.setContentsMargins(0, 5, 0, 5)
        right_pills_layout.setSpacing(3)

        self._right_label = QLabel("RIGHT")
        self._right_label.setFixedSize(48, 30)
        self._right_label.setAlignment(Qt.AlignCenter)
        self._right_label.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        self._right_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        right_pills_layout.addWidget(self._right_label)

        for i in range(1, 11):
            k = f"R{i}"
            btn = QPushButton(k)
            btn.setCheckable(True)
            btn.setChecked(True)
            btn.setFixedSize(30, 30)
            btn.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
            btn.setCursor(Qt.PointingHandCursor)
            self._style_pill_button(btn, k, checked=True)
            btn.toggled.connect(lambda checked, tk=k: self._on_filter_toggled(tk, checked))
            right_pills_layout.addWidget(btn)
            self._pill_buttons[k] = btn

        # Divider before Right Mean
        self._sep_r_mean = QFrame()
        self._sep_r_mean.setFrameShape(QFrame.VLine)
        self._sep_r_mean.setFixedWidth(1)
        self._sep_r_mean.setFixedHeight(22)
        right_pills_layout.addWidget(self._sep_r_mean)

        # Right Mean curve pill
        mean_r_btn = QPushButton("R Mean")
        mean_r_btn.setCheckable(True)
        mean_r_btn.setChecked(False)
        mean_r_btn.setFixedSize(62, 30)
        mean_r_btn.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        mean_r_btn.setCursor(Qt.PointingHandCursor)
        mean_r_btn.setToolTip("Toggle Right Limb Mean curve (averaged over active Right trials R1-R10)")
        self._style_pill_button(mean_r_btn, "Mean_R", checked=False)
        mean_r_btn.toggled.connect(lambda checked: self._on_filter_toggled("Mean_R", checked))
        right_pills_layout.addWidget(mean_r_btn)
        self._pill_buttons["Mean_R"] = mean_r_btn

        self._row_right_layout.addWidget(self._right_container)
        self._row_right_layout.addStretch()
        header_card_layout.addWidget(self._row_right)

        # Row 4: Clinical Bilateral Mean Legend Bar (dynamically visible when Mean is active in Bilateral mode)
        self._mean_legend_bar = QFrame()
        self._mean_legend_bar.setObjectName("meanLegendBar")
        self._mean_legend_bar.setFixedHeight(28)
        mean_leg_layout = QHBoxLayout(self._mean_legend_bar)
        mean_leg_layout.setContentsMargins(10, 0, 10, 0)
        mean_leg_layout.setSpacing(12)

        self._mean_leg_title = QLabel("CLINICAL MEAN:")
        self._mean_leg_title.setFont(QFont(FONT_FAMILY, 7, QFont.Bold))
        mean_leg_layout.addWidget(self._mean_leg_title)

        self._mean_leg_l_label = QLabel("╍╍ Left Mean (Royal Blue)")
        self._mean_leg_l_label.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        mean_leg_layout.addWidget(self._mean_leg_l_label)

        self._mean_leg_r_label = QLabel("╍╍ Right Mean (Crimson Red)")
        self._mean_leg_r_label.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        mean_leg_layout.addWidget(self._mean_leg_r_label)

        self._mean_leg_toe_label = QLabel("┆ Vertical dashed lines = Limb Toe-Off")
        self._mean_leg_toe_label.setFont(QFont(FONT_FAMILY, 7, QFont.Medium))
        mean_leg_layout.addWidget(self._mean_leg_toe_label)

        mean_leg_layout.addStretch()

        self._mean_leg_tip_label = QLabel("Tip: Double-click any chart for enlarged inspection")
        self._mean_leg_tip_label.setFont(QFont(FONT_FAMILY, 7, QFont.Normal))
        mean_leg_layout.addWidget(self._mean_leg_tip_label)

        header_card_layout.addWidget(self._mean_legend_bar)
        self._mean_legend_bar.setVisible(False)

        right_layout.addWidget(self._header_card)

        # Clinical Multi-Plot Grid (5 rows x 3 cols)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)

        self._plot_grid = MultiPlotGrid(rows=5, cols=3)
        self._scroll.setWidget(self._plot_grid)
        right_layout.addWidget(self._scroll, 1)

        # 60 FPS kinetic smooth scrolling: install filter on scroll area, plot grid, all canvases, header card, sidebar, and page
        self._smooth_scroll = apply_smooth_scroll(self._scroll)
        self._plot_grid.installEventFilter(self._smooth_scroll)
        for canvas in self._plot_grid.get_all_canvases():
            canvas.installEventFilter(self._smooth_scroll)
        self._header_card.installEventFilter(self._smooth_scroll)
        self._sidebar.installEventFilter(self._smooth_scroll)
        right_container.installEventFilter(self._smooth_scroll)
        self.installEventFilter(self._smooth_scroll)

        main_layout.addWidget(right_container, 1)

        # 3. Clinical Loading Overlay (covers whole presentation workspace)
        self._loading_overlay = LoadingOverlay(self)

        self._is_dark = False
        self.apply_theme(dark=False)
        self._sidebar.select_default()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_loading_overlay") and self._loading_overlay:
            self._loading_overlay.resize(self.size())

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        """Propagate dark/light theme to CasePresentation toolbar, sidebar, and plot grid."""
        self._is_dark = dark

        if hasattr(self, "_loading_overlay") and self._loading_overlay:
            self._loading_overlay.apply_theme(palette, dark)

        if hasattr(self, "_header_card"):
            if dark:
                self._header_card.setStyleSheet(
                    "QFrame#headerCard { background: #1E293B; border: 1px solid #334155; border-radius: 8px; }"
                )
            else:
                self._header_card.setStyleSheet(
                    "QFrame#headerCard { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }"
                )

        title_col = "#F8FAFC" if dark else "#0F172A"
        self._title_label.setStyleSheet(f"color: {title_col}; font-weight: 800;")

        # Badges styling
        if hasattr(self, "_category_badge"):
            if dark:
                self._category_badge.setStyleSheet("background: #134E4A; color: #2DD4BF; border: 1px solid #14B8A6; border-radius: 4px; padding: 0px 8px; font-weight: 600; min-height: 30px; max-height: 30px;")
                self._side_badge.setStyleSheet("background: #0F172A; color: #94A3B8; border: 1px solid #334155; border-radius: 4px; padding: 0px 8px; font-weight: 600; min-height: 30px; max-height: 30px;")
                self._mode_badge.setStyleSheet("background: #312E81; color: #A5B4FC; border: 1px solid #6366F1; border-radius: 4px; padding: 0px 8px; min-height: 30px; max-height: 30px;")
                self._meta_badge.setStyleSheet("background: #1E293B; color: #94A3B8; border: 1px solid #334155; border-radius: 4px; padding: 0px 8px; font-weight: 600; font-size: 11px; min-height: 30px; max-height: 30px;")
                self._left_label.setStyleSheet("background: #1E293B; color: #60A5FA; border: 1px solid #2563EB; border-radius: 4px; font-weight: 800;")
                self._right_label.setStyleSheet("background: #1E293B; color: #F87171; border: 1px solid #DC2626; border-radius: 4px; font-weight: 800;")
                if hasattr(self, "_sep_actions"):
                    self._sep_actions.setStyleSheet("background: #334155;")
            else:
                self._category_badge.setStyleSheet("background: #F0FDFA; color: #0F766E; border: 1px solid #99F6E4; border-radius: 4px; padding: 0px 8px; font-weight: 600; min-height: 30px; max-height: 30px;")
                self._side_badge.setStyleSheet("background: #F8FAFC; color: #334155; border: 1px solid #CBD5E1; border-radius: 4px; padding: 0px 8px; font-weight: 600; min-height: 30px; max-height: 30px;")
                self._mode_badge.setStyleSheet("background: #EEF2FF; color: #4338CA; border: 1px solid #C7D2FE; border-radius: 4px; padding: 0px 8px; min-height: 30px; max-height: 30px;")
                self._meta_badge.setStyleSheet("background: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; border-radius: 4px; padding: 0px 8px; font-weight: 600; font-size: 11px; min-height: 30px; max-height: 30px;")
                self._left_label.setStyleSheet("background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; border-radius: 4px; font-weight: 800;")
                self._right_label.setStyleSheet("background: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; border-radius: 4px; font-weight: 800;")
                if hasattr(self, "_sep_actions"):
                    self._sep_actions.setStyleSheet("background: #E2E8F0;")

        # Session switcher combo styling
        if hasattr(self, "_session_combo"):
            icons_dir = Path(__file__).resolve().parent.parent.parent.parent / "resources" / "icons"
            arrow_svg_dark = (icons_dir / "chevron_down_teal_dark.svg").as_posix()
            arrow_svg_light = (icons_dir / "chevron_down_teal.svg").as_posix()

            if dark:
                self._session_combo.setStyleSheet(f"""
                    QComboBox#sessionSelectorCombo {{
                        background-color: #134E4A;
                        color: #2DD4BF;
                        border: 1px solid #14B8A6;
                        border-radius: 4px;
                        padding: 0px 22px 0px 8px;
                        font-weight: 600;
                        font-size: 11px;
                        min-height: 30px;
                        max-height: 30px;
                    }}
                    QComboBox#sessionSelectorCombo:hover {{
                        background-color: #115E59;
                        border-color: #2DD4BF;
                    }}
                    QComboBox#sessionSelectorCombo::drop-down {{
                        subcontrol-origin: padding;
                        subcontrol-position: center right;
                        width: 18px;
                        border: none;
                        background: transparent;
                    }}
                    QComboBox#sessionSelectorCombo::down-arrow {{
                        image: url('{arrow_svg_dark}');
                        width: 10px;
                        height: 10px;
                        margin-right: 4px;
                    }}
                    QComboBox#sessionSelectorCombo QAbstractItemView {{
                        background: #1E293B;
                        color: #F8FAFC;
                        selection-background-color: #0F766E;
                        selection-color: #FFFFFF;
                        border: 1px solid #334155;
                        border-radius: 4px;
                        padding: 2px;
                    }}
                """)
            else:
                self._session_combo.setStyleSheet(f"""
                    QComboBox#sessionSelectorCombo {{
                        background-color: #F0FDFA;
                        color: #0F766E;
                        border: 1px solid #14B8A6;
                        border-radius: 4px;
                        padding: 0px 22px 0px 8px;
                        font-weight: 600;
                        font-size: 11px;
                        min-height: 30px;
                        max-height: 30px;
                    }}
                    QComboBox#sessionSelectorCombo:hover {{
                        background-color: #CCFBF1;
                        border-color: #0D9488;
                    }}
                    QComboBox#sessionSelectorCombo::drop-down {{
                        subcontrol-origin: padding;
                        subcontrol-position: center right;
                        width: 18px;
                        border: none;
                        background: transparent;
                    }}
                    QComboBox#sessionSelectorCombo::down-arrow {{
                        image: url('{arrow_svg_light}');
                        width: 10px;
                        height: 10px;
                        margin-right: 4px;
                    }}
                    QComboBox#sessionSelectorCombo QAbstractItemView {{
                        background: #FFFFFF;
                        color: #0F172A;
                        selection-background-color: #F0FDFA;
                        selection-color: #0F766E;
                        border: 1px solid #CBD5E1;
                        border-radius: 4px;
                        padding: 2px;
                    }}
                """)

        # Quick batch buttons
        for btn in (getattr(self, "_quick_all_btn", None), getattr(self, "_quick_none_btn", None), getattr(self, "_quick_mr_btn", None)):
            if btn:
                if dark:
                    btn.setStyleSheet("QPushButton { background: #0F172A; color: #94A3B8; border: 1px solid #334155; border-radius: 4px; padding: 0px; min-height: 30px; max-height: 30px; font-weight: 600; } QPushButton:hover { background: #334155; color: #F8FAFC; }")
                else:
                    btn.setStyleSheet("QPushButton { background: #F8FAFC; color: #475569; border: 1px solid #CBD5E1; border-radius: 4px; padding: 0px; min-height: 30px; max-height: 30px; font-weight: 600; } QPushButton:hover { background: #E2E8F0; color: #0F172A; }")

        # Re-style trial pills with their specific colors
        for key, p_btn in self._pill_buttons.items():
            self._style_pill_button(p_btn, key, p_btn.isChecked())
            p_btn.style().unpolish(p_btn)
            p_btn.style().polish(p_btn)

        if dark:
            norm_qss = (
                "QPushButton { background: #0F172A; color: #94A3B8; border: 1px solid #334155; border-radius: 4px; padding: 4px 10px; font-weight: 600; }"
                "QPushButton:checked { background: #134E4A; color: #2DD4BF; font-weight: 600; border-color: #14B8A6; }"
            )
            open_qss = (
                "QPushButton { background: #1E293B; color: #14B8A6; border: 1.5px solid #14B8A6; border-radius: 4px; padding: 4px 12px; font-weight: 600; }"
                "QPushButton:hover { background: #334155; }"
            )
            pdf_qss = (
                "QPushButton { background: #0F766E; color: #FFFFFF; border: 1px solid #14B8A6; border-radius: 4px; padding: 5px 14px; font-weight: 600; }"
                "QPushButton:hover { background: #115E59; }"
            )
        else:
            norm_qss = (
                "QPushButton { background: #F8FAFC; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px 10px; font-weight: 600; }"
                "QPushButton:checked { background: #F0FDFA; color: #0F766E; font-weight: 600; border-color: #0F766E; }"
            )
            open_qss = (
                "QPushButton { background: #FFFFFF; color: #0F766E; border: 1.5px solid #0F766E; border-radius: 4px; padding: 4px 12px; font-weight: 600; }"
                "QPushButton:hover { background: #F0FDFA; }"
            )
            pdf_qss = (
                "QPushButton { background: #0F766E; color: #FFFFFF; border: 1px solid #0F766E; border-radius: 4px; padding: 5px 14px; font-weight: 600; }"
                "QPushButton:hover { background: #115E59; }"
            )

        self._norm_btn.setStyleSheet(norm_qss)
        self._open_btn.setStyleSheet(open_qss)
        self._pdf_btn.setStyleSheet(pdf_qss)

        if hasattr(self, "_mean_legend_bar"):
            if dark:
                self._mean_legend_bar.setStyleSheet(
                    "QFrame#meanLegendBar { background: #0F172A; border: 1px solid #334155; border-radius: 4px; }"
                )
                self._mean_leg_title.setStyleSheet("color: #94A3B8; font-weight: bold;")
                self._mean_leg_l_label.setStyleSheet("color: #38BDF8; font-weight: bold;")
                self._mean_leg_r_label.setStyleSheet("color: #F87171; font-weight: bold;")
                self._mean_leg_toe_label.setStyleSheet("color: #94A3B8;")
                self._mean_leg_tip_label.setStyleSheet("color: #64748B;")
            else:
                self._mean_legend_bar.setStyleSheet(
                    "QFrame#meanLegendBar { background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 4px; }"
                )
                self._mean_leg_title.setStyleSheet("color: #475569; font-weight: bold;")
                self._mean_leg_l_label.setStyleSheet("color: #1D4ED8; font-weight: bold;")
                self._mean_leg_r_label.setStyleSheet("color: #DC2626; font-weight: bold;")
                self._mean_leg_toe_label.setStyleSheet("color: #475569;")
                self._mean_leg_tip_label.setStyleSheet("color: #64748B;")

        self._sidebar.apply_theme(palette, dark)
        self._plot_grid.apply_theme(palette, dark)
        self._refresh_plots(show_overlay=False)

    def _load_default_norm(self) -> None:
        """Attempt to load default normative data file."""
        candidates = [
            Path(__file__).resolve().parent.parent.parent.parent / "MAC_CasePresentation" / "TD_Run_Ave.GCD",
            Path.cwd() / "MAC_CasePresentation" / "TD_Ave.GCD",
            Path(__file__).resolve().parent.parent.parent / "MAC_CasePresentation" / "TD_Ave.GCD",
            Path.cwd() / "MAC_CasePresentation" / "TD_Run_Ave.GCD",
            Path(__file__).resolve().parent.parent.parent / "MAC_CasePresentation" / "TD_Run_Ave.GCD",
        ]
        for norm_file in candidates:
            if norm_file.is_file():
                try:
                    self._norm_data = self._gcd_svc.read_gcd(str(norm_file))
                    logger.info("Loaded normative data: %s", norm_file)
                    break
                except Exception as e:
                    logger.warning("Could not load norm GCD %s: %s", norm_file, e)

    def _find_gcd_file(self, session_dir: Path, filename_or_stem: str) -> Optional[Path]:
        """Find a GCD file in session_dir by stem or filename (case-insensitive)."""
        if not session_dir.is_dir():
            return None
        from app.services.session_organizer import find_gcd_file
        found = find_gcd_file(session_dir, filename_or_stem)
        if found:
            return found

        target = filename_or_stem.strip()
        target_with_ext = target if target.upper().endswith(".GCD") else f"{target}.GCD"
        gcd_dir = session_dir / "GCD"
        for d in [gcd_dir, session_dir]:
            if not d.is_dir():
                continue
            direct = d / target_with_ext
            if direct.is_file():
                return direct

        target_lower = target_with_ext.lower()
        target_stem = Path(target).stem.lower()
        for d in [gcd_dir, session_dir]:
            if not d.is_dir():
                continue
            for f in d.iterdir():
                if f.is_file() and f.suffix.lower() == ".gcd":
                    if f.name.lower() == target_lower or f.stem.lower() == target_stem:
                        return f
        return None

    def load_session_data(
        self,
        sessions: List[SessionInfo],
        active_session_index: int = 0,
        display_mode: str = "MR",
    ) -> None:
        """
        Load configured trials and metadata from Patients & Sessions page.
        Supports multiple sessions with an in-page Session Switcher dropdown.
        """
        if not sessions:
            return

        self._sessions = sessions
        self._display_mode = display_mode
        self._current_session_idx = max(0, min(active_session_index, len(sessions) - 1))

        if hasattr(self, "_loading_overlay") and self._loading_overlay:
            self._loading_overlay.show_loading(
                title="Processing GCD Files for Presentation",
                message=f"Preparing Session {self._current_session_idx + 1} data...",
                determinate=True,
            )
            self._loading_overlay.set_progress(5, "Reading session configuration...", "5%")

        # Populate session switcher dropdown
        if hasattr(self, "_session_combo"):
            self._session_combo.blockSignals(True)
            self._session_combo.clear()
            for i, s in enumerate(sessions):
                name = f"Session {i + 1}"
                details = [p for p in (s.study_type, s.analysis_date) if p]
                label = f"{name}: {' • '.join(details)}" if details else name
                self._session_combo.addItem(label, i)

            if len(sessions) > 1:
                self._session_combo.setVisible(True)
                self._session_combo.setCurrentIndex(self._current_session_idx)
            else:
                self._session_combo.setVisible(False)
            self._session_combo.blockSignals(False)

        self._load_active_session(self._current_session_idx)

    def _on_session_combo_changed(self, idx: int) -> None:
        """Handle user selecting a different session from the in-page dropdown."""
        if 0 <= idx < len(self._sessions):
            self._current_session_idx = idx
            if hasattr(self, "_loading_overlay") and self._loading_overlay:
                self._loading_overlay.show_loading(
                    title="Loading Session Graphs",
                    message=f"Switching to Session {idx + 1}...",
                    determinate=True,
                )
                self._loading_overlay.set_progress(5, f"Switching to Session {idx + 1}...", "5%")
            self._load_active_session(idx)

    def _load_active_session(self, idx: int) -> None:
        """Load trials and metadata for a specific session index."""
        if not (0 <= idx < len(self._sessions)):
            return

        sess = self._sessions[idx]
        self._session_path = sess.directory
        session_dir = Path(sess.directory) if sess.directory else Path(".")

        self._trial_data.clear()

        # Collect session metadata for presentation
        self._session_date = sess.analysis_date
        self._study_type = sess.study_type
        self._activity_type = sess.activity_type
        self._orthosis = sess.orthosis
        self._assist = sess.assistive_device
        self._mr_left_name = sess.mr_left
        self._mr_right_name = sess.mr_right

        active_left = [t for t in sess.left_trials if t.gcd_filename and t.gcd_filename != "--"]
        active_right = [t for t in sess.right_trials if t.gcd_filename and t.gcd_filename != "--"]
        total_trials = len(active_left) + len(active_right)
        read_idx = 0

        # Load selected Left trials (L1 - L10)
        for i, trial_info in enumerate(sess.left_trials, start=1):
            fname = trial_info.gcd_filename
            if not fname or fname == "--":
                continue
            read_idx += 1
            if hasattr(self, "_loading_overlay") and self._loading_overlay and total_trials > 0:
                pct = 5 + int((read_idx / (total_trials + 1)) * 30)
                self._loading_overlay.set_progress(
                    pct,
                    f"Reading Left trial {read_idx}/{total_trials}: {fname}",
                    f"Loading GCD trials ({pct}%)",
                )
            gcd_path = self._find_gcd_file(session_dir, fname)
            if gcd_path and gcd_path.is_file():
                try:
                    self._trial_data[f"L{i}"] = self._gcd_svc.read_gcd(str(gcd_path))
                    logger.info("Loaded Left trial L%d: %s", i, gcd_path.name)
                except Exception as e:
                    logger.warning("Error reading GCD %s: %s", gcd_path, e)

        # Load selected Right trials (R1 - R10)
        for i, trial_info in enumerate(sess.right_trials, start=1):
            fname = trial_info.gcd_filename
            if not fname or fname == "--":
                continue
            read_idx += 1
            if hasattr(self, "_loading_overlay") and self._loading_overlay and total_trials > 0:
                pct = 5 + int((read_idx / (total_trials + 1)) * 30)
                self._loading_overlay.set_progress(
                    pct,
                    f"Reading Right trial {read_idx}/{total_trials}: {fname}",
                    f"Loading GCD trials ({pct}%)",
                )
            gcd_path = self._find_gcd_file(session_dir, fname)
            if gcd_path and gcd_path.is_file():
                try:
                    self._trial_data[f"R{i}"] = self._gcd_svc.read_gcd(str(gcd_path))
                    logger.info("Loaded Right trial R%d: %s", i, gcd_path.name)
                except Exception as e:
                    logger.warning("Error reading GCD %s: %s", gcd_path, e)

        # Ensure all available GCD files in the session are discovered and populated
        from app.services.session_organizer import find_all_gcd_files
        all_session_gcds = find_all_gcd_files(session_dir)
        for idx, gcd_f in enumerate(all_session_gcds):
            if idx >= 10:
                break
            l_k = f"L{idx + 1}"
            r_k = f"R{idx + 1}"
            if l_k not in self._trial_data:
                try:
                    self._trial_data[l_k] = self._gcd_svc.read_gcd(str(gcd_f))
                    logger.info("Auto-discovered Left trial %s: %s", l_k, gcd_f.name)
                except Exception as e:
                    logger.warning("Error reading GCD %s: %s", gcd_f, e)
            if r_k not in self._trial_data:
                try:
                    self._trial_data[r_k] = self._gcd_svc.read_gcd(str(gcd_f))
                    logger.info("Auto-discovered Right trial %s: %s", r_k, gcd_f.name)
                except Exception as e:
                    logger.warning("Error reading GCD %s: %s", gcd_f, e)

        # Find which trial key corresponds to MR Left and MR Right
        self._mr_left_key = None
        for i, trial_info in enumerate(sess.left_trials, start=1):
            if trial_info.gcd_filename == sess.mr_left and f"L{i}" in self._trial_data:
                self._mr_left_key = f"L{i}"
                break
        if not self._mr_left_key and any(k.startswith("L") for k in self._trial_data):
            self._mr_left_key = [k for k in self._trial_data if k.startswith("L")][0]

        self._mr_right_key = None
        for i, trial_info in enumerate(sess.right_trials, start=1):
            if trial_info.gcd_filename == sess.mr_right and f"R{i}" in self._trial_data:
                self._mr_right_key = f"R{i}"
                break
        if not self._mr_right_key and any(k.startswith("R") for k in self._trial_data):
            self._mr_right_key = [k for k in self._trial_data if k.startswith("R")][0]

        # Configure filter pills
        self._active_trial_filter.clear()
        for i in range(1, 11):
            l_key = f"L{i}"
            if l_key in self._trial_data:
                self._pill_buttons[l_key].setEnabled(True)
                self._pill_buttons[l_key].setChecked(True)
                self._active_trial_filter.add(l_key)
            else:
                self._pill_buttons[l_key].setEnabled(False)
                self._pill_buttons[l_key].setChecked(False)

            r_key = f"R{i}"
            if r_key in self._trial_data:
                self._pill_buttons[r_key].setEnabled(True)
                self._pill_buttons[r_key].setChecked(True)
                self._active_trial_filter.add(r_key)
            else:
                self._pill_buttons[r_key].setEnabled(False)
                self._pill_buttons[r_key].setChecked(False)

        # Mean / Average pills
        is_ave = getattr(self, "_display_mode", "MR") == "Ave"
        if "Mean" in self._pill_buttons:
            self._pill_buttons["Mean"].setChecked(is_ave)
        if "Mean_L" in self._pill_buttons:
            self._pill_buttons["Mean_L"].setChecked(is_ave)
        if "Mean_R" in self._pill_buttons:
            self._pill_buttons["Mean_R"].setChecked(is_ave)
        if is_ave:
            self._active_trial_filter.add("Mean")
            self._active_trial_filter.add("Mean_L")
            self._active_trial_filter.add("Mean_R")
        else:
            self._active_trial_filter.discard("Mean")
            self._active_trial_filter.discard("Mean_L")
            self._active_trial_filter.discard("Mean_R")

        if hasattr(self, "_smooth_scroll") and self._smooth_scroll:
            self._smooth_scroll.reset(0)
        self._update_pill_visibility()
        self._refresh_plots(show_overlay=True)

    def load_folder(self, folder_path: str) -> None:
        """Load all GCD files in the session directory."""
        if hasattr(self, "_loading_overlay") and self._loading_overlay:
            self._loading_overlay.show_loading(
                title="Processing GCD Files for Presentation",
                message=f"Scanning folder for GCD trials: {Path(folder_path).name}...",
                determinate=True,
            )
            self._loading_overlay.set_progress(10, "Reading GCD directory...", "10%")

        self._session_path = folder_path
        session_dir = Path(folder_path)
        if session_dir.is_file():
            session_dir = session_dir.parent

        self._trial_data.clear()
        from app.services.session_organizer import find_all_gcd_files
        gcd_files = find_all_gcd_files(session_dir)
        logger.info("Scanning for GCD files in %s: found %d", session_dir, len(gcd_files))

        for i, gcd_path in enumerate(gcd_files):
            pct = 10 + int(((i + 1) / max(1, len(gcd_files))) * 25)
            if hasattr(self, "_loading_overlay") and self._loading_overlay:
                self._loading_overlay.set_progress(
                    pct,
                    f"Reading trial {i + 1}/{len(gcd_files)}: {gcd_path.name}",
                    f"Loading files ({pct}%)",
                )
            try:
                gcd = self._gcd_svc.read_gcd(str(gcd_path))
                stem = gcd_path.stem.lower()
                matched = False
                for t_num in range(1, 11):
                    if f"dynamic {t_num}" in stem or f"d{t_num}" in stem:
                        self._trial_data[f"L{t_num}"] = gcd
                        self._trial_data[f"R{t_num}"] = gcd
                        matched = True
                        break
                if not matched:
                    key = f"L{i + 1}" if i < 10 else f"R{i - 9}"
                    self._trial_data[key] = gcd
            except Exception as e:
                logger.warning("Error reading GCD file %s: %s", gcd_path, e)

        if hasattr(self, "_smooth_scroll") and self._smooth_scroll:
            self._smooth_scroll.reset(0)
        self._refresh_plots(show_overlay=True)

    def _on_open_folder_clicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Session Folder Containing GCD Files",
            self._session_path or "",
        )
        if folder:
            self.load_folder(folder)

    def _on_export_pdf_clicked(self) -> None:
        """Generate and export a complete multi-page clinical case presentation vector PDF."""
        # Ensure trials are loaded
        if not self._trial_data and self._session_path:
            self.load_folder(self._session_path)

        if not self._trial_data:
            # Fallback to demo workspace session if present
            demo_session_dir = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "Shriners_Gait_Model_PAF_v1.0"
                / "Shriners_Gait_Model_PAF_v1.0"
                / "Data"
                / "Shriners_test_002"
                / "2025-02-21_0003"
            )
            if demo_session_dir.is_dir():
                self.load_folder(str(demo_session_dir))

        if not self._trial_data:
            QMessageBox.warning(
                self,
                "No Data Available",
                "No dynamic trial (.GCD) files found for export.\nPlease load or process dynamic gait trials first.",
            )
            return

        # Determine which trials are selected in the trial pills (Left "LL" section and Right "R" section)
        selected_l = {k for k in self._active_trial_filter if k.startswith("L") and k in self._trial_data}
        selected_r = {k for k in self._active_trial_filter if k.startswith("R") and k in self._trial_data}

        if self._current_side == "L":
            all_r = {k for k in self._trial_data if k.startswith("R")}
            # If user has only Left side active, export Left trials (unless user specifically selected a subset of Right trials too)
            if selected_r and selected_r != all_r:
                selected_keys = selected_l | selected_r
            else:
                selected_keys = selected_l
        elif self._current_side == "R":
            all_l = {k for k in self._trial_data if k.startswith("L")}
            if selected_l and selected_l != all_l:
                selected_keys = selected_l | selected_r
            else:
                selected_keys = selected_r
        else:  # "LR" (Bilateral)
            selected_keys = selected_l | selected_r

        if not selected_keys:
            QMessageBox.warning(
                self,
                "No Trials Selected",
                "No active trials are selected for export.\nPlease select at least one trial (e.g. L1, R1) in the trial filter pills before exporting.",
            )
            return

        filtered_trials = {k: self._trial_data[k] for k in selected_keys}

        default_name = "Gait_Analysis_Report.pdf"
        if self._session_path:
            p = Path(self._session_path)
            mrn = p.parent.name if p.is_dir() else p.parent.parent.name
            dt = p.name if p.is_dir() else p.parent.name
            trial_summary = "_".join(sorted(selected_keys, key=lambda x: (x[0], int(x[1:]))))
            default_name = f"Gait_Analysis_Report_{mrn}_{dt}_{trial_summary}.pdf"
        default_dir = p if p.is_dir() else p.parent
        from app.services.session_organizer import get_reports_dir
        reports_dir = get_reports_dir(default_dir, create=True)
        default_path = str(reports_dir / default_name)

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Clinical Case Presentation PDF",
            default_path,
            "PDF Files (*.pdf);;All Files (*.*)",
        )
        if not save_path:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            pdf_path = CasePresentationPdfService.generate_report(
                session_path=self._session_path or os.getcwd(),
                output_pdf_path=save_path,
                trials_data=filtered_trials,
                norm_data=self._norm_data,
                selected_trials=selected_keys,
            )
        except Exception as e:
            QApplication.restoreOverrideCursor()
            logger.error("Failed to generate PDF report: %s", e, exc_info=True)
            QMessageBox.critical(
                self,
                "PDF Export Error",
                f"An error occurred while generating the clinical report:\n{e}",
            )
            return
        finally:
            QApplication.restoreOverrideCursor()

        # Prompt user with interactive options
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("PDF Export Successful")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText(
            f"Clinical Case Presentation Report exported successfully!\n\n"
            f"File: {os.path.basename(pdf_path)}\n"
            f"Location: {os.path.dirname(pdf_path)}"
        )
        open_btn = msg_box.addButton("Open PDF", QMessageBox.ActionRole)
        folder_btn = msg_box.addButton("Open Folder", QMessageBox.ActionRole)
        close_btn = msg_box.addButton("Close", QMessageBox.RejectRole)
        msg_box.setDefaultButton(open_btn)

        msg_box.exec()
        if msg_box.clickedButton() == open_btn:
            CasePresentationPdfService.open_pdf(pdf_path)
        elif msg_box.clickedButton() == folder_btn:
            CasePresentationPdfService.open_containing_folder(pdf_path)

    def _get_trial_color(self, key: str) -> str:
        """Return the distinct display color for a specific trial key (L1-L5, R1-R5, Mean)."""
        color_map = DARK_TRIAL_COLORS if self._is_dark else TRIAL_COLORS
        return color_map.get(key, "#2563EB")

    def _style_pill_button(self, btn: QPushButton, key: str, checked: bool) -> None:
        """Style trial pill buttons so each displays its distinctive trial color."""
        color = self._get_trial_color(key)
        if key in ("Mean_L", "Mean_R"):
            fg = "#FFFFFF"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#1E293B' if self._is_dark else '#F8FAFC'};
                    color: {color};
                    border: 1.5px dashed {color};
                    border-radius: 4px;
                    padding: 0px 4px;
                    min-height: 30px;
                    max-height: 30px;
                    min-width: 62px;
                    max-width: 62px;
                    font-weight: 700;
                    outline: none;
                }}
                QPushButton:hover {{
                    background: {color};
                    color: {fg};
                    border: 1.5px solid {color};
                }}
                QPushButton:checked {{
                    background: {color};
                    color: {fg};
                    border: 1.5px solid {color};
                    font-weight: bold;
                }}
            """)
        elif key == "Mean":
            mean_bg = "#FAFAFA" if self._is_dark else "#111827"
            mean_fg = "#111827" if self._is_dark else "#FAFAFA"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#27272A' if self._is_dark else '#F4F4F5'};
                    color: {'#A1A1AA' if self._is_dark else '#71717A'};
                    border: 1px dashed {'#3F3F46' if self._is_dark else '#D4D4D8'};
                    border-radius: 4px;
                    padding: 0px;
                    min-height: 30px;
                    max-height: 30px;
                    min-width: 50px;
                    max-width: 50px;
                    font-weight: 600;
                    outline: none;
                }}
                QPushButton:hover {{
                    border-color: {mean_bg};
                    color: {mean_bg};
                }}
                QPushButton:checked {{
                    background: {mean_bg};
                    color: {mean_fg};
                    border: 1px solid {mean_bg};
                    font-weight: bold;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#18181B' if self._is_dark else '#F4F4F5'};
                    color: {'#A1A1AA' if self._is_dark else '#71717A'};
                    border: 1px solid {'#27272A' if self._is_dark else '#E4E4E7'};
                    border-radius: 4px;
                    padding: 0px;
                    min-height: 30px;
                    max-height: 30px;
                    min-width: 30px;
                    max-width: 30px;
                    font-weight: bold;
                    outline: none;
                }}
                QPushButton:hover {{
                    border-color: {color};
                    color: {color};
                }}
                QPushButton:checked {{
                    background: {color};
                    color: #FFFFFF;
                    border: 1px solid {color};
                    font-weight: bold;
                }}
                QPushButton:disabled {{
                    background: {'#141414' if self._is_dark else '#FAFAFA'};
                    color: {'#3F3F46' if self._is_dark else '#D4D4D8'};
                    border: 1px solid {'#1F1F23' if self._is_dark else '#E4E4E7'};
                }}
            """)

    def _mean_curve(self, plot_idx, side, traces):
        if not hasattr(self, "_mean_cache"):
            self._mean_cache = {}
        key = (plot_idx, side)
        signature = tuple(np.asarray(trace).tobytes() for trace in traces)
        cached = self._mean_cache.get(key)
        if cached is None or cached[0] != signature:
            cached = self._mean_cache[key] = (signature, np.mean(traces, axis=0))
        return cached[1]

    def _schedule_plot_refresh(self):
        if not hasattr(self, "_plot_refresh_timer"):
            self._plot_refresh_timer = QTimer(self)
            self._plot_refresh_timer.setSingleShot(True)
            self._plot_refresh_timer.timeout.connect(lambda: self._refresh_plots(show_overlay=False))
        self._plot_refresh_timer.start(0)

    def _on_filter_toggled(self, trial_key: str, checked: bool) -> None:
        if trial_key in self._pill_buttons:
            self._style_pill_button(self._pill_buttons[trial_key], trial_key, checked)
        if checked:
            self._active_trial_filter.add(trial_key)
        else:
            self._active_trial_filter.discard(trial_key)

        # Synchronize master Mean with L Mean and R Mean
        if trial_key == "Mean":
            for sub_key in ("Mean_L", "Mean_R"):
                if sub_key in self._pill_buttons:
                    self._pill_buttons[sub_key].blockSignals(True)
                    self._pill_buttons[sub_key].setChecked(checked)
                    self._style_pill_button(self._pill_buttons[sub_key], sub_key, checked)
                    self._pill_buttons[sub_key].blockSignals(False)
                    if checked:
                        self._active_trial_filter.add(sub_key)
                    else:
                        self._active_trial_filter.discard(sub_key)
        elif trial_key in ("Mean_L", "Mean_R"):
            l_on = self._pill_buttons["Mean_L"].isChecked() if "Mean_L" in self._pill_buttons else False
            r_on = self._pill_buttons["Mean_R"].isChecked() if "Mean_R" in self._pill_buttons else False
            has_any = l_on or r_on
            if "Mean" in self._pill_buttons:
                self._pill_buttons["Mean"].blockSignals(True)
                self._pill_buttons["Mean"].setChecked(has_any)
                self._style_pill_button(self._pill_buttons["Mean"], "Mean", has_any)
                self._pill_buttons["Mean"].blockSignals(False)
                if has_any:
                    self._active_trial_filter.add("Mean")
                else:
                    self._active_trial_filter.discard("Mean")

        self._schedule_plot_refresh()

    def _on_norm_toggled(self, checked: bool) -> None:
        self._show_norm_band = checked
        self._schedule_plot_refresh()

    def _on_category_changed(self, cat: str) -> None:
        self._current_category = cat
        if hasattr(self, "_smooth_scroll") and self._smooth_scroll:
            self._smooth_scroll.reset(0)
        self._refresh_plots(show_overlay=True)

    def _select_all_trials(self) -> None:
        """Select all visible trials for the current side."""
        for key, btn in self._pill_buttons.items():
            if btn.isVisible() and btn.isEnabled() and key not in ("Mean", "Mean_L", "Mean_R"):
                btn.setChecked(True)
        self._refresh_plots(show_overlay=False)

    def _clear_all_trials(self) -> None:
        """Deselect all visible trials."""
        for key, btn in self._pill_buttons.items():
            if btn.isVisible() and key not in ("Mean", "Mean_L", "Mean_R"):
                btn.setChecked(False)
        self._refresh_plots(show_overlay=False)

    def _select_mr_only(self) -> None:
        """Select only the Most Representative trial(s)."""
        mr_keys = set()
        if self._mr_left_key:
            mr_keys.add(self._mr_left_key)
        if self._mr_right_key:
            mr_keys.add(self._mr_right_key)
        for key, btn in self._pill_buttons.items():
            if key in ("Mean", "Mean_L", "Mean_R"):
                continue
            if key in mr_keys:
                btn.setChecked(True)
            else:
                btn.setChecked(False)
        self._refresh_plots(show_overlay=False)

    def _update_pill_visibility(self) -> None:
        """Show only relevant limb pills for the selected side and re-style them."""
        side = self._current_side
        show_left = side in ("L", "LR")
        show_right = side in ("R", "LR")

        if side == "L":
            if hasattr(self, "_row_left"):
                self._row_left.setVisible(True)
            if hasattr(self, "_left_container"):
                self._left_container.setVisible(True)
            if hasattr(self, "_row_right"):
                self._row_right.setVisible(False)
            if hasattr(self, "_actions_container") and hasattr(self, "_row_left_layout"):
                self._row_left_layout.insertWidget(1, self._actions_container)
                self._actions_container.setVisible(True)
        elif side == "R":
            if hasattr(self, "_row_left"):
                self._row_left.setVisible(False)
            if hasattr(self, "_row_right"):
                self._row_right.setVisible(True)
            if hasattr(self, "_right_container"):
                self._right_container.setVisible(True)
            if hasattr(self, "_actions_container") and hasattr(self, "_row_right_layout"):
                self._row_right_layout.insertWidget(1, self._actions_container)
                self._actions_container.setVisible(True)
        else:  # "LR" (Bilateral)
            if hasattr(self, "_row_left"):
                self._row_left.setVisible(True)
            if hasattr(self, "_left_container"):
                self._left_container.setVisible(True)
            if hasattr(self, "_actions_container") and hasattr(self, "_row_left_layout"):
                self._row_left_layout.insertWidget(1, self._actions_container)
                self._actions_container.setVisible(True)
            if hasattr(self, "_row_right"):
                self._row_right.setVisible(True)
            if hasattr(self, "_right_container"):
                self._right_container.setVisible(True)

        if hasattr(self, "_sep_l_mean"):
            self._sep_l_mean.setVisible(show_left)
        if hasattr(self, "_sep_r_mean"):
            self._sep_r_mean.setVisible(show_right)

        for key, btn in self._pill_buttons.items():
            if key == "Mean":
                btn.setVisible(True)
            elif key == "Mean_L":
                btn.setVisible(show_left)
            elif key == "Mean_R":
                btn.setVisible(show_right)
            elif key.startswith("L"):
                btn.setVisible(show_left)
            elif key.startswith("R"):
                btn.setVisible(show_right)
            self._style_pill_button(btn, key, btn.isChecked())

    def _on_side_changed(self, side: str) -> None:
        self._current_side = side
        self._update_pill_visibility()
        self._refresh_plots(show_overlay=True)

    def _get_page_settings(self) -> PageSettings:
        mapping = {
            "kinematics": self._settings_svc.get_kinematics_settings,
            "sagittal_kinetics": self._settings_svc.get_sagittal_kinetics_settings,
            "coronal_kinetics": self._settings_svc.get_coronal_kinetics_settings,
            "emg": self._settings_svc.get_emg_settings,
            "foot_kinematics": self._settings_svc.get_foot_kinematics_settings,
            "muscle_length": self._settings_svc.get_muscle_length_settings,
            "muscle_velocity": self._settings_svc.get_muscle_velocity_settings,
        }
        getter = mapping.get(self._current_category)
        return getter() if getter else PageSettings()

    def _refresh_plots(self, show_overlay: bool = True) -> None:
        if hasattr(self, "_plot_refresh_timer"):
            self._plot_refresh_timer.stop()
        cat = self._current_category
        side = self._current_side
        palette = DARK_PALETTE if self._is_dark else LIGHT_PALETTE

        cat_title = cat.replace("_", " ").title()
        side_title = {"L": "Left Limb", "R": "Right Limb", "LR": "Bilateral (L/R)"}.get(side, side)

        if show_overlay and hasattr(self, "_loading_overlay") and self._loading_overlay:
            if not self._loading_overlay.isVisible():
                self._loading_overlay.show_loading(
                    title="Rendering Clinical Graphs",
                    message=f"Computing gait curves for {cat_title} ({side_title})...",
                    determinate=True,
                )
                self._loading_overlay.set_progress(35, f"Analyzing trials for {cat_title}...", f"Starting {cat_title}")

        self._title_label.setText("CASE PRESENTATION")
        if hasattr(self, "_category_badge"):
            self._category_badge.setText(cat_title)
        if hasattr(self, "_side_badge"):
            self._side_badge.setText(side_title)
        if hasattr(self, "_mode_badge"):
            self._mode_badge.setText("MR Mode" if getattr(self, "_display_mode", "MR") == "MR" else "Average Mode")
        if hasattr(self, "_meta_badge"):
            if hasattr(self, "_session_combo") and not self._session_combo.isHidden():
                meta_parts = [p for p in [self._activity_type, self._orthosis, self._assist] if p]
            else:
                meta_parts = [p for p in [self._study_type, self._session_date, self._activity_type, self._orthosis, self._assist] if p]
            text = " • ".join(meta_parts) if meta_parts else ""
            self._meta_badge.setText(text)
            self._meta_badge.setVisible(bool(text))

        settings = self._get_page_settings()
        left_vars = settings.left_names or []
        right_vars = settings.right_names or []
        num_plots = min(max(len(left_vars), len(right_vars)), 15)

        # Determine which trial keys to plot based on selected side (Left, Right, or Bilateral)
        if side == "L":
            trial_keys = [f"L{i}" for i in range(1, 11)]
        elif side == "R":
            trial_keys = [f"R{i}" for i in range(1, 11)]
        else:  # "LR"
            trial_keys = [f"L{i}" for i in range(1, 11)] + [f"R{i}" for i in range(1, 11)]

        # Update Clinical Bilateral Mean Legend Bar visibility and dynamic trial counts
        master_mean = ("Mean" in self._active_trial_filter) or (getattr(self, "_display_mode", "MR") == "Ave")
        has_l_explicit = "Mean_L" in self._active_trial_filter
        has_r_explicit = "Mean_R" in self._active_trial_filter
        if has_l_explicit or has_r_explicit:
            has_l_mean = has_l_explicit
            has_r_mean = has_r_explicit
        else:
            has_l_mean = master_mean
            has_r_mean = master_mean

        n_left_active = len([k for k in trial_keys if k.startswith("L") and k in self._active_trial_filter and k in self._trial_data])
        n_right_active = len([k for k in trial_keys if k.startswith("R") and k in self._active_trial_filter and k in self._trial_data])
        show_bilateral_legend = (side == "LR") and (has_l_mean or has_r_mean) and (n_left_active > 0 or n_right_active > 0)

        if hasattr(self, "_mean_legend_bar"):
            if show_bilateral_legend:
                self._mean_leg_l_label.setText(f"╍╍ Left Mean ({n_left_active} trials)")
                self._mean_leg_l_label.setVisible(has_l_mean and n_left_active > 0)
                self._mean_leg_r_label.setText(f"╍╍ Right Mean ({n_right_active} trials)")
                self._mean_leg_r_label.setVisible(has_r_mean and n_right_active > 0)
                self._mean_legend_bar.setVisible(True)
            else:
                self._mean_legend_bar.setVisible(False)

        x = GCDService.get_gait_cycle_x()
        # Clear only unused cells when the category actually removes a plot.
        for idx, canvas in enumerate(self._plot_grid.get_all_canvases()):
            has_var = False
            if idx < num_plots:
                lv = left_vars[idx] if idx < len(left_vars) else ""
                rv = right_vars[idx] if idx < len(right_vars) else ""
                has_var = bool(lv or rv)
            if not has_var and getattr(canvas, "_last_plot_kwargs", None):
                canvas.clear_plot()
                canvas.draw_idle()

        for plot_idx in range(num_plots):
            l_var = left_vars[plot_idx] if plot_idx < len(left_vars) else ""
            r_var = right_vars[plot_idx] if plot_idx < len(right_vars) else ""
            if not l_var and not r_var:
                continue

            title = settings.titles[plot_idx] if plot_idx < len(settings.titles) else f"Plot {plot_idx + 1}"
            if show_overlay and hasattr(self, "_loading_overlay") and self._loading_overlay:
                pct = 35 + int(((plot_idx + 1) / num_plots) * 60)
                self._loading_overlay.set_progress(
                    pct,
                    f"Rendering graph {plot_idx + 1}/{num_plots}: {title}",
                    f"{cat_title} ({plot_idx + 1}/{num_plots})",
                )

            y_data = []
            curve_ids = []
            colors = []
            toe_offs = []
            opp_toe_offs = []
            opp_foot_contacts = []
            line_widths = []
            line_styles = []

            left_y_traces = []
            left_to_vals = []
            right_y_traces = []
            right_to_vals = []

            for key in trial_keys:
                if key not in self._active_trial_filter:
                    continue
                gcd = self._trial_data.get(key)
                if gcd is None:
                    continue

                limb = "Left" if key.startswith("L") else "Right"
                var = l_var if limb == "Left" else r_var
                if not var:
                    continue

                arr = GCDService.get_variable_array(gcd, var)
                if arr is not None and len(arr) == 101:
                    y_data.append(arr)
                    curve_ids.append(key)
                    # Assign distinctive trial-specific color
                    colors.append(self._get_trial_color(key))
                    to_val = GCDService.get_toe_off(gcd, limb)
                    toe_offs.append(to_val)
                    opp_toe_offs.append(GCDService.get_opposite_foot_off(gcd, limb))
                    opp_foot_contacts.append(GCDService.get_opposite_foot_contact(gcd, limb))

                    if limb == "Left":
                        left_y_traces.append(arr)
                        if to_val is not None and to_val > 0:
                            left_to_vals.append(to_val)
                    else:
                        right_y_traces.append(arr)
                        if to_val is not None and to_val > 0:
                            right_to_vals.append(to_val)

                    # Emphasize MR trial in MR mode with bolder stroke
                    is_mr = (getattr(self, "_display_mode", "MR") == "MR") and (
                        (key == self._mr_left_key if limb == "Left" else key == self._mr_right_key)
                    )
                    if is_mr:
                        line_widths.append(2.6)
                        line_styles.append("-")
                    else:
                        line_widths.append(1.5)
                        line_styles.append("-")

            # Mean / Average curve: compute Left and Right limb means separately
            master_mean = ("Mean" in self._active_trial_filter) or (getattr(self, "_display_mode", "MR") == "Ave")
            if side == "LR":
                has_l_explicit = "Mean_L" in self._active_trial_filter
                has_r_explicit = "Mean_R" in self._active_trial_filter
                if has_l_explicit or has_r_explicit:
                    show_l_mean = has_l_explicit and len(left_y_traces) >= 1
                    show_r_mean = has_r_explicit and len(right_y_traces) >= 1
                else:
                    show_l_mean = master_mean and len(left_y_traces) >= 1
                    show_r_mean = master_mean and len(right_y_traces) >= 1
            else:
                show_l_mean = (master_mean or "Mean_L" in self._active_trial_filter) and len(left_y_traces) >= 1
                show_r_mean = (master_mean or "Mean_R" in self._active_trial_filter) and len(right_y_traces) >= 1

            leg_entries = []

            if show_l_mean and show_r_mean:
                # Both Left and Right Means: separate clinical curves and toe-offs
                mean_l = self._mean_curve(plot_idx, "L", left_y_traces)
                y_data.append(mean_l)
                curve_ids.append("Mean_L")
                col_l = self._get_trial_color("Mean_L")
                colors.append(col_l)
                line_widths.append(2.8)
                line_styles.append("--")
                val_l_to = [t for t in left_to_vals if t is not None and t > 0]
                toe_offs.append(float(np.mean(val_l_to)) if val_l_to else None)
                opp_toe_offs.append(None)
                opp_foot_contacts.append(None)
                leg_entries.append(("L Mean", col_l, "--"))

                mean_r = self._mean_curve(plot_idx, "R", right_y_traces)
                y_data.append(mean_r)
                curve_ids.append("Mean_R")
                col_r = self._get_trial_color("Mean_R")
                colors.append(col_r)
                line_widths.append(2.8)
                line_styles.append("--")
                val_r_to = [t for t in right_to_vals if t is not None and t > 0]
                toe_offs.append(float(np.mean(val_r_to)) if val_r_to else None)
                opp_toe_offs.append(None)
                opp_foot_contacts.append(None)
                leg_entries.append(("R Mean", col_r, "--"))

            elif show_l_mean:
                mean_l = self._mean_curve(plot_idx, "L", left_y_traces)
                y_data.append(mean_l)
                curve_ids.append("Mean_L")
                col_l = self._get_trial_color("Mean_L") if side == "LR" else self._get_trial_color("Mean")
                colors.append(col_l)
                line_widths.append(2.8)
                line_styles.append("--")
                val_l_to = [t for t in left_to_vals if t is not None and t > 0]
                toe_offs.append(float(np.mean(val_l_to)) if val_l_to else None)
                opp_toe_offs.append(None)
                opp_foot_contacts.append(None)
                if side == "LR":
                    leg_entries.append(("L Mean", col_l, "--"))

            elif show_r_mean:
                mean_r = self._mean_curve(plot_idx, "R", right_y_traces)
                y_data.append(mean_r)
                curve_ids.append("Mean_R")
                col_r = self._get_trial_color("Mean_R") if side == "LR" else self._get_trial_color("Mean")
                colors.append(col_r)
                line_widths.append(2.8)
                line_styles.append("--")
                val_r_to = [t for t in right_to_vals if t is not None and t > 0]
                toe_offs.append(float(np.mean(val_r_to)) if val_r_to else None)
                opp_toe_offs.append(None)
                opp_foot_contacts.append(None)
                if side == "LR":
                    leg_entries.append(("R Mean", col_r, "--"))

            # Normative ideal range band & dotted mean curve
            norm_y_low = norm_y_high = norm_y_mean = None
            norm_x = x if self._show_norm_band else None
            norm_to = None
            if self._show_norm_band and self._norm_data:
                l_name = settings.left_names[plot_idx] if plot_idx < len(settings.left_names) else ""
                r_name = settings.right_names[plot_idx] if plot_idx < len(settings.right_names) else ""
                norm_key = (
                    
                    GCDService.find_norm_variable(self._norm_data, l_name)
                    or GCDService.find_norm_variable(self._norm_data, r_name)
                )
                if norm_key:
                    norm_arr = GCDService.get_variable_array(self._norm_data, norm_key)
                    norm_sd = GCDService.get_variable_sd_array(self._norm_data, norm_key)
                    
                    if (
                        norm_arr is not None
                        and norm_sd is not None
                        and len(norm_arr) == 101
                        and len(norm_sd) == 101
                        and np.isfinite(norm_arr).all()
                        and np.isfinite(norm_sd).all()
                        and np.all(norm_sd >= 0)
                    ):
                        norm_y_mean = norm_arr
                        norm_y_high = norm_arr + norm_sd
                        norm_y_low = norm_arr - norm_sd

                        to_val = GCDService.get_toe_off(self._norm_data, "Left")
                        if to_val and 0 < to_val < 100:
                            norm_to = to_val


            title = settings.titles[plot_idx] if plot_idx < len(settings.titles) else ""
            y_min = settings.lower_limits[plot_idx] if plot_idx < len(settings.lower_limits) else -30
            y_max = settings.upper_limits[plot_idx] if plot_idx < len(settings.upper_limits) else 30
            y_ticks = settings.y_tick_labels[plot_idx] if plot_idx < len(settings.y_tick_labels) else None

            row = plot_idx // 3
            col = plot_idx % 3
            self._plot_grid.plot_at(
                row, col,
                graph_id=(os.path.normcase(os.path.abspath(self._session_path)), cat, side, l_var or r_var or str(plot_idx)),
                x_data=[x] * len(y_data),
                y_data=y_data,
                curve_ids=curve_ids,
                colors=colors,
                toe_offs=toe_offs,
                opposite_toe_offs=opp_toe_offs,
                opposite_foot_contacts=opp_foot_contacts,
                line_widths=line_widths,
                line_styles=line_styles,
                legend_entries=leg_entries if leg_entries else None,
                norm_x=norm_x,
                norm_y_low=norm_y_low,
                norm_y_high=norm_y_high,
                norm_y_mean=norm_y_mean,
                norm_toe_off=norm_to,
                y_min=y_min,
                y_max=y_max,
                title=title,
                y_ticks=y_ticks,
                show_x_labels=(row == 4),
            )

        if show_overlay and hasattr(self, "_loading_overlay") and self._loading_overlay and self._loading_overlay.isVisible():
            self._loading_overlay.set_progress(100, "Clinical graphs ready!", "Complete")
            QTimer.singleShot(150, self._loading_overlay.hide_loading)
