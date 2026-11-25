# -*- coding: utf-8 -*-
"""
Reports Page — PDF report configuration and generation.
Wraps the existing ReportLab-based PDF generation logic.
"""

from __future__ import annotations

import logging
import os

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.pdf_report_service import CasePresentationPdfService
from app.ui.theme.design_tokens import FONT_SIZE_H2, SPACE_LG, SPACE_MD, SPACE_SM, SPACE_XL, SPACE_XS
from app.ui.widgets.components import NotificationBanner, SectionCard

logger = logging.getLogger(__name__)


class ReportsPage(QScrollArea):
    """PDF report generation page."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        self.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        layout.setSpacing(SPACE_LG)

        # Header
        header = QLabel("Report Generation")
        header.setObjectName("headerTitle")
        header.setStyleSheet(f"font-size: {FONT_SIZE_H2}px; font-weight: 700;")
        layout.addWidget(header)

        self._notification = NotificationBanner()
        layout.addWidget(self._notification)

        # ── Report info ────────────────────────────────────────────
        info_card = SectionCard("Report Information")
        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("Patient:"))
        self._patient_label = QLabel("—")
        self._patient_label.setStyleSheet("font-weight: 600;")
        info_row.addWidget(self._patient_label)
        info_row.addSpacing(SPACE_LG)
        info_row.addWidget(QLabel("Session:"))
        self._session_label = QLabel("—")
        self._session_label.setStyleSheet("font-weight: 600;")
        info_row.addWidget(self._session_label)
        info_row.addStretch()
        info_card.add_layout(info_row)
        layout.addWidget(info_card)

        # ── Section selection ──────────────────────────────────────
        sections_card = SectionCard("Report Sections")
        sections_grid = QGridLayout()
        sections_grid.setSpacing(SPACE_SM)

        self._section_checks = {}
        sections = [
            ("kinematics", "Kinematics"),
            ("sagittal_kinetics", "Sagittal Kinetics"),
            ("coronal_kinetics", "Coronal Kinetics"),
            ("emg", "EMG"),
            ("foot_kinematics", "Foot Kinematics"),
            ("muscle_length", "Muscle Length"),
            ("muscle_velocity", "Muscle Velocity"),
            ("comparison", "Session Comparison"),
            ("temporal", "Temporal-Spatial Summary"),
        ]
        for i, (key, label) in enumerate(sections):
            cb = QCheckBox(label)
            cb.setChecked(True)
            sections_grid.addWidget(cb, i // 3, i % 3)
            self._section_checks[key] = cb

        sections_card.add_layout(sections_grid)
        layout.addWidget(sections_card)

        # ── Output ─────────────────────────────────────────────────
        output_card = SectionCard("Output")
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Directory:"))
        self._output_dir = QLineEdit()
        self._output_dir.setPlaceholderText("Select output directory…")
        out_row.addWidget(self._output_dir, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_output)
        out_row.addWidget(browse_btn)
        output_card.add_layout(out_row)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Filename:"))
        self._filename_edit = QLineEdit()
        self._filename_edit.setPlaceholderText("Report.pdf")
        name_row.addWidget(self._filename_edit, 1)
        output_card.add_layout(name_row)
        layout.addWidget(output_card)

        # ── Generate button ────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._generate_btn = QPushButton("Generate PDF Report")
        self._generate_btn.setObjectName("primaryButton")
        self._generate_btn.setFixedHeight(44)
        self._generate_btn.clicked.connect(self._generate_report)
        btn_row.addWidget(self._generate_btn)

        self._open_btn = QPushButton("Open Report")
        self._open_btn.setEnabled(False)
        self._open_btn.clicked.connect(self._open_report)
        btn_row.addWidget(self._open_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

        self._last_report_path = ""

    def update_patient_info(self, mrn: str, session: str) -> None:
        self._patient_label.setText(mrn or "—")
        self._session_label.setText(session or "—")

    def _browse_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self._output_dir.setText(directory)

    def _generate_report(self) -> None:
        """
        Trigger PDF generation.

        NOTE: The actual PDF generation logic lives in the original
        MAC_CasePresentation's savePdf() function (~10K lines).
        This page provides the UI wrapper; the full integration will
        call that logic through the service layer.
        """
        selected = {k: cb.isChecked() for k, cb in self._section_checks.items()}
        logger.info("Generate report with sections: %s", selected)

        out_dir = self._output_dir.text()
        filename = self._filename_edit.text() or "Report.pdf"

        if not out_dir:
            self._notification.show_message(
                "Please select an output directory.", "warning"
            )
            return

        self._notification.show_message("Generating clinical PDF report…", "info", timeout_ms=0)
        self._generate_btn.setEnabled(False)

        session_dir = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "Shriners_Gait_Model_PAF_v1.0"
            / "Shriners_Gait_Model_PAF_v1.0"
            / "Data"
            / "Shriners_test_002"
            / "2025-02-21_0003"
        )
        target_path = os.path.join(out_dir, filename)

        try:
            res_path = CasePresentationPdfService.generate_report(
                session_path=session_dir,
                output_pdf_path=target_path,
            )
            self._on_generation_complete(res_path)
        except Exception as e:
            logger.error("Report generation failed: %s", e)
            self._generate_btn.setEnabled(True)
            self._notification.show_message(f"PDF generation failed: {e}", "error")

    def _on_generation_complete(self, path: str) -> None:
        self._last_report_path = path
        self._generate_btn.setEnabled(True)
        self._open_btn.setEnabled(True)
        self._notification.show_message(
            f"Report generated: {os.path.basename(path)}", "success"
        )

    def _open_report(self) -> None:
        if self._last_report_path and os.path.isfile(self._last_report_path):
            os.startfile(self._last_report_path)
