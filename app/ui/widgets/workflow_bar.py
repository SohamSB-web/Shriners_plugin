# -*- coding: utf-8 -*-
"""
Minimal Clinical Workflow Stepper Bar — Monochrome B&W.

Displays the linear scientific analysis workflow:
  Static Calibration → Dynamic Analysis → Case Presentation
"""

from __future__ import annotations

from typing import List, Tuple
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from app.ui.theme.design_tokens import (
    FONT_FAMILY,
    FONT_SIZE_BODY,
    FONT_SIZE_CAPTION,
    FONT_SIZE_SMALL,
    FONT_WEIGHT_MEDIUM,
    FONT_WEIGHT_SEMIBOLD,
    RADIUS_ROUND,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    COLOR_PRIMARY,
    COLOR_ACCENT,
    COLOR_MOTION,
    COLOR_NORMAL,
    COLOR_WARNING,
    COLOR_CRITICAL,
    COLOR_BACKGROUND,
    COLOR_SURFACE,
    COLOR_TEXT,
    COLOR_MUTED,
    COLOR_BORDER,
)


class WorkflowBar(QFrame):
    """
    Minimal horizontal workflow stepper.
    Static Analysis → Dynamic Analysis → Case Presentation.
    """

    stage_selected = Signal(str)

    STAGES: List[Tuple[str, str, str]] = [
        ("static_analysis", "1", "Static Calibration"),
        ("dynamic_analysis", "2", "Dynamic Analysis"),
        ("patients", "3", "Patients && Sessions"),
        ("case_presentation", "4", "Case Presentation"),
    ]

    def __init__(self, current_stage: str = "static_analysis", parent: QWidget | None = None):
        super().__init__(parent)
        self._current_stage = current_stage
        self._completed_stages = set()

        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(
            "WorkflowBar { background: transparent; border: none; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, SPACE_MD, 6)
        layout.setSpacing(SPACE_SM)
        layout.setAlignment(Qt.AlignVCenter)

        self._buttons = {}
        self._separators = []

        for i, (key, num, label) in enumerate(self.STAGES):
            btn = QPushButton()
            btn.setObjectName("workflowTabButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, FONT_WEIGHT_MEDIUM))
            btn.clicked.connect(lambda checked, k=key: self._on_btn_clicked(k))
            layout.addWidget(btn)
            self._buttons[key] = btn

            if i < len(self.STAGES) - 1:
                sep = QLabel("→")
                sep.setStyleSheet(
                    "color: #909090; font-size: 13px; font-weight: 500; "
                    "background: transparent; padding: 0 4px;"
                )
                layout.addWidget(sep)
                self._separators.append(sep)

        self._is_dark = False
        layout.addStretch()
        self._update_styles()

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        """Update workflow bar styling for light or dark mode."""
        self._is_dark = dark
        sep_color = "#475569" if dark else COLOR_MUTED
        for sep in self._separators:
            sep.setStyleSheet(
                f"color: {sep_color}; font-size: 13px; font-weight: 500; "
                f"background: transparent; padding: 0 4px;"
            )
        self._update_styles()

    def set_active_stage(self, stage_key: str) -> None:
        self._current_stage = stage_key
        self._update_styles()

    def mark_completed(self, stage_key: str, completed: bool = True) -> None:
        if completed:
            self._completed_stages.add(stage_key)
        else:
            self._completed_stages.discard(stage_key)
        self._update_styles()

    def _on_btn_clicked(self, stage_key: str) -> None:
        self.set_active_stage(stage_key)
        self.stage_selected.emit(stage_key)

    def _update_styles(self) -> None:
        for key, num, label in self.STAGES:
            btn = self._buttons[key]
            is_active = (key == self._current_stage)
            is_done = (key in self._completed_stages)

            if self._is_dark:
                if is_done and not is_active:
                    prefix = "✓"
                    bg = "#134E4A"
                    fg = "#2DD4BF"
                    border = "#14B8A6"
                    hover_bg = "#115E59"
                    hover_border = "#2DD4BF"
                    hover_fg = "#FFFFFF"
                    font_weight = "600"
                elif is_active:
                    prefix = num
                    bg = "#0F766E"
                    fg = "#FFFFFF"
                    border = "#14B8A6"
                    hover_bg = "#115E59"
                    hover_border = "#2DD4BF"
                    hover_fg = "#FFFFFF"
                    font_weight = "700"
                else:
                    prefix = num
                    bg = "#1E293B"
                    fg = "#94A3B8"
                    border = "#334155"
                    hover_bg = "#334155"
                    hover_border = "#14B8A6"
                    hover_fg = "#FFFFFF"
                    font_weight = "500"
            else:
                if is_done and not is_active:
                    prefix = "✓"
                    bg = "#F0FDFA"
                    fg = COLOR_PRIMARY
                    border = COLOR_ACCENT
                    hover_bg = "#CCFBF1"
                    hover_border = COLOR_PRIMARY
                    hover_fg = COLOR_PRIMARY
                    font_weight = "600"
                elif is_active:
                    prefix = num
                    bg = COLOR_PRIMARY
                    fg = COLOR_SURFACE
                    border = COLOR_PRIMARY
                    hover_bg = "#115E59"
                    hover_border = COLOR_PRIMARY
                    hover_fg = COLOR_SURFACE
                    font_weight = "700"
                else:
                    prefix = num
                    bg = COLOR_SURFACE
                    fg = COLOR_TEXT
                    border = COLOR_BORDER
                    hover_bg = COLOR_BACKGROUND
                    hover_border = COLOR_ACCENT
                    hover_fg = COLOR_PRIMARY
                    font_weight = "500"

            btn.setText(f"  {prefix}  {label}  ")
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  background-color: {bg};"
                f"  color: {fg};"
                f"  border: 1.5px solid {border};"
                f"  border-radius: 5px;"
                f"  min-height: 28px;"
                f"  max-height: 28px;"
                f"  height: 28px;"
                f"  padding: 0 14px;"
                f"  font-weight: {font_weight};"
                f"  font-size: 11px;"
                f"  letter-spacing: 0.3px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background-color: {hover_bg};"
                f"  border-color: {hover_border};"
                f"  color: {hover_fg};"
                f"}}"
            )
