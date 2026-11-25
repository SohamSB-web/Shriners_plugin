# -*- coding: utf-8 -*-
"""
Dynamic Analysis GUI — Redesigned in PySide6 for Shriners Gait Analysis.

Provides a clean, data-oriented clinical workstation interface for dynamic gait trials:
- Patient & Session metadata card
- Modern selectable trial rows (TrialRowWidget) for Left/Right trials
- Processing options (Kinematics, Kinetics, EMG, Muscle Data, GDI, Foot Model)
- Compact, non-blocking real-time processing panel with per-trial status
- Seamless navigation to MAC Case Presentation once trials are processed.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal, QTimer, QFileSystemWatcher
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.models.data_models import ProcessingStatus
from app.services.event_service import (
    get_session_events_summary,
    load_trial_events,
    send_events_to_qtm,
    sync_qtm_events_to_session,
    trial_names_match,
)
from app.services.qtm_metadata_service import get_session_dynamic_trials
from app.services.pdf_report_service import CasePresentationPdfService
from app.services.processing_service import GaitProcessingService
from app.ui.dialogs.event_details_dialog import EventDetailsDialog
from app.ui.theme.design_tokens import (
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
    RADIUS_MD,
    RADIUS_SM,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
    LIGHT_PALETTE,
)
from app.ui.widgets.force_plate_dialog import ForcePlateConfigDialog
from app.ui.widgets.trial_row import TrialRowWidget

logger = logging.getLogger(__name__)


class DynamicAnalysisPage(QScrollArea):
    """
    Minimal, premium scientific dynamic trials processing workspace.
    """

    proceed_to_patients = Signal(str)      # session_path -> navigates to Patients & Sessions
    proceed_to_presentation = Signal(str)  # session_path (backward-compat)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setObjectName("dynamicAnalysisPage")

        self._session_path: str = ""
        self._patient_mrn: str = "MRN --"
        self._session_date: str = "--"
        self._trial_rows: Dict[str, TrialRowWidget] = {}
        self._trial_metadata: Dict[str, dict] = {}
        self._force_plate_configs: Dict[str, dict] = {}
        self._processing_queue: List[Tuple[str, str]] = []  # List of (task_type, filename)
        self._current_task_type: str = "dynamic"
        self._current_processing_file: str = ""
        self._analysis_generation = 0
        self._processing_slots = []
        self._last_completion_message: str = ""
        self._processed_success_count: int = 0
        self._processed_error_count: int = 0
        self._failed_trials: List[str] = []

        # Processing service
        self._service = GaitProcessingService()


        # Real-time QTM timeline event synchronization & file watching
        self._is_syncing_events: bool = False
        self._fs_watcher = QFileSystemWatcher(self)
        self._fs_watcher.fileChanged.connect(self._on_fs_file_changed)
        self._fs_watcher.directoryChanged.connect(self._on_fs_directory_changed)

        self._qtm_sync_timer = QTimer(self)
        self._qtm_sync_timer.setInterval(3000)  # poll every 3 seconds — QTM sync doesn't need sub-second latency
        self._qtm_sync_timer.timeout.connect(self._poll_qtm_events_sync)

        self._init_ui()
        from app.ui.widgets.smooth_scroll import apply_smooth_scroll
        self._smooth_scroll = apply_smooth_scroll(self)

    @staticmethod
    def _create_tinted_icon(svg_path: Path, stroke_color: str, size: int = 16) -> QIcon:
        try:
            import re
            from PySide6.QtSvg import QSvgRenderer
            from PySide6.QtCore import QByteArray, Qt
            from PySide6.QtGui import QPixmap, QPainter

            raw = svg_path.read_text(encoding="utf-8")
            recolored = re.sub(r'stroke="[^"]*"', f'stroke="{stroke_color}"', raw)
            recolored = re.sub(r'fill="(?!none)[^"]*"', f'fill="{stroke_color}"', recolored)
            renderer = QSvgRenderer(QByteArray(recolored.encode("utf-8")))
            if not renderer.isValid():
                return QIcon(str(svg_path))
            pix = QPixmap(size * 2, size * 2)
            pix.fill(Qt.transparent)
            painter = QPainter(pix)
            renderer.render(painter)
            painter.end()
            pix.setDevicePixelRatio(2.0)
            return QIcon(pix)
        except Exception:
            return QIcon(str(svg_path))

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        """Update icons, badges, and rows for dark/light theme."""
        self._is_dark = dark
        pal = palette or (DARK_PALETTE if dark else LIGHT_PALETTE)
        icon_color = pal.accent if dark else pal.primary
        icons_dir = Path(__file__).resolve().parent.parent.parent.parent / "resources" / "icons"

        fp_icon_path = icons_dir / "force_plate.svg"
        if fp_icon_path.is_file():
            self._adj_fp_btn.setIcon(self._create_tinted_icon(fp_icon_path, icon_color, 16))

        ev_icon_path = icons_dir / "auto_event.svg"
        if ev_icon_path.is_file():
            self._auto_event_btn.setIcon(self._create_tinted_icon(ev_icon_path, icon_color, 16))
            self._auto_label_action_btn.setIcon(self._create_tinted_icon(ev_icon_path, icon_color, 16))

        refresh_icon_path = icons_dir / "refresh.svg"
        if hasattr(self, "_sync_qtm_btn") and refresh_icon_path.is_file():
            self._sync_qtm_btn.setIcon(self._create_tinted_icon(refresh_icon_path, icon_color, 16))

        # Propagate to all dynamic trial rows
        for row in getattr(self, "_trial_rows", {}).values():
            if hasattr(row, "apply_theme"):
                row.apply_theme(pal, dark)

        # Style standard pipeline modules for light/dark
        text_col = pal.text_secondary
        ind_bg = pal.primary
        ind_border = pal.accent if dark else pal.primary
        cb_style = (
            f"QCheckBox:disabled {{ color: {text_col}; }} "
            f"QCheckBox::indicator:disabled {{ background-color: {ind_bg}; border: 1.5px solid {ind_border}; border-radius: 3px; }}"
        )
        for cb in getattr(self, "_readonly_cbs", []):
            cb.setStyleSheet(cb_style)

        if hasattr(self, "_modules_sep"):
            self._modules_sep.setStyleSheet(
                f"background-color: {pal.border}; border: none; min-height: 1px; max-height: 1px; margin-top: 4px; margin-bottom: 4px;"
            )
        if hasattr(self, "_modules_title"):
            self._modules_title.setStyleSheet(
                f"color: {pal.text_muted}; text-transform: uppercase; letter-spacing: 0.5px;"
            )
        if hasattr(self, "_modules_note"):
            self._modules_note.setStyleSheet(
                f"color: {pal.text_muted}; font-style: italic;"
            )

    def _init_ui(self) -> None:
        container = QWidget()
        self.setWidget(container)

        self._main_layout = QVBoxLayout(container)
        self._main_layout.setContentsMargins(SPACE_XL * 2, SPACE_XL, SPACE_XL * 2, SPACE_XL * 2)
        self._main_layout.setSpacing(SPACE_LG)

        # ── Header ─────────────────────────────────────────────────────────
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        header_title = QLabel("DYNAMIC ANALYSIS")
        header_title.setObjectName("pageHeaderTitle")
        header_title.setFont(QFont(FONT_FAMILY, FONT_SIZE_H2, QFont.Bold))
        header_layout.addWidget(header_title)

        header_sub = QLabel("Compute joint kinematics, kinetics, EMG, muscle dynamics, and GDI across walking trials")
        header_sub.setObjectName("pageHeaderSub")
        header_sub.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        header_layout.addWidget(header_sub)

        self._main_layout.addLayout(header_layout)

        # ── Session Info Card ───────────────────────────────────────────────
        session_box = QFrame()
        session_box.setObjectName("card")
        session_layout = QHBoxLayout(session_box)
        session_layout.setSpacing(SPACE_XL)

        # Patient Info
        p_layout = QVBoxLayout()
        p_title = QLabel("PATIENT")
        p_title.setObjectName("cardSectionTitle")
        p_title.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        p_layout.addWidget(p_title)

        self._mrn_label = QLabel("MRN 002 (Shriners_test)")
        self._mrn_label.setObjectName("valueLabel")
        self._mrn_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_SEMIBOLD))
        p_layout.addWidget(self._mrn_label)
        session_layout.addLayout(p_layout)

        # Date Info
        d_layout = QVBoxLayout()
        d_title = QLabel("SESSION DATE")
        d_title.setObjectName("cardSectionTitle")
        d_title.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        d_layout.addWidget(d_title)

        self._date_label = QLabel("2025-02-21 (Session 0003)")
        self._date_label.setObjectName("valueLabel")
        self._date_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        d_layout.addWidget(self._date_label)
        session_layout.addLayout(d_layout)

        session_layout.addStretch()

        # Calibration status pill
        self._calib_status_label = QLabel("● Static Calibration Ready")
        self._calib_status_label.setObjectName("badge")
        self._calib_status_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, FONT_WEIGHT_MEDIUM))
        session_layout.addWidget(self._calib_status_label)

        self._main_layout.addWidget(session_box)

        # ── Dynamic Trials List ─────────────────────────────────────────────
        trials_section_header = QHBoxLayout()
        t_label = QLabel("DYNAMIC TRIALS")
        t_label.setObjectName("cardSectionTitle")
        t_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        trials_section_header.addWidget(t_label)

        # Force Plate Adjust button
        self._adj_fp_btn = QPushButton("  Adjust Force Plates…")
        self._adj_fp_btn.setObjectName("secondaryButton")
        fp_icon_path = Path(__file__).resolve().parent.parent.parent.parent / "resources" / "icons" / "force_plate.svg"
        if fp_icon_path.is_file():
            self._adj_fp_btn.setIcon(QIcon(str(fp_icon_path)))
        self._adj_fp_btn.setCursor(Qt.PointingHandCursor)
        self._adj_fp_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        self._adj_fp_btn.clicked.connect(self._on_open_force_plate_dialog)
        trials_section_header.addWidget(self._adj_fp_btn)

        self._fp_badge = QLabel("Force Plate: Ready (FP0)")
        self._fp_badge.setObjectName("badge")
        self._fp_badge.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION))
        trials_section_header.addWidget(self._fp_badge)

        # Auto Event Labeling Quick Button
        self._auto_event_btn = QPushButton("  Auto-Label Events…")
        self._auto_event_btn.setObjectName("secondaryButton")
        ev_icon_path = Path(__file__).resolve().parent.parent.parent.parent / "resources" / "icons" / "auto_event.svg"
        if ev_icon_path.is_file():
            self._auto_event_btn.setIcon(QIcon(str(ev_icon_path)))
        self._auto_event_btn.setCursor(Qt.PointingHandCursor)
        self._auto_event_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        self._auto_event_btn.setToolTip("Auto-detect and label gait events (Heel Strikes & Toe Offs) on selected dynamic trials")
        self._auto_event_btn.clicked.connect(self._on_auto_label_clicked)
        trials_section_header.addWidget(self._auto_event_btn)

        # Sync from QTM Button
        self._sync_qtm_btn = QPushButton("  Sync from QTM")
        self._sync_qtm_btn.setObjectName("secondaryButton")
        refresh_icon_path = Path(__file__).resolve().parent.parent.parent.parent / "resources" / "icons" / "refresh.svg"
        if refresh_icon_path.is_file():
            self._sync_qtm_btn.setIcon(QIcon(str(refresh_icon_path)))
        self._sync_qtm_btn.setCursor(Qt.PointingHandCursor)
        self._sync_qtm_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        self._sync_qtm_btn.setToolTip("Pull latest gait events directly from the live QTM timeline for the active trial")
        self._sync_qtm_btn.clicked.connect(self._on_sync_from_qtm_clicked)
        trials_section_header.addWidget(self._sync_qtm_btn)

        # Events summary badge
        self._events_badge = QLabel("Events: Ready")
        self._events_badge.setObjectName("badge")
        self._events_badge.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION))
        trials_section_header.addWidget(self._events_badge)

        trials_section_header.addStretch()

        # Select all / Deselect all
        sel_all_btn = QPushButton("Select All")
        sel_all_btn.setObjectName("ghostButton")
        sel_all_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL))
        sel_all_btn.clicked.connect(self._select_all_trials)
        trials_section_header.addWidget(sel_all_btn)

        desel_btn = QPushButton("Deselect")
        desel_btn.setObjectName("ghostButton")
        desel_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL))
        desel_btn.clicked.connect(self._deselect_all_trials)
        trials_section_header.addWidget(desel_btn)

        self._main_layout.addLayout(trials_section_header)

        # Trial rows container
        self._trials_container = QVBoxLayout()
        self._trials_container.setSpacing(SPACE_SM)
        self._main_layout.addLayout(self._trials_container)

        # ── Processing Options ──────────────────────────────────────────────
        options_box = QFrame()
        options_box.setObjectName("card")
        opt_layout = QVBoxLayout(options_box)
        opt_layout.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        opt_layout.setSpacing(SPACE_SM)

        # 1. Active Options Header & Toggles
        active_title = QLabel("PROCESSING OPTIONS")
        active_title.setObjectName("cardSectionTitle")
        active_title.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        opt_layout.addWidget(active_title)

        active_toggles_layout = QVBoxLayout()
        active_toggles_layout.setSpacing(8)

        self._opt_auto_events = QCheckBox("Auto-detect gait events (HS / TO) before processing")
        self._opt_auto_events.setChecked(True)
        self._opt_auto_events.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Medium))
        self._opt_auto_events.setToolTip("Automatically run automated heel strike / toe off event detection on dynamic trials.")
        active_toggles_layout.addWidget(self._opt_auto_events)

        self._opt_interactive_fp = QCheckBox("Prompt Force Plate Setup during processing")
        self._opt_interactive_fp.setChecked(False)
        self._opt_interactive_fp.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        self._opt_interactive_fp.setToolTip("Open interactive ForcePlate GUI for manual plate assignment verification.")
        active_toggles_layout.addWidget(self._opt_interactive_fp)

        opt_layout.addLayout(active_toggles_layout)

        # Subtle separator line
        self._modules_sep = QFrame()
        self._modules_sep.setFrameShape(QFrame.HLine)
        self._modules_sep.setStyleSheet("background-color: #E4E4E7; border: none; min-height: 1px; max-height: 1px; margin-top: 4px; margin-bottom: 4px;")
        opt_layout.addWidget(self._modules_sep)

        # 2. Standard Pipeline Modules (Read-only / Checked)
        modules_header = QHBoxLayout()
        self._modules_title = QLabel("Standard Pipeline Modules (Included in GCD)")
        self._modules_title.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, QFont.Bold))
        self._modules_title.setStyleSheet("color: #71717A; text-transform: uppercase; letter-spacing: 0.5px;")
        modules_header.addWidget(self._modules_title)

        self._modules_note = QLabel("— automatically produced by Shriners model")
        self._modules_note.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION))
        self._modules_note.setStyleSheet("color: #A1A1AA; font-style: italic;")
        modules_header.addWidget(self._modules_note)
        modules_header.addStretch()
        opt_layout.addLayout(modules_header)

        modules_grid = QGridLayout()
        modules_grid.setSpacing(SPACE_SM)

        self._opt_kinematics = QCheckBox("Joint Kinematics (Angles)")
        self._opt_kinetics = QCheckBox("Joint Kinetics (Moments && Powers)")
        self._opt_emg = QCheckBox("EMG Processing && Bandpass")
        self._opt_muscle = QCheckBox("Muscle Length && Velocity")
        self._opt_gdi = QCheckBox("Gait Deviation Index (GDI)")
        self._opt_foot = QCheckBox("Foot Model Multi-Segment")

        self._readonly_cbs = [
            self._opt_kinematics, self._opt_kinetics, self._opt_emg,
            self._opt_muscle, self._opt_gdi, self._opt_foot
        ]
        for cb in self._readonly_cbs:
            cb.setChecked(True)
            cb.setEnabled(False)
            cb.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
            cb.setToolTip("Included automatically in standard GCD output.")

        modules_grid.addWidget(self._opt_kinematics, 0, 0)
        modules_grid.addWidget(self._opt_kinetics, 0, 1)
        modules_grid.addWidget(self._opt_emg, 0, 2)
        modules_grid.addWidget(self._opt_muscle, 1, 0)
        modules_grid.addWidget(self._opt_gdi, 1, 1)
        modules_grid.addWidget(self._opt_foot, 1, 2)

        opt_layout.addLayout(modules_grid)
        self._main_layout.addWidget(options_box)

        # ── Compact Live Processing Panel ───────────────────────────────────
        self._proc_panel = QFrame()
        self._proc_panel.setObjectName("card")
        self._proc_panel.setVisible(False)
        proc_layout = QVBoxLayout(self._proc_panel)
        proc_layout.setSpacing(SPACE_SM)

        p_row = QHBoxLayout()
        self._proc_title = QLabel("Processing Dynamic Trials...")
        self._proc_title.setObjectName("cardSectionTitle")
        self._proc_title.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_SEMIBOLD))
        p_row.addWidget(self._proc_title)

        p_row.addStretch()

        self._proc_cancel_btn = QPushButton("Cancel")
        self._proc_cancel_btn.setObjectName("ghostButton")
        self._proc_cancel_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL))
        self._proc_cancel_btn.clicked.connect(self._on_cancel_processing)
        p_row.addWidget(self._proc_cancel_btn)
        proc_layout.addLayout(p_row)

        self._proc_bar = QProgressBar()
        self._proc_bar.setRange(0, 100)
        self._proc_bar.setValue(0)
        self._proc_bar.setFixedHeight(6)
        self._proc_bar.setTextVisible(False)
        proc_layout.addWidget(self._proc_bar)

        self._proc_status = QLabel("Initializing...")
        self._proc_status.setObjectName("fieldLabel")
        self._proc_status.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_CAPTION))
        proc_layout.addWidget(self._proc_status)

        self._main_layout.addWidget(self._proc_panel)

        # ── Bottom Action Row ───────────────────────────────────────────────
        action_row = QHBoxLayout()
        self._completion_label = QLabel("")
        self._completion_label.setObjectName("valueLabel")
        self._completion_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_MEDIUM))
        action_row.addWidget(self._completion_label)

        action_row.addStretch()

        self._auto_label_action_btn = QPushButton("Auto-Label Events")
        self._auto_label_action_btn.setObjectName("secondaryButton")
        ev_icon_path = Path(__file__).resolve().parent.parent.parent.parent / "resources" / "icons" / "auto_event.svg"
        if ev_icon_path.is_file():
            self._auto_label_action_btn.setIcon(QIcon(str(ev_icon_path)))
        self._auto_label_action_btn.setCursor(Qt.PointingHandCursor)
        self._auto_label_action_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        self._auto_label_action_btn.setToolTip("Auto-detect gait events for all selected dynamic trials")
        self._auto_label_action_btn.clicked.connect(self._on_auto_label_clicked)
        action_row.addWidget(self._auto_label_action_btn)

        self._process_btn = QPushButton("Process Selected Trials")
        self._process_btn.setObjectName("primaryButton")
        self._process_btn.setCursor(Qt.PointingHandCursor)
        self._process_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        self._process_btn.clicked.connect(self._on_process_clicked)
        action_row.addWidget(self._process_btn)

        self._view_pres_btn = QPushButton("Proceed to Patients && Sessions →")
        self._view_pres_btn.setObjectName("primaryButton")
        self._view_pres_btn.setCursor(Qt.PointingHandCursor)
        self._view_pres_btn.setVisible(False)
        self._view_pres_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        self._view_pres_btn.clicked.connect(self._on_view_presentation)
        action_row.addWidget(self._view_pres_btn)

        self._export_pdf_btn = QPushButton("Export Case Presentation PDF")
        self._export_pdf_btn.setObjectName("secondaryButton")
        self._export_pdf_btn.setCursor(Qt.PointingHandCursor)
        self._export_pdf_btn.setVisible(False)
        self._export_pdf_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        self._export_pdf_btn.clicked.connect(self._on_export_pdf_clicked)
        action_row.addWidget(self._export_pdf_btn)

        self._main_layout.addLayout(action_row)
        self._main_layout.addStretch()

        # Load default demo session if available
        self.clear_session()

    # ═══════════════════════════════════════════════════════════════════
    #  Session & Trial Loading
    # ═══════════════════════════════════════════════════════════════════

    def _bind_processing_context(self):
        for signal, slot in self._processing_slots:
            signal.disconnect(slot)
        self._processing_slots = []
        for signal, handler in ((self._service.processing_started, self._on_trial_started),
                                (self._service.processing_progress, self._on_trial_progress),
                                (self._service.processing_finished, self._on_trial_finished),
                                (self._service.processing_error, self._on_trial_error)):
            slot = lambda value, g=self._analysis_generation, h=handler: h(value) if g == self._analysis_generation else None
            signal.connect(slot)
            self._processing_slots.append((signal, slot))

    def _schedule(self, delay, callback):
        generation = self._analysis_generation
        QTimer.singleShot(delay, lambda: callback() if generation == self._analysis_generation else None)

    def clear_session(self):
        self._analysis_generation += 1
        self._service.invalidate()
        self._bind_processing_context()
        self._qtm_sync_timer.stop()
        paths = self._fs_watcher.files() + self._fs_watcher.directories()
        if paths:
            self._fs_watcher.removePaths(paths)
        for row in self._trial_rows.values():
            self._trials_container.removeWidget(row)
            row.setParent(None)
            row.deleteLater()
        self._trial_rows.clear()
        self._trial_metadata.clear()
        self._force_plate_configs.clear()
        self._processing_queue.clear()
        self._current_processing_file = self._session_path = ""
        self._current_task_type = "dynamic"
        self._patient_mrn = self._session_date = self._last_completion_message = ""
        self._processed_success_count = self._processed_error_count = 0
        self._failed_trials.clear()
        self._mrn_label.setText("Select a patient and session in Patients & Sessions to begin.")
        self._date_label.clear()
        self._calib_status_label.setText("No static calibration loaded")
        self._fp_badge.setText("Force Plate: —")
        self._events_badge.setText("Events: —")
        self._proc_panel.hide()
        self._proc_bar.setValue(0)
        self._proc_status.clear()
        self._proc_title.setText("Processing Dynamic Trials...")
        self._completion_label.clear()
        self._view_pres_btn.hide()
        self._export_pdf_btn.hide()
        for button in (self._process_btn, self._auto_label_action_btn, self._auto_event_btn,
                       self._sync_qtm_btn, self._adj_fp_btn):
            button.setEnabled(False)


    def _get_session_dir(self) -> Path:
        if not self._session_path:
            return Path(".")
        p = Path(self._session_path).resolve()
        return p if p.is_dir() else p.parent

    def load_session(self, session_xml_path: str) -> None:
        """Load session and populate dynamic trials.

        All heavy I/O (OLE2/C3D parsing, forceplate detection, SQLite event
        reads) is done in a background thread so the UI stays responsive.
        """
        context = str(Path(session_xml_path).resolve())
        if self._session_path and os.path.normcase(self._session_path) == os.path.normcase(context):
            return
        self.clear_session()
        self._session_path = context
        for button in (self._process_btn, self._auto_label_action_btn, self._auto_event_btn,
                       self._sync_qtm_btn, self._adj_fp_btn):
            button.setEnabled(True)
        ready, _ = self._is_static_calibration_ready()
        self._calib_status_label.setText("● Static Calibration Ready" if ready else "Static calibration required")
        session_dir = self._get_session_dir()

        self._setup_fs_watcher(session_dir)

        parent_dir = session_dir.parent.name
        self._patient_mrn = f"MRN {parent_dir}"
        self._session_date = session_dir.name
        self._mrn_label.setText(self._patient_mrn)
        self._date_label.setText(self._session_date)

        # Show a lightweight placeholder while the background worker loads data
        self._mrn_label.setText(f"{self._patient_mrn}  —  Loading trials…")
        self._events_badge.setText("Events: loading…")

        # ── Background worker: all disk I/O happens off the main thread ──────
        from PySide6.QtCore import QRunnable, QThreadPool, QObject, Signal
        from app.services.session_organizer import find_gcd_file, find_all_gcd_files

        generation = self._analysis_generation

        class _Signals(QObject):
            done = Signal(object)  # payload dict

        class _Loader(QRunnable):
            def __init__(self, sdir, gen):
                super().__init__()
                self._sdir = sdir
                self._gen = gen
                self.signals = _Signals()

            def run(self):
                try:
                    trials_info = get_session_dynamic_trials(self._sdir)
                    enriched = []
                    for t in trials_info:
                        fname = t["filename"]
                        stem  = t["stem"]
                        gcd   = find_gcd_file(self._sdir, stem)
                        ev    = load_trial_events(self._sdir, fname)
                        enriched.append({**t, "_gcd_exists": gcd is not None and gcd.is_file(),
                                         "_ev_info": ev})
                    gcd_files = find_all_gcd_files(self._sdir)
                    payload = {"generation": self._gen, "trials": enriched,
                               "has_gcds": bool(gcd_files), "error": None}
                except Exception as exc:
                    payload = {"generation": self._gen, "trials": [], "has_gcds": False,
                               "error": str(exc)}
                try:
                    self.signals.done.emit(payload)
                except RuntimeError:
                    pass  # widget was destroyed before worker finished

        loader = _Loader(session_dir, generation)
        loader.signals.done.connect(self._on_session_loaded)
        QThreadPool.globalInstance().start(loader)

    def _on_session_loaded(self, payload: dict) -> None:
        """Called on the main thread when the background session loader finishes."""
        if payload["generation"] != self._analysis_generation:
            return  # stale load — user already navigated away

        self._mrn_label.setText(self._patient_mrn)  # restore clean label

        if payload["error"]:
            logger.error("Session load failed: %s", payload["error"])
            self._events_badge.setText("Events: —")
            return

        session_dir = self._get_session_dir()
        dark = getattr(self, "_is_dark", False)

        for i, t in enumerate(payload["trials"]):
            fname  = t["filename"]
            strike = t.get("comment", "")
            status = "COMPLETE" if t["_gcd_exists"] else "READY"
            ev_info = t["_ev_info"]

            row = TrialRowWidget(
                trial_id=f"#{i+1}",
                name=fname,
                metadata=t.get("metadata_str", ""),
                status=status,
                selected=(i == 0),
                strike=strike,
            )
            row.set_events_info(ev_info)
            if ev_info and ev_info.get("total_events", 0) > 0 and status == "READY":
                row.set_status("EVENTS LABELED")

            row.view_events_clicked.connect(self._on_view_trial_events)
            row.auto_label_clicked.connect(self._on_single_trial_auto_label)
            row.push_to_qtm_clicked.connect(self._on_push_trial_events_to_qtm)
            row.pull_from_qtm_clicked.connect(self._on_single_trial_pull_from_qtm)
            row.apply_theme(dark=dark)

            self._trials_container.addWidget(row)
            self._trial_rows[fname] = row
            self._trial_metadata[fname] = t

            c_lower = strike.lower()
            if "right" in c_lower:
                self._force_plate_configs[fname] = {"left_plate": "0", "right_plate": "FP0"}
            elif "left" in c_lower:
                self._force_plate_configs[fname] = {"left_plate": "FP0", "right_plate": "0"}
            elif "bad" in c_lower or "no" in c_lower:
                self._force_plate_configs[fname] = {"left_plate": "0", "right_plate": "0"}

        self._update_events_summary_badge()
        logger.info("Loaded %d dynamic trials for session: %s", len(self._trial_rows), session_dir)

        if payload["has_gcds"]:
            self._view_pres_btn.setVisible(True)
            self._export_pdf_btn.setVisible(True)

        # Start live background QTM sync timer and trigger initial check
        if hasattr(self, "_qtm_sync_timer"):
            self._qtm_sync_timer.start(3000)
            self._schedule(800, self._poll_qtm_events_sync)

    def _select_all_trials(self) -> None:
        for row in self._trial_rows.values():
            row.set_selected(True)

    def _deselect_all_trials(self) -> None:
        for row in self._trial_rows.values():
            row.set_selected(False)

    def _update_events_summary_badge(self) -> None:
        """Refresh dynamic trials event detection count badge from in-memory row state."""
        n_total = len(self._trial_rows)
        n_labeled = 0
        tot_ev = 0
        for row in self._trial_rows.values():
            info = row.events_info
            if info and info.get("total_events", 0) > 0:
                n_labeled += 1
                tot_ev += info.get("total_events", 0)

        if n_total == 0:
            self._events_badge.setText("Events: None")
        elif n_labeled == n_total:
            self._events_badge.setText(f"Events: {n_labeled}/{n_total} Labeled ({tot_ev})")
        elif n_labeled > 0:
            self._events_badge.setText(f"Events: {n_labeled}/{n_total} Labeled ({tot_ev})")
        else:
            self._events_badge.setText(f"Events: 0/{n_total} Labeled")

    # ═══════════════════════════════════════════════════════════════════
    #  Auto Event Labeling Handlers
    # ═══════════════════════════════════════════════════════════════════

    def _on_auto_label_clicked(self) -> None:
        """Run auto event labeling for selected trials (or all if none selected)."""
        selected_files = [
            fname for fname, row in self._trial_rows.items()
            if row.is_selected
        ]
        if not selected_files:
            selected_files = list(self._trial_rows.keys())

        if not selected_files:
            return

        self._processing_queue = [("auto_event", f) for f in selected_files]
        self._proc_panel.setVisible(True)
        self._process_btn.setEnabled(False)
        self._auto_label_action_btn.setEnabled(False)
        self._auto_event_btn.setEnabled(False)
        self._completion_label.setText("")
        self._view_pres_btn.setVisible(False)
        self._export_pdf_btn.setVisible(False)

        self._process_next_in_queue()

    def _on_single_trial_auto_label(self, filename: str) -> None:
        """Run auto event labeling for a single specific trial."""
        if not filename or filename not in self._trial_rows:
            return

        self._processing_queue = [("auto_event", filename)]
        self._proc_panel.setVisible(True)
        self._process_btn.setEnabled(False)
        self._auto_label_action_btn.setEnabled(False)
        self._auto_event_btn.setEnabled(False)
        self._completion_label.setText("")

        self._process_next_in_queue()

    def _on_view_trial_events(self, trial_filename: str) -> None:
        """Open Event Details inspection dialog for trial."""
        session_dir = self._get_session_dir()
        ev_info = load_trial_events(session_dir, trial_filename)
        # Resolve trial capture frequency from C3D if available
        stem = Path(trial_filename).stem
        c3d_cand = session_dir / f"{stem}.c3d"
        freq = 100.0
        if not c3d_cand.is_file():
            for cand in session_dir.glob("*.c3d"):
                if cand.stem.lower() == stem.lower():
                    c3d_cand = cand
                    break
        if c3d_cand.is_file():
            try:
                import ezc3d
                c_reader = ezc3d.c3d(str(c3d_cand))
                freq = float(c_reader["header"]["points"]["frame_rate"])
            except Exception:
                pass
        if freq == 100.0 and ev_info:
            freq = float(ev_info.get("frame_rate") or ev_info.get("meta", {}).get("frame_rate") or 100.0)

        dlg = EventDetailsDialog(
            trial_filename=trial_filename,
            events_info=ev_info,
            frame_rate=freq,
            session_dir=session_dir,
            parent=self,
            is_dark=getattr(self, "_is_dark", False),
        )
        generation = self._analysis_generation
        dlg.rerun_requested.connect(lambda name: self._on_single_trial_auto_label(name) if generation == self._analysis_generation else None)
        dlg.events_updated.connect(lambda name, info: self._on_trial_events_updated(name, info) if generation == self._analysis_generation else None)
        dlg.exec()

    def _on_trial_events_updated(self, trial_filename: str, ev_info: dict) -> None:
        """Handle events update from manual event dialog and update UI immediately."""
        row = self._trial_rows.get(trial_filename)
        if row:
            row.set_events_info(ev_info)
            if ev_info.get("total_events", 0) > 0 and row._status in ("READY", "SELECTED"):
                row.set_status("EVENTS LABELED")
        self._update_events_summary_badge()

    def _on_push_trial_events_to_qtm(self, trial_filename: str) -> None:
        """Push stored events for this trial directly onto the QTM timeline if open."""
        session_dir = self._get_session_dir()
        ev_info = load_trial_events(session_dir, trial_filename)
        if ev_info is None:
            QMessageBox.information(
                self,
                "No Events Found",
                f"No gait events have been detected or saved for {trial_filename} yet.\n\n"
                "Please run 'Auto-Label Events' first.",
            )
            return

        meta = self._trial_metadata.get(trial_filename, {})
        freq = float(meta.get("frequency") or ev_info.get("frame_rate") or 100.0)
        offset = int(ev_info.get("initial_frame_offset") or 0)

        from app.services.event_sync_service import push_saved_events
        ok, msg = push_saved_events(session_dir, trial_filename)
        updated = load_trial_events(session_dir, trial_filename)
        self._on_trial_events_updated(trial_filename, updated)
        if updated and updated["meta"].get("event_sync_status") == "QTM Conflict":
            self._review_event_conflict(trial_filename)
        elif ok:
            QMessageBox.information(self, "QTM Events", msg)
        else:
            QMessageBox.warning(self, "QTM Events", msg)

    def _review_event_conflict(self, trial_filename):
        from app.services.event_store import EventStore
        from app.services.event_sync_service import event_rpc, resolve_event_conflict
        session_dir = self._get_session_dir()
        try:
            remote = event_rpc("GetEventSnapshot")
            record = EventStore(session_dir).read(trial_filename)
            revision = record["revision"] if record else 0
            local = record["payload"]["events"] if record else []
            box = QMessageBox(self)
            box.setWindowTitle("QTM Event Conflict")
            box.setText(f"{trial_filename}: {len(local)} saved events; {len(remote['events'])} QTM events. Choose which version to keep.")
            import json
            box.setDetailedText(json.dumps({"saved": local, "QTM": remote["events"]}, indent=2, default=str))
            keep_local = box.addButton("Keep Saved Events", QMessageBox.AcceptRole)
            keep_qtm = box.addButton("Keep QTM Events", QMessageBox.DestructiveRole)
            box.addButton(QMessageBox.Cancel)
            box.exec()
            if box.clickedButton() not in (keep_local, keep_qtm):
                return
            info = resolve_event_conflict(session_dir, trial_filename,
                                          "local" if box.clickedButton() is keep_local else "qtm",
                                          revision, remote)
            self._on_trial_events_updated(trial_filename, info)
        except Exception as error:
            QMessageBox.warning(self, "QTM Events", str(error))

    def _on_single_trial_pull_from_qtm(self, trial_filename: str) -> None:
        """
        Explicitly pull events from QTM timeline for a single trial (invoked from row context menu).
        """
        if not self._session_path:
            return
        session_dir = self._get_session_dir()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            updated, msg, matched_file, clean_events, ev_info = sync_qtm_events_to_session(
                session_dir=session_dir,
                trial_filenames=[trial_filename],
                port=50052,
                force=True,
            )
        finally:
            QApplication.restoreOverrideCursor()

        if trial_filename and (ev_info is None or ev_info.get("meta", {}).get("event_sync_status") == "QTM Conflict"):
            self._review_event_conflict(trial_filename)
            return

        if updated or (ev_info and ev_info.get("events")):
            row = self._trial_rows.get(trial_filename)
            if row and ev_info:
                if ev_info.get("total_events", 0) == 0:
                    QMessageBox.information(
                        self,
                        "QTM Timeline Empty",
                        f"No events were found on the QTM timeline for '{trial_filename}'.\n\n"
                        "Existing labeled events in the application were preserved.",
                    )
                    return
                row.set_events_info(ev_info)
                if row._status in ("READY", "SELECTED"):
                    row.set_status("EVENTS LABELED")
            self._update_events_summary_badge()
            QMessageBox.information(
                self,
                "Events Synced from QTM",
                f"✓ Successfully pulled {len(clean_events)} event(s) from QTM timeline for {trial_filename}!\n\n"
                f"Details: {msg}",
            )
        else:
            QMessageBox.warning(
                self,
                "QTM Sync Notice",
                f"Could not pull events for '{trial_filename}':\n\n{msg}\n\n"
                "Please ensure QTM is running and has this trial open.",
            )

    def _on_sync_from_qtm_clicked(self) -> None:
        """
        Manual toolbar trigger: pull events from QTM timeline for the active trial in QTM.
        """
        if not self._session_path or not self._trial_rows:
            return
        session_dir = self._get_session_dir()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            trial_names = list(self._trial_rows.keys())
            updated, msg, matched_file, clean_events, ev_info = sync_qtm_events_to_session(
                session_dir=session_dir,
                trial_filenames=trial_names,
                port=50052,
                force=True,
            )
        finally:
            QApplication.restoreOverrideCursor()

        if matched_file and (ev_info is None or ev_info.get("meta", {}).get("event_sync_status") == "QTM Conflict"):
            self._review_event_conflict(matched_file)
            return

        if matched_file and matched_file in self._trial_rows and ev_info:
            row = self._trial_rows[matched_file]
            if ev_info.get("total_events", 0) == 0:
                QMessageBox.information(
                    self,
                    "QTM Timeline Empty",
                    f"No events were found on the QTM timeline for '{matched_file}'.\n\n"
                    "Existing labeled events in the application were preserved.",
                )
                return
            row.set_events_info(ev_info)
            if row._status in ("READY", "SELECTED"):
                row.set_status("EVENTS LABELED")
            self._update_events_summary_badge()
            QMessageBox.information(
                self,
                "QTM Events Synced",
                f"✓ Successfully synced {len(clean_events)} event(s) from QTM for trial:\n'{matched_file}'\n\n"
                f"Details: {msg}",
            )
        else:
            QMessageBox.information(
                self,
                "QTM Sync Status",
                f"{msg}\n\n"
                "Tip: Ensure the desired trial is actively open in QTM with events marked on its timeline.",
            )

    def _poll_qtm_events_sync(self) -> None:
        """
        Background poll: check if events on the QTM timeline have been modified
        for the currently active trial in QTM, and auto-update the GUI row if so.
        """
        if getattr(self, "_is_syncing_events", False):
            return
        if not self._session_path or not self._trial_rows:
            return
        # Don't poll while an active pipeline job is executing
        if hasattr(self, "_proc_panel") and self._proc_panel.isVisible():
            return
        if self._processing_queue:
            return

        session_dir = self._get_session_dir()
        if not session_dir.is_dir():
            return

        from app.services.event_sync_service import start_event_observation
        self._is_syncing_events = True
        generation = self._analysis_generation
        self._event_sync_worker = start_event_observation(
            session_dir, list(self._trial_rows),
            lambda result: self._on_event_sync_observed(generation, result),
            lambda trial: self._on_event_sync_started(generation, trial))

    def _on_event_sync_started(self, generation, trial):
        pass

    def _on_event_sync_observed(self, generation, result):
        self._is_syncing_events = False
        self._event_sync_worker = None
        if generation != self._analysis_generation:
            return
        updated, message, trial, events, info = result
        if info and trial in self._trial_rows:
            self._trial_rows[trial].set_events_info(info)
            if info.get("total_events", 0) > 0 and self._trial_rows[trial]._status in ("READY", "SELECTED"):
                self._trial_rows[trial].set_status("EVENTS LABELED")
            self._update_events_summary_badge()
        if message != getattr(self, "_last_event_sync_notice", None):
            logger.info("QTM event observation: %s", message)
            self._last_event_sync_notice = message

    def _setup_fs_watcher(self, session_dir: Path) -> None:
        paths = self._fs_watcher.files() + self._fs_watcher.directories()
        if paths:
            self._fs_watcher.removePaths(paths)
        self._event_projection_stamps = {}
        for directory in (session_dir, session_dir / "Events"):
            if directory.is_dir():
                self._fs_watcher.addPath(str(directory))
                for path in directory.glob("auto_event_*_results.json"):
                    self._fs_watcher.addPath(str(path))
                    stat = path.stat()
                    self._event_projection_stamps[str(path)] = (stat.st_mtime_ns, stat.st_size)

    def _on_fs_file_changed(self, path: str) -> None:
        if not self._session_path:
            return
        path = Path(path)
        session = Path(self._session_path).parent.resolve()
        if path.resolve().parent not in {session, session / "Events"} or not path.is_file():
            return
        stamps = self._event_projection_stamps
        stat = path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
        if stamps.get(str(path)) == stamp:
            return
        stamps[str(path)] = stamp
        if str(path) not in self._fs_watcher.files():
            self._fs_watcher.addPath(str(path))
        import re
        match = re.match(r"^auto_event_(.+)_results$", path.stem, re.IGNORECASE)
        if not match:
            return
        for trial in self._trial_rows:
            if trial_names_match(trial, match.group(1)):
                info = load_trial_events(session, trial)
                if info:
                    self._on_trial_events_updated(trial, info)
                break

    def _on_fs_directory_changed(self, dir_path: str) -> None:
        if not self._session_path:
            return
        session = Path(self._session_path).parent.resolve()
        directory = Path(dir_path).resolve()
        if directory not in {session, session / "Events"}:
            return
        for folder in (session, session / "Events"):
            if not folder.is_dir():
                continue
            if str(folder) not in self._fs_watcher.directories():
                self._fs_watcher.addPath(str(folder))
            for path in folder.glob("auto_event_*_results.json"):
                self._on_fs_file_changed(str(path))
        # SQLite WAL notifications never cause projection reads or QTM writes.

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if hasattr(self, "_qtm_sync_timer") and self._session_path:
            if not self._qtm_sync_timer.isActive():
                self._qtm_sync_timer.start(1200)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        if hasattr(self, "_qtm_sync_timer") and self._qtm_sync_timer.isActive():
            self._qtm_sync_timer.stop()

    # ═══════════════════════════════════════════════════════════════════
    #  Processing Workflow
    # ═══════════════════════════════════════════════════════════════════

    def _is_static_calibration_ready(self) -> Tuple[bool, str]:
        """Check if session has a valid static calibration with transformation matrices."""
        if not self._session_path:
            return False, "No session loaded."
        session_dir = Path(self._session_path).resolve().parent
        if not session_dir.is_dir():
            return False, "Session directory not found."

        from app.services.session_organizer import find_static_calibration_files
        static_files = [
            sf for sf in find_static_calibration_files(session_dir)
            if sf.resolve().parent in {session_dir, session_dir / "Calibration"}
        ]
        if not static_files:
            return False, "No Static calibration file (Static_*.py) found in this session."

        calibrated = False
        for sf in static_files:
            try:
                content = sf.read_text(encoding="utf-8", errors="replace")
                if "valueEPelvisAnatRelTech" in content and "Transformation Matrices" in content:
                    calibrated = True
                    break
            except Exception:
                continue

        if not calibrated:
            return False, (
                "Static calibration has not been completed for this session yet\n"
                "(calibration transformation matrices are missing).\n\n"
                "Please run Static Calibration from Stage 1 first."
            )
        return True, ""

    def _on_process_clicked(self) -> None:
        selected_files = [
            fname for fname, row in self._trial_rows.items()
            if row.is_selected
        ]
        if not selected_files:
            return

        ready, reason = self._is_static_calibration_ready()
        if not ready:
            QMessageBox.warning(
                self,
                "Static Calibration Required",
                f"Cannot process dynamic trials:\n\n{reason}",
            )
            return

        self._processed_success_count = 0
        self._processed_error_count = 0
        self._failed_trials.clear()

        queue: List[Tuple[str, str]] = []
        if self._opt_auto_events.isChecked():
            # Automatically auto-label any selected trials that have no events yet
            for f in selected_files:
                row = self._trial_rows.get(f)
                if not row or not row.events_info or row.events_info.get("total_events", 0) == 0:
                    queue.append(("auto_event", f))

        for f in selected_files:
            queue.append(("dynamic", f))

        self._processing_queue = queue
        self._proc_panel.setVisible(True)
        self._process_btn.setEnabled(False)
        self._auto_label_action_btn.setEnabled(False)
        self._auto_event_btn.setEnabled(False)
        self._completion_label.setText("")
        self._view_pres_btn.setVisible(False)
        self._export_pdf_btn.setVisible(False)

        self._process_next_in_queue()

    def _on_open_force_plate_dialog(self) -> None:
        """Open Force Plate configuration dialog for selected trial."""
        selected_file = None
        for fname, row in self._trial_rows.items():
            if row.is_selected:
                selected_file = fname
                break
        if not selected_file and self._trial_rows:
            selected_file = list(self._trial_rows.keys())[0]

        if not selected_file:
            return

        session_dir = str(Path(self._session_path).parent) if self._session_path else os.getcwd()
        cur_cfg = self._force_plate_configs.get(selected_file, {})
        dlg = ForcePlateConfigDialog(
            session_dir=session_dir,
            trial_filename=selected_file,
            current_left=cur_cfg.get("left_plate", "FP0"),
            current_right=cur_cfg.get("right_plate", "0"),
            parent=self,
            is_dark=getattr(self, "_is_dark", False),
        )
        generation = self._analysis_generation
        dlg.configuration_saved.connect(lambda cfg: self._on_fp_config_saved(selected_file, cfg) if generation == self._analysis_generation else None)
        dlg.exec()

    def _on_fp_config_saved(self, trial_file: str, cfg: dict) -> None:
        if cfg.get("apply_to_all", False):
            for f in self._trial_rows.keys():
                self._force_plate_configs[f] = dict(cfg)
        else:
            self._force_plate_configs[trial_file] = dict(cfg)
        l_p = cfg.get("left_plate", "0")
        r_p = cfg.get("right_plate", "0")
        self._fp_badge.setText(f"Force Plate: Left={l_p}, Right={r_p}")

    def _process_next_in_queue(self) -> None:
        if not self._processing_queue:
            # All done!
            self._proc_panel.setVisible(False)
            self._process_btn.setEnabled(True)
            self._auto_label_action_btn.setEnabled(True)
            self._auto_event_btn.setEnabled(True)

            if self._processed_error_count > 0 and self._processed_success_count == 0:
                self._completion_label.setText(
                    f"⚠ Processing failed ({self._processed_error_count} trial(s) had errors) — no GCD files generated"
                )
                self._completion_label.setStyleSheet("color: #EF4444; font-weight: bold;")
            elif self._processed_error_count > 0:
                self._completion_label.setText(
                    f"⚠ Processing finished: {self._processed_success_count} succeeded, {self._processed_error_count} failed"
                )
                self._completion_label.setStyleSheet("color: #ED8B00; font-weight: bold;")
            elif self._processed_success_count > 0:
                self._completion_label.setText(
                    f"✓ Processing complete — {self._processed_success_count} GCD file(s) generated"
                )
                self._completion_label.setStyleSheet("color: #22C55E; font-weight: bold;")
            else:
                self._completion_label.setText(
                    self._last_completion_message or "✓ Processing complete — proceed to Patients && Sessions"
                )
                self._completion_label.setStyleSheet("")

            # If any GCD exists, show view_pres_btn and export_pdf_btn
            session_dir = Path(os.path.dirname(self._session_path)) if self._session_path else Path(".")
            from app.services.session_organizer import find_all_gcd_files, find_gcd_file
            gcds = find_all_gcd_files(session_dir)
            if gcds:
                self._view_pres_btn.setText("Proceed to Patients && Sessions →")
                self._view_pres_btn.setVisible(True)
                self._export_pdf_btn.setVisible(True)
            return

        self._current_task_type, self._current_processing_file = self._processing_queue.pop(0)
        row = self._trial_rows.get(self._current_processing_file)

        if self._current_task_type == "auto_event":
            if row:
                row.set_status("LABELING")

            self._proc_title.setText(f"Auto-Labeling Gait Events: {self._current_processing_file}")
            self._proc_bar.setValue(10)
            self._proc_status.setText("Reading marker trajectories and detecting foot strikes / toe offs...")

            logger.info("Starting auto event labeling for %s", self._current_processing_file)
            self._service.run_auto_event_labeling(
                self._session_path,
                self._current_processing_file,
                condition="BF",
            )
        else:  # dynamic
            if row:
                row.set_status("PROCESSING")

            self._proc_title.setText(f"Processing Dynamic Trial: {self._current_processing_file}")
            self._proc_bar.setValue(10)
            self._proc_status.setText("Reading session metadata and marker trajectories...")

            fp_cfg = self._force_plate_configs.get(self._current_processing_file, {})
            left_plate = fp_cfg.get("left_plate", "FP0")
            right_plate = fp_cfg.get("right_plate", "0")
            interactive = self._opt_interactive_fp.isChecked()

            logger.info(
                "Starting dynamic processing for %s (Left=%s, Right=%s, interactive=%s)",
                self._current_processing_file, left_plate, right_plate, interactive,
            )
            self._service.process_dynamic(
                self._session_path,
                self._current_processing_file,
                condition="BF",
                left_plate=left_plate,
                right_plate=right_plate,
                interactive_fp=interactive,
            )

    def _on_trial_started(self, script_name: str) -> None:
        self._proc_bar.setValue(20)

    def _on_trial_progress(self, status: ProcessingStatus) -> None:
        self._proc_bar.setValue(status.progress)
        if status.message:
            self._proc_status.setText(status.message)

    def _on_trial_finished(self, status: ProcessingStatus) -> None:
        row = self._trial_rows.get(self._current_processing_file)
        session_dir = Path(os.path.dirname(self._session_path)) if self._session_path else Path(".")

        if self._current_task_type == "auto_event":
            ev_info = load_trial_events(session_dir, self._current_processing_file)
            if row:
                row.set_events_info(ev_info)
                if status.step == "complete" or status.completed:
                    if row._status != "COMPLETE":
                        row.set_status("EVENTS LABELED")
                else:
                    row.set_status("ERROR")
            self._update_events_summary_badge()
            tot = ev_info.get("total_events", 0) if ev_info else 0
            self._last_completion_message = f"Auto-Label completed ({tot} events)" if ev_info else "Auto-Label did not commit events"
        else:  # dynamic
            from app.services.session_organizer import find_gcd_file
            stem = Path(self._current_processing_file).stem
            gcd_file = find_gcd_file(session_dir, stem)
            is_success = (status.step == "complete" or status.completed) and gcd_file is not None and gcd_file.is_file()
            if is_success:
                if row:
                    row.set_status("COMPLETE")
                self._processed_success_count += 1
                logger.info("Dynamic processing finished for %s (GCD file created)", self._current_processing_file)
            else:
                if row:
                    row.set_status("ERROR")
                self._processed_error_count += 1
                self._failed_trials.append(self._current_processing_file)
                logger.error("Dynamic processing failed for %s", self._current_processing_file)
            self._last_completion_message = "✓ Processing complete — GCD files generated"

        # Trigger next in queue
        self._schedule(400, self._process_next_in_queue)

    def _on_trial_error(self, err_msg: str) -> None:
        row = self._trial_rows.get(self._current_processing_file)
        if row:
            row.set_status("ERROR")
        if self._current_task_type == "dynamic":
            self._processed_error_count += 1
            if self._current_processing_file not in self._failed_trials:
                self._failed_trials.append(self._current_processing_file)
        self._proc_status.setText(f"Error: {err_msg}")
        self._schedule(1000, self._process_next_in_queue)

    def _on_cancel_processing(self) -> None:
        self._service.cancel()
        self._processing_queue.clear()
        self._proc_panel.setVisible(False)
        self._process_btn.setEnabled(True)
        self._auto_label_action_btn.setEnabled(True)
        self._auto_event_btn.setEnabled(True)

    def _on_view_presentation(self) -> None:
        self.proceed_to_patients.emit(self._session_path)

    def _on_export_pdf_clicked(self) -> None:
        """Directly export complete clinical PDF report from Dynamic Analysis page."""
        session_dir = Path(os.path.dirname(self._session_path)) if self._session_path else Path(".")
        from app.services.session_organizer import find_all_gcd_files, get_reports_dir
        gcds = find_all_gcd_files(session_dir)
        if not gcds:
            QMessageBox.warning(
                self,
                "No Data Available",
                "No dynamic trial (.GCD) files found in this session.\nPlease process dynamic gait trials first.",
            )
            return

        mrn = session_dir.parent.name
        dt = session_dir.name
        default_name = f"Gait_Analysis_Report_{mrn}_{dt}.pdf"
        reports_dir = get_reports_dir(session_dir, create=True)
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
                session_path=session_dir,
                output_pdf_path=save_path,
            )
        except Exception as e:
            QApplication.restoreOverrideCursor()
            logger.error("Failed to generate PDF report from dynamic page: %s", e, exc_info=True)
            QMessageBox.critical(
                self,
                "PDF Export Error",
                f"An error occurred while generating the clinical report:\n{e}",
            )
            return
        finally:
            QApplication.restoreOverrideCursor()

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
        pres_btn = msg_box.addButton("View in Presentation", QMessageBox.ActionRole)
        close_btn = msg_box.addButton("Close", QMessageBox.RejectRole)
        msg_box.setDefaultButton(open_btn)

        msg_box.exec()
        if msg_box.clickedButton() == open_btn:
            CasePresentationPdfService.open_pdf(pdf_path)
        elif msg_box.clickedButton() == folder_btn:
            CasePresentationPdfService.open_containing_folder(pdf_path)
        elif msg_box.clickedButton() == pres_btn:
            self._on_view_presentation()

