# -*- coding: utf-8 -*-
"""
Patient / Session Selection Page — MRN entry, session directory, trial
selection.  Replaces the Tkinter TrialSelection_Page.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re
import shutil
from typing import List, Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.data_models import SessionInfo, TrialInfo
from app.services.gcd_service import GCDService
from app.ui.theme.design_tokens import (
    DARK_PALETTE,
    FONT_FAMILY,
    FONT_SIZE_BODY,
    FONT_SIZE_CAPTION,
    FONT_SIZE_H2,
    FONT_SIZE_H3,
    FONT_SIZE_SMALL,
    FONT_WEIGHT_BOLD,
    LIGHT_PALETTE,
    RADIUS_MD,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
)
from app.ui.widgets.components import SectionCard, SearchBar, EmptyState, create_tinted_icon, create_tinted_pixmap
from app.ui.widgets.smooth_scroll import apply_smooth_scroll

logger = logging.getLogger(__name__)


class SessionRow(QFrame):
    """One row of session configuration (directory, date, trials, etc.)."""

    trials_changed = Signal(int)  # row index
    directory_selected = Signal(str)
    open_presentation_requested = Signal(int)  # row index

    def __init__(self, row_index: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.row_index = row_index
        self.session_info = SessionInfo()
        self.default_browse_dir: str = ""
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_MD, SPACE_SM, SPACE_MD, SPACE_SM)
        layout.setSpacing(SPACE_XS)

        # ── Row header ─────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(SPACE_SM)

        self.row_label = QLabel(f"Session {row_index + 1}")
        self.row_label.setStyleSheet(f"font-size: {FONT_SIZE_H3}px; font-weight: 600;")
        header.addWidget(self.row_label)

        self.dir_btn = QPushButton(" Select Directory…")
        self.dir_btn.setIcon(create_tinted_icon("folder.svg", LIGHT_PALETTE.text_secondary, 14))
        self.dir_btn.setIconSize(QSize(14, 14))
        self.dir_btn.setFixedWidth(145)
        self.dir_btn.setCursor(Qt.PointingHandCursor)
        self.dir_btn.clicked.connect(self._select_directory)
        header.addWidget(self.dir_btn)

        self.import_gcd_btn = QPushButton(" Import GCD…")
        self.import_gcd_btn.setObjectName("secondaryButton")
        self.import_gcd_btn.setIcon(create_tinted_icon("file_text.svg", LIGHT_PALETTE.text_secondary, 14))
        self.import_gcd_btn.setIconSize(QSize(14, 14))
        self.import_gcd_btn.setCursor(Qt.PointingHandCursor)
        self.import_gcd_btn.setToolTip("Import or copy external/generated .GCD files directly into this session folder")
        self.import_gcd_btn.clicked.connect(self._import_gcd_files)
        header.addWidget(self.import_gcd_btn)

        self.refresh_btn = QPushButton(" Refresh")
        self.refresh_btn.setIcon(create_tinted_icon("refresh.svg", LIGHT_PALETTE.text_secondary, 14))
        self.refresh_btn.setIconSize(QSize(14, 14))
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setToolTip("Re-scan directory for newly generated GCD files")
        self.refresh_btn.clicked.connect(self._refresh_gcds)
        header.addWidget(self.refresh_btn)

        self.auto_assign_btn = QPushButton(" Auto-Assign")
        self.auto_assign_btn.setIcon(create_tinted_icon("sliders.svg", LIGHT_PALETTE.text_secondary, 14))
        self.auto_assign_btn.setIconSize(QSize(14, 14))
        self.auto_assign_btn.setCursor(Qt.PointingHandCursor)
        self.auto_assign_btn.setToolTip("Automatically map available GCD files to L1-L10, R1-R10 and MR")
        self.auto_assign_btn.clicked.connect(self._auto_assign_trials)
        header.addWidget(self.auto_assign_btn)

        self.clear_btn = QPushButton(" Clear")
        self.clear_btn.setIcon(create_tinted_icon("x.svg", LIGHT_PALETTE.text_secondary, 14))
        self.clear_btn.setIconSize(QSize(14, 14))
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setToolTip("Clear all dynamic trial selections (L1-L10, R1-R10, and Most Representative)")
        self.clear_btn.clicked.connect(self.clear_dynamic_trials)
        header.addWidget(self.clear_btn)

        self.dir_label = QLabel("No directory selected")
        self.dir_label.setObjectName("captionLabel")
        self.dir_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        header.addWidget(self.dir_label, 1)

        self.view_case_btn = QPushButton(" View MAC Case ↗")
        self.view_case_btn.setObjectName("viewCaseButton")
        self.view_case_btn.setIcon(create_tinted_icon("case_presentation.svg", "#0F766E", 14))
        self.view_case_btn.setIconSize(QSize(14, 14))
        self.view_case_btn.setCursor(Qt.PointingHandCursor)
        self.view_case_btn.setFixedHeight(28)
        self.view_case_btn.setToolTip("Open MAC Case Presentation directly for this specific session")
        self.view_case_btn.setStyleSheet("""
            QPushButton#viewCaseButton {
                background: #F0FDFA;
                color: #0F766E;
                border: 1.5px solid #14B8A6;
                border-radius: 6px;
                padding: 3px 12px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton#viewCaseButton:hover {
                background: #CCFBF1;
                color: #115E59;
                border-color: #0D9488;
            }
        """)
        self.view_case_btn.clicked.connect(lambda: self.open_presentation_requested.emit(self.row_index))
        header.addWidget(self.view_case_btn)

        layout.addLayout(header)

        # ── Metadata row ───────────────────────────────────────────
        meta = QHBoxLayout()
        meta.setSpacing(SPACE_SM)

        meta.addWidget(QLabel("Date:"))
        self.date_edit = QLineEdit()
        self.date_edit.setPlaceholderText("MM/DD/YYYY")
        self.date_edit.setFixedWidth(120)
        meta.addWidget(self.date_edit)

        meta.addWidget(QLabel("Study:"))
        self.study_combo = QComboBox()
        self.study_combo.addItems(["Initial", "Follow-up", "Annual", "Pre-op", "Post-op"])
        self.study_combo.setFixedWidth(110)
        meta.addWidget(self.study_combo)

        meta.addWidget(QLabel("Activity:"))
        self.activity_combo = QComboBox()
        self.activity_combo.addItems(["Walk", "Run", "Stairs", "Other"])
        self.activity_combo.setFixedWidth(100)
        meta.addWidget(self.activity_combo)

        meta.addWidget(QLabel("Orthosis:"))
        self.orthosis_edit = QLineEdit()
        self.orthosis_edit.setFixedWidth(100)
        meta.addWidget(self.orthosis_edit)

        meta.addWidget(QLabel("Assist:"))
        self.assist_edit = QLineEdit()
        self.assist_edit.setFixedWidth(100)
        meta.addWidget(self.assist_edit)

        meta.addStretch()
        layout.addLayout(meta)

        # ── Static file ────────────────────────────────────────────
        static_row = QHBoxLayout()
        static_row.setSpacing(SPACE_SM)
        static_row.addWidget(QLabel("Static:"))
        self.static_combo = QComboBox()
        self.static_combo.setMinimumWidth(250)
        static_row.addWidget(self.static_combo, 1)
        static_row.addStretch()
        layout.addLayout(static_row)

        # ── Trial selectors (L1-L10, R1-R10, MR) ───────────────────
        trials_group = QHBoxLayout()
        trials_group.setSpacing(SPACE_LG)

        # Left trials (2 columns: L1-L5, L6-L10)
        left_box = QVBoxLayout()
        left_lbl = QLabel("Left Trials (L1–L10)")
        left_lbl.setStyleSheet(f"font-weight: 600; font-size: {FONT_SIZE_BODY}px;")
        left_box.addWidget(left_lbl)

        left_cols = QHBoxLayout()
        left_cols.setSpacing(SPACE_MD)
        left_col1 = QVBoxLayout()
        left_col1.setSpacing(SPACE_XS)
        left_col2 = QVBoxLayout()
        left_col2.setSpacing(SPACE_XS)

        self.left_combos: List[QComboBox] = []
        for i in range(1, 11):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            lbl = QLabel(f"L{i}:")
            lbl.setFixedWidth(32)
            row_layout.addWidget(lbl)
            combo = QComboBox()
            combo.addItem("--")
            combo.setMinimumWidth(130)
            combo.currentIndexChanged.connect(self._on_trial_changed)
            row_layout.addWidget(combo, 1)
            if i <= 5:
                left_col1.addLayout(row_layout)
            else:
                left_col2.addLayout(row_layout)
            self.left_combos.append(combo)

        left_cols.addLayout(left_col1)
        left_cols.addLayout(left_col2)
        left_box.addLayout(left_cols)
        trials_group.addLayout(left_box)

        # Right trials (2 columns: R1-R5, R6-R10)
        right_box = QVBoxLayout()
        right_lbl = QLabel("Right Trials (R1–R10)")
        right_lbl.setStyleSheet(f"font-weight: 600; font-size: {FONT_SIZE_BODY}px;")
        right_box.addWidget(right_lbl)

        right_cols = QHBoxLayout()
        right_cols.setSpacing(SPACE_MD)
        right_col1 = QVBoxLayout()
        right_col1.setSpacing(SPACE_XS)
        right_col2 = QVBoxLayout()
        right_col2.setSpacing(SPACE_XS)

        self.right_combos: List[QComboBox] = []
        for i in range(1, 11):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            lbl = QLabel(f"R{i}:")
            lbl.setFixedWidth(32)
            row_layout.addWidget(lbl)
            combo = QComboBox()
            combo.addItem("--")
            combo.setMinimumWidth(130)
            combo.currentIndexChanged.connect(self._on_trial_changed)
            row_layout.addWidget(combo, 1)
            if i <= 5:
                right_col1.addLayout(row_layout)
            else:
                right_col2.addLayout(row_layout)
            self.right_combos.append(combo)

        right_cols.addLayout(right_col1)
        right_cols.addLayout(right_col2)
        right_box.addLayout(right_cols)
        trials_group.addLayout(right_box)

        # MR trials
        mr_box = QVBoxLayout()
        mr_lbl = QLabel("Most Representative")
        mr_lbl.setStyleSheet(f"font-weight: 600; font-size: {FONT_SIZE_BODY}px;")
        mr_box.addWidget(mr_lbl)

        mr_row = QHBoxLayout()
        mr_row.setSpacing(4)
        mr_l_lbl = QLabel("MR Left:")
        mr_l_lbl.setFixedWidth(60)
        mr_row.addWidget(mr_l_lbl)
        self.mr_left_combo = QComboBox()
        self.mr_left_combo.addItem("--")
        self.mr_left_combo.setMinimumWidth(140)
        self.mr_left_combo.currentIndexChanged.connect(lambda idx: self.trials_changed.emit(self.row_index))
        mr_row.addWidget(self.mr_left_combo, 1)
        mr_box.addLayout(mr_row)

        mr_row2 = QHBoxLayout()
        mr_row2.setSpacing(4)
        mr_r_lbl = QLabel("MR Right:")
        mr_r_lbl.setFixedWidth(60)
        mr_row2.addWidget(mr_r_lbl)
        self.mr_right_combo = QComboBox()
        self.mr_right_combo.addItem("--")
        self.mr_right_combo.setMinimumWidth(140)
        self.mr_right_combo.currentIndexChanged.connect(lambda idx: self.trials_changed.emit(self.row_index))
        mr_row2.addWidget(self.mr_right_combo, 1)
        mr_box.addLayout(mr_row2)
        mr_box.addStretch()
        trials_group.addLayout(mr_box)

        trials_group.addStretch()
        layout.addLayout(trials_group)

    def _on_trial_changed(self) -> None:
        self.trials_changed.emit(self.row_index)
        self._sync_mr_options()

    def _sync_mr_options(self) -> None:
        """Synchronize MR combo options with currently assigned Left and Right trials."""
        cur_l = self.mr_left_combo.currentText()
        cur_r = self.mr_right_combo.currentText()

        selected_l = [c.currentText() for c in self.left_combos if c.currentText() != "--"]
        selected_r = [c.currentText() for c in self.right_combos if c.currentText() != "--"]

        if selected_l:
            self.mr_left_combo.blockSignals(True)
            self.mr_left_combo.clear()
            self.mr_left_combo.addItem("--")
            for t in selected_l:
                self.mr_left_combo.addItem(t)
            if cur_l in selected_l:
                self.mr_left_combo.setCurrentText(cur_l)
            else:
                self.mr_left_combo.setCurrentText(selected_l[0])
            self.mr_left_combo.blockSignals(False)

        if selected_r:
            self.mr_right_combo.blockSignals(True)
            self.mr_right_combo.clear()
            self.mr_right_combo.addItem("--")
            for t in selected_r:
                self.mr_right_combo.addItem(t)
            if cur_r in selected_r:
                self.mr_right_combo.setCurrentText(cur_r)
            else:
                self.mr_right_combo.setCurrentText(selected_r[0])
            self.mr_right_combo.blockSignals(False)

    def _select_directory(self) -> None:
        init_dir = self.session_info.directory or self.default_browse_dir or ""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Session Directory", init_dir
        )
        if directory:
            self.set_directory(directory)

    def set_directory(self, directory: str) -> None:
        """Programmatically set and scan the session directory."""
        if not directory or not os.path.isdir(directory):
            return
        directory = str(Path(directory).resolve())
        if self.session_info.directory and os.path.normcase(directory) == os.path.normcase(self.session_info.directory):
            return
        self.clear_directory()
        self.session_info.directory = directory
        short = os.path.basename(directory)
        self.dir_label.setText(directory)
        self.dir_label.setToolTip(directory)
        self.row_label.setText(f"Session {self.row_index + 1} — {short}")

        # Auto-extract date from directory name (e.g. 2025-02-21_0003 or 2025-02-21)
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", short)
        if m:
            yyyy, mm, dd = m.group(1), m.group(2), m.group(3)
            self.date_edit.setText(f"{mm}/{dd}/{yyyy}")

        self._populate_trial_combos(directory, preserve_selection=False)
        self.directory_selected.emit(directory)

    def clear_directory(self):
        """Discard the previous row's selections without touching saved data."""
        self.session_info = SessionInfo()
        self.dir_label.setText("No directory selected")
        self.dir_label.setToolTip("")
        self.row_label.setText(f"Session {self.row_index + 1}")
        self.date_edit.clear()
        for combo in [self.static_combo, *self.left_combos, *self.right_combos,
                      self.mr_left_combo, self.mr_right_combo]:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("--")
            combo.blockSignals(False)

    def _populate_trial_combos(self, directory: str, preserve_selection: bool = True) -> None:
        """Scan the directory for GCD files and populate combos."""
        from app.services.session_organizer import find_all_gcd_files
        gcd_files = [p.stem for p in find_all_gcd_files(directory)]

        # Also scan for static c3d / qtm files
        static_files = []
        if os.path.isdir(directory):
            for f in sorted(os.listdir(directory)):
                up = f.upper()
                if (up.endswith(".C3D") or up.endswith(".QTM")) and "static" in f.lower():
                    static_files.append(f)

        prev_static = self.static_combo.currentText()
        prev_left = [c.currentText() for c in self.left_combos]
        prev_right = [c.currentText() for c in self.right_combos]
        prev_mr_l = self.mr_left_combo.currentText()
        prev_mr_r = self.mr_right_combo.currentText()

        # Populate static combo
        self.static_combo.blockSignals(True)
        self.static_combo.clear()
        self.static_combo.addItem("--")
        for sf in static_files:
            self.static_combo.addItem(sf)
        if preserve_selection and prev_static in static_files:
            self.static_combo.setCurrentText(prev_static)
        elif static_files:
            self.static_combo.setCurrentIndex(1)
        self.static_combo.blockSignals(False)

        # Populate trial combos
        all_combos = self.left_combos + self.right_combos + [self.mr_left_combo, self.mr_right_combo]
        for combo in all_combos:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("--")
            for gf in gcd_files:
                combo.addItem(gf)
            combo.blockSignals(False)

        # Restore or auto-assign
        if preserve_selection and any(pl != "--" for pl in prev_left):
            for i, combo in enumerate(self.left_combos):
                if i < len(prev_left) and prev_left[i] in gcd_files:
                    combo.setCurrentText(prev_left[i])
            for i, combo in enumerate(self.right_combos):
                if i < len(prev_right) and prev_right[i] in gcd_files:
                    combo.setCurrentText(prev_right[i])
            if prev_mr_l in gcd_files:
                self.mr_left_combo.setCurrentText(prev_mr_l)
            if prev_mr_r in gcd_files:
                self.mr_right_combo.setCurrentText(prev_mr_r)
        else:
            self._auto_assign_trials()

    def _auto_assign_trials(self) -> None:
        """Intelligently map available GCD files into L1-L10, R1-R10, and MR trials."""
        directory = self.session_info.directory
        if not directory or not os.path.isdir(directory):
            return

        from app.services.session_organizer import find_all_gcd_files
        gcd_files = [p.stem for p in find_all_gcd_files(directory)]
        if not gcd_files:
            return

        # Check for limb-specific names if present (e.g. Left / Right in file)
        left_named = [f for f in gcd_files if "_l" in f.lower() or "left" in f.lower()]
        right_named = [f for f in gcd_files if "_r" in f.lower() or "right" in f.lower()]

        l_pool = left_named if left_named else gcd_files
        r_pool = right_named if right_named else gcd_files

        for i, combo in enumerate(self.left_combos):
            combo.blockSignals(True)
            combo.setCurrentText(l_pool[i] if i < len(l_pool) else "--")
            combo.blockSignals(False)

        for i, combo in enumerate(self.right_combos):
            combo.blockSignals(True)
            combo.setCurrentText(r_pool[i] if i < len(r_pool) else "--")
            combo.blockSignals(False)

        self._sync_mr_options()
        self.trials_changed.emit(self.row_index)

    def clear_dynamic_trials(self) -> None:
        """Clear all dynamic trial combo selections (L1-L10, R1-R10, MR Left, MR Right)."""
        for combo in self.left_combos:
            combo.blockSignals(True)
            combo.setCurrentText("--")
            combo.blockSignals(False)

        for combo in self.right_combos:
            combo.blockSignals(True)
            combo.setCurrentText("--")
            combo.blockSignals(False)

        self.mr_left_combo.blockSignals(True)
        self.mr_left_combo.clear()
        self.mr_left_combo.addItem("--")
        self.mr_left_combo.setCurrentText("--")
        self.mr_left_combo.blockSignals(False)

        self.mr_right_combo.blockSignals(True)
        self.mr_right_combo.clear()
        self.mr_right_combo.addItem("--")
        self.mr_right_combo.setCurrentText("--")
        self.mr_right_combo.blockSignals(False)

        self.trials_changed.emit(self.row_index)

    def _import_gcd_files(self) -> None:
        """Allow user to select external or generated GCD files to add to the session folder."""
        directory = self.session_info.directory
        if not directory or not os.path.isdir(directory):
            init_dir = self.default_browse_dir or ""
            directory = QFileDialog.getExistingDirectory(
                self, "Select Session Directory to Add GCD Files To", init_dir
            )
            if not directory:
                return
            self.set_directory(directory)

        init_dir = self.session_info.directory or self.default_browse_dir or ""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select GCD File(s) to Add to Session",
            init_dir,
            "GCD Files (*.GCD *.gcd);;All Files (*.*)",
        )
        if not files:
            return

        from app.services.session_organizer import get_gcd_dir
        dest_dir = get_gcd_dir(self.session_info.directory)
        for f in files:
            src = Path(f)
            dest = dest_dir / src.name
            try:
                if src.resolve() != dest.resolve():
                    shutil.copy2(src, dest)
                copied_count += 1
            except Exception as e:
                logger.error("Failed to copy GCD file %s to %s: %s", src, dest, e)

        self._populate_trial_combos(self.session_info.directory, preserve_selection=False)
        if self.isVisible():
            QMessageBox.information(
                self,
                "GCD Files Added",
                f"Successfully added {copied_count} GCD file(s) to session folder:\n{self.session_info.directory}\n\nDropdowns have been updated.",
            )

    def _refresh_gcds(self, notify: bool = False) -> None:
        if self.session_info.directory and os.path.isdir(self.session_info.directory):
            self._populate_trial_combos(self.session_info.directory, preserve_selection=True)
            if notify and self.isVisible():
                QMessageBox.information(
                    self,
                    "Refreshed",
                    f"Session directory re-scanned for GCD files:\n{self.session_info.directory}",
                )
        else:
            if notify and self.isVisible():
                QMessageBox.warning(
                    self,
                    "No Directory",
                    "Please select a session directory first.",
                )

    def get_session_info(self) -> SessionInfo:
        """Collect current widget state into a SessionInfo."""
        s = self.session_info
        s.analysis_date = self.date_edit.text()
        s.study_type = self.study_combo.currentText()
        s.activity_type = self.activity_combo.currentText()
        s.orthosis = self.orthosis_edit.text()
        s.assistive_device = self.assist_edit.text()
        s.static_file = self.static_combo.currentText()
        s.mr_left = self.mr_left_combo.currentText()
        s.mr_right = self.mr_right_combo.currentText()

        for i, combo in enumerate(self.left_combos):
            if i < len(s.left_trials):
                s.left_trials[i].gcd_filename = combo.currentText()
        for i, combo in enumerate(self.right_combos):
            if i < len(s.right_trials):
                s.right_trials[i].gcd_filename = combo.currentText()

        return s


class PatientsPage(QScrollArea):
    """Patient entry and session configuration page."""

    proceed_to_analysis = Signal()  # emitted when user clicks "Save & Proceed"
    patient_selected = Signal(str)  # emitted with MRN
    analysis_context_selected = Signal(str, str)  # patient identity, absolute session directory
    open_session_presentation = Signal(int)  # emitted with session row index

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self._smooth_scroll = apply_smooth_scroll(self)

        self._patients_data_root: str = ""
        self._current_patient_dir: str = ""
        self._loading_patient = False
        self._active_session_dir = ""
        self._discovered_patients: dict[str, str] = {}

        container = QWidget()
        self.setWidget(container)
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        self._layout.setSpacing(SPACE_LG)

        # ── Header ─────────────────────────────────────────────────
        header_row = QHBoxLayout()
        title = QLabel("Patient & Session Selection")
        title.setObjectName("headerTitle")
        title.setStyleSheet(f"font-size: {FONT_SIZE_H2}px; font-weight: 700;")
        header_row.addWidget(title)
        header_row.addStretch()

        self.open_dir_btn = QPushButton(" Open Patient Directory")
        self.open_dir_btn.setIcon(create_tinted_icon("folder.svg", LIGHT_PALETTE.text_secondary, 14))
        self.open_dir_btn.setIconSize(QSize(14, 14))
        self.open_dir_btn.setEnabled(False)
        self.open_dir_btn.setCursor(Qt.PointingHandCursor)
        self.open_dir_btn.clicked.connect(self._on_open_patient_dir)
        header_row.addWidget(self.open_dir_btn)

        self.proceed_btn = QPushButton("Save && Proceed to Presentation →")
        self.proceed_btn.setObjectName("primaryButton")
        self.proceed_btn.setCursor(Qt.PointingHandCursor)
        self.proceed_btn.clicked.connect(self.proceed_to_analysis.emit)
        header_row.addWidget(self.proceed_btn)

        self._layout.addLayout(header_row)

        self._presentation_notice = QLabel()
        self._presentation_notice.setWordWrap(True)
        self._presentation_notice.hide()
        self._layout.addWidget(self._presentation_notice)

        # ── Patient card ───────────────────────────────────────────
        patient_card = SectionCard("Patient Information")

        # Row 1: Global data directory quick patient selector
        quick_row = QHBoxLayout()
        quick_row.setSpacing(SPACE_SM)
        quick_lbl = QLabel("Patient from Data Root:")
        quick_lbl.setFixedWidth(160)
        quick_row.addWidget(quick_lbl)

        self.patient_combo = QComboBox()
        self.patient_combo.setMinimumWidth(320)
        self.patient_combo.setToolTip("Quickly select any patient detected in the global Patients Data Location")
        self.patient_combo.currentIndexChanged.connect(self._on_patient_combo_selected)
        quick_row.addWidget(self.patient_combo, 1)

        self.rescan_patients_btn = QPushButton(" Rescan Patients")
        self.rescan_patients_btn.setIcon(create_tinted_icon("refresh.svg", LIGHT_PALETTE.text_secondary, 15))
        self.rescan_patients_btn.setIconSize(QSize(15, 15))
        self.rescan_patients_btn.setCursor(Qt.PointingHandCursor)
        self.rescan_patients_btn.setToolTip("Re-scan the global Patients Data Location for patient records")
        self.rescan_patients_btn.clicked.connect(lambda: self.scan_patients(notify=True))
        quick_row.addWidget(self.rescan_patients_btn)

        quick_row.addStretch()
        patient_card.add_layout(quick_row)

        # Row 2: MRN manual / active entry
        mrn_row = QHBoxLayout()
        mrn_row.setSpacing(SPACE_SM)
        mrn_lbl = QLabel("Patient Number (MRN):")
        mrn_lbl.setFixedWidth(160)
        mrn_row.addWidget(mrn_lbl)

        self.mrn_input = QLineEdit()
        self.mrn_input.setPlaceholderText("Enter MRN or select above…")
        self.mrn_input.setFixedWidth(240)
        self.mrn_input.returnPressed.connect(self._on_select_patient)
        mrn_row.addWidget(self.mrn_input)

        self.select_patient_btn = QPushButton("Select Patient")
        self.select_patient_btn.setObjectName("primaryButton")
        self.select_patient_btn.setCursor(Qt.PointingHandCursor)
        self.select_patient_btn.clicked.connect(self._on_select_patient)
        mrn_row.addWidget(self.select_patient_btn)

        # Professional SVG Data Root indicator badge
        self.data_root_container = QFrame()
        self.data_root_container.setObjectName("dataRootContainer")
        self.data_root_container.setStyleSheet("background: transparent; border: none;")
        data_root_layout = QHBoxLayout(self.data_root_container)
        data_root_layout.setContentsMargins(SPACE_XS, 0, 0, 0)
        data_root_layout.setSpacing(6)

        self.data_root_icon = QLabel()
        self.data_root_icon.setFixedSize(16, 16)
        self.data_root_icon.setStyleSheet("background: transparent; border: none;")
        data_root_layout.addWidget(self.data_root_icon)

        self.data_root_badge = QLabel("")
        self.data_root_badge.setObjectName("captionLabel")
        self.data_root_badge.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}px; color: {LIGHT_PALETTE.text_muted}; background: transparent; border: none;")
        self.data_root_badge.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        data_root_layout.addWidget(self.data_root_badge, 1)

        mrn_row.addWidget(self.data_root_container, 1)

        patient_card.add_layout(mrn_row)
        self._layout.addWidget(patient_card)

        # ── MR/Ave selector ────────────────────────────────────────
        display_card = SectionCard("Display Mode")
        mode_row = QHBoxLayout()
        self.mr_radio = QRadioButton("Most Representative (MR)")
        self.mr_radio.setChecked(True)
        mode_row.addWidget(self.mr_radio)
        self.ave_radio = QRadioButton("Average")
        mode_row.addWidget(self.ave_radio)
        mode_row.addStretch()
        display_card.add_layout(mode_row)
        self._layout.addWidget(display_card)

        # ── Session rows ───────────────────────────────────────────
        sessions_label = QLabel("Sessions")
        sessions_label.setObjectName("sectionTitle")
        self._layout.addWidget(sessions_label)

        self.session_rows: List[SessionRow] = []
        # Start with 2 rows (Initial + Follow-up), can add more
        for i in range(2):
            row = SessionRow(i)
            row.directory_selected.connect(self._on_session_directory_selected)
            row.open_presentation_requested.connect(self.open_session_presentation.emit)
            self.session_rows.append(row)
            self._layout.addWidget(row)

        # Add session button
        self.add_session_btn = QPushButton("+ Add Session Row")
        self.add_session_btn.setFixedWidth(180)
        self.add_session_btn.clicked.connect(self._add_session_row)
        self._layout.addWidget(self.add_session_btn)

        # ── Bottom Action Row ──────────────────────────────────────
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        self.bottom_open_dir_btn = QPushButton(" Open Patient Directory")
        self.bottom_open_dir_btn.setIcon(create_tinted_icon("folder.svg", LIGHT_PALETTE.text_secondary, 14))
        self.bottom_open_dir_btn.setIconSize(QSize(14, 14))
        self.bottom_open_dir_btn.setEnabled(False)
        self.bottom_open_dir_btn.setCursor(Qt.PointingHandCursor)
        self.bottom_open_dir_btn.clicked.connect(self._on_open_patient_dir)
        bottom_row.addWidget(self.bottom_open_dir_btn)

        self.bottom_proceed_btn = QPushButton("Save && Proceed to Presentation →")
        self.bottom_proceed_btn.setObjectName("primaryButton")
        self.bottom_proceed_btn.setCursor(Qt.PointingHandCursor)
        self.bottom_proceed_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        self.bottom_proceed_btn.clicked.connect(self.proceed_to_analysis.emit)
        bottom_row.addWidget(self.bottom_proceed_btn)

        self._layout.addLayout(bottom_row)
        self._layout.addStretch()

    def set_patients_data_root(self, root_dir: str) -> None:
        """Set the global patient data directory and scan for patient folders."""
        self._patients_data_root = str(root_dir).strip() if root_dir else ""
        for row in self.session_rows:
            row.default_browse_dir = self._patients_data_root

        self._update_data_root_display()
        self.scan_patients(notify=False)

    def _update_data_root_display(self) -> None:
        pal = DARK_PALETTE if getattr(self, "_is_dark", False) else LIGHT_PALETTE
        if self._patients_data_root and os.path.isdir(self._patients_data_root):
            if hasattr(self, "data_root_icon"):
                self.data_root_icon.setPixmap(create_tinted_pixmap("folder.svg", pal.text_muted, 15))
                self.data_root_icon.setVisible(True)
            self.data_root_badge.setText(f"Data Root: {self._patients_data_root}")
            if hasattr(self, "data_root_container"):
                self.data_root_container.setToolTip(self._patients_data_root)
            self.data_root_badge.setToolTip(self._patients_data_root)
        elif self._patients_data_root:
            if hasattr(self, "data_root_icon"):
                self.data_root_icon.setPixmap(create_tinted_pixmap("alert.svg", "#F59E0B", 15))
                self.data_root_icon.setVisible(True)
            self.data_root_badge.setText(f"Data Root path not found: {self._patients_data_root}")
            if hasattr(self, "data_root_container"):
                self.data_root_container.setToolTip(self._patients_data_root)
            self.data_root_badge.setToolTip(self._patients_data_root)
        else:
            if hasattr(self, "data_root_icon"):
                self.data_root_icon.setPixmap(create_tinted_pixmap("alert.svg", "#9CA3AF", 15))
                self.data_root_icon.setVisible(True)
            self.data_root_badge.setText("Configure Patients Data Location in Settings")
            if hasattr(self, "data_root_container"):
                self.data_root_container.setToolTip("Set Patients Data Location under Settings -> File Paths")
            self.data_root_badge.setToolTip("Set Patients Data Location under Settings -> File Paths")

        self.data_root_badge.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}px; color: {pal.text_muted}; background: transparent; border: none;")

    def scan_patients(self, notify: bool = False) -> None:
        """Scan self._patients_data_root for patient directories."""
        self._discovered_patients.clear()
        if self._patients_data_root and os.path.isdir(self._patients_data_root):
            try:
                for entry in sorted(os.listdir(self._patients_data_root)):
                    p = os.path.join(self._patients_data_root, entry)
                    if os.path.isdir(p) and not entry.startswith(".") and entry.lower() != "meshes":
                        self._discovered_patients[entry] = p
            except Exception as e:
                logger.warning("Error scanning patients in %s: %s", self._patients_data_root, e)

        self.patient_combo.blockSignals(True)
        self.patient_combo.clear()
        self.patient_combo.addItem("-- Select Patient from Data Root --", "")
        for name, p in self._discovered_patients.items():
            self.patient_combo.addItem(name, p)
        self.patient_combo.blockSignals(False)

        if notify and self.isVisible():
            QMessageBox.information(
                self,
                "Patients Scanned",
                f"Discovered {len(self._discovered_patients)} patient(s) in:\n{self._patients_data_root}",
            )

    def _find_session_dirs(self, patient_path: str) -> List[str]:
        """Discover session subdirectories inside a patient folder (up to depth 2)."""
        p_path = Path(patient_path)
        sessions = []
        try:
            for root, dirs, files in os.walk(p_path):
                rel = Path(root).relative_to(p_path)
                if len(rel.parts) > 2:
                    continue
                if any(part.startswith(".") for part in rel.parts):
                    continue
                has_gcd = any(f.upper().endswith(".GCD") for f in files)
                has_c3d = any(f.upper().endswith(".C3D") for f in files)
                has_xml = any(f.lower() == "session.xml" for f in files)
                has_date = bool(re.search(r"\d{4}-\d{2}-\d{2}", Path(root).name))
                if has_gcd or has_c3d or has_xml or (has_date and Path(root) != p_path):
                    sessions.append(root)
        except Exception as e:
            logger.warning("Error walking patient path %s: %s", patient_path, e)

        # Sort sessions: those with GCD files first, then by path name
        def sort_key(s: str):
            try:
                from app.services.session_organizer import find_all_gcd_files
                has_gcd = bool(find_all_gcd_files(s))
            except Exception:
                has_gcd = False
            return (0 if has_gcd else 1, s)

        sessions.sort(key=sort_key)
        return sessions

    def load_patient_by_path(self, patient_name: str, patient_path: str) -> None:
        """Load a patient from its path, discover sessions, and auto-populate session rows."""
        if not patient_path or not os.path.isdir(patient_path):
            return
        patient_path = str(Path(patient_path).resolve())
        if self._current_patient_dir and os.path.normcase(patient_path) == os.path.normcase(self._current_patient_dir):
            self.patient_selected.emit(patient_name)
            self.analysis_context_selected.emit(patient_path, self._active_session_dir)
            return
        self._loading_patient = True
        for row in self.session_rows:
            row.clear_directory()
        self._current_patient_dir = patient_path
        self._selected_mrn = patient_name
        self.show_presentation_notice("")
        self.mrn_input.setText(patient_name)

        for row in self.session_rows:
            row.default_browse_dir = patient_path

        session_dirs = self._find_session_dirs(patient_path)
        if session_dirs:
            if len(self.session_rows) > 0:
                self.session_rows[0].set_directory(session_dirs[0])
            if len(session_dirs) > 1:
                if len(self.session_rows) < 2:
                    self._add_session_row()
                self.session_rows[1].set_directory(session_dirs[1])
        else:
            if len(self.session_rows) > 0:
                self.session_rows[0].set_directory(patient_path)

        self._loading_patient = False
        self._active_session_dir = self.session_rows[0].session_info.directory if self.session_rows else ""

        self.open_dir_btn.setEnabled(True)
        if hasattr(self, "bottom_open_dir_btn"):
            self.bottom_open_dir_btn.setEnabled(True)

        self.patient_selected.emit(patient_name)
        self.analysis_context_selected.emit(patient_path, self._active_session_dir)

    def _on_session_directory_selected(self, directory):
        if not self._loading_patient:
            folder = Path(directory).resolve()
            if not self._current_patient_dir or not folder.is_relative_to(Path(self._current_patient_dir).resolve()):
                owners = [Path(path).resolve() for path in self._discovered_patients.values()
                          if folder.is_relative_to(Path(path).resolve())]
                owner = max(owners, key=lambda path: len(path.parts)) if owners else folder.parent
                self._current_patient_dir = str(owner)
                self.mrn_input.setText(owner.name)
                self._selected_mrn = owner.name
                self.patient_selected.emit(owner.name)
            self._active_session_dir = directory
            self.analysis_context_selected.emit(self._current_patient_dir or self.mrn_input.text().strip(), directory)

    def _on_patient_combo_selected(self, index: int) -> None:
        if index <= 0:
            return
        p_name = self.patient_combo.currentText()
        p_path = self.patient_combo.currentData()
        if p_path:
            self.load_patient_by_path(p_name, p_path)

    def _on_select_patient(self) -> None:
        mrn = self.mrn_input.text().strip()
        if not mrn:
            QMessageBox.warning(
                self, "Patient Number Required",
                "Please enter a Patient Number or select one from the Data Root.",
            )
            return

        matched_name = ""
        matched_path = ""
        for name, path in self._discovered_patients.items():
            if mrn.lower() == name.lower() or mrn.lower() in name.lower():
                matched_name = name
                matched_path = path
                break

        if matched_path:
            idx = self.patient_combo.findText(matched_name)
            if idx >= 0:
                self.patient_combo.blockSignals(True)
                self.patient_combo.setCurrentIndex(idx)
                self.patient_combo.blockSignals(False)
            self.load_patient_by_path(matched_name, matched_path)
        else:
            if self._current_patient_dir or self.mrn_input.text().strip() != getattr(self, "_selected_mrn", ""):
                for row in self.session_rows:
                    row.clear_directory()
                self._current_patient_dir = self._active_session_dir = ""
            self._selected_mrn = mrn
            self.open_dir_btn.setEnabled(True)
            if hasattr(self, "bottom_open_dir_btn"):
                self.bottom_open_dir_btn.setEnabled(True)
            self.patient_selected.emit(mrn)
            self.analysis_context_selected.emit(mrn, self._active_session_dir)

    def _add_session_row(self) -> None:
        idx = len(self.session_rows)
        row = SessionRow(idx)
        row.directory_selected.connect(self._on_session_directory_selected)
        row.open_presentation_requested.connect(self.open_session_presentation.emit)
        row.default_browse_dir = self._current_patient_dir or self._patients_data_root or ""
        self.session_rows.append(row)
        # Insert before the stretch
        self._layout.insertWidget(self._layout.count() - 2, row)

    def get_all_sessions(self) -> List[SessionInfo]:
        return [row.get_session_info() for row in self.session_rows]

    def get_mrn(self) -> str:
        return self.mrn_input.text().strip()

    def has_selected_patient(self) -> bool:
        return bool(self.get_mrn() and self.get_mrn() == getattr(self, "_selected_mrn", ""))

    def show_presentation_notice(self, message: str) -> None:
        self._presentation_notice.setText(message)
        self._presentation_notice.setVisible(bool(message))

    def get_display_mode(self) -> str:
        return "MR" if self.mr_radio.isChecked() else "Ave"

    def load_session(self, session_path: str) -> None:
        """Load an active session directory and extract patient MRN into Session 1."""
        if not session_path:
            return
        p = Path(session_path)
        session_dir = str(p.parent if p.is_file() else p)

        # Extract MRN from directory hierarchy: .../Data/<Patient_MRN>/<Session_Date>
        parts = Path(session_dir).parts
        mrn = ""
        for i, part in enumerate(parts):
            if part.lower() == "data" and i + 1 < len(parts):
                mrn = parts[i + 1]
                break
        if not mrn and len(parts) >= 2:
            mrn = Path(session_dir).parent.name

        if mrn:
            self._selected_mrn = mrn
            self.mrn_input.setText(mrn)
            idx = self.patient_combo.findText(mrn)
            if idx >= 0:
                self.patient_combo.blockSignals(True)
                self.patient_combo.setCurrentIndex(idx)
                self.patient_combo.blockSignals(False)
                self._current_patient_dir = self.patient_combo.itemData(idx)
            self.open_dir_btn.setEnabled(True)
            if hasattr(self, "bottom_open_dir_btn"):
                self.bottom_open_dir_btn.setEnabled(True)

        if self.session_rows:
            self._loading_patient = True
            self.session_rows[0].set_directory(session_dir)
            self._active_session_dir = session_dir
            self._loading_patient = False

    def _on_open_patient_dir(self) -> None:
        """Open the patient's data folder in system file manager."""
        target = self._current_patient_dir
        if not target and self.session_rows and self.session_rows[0].session_info.directory:
            target = os.path.dirname(self.session_rows[0].session_info.directory)
        if not target and self._patients_data_root:
            target = self._patients_data_root

        if target and os.path.exists(target):
            try:
                os.startfile(target)
            except Exception as e:
                logger.warning("Could not open directory %s: %s", target, e)

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        """Update any custom styled labels and SVG icon tints for light/dark theme."""
        self._is_dark = dark
        pal = palette or (DARK_PALETTE if dark else LIGHT_PALETTE)
        icon_col = pal.text_secondary

        if hasattr(self, "open_dir_btn"):
            self.open_dir_btn.setIcon(create_tinted_icon("folder.svg", icon_col, 14))
        if hasattr(self, "bottom_open_dir_btn"):
            self.bottom_open_dir_btn.setIcon(create_tinted_icon("folder.svg", icon_col, 14))
        if hasattr(self, "rescan_patients_btn"):
            self.rescan_patients_btn.setIcon(create_tinted_icon("refresh.svg", icon_col, 15))
        if hasattr(self, "session_rows"):
            for row in self.session_rows:
                if hasattr(row, "refresh_btn"):
                    row.refresh_btn.setIcon(create_tinted_icon("refresh.svg", icon_col, 14))
                if hasattr(row, "import_gcd_btn"):
                    row.import_gcd_btn.setIcon(create_tinted_icon("file_text.svg", icon_col, 14))
                if hasattr(row, "dir_btn"):
                    row.dir_btn.setIcon(create_tinted_icon("folder.svg", icon_col, 14))
                if hasattr(row, "auto_assign_btn"):
                    row.auto_assign_btn.setIcon(create_tinted_icon("sliders.svg", icon_col, 14))
                if hasattr(row, "clear_btn"):
                    row.clear_btn.setIcon(create_tinted_icon("x.svg", icon_col, 14))
                if hasattr(row, "view_case_btn"):
                    if dark:
                        row.view_case_btn.setIcon(create_tinted_icon("case_presentation.svg", "#2DD4BF", 14))
                        row.view_case_btn.setStyleSheet("""
                            QPushButton#viewCaseButton {
                                background: #134E4A;
                                color: #2DD4BF;
                                border: 1.5px solid #14B8A6;
                                border-radius: 6px;
                                padding: 3px 12px;
                                font-weight: 700;
                                font-size: 12px;
                            }
                            QPushButton#viewCaseButton:hover {
                                background: #115E59;
                                color: #5EEAD4;
                            }
                        """)
                    else:
                        row.view_case_btn.setIcon(create_tinted_icon("case_presentation.svg", "#0F766E", 14))
                        row.view_case_btn.setStyleSheet("""
                            QPushButton#viewCaseButton {
                                background: #F0FDFA;
                                color: #0F766E;
                                border: 1.5px solid #14B8A6;
                                border-radius: 6px;
                                padding: 3px 12px;
                                font-weight: 700;
                                font-size: 12px;
                            }
                            QPushButton#viewCaseButton:hover {
                                background: #CCFBF1;
                                color: #115E59;
                                border-color: #0D9488;
                            }
                        """)

        self._update_data_root_display()
