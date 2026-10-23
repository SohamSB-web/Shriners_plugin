# -*- coding: utf-8 -*-
"""
Comparison Page — Initial vs. Follow-up session comparison.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.models.data_models import GCDData, SessionInfo
from app.services.gcd_service import GCDService
from app.services.settings_service import SettingsService
from app.ui.charts.clinical_plots import MultiPlotGrid
from app.ui.theme.design_tokens import FONT_SIZE_H2, LIGHT_PALETTE, SPACE_LG, SPACE_MD, SPACE_SM, SPACE_XL
from app.ui.widgets.components import EmptyState, SectionCard

logger = logging.getLogger(__name__)


class ComparisonPage(QScrollArea):
    """Session comparison interface — overlay initial vs. follow-up."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)

        self._settings_svc = SettingsService()
        self._gcd_svc = GCDService()

        container = QWidget()
        self.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        layout.setSpacing(SPACE_LG)

        # Header
        header = QLabel("Session Comparison")
        header.setObjectName("headerTitle")
        header.setStyleSheet(f"font-size: {FONT_SIZE_H2}px; font-weight: 700;")
        layout.addWidget(header)

        # ── Session selectors ──────────────────────────────────────
        selectors = QHBoxLayout()
        selectors.setSpacing(SPACE_LG)

        # Initial session
        init_card = SectionCard("Initial Study")
        self._init_combo = QComboBox()
        self._init_combo.setMinimumWidth(200)
        init_card.add_widget(self._init_combo)
        self._init_info = QLabel("No session selected")
        self._init_info.setObjectName("captionLabel")
        init_card.add_widget(self._init_info)
        selectors.addWidget(init_card)

        vs_label = QLabel("VS")
        vs_label.setAlignment(Qt.AlignCenter)
        vs_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #808080;")
        vs_label.setFixedWidth(60)
        selectors.addWidget(vs_label)

        # Follow-up session
        fu_card = SectionCard("Follow-up Study")
        self._fu_combo = QComboBox()
        self._fu_combo.setMinimumWidth(200)
        fu_card.add_widget(self._fu_combo)
        self._fu_info = QLabel("No session selected")
        self._fu_info.setObjectName("captionLabel")
        fu_card.add_widget(self._fu_info)
        selectors.addWidget(fu_card)

        layout.addLayout(selectors)

        # ── Variable / side selector ───────────────────────────────
        controls = QHBoxLayout()
        controls.setSpacing(SPACE_SM)

        controls.addWidget(QLabel("Category:"))
        self._cat_combo = QComboBox()
        self._cat_combo.addItems([
            "Kinematics", "Sagittal Kinetics", "Coronal Kinetics",
            "EMG", "Foot Kinematics", "Muscle Length", "Muscle Velocity",
        ])
        self._cat_combo.currentTextChanged.connect(self._on_refresh)
        controls.addWidget(self._cat_combo)

        controls.addWidget(QLabel("Side:"))
        self._side_combo = QComboBox()
        self._side_combo.addItems(["Left", "Right"])
        self._side_combo.currentTextChanged.connect(self._on_refresh)
        controls.addWidget(self._side_combo)

        self._compare_btn = QPushButton("Compare")
        self._compare_btn.setObjectName("primaryButton")
        self._compare_btn.clicked.connect(self._on_refresh)
        controls.addWidget(self._compare_btn)

        controls.addStretch()
        layout.addLayout(controls)

        # ── Legend ─────────────────────────────────────────────────
        legend = QHBoxLayout()
        palette = LIGHT_PALETTE
        legend.addWidget(self._legend_dot(palette.comparison_initial, "Initial Study"))
        legend.addWidget(self._legend_dot(palette.comparison_followup, "Follow-up Study"))
        legend.addStretch()
        layout.addLayout(legend)

        # ── Plot grid ──────────────────────────────────────────────
        self._plot_grid = MultiPlotGrid(rows=5, cols=3)
        layout.addWidget(self._plot_grid, 1)

        layout.addStretch()

        # State
        self._sessions: List[SessionInfo] = []

    def _legend_dot(self, color: str, text: str) -> QWidget:
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(4)
        dot = QLabel()
        dot.setFixedSize(12, 3)
        dot.setStyleSheet(f"background-color: {color}; border: none;")
        l.addWidget(dot)
        l.addWidget(QLabel(text))
        return w

    def set_sessions(self, sessions: List[SessionInfo]) -> None:
        """Update available sessions for comparison."""
        self._sessions = sessions
        self._init_combo.clear()
        self._fu_combo.clear()
        for i, s in enumerate(sessions):
            label = f"Session {i+1}: {s.analysis_date or s.directory}"
            self._init_combo.addItem(label)
            self._fu_combo.addItem(label)
        if len(sessions) >= 2:
            self._fu_combo.setCurrentIndex(1)

    def _on_refresh(self) -> None:
        """Placeholder for comparison plot refresh."""
        self._plot_grid.clear_all()
        # TODO: Load GCD data from both sessions and overlay plots
        # using comparison colors
        logger.info("Comparison refresh requested")
