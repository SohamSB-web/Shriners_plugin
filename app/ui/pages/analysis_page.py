# -*- coding: utf-8 -*-
"""
Analysis Workspace Page — tabbed interface for Kinematics, Sagittal Kinetics,
Coronal Kinetics, EMG, Foot Kinematics, Muscle Length, Muscle Velocity.

Replaces the GraphsDisplay_Page from MAC_CasePresentation.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

import numpy as np

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.models.data_models import GCDData, PageSettings, SessionInfo
from app.services.gcd_service import GCDService
from app.services.settings_service import SettingsService
from app.ui.charts.clinical_plots import ClinicalPlotCanvas, MultiPlotGrid
from app.ui.theme.design_tokens import (
    FONT_SIZE_H2,
    FONT_SIZE_H3,
    LIGHT_PALETTE,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
)
from app.ui.widgets.components import EmptyState, SectionCard

logger = logging.getLogger(__name__)


class AnalysisSidebar(QFrame):
    """Left sidebar within the analysis page for category + side selection."""

    category_changed = Signal(str)
    side_changed = Signal(str)  # "L", "R", or "LR"

    CATEGORIES = [
        ("Kinematics", "kinematics"),
        ("Sagittal Kinetics", "sagittal_kinetics"),
        ("Coronal Kinetics", "coronal_kinetics"),
        ("EMG", "emg"),
        ("Foot Kinematics", "foot_kinematics"),
        ("Muscle Length", "muscle_length"),
        ("Muscle Velocity", "muscle_velocity"),
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_SM, SPACE_MD, SPACE_SM, SPACE_MD)
        layout.setSpacing(SPACE_XS)

        title = QLabel("Analysis")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # Category buttons
        self._cat_buttons: Dict[str, QPushButton] = {}
        for label, key in self.CATEGORIES:
            btn = QPushButton(label)
            btn.setObjectName("tabButton")
            btn.setCheckable(False)
            btn.clicked.connect(lambda checked, k=key: self._on_category(k))
            layout.addWidget(btn)
            self._cat_buttons[key] = btn

        layout.addSpacing(SPACE_LG)

        # Side selector
        side_label = QLabel("Display")
        side_label.setObjectName("sectionTitle")
        layout.addWidget(side_label)

        side_row = QHBoxLayout()
        side_row.setSpacing(SPACE_XS)

        self._side_buttons: Dict[str, QPushButton] = {}
        for label, key in [("Left", "L"), ("Right", "R"), ("L/R", "LR")]:
            btn = QPushButton(label)
            btn.setObjectName("tabButton")
            btn.setFixedWidth(55)
            btn.clicked.connect(lambda checked, k=key: self._on_side(k))
            side_row.addWidget(btn)
            self._side_buttons[key] = btn

        layout.addLayout(side_row)
        layout.addStretch()

        self._active_category = ""
        self._active_side = ""

    def _on_category(self, key: str) -> None:
        self._active_category = key
        for k, btn in self._cat_buttons.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.category_changed.emit(key)

    def _on_side(self, key: str) -> None:
        self._active_side = key
        for k, btn in self._side_buttons.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.side_changed.emit(key)

    def select_default(self):
        """Programmatically select kinematics + left."""
        self._on_category("kinematics")
        self._on_side("L")


class AnalysisPage(QWidget):
    """
    Main analysis workspace — left sidebar for category/side selection,
    right area shows the 5×3 clinical plot grid.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._settings_svc = SettingsService()
        self._gcd_svc = GCDService()

        # State
        self._current_category = "kinematics"
        self._current_side = "L"
        self._trial_data: Dict[str, List[GCDData]] = {}  # "L1" -> GCDData, etc.
        self._norm_data: Optional[GCDData] = None
        self._sessions: List[SessionInfo] = []

        # Layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Analysis sidebar
        self._sidebar = AnalysisSidebar()
        self._sidebar.category_changed.connect(self._on_category_changed)
        self._sidebar.side_changed.connect(self._on_side_changed)
        main_layout.addWidget(self._sidebar)

        # Content area
        content_container = QVBoxLayout()
        content_container.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        content_container.setSpacing(SPACE_SM)

        # Header with info
        self._header_label = QLabel("Kinematics — Left")
        self._header_label.setObjectName("headerTitle")
        content_container.addWidget(self._header_label)

        self._info_label = QLabel("")
        self._info_label.setObjectName("captionLabel")
        content_container.addWidget(self._info_label)

        # Plot grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        self._plot_grid = MultiPlotGrid(rows=5, cols=3)
        scroll.setWidget(self._plot_grid)
        content_container.addWidget(scroll, 1)

        main_layout.addLayout(content_container, 1)

        # Empty state (shown when no data loaded)
        self._empty_state = EmptyState(
            icon_name="chart.svg",
            title="No Analysis Data",
            description="Load a patient session and select trials to begin analysis.",
        )

    def load_data(
        self,
        sessions: List[SessionInfo],
        norm_gcd_path: str = "",
    ) -> None:
        """Load GCD data for the given sessions."""
        self._sessions = sessions
        self._trial_data.clear()

        # Load norm data
        if norm_gcd_path and os.path.isfile(norm_gcd_path):
            self._norm_data = self._gcd_svc.read_gcd(norm_gcd_path)

        # Load trial data from first (active) session
        if sessions:
            session = sessions[0]
            for trial in session.left_trials:
                if trial.gcd_filename and trial.gcd_filename != "--":
                    gcd_path = os.path.join(session.directory, trial.gcd_filename + ".GCD")
                    trial.gcd_data = self._gcd_svc.read_gcd(gcd_path)
                    self._trial_data[trial.label] = trial.gcd_data

            for trial in session.right_trials:
                if trial.gcd_filename and trial.gcd_filename != "--":
                    gcd_path = os.path.join(session.directory, trial.gcd_filename + ".GCD")
                    trial.gcd_data = self._gcd_svc.read_gcd(gcd_path)
                    self._trial_data[trial.label] = trial.gcd_data

        # Show initial view
        self._sidebar.select_default()

    def _on_category_changed(self, category: str) -> None:
        self._current_category = category
        self._refresh_plots()

    def _on_side_changed(self, side: str) -> None:
        self._current_side = side
        self._refresh_plots()

    def _get_page_settings(self) -> PageSettings:
        """Return the correct PageSettings for the current category."""
        mapping = {
            "kinematics": self._settings_svc.get_kinematics_settings,
            "sagittal_kinetics": self._settings_svc.get_sagittal_kinetics_settings,
            "coronal_kinetics": self._settings_svc.get_coronal_kinetics_settings,
            "foot_kinematics": self._settings_svc.get_foot_kinematics_settings,
            "muscle_length": self._settings_svc.get_muscle_length_settings,
            "muscle_velocity": self._settings_svc.get_muscle_velocity_settings,
        }
        getter = mapping.get(self._current_category)
        if getter:
            return getter()
        return PageSettings()

    def _refresh_plots(self) -> None:
        """Redraw the plot grid for the current category + side."""
        cat = self._current_category
        side = self._current_side
        palette = LIGHT_PALETTE

        # Update header
        cat_label = cat.replace("_", " ").title()
        side_label = {"L": "Left", "R": "Right", "LR": "Left / Right"}.get(side, side)
        self._header_label.setText(f"{cat_label} — {side_label}")

        # Handle EMG separately (different plot layout)
        if cat == "emg":
            self._draw_emg_plots(side)
            return

        settings = self._get_page_settings()
        if not settings.left_names:
            self._plot_grid.clear_all()
            return

        # Determine variable names based on side
        if side == "LR":
            # Left/Right overlay — use left names for now, overlay right
            var_names = settings.left_names
        elif side == "R":
            var_names = settings.right_names
        else:
            var_names = settings.left_names

        # Get trials for this side
        side_prefix = "Left" if side in ("L", "LR") else "Right"
        trial_keys = [f"{'L' if side in ('L', 'LR') else 'R'}{i}" for i in range(1, 11)]

        x = GCDService.get_gait_cycle_x()

        # Draw each plot in the 5×3 grid
        num_plots = min(len(var_names), 15)
        self._plot_grid.clear_all()

        for plot_idx in range(num_plots):
            row = plot_idx // 3
            col = plot_idx % 3

            var_name = var_names[plot_idx]
            if not var_name:
                continue

            # Collect Y data from loaded trials
            y_data = []
            colors = []
            toe_offs = []
            opp_toe_offs = []
            opp_foot_contacts = []

            for i, key in enumerate(trial_keys):
                gcd = self._trial_data.get(key)
                if gcd is None:
                    continue
                arr = GCDService.get_variable_array(gcd, var_name)
                if arr is not None and len(arr) == 101:
                    y_data.append(arr)
                    colors.append(palette.chart_trial_colors[i % len(palette.chart_trial_colors)])
                    toe_offs.append(GCDService.get_toe_off(gcd, side_prefix))
                    opp_toe_offs.append(GCDService.get_opposite_foot_off(gcd, side_prefix))
                    opp_foot_contacts.append(GCDService.get_opposite_foot_contact(gcd, side_prefix))

            # Norm data (ideal range)
            norm_y_low = norm_y_high = norm_y_mean = None
            norm_x = x
            if self._norm_data:
                norm_key = GCDService.find_norm_variable(self._norm_data, var_name)
                if norm_key:
                    norm_arr = GCDService.get_variable_array(self._norm_data, norm_key)
                    norm_sd = GCDService.get_variable_sd_array(self._norm_data, norm_key)
                    if norm_arr is not None and len(norm_arr) == 101:
                        sd_val = norm_sd if (norm_sd is not None and len(norm_sd) == 101 and np.any(norm_sd > 0.05)) else 5.0
                        norm_y_mean = norm_arr
                        norm_y_high = norm_arr + sd_val
                        norm_y_low = norm_arr - sd_val

            # Get axis settings
            title = settings.titles[plot_idx] if plot_idx < len(settings.titles) else ""
            y_min = settings.lower_limits[plot_idx] if plot_idx < len(settings.lower_limits) else -30
            y_max = settings.upper_limits[plot_idx] if plot_idx < len(settings.upper_limits) else 30
            y_ticks = settings.y_tick_labels[plot_idx] if plot_idx < len(settings.y_tick_labels) else None

            y_label_top = ""
            y_label_bottom = ""
            if settings.y_labels and plot_idx < len(settings.y_labels):
                yl = settings.y_labels[plot_idx]
                if "-" in yl:
                    parts = yl.split("-")
                    y_label_top = parts[0].strip()
                    y_label_bottom = parts[1].strip() if len(parts) > 1 else ""

            show_x = (row == 4)  # only bottom row

            if y_data:
                x_arrays = [x] * len(y_data)
                self._plot_grid.plot_at(
                    row, col,
                    x_data=x_arrays,
                    y_data=y_data,
                    colors=colors,
                    toe_offs=toe_offs,
                    opposite_toe_offs=opp_toe_offs,
                    opposite_foot_contacts=opp_foot_contacts,
                    norm_x=norm_x if norm_y_low is not None else None,
                    norm_y_low=norm_y_low,
                    norm_y_high=norm_y_high,
                    norm_y_mean=norm_y_mean,
                    y_min=y_min,
                    y_max=y_max,
                    title=title,
                    y_ticks=y_ticks if y_ticks else None,
                    y_label_top=y_label_top,
                    y_label_bottom=y_label_bottom,
                    show_x_labels=show_x,
                )
            else:
                canvas = self._plot_grid.get_canvas(row, col)
                canvas.axes.clear()
                canvas.axes.set_title(title, fontsize=9)
                canvas.axes.text(
                    50, 0.5, "No data", ha="center", va="center",
                    transform=canvas.axes.transAxes, color="#9CA3AF",
                )
                canvas.draw_idle()

    def _draw_emg_plots(self, side: str) -> None:
        """Draw EMG plots (different layout than standard kinematics)."""
        settings = self._settings_svc.get_emg_settings()
        if not settings.left_names:
            self._plot_grid.clear_all()
            return

        palette = LIGHT_PALETTE
        x = GCDService.get_gait_cycle_x()

        var_names = settings.left_names if side in ("L", "LR") else settings.right_names
        side_prefix = "Left" if side in ("L", "LR") else "Right"
        trial_keys = [f"{'L' if side in ('L', 'LR') else 'R'}{i}" for i in range(1, 11)]

        self._plot_grid.clear_all()

        for emg_idx in range(min(len(var_names), 5)):
            var_name = var_names[emg_idx]
            title = settings.titles[emg_idx] if emg_idx < len(settings.titles) else var_name

            y_data = []
            colors = []

            for i, key in enumerate(trial_keys):
                gcd = self._trial_data.get(key)
                if gcd is None:
                    continue
                arr = GCDService.get_variable_array(gcd, var_name)
                if arr is not None and len(arr) == 101:
                    y_data.append(arr)
                    colors.append(palette.chart_trial_colors[i % len(palette.chart_trial_colors)])

            # EMG plots go in first column only, one per row
            if y_data:
                self._plot_grid.plot_at(
                    emg_idx, 0,
                    x_data=[x] * len(y_data),
                    y_data=y_data,
                    colors=colors,
                    y_min=-5, y_max=5,
                    title=title,
                    show_x_labels=(emg_idx == len(var_names) - 1),
                )
