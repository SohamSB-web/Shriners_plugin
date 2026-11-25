# -*- coding: utf-8 -*-
"""
Processing Page — visual pipeline for static calibration, dynamic processing,
and GCD generation.  Connects to GaitProcessingService for background work.
"""

from __future__ import annotations

import logging
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.data_models import ProcessingStatus
from app.services.processing_service import GaitProcessingService
from app.ui.theme.design_tokens import FONT_SIZE_H2, SPACE_LG, SPACE_MD, SPACE_SM, SPACE_XL, SPACE_XS
from app.ui.widgets.components import (
    NotificationBanner,
    ProcessingStep,
    SectionCard,
)

logger = logging.getLogger(__name__)


class ProcessingPage(QScrollArea):
    """Data processing pipeline page."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)

        self._processing_svc = GaitProcessingService()
        self._processing_svc.processing_started.connect(self._on_started)
        self._processing_svc.processing_log.connect(self._log)
        self._processing_svc.processing_progress.connect(self._on_progress)
        self._processing_svc.processing_finished.connect(self._on_finished)
        self._processing_svc.processing_error.connect(self._on_error)

        container = QWidget()
        self.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        layout.setSpacing(SPACE_LG)

        # Header
        header = QLabel("Data Processing")
        header.setObjectName("headerTitle")
        header.setStyleSheet(f"font-size: {FONT_SIZE_H2}px; font-weight: 700;")
        layout.addWidget(header)

        # Notification
        self._notification = NotificationBanner()
        layout.addWidget(self._notification)

        # ── File Selection ─────────────────────────────────────────
        file_card = SectionCard("Session Selection")
        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("QTM File:"))
        self._file_input = QLineEdit()
        self._file_input.setReadOnly(True)
        self._file_input.setPlaceholderText("Select a .qtm file to process…")
        file_row.addWidget(self._file_input, 1)

        self._browse_btn = QPushButton("Browse…")
        self._browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(self._browse_btn)

        # Testing Condition
        file_row.addSpacing(SPACE_MD)
        file_row.addWidget(QLabel("Condition:"))
        self._cond_combo = QComboBox()
        self._cond_combo.addItems(["BF", "AFO", "Shoes", "Braces", "Custom"])
        self._cond_combo.setFixedWidth(90)
        file_row.addWidget(self._cond_combo)

        file_card.add_layout(file_row)
        layout.addWidget(file_card)

        # ── Pipeline Steps ─────────────────────────────────────────
        pipeline_card = SectionCard("Processing Pipeline")
        self._steps = []
        step_data = [
            (1, "Session Selection"),
            (2, "Static Calibration"),
            (3, "Dynamic Trials"),
            (4, "GCD Generation"),
            (5, "Validation"),
        ]
        for num, title in step_data:
            step = ProcessingStep(num, title)
            self._steps.append(step)
            pipeline_card.add_widget(step)
        layout.addWidget(pipeline_card)

        # ── Action Buttons ─────────────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setSpacing(SPACE_SM)

        self._static_btn = QPushButton("Run Static Analysis")
        self._static_btn.setObjectName("primaryButton")
        self._static_btn.clicked.connect(self._run_static)
        self._static_btn.setEnabled(False)
        action_row.addWidget(self._static_btn)

        self._dynamic_btn = QPushButton("Run Dynamic Analysis")
        self._dynamic_btn.setObjectName("primaryButton")
        self._dynamic_btn.clicked.connect(self._run_dynamic)
        self._dynamic_btn.setEnabled(False)
        action_row.addWidget(self._dynamic_btn)

        self._auto_btn = QPushButton("Auto Event Labeling")
        self._auto_btn.clicked.connect(self._run_auto_label)
        self._auto_btn.setEnabled(False)
        action_row.addWidget(self._auto_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("dangerButton")
        self._cancel_btn.clicked.connect(self._cancel_processing)
        self._cancel_btn.setEnabled(False)
        action_row.addWidget(self._cancel_btn)

        action_row.addStretch()
        layout.addLayout(action_row)

        # ── Progress ───────────────────────────────────────────────
        progress_card = SectionCard("Progress")
        self._progress_label = QLabel("Idle")
        progress_card.add_widget(self._progress_label)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(12)
        progress_card.add_widget(self._progress_bar)
        layout.addWidget(progress_card)

        # ── Log output ─────────────────────────────────────────────
        log_card = SectionCard("Processing Log")
        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("Real-time Output:"))
        log_header.addStretch()
        clear_btn = QPushButton("Clear Log")
        clear_btn.setFixedWidth(80)
        clear_btn.clicked.connect(self._clear_log)
        log_header.addWidget(clear_btn)
        log_card.add_layout(log_header)

        self._log_output = QTextEdit()
        self._log_output.setReadOnly(True)
        self._log_output.setFixedHeight(220)
        self._update_log_style(dark=False)
        log_card.add_widget(self._log_output)
        layout.addWidget(log_card)

        layout.addStretch()

        # State
        self._session_xml = ""
        self._filename = ""
        self._active_action = ""

    def _browse_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select QTM File", "", "QTM Files (*.qtm);;All Files (*.*)"
        )
        if file_path:
            self._set_file(file_path)

    def _set_file(self, file_path: str) -> None:
        """Configure the page for a specific QTM file path."""
        self._file_input.setText(file_path)
        self._filename = os.path.basename(file_path)
        dir_path = os.path.dirname(file_path)
        self._session_xml = os.path.join(dir_path, "session.xml")

        if os.path.exists(self._session_xml):
            self._steps[0].set_status("complete")
            self._enable_buttons()
            self._notification.show_message(
                f"Loaded {self._filename} with valid session.xml", "info"
            )
            self._log(f"Selected: {file_path}")
            self._log(f"Found session metadata: {self._session_xml}")
        else:
            self._steps[0].set_status("complete")
            self._enable_buttons()
            self._notification.show_message(
                f"Warning: session.xml not found in {dir_path}. Processing scripts require session.xml.",
                "warning",
            )
            self._log(f"Selected: {file_path}")
            self._log(f"WARNING: session.xml not found in directory: {dir_path}")

    def _clear_log(self) -> None:
        self._log_output.clear()

    def _run_static(self) -> None:
        if not self._session_xml:
            return
        self._active_action = "static"
        self._disable_buttons()
        self._steps[1].set_status("running")
        cond = self._cond_combo.currentText()
        self._processing_svc.process_static(self._session_xml, self._filename, condition=cond)

    def _run_dynamic(self) -> None:
        if not self._session_xml:
            return
        self._active_action = "dynamic"
        self._disable_buttons()
        self._steps[2].set_status("running")
        self._steps[3].set_status("running")
        cond = self._cond_combo.currentText()
        self._processing_svc.process_dynamic(self._session_xml, self._filename, condition=cond)

    def _run_auto_label(self) -> None:
        if not self._session_xml:
            return
        self._active_action = "auto_label"
        self._disable_buttons()
        self._steps[4].set_status("running")
        cond = self._cond_combo.currentText()
        self._processing_svc.run_auto_event_labeling(self._session_xml, self._filename, condition=cond)

    def _cancel_processing(self) -> None:
        self._log("Cancelling processing...")
        self._processing_svc.cancel()

    def _disable_buttons(self) -> None:
        self._static_btn.setEnabled(False)
        self._dynamic_btn.setEnabled(False)
        self._auto_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)

    def _enable_buttons(self) -> None:
        self._static_btn.setEnabled(bool(self._session_xml))
        self._dynamic_btn.setEnabled(bool(self._session_xml))
        self._auto_btn.setEnabled(bool(self._session_xml))
        self._cancel_btn.setEnabled(False)

    def _on_started(self, script: str) -> None:
        self._progress_label.setText(f"Running {script}…")
        self._progress_bar.setValue(0)
        self._progress_bar.setRange(0, 0)  # indeterminate
        self._log(f"Started: {script}")

    def _on_progress(self, status: ProcessingStatus) -> None:
        self._progress_label.setText(status.message)
        if status.progress > 0:
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(status.progress)

    def _on_finished(self, status: ProcessingStatus) -> None:
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100 if status.completed else 0)
        self._progress_label.setText(status.message)
        self._enable_buttons()

        if status.completed:
            self._notification.show_message("Processing completed successfully!", "success")
            self._log(f"✓ {status.message}")
            if self._active_action == "static":
                self._steps[1].set_status("complete")
            elif self._active_action == "dynamic":
                self._steps[2].set_status("complete")
                self._steps[3].set_status("complete")
            elif self._active_action == "auto_label":
                self._steps[4].set_status("complete")
        else:
            self._notification.show_message(status.message, "error")
            if self._active_action == "static":
                self._steps[1].set_status("error")
            elif self._active_action == "dynamic":
                self._steps[2].set_status("error")
                self._steps[3].set_status("error")
            elif self._active_action == "auto_label":
                self._steps[4].set_status("error")
            for err in status.errors:
                self._log(f"ERROR: {err}")

    def _on_error(self, msg: str) -> None:
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_label.setText("Error")
        self._enable_buttons()
        self._notification.show_message(msg, "error")
        self._log(f"ERROR: {msg}")
        if self._active_action == "static":
            self._steps[1].set_status("error")
        elif self._active_action == "dynamic":
            self._steps[2].set_status("error")
            self._steps[3].set_status("error")
        elif self._active_action == "auto_label":
            self._steps[4].set_status("error")

    def _log(self, message: str) -> None:
        self._log_output.append(message)
        sb = self._log_output.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def cleanup(self) -> None:
        """Safely terminate any active background task."""
        if self._processing_svc.is_running:
            self._processing_svc.cancel()

    def _update_log_style(self, dark: bool = False) -> None:
        if dark:
            self._log_output.setStyleSheet(
                "font-family: Consolas, monospace; font-size: 12px; "
                "background-color: #0F172A; color: #14B8A6; "
                "border: 1.5px solid #334155; border-radius: 8px; padding: 10px;"
            )
        else:
            self._log_output.setStyleSheet(
                "font-family: Consolas, monospace; font-size: 12px; "
                "background-color: #F8FAFC; color: #0F172A; "
                "border: 1.5px solid #E2E8F0; border-radius: 8px; padding: 10px;"
            )

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        """Update processing page theme."""
        self._is_dark = dark
        self._update_log_style(dark=dark)

