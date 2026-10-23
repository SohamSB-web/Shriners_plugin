# -*- coding: utf-8 -*-
"""
Settings Page — organized settings for paths, processing, EMG, display.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.models.data_models import AppSettings
from app.ui.theme.design_tokens import FONT_SIZE_H2, SPACE_LG, SPACE_MD, SPACE_SM, SPACE_XL, SPACE_XS
from app.ui.widgets.components import CollapsibleSectionCard, NotificationBanner, SectionCard
from app.ui.widgets.smooth_scroll import apply_smooth_scroll

logger = logging.getLogger(__name__)


class SettingsPage(QScrollArea):
    """Application settings page."""

    theme_changed = Signal(bool)  # True = dark mode
    settings_saved = Signal(AppSettings)

    def __init__(self, settings: AppSettings | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self._smooth_scroll = apply_smooth_scroll(self)

        self._settings = settings or AppSettings()

        container = QWidget()
        self.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        layout.setSpacing(SPACE_LG)

        # Header
        header_row = QHBoxLayout()
        header = QLabel("Settings")
        header.setObjectName("headerTitle")
        header.setStyleSheet(f"font-size: {FONT_SIZE_H2}px; font-weight: 700;")
        header_row.addWidget(header)
        header_row.addStretch()
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save)
        header_row.addWidget(save_btn)
        layout.addLayout(header_row)

        self._notification = NotificationBanner()
        layout.addWidget(self._notification)

        # ── General ────────────────────────────────────────────────
        general = SectionCard("General")
        row = QHBoxLayout()
        row.addWidget(QLabel("Institution Name:"))
        self._institution = QLineEdit(self._settings.institute_name)
        row.addWidget(self._institution, 1)
        general.add_layout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Conda Environment:"))
        self._conda_env = QLineEdit(self._settings.conda_env_name)
        self._conda_env.setFixedWidth(200)
        row2.addWidget(self._conda_env)
        row2.addStretch()
        general.add_layout(row2)
        layout.addWidget(general)

        # ── Display ────────────────────────────────────────────────
        display = SectionCard("Display")
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme:"))
        self._light_radio = QRadioButton("Light")
        self._dark_radio = QRadioButton("Dark")
        if self._settings.dark_mode:
            self._dark_radio.setChecked(True)
        else:
            self._light_radio.setChecked(True)
        self._dark_radio.toggled.connect(lambda checked: self.theme_changed.emit(True) if checked else None)
        self._light_radio.toggled.connect(lambda checked: self.theme_changed.emit(False) if checked else None)
        theme_row.addWidget(self._light_radio)
        theme_row.addWidget(self._dark_radio)
        theme_row.addStretch()
        display.add_layout(theme_row)

        mr_row = QHBoxLayout()
        mr_row.addWidget(QLabel("Default Display Mode:"))
        self._mr_combo = QComboBox()
        self._mr_combo.addItems(["MR (Most Representative)", "Ave (Average)"])
        if self._settings.mr_or_ave == "Ave":
            self._mr_combo.setCurrentIndex(1)
        mr_row.addWidget(self._mr_combo)
        mr_row.addStretch()
        display.add_layout(mr_row)
        layout.addWidget(display)

        # ── Advanced Laboratory Configuration (Optional) ────────────
        self._paths_card = CollapsibleSectionCard(
            title="Advanced Laboratory Configuration (Optional)",
            subtitle=(
                "Default paths are automatically detected from the workspace. "
                "Expand only if connecting to an external hospital server, network storage, "
                "or custom Vicon / QTM / GCD model directories."
            ),
            collapsed=True,
            expand_text="Configure File Paths ▾",
            collapse_text="Hide File Paths ▴",
        )
        paths = self._paths_card

        note_lbl = QLabel(
            "ℹ Default paths are relative to the current workstation. "
            "Modify these paths if your laboratory stores patient records or models on a shared network drive."
        )
        note_lbl.setObjectName("fieldHint")
        note_lbl.setStyleSheet(f"font-size: {SPACE_SM + 4}px; color: #9CA3AF; padding: 2px 0 6px 0;")
        note_lbl.setWordWrap(True)
        paths.add_widget(note_lbl)

        self._path_edits: dict[str, QLineEdit] = {}
        for label, attr, placeholder, path_type in [
            ("Patients Data Location:", "patients_data_location", "Root directory for patient records and sessions", "dir"),
            ("Vicon Files Location:", "vicon_files_location", "Path to Vicon files", "dir"),
            ("Display Settings:", "display_settings_location", "Path for display settings", "dir"),
            ("QTM-GRPC Location:", "qtm_grpc_location", "Path to QTM-GRPC directory containing gapi.py", "dir"),
            ("PDF Output:", "initial_path_for_pdf", "Default PDF output path", "dir"),
            ("Norm GCD (Walk):", "norm_ave_gcd_filename", "Path to TD_Ave.GCD", "file"),
            ("Norm GCD (Run):", "norm_run_ave_gcd_filename", "Path to TD_Run_Ave.GCD", "file"),
        ]:
            r = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(175)
            r.addWidget(lbl)
            le = QLineEdit(str(getattr(self._settings, attr, "")))
            le.setPlaceholderText(placeholder)
            r.addWidget(le, 1)
            browse = QPushButton("…")
            browse.setFixedWidth(36)
            browse.setCursor(Qt.PointingHandCursor)
            if path_type == "dir":
                browse.clicked.connect(self._make_browse_dir(le, f"Select {label.rstrip(':')}"))
            else:
                browse.clicked.connect(self._make_browse_file(le, f"Select {label.rstrip(':')}"))
            r.addWidget(browse)
            paths.add_layout(r)
            setattr(self, f"_path_{attr}", le)
            self._path_edits[attr] = le
        layout.addWidget(paths)

        # ── Gait Processing ────────────────────────────────────────
        gait = SectionCard("Gait Processing")
        hip_row = QHBoxLayout()
        hip_row.addWidget(QLabel("Hip Model:"))
        self._hip_model = QComboBox()
        self._hip_model.addItems(["Harrington2", "Harrington", "Newington"])
        hip_row.addWidget(self._hip_model)
        hip_row.addStretch()
        gait.add_layout(hip_row)

        coord_row = QHBoxLayout()
        coord_row.addWidget(QLabel("Shank Coordinate System:"))
        self._shank_coord = QComboBox()
        self._shank_coord.addItems(["Distal", "Proximal"])
        coord_row.addWidget(self._shank_coord)
        coord_row.addStretch()
        gait.add_layout(coord_row)
        layout.addWidget(gait)

        # ── EMG ────────────────────────────────────────────────────
        emg = SectionCard("EMG Configuration")
        emg_row = QHBoxLayout()
        emg_row.addWidget(QLabel("EMG Min On Threshold:"))
        self._emg_min = QLineEdit(str(self._settings.emg_min_on))
        self._emg_min.setFixedWidth(80)
        emg_row.addWidget(self._emg_min)
        emg_row.addStretch()
        emg.add_layout(emg_row)
        layout.addWidget(emg)

        # ── About ──────────────────────────────────────────────────
        about = SectionCard("About")
        about.add_widget(QLabel("Shriners Gait Analysis Platform"))
        about.add_widget(QLabel("PySide6 Clinical Workstation"))
        about.add_widget(QLabel("Based on MAC_CasePresentation by psaraswat"))
        layout.addWidget(about)

        layout.addStretch()

    def _make_browse_dir(self, line_edit: QLineEdit, title: str):
        def _browse():
            init = line_edit.text().strip() or ""
            d = QFileDialog.getExistingDirectory(self, title, init)
            if d:
                line_edit.setText(d)
        return _browse

    def _make_browse_file(self, line_edit: QLineEdit, title: str):
        def _browse():
            init = line_edit.text().strip() or ""
            f, _ = QFileDialog.getOpenFileName(self, title, init, "GCD Files (*.GCD *.gcd);;All Files (*.*)")
            if f:
                line_edit.setText(f)
        return _browse

    def _save(self) -> None:
        self._settings.institute_name = self._institution.text().strip()
        self._settings.conda_env_name = self._conda_env.text().strip()
        self._settings.dark_mode = self._dark_radio.isChecked()
        self._settings.mr_or_ave = "Ave" if self._mr_combo.currentIndex() == 1 else "MR"
        try:
            self._settings.emg_min_on = float(self._emg_min.text())
        except ValueError:
            pass

        # Save all path attributes
        if hasattr(self, "_path_patients_data_location"):
            self._settings.patients_data_location = self._path_patients_data_location.text().strip()
        if hasattr(self, "_path_vicon_files_location"):
            self._settings.vicon_files_location = self._path_vicon_files_location.text().strip()
        if hasattr(self, "_path_display_settings_location"):
            self._settings.display_settings_location = self._path_display_settings_location.text().strip()
        if hasattr(self, "_path_qtm_grpc_location"):
            self._settings.qtm_grpc_location = self._path_qtm_grpc_location.text().strip()
        if hasattr(self, "_path_initial_path_for_pdf"):
            self._settings.initial_path_for_pdf = self._path_initial_path_for_pdf.text().strip()
        if hasattr(self, "_path_norm_ave_gcd_filename"):
            self._settings.norm_ave_gcd_filename = self._path_norm_ave_gcd_filename.text().strip()
        if hasattr(self, "_path_norm_run_ave_gcd_filename"):
            self._settings.norm_run_ave_gcd_filename = self._path_norm_run_ave_gcd_filename.text().strip()

        # Persist to FilePathSettings.py
        from app.services.settings_service import SettingsService
        SettingsService().save_app_settings(self._settings)

        self.settings_saved.emit(self._settings)
        self._notification.show_message("Settings saved successfully", "success")

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        """Synchronize settings radio buttons when theme is changed externally."""
        self._dark_radio.blockSignals(True)
        self._light_radio.blockSignals(True)
        if dark:
            self._dark_radio.setChecked(True)
        else:
            self._light_radio.setChecked(True)
        self._dark_radio.blockSignals(False)
        self._light_radio.blockSignals(False)

