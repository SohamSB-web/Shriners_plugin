# -*- coding: utf-8 -*-
"""Dashboard Page — overview cards for patient, session, processing, analysis."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme.design_tokens import (
    FONT_SIZE_H2,
    FONT_SIZE_H3,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
)
from app.ui.widgets.components import MetricCard, SectionCard, StatusIndicator
from app.ui.widgets.smooth_scroll import apply_smooth_scroll


class DashboardPage(QScrollArea):
    """Main dashboard with summary cards."""

    navigate_to = Signal(str)  # emits page name

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self._smooth_scroll = apply_smooth_scroll(self)

        container = QWidget()
        self.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        layout.setSpacing(SPACE_LG)

        # Page header
        header = QLabel("Dashboard")
        header.setObjectName("headerTitle")
        header.setStyleSheet(f"font-size: {FONT_SIZE_H2}px; font-weight: 700;")
        layout.addWidget(header)

        subtitle = QLabel("Shriners Motion Analysis Center — Clinical Workstation")
        subtitle.setObjectName("captionLabel")
        layout.addWidget(subtitle)

        # ── Top row: Patient + Session ──────────────────────────────
        row1 = QGridLayout()
        row1.setSpacing(SPACE_MD)

        self.patient_card = MetricCard(
            title="Current Patient", value="—", subtext="No patient loaded",
            icon_name="patients.svg",
        )
        self.patient_card.clicked.connect(lambda: self.navigate_to.emit("patients"))
        row1.addWidget(self.patient_card, 0, 0)

        self.session_card = MetricCard(
            title="Active Session", value="—", subtext="No session selected",
            icon_name="folder.svg",
        )
        self.session_card.clicked.connect(lambda: self.navigate_to.emit("sessions"))
        row1.addWidget(self.session_card, 0, 1)

        self.trials_card = MetricCard(
            title="Trials Loaded", value="0", subtext="Left: 0  |  Right: 0",
            icon_name="dynamic_analysis.svg",
        )
        row1.addWidget(self.trials_card, 0, 2)

        layout.addLayout(row1)

        # ── Second row: Processing + Analysis ───────────────────────
        row2 = QGridLayout()
        row2.setSpacing(SPACE_MD)

        self.processing_card = MetricCard(
            title="Processing", value="Idle", subtext="No active processing",
            icon_name="settings.svg",
        )
        self.processing_card.clicked.connect(lambda: self.navigate_to.emit("processing"))
        row2.addWidget(self.processing_card, 0, 0)

        self.analysis_card = MetricCard(
            title="Analysis", value="—", subtext="Kinematics · Kinetics · EMG · Muscle",
            icon_name="chart.svg",
        )
        self.analysis_card.clicked.connect(lambda: self.navigate_to.emit("analysis"))
        row2.addWidget(self.analysis_card, 0, 1)

        self.report_card = MetricCard(
            title="Reports", value="—", subtext="No reports generated",
            icon_name="file_text.svg",
        )
        self.report_card.clicked.connect(lambda: self.navigate_to.emit("reports"))
        row2.addWidget(self.report_card, 0, 2)

        layout.addLayout(row2)

        # ── Third row: QTM + System Status ──────────────────────────
        row3 = QGridLayout()
        row3.setSpacing(SPACE_MD)

        self.qtm_card = MetricCard(
            title="QTM Connection", value="Disconnected",
            subtext="gRPC port 50051",
            icon_name="qtm_bridge.svg",
        )
        self.qtm_card.clicked.connect(lambda: self.navigate_to.emit("qtm"))
        row3.addWidget(self.qtm_card, 0, 0)

        # Quick status section
        status_card = SectionCard("System Status")
        self.qtm_status = StatusIndicator("disconnected", "QTM: Disconnected")
        status_card.add_widget(self.qtm_status)
        self.processing_status = StatusIndicator("idle", "Processing: Idle")
        status_card.add_widget(self.processing_status)
        row3.addWidget(status_card, 0, 1, 1, 2)

        layout.addLayout(row3)
        layout.addStretch()

    # ── Public update methods ───────────────────────────────────────

    def update_patient(self, mrn: str) -> None:
        self.patient_card.set_value(mrn if mrn else "—")
        self.patient_card.set_subtext(f"MRN: {mrn}" if mrn else "No patient loaded")

    def update_session(self, directory: str, date: str = "") -> None:
        import os
        short = os.path.basename(directory) if directory else "—"
        self.session_card.set_value(short)
        self.session_card.set_subtext(date if date else "Session loaded")

    def update_trials(self, left_count: int, right_count: int) -> None:
        total = left_count + right_count
        self.trials_card.set_value(str(total))
        self.trials_card.set_subtext(f"Left: {left_count}  |  Right: {right_count}")

    def update_qtm_status(self, connected: bool) -> None:
        if connected:
            self.qtm_card.set_value("Connected")
            self.qtm_status.set_status("connected", "QTM: Connected")
        else:
            self.qtm_card.set_value("Disconnected")
            self.qtm_status.set_status("disconnected", "QTM: Disconnected")

    def update_processing_status(self, status: str) -> None:
        self.processing_status.set_status(
            "processing" if status == "running" else status,
            f"Processing: {status.capitalize()}",
        )

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        """Update dashboard metric cards for theme change."""
        self._is_dark = dark
        cards = [
            self.patient_card,
            self.session_card,
            self.trials_card,
            self.processing_card,
            self.analysis_card,
            self.report_card,
            self.qtm_card,
        ]
        for card in cards:
            card.apply_theme(palette, dark)

