# -*- coding: utf-8 -*-
"""
Update Measurements GUI Page — Shriners Gait Analysis Platform.

Allows opening any patient session to view and update patient & anthropometric
measurements, with full bidirectional synchronization to Qualisys Track Manager (QTM)
and automatic propagation to all dynamic and static trial files in the session folder.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import xml.etree.ElementTree as ET

from PySide6.QtCore import Qt, Signal, QSignalBlocker, QTimer, QSize
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.anthropometric_sync_service import (
    ANTHROPOMETRIC_FIELDS,
    PATIENT_FIELDS,
    AnthropometricSyncService,
    format_measurement,
    get_session_xml_path,
    parameter_text,
    same_field_value,
    update_session_xml,
    validate_parameter,
    validate_patient_field,
)
from app.ui.theme.design_tokens import (
    COLOR_ACCENT,
    COLOR_MUTED,
    COLOR_NORMAL,
    COLOR_PRIMARY,
    COLOR_WARNING,
    DARK_PALETTE,
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
    LIGHT_PALETTE,
    RADIUS_MD,
    RADIUS_SM,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
)
from app.ui.widgets.components import SectionCard, create_tinted_icon
from app.ui.widgets.smooth_scroll import apply_smooth_scroll

logger = logging.getLogger(__name__)

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class UpdateMeasurementsPage(QScrollArea):
    """
    Dedicated clinical workstation page for viewing and updating session measurements.

    Features:
    - Session selector: open any session folder or session.xml.
    - Patient metadata: Name, ID, Sex, Date of Birth.
    - Anthropometric measurements: BodyMass (1 decimal), Height (3 decimals),
      InterAsisDistance (3 decimals), bilateral Leg Length, Knee Width,
      Ankle Width, ASIS-to-GT distance (3 decimals).
    - Session trials sync status: lists all static & dynamic trials in the session
      and confirms they inherit the session measurements.
    - Full bidirectional sync with QTM and session.xml.
    """

    session_selected = Signal(str)
    measurements_updated = Signal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("updateMeasurementsPage")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)

        self._session_path: Optional[str] = None
        self._session_dir: Optional[Path] = None
        self._data_root: Optional[str] = None
        self._is_populating: bool = False
        self._is_dark: bool = False

        # Dirty field tracking
        self._dirty_fields: Set[str] = set()
        self._field_revisions: Dict[str, int] = {}
        self._last_external_mtime: Dict[str, float] = {}

        # Sync service setup
        self._anthro_generation: int = 0
        self._anthro_context: Optional[Tuple[str]] = None
        self._anthro_connected: bool = False
        self._anthro_sync = AnthropometricSyncService(self)
        self._anthro_sync.finished.connect(self._on_anthro_sync_finished)
        self._anthro_sync.write_finished.connect(self._on_anthro_write_finished)

        # Timers
        self._auto_sync_timer = QTimer(self)
        self._auto_sync_timer.setSingleShot(True)
        self._auto_sync_timer.setInterval(3500)
        self._auto_sync_timer.timeout.connect(self._on_auto_sync_timer_timeout)

        self._external_sync_timer = QTimer(self)
        self._external_sync_timer.setInterval(1200)
        self._external_sync_timer.timeout.connect(self._poll_external_sync)
        self._external_sync_timer.start()

        self._init_ui()
        apply_smooth_scroll(self)
        self.clear_session()

    def set_data_root(self, root: str) -> None:
        """Set root patient data directory for file browsing."""
        self._data_root = root

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        """Update icons, badges and styles when theme toggles."""
        self._is_dark = dark
        pal = palette or (DARK_PALETTE if dark else LIGHT_PALETTE)
        if hasattr(self, "_browse_btn"):
            self._browse_btn.setIcon(create_tinted_icon("folder.svg", pal.text_secondary, 15))
        if hasattr(self, "_reload_btn"):
            self._reload_btn.setIcon(create_tinted_icon("refresh.svg", pal.text_secondary, 15))
        self._update_badges()

    # ═══════════════════════════════════════════════════════════════════
    #  UI Construction
    # ═══════════════════════════════════════════════════════════════════

    def _init_ui(self) -> None:
        container = QWidget()
        self.setWidget(container)

        self._main_layout = QVBoxLayout(container)
        self._main_layout.setContentsMargins(SPACE_XL * 2, SPACE_XL, SPACE_XL * 2, SPACE_XL * 2)
        self._main_layout.setSpacing(SPACE_LG)

        # ── 1. Page Header ──────────────────────────────────────────────
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        header_title = QLabel("UPDATE MEASUREMENTS")
        header_title.setObjectName("pageHeaderTitle")
        header_title.setFont(QFont(FONT_FAMILY, FONT_SIZE_H2, QFont.Bold))
        header_layout.addWidget(header_title)

        header_sub = QLabel(
            "Open any patient session to view and update measurements. "
            "All changes synchronize automatically with QTM and propagate to all session trials."
        )
        header_sub.setObjectName("pageHeaderSub")
        header_sub.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        header_sub.setWordWrap(True)
        header_layout.addWidget(header_sub)

        self._main_layout.addLayout(header_layout)

        # ── 2. Session Selector Card ────────────────────────────────────
        session_card = SectionCard("SESSION SELECTION")
        s_layout = QVBoxLayout()
        s_layout.setSpacing(SPACE_SM)

        # File browser row
        path_row = QHBoxLayout()
        path_row.setSpacing(SPACE_SM)

        self._session_path_edit = QLineEdit()
        self._session_path_edit.setPlaceholderText("Select a session folder or session.xml file...")
        self._session_path_edit.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
        self._session_path_edit.returnPressed.connect(self._on_session_path_entered)
        path_row.addWidget(self._session_path_edit, 1)

        self._browse_btn = QPushButton(" Browse Session…")
        self._browse_btn.setObjectName("secondaryButton")
        self._browse_btn.setIcon(create_tinted_icon("folder.svg", LIGHT_PALETTE.text_secondary, 15))
        self._browse_btn.setIconSize(QSize(15, 15))
        self._browse_btn.setCursor(Qt.PointingHandCursor)
        self._browse_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_MEDIUM))
        self._browse_btn.clicked.connect(self._browse_session)
        path_row.addWidget(self._browse_btn)

        self._reload_btn = QPushButton(" Reload")
        self._reload_btn.setObjectName("secondaryButton")
        self._reload_btn.setIcon(create_tinted_icon("refresh.svg", LIGHT_PALETTE.text_secondary, 15))
        self._reload_btn.setIconSize(QSize(15, 15))
        self._reload_btn.setCursor(Qt.PointingHandCursor)
        self._reload_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_MEDIUM))
        self._reload_btn.clicked.connect(self._reload_current_session)
        path_row.addWidget(self._reload_btn)

        s_layout.addLayout(path_row)

        # Session Metadata Badges Row
        badge_row = QHBoxLayout()
        badge_row.setSpacing(SPACE_MD)

        self._badge_patient = QLabel("Patient: —")
        self._badge_patient.setObjectName("captionLabel")
        self._badge_patient.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}px; font-weight: 600; color: {COLOR_PRIMARY};")
        badge_row.addWidget(self._badge_patient)

        self._badge_session = QLabel("Session: —")
        self._badge_session.setObjectName("captionLabel")
        self._badge_session.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}px; color: {COLOR_MUTED};")
        badge_row.addWidget(self._badge_session)

        self._badge_trials = QLabel("Trials: 0")
        self._badge_trials.setObjectName("captionLabel")
        self._badge_trials.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}px; color: {COLOR_MUTED};")
        badge_row.addWidget(self._badge_trials)

        self._badge_sync = QLabel("● Ready")
        self._badge_sync.setObjectName("captionLabel")
        self._badge_sync.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}px; font-weight: 600; color: {COLOR_NORMAL};")
        badge_row.addWidget(self._badge_sync)

        badge_row.addStretch()
        s_layout.addLayout(badge_row)

        session_card.add_layout(s_layout)
        self._main_layout.addWidget(session_card)

        # ── 3. Patient Information Card ─────────────────────────────────
        patient_card = SectionCard("PATIENT INFORMATION")
        p_grid = QGridLayout()
        p_grid.setSpacing(SPACE_SM)
        p_grid.setColumnStretch(1, 1)
        p_grid.setColumnStretch(3, 1)

        # Row 0: Name / ID
        p_grid.addWidget(self._create_field_label("Patient Name"), 0, 0, Qt.AlignRight)
        self._patient_name = QLineEdit()
        self._patient_name.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        self._patient_name.setObjectName("Name")
        self._patient_name.textEdited.connect(lambda t: self._on_field_edited("Name"))
        self._patient_name.editingFinished.connect(lambda: self._on_field_commit("Name"))
        p_grid.addWidget(self._patient_name, 0, 1)

        p_grid.addWidget(self._create_field_label("Patient ID / MRN"), 0, 2, Qt.AlignRight)
        self._patient_id = QLineEdit()
        self._patient_id.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        self._patient_id.setObjectName("ID")
        self._patient_id.textEdited.connect(lambda t: self._on_field_edited("ID"))
        self._patient_id.editingFinished.connect(lambda: self._on_field_commit("ID"))
        p_grid.addWidget(self._patient_id, 0, 3)

        # Row 1: Sex / Date of Birth
        p_grid.addWidget(self._create_field_label("Sex"), 1, 0, Qt.AlignRight)
        self._sex = QComboBox()
        self._sex.addItems(["", "Female", "Male", "Other"])
        self._style_combo(self._sex)
        self._sex.setObjectName("Sex")
        self._sex.activated.connect(lambda idx: self._on_patient_combo_choice("Sex"))
        p_grid.addWidget(self._sex, 1, 1)

        p_grid.addWidget(self._create_field_label("Date of Birth"), 1, 2, Qt.AlignRight)
        dob_row = QHBoxLayout()
        dob_row.setSpacing(SPACE_XS)

        self._dob_day = QComboBox()
        self._dob_day.addItems([f"{i:02d}" for i in range(1, 32)])
        self._style_combo(self._dob_day)
        self._dob_day.setFixedWidth(65)
        self._dob_day.activated.connect(lambda idx: self._on_patient_combo_choice("DOB"))
        dob_row.addWidget(self._dob_day)

        self._dob_month = QComboBox()
        self._dob_month.addItems(MONTH_NAMES)
        self._style_combo(self._dob_month)
        self._dob_month.setFixedWidth(70)
        self._dob_month.activated.connect(lambda idx: self._on_patient_combo_choice("DOB"))
        dob_row.addWidget(self._dob_month)

        self._dob_year = QComboBox()
        self._dob_year.addItems([str(y) for y in range(1930, 2036)])
        self._style_combo(self._dob_year)
        self._dob_year.setFixedWidth(80)
        self._dob_year.activated.connect(lambda idx: self._on_patient_combo_choice("DOB"))
        dob_row.addWidget(self._dob_year)

        dob_row.addStretch()
        p_grid.addLayout(dob_row, 1, 3)

        patient_card.add_layout(p_grid)
        self._main_layout.addWidget(patient_card)

        # ── 4. Anthropometric Parameters Card ───────────────────────────
        anthro_card = SectionCard("ANTHROPOMETRIC MEASUREMENTS")
        a_vbox = QVBoxLayout()
        a_vbox.setSpacing(SPACE_MD)

        # Explanatory Banner
        banner = QFrame()
        banner.setStyleSheet(
            f"background-color: rgba(15, 118, 110, 0.08); border-left: 3px solid {COLOR_PRIMARY}; "
            f"border-radius: {RADIUS_SM}px; padding: 8px 12px;"
        )
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(SPACE_XS, SPACE_XS, SPACE_XS, SPACE_XS)
        banner_lbl = QLabel(
            "<b>Session-wide Synchronized Measurements:</b> Any changes saved here apply to "
            "the session root, all static trials, all dynamic trials, and Qualisys Track Manager (QTM)."
        )
        banner_lbl.setObjectName("captionLabel")
        banner_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION))
        banner_lbl.setStyleSheet(f"color: {COLOR_PRIMARY}; background: transparent; border: none;")
        banner_lbl.setWordWrap(True)
        banner_layout.addWidget(banner_lbl)
        a_vbox.addWidget(banner)

        # Grid of measurements
        a_grid = QGridLayout()
        a_grid.setSpacing(SPACE_SM)
        a_grid.setColumnStretch(1, 1)
        a_grid.setColumnStretch(3, 1)

        # General Measurements
        a_grid.addWidget(self._create_field_label("Body Mass (kg)"), 0, 0, Qt.AlignRight)
        self._body_mass = QLineEdit()
        self._body_mass.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
        self._body_mass.setAlignment(Qt.AlignCenter)
        self._body_mass.setObjectName("BodyMass")
        a_grid.addWidget(self._body_mass, 0, 1)

        a_grid.addWidget(self._create_field_label("Height (m)"), 0, 2, Qt.AlignRight)
        self._height = QLineEdit()
        self._height.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
        self._height.setAlignment(Qt.AlignCenter)
        self._height.setObjectName("Height")
        a_grid.addWidget(self._height, 0, 3)

        a_grid.addWidget(self._create_field_label("Inter-ASIS Distance (m)"), 1, 0, Qt.AlignRight)
        self._asis_dist = QLineEdit()
        self._asis_dist.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
        self._asis_dist.setAlignment(Qt.AlignCenter)
        self._asis_dist.setObjectName("InterAsisDistance")
        a_grid.addWidget(self._asis_dist, 1, 1)

        # Bilateral Headers
        left_header = QLabel("Left Side")
        left_header.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        left_header.setAlignment(Qt.AlignCenter)
        a_grid.addWidget(left_header, 2, 1)

        right_header = QLabel("Right Side")
        right_header.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        right_header.setAlignment(Qt.AlignCenter)
        a_grid.addWidget(right_header, 2, 3)

        # Bilateral fields
        self._anthro_inputs: Dict[str, QLineEdit] = {
            "BodyMass": self._body_mass,
            "Height": self._height,
            "InterAsisDistance": self._asis_dist,
        }

        bilateral_specs = [
            ("Leg Length (m)", "LeftLegLength", "RightLegLength"),
            ("Knee Width (m)", "LeftKneeWidth", "RightKneeWidth"),
            ("Ankle Width (m)", "LeftAnkleWidth", "RightAnkleWidth"),
            ("ASIS-to-GT (m)", "LeftAsisTrocanterDistance", "RightAsisTrocanterDistance"),
        ]

        for i, (label_text, left_key, right_key) in enumerate(bilateral_specs):
            row = 3 + i
            a_grid.addWidget(self._create_field_label(label_text), row, 0, Qt.AlignRight)

            left_edit = QLineEdit()
            left_edit.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
            left_edit.setAlignment(Qt.AlignCenter)
            left_edit.setObjectName(left_key)
            a_grid.addWidget(left_edit, row, 1)
            self._anthro_inputs[left_key] = left_edit

            right_edit = QLineEdit()
            right_edit.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
            right_edit.setAlignment(Qt.AlignCenter)
            right_edit.setObjectName(right_key)
            a_grid.addWidget(right_edit, row, 3)
            self._anthro_inputs[right_key] = right_edit

        # Connect all anthro edits
        for name, widget in self._anthro_inputs.items():
            widget.setToolTip(f"{name}: enter a numeric value (e.g. 0.600 for meters, 150.0 for kg)")
            widget.textEdited.connect(lambda text, n=name: self._on_field_edited(n))
            widget.editingFinished.connect(lambda n=name: self._on_field_commit(n))

        a_vbox.addLayout(a_grid)
        anthro_card.add_layout(a_vbox)
        self._main_layout.addWidget(anthro_card)

        # ── 5. Session Trials Synchronization Card ──────────────────────
        trials_card = SectionCard("SESSION TRIALS SYNCHRONIZATION STATUS")
        t_vbox = QVBoxLayout()
        t_vbox.setSpacing(SPACE_SM)

        self._trials_table = QTableWidget(0, 4)
        self._trials_table.setHorizontalHeaderLabels(["Trial Name", "Type", "Status", "Inherited Values"])
        self._trials_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._trials_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._trials_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._trials_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._trials_table.setAlternatingRowColors(True)
        self._trials_table.setSelectionMode(QTableWidget.NoSelection)
        self._trials_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._trials_table.setFixedHeight(180)
        t_vbox.addWidget(self._trials_table)

        trials_card.add_layout(t_vbox)
        self._main_layout.addWidget(trials_card)

        # ── 6. Action and Status Bar ────────────────────────────────────
        action_layout = QHBoxLayout()
        action_layout.setSpacing(SPACE_MD)

        self._status_label = QLabel("Ready. Select a session to view measurements.")
        self._status_label.setObjectName("pageHeaderSub")
        self._status_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        self._status_label.setWordWrap(True)
        action_layout.addWidget(self._status_label, 1)

        self._fetch_btn = QPushButton(" Fetch from QTM")
        self._fetch_btn.setObjectName("secondaryButton")
        self._fetch_btn.setCursor(Qt.PointingHandCursor)
        self._fetch_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_MEDIUM))
        self._fetch_btn.setToolTip("Fetch active measurement/session values from QTM REST API")
        self._fetch_btn.clicked.connect(self._fetch_from_qtm)
        action_layout.addWidget(self._fetch_btn)

        self._save_btn = QPushButton(" Save to Session & QTM")
        self._save_btn.setObjectName("primaryButton")
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        self._save_btn.setToolTip("Persist all measurements to session.xml, propagate to all trials, and update QTM")
        self._save_btn.clicked.connect(self._save_all_to_session_and_qtm)
        action_layout.addWidget(self._save_btn)

        self._main_layout.addLayout(action_layout)
        self._main_layout.addStretch(1)

    # ═══════════════════════════════════════════════════════════════════
    #  Helper Widget Builders
    # ═══════════════════════════════════════════════════════════════════

    def _create_field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("fieldLabel")
        lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_MEDIUM))
        return lbl

    def _style_combo(self, combo: QComboBox) -> None:
        combo.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        combo.setFixedHeight(32)

    # ═══════════════════════════════════════════════════════════════════
    #  Session Loading & Population
    # ═══════════════════════════════════════════════════════════════════

    def clear_session(self) -> None:
        """Clear all input fields and reset state."""
        self._is_populating = True
        self._session_path = None
        self._session_dir = None
        self._dirty_fields.clear()
        self._session_path_edit.setText("")
        self._patient_name.setText("")
        self._patient_id.setText("")
        self._sex.setCurrentIndex(0)
        self._dob_day.setCurrentIndex(0)
        self._dob_month.setCurrentIndex(0)
        self._dob_year.setCurrentIndex(0)

        for widget in self._anthro_inputs.values():
            widget.setText("")

        self._trials_table.setRowCount(0)
        self._badge_patient.setText("Patient: —")
        self._badge_session.setText("Session: —")
        self._badge_trials.setText("Trials: 0")
        self._badge_sync.setText("● No Session Selected")
        self._badge_sync.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}px; color: {COLOR_MUTED};")
        self._status_label.setText("No session selected. Please browse and select a session folder.")
        self._save_btn.setEnabled(False)
        self._fetch_btn.setEnabled(False)
        self._reload_btn.setEnabled(False)
        self._is_populating = False

    def set_session(self, path: str | Path) -> bool:
        """
        Open and populate a session given a directory, session.xml, or trial file path.
        """
        resolved_xml = get_session_xml_path(Path(path))
        if not resolved_xml or not resolved_xml.is_file():
            self._status_label.setText(f"Error: Invalid session path: {path}")
            return False

        self._session_path = str(resolved_xml)
        self._session_dir = resolved_xml.parent
        self._session_path_edit.setText(str(self._session_dir))

        session_ctx = (os.path.normcase(str(self._session_dir.resolve())),)
        if session_ctx != self._anthro_context:
            self._anthro_sync.cancel()
            self._anthro_generation += 1
            self._anthro_context = session_ctx
            self._anthro_connected = False
            self._dirty_fields.clear()

        # Record file modification times
        self._last_external_mtime["xml"] = resolved_xml.stat().st_mtime
        qpr_file = self._session_dir / "data.qpr"
        if qpr_file.is_file():
            self._last_external_mtime["qpr"] = qpr_file.stat().st_mtime

        success = self._populate_from_session_xml(resolved_xml)
        if success:
            self._save_btn.setEnabled(True)
            self._fetch_btn.setEnabled(True)
            self._reload_btn.setEnabled(True)
            self._status_label.setText("✓ Session loaded. Measurements synchronized with session.xml and QTM.")
            self._badge_sync.setText("✓ Synced")
            self._badge_sync.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}px; font-weight: 600; color: {COLOR_NORMAL};")
            self.session_selected.emit(str(self._session_dir))
            # Also poll QTM instance to verify connection
            if self._anthro_sync.operation is None:
                self._anthro_sync.request(str(self._session_dir), self._anthro_generation)
        return success

    def _populate_from_session_xml(self, xml_path: Path) -> bool:
        """Parse session.xml and populate all GUI fields and trials table."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except Exception as e:
            logger.error("Failed to parse session.xml at %s: %s", xml_path, e)
            self._status_label.setText(f"Error reading session.xml: {e}")
            return False

        self._is_populating = True
        try:
            fields: Dict[str, str] = {}
            for f_elem in [root.find("Fields"), root.find(".//Session/Fields")]:
                if f_elem is not None:
                    for child in f_elem:
                        if child.text is not None and child.text.strip():
                            fields[child.tag] = child.text.strip()

            # Patient Fields (support aliases)
            name_val = fields.get("Name") or fields.get("First_name") or fields.get("First name") or ""
            id_val = fields.get("ID") or fields.get("Patient_ID") or fields.get("Patient ID") or ""
            self._patient_name.setText(name_val)
            self._patient_id.setText(id_val)

            sex_val = fields.get("Sex") or fields.get("Gender") or ""
            sex_idx = self._sex.findText(sex_val)
            if sex_idx >= 0:
                self._sex.setCurrentIndex(sex_idx)
            elif sex_val:
                self._sex.addItem(sex_val)
                self._sex.setCurrentIndex(self._sex.findText(sex_val))

            dob_val = fields.get("DOB") or fields.get("Date_of_birth") or fields.get("Date of birth") or ""
            if dob_val:
                self._set_dob_widgets(dob_val)

            # Anthropometric Fields (support aliases)
            for name, widget in self._anthro_inputs.items():
                val = fields.get(name)
                if not val and name == "InterAsisDistance":
                    val = fields.get("Inter-ASIS distance") or fields.get("InterAsis")
                elif not val and name == "BodyMass":
                    val = fields.get("Weight") or fields.get("Bodymass")
                elif not val and name == "LeftAsisTrocanterDistance":
                    val = fields.get("Left ASIS-trochanter distance")
                elif not val and name == "RightAsisTrocanterDistance":
                    val = fields.get("Right ASIS-trochanter distance")
                elif not val:
                    norm = name.lower().replace(" ", "").replace("_", "").replace("-", "")
                    for fk, fv in fields.items():
                        if fk.lower().replace(" ", "").replace("_", "").replace("-", "") == norm:
                            val = fv
                            break
                if val:
                    widget.setText(format_measurement(name, val))
                else:
                    widget.setText("")

            # Update Badges
            pat_display = f"{name_val} ({id_val})" if name_val or id_val else "Unknown"
            self._badge_patient.setText(f"Patient: {pat_display}")
            session_id = fields.get("Session_ID") or root.attrib.get("Filename") or root.attrib.get("Name") or self._session_dir.name
            self._badge_session.setText(f"Session: {session_id}")

            # Populate Trials Table
            self._populate_trials_table(root, fields)

            return True
        finally:
            self._is_populating = False

    def _set_dob_widgets(self, dob_str: str) -> None:
        """Parse YYYY-MM-DD or YYYY-Mon-DD and set comboboxes."""
        parts = dob_str.replace("/", "-").split("-")
        if len(parts) == 3:
            y, m, d = parts[0], parts[1], parts[2]
            # Year
            idx_y = self._dob_year.findText(y)
            if idx_y >= 0:
                self._dob_year.setCurrentIndex(idx_y)
            # Month
            if m.isdigit():
                m_int = int(m)
                if 1 <= m_int <= 12:
                    self._dob_month.setCurrentIndex(m_int - 1)
            else:
                idx_m = self._dob_month.findText(m[:3])
                if idx_m >= 0:
                    self._dob_month.setCurrentIndex(idx_m)
            # Day
            d_str = f"{int(d):02d}" if d.isdigit() else d
            idx_d = self._dob_day.findText(d_str)
            if idx_d >= 0:
                self._dob_day.setCurrentIndex(idx_d)

    def _get_dob_string(self) -> str:
        """Return YYYY-MM-DD string from DOB dropdowns."""
        day = self._dob_day.currentText().strip()
        month_txt = self._dob_month.currentText().strip()
        year = self._dob_year.currentText().strip()
        if not day or not month_txt or not year:
            return ""
        if month_txt in MONTH_NAMES:
            month_num = MONTH_NAMES.index(month_txt) + 1
            return f"{year}-{month_num:02d}-{day}"
        return ""

    def _populate_trials_table(self, root: ET.Element, session_fields: Dict[str, str]) -> None:
        """Find all dynamic and static measurements in session.xml or folder and list them."""
        self._trials_table.setRowCount(0)
        measurements = root.findall(".//Measurement")

        # Also detect any .qtm files in session_dir
        found_qtm_files = set()
        if self._session_dir and self._session_dir.is_dir():
            for f in self._session_dir.glob("*.qtm"):
                found_qtm_files.add(f.name)

        trials_data = []

        # From session.xml <Measurement>
        for m in measurements:
            m_type = m.attrib.get("Type", "Trial")
            m_fields = m.find("Fields")
            t_name = m.attrib.get("Filename") or ""
            if not t_name and m_fields is not None:
                t_name = m_fields.findtext("Filename") or m_fields.findtext("Name") or ""
            if not t_name:
                t_name = m.attrib.get("Name", "Unnamed Trial")
            if not t_name.endswith(".qtm"):
                t_name_qtm = f"{t_name}.qtm"
            else:
                t_name_qtm = t_name

            trials_data.append((t_name_qtm, m_type, "✓ Inherits Session Values"))
            found_qtm_files.discard(t_name_qtm)

        # Any extra .qtm files in folder
        for qtm_name in sorted(found_qtm_files):
            q_type = "Static" if "static" in qtm_name.lower() or "cal" in qtm_name.lower() else "Dynamic"
            trials_data.append((qtm_name, q_type, "✓ Inherits Session Values"))

        self._badge_trials.setText(f"Trials: {len(trials_data)}")
        self._trials_table.setRowCount(len(trials_data))

        for row, (name, trial_type, status_text) in enumerate(trials_data):
            # Name
            item_name = QTableWidgetItem(name)
            item_name.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_CAPTION))
            self._trials_table.setItem(row, 0, item_name)

            # Type
            item_type = QTableWidgetItem(trial_type)
            item_type.setTextAlignment(Qt.AlignCenter)
            item_type.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, FONT_WEIGHT_SEMIBOLD))
            self._trials_table.setItem(row, 1, item_type)

            # Status
            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignCenter)
            item_status.setForeground(QColor(COLOR_NORMAL))
            item_status.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, FONT_WEIGHT_BOLD))
            self._trials_table.setItem(row, 2, item_status)

            # Inherited Values Summary
            mass = session_fields.get("BodyMass", "")
            ht = session_fields.get("Height", "")
            summary = f"Mass: {format_measurement('BodyMass', mass) if mass else '—'} kg | Ht: {format_measurement('Height', ht) if ht else '—'} m"
            item_summary = QTableWidgetItem(summary)
            item_summary.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_CAPTION))
            item_summary.setForeground(QColor(COLOR_MUTED))
            self._trials_table.setItem(row, 3, item_summary)

    def _update_badges(self) -> None:
        """Refresh badge colors according to theme."""
        if hasattr(self, "_badge_sync"):
            text = self._badge_sync.text()
            color = COLOR_NORMAL if "Synced" in text else COLOR_MUTED
            self._badge_sync.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}px; font-weight: 600; color: {color};")

    # ═══════════════════════════════════════════════════════════════════
    #  User Actions & File Browsing
    # ═══════════════════════════════════════════════════════════════════

    def _browse_session(self) -> None:
        """Browse and select a session folder or session.xml file."""
        start_dir = self._data_root if self._data_root and os.path.isdir(self._data_root) else (
            str(self._session_dir.parent) if self._session_dir and self._session_dir.exists() else ""
        )
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Session Folder",
            start_dir,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        if folder:
            self.set_session(folder)

    def _on_session_path_entered(self) -> None:
        """Handle direct path entry in line edit."""
        text = self._session_path_edit.text().strip()
        if text:
            self.set_session(text)

    def _reload_current_session(self) -> None:
        """Reload the currently open session from disk and QTM."""
        if self._session_path:
            self.set_session(self._session_path)

    # ═══════════════════════════════════════════════════════════════════
    #  Field Editing & Synchronization Handlers
    # ═══════════════════════════════════════════════════════════════════

    def _on_field_edited(self, name: str) -> None:
        """Mark field dirty when typed and indicate editing status without altering keystrokes."""
        if self._is_populating:
            return
        self._dirty_fields.add(name)
        self._field_revisions[name] = self._field_revisions.get(name, 0) + 1
        self._status_label.setText(f"Editing {name}… (press Enter, Tab, or Save to sync)")
        self._badge_sync.setText("● Editing…")
        self._badge_sync.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}px; font-weight: 600; color: {COLOR_WARNING};")
        self._auto_sync_timer.stop()

    def _on_patient_combo_choice(self, name: str) -> None:
        """Trigger sync immediately when sex or dob dropdown changes."""
        if self._is_populating:
            return
        self._dirty_fields.add(name)
        self._field_revisions[name] = self._field_revisions.get(name, 0) + 1
        self._sync_single_field(name, force_format=True)

    def _on_field_commit(self, name: str) -> None:
        """Commit edit when enter is pressed or focus leaves field."""
        if self._is_populating:
            return
        self._auto_sync_timer.stop()
        val = self._get_field_value(name)
        self._sync_fields({name: val}, force_format=True)

    def _on_auto_sync_timer_timeout(self) -> None:
        """Auto-save dirty fields after typing debounce, never disturbing actively focused fields."""
        if self._is_populating or not self._dirty_fields:
            return
        fields_to_sync = {}
        for n in list(self._dirty_fields):
            widget = self._anthro_inputs.get(n) or (self._patient_name if n == "Name" else (self._patient_id if n == "ID" else None))
            if widget is not None and widget.hasFocus():
                continue  # Skip field currently being typed into!
            val = self._get_field_value(n)
            if val:
                fields_to_sync[n] = val
        if fields_to_sync:
            self._sync_fields(fields_to_sync, force_format=True)

    def _get_field_value(self, name: str) -> str:
        """Extract clean current value of a field from GUI widget."""
        if name in self._anthro_inputs:
            return self._anthro_inputs[name].text().strip()
        if name == "Name":
            return self._patient_name.text().strip()
        if name == "ID":
            return self._patient_id.text().strip()
        if name == "Sex":
            return self._sex.currentText().strip()
        if name == "DOB":
            return self._get_dob_string()
        return ""

    def _sync_single_field(self, name: str, force_format: bool = False) -> None:
        val = self._get_field_value(name)
        self._sync_fields({name: val}, force_format=force_format)

    def _sync_fields(self, fields_to_sync: Dict[str, Any], force_format: bool = False) -> None:
        """
        Validate and push fields to session.xml (root and all trials) and QTM REST API.
        Only formats field text on commit or when the user is not actively typing inside it.
        """
        if self._is_populating or not self._session_path:
            return

        valid: Dict[str, Any] = {}
        for name, val in fields_to_sync.items():
            if val is None or str(val).strip() == "":
                continue
            try:
                if name in ANTHROPOMETRIC_FIELDS:
                    validate_parameter(name, val)
                elif name in PATIENT_FIELDS:
                    validate_patient_field(name, val)
                valid[name] = val
            except ValueError as e:
                logger.debug("Validation error on %s (%s): %s", name, val, e)
                continue

        if not valid:
            return

        # 1. Update session.xml (root Session and all child Measurement blocks!)
        update_session_xml(self._session_path, valid)

        # 2. Update QTM REST API asynchronously
        session_dir = Path(self._session_path).resolve().parent
        self._anthro_sync.write_async(session_dir, valid, self._anthro_generation)

        # 3. Clean up dirty state and format fields
        for name in valid:
            self._dirty_fields.discard(name)
            if name in self._anthro_inputs:
                widget = self._anthro_inputs[name]
                # Only re-format if explicitly committed or if user is not actively typing in it
                if force_format or not widget.hasFocus():
                    formatted = format_measurement(name, valid[name])
                    if widget.text().strip() != formatted:
                        with QSignalBlocker(widget):
                            widget.setText(formatted)

        synced_names = ", ".join(sorted(valid.keys()))
        self._status_label.setText(f"✓ Updated {synced_names} in session.xml & QTM.")
        self._badge_sync.setText("✓ Synced")
        self._badge_sync.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}px; font-weight: 600; color: {COLOR_NORMAL};")

        # Refresh trials table display
        if self._session_path and Path(self._session_path).is_file():
            try:
                tree = ET.parse(self._session_path)
                root = tree.getroot()
                fields_elem = root.find("Fields")
                current_fields = {c.tag: c.text for c in fields_elem} if fields_elem is not None else {}
                self._populate_trials_table(root, current_fields)
            except Exception:
                pass

        self.measurements_updated.emit(valid)

    def _save_all_to_session_and_qtm(self) -> None:
        """Explicit save of all patient and anthropometric parameters."""
        if not self._session_path:
            return
        all_fields = {}
        for name in list(self._anthro_inputs.keys()) + ["Name", "ID", "Sex", "DOB"]:
            val = self._get_field_value(name)
            if val:
                all_fields[name] = val
        self._sync_fields(all_fields)

    def _fetch_from_qtm(self) -> None:
        """Fetch latest session values directly from QTM."""
        if not self._session_path or not self._session_dir:
            return
        if self._anthro_sync.operation is not None:
            self._status_label.setText("A QTM operation is in progress. Please wait.")
            return

        self._status_label.setText("Fetching measurements from QTM…")
        self._save_btn.setEnabled(False)
        self._fetch_btn.setEnabled(False)
        self._anthro_sync.request(str(self._session_dir), self._anthro_generation)

    # ═══════════════════════════════════════════════════════════════════
    #  Bi-directional Sync from External Sources (QTM / Disk)
    # ═══════════════════════════════════════════════════════════════════

    def _poll_external_sync(self) -> None:
        """
        Poll disk & QTM: detect external changes in session.xml or data.qpr
        and update GUI inputs automatically.
        """
        if self._is_populating or not self._session_path:
            return
        xml_file = Path(self._session_path)
        if not xml_file.is_file():
            return

        session_dir = xml_file.parent
        qpr_file = session_dir / "data.qpr"

        xml_mtime = xml_file.stat().st_mtime if xml_file.is_file() else 0.0
        qpr_mtime = qpr_file.stat().st_mtime if qpr_file.is_file() else 0.0

        last_xml = self._last_external_mtime.get("xml", 0.0)
        last_qpr = self._last_external_mtime.get("qpr", 0.0)

        if "xml" not in self._last_external_mtime:
            self._last_external_mtime["xml"] = xml_mtime
            self._last_external_mtime["qpr"] = qpr_mtime
            return

        changed = False
        if xml_mtime > last_xml:
            self._last_external_mtime["xml"] = xml_mtime
            changed = True
        if qpr_file.is_file() and qpr_mtime > (last_qpr or 0.0):
            self._last_external_mtime["qpr"] = qpr_mtime
            changed = True

        if changed:
            self._sync_from_external_sources()

        # If QTM is connected and idle, query QTM for in-memory session changes
        if self._anthro_connected and self._anthro_sync.operation is None and not self._dirty_fields and self._session_dir:
            self._anthro_sync.request(str(self._session_dir), self._anthro_generation)

    def _sync_from_external_sources(self) -> None:
        """Read external modifications and update GUI non-dirty fields."""
        if self._is_populating or not self._session_path:
            return
        try:
            tree = ET.parse(self._session_path)
            root = tree.getroot()
            fields_elem = root.find("Fields")
            if fields_elem is None:
                return

            updated_fields = {}
            for child in fields_elem:
                if child.text is not None:
                    updated_fields[child.tag] = child.text.strip()

            # Update GUI for fields not being actively edited
            for name, val in updated_fields.items():
                if name in self._dirty_fields:
                    continue
                widget = self._anthro_inputs.get(name) or (self._patient_name if name == "Name" else (self._patient_id if name == "ID" else None))
                if widget is not None and widget.hasFocus():
                    continue
                current_gui_val = self._get_field_value(name)
                if not same_field_value(name, current_gui_val, val):
                    self._set_field_gui_value(name, val)

            # Ensure all Measurement blocks in session.xml remain synchronized with session fields
            update_session_xml(self._session_path, updated_fields)
            self._populate_trials_table(root, updated_fields)
            self._status_label.setText("✓ External QTM changes detected and synchronized with GUI.")
            self._badge_sync.setText("✓ Synced")
            self._badge_sync.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}px; font-weight: 600; color: {COLOR_NORMAL};")
        except Exception as e:
            logger.debug("External sync check error: %s", e)

    def _set_field_gui_value(self, name: str, value: Any) -> None:
        """Helper to set a field widget value cleanly without triggering edit signals or disturbing active edits."""
        if name in self._anthro_inputs:
            widget = self._anthro_inputs[name]
            if widget.hasFocus() or name in self._dirty_fields:
                return
            with QSignalBlocker(widget):
                widget.setText(format_measurement(name, value))
        elif name == "Name":
            if self._patient_name.hasFocus() or name in self._dirty_fields:
                return
            with QSignalBlocker(self._patient_name):
                self._patient_name.setText(str(value))
        elif name == "ID":
            if self._patient_id.hasFocus() or name in self._dirty_fields:
                return
            with QSignalBlocker(self._patient_id):
                self._patient_id.setText(str(value))
        elif name == "Sex":
            with QSignalBlocker(self._sex):
                idx = self._sex.findText(str(value))
                if idx >= 0:
                    self._sex.setCurrentIndex(idx)
        elif name == "DOB":
            self._set_dob_widgets(str(value))

    # ═══════════════════════════════════════════════════════════════════
    #  QTM Sync Callbacks
    # ═══════════════════════════════════════════════════════════════════

    def _on_anthro_sync_finished(self, result: dict) -> None:
        """Handle completion of background QTM read/request."""
        if result.get("generation") != self._anthro_generation:
            return
        self._anthro_sync.operation = None
        self._save_btn.setEnabled(bool(self._session_path))
        self._fetch_btn.setEnabled(bool(self._session_path))

        snapshot = result.get("snapshot")
        if snapshot is None:
            self._anthro_connected = False
            # If QTM not running, that's okay, local session.xml is used
            logger.debug("QTM snapshot not available: %s", result.get("diagnostics"))
            return

        self._anthro_connected = True
        qtm_values = snapshot.get("values", {})
        if qtm_values:
            fields_to_update = {}
            for name, val in qtm_values.items():
                if name in self._dirty_fields:
                    continue
                widget = self._anthro_inputs.get(name) or (self._patient_name if name == "Name" else (self._patient_id if name == "ID" else None))
                if widget is not None and widget.hasFocus():
                    continue
                current_gui_val = self._get_field_value(name)
                if not same_field_value(name, current_gui_val, val):
                    fields_to_update[name] = val
                self._set_field_gui_value(name, val)

            if fields_to_update and self._session_path:
                update_session_xml(self._session_path, fields_to_update)
                if self._session_dir:
                    self._anthro_sync.write_async(self._session_dir, fields_to_update, self._anthro_generation)
                try:
                    tree = ET.parse(self._session_path)
                    root = tree.getroot()
                    fields_elem = root.find("Fields")
                    current_fields = {c.tag: c.text for c in fields_elem} if fields_elem is not None else {}
                    self._populate_trials_table(root, current_fields)
                except Exception:
                    pass

            self._status_label.setText("✓ QTM parameters fetched and synchronized successfully.")
            self._badge_sync.setText("✓ Live QTM Synced")
            self._badge_sync.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}px; font-weight: 600; color: {COLOR_NORMAL};")

    def _on_anthro_write_finished(self, result: dict) -> None:
        """Handle completion of background QTM write."""
        if result.get("generation") != self._anthro_generation:
            return
        if result.get("success"):
            self._anthro_connected = True
            logger.info("QTM write confirmed for fields: %s", list(result.get("fields", {}).keys()))
        else:
            logger.warning("QTM write note: %s", result.get("error"))
