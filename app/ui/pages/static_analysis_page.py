# -*- coding: utf-8 -*-
"""
Static Analysis GUI — Redesigned in PySide6 for Shriners Gait Analysis.

Provides a minimal, modern, clinical workstation interface for static calibration:
- Patient information (First/Last name, Patient Number, DOB, Trial Activity/Modifier)
- Anthropometric parameters (Body Mass, Height, ASIS, Leg Length, Knee/Ankle Width, etc.)
- Foot model configuration (Hindfoot Varus/Valgus, Calcaneal Pitch, etc.)
- Special test conditions (Plantigrade, Shod, Knee Option, Pelvic Fix)
- Scientific configuration (Hip model, coordinate system, marker set)
- Progressive processing state with real-time trajectory status
- Completion state with direct continuation to Dynamic Analysis.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

from PySide6.QtCore import Qt, Signal, QSignalBlocker, QTimer, QPropertyAnimation, QEasingCurve, QSize, QSaveFile, QIODevice
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPlainTextEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QGraphicsOpacityEffect,
)

from app.models.data_models import ProcessingStatus
from app.services.processing_service import GaitProcessingService
from app.services.anthropometric_sync_service import (
    ANTHROPOMETRIC_FIELDS, PATIENT_FIELDS, AnthropometricSyncService,
    parameter_text, format_measurement, same_field_value, validate_parameter, validate_patient_field,
    update_session_xml, get_session_xml_path,
)
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
    RADIUS_LG,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
    SPACE_XXS,
    LIGHT_PALETTE,
)
from app.ui.widgets.components import create_tinted_icon, create_tinted_pixmap

logger = logging.getLogger(__name__)

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

DEFAULT_STATIC_TEMPLATE_HEADER = """self.MarkerDiameter = 14 + 4 # Add Marker Base thickness x 2
self.StaticForwardDirection = '+X'
self.HipModelName = 'Harrington2' # Options are 'Newington' or 'Harrington' or 'Harrington2'
self.TrunkRotationSequence = 'ROT' # Options are 'ROT' or 'TOR'
self.PelvisRotationSequence = 'ROT' # Options are 'ROT' or 'TOR'
self.ShankCoordinateSystem = 'Distal' # Options are 'Distal' or 'Proximal'
self.C7MarkerName = 'C7'
self.LeftClavicleMarkerName = 'Left_Clavicle'
self.RightClavicleMarkerName = 'Right_Clavicle'
self.SacralTriadMarkerName = 'Sacral_Triad'
self.LeftASISMarkerName = 'Left_ASIS'
self.LeftPSISMarkerName = 'Left_PSIS'
self.LeftIliacMarkerName = 'Left_IliacCrest'
self.LeftThighMarkerName  = 'Left_Patella'
self.LeftLateralKneeMarkerName  = 'Left_Lateral_Knee'
self.LeftMedialKneeMarkerName = 'Left_Medial_Knee.Cal'
self.LeftTibialMarkerName  = 'Left_Lower_Tibia'
self.LeftTibialUpperMarkerName  = 'Left_Upper_Tibia'
self.LeftTibialLowerMarkerName  = 'Left_Lateral_Tibia'
self.LeftLateralAnkleMarkerName = 'Left_Lateral_Malleolus'
self.LeftToeMarkerName = 'Left_2nd3rd_MT_Head'
self.LeftMedialAnkleMarkerName = 'Left_Medial_Malleolus.Cal'
self.LeftHeelMarkerName = 'Left_Heel'
self.LeftLateralCalcaneusMarkerName = 'Left_Lateral_Calcaneus'
self.LeftPosteriorCalcaneusMarkerName = 'Left_Posterior_Calcaneus'
self.LeftMedialCalcaneusMarkerName = 'Left_Medial_Calcaneus'
self.LeftSuperiorCalcaneusMarkerName = 'Left_Superior_Calcaneus_Marker'
self.LeftFirstMetarsalBaseMarkerName = 'Left_1st_MT_Base'
self.LeftFirstMetarsalHeadMarkerName = 'Left_1st_MT_Head'
self.LeftFifthMetarsalHeadMarkerName = 'Left_5th_MT_Head'
self.LeftHalluxMarkerName = 'Left_Hallux'
self.Left23MetatarsalBaseMarkerName = 'Left_2nd3rd_MT_Base.Cal'
self.Left23MetatarsalHeadMarkerName = 'Left_2nd3rd_MT_Head.Cal'
self.LeftFirstMetatarsalMedialBaseMarkerName = 'Left_1st_MT_Medial_Base.Cal'
self.LeftFirstMetatarsalMedialHeadMarkerName = 'Left_1st_MT_Medial_Head.Cal'
self.LeftCalcanealPeronealTrochleaMarkerName = 'Left_Peroneal_Trochlea.Cal'
self.LeftFirstMetatarsoPhalangealJointMarkerName = 'Left_1st_MTP_Joint.Cal'
self.RightASISMarkerName = 'Right_ASIS'
self.RightPSISMarkerName = 'Right_PSIS'
self.RightIliacMarkerName = 'Right_Iliac_Crest'
self.RightThighMarkerName  = 'Right_Patella'
self.RightLateralKneeMarkerName  = 'Right_Lateral_Knee'
self.RightMedialKneeMarkerName = 'Right_Medial_Knee.Cal'
self.RightTibialMarkerName  = 'Right_Lower_Tibia'
self.RightTibialUpperMarkerName  = 'Right_Upper_Tibia'
self.RightTibialLowerMarkerName  = 'Right_Lateral_Tibia'
self.RightLateralAnkleMarkerName = 'Right_Lateral_Malleolus'
self.RightToeMarkerName = 'Right_2nd3rd_MT_Head'
self.RightMedialAnkleMarkerName = 'Right_Medial_Malleolus.Cal'
self.RightHeelMarkerName = 'Right_Heel'
self.RightLateralCalcaneusMarkerName = 'Right_Lateral_Calcaneus'
self.RightPosteriorCalcaneusMarkerName = 'Right_Posterior_Calcaneus'
self.RightMedialCalcaneusMarkerName = 'Right_Medial_Calcaneus'
self.RightSuperiorCalcaneusMarkerName = 'Right_Superior_Calcaneus_Marker'
self.RightFirstMetarsalBaseMarkerName = 'Right_1st_MT_Base'
self.RightFirstMetarsalHeadMarkerName = 'Right_1st_MT_Head'
self.RightFifthMetarsalHeadMarkerName = 'Right_5th_MT_Head'
self.RightHalluxMarkerName = 'Right_Hallux'
self.Right23MetatarsalBaseMarkerName = 'Right_2nd3rd_MT_Base.Cal'
self.Right23MetatarsalHeadMarkerName = 'Right_2nd3rd_MT_Head.Cal'
self.RightFirstMetatarsalMedialBaseMarkerName = 'Right_1st_MT_Medial_Base.Cal'
self.RightFirstMetatarsalMedialHeadMarkerName = 'Right_1st_MT_Medial_Head.Cal'
self.RightCalcanealPeronealTrochleaMarkerName = 'Right_Peroneal_Trochlea.Cal'
self.RightFirstMetatarsoPhalangealJointMarkerName = 'Right_1st_MTP_Joint.Cal'
self.LeftUpperKADMarkerName = 'Left_Upper_KAD.Cal'
self.LeftLowerKADMarkerName = 'Left_Lower_KAD.Cal'
self.LeftLateralKADMarkerName = 'Left_Lateral_KAD.Cal'
self.RightUpperKADMarkerName = 'Right_Upper_KAD.Cal'
self.RightLowerKADMarkerName = 'Right_Lower_KAD.Cal'
self.RightLateralKADMarkerName = 'Right_Lateral_KAD.Cal'
self.HindfootValgusIsNegative = True
self.PointerTipMarkerName = 'Pointer_Tip.Cal'
self.PointerTailMarkerName = 'Pointer_Tail.Cal'
self.PointerMarkerTipDistance = 127
self.LeftRectusFemorisEMGName     = 'EMG01 - L Rec'
self.LeftVasltusLateralisEMGName  = 'EMG03 - L V Lat'
self.LeftMedialHamstringsEMGName  = 'EMG05 - L Med Ham'
self.LeftGastrocnemiusEMGName     = 'EMG07 - L Gastroc'
self.LeftTibialisAnteriorEMGName  = 'EMG09 - L Tib Ant'
self.LeftGluteusMediusEMGName     = 'Sensor 1'
self.LeftGluteusMaximusEMGName    = 'Sensor 2'
self.LeftAdductorsEMGName         = 'Sensor 3'
self.LeftVasltusMedialisEMGName   = 'Sensor 4'
self.LeftLateralHamstringsEMGName = 'Sensor 5'
self.LeftPeroneusLongusEMGName    = 'Sensor 6'
self.RightRectusFemorisEMGName    = 'EMG02 - R Rec'
self.RightVasltusLateralisEMGName = 'EMG04 - R V Lat'
self.RightMedialHamstringsEMGName = 'EMG06 - R Med Ham'
self.RightGastrocnemiusEMGName    = 'EMG08 - R Gastroc'
self.RightTibialisAnteriorEMGName = 'EMG10 - R Tib Ant'
self.RightGluteusMediusEMGName    = 'Sensor 7'
self.RightAdductorsEMGName        = 'Sensor 8'
self.RightGluteusMaximusEMGName   = 'Sensor 9'
self.RightVasltusMedialisEMGName  = 'Sensor 10'
self.RightLateralHamstringsEMGName= 'Sensor 11'
self.RightPeroneusLongusEMGName   = 'Sensor 12'
"""



# ═══════════════════════════════════════════════════════════════════════
#  Reusable Card Widget — consistent section container
# ═══════════════════════════════════════════════════════════════════════

class _SectionCard(QFrame):
    """Styled card container matching the app's design language."""

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        self._layout.setSpacing(SPACE_SM)

        if title:
            lbl = QLabel(title)
            lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
            lbl.setObjectName("cardSectionTitle")
            self._layout.addWidget(lbl)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._layout

    def add_widget(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        self._layout.addLayout(layout)


class _AutoResizingStackedWidget(QStackedWidget):
    """
    QStackedWidget that dynamically adjusts its height based on the currently
    active page, preventing tall pages (e.g. 1800px forms) from expanding short pages.
    """
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.currentChanged.connect(self._on_page_changed)

    def _on_page_changed(self, index: int) -> None:
        curr = self.currentWidget()
        if curr is not None:
            if index == 0:
                self.setMinimumHeight(0)
                self.setMaximumHeight(16777215)
            else:
                h = curr.sizeHint().height()
                if h > 0:
                    self.setFixedHeight(h)
        self.updateGeometry()

        p = self.parentWidget()
        if p:
            if hasattr(p, "adjustSize"):
                p.adjustSize()
            if p.layout():
                p.layout().activate()

        # Find enclosing scroll area and scroll to top
        w = self.parentWidget()
        while w:
            if isinstance(w, QScrollArea):
                if hasattr(w, "scroll_to_top"):
                    w.scroll_to_top()
                else:
                    w.verticalScrollBar().setValue(0)
                break
            w = w.parentWidget()

    def sizeHint(self) -> QSize:
        curr = self.currentWidget()
        if curr is not None:
            return curr.sizeHint()
        return super().sizeHint()

    def minimumSizeHint(self) -> QSize:
        curr = self.currentWidget()
        if curr is not None:
            return curr.minimumSizeHint()
        return super().minimumSizeHint()


# ═══════════════════════════════════════════════════════════════════════
#  Static Analysis Page
# ═══════════════════════════════════════════════════════════════════════

class StaticAnalysisPage(QScrollArea):
    """
    Minimal, premium scientific static calibration interface.

    Matches the main app's PySide6 UI design with clean card sections,
    monochrome B&W palette, smooth animations, and responsive layout.
    """

    proceed_to_dynamic = Signal(str, str)  # session_xml_path, static_filename
    session_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setObjectName("staticAnalysisPage")

        self._data_root: str = ""
        self._is_dark: bool = False
        self._session_path: str = ""
        self._filename: str = ""
        self._subject_name: str = ""
        self._loaded_py_path: str = ""
        self._is_populating: bool = False
        self._analysis_generation = 0
        self._processing_slots = []

        # Background processing service
        self._service = GaitProcessingService()


        self._init_ui()
        from app.ui.widgets.smooth_scroll import apply_smooth_scroll
        self._smooth_scroll = apply_smooth_scroll(self)
        self._init_anthropometric_sync()
        self.clear_session()

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        """Update any custom components if needed when theme toggles."""
        self._is_dark = dark
        pal = palette or (DARK_PALETTE if dark else LIGHT_PALETTE)
        if hasattr(self, "_browse_btn"):
            self._browse_btn.setIcon(create_tinted_icon("folder.svg", pal.text_secondary, 15))
        self._update_data_root_display()

    def _init_ui(self) -> None:
        container = QWidget()
        self.setWidget(container)

        self._main_layout = QVBoxLayout(container)
        self._main_layout.setContentsMargins(SPACE_XL * 2, SPACE_XL, SPACE_XL * 2, SPACE_XL * 2)
        self._main_layout.setSpacing(SPACE_LG)

        # ── Header ─────────────────────────────────────────────────────────
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        header_title = QLabel("STATIC ANALYSIS")
        header_title.setObjectName("pageHeaderTitle")
        header_title.setFont(QFont(FONT_FAMILY, FONT_SIZE_H2, QFont.Bold))
        header_layout.addWidget(header_title)

        header_sub = QLabel("Establish reference anatomical calibration and joint centers for this session")
        header_sub.setObjectName("pageHeaderSub")
        header_sub.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        header_layout.addWidget(header_sub)

        self._main_layout.addLayout(header_layout)

        # ── State Stack (Ready / Processing / Complete) ─────────────────────
        self._stack = _AutoResizingStackedWidget()

        # Page 0: Configuration & Ready State
        self._config_widget = self._create_config_view()
        self._stack.addWidget(self._config_widget)

        # Page 1: Processing State
        self._processing_widget = self._create_processing_view()
        self._stack.addWidget(self._processing_widget)

        # Page 2: Completion State
        self._completion_widget = self._create_completion_view()
        self._stack.addWidget(self._completion_widget)

        self._main_layout.addWidget(self._stack)
        self._main_layout.addStretch()

    # ═══════════════════════════════════════════════════════════════════
    #  View 1: Configuration & File Selection
    # ═══════════════════════════════════════════════════════════════════

    def _create_config_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_LG)

        # ── 1. Calibration File Card ────────────────────────────────────
        file_card = _SectionCard("CALIBRATION TRIAL")
        file_input_row = QHBoxLayout()
        file_input_row.setSpacing(SPACE_SM)

        self._file_path_edit = QLineEdit()
        self._file_path_edit.setPlaceholderText("Select static calibration trial (.c3d, .qtm, session.xml)...")
        self._file_path_edit.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
        self._file_path_edit.textChanged.connect(self._on_path_changed)
        file_input_row.addWidget(self._file_path_edit, 1)

        self._browse_btn = QPushButton(" Browse Data…")
        self._browse_btn.setObjectName("secondaryButton")
        self._browse_btn.setIcon(create_tinted_icon("folder.svg", LIGHT_PALETTE.text_secondary, 15))
        self._browse_btn.setIconSize(QSize(15, 15))
        self._browse_btn.setCursor(Qt.PointingHandCursor)
        self._browse_btn.setToolTip("Browse and select static calibration trial from global data folder")
        self._browse_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_MEDIUM))
        self._browse_btn.clicked.connect(self._browse_static_file)
        file_input_row.addWidget(self._browse_btn)

        file_card.add_layout(file_input_row)

        # Data Root badge indicator row
        data_root_row = QHBoxLayout()
        data_root_row.setContentsMargins(SPACE_XS, 0, 0, 0)
        data_root_row.setSpacing(6)

        self._data_root_icon = QLabel()
        self._data_root_icon.setFixedSize(14, 14)
        self._data_root_icon.setStyleSheet("background: transparent; border: none;")
        data_root_row.addWidget(self._data_root_icon)

        self._data_root_label = QLabel("")
        self._data_root_label.setObjectName("captionLabel")
        self._data_root_label.setStyleSheet(
            f"font-size: {FONT_SIZE_CAPTION}px; color: {LIGHT_PALETTE.text_muted}; background: transparent; border: none;"
        )
        data_root_row.addWidget(self._data_root_label, 1)
        file_card.add_layout(data_root_row)

        layout.addWidget(file_card)

        # ── 2. Patient Information Card ─────────────────────────────────
        patient_card = _SectionCard("PATIENT INFORMATION")
        p_grid = QGridLayout()
        p_grid.setSpacing(SPACE_SM)
        p_grid.setColumnStretch(1, 1)
        p_grid.setColumnStretch(3, 1)

        # Row 0: First Name / Last Name
        p_grid.addWidget(self._create_field_label("First Name"), 0, 0, Qt.AlignRight)
        self._first_name = QLineEdit()
        self._first_name.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        p_grid.addWidget(self._first_name, 0, 1)

        p_grid.addWidget(self._create_field_label("Last Name"), 0, 2, Qt.AlignRight)
        self._last_name = QLineEdit()
        self._last_name.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        self._last_name.setToolTip("Local static configuration only: this QTM PAF has no separate last-name field.")
        p_grid.addWidget(self._last_name, 0, 3)

        # Row 1: Patient Number / Date of Birth
        p_grid.addWidget(self._create_field_label("Patient Number"), 1, 0, Qt.AlignRight)
        self._patient_number = QLineEdit()
        self._patient_number.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        p_grid.addWidget(self._patient_number, 1, 1)

        p_grid.addWidget(self._create_field_label("Date of Birth"), 1, 2, Qt.AlignRight)
        dob_row = QHBoxLayout()
        dob_row.setSpacing(SPACE_XS)
        self._dob_day = QComboBox()
        self._dob_day.addItems([f"{i:02d}" for i in range(1, 32)])
        self._style_combo(self._dob_day)
        self._dob_day.setFixedWidth(65)
        dob_row.addWidget(self._dob_day)

        self._dob_month = QComboBox()
        self._dob_month.addItems(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        self._style_combo(self._dob_month)
        self._dob_month.setFixedWidth(70)
        dob_row.addWidget(self._dob_month)

        self._dob_year = QComboBox()
        self._dob_year.addItems([str(y) for y in range(1930, 2036)])
        self._style_combo(self._dob_year)
        self._dob_year.setFixedWidth(80)
        dob_row.addWidget(self._dob_year)
        dob_row.addStretch()
        p_grid.addLayout(dob_row, 1, 3)

        # Row 2: Trial Activity / Trial Modifier
        p_grid.addWidget(self._create_field_label("Trial Activity"), 2, 0, Qt.AlignRight)
        self._trial_activity = QComboBox()
        self._trial_activity.addItems([
            "Static", "Walking - Fast", "Walking - Heel-Toe", "Running",
            "Sprinting", "Stair Ascent", "Stair Descent", "Sit-To-Stand", "Other"
        ])
        self._style_combo(self._trial_activity)
        p_grid.addWidget(self._trial_activity, 2, 1)

        p_grid.addWidget(self._create_field_label("Trial Modifier"), 2, 2, Qt.AlignRight)
        self._trial_modifier = QComboBox()
        self._trial_modifier.addItems([
            "Barefoot", "B AFO-PLS", "L AFO-PLS", "R AFO-PLS",
            "B AFO-Solid", "L AFO-Solid", "R AFO-Solid",
            "B AFO-FR", "L AFO-FR", "R AFO-FR",
            "B AFO-Artic", "L AFO-Artic", "R AFO-Artic",
            "L LIFT", "R LIFT",
            "B SMO", "L SMO", "R SMO",
            "B UCBL", "L UCBL", "R UCBL",
            "KAFO", "HKAFO", "RGO", "Parawalker",
            "Shoes Only", "Other"
        ])
        self._style_combo(self._trial_modifier)
        p_grid.addWidget(self._trial_modifier, 2, 3)

        # Row 3: Static Fwd Dir / Assistive Device
        p_grid.addWidget(self._create_field_label("Static Fwd Dir"), 3, 0, Qt.AlignRight)
        self._fwd_dir = QComboBox()
        self._fwd_dir.addItems(["+X", "-X", "+Y", "-Y"])
        self._style_combo(self._fwd_dir)
        p_grid.addWidget(self._fwd_dir, 3, 1)

        p_grid.addWidget(self._create_field_label("Assistive Device"), 3, 2, Qt.AlignRight)
        self._assistive_device = QComboBox()
        self._assistive_device.addItems([
            "None", "Walker", "Walker - Wheeled", "Walker - Pickup",
            "Crutches", "Crutches - Axillary", "Crutches - Loftstrand",
            "Cane", "Bobath Poles", "Hand-Held", "Other"
        ])
        self._style_combo(self._assistive_device)
        p_grid.addWidget(self._assistive_device, 3, 3)

        # Row 4: Static Frame Number
        p_grid.addWidget(self._create_field_label("Sex"), 4, 0, Qt.AlignRight)
        self._sex = QComboBox()
        self._sex.addItems(["", "Female", "Male", "Other"])
        self._style_combo(self._sex)
        p_grid.addWidget(self._sex, 4, 1)
        p_grid.addWidget(self._create_field_label("Static Frame Num."), 4, 2, Qt.AlignRight)
        self._static_frame_num = QLineEdit("20")
        self._static_frame_num.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
        self._static_frame_num.setAlignment(Qt.AlignCenter)
        self._static_frame_num.setFixedWidth(100)
        p_grid.addWidget(self._static_frame_num, 4, 3, Qt.AlignLeft)

        self._metadata_status = QLabel("QTM patient metadata has not been verified yet.")
        self._metadata_status.setWordWrap(True)
        self._metadata_status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self._metadata_status.setObjectName("captionLabel")
        p_grid.addWidget(self._metadata_status, 5, 0, 1, 4)

        patient_card.add_layout(p_grid)
        layout.addWidget(patient_card)

        # ── 3. Anthropometric Parameters Card ───────────────────────────
        anthro_card = _SectionCard("ANTHROPOMETRIC PARAMETERS")
        a_grid = QGridLayout()
        a_grid.setSpacing(SPACE_SM)
        a_grid.setColumnStretch(1, 1)
        a_grid.setColumnStretch(3, 1)

        # Row 0: Static File / Anthro File
        a_grid.addWidget(self._create_field_label("Static File"), 0, 0, Qt.AlignRight)
        self._static_file_display = QLineEdit()
        self._static_file_display.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
        self._static_file_display.setReadOnly(True)
        a_grid.addWidget(self._static_file_display, 0, 1)

        a_grid.addWidget(self._create_field_label("Anthro File"), 0, 2, Qt.AlignRight)
        self._anthro_file_label = QLabel("—")
        self._anthro_file_label.setObjectName("valueLabel")
        self._anthro_file_label.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_CAPTION))
        a_grid.addWidget(self._anthro_file_label, 0, 3)

        # Row 1: Date Captured
        a_grid.addWidget(self._create_field_label("Date Captured"), 1, 0, Qt.AlignRight)
        date_row = QHBoxLayout()
        date_row.setSpacing(SPACE_XS)
        now = datetime.datetime.now()
        self._cap_day = QComboBox()
        self._cap_day.addItems([f"{i:02d}" for i in range(1, 32)])
        self._cap_day.setCurrentIndex(now.day - 1)
        self._style_combo(self._cap_day)
        self._cap_day.setFixedWidth(65)
        date_row.addWidget(self._cap_day)

        self._cap_month = QComboBox()
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        self._cap_month.addItems(month_names)
        self._cap_month.setCurrentIndex(now.month - 1)
        self._style_combo(self._cap_month)
        self._cap_month.setFixedWidth(70)
        date_row.addWidget(self._cap_month)

        self._cap_year = QComboBox()
        self._cap_year.addItems([str(y) for y in range(1990, 2036)])
        yr_idx = now.year - 1990
        if 0 <= yr_idx < self._cap_year.count():
            self._cap_year.setCurrentIndex(yr_idx)
        self._style_combo(self._cap_year)
        self._cap_year.setFixedWidth(80)
        date_row.addWidget(self._cap_year)
        date_row.addStretch()
        a_grid.addLayout(date_row, 1, 1, 1, 3)

        # Row 2: Body Mass / Height
        a_grid.addWidget(self._create_field_label("Body Mass (kg)"), 2, 0, Qt.AlignRight)
        self._body_mass = QLineEdit()
        self._body_mass.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
        self._body_mass.setAlignment(Qt.AlignCenter)
        a_grid.addWidget(self._body_mass, 2, 1)

        a_grid.addWidget(self._create_field_label("Height (m)"), 2, 2, Qt.AlignRight)
        self._height = QLineEdit()
        self._height.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
        self._height.setAlignment(Qt.AlignCenter)
        a_grid.addWidget(self._height, 2, 3)

        # Row 3: ASIS-to-ASIS
        a_grid.addWidget(self._create_field_label("ASIS-to-ASIS (m)"), 3, 0, Qt.AlignRight)
        self._asis_dist = QLineEdit()
        self._asis_dist.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
        self._asis_dist.setAlignment(Qt.AlignCenter)
        a_grid.addWidget(self._asis_dist, 3, 1)

        # Row 4: Left / Right Headers
        left_header = QLabel("Left")
        left_header.setObjectName("fieldLabel")
        left_header.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        left_header.setAlignment(Qt.AlignCenter)
        a_grid.addWidget(left_header, 4, 1)

        right_header = QLabel("Right")
        right_header.setObjectName("fieldLabel")
        right_header.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        right_header.setAlignment(Qt.AlignCenter)
        a_grid.addWidget(right_header, 4, 3)

        # Row 5–8: Bilateral measurements
        bilateral_fields = [
            ("Leg Length (m)", "leg_length"),
            ("Knee Width (m)", "knee_width"),
            ("Ankle Width (m)", "ankle_width"),
            ("ASIS-to-GT (m)", "asis_gt"),
        ]
        self._anthro_inputs = {}
        for i, (label_text, key) in enumerate(bilateral_fields):
            row = 5 + i
            a_grid.addWidget(self._create_field_label(label_text), row, 0, Qt.AlignRight)

            left_edit = QLineEdit()
            left_edit.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
            left_edit.setAlignment(Qt.AlignCenter)
            a_grid.addWidget(left_edit, row, 1)

            right_edit = QLineEdit()
            right_edit.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
            right_edit.setAlignment(Qt.AlignCenter)
            a_grid.addWidget(right_edit, row, 3)

            self._anthro_inputs[f"left_{key}"] = left_edit
            self._anthro_inputs[f"right_{key}"] = right_edit

        anthro_card.add_layout(a_grid)
        layout.addWidget(anthro_card)

        # ── 4. Foot Model Card ──────────────────────────────────────────
        foot_card = _SectionCard("FOOT MODEL")
        f_grid = QGridLayout()
        f_grid.setSpacing(SPACE_SM)
        f_grid.setColumnStretch(1, 1)
        f_grid.setColumnStretch(3, 1)

        # Row 0: Left / Right checkboxes
        self._left_foot_check = QCheckBox("Left")
        self._left_foot_check.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        f_grid.addWidget(self._left_foot_check, 0, 1, Qt.AlignCenter)

        self._right_foot_check = QCheckBox("Right")
        self._right_foot_check.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        f_grid.addWidget(self._right_foot_check, 0, 3, Qt.AlignCenter)

        # Foot model measurements
        foot_fields = [
            ("Hindfoot Varus/Valgus (deg)", "hindfoot_varus"),
            ("Calcaneal Pitch (deg)", "calcaneal_pitch"),
            ("Hindfoot Progression (deg)", "hindfoot_progression"),
            ("1st Metatarsal Pitch (deg)", "first_metatarsal_pitch"),
        ]
        self._foot_inputs = {}
        for i, (label_text, key) in enumerate(foot_fields):
            row = 1 + i
            f_grid.addWidget(self._create_field_label(label_text), row, 0, Qt.AlignRight)

            left_edit = QLineEdit()
            left_edit.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
            left_edit.setAlignment(Qt.AlignCenter)
            f_grid.addWidget(left_edit, row, 1)

            right_edit = QLineEdit()
            right_edit.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
            right_edit.setAlignment(Qt.AlignCenter)
            f_grid.addWidget(right_edit, row, 3)

            self._foot_inputs[f"left_{key}"] = left_edit
            self._foot_inputs[f"right_{key}"] = right_edit

        foot_card.add_layout(f_grid)
        layout.addWidget(foot_card)

        # ── 5. Special Test Conditions Card ─────────────────────────────
        cond_card = _SectionCard("SPECIAL TEST CONDITIONS")
        c_grid = QGridLayout()
        c_grid.setSpacing(SPACE_SM)
        c_grid.setColumnStretch(1, 1)
        c_grid.setColumnStretch(2, 1)

        # Row 0: Subject Plantigrade
        c_grid.addWidget(self._create_field_label("Subject Plantigrade:"), 0, 0, Qt.AlignRight)
        plantigrade_row = QHBoxLayout()
        plantigrade_row.setSpacing(SPACE_MD)
        self._left_plantigrade = QCheckBox("Left")
        self._left_plantigrade.setChecked(True)
        self._left_plantigrade.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        plantigrade_row.addWidget(self._left_plantigrade)

        self._right_plantigrade = QCheckBox("Right")
        self._right_plantigrade.setChecked(True)
        self._right_plantigrade.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        plantigrade_row.addWidget(self._right_plantigrade)
        plantigrade_row.addStretch()
        c_grid.addLayout(plantigrade_row, 0, 1, 1, 2)

        # Row 1: Subject Shod + Sole Thickness
        self._subject_shod = QCheckBox("Subject Shod")
        self._subject_shod.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        c_grid.addWidget(self._subject_shod, 1, 0, Qt.AlignRight)

        sole_row = QHBoxLayout()
        sole_row.setSpacing(SPACE_XS)
        sole_lbl = QLabel("Sole Diff (m):")
        sole_lbl.setObjectName("fieldLabel")
        sole_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION))
        sole_row.addWidget(sole_lbl)

        l_sole_lbl = QLabel("L:")
        l_sole_lbl.setObjectName("fieldLabel")
        l_sole_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        sole_row.addWidget(l_sole_lbl)
        self._left_sole = QLineEdit()
        self._left_sole.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
        self._left_sole.setAlignment(Qt.AlignCenter)
        self._left_sole.setFixedWidth(70)
        sole_row.addWidget(self._left_sole)

        r_sole_lbl = QLabel("R:")
        r_sole_lbl.setObjectName("fieldLabel")
        r_sole_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        sole_row.addWidget(r_sole_lbl)
        self._right_sole = QLineEdit()
        self._right_sole.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
        self._right_sole.setAlignment(Qt.AlignCenter)
        self._right_sole.setFixedWidth(70)
        sole_row.addWidget(self._right_sole)
        sole_row.addStretch()
        c_grid.addLayout(sole_row, 1, 1, 1, 2)

        # Row 2: Knee Option
        c_grid.addWidget(self._create_field_label("Knee Option:"), 2, 0, Qt.AlignRight)
        knee_row = QHBoxLayout()
        knee_row.setSpacing(SPACE_MD)
        self._knee_group = QButtonGroup(self)
        self._knee_kad = QRadioButton("KAD")
        self._knee_kad.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        self._knee_ml = QRadioButton("M/L Markers")
        self._knee_ml.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        self._knee_ml.setChecked(True)
        self._knee_group.addButton(self._knee_kad, 0)
        self._knee_group.addButton(self._knee_ml, 1)
        knee_row.addWidget(self._knee_kad)
        knee_row.addWidget(self._knee_ml)
        knee_row.addStretch()
        c_grid.addLayout(knee_row, 2, 1, 1, 2)

        # Row 3: Pelvic Fix
        c_grid.addWidget(self._create_field_label("Pelvic Fix:"), 3, 0, Qt.AlignRight)
        pelvic_row = QHBoxLayout()
        pelvic_row.setSpacing(SPACE_MD)
        self._pelvic_group = QButtonGroup(self)
        self._pelvic_na = QRadioButton("N/A")
        self._pelvic_na.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        self._pelvic_na.setChecked(True)
        self._pelvic_iliac = QRadioButton("Iliac")
        self._pelvic_iliac.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        self._pelvic_triad = QRadioButton("Triad")
        self._pelvic_triad.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        self._pelvic_group.addButton(self._pelvic_na, 0)
        self._pelvic_group.addButton(self._pelvic_iliac, 1)
        self._pelvic_group.addButton(self._pelvic_triad, 2)
        pelvic_row.addWidget(self._pelvic_na)
        pelvic_row.addWidget(self._pelvic_iliac)
        pelvic_row.addWidget(self._pelvic_triad)
        pelvic_row.addStretch()
        c_grid.addLayout(pelvic_row, 3, 1, 1, 2)

        cond_card.add_layout(c_grid)
        layout.addWidget(cond_card)

        # ── 6. Model Configuration (collapsible) ───────────────────────
        self._model_toggle = QPushButton("▸ Model Configuration (Hip Joint, Coordinate System, Marker Set)")
        self._model_toggle.setObjectName("linkToggle")
        self._model_toggle.setCheckable(True)
        self._model_toggle.setChecked(False)
        self._model_toggle.setCursor(Qt.PointingHandCursor)
        self._model_toggle.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_SEMIBOLD))
        self._model_toggle.clicked.connect(self._toggle_model_config)
        layout.addWidget(self._model_toggle)

        self._model_box = _SectionCard()
        self._model_box.setVisible(False)
        m_grid = QGridLayout()
        m_grid.setSpacing(SPACE_MD)

        # Hip Model
        m_grid.addWidget(self._create_field_label("Hip Joint Center Model"), 0, 0)
        self._hip_combo = QComboBox()
        self._hip_combo.addItem("Harrington 2 (Predictive)", "Harrington2")
        self._hip_combo.addItem("Harrington (Classic)", "Harrington")
        self._hip_combo.addItem("Newington (Davis / Helen Hayes)", "Newington")
        self._style_combo(self._hip_combo)
        m_grid.addWidget(self._hip_combo, 1, 0)

        # Coordinate System
        m_grid.addWidget(self._create_field_label("Coordinate System"), 0, 1)
        self._coord_combo = QComboBox()
        self._coord_combo.addItem("Distal (Standard Shriners)", "Distal")
        self._coord_combo.addItem("Proximal", "Proximal")
        self._style_combo(self._coord_combo)
        m_grid.addWidget(self._coord_combo, 1, 1)

        # Marker Configuration
        m_grid.addWidget(self._create_field_label("Marker Set Configuration"), 2, 0)
        self._marker_combo = QComboBox()
        self._marker_combo.addItems([
            "Standard Shriners Lower Body Marker Set (34 Markers)",
            "Shriners Full Body with Trunk & Arms",
            "Modified Helen Hayes Set",
        ])
        self._style_combo(self._marker_combo)
        m_grid.addWidget(self._marker_combo, 3, 0)

        # Foot Model Type
        m_grid.addWidget(self._create_field_label("Foot Model"), 2, 1)
        self._foot_model_combo = QComboBox()
        self._foot_model_combo.addItems(["Normal (Single Rigid Body)", "Leardini Multi-Segment Foot Model"])
        self._style_combo(self._foot_model_combo)
        m_grid.addWidget(self._foot_model_combo, 3, 1)

        self._model_box.add_layout(m_grid)
        layout.addWidget(self._model_box)

        # ── 7. Action Row ───────────────────────────────────────────────
        action_layout = QHBoxLayout()
        action_layout.setSpacing(SPACE_SM)

        # Status text
        self._config_status = QLabel("")
        self._config_status.setObjectName("pageHeaderSub")
        self._config_status.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION))
        self._config_status.setWordWrap(True)
        self._config_status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        action_layout.addWidget(self._config_status, 1)

        self._sync_details_btn = QPushButton("Details")
        self._sync_details_btn.setObjectName("secondaryButton")
        self._sync_details_btn.clicked.connect(self._show_sync_details)
        self._sync_details_btn.hide()
        action_layout.addWidget(self._sync_details_btn)

        self._save_btn = QPushButton("Save Parameters")
        self._save_btn.setObjectName("secondaryButton")
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_MEDIUM))
        self._save_btn.clicked.connect(self._on_save_clicked)
        self._save_btn.setToolTip("Save the current calibration parameters locally for this session.")
        action_layout.addWidget(self._save_btn)

        self._fetch_btn = QPushButton("Fetch QTM")
        self._fetch_btn.setObjectName("secondaryButton")
        self._fetch_btn.setCursor(Qt.PointingHandCursor)
        self._fetch_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_MEDIUM))
        self._fetch_btn.setToolTip("Read the session of QTM's open measurement; otherwise use the selected session folder.")
        self._fetch_btn.clicked.connect(self._on_fetch_clicked)
        action_layout.addWidget(self._fetch_btn)

        self._run_btn = QPushButton("Save & Run Static Analysis")
        self._run_btn.setObjectName("primaryButton")
        self._run_btn.setCursor(Qt.PointingHandCursor)
        self._run_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        self._run_btn.clicked.connect(self._on_run_clicked)
        action_layout.addWidget(self._run_btn)

        layout.addLayout(action_layout)
        return view

    # ═══════════════════════════════════════════════════════════════════
    #  View 2: Processing State
    # ═══════════════════════════════════════════════════════════════════

    def _create_processing_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_LG)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(SPACE_LG)
        card_layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)

        # Header
        p_title = QLabel("STATIC ANALYSIS")
        p_title.setObjectName("cardSectionTitle")
        p_title.setFont(QFont(FONT_FAMILY, FONT_SIZE_H3, QFont.Bold))
        card_layout.addWidget(p_title)

        self._p_subtitle = QLabel("Processing calibration...")
        self._p_subtitle.setObjectName("pageHeaderSub")
        self._p_subtitle.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        card_layout.addWidget(self._p_subtitle)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        card_layout.addWidget(self._progress_bar)

        # Details
        details_box = QVBoxLayout()
        details_box.setSpacing(4)

        det_lbl = QLabel("Current Status:")
        det_lbl.setObjectName("fieldLabel")
        det_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, QFont.Bold))
        details_box.addWidget(det_lbl)

        self._step_desc = QLabel("Analyzing marker trajectories...")
        self._step_desc.setObjectName("valueLabel")
        self._step_desc.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_BODY))
        self._step_desc.setWordWrap(True)
        details_box.addWidget(self._step_desc)

        self._live_status = QLabel("● Processing")
        self._live_status.setObjectName("badge")
        self._live_status.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION))
        details_box.addWidget(self._live_status)

        card_layout.addLayout(details_box)

        # Cancel button
        cancel_row = QHBoxLayout()
        cancel_row.addStretch()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("secondaryButton")
        self._cancel_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        cancel_row.addWidget(self._cancel_btn)
        card_layout.addLayout(cancel_row)

        layout.addWidget(card)
        layout.addStretch(1)
        return view

    # ═══════════════════════════════════════════════════════════════════
    #  View 3: Completion State
    # ═══════════════════════════════════════════════════════════════════

    def _create_completion_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_LG)

        # ── Card 1: Success Hero Card ──────────────────────────────────────
        hero_card = QFrame()
        hero_card.setObjectName("card")
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        hero_layout.setSpacing(SPACE_MD)

        top_row = QHBoxLayout()
        top_row.setSpacing(SPACE_MD)

        icon_badge = QLabel("✓")
        icon_badge.setFixedSize(38, 38)
        icon_badge.setAlignment(Qt.AlignCenter)
        icon_badge.setFont(QFont(FONT_FAMILY, 18, QFont.Bold))
        icon_badge.setStyleSheet("background-color: #0F766E; color: #FFFFFF; border-radius: 19px;")
        top_row.addWidget(icon_badge)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel("STATIC CALIBRATION COMPLETE")
        title_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_H3, QFont.Bold))
        title_lbl.setStyleSheet("color: #0F766E;")
        title_col.addWidget(title_lbl)

        self._comp_subtitle = QLabel("Static trial processed successfully. Anatomical reference frames established.")
        self._comp_subtitle.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        self._comp_subtitle.setStyleSheet("color: #64748B;")
        title_col.addWidget(self._comp_subtitle)
        top_row.addLayout(title_col, 1)

        status_badge = QLabel("● Reference Locked")
        status_badge.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, QFont.Bold))
        status_badge.setStyleSheet(
            "background-color: #F0FDFA; color: #0F766E; border: 1px solid #14B8A6; border-radius: 12px; padding: 4px 12px;"
        )
        top_row.addWidget(status_badge, alignment=Qt.AlignVCenter)
        hero_layout.addLayout(top_row)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #E2E8F0; border: none;")
        hero_layout.addWidget(sep)

        msg_lbl = QLabel(
            "Anatomical coordinate systems, joint centers (Hip, Knee, Ankle), and segment lengths have been calculated and saved to the session database.\nData is ready for Dynamic Walking Analysis."
        )
        msg_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        msg_lbl.setStyleSheet("color: #0F172A; line-height: 1.4;")
        msg_lbl.setWordWrap(True)
        hero_layout.addWidget(msg_lbl)

        layout.addWidget(hero_card)

        # ── Card 2: Parameters Summary Grid Card ───────────────────────────
        param_card = QFrame()
        param_card.setObjectName("card")
        p_layout = QVBoxLayout(param_card)
        p_layout.setContentsMargins(SPACE_XL, SPACE_LG, SPACE_XL, SPACE_LG)
        p_layout.setSpacing(SPACE_MD)

        sec_title = QLabel("CALIBRATION PARAMETERS SUMMARY")
        sec_title.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        sec_title.setStyleSheet("color: #64748B; letter-spacing: 0.8px;")
        p_layout.addWidget(sec_title)

        grid = QGridLayout()
        grid.setSpacing(SPACE_MD)

        def add_summary_cell(r: int, c: int, title: str, default_val: str) -> QLabel:
            lbl_t = QLabel(title)
            lbl_t.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, QFont.Bold))
            lbl_t.setStyleSheet("color: #64748B; letter-spacing: 0.5px;")
            lbl_v = QLabel(default_val)
            lbl_v.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.DemiBold))
            lbl_v.setStyleSheet("color: #0F172A;")
            grid.addWidget(lbl_t, r, c)
            grid.addWidget(lbl_v, r + 1, c)
            return lbl_v

        self._comp_trial_lbl = add_summary_cell(0, 0, "CALIBRATION TRIAL", "—")
        self._comp_patient_lbl = add_summary_cell(0, 1, "PATIENT / MRN", "—")
        self._comp_activity_lbl = add_summary_cell(0, 2, "ACTIVITY / MODIFIER", "—")

        self._comp_frame_lbl = add_summary_cell(2, 0, "CALIBRATION FRAME", "Frame 20")
        self._comp_hjc_lbl = add_summary_cell(2, 1, "HIP JOINT MODEL", "Harrington")
        self._comp_coord_lbl = add_summary_cell(2, 2, "KINEMATIC MODEL", "Standard Shriners (ISB)")

        p_layout.addLayout(grid)
        layout.addWidget(param_card)

        # ── Card 3: Action Bar Card ────────────────────────────────────────
        act_card = QFrame()
        act_card.setObjectName("card")
        act_layout = QHBoxLayout(act_card)
        act_layout.setContentsMargins(SPACE_LG, SPACE_MD, SPACE_LG, SPACE_MD)
        act_layout.setSpacing(SPACE_MD)

        recal_btn = QPushButton("← Edit Calibration / Re-run")
        recal_btn.setObjectName("secondaryButton")
        recal_btn.setCursor(Qt.PointingHandCursor)
        recal_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_MEDIUM))
        recal_btn.clicked.connect(lambda: self._stack.setCurrentWidget(self._config_widget))
        act_layout.addWidget(recal_btn)

        act_layout.addStretch()

        self._continue_btn = QPushButton("Continue to Dynamic Analysis →")
        self._continue_btn.setObjectName("primaryButton")
        self._continue_btn.setCursor(Qt.PointingHandCursor)
        self._continue_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        self._continue_btn.clicked.connect(self._on_continue_clicked)
        act_layout.addWidget(self._continue_btn)

        layout.addWidget(act_card)
        layout.addStretch(1)

        return view

    # ═══════════════════════════════════════════════════════════════════
    #  Helpers & Styling
    # ═══════════════════════════════════════════════════════════════════

    def _create_field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("fieldLabel")
        lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, FONT_WEIGHT_MEDIUM))
        return lbl

    def _style_combo(self, combo: QComboBox) -> None:
        combo.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))

    def _toggle_model_config(self) -> None:
        checked = self._model_toggle.isChecked()
        self._model_box.setVisible(checked)
        prefix = "▾" if checked else "▸"
        self._model_toggle.setText(f"{prefix} Model Configuration (Hip Joint, Coordinate System, Marker Set)")

    # ═══════════════════════════════════════════════════════════════════
    #  Public API & Session Loading
    # ═══════════════════════════════════════════════════════════════════

    def set_data_root(self, data_root: str) -> None:
        self._data_root = str(data_root).strip() if data_root else ""
        self._update_data_root_display()

    def _update_data_root_display(self) -> None:
        if not hasattr(self, "_data_root_label") or not hasattr(self, "_data_root_icon"):
            return
        pal = DARK_PALETTE if self._is_dark else LIGHT_PALETTE
        if self._data_root and os.path.isdir(self._data_root):
            self._data_root_icon.setPixmap(create_tinted_pixmap("folder.svg", pal.text_muted, 14))
            self._data_root_icon.setVisible(True)
            self._data_root_label.setText(f"Data Root: {self._data_root}")
            self._data_root_label.setToolTip(self._data_root)
        elif self._data_root:
            self._data_root_icon.setPixmap(create_tinted_pixmap("alert.svg", "#F59E0B", 14))
            self._data_root_icon.setVisible(True)
            self._data_root_label.setText(f"Data Root path not found: {self._data_root}")
            self._data_root_label.setToolTip(self._data_root)
        else:
            self._data_root_icon.setPixmap(create_tinted_pixmap("alert.svg", "#9CA3AF", 14))
            self._data_root_icon.setVisible(True)
            self._data_root_label.setText("Configure Patients Data Location in Settings")
            self._data_root_label.setToolTip("Set Patients Data Location under Settings -> File Paths")
        self._data_root_label.setStyleSheet(
            f"font-size: {FONT_SIZE_CAPTION}px; color: {pal.text_muted}; background: transparent; border: none;"
        )





    def set_session(self, session_path: str, filename: str | None = None) -> None:
        """Load an explicitly chosen session; results require fresh processing."""
        path = Path(session_path).resolve()
        if path.suffix.lower() != ".xml":
            self._anthro_status("Choose an XML calibration/session file.", error=True)
            return
        try:
            root = ET.parse(path).getroot()
            if root.find("Fields") is None or (root.tag != "Session" and root.get("Type") != "Session"):
                raise ValueError("Expected a session XML containing Fields.")
        except (OSError, ET.ParseError, ValueError) as error:
            self._anthro_status(f"Could not load calibration XML: {error}", error=True)
            return
        if (self._session_path and os.path.normcase(str(Path(self._session_path).resolve())) == os.path.normcase(str(path))
                and (filename is None or filename == self._filename)):
            return
        self.clear_session()
        self._session_path = str(path)
        self._filename = filename or ""
        with QSignalBlocker(self._file_path_edit):
            self._file_path_edit.setText(str(path))
        self._on_path_changed(str(path))
        self._set_calibration_enabled(True)
        self.session_selected.emit(self._session_path)

    def _set_calibration_enabled(self, enabled):
        for widget in (self._config_widget.findChildren(QLineEdit) + self._config_widget.findChildren(QComboBox)
                       + self._config_widget.findChildren(QCheckBox) + self._config_widget.findChildren(QRadioButton)):
            if widget is not self._file_path_edit:
                if isinstance(widget, QLineEdit):
                    widget.setReadOnly(not enabled)
                widget.setEnabled(enabled)
        self._save_btn.setEnabled(enabled)
        self._fetch_btn.setEnabled(enabled)
        self._run_btn.setEnabled(enabled and bool(self._filename))

    def _bind_processing_context(self):
        for signal, slot in self._processing_slots:
            signal.disconnect(slot)
        self._processing_slots = []
        for signal, handler in ((self._service.processing_started, self._on_started),
                                (self._service.processing_progress, self._on_progress),
                                (self._service.processing_finished, self._on_finished),
                                (self._service.processing_error, self._on_error)):
            slot = lambda value, g=self._analysis_generation, h=handler: h(value) if g == self._analysis_generation else None
            signal.connect(slot)
            self._processing_slots.append((signal, slot))

    def clear_session(self):
        self._analysis_generation += 1
        self._service.invalidate()
        self._bind_processing_context()
        self._anthro_sync.cancel()
        self._anthro_sync.operation = None
        self._anthro_generation += 1
        self._anthro_context = None
        self._anthro_connected = False
        self._anthro_dirty.clear()
        self._manual_baseline.clear()
        self._manual_requested_identity = {}
        self._manual_inflight_values = {}
        self._anthro_inflight_revisions = {}
        self._auto_sync_timer.stop()
        self._manual_local_dirty = False
        self._session_path = self._filename = self._subject_name = self._loaded_py_path = ""
        self._is_populating = True
        try:
            for widget in self._config_widget.findChildren(QLineEdit):
                widget.clear()
            for widget in self._config_widget.findChildren(QComboBox):
                widget.setCurrentIndex(0)
            for widget in self._config_widget.findChildren(QCheckBox):
                widget.setChecked(False)
            self._knee_kad.setChecked(True)
            self._pelvic_na.setChecked(True)
            for widget in (self._sex, self._dob_day, self._dob_month, self._dob_year,
                           self._cap_day, self._cap_month, self._cap_year):
                widget.setCurrentIndex(-1)
        finally:
            self._is_populating = False
        self._static_file_display.setText("—")
        self._anthro_file_label.setText("—")
        self._progress_bar.setValue(0)
        self._step_desc.clear()
        self._live_status.clear()
        for name in ("_comp_subtitle", "_comp_trial_lbl", "_comp_patient_lbl", "_comp_activity_lbl",
                     "_comp_frame_lbl", "_comp_hjc_lbl", "_comp_coord_lbl"):
            getattr(self, name).clear()
        self._stack.setCurrentWidget(self._config_widget)
        self._set_calibration_enabled(False)
        self._anthro_status("Select a patient and session in Patients & Sessions to begin.")

    def _on_path_changed(self, text: str) -> None:
        if self._is_populating:
            return
        clean = text.strip().strip('"\'')
        if not clean:
            return
        path = Path(clean).resolve()
        if not self._session_path or path != Path(self._session_path):
            self.set_session(str(path))
            return
        if not self._filename:
            try:
                root = ET.parse(path).getroot()
                self._filename = next((m.get("Filename", "") for m in root.findall(".//Measurement")
                    if "static" in m.get("Filename", "").lower()), "")
                if not self._filename:
                    self._filename = next((p.name for p in sorted(path.parent.iterdir())
                        if p.stem.lower().startswith("static") and p.suffix.lower() in {".qtm", ".c3d"}), "")
            except (OSError, ET.ParseError) as error:
                self._anthro_status(f"Could not load calibration XML: {error}", error=True)
                return
        self._static_file_display.setText(self._filename or "—")
        if self._filename and Path(self._filename).name != self._filename:
            self._filename = ""
            self._anthro_status("Calibration XML must reference a static trial in its own session.", error=True)
            return
        self._auto_fetch_static_data()

    def _browse_static_file(self) -> None:
        """Browse for a static trial file, automatically directed to the global data folder."""
        start_dir = ""
        current = self._file_path_edit.text().strip().strip('"\'')

        if self._data_root and os.path.isdir(self._data_root):
            # Check if current path exists inside data_root
            if current and os.path.exists(current):
                try:
                    rel = os.path.relpath(current, self._data_root)
                    if not rel.startswith(".."):
                        start_dir = os.path.dirname(current) if os.path.isfile(current) else current
                    else:
                        start_dir = self._data_root
                except Exception:
                    start_dir = self._data_root
            else:
                start_dir = self._data_root
        elif current and os.path.exists(current):
            start_dir = os.path.dirname(current) if os.path.isfile(current) else current
        elif self._session_path and os.path.exists(self._session_path):
            start_dir = os.path.dirname(self._session_path) if os.path.isfile(self._session_path) else self._session_path

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Static Calibration Trial",
            start_dir or "",
            "XML Files (*.xml)"
        )
        if path:
            self.set_session(path)

    # ═══════════════════════════════════════════════════════════════════
    #  Auto-Fetch Data from Static Trial & Session
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _parse_date_components(date_str: str) -> tuple[str, str, str]:
        """Parse date string into (day_str_2digits, month_abbr_3letters, year_str_4digits)."""
        if not date_str:
            return ("", "", "")
        import re
        m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", str(date_str).strip())
        if m:
            yr, mo, da = int(m.group(1)), int(m.group(2)), int(m.group(3))
            month_abbr = MONTH_NAMES[mo - 1] if 1 <= mo <= 12 else "Jan"
            return (f"{da:02d}", month_abbr, str(yr))
        m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})", str(date_str).strip())
        if m:
            da, mo, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
            month_abbr = MONTH_NAMES[mo - 1] if 1 <= mo <= 12 else "Jan"
            return (f"{da:02d}", month_abbr, str(yr))
        return ("", "", "")

    @staticmethod
    def _set_combo(combo: QComboBox, val: str) -> None:
        if not val:
            return
        idx = combo.findText(str(val))
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            for i in range(combo.count()):
                if combo.itemText(i).strip().lower() == str(val).strip().lower():
                    combo.setCurrentIndex(i)
                    return

    def _auto_fetch_static_data(self) -> None:
        """
        Auto-fetch patient, session, anthropometric, and foot model data
        from session.xml, existing Static_*.py, or C3D files, and populate the UI fields.
        """
        if getattr(self, "_is_populating", False):
            return
        self._is_populating = True
        try:
            # 1. Determine session_dir and filename
            session_dir: Optional[Path] = None
            if self._session_path and os.path.isfile(self._session_path):
                session_dir = Path(os.path.dirname(self._session_path))
            elif self._file_path_edit.text().strip():
                p = Path(self._file_path_edit.text().strip())
                if p.is_dir():
                    session_dir = p
                elif p.is_file():
                    session_dir = p.parent

            if not session_dir or not session_dir.is_dir():
                return

            if not self._session_path:
                sess_xml = session_dir / "session.xml"
                if sess_xml.is_file():
                    self._session_path = str(sess_xml).replace("\\", "/")

            self._prepare_anthro_context(session_dir)

            # 2. Extract from session.xml
            xml_data: dict[str, str] = {}
            sess_xml_path = Path(self._session_path)
            if sess_xml_path.is_file():
                try:
                    tree = ET.parse(str(sess_xml_path))
                    root = tree.getroot()
                    f_elem = root.find("Fields")
                    if f_elem is not None:
                        for child in f_elem:
                            if child.text:
                                xml_data[child.tag] = child.text.strip()
                    # Patient/session fields are distinct from per-measurement export snapshots.
                except Exception as e:
                    logger.warning("Error reading session.xml: %s", e)

            # 3. Locate existing Static_*.py files
            subject_name = xml_data.get("Name", "") or self._subject_name or ""
            candidates: list[Path] = []
            calib_dir = session_dir / "Calibration"
            allowed_parents = {session_dir.resolve()}
            if calib_dir.is_dir():
                allowed_parents.add(calib_dir.resolve())
                if subject_name:
                    candidates.append(calib_dir / f"Static_BF_{subject_name}.py")
                    candidates.append(calib_dir / f"Static_{subject_name}.py")
                for f in sorted(calib_dir.glob("Static_*.py")):
                    if f not in candidates:
                        candidates.append(f)

            if subject_name:
                candidates.append(session_dir / f"Static_BF_{subject_name}.py")
                candidates.append(session_dir / f"Static_{subject_name}.py")
            for f in sorted(session_dir.glob("Static_*.py")):
                if f not in candidates:
                    candidates.append(f)

            py_data: dict[str, Any] = {}
            loaded_py_path = None
            candidates = sorted((c for c in candidates if c.is_file()), key=lambda c: c.stat().st_mtime_ns, reverse=True)
            for cand in candidates:
                if cand.is_file():
                    if cand.resolve().parent not in allowed_parents:
                        continue
                    try:
                        import numpy as np
                        class MockConfig:
                            pass
                        cfg = MockConfig()
                        content = cand.read_text(encoding="utf-8", errors="replace")
                        exec(content, {"self": cfg, "np": np, "numpy": np})
                        for k, v in cfg.__dict__.items():
                            py_data[k] = v
                        loaded_py_path = cand
                        break
                    except Exception as e:
                        logger.warning("Error loading static python config %s: %s", cand, e)

            self._loaded_py_path = str(loaded_py_path) if loaded_py_path else ""

            # 4. Optional fallback to C3D parameters
            c3d_data: dict[str, Any] = {}
            c3d_cand = None
            if self._filename:
                stem = Path(self._filename).stem
                c3d_cand = session_dir / f"{stem}.c3d"
            if not c3d_cand or not c3d_cand.is_file():
                c3d_files = list(session_dir.glob("Static*.c3d"))
                if c3d_files:
                    c3d_cand = c3d_files[0]
            if c3d_cand and c3d_cand.is_file():
                try:
                    # pyrefly: ignore [missing-import]
                    from ezc3d import c3d
                    reader = c3d(str(c3d_cand))
                    proc = reader.get("parameters", {}).get("PROCESSING", {})
                    for k, val in proc.items():
                        if "value" in val and len(val["value"]) > 0:
                            c3d_data[k] = val["value"][0]
                except Exception:
                    pass

            qtm_data = {}  # Live values arrive asynchronously and take precedence over file fallbacks.

            def find_xml_val(*keys: str) -> str:
                for k in keys:
                    if not k:
                        continue
                    if k in xml_data and xml_data[k] is not None and str(xml_data[k]).strip() != "":
                        return str(xml_data[k]).strip()
                    norm_k = k.lower().replace(" ", "").replace("_", "").replace("-", "")
                    for xk, xv in xml_data.items():
                        if xv is not None and str(xv).strip() != "":
                            if xk.lower().replace(" ", "").replace("_", "").replace("-", "") == norm_k:
                                return str(xv).strip()
                return ""

            def get_val(py_key: str, xml_key: str = "", c3d_key: str = "", qtm_key: str = "", default: str = "") -> str:
                # 1. Live QTM value takes top priority
                if qtm_key and qtm_key in qtm_data and qtm_data[qtm_key] is not None:
                    v = str(qtm_data[qtm_key]).strip()
                    if v != "":
                        return v
                # 2. session.xml values (session source of truth)
                if xml_key:
                    xv = find_xml_val(xml_key)
                    if xv != "":
                        return xv
                # 3. py_data from existing Static_*.py
                if py_key and py_key in py_data and py_data[py_key] is not None:
                    v = str(py_data[py_key]).strip()
                    if v != "":
                        return v
                # 4. c3d_data
                if c3d_key and c3d_key in c3d_data and c3d_data[c3d_key] is not None:
                    v = str(c3d_data[c3d_key]).strip()
                    if v != "":
                        return v
                return default

            def format_meters(val_str: str) -> str:
                if not val_str or str(val_str).strip() == "":
                    return ""
                try:
                    return f"{float(val_str):.3f}"
                except (ValueError, TypeError):
                    return str(val_str).strip()

            def format_mass(val_str: str) -> str:
                if not val_str or str(val_str).strip() == "":
                    return ""
                try:
                    return f"{float(val_str):.1f}"
                except (ValueError, TypeError):
                    return str(val_str).strip()

            # ── 1. Patient Information
            first_name = get_val("valueFirstName", "Name", qtm_key="Name", default="")
            self._first_name.setText(first_name)
            last_name = get_val("valueLastName", "Last_name", qtm_key="Last_name", default="")
            self._last_name.setText(last_name)
            pat_num = get_val("valuePatientNumber", "ID", qtm_key="ID", default="")
            self._patient_number.setText(pat_num)
            self._set_combo(self._sex, get_val("valueSex", "Sex", qtm_key="Sex", default=""))

            # Date of Birth
            xml_dob = find_xml_val("DOB", "Date_of_birth", "Date of birth") or str(qtm_data.get("DOB", ""))
            if xml_dob:
                d, m, y = self._parse_date_components(xml_dob)
                dob_day, dob_mon, dob_yr = d, m, y
            else:
                dob_day = get_val("valueDateOfBirth_Day")
                dob_mon = get_val("valueDateOfBirth_Month")
                dob_yr = get_val("valueDateOfBirth_Year")
            if dob_day:
                self._set_combo(self._dob_day, f"{int(dob_day):02d}" if str(dob_day).isdigit() else str(dob_day))
            if dob_mon:
                self._set_combo(self._dob_month, str(dob_mon))
            if dob_yr:
                self._set_combo(self._dob_year, str(dob_yr))

            # Activity & Modifier
            self._set_combo(self._trial_activity, get_val("valueTrialActivity", "Measurement_type", default="Static"))
            self._set_combo(self._trial_modifier, get_val("valueTrialModifier", default="Barefoot"))
            self._set_combo(self._fwd_dir, get_val("StaticForwardDirection", default="+X"))
            self._set_combo(self._assistive_device, get_val("valueAssistiveDevice", default="None"))
            self._static_frame_num.setText(get_val("valueStaticFrameNumber", default="20"))

            # Model & Coordinate System
            hip_val = get_val("HipModelName", default="Harrington2")
            for idx in range(self._hip_combo.count()):
                d = str(self._hip_combo.itemData(idx) or "")
                t = self._hip_combo.itemText(idx)
                if d == hip_val or hip_val.lower() in t.lower() or hip_val.lower() in d.lower():
                    self._hip_combo.setCurrentIndex(idx)
                    break

            coord_val = get_val("ShankCoordinateSystem", default="Distal")
            for idx in range(self._coord_combo.count()):
                d = str(self._coord_combo.itemData(idx) or "")
                t = self._coord_combo.itemText(idx)
                if d == coord_val or coord_val.lower() in t.lower() or coord_val.lower() in d.lower():
                    self._coord_combo.setCurrentIndex(idx)
                    break

            # ── 2. Anthropometric Parameters
            if self._filename:
                self._static_file_display.setText(self._filename)
            elif "valueStaticFile" in py_data:
                self._static_file_display.setText(str(py_data["valueStaticFile"]))

            anthro_name = get_val("valueAnthropometricFile", default=(loaded_py_path.stem if loaded_py_path else "—"))
            self._anthro_file_label.setText(anthro_name)

            # Date Captured
            c_date = find_xml_val("Creation_date", "Creation date") or str(qtm_data.get("Creation date", ""))
            if c_date:
                d, m, y = self._parse_date_components(c_date)
                cap_day, cap_mon, cap_yr = d, m, y
            else:
                cap_day = get_val("valueDataCollectionDate_Day")
                cap_mon = get_val("valueDataCollectionDate_Month")
                cap_yr = get_val("valueDataCollectionDate_Year")
            if cap_day:
                self._set_combo(self._cap_day, f"{int(cap_day):02d}" if str(cap_day).isdigit() else str(cap_day))
            if cap_mon:
                self._set_combo(self._cap_month, str(cap_mon))
            if cap_yr:
                self._set_combo(self._cap_year, str(cap_yr))

            # Body mass & Height & ASIS
            self._body_mass.setText(format_mass(get_val("valueBodyMass", "BodyMass", "Bodymass", qtm_key="BodyMass", default="")))
            self._height.setText(format_meters(get_val("valueHeight", "Height", "Height", qtm_key="Height", default="")))
            self._asis_dist.setText(format_meters(get_val("valueASISdist", "InterAsisDistance", "InterAsisDistance", qtm_key="InterAsisDistance", default="")))

            # Bilateral metrics
            anthro_map = [
                ("left_leg_length", "valueLeftLegLength", "LeftLegLength", "LeftLegLength"),
                ("right_leg_length", "valueRightLegLength", "RightLegLength", "RightLegLength"),
                ("left_knee_width", "valueLeftKneeWidth", "LeftKneeWidth", "LeftKneeWidth"),
                ("right_knee_width", "valueRightKneeWidth", "RightKneeWidth", "RightKneeWidth"),
                ("left_ankle_width", "valueLeftAnkleWidth", "LeftAnkleWidth", "LeftAnkleWidth"),
                ("right_ankle_width", "valueRightAnkleWidth", "RightAnkleWidth", "RightAnkleWidth"),
                ("left_asis_gt", "valueLeftASIStoGTdist", "LeftAsisTrocanterDistance", "LeftAsisTrocanterDistance"),
                ("right_asis_gt", "valueRightASIStoGTdist", "RightAsisTrocanterDistance", "RightAsisTrocanterDistance"),
            ]
            for widget_key, p_key, x_key, q_key in anthro_map:
                w = self._anthro_inputs.get(widget_key)
                if w:
                    w.setText(format_meters(get_val(p_key, x_key, x_key, q_key, default="")))

            # ── 3. Foot Model
            self._left_foot_check.setChecked(get_val("valueLeftFootModelCheck") == "1")
            self._right_foot_check.setChecked(get_val("valueRightFootModelCheck") == "1")
            foot_map = [
                ("left_hindfoot_varus", "valueLeftHindfootVarus"),
                ("right_hindfoot_varus", "valueRightHindfootVarus"),
                ("left_calcaneal_pitch", "valueLeftCalcanealPitch"),
                ("right_calcaneal_pitch", "valueRightCalcanealPitch"),
                ("left_hindfoot_progression", "valueLeftHindfootProgression"),
                ("right_hindfoot_progression", "valueRightHindfootProgression"),
                ("left_first_metatarsal_pitch", "valueLeftFirstMetatarsalPitch"),
                ("right_first_metatarsal_pitch", "valueRightFirstMetatarsalPitch"),
            ]
            for widget_key, p_key in foot_map:
                w = self._foot_inputs.get(widget_key)
                if w:
                    w.setText(get_val(p_key, default=""))

            # ── 4. Special Test Conditions
            self._left_plantigrade.setChecked(get_val("valueLeftPlantigradeCheck", default="1") == "1")
            self._right_plantigrade.setChecked(get_val("valueRightPlantigradeCheck", default="1") == "1")
            self._subject_shod.setChecked(get_val("valueSujectShodCheck", default="0") == "1")
            self._left_sole.setText(get_val("valueLeftSoleThickness", default="0"))
            self._right_sole.setText(get_val("valueRightSoleThickness", default="0"))

            knee_opt = get_val("valueKneeAlignmentCheck", default="1")
            if knee_opt == "0":
                self._knee_kad.setChecked(True)
            else:
                self._knee_ml.setChecked(True)

            pelvic_fix = get_val("valuePelvicFixCheck", default="0")
            if pelvic_fix == "1":
                self._pelvic_iliac.setChecked(True)
            elif pelvic_fix == "2":
                self._pelvic_triad.setChecked(True)
            else:
                self._pelvic_na.setChecked(True)

            # ── 5. Model Configuration
            hip_val = get_val("HipModelName", default="Harrington2")
            if "Harrington" in hip_val:
                self._hip_combo.setCurrentIndex(0)
            elif "Davis" in hip_val or "Newington" in hip_val:
                self._hip_combo.setCurrentIndex(1)
            elif "Prentice" in hip_val:
                self._hip_combo.setCurrentIndex(2)

            self._set_combo(self._coord_combo, get_val("ShankCoordinateSystem", default="Standard Shriners (ISB Aligned)"))

            self._manual_baseline = {name: self._sync_value(name) for name in self._sync_fields}
            logger.info("Auto-fetched static parameters for trial '%s' (subject: %s)", self._filename, first_name)
        finally:
            self._is_populating = False

    # ═══════════════════════════════════════════════════════════════════
    #  Save Modified Parameters to Static_<Condition>_<SubjectName>.py
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _build_updated_static_py(existing_lines: list[str], values: dict) -> str:
        out: list[str] = []
        user_pref_ends = False

        if existing_lines:
            for line in existing_lines:
                words = line.strip().split()
                if not words:
                    if not user_pref_ends:
                        out.append(line)
                    continue
                if words[0] == "self.valueFirstName":
                    user_pref_ends = True
                    break
                if words[0] == "self.StaticForwardDirection":
                    out.append(f"self.StaticForwardDirection = '{values.get('StaticForwardDirection', '+X')}'\n")
                elif words[0] == "self.HipModelName":
                    out.append(f"self.HipModelName = '{values.get('HipModelName', 'Harrington2')}'\n")
                elif words[0] == "self.ShankCoordinateSystem":
                    out.append(f"self.ShankCoordinateSystem = '{values.get('ShankCoordinateSystem', 'Distal')}'\n")
                else:
                    out.append(line)
        else:
            out = DEFAULT_STATIC_TEMPLATE_HEADER.splitlines(keepends=True)

        # Write all self.value* variables
        for k, v in values.items():
            if k.startswith("value"):
                if isinstance(v, (int, float)):
                    out.append(f"self.{k} = {v}\n")
                else:
                    out.append(f"self.{k} = {v!r}\n")

        # If existing_lines had Pelfix / Transformation matrices, preserve them
        if existing_lines:
            recording_tail = False
            for line in existing_lines:
                words = line.strip().split()
                if len(words) >= 2 and words[0] == "#" and (words[1] in ("Pelfix", "Transformation")):
                    recording_tail = True
                if recording_tail:
                    out.append(line)

        return "".join(out)



    def _init_anthropometric_sync(self):
        self._anthro_widgets = {
            "BodyMass": self._body_mass, "Height": self._height,
            "InterAsisDistance": self._asis_dist,
        }
        for side in ("left", "right"):
            for key, suffix in (("leg_length", "LegLength"), ("knee_width", "KneeWidth"),
                                ("ankle_width", "AnkleWidth"), ("asis_gt", "AsisTrocanterDistance")):
                self._anthro_widgets[side.title() + suffix] = self._anthro_inputs[f"{side}_{key}"]
        self._patient_widgets = {"Name": self._first_name, "ID": self._patient_number,
                                 "Sex": self._sex, "DOB": (self._dob_day, self._dob_month, self._dob_year)}
        self._sync_fields = set(self._anthro_widgets) | set(self._patient_widgets)
        self._anthro_context = None
        self._anthro_generation = 0
        self._anthro_connected = False
        self._anthro_dirty = set()
        self._anthro_revisions = {name: 0 for name in self._sync_fields}
        self._anthro_inflight_revisions = {}
        self._manual_baseline = {}
        self._manual_inflight_values = {}
        self._manual_local_dirty = False
        self._sync_details = {}
        self._manual_requested_identity = {}
        self._anthro_sync = AnthropometricSyncService(self)
        self._anthro_sync.finished.connect(self._on_anthro_sync_finished)
        self._anthro_sync.write_finished.connect(self._on_anthro_write_finished)

        self._auto_sync_timer = QTimer(self)
        self._auto_sync_timer.setSingleShot(True)
        self._auto_sync_timer.setInterval(600)
        self._auto_sync_timer.timeout.connect(self._on_auto_sync_timer_timeout)

        self._external_sync_timer = QTimer(self)
        self._external_sync_timer.setInterval(1200)
        self._external_sync_timer.timeout.connect(self._poll_external_qtm_sync)
        self._last_external_mtime = {}
        self._external_sync_timer.start()

        for name, widget in self._anthro_widgets.items():
            widget.setObjectName(name)
            widget.setToolTip(f"{name} ({ANTHROPOMETRIC_FIELDS[name]}): enter a finite number.")
            widget.textEdited.connect(lambda text, n=name: self._on_anthro_edited(n))
            widget.editingFinished.connect(lambda n=name: self._on_anthro_commit(n))
        for name in ("Name", "ID"):
            widget = self._patient_widgets[name]
            widget.setObjectName(name)
            widget.textEdited.connect(lambda text, n=name: self._on_anthro_edited(n))
            widget.editingFinished.connect(lambda n=name: self._on_anthro_commit(n))
        self._first_name.setToolTip("QTM Name, preserved as one field without splitting or joining names.")
        self._sex.setObjectName("Sex")
        self._sex.activated.connect(lambda index: self._on_patient_choice("Sex"))
        for widget in self._patient_widgets["DOB"]:
            widget.activated.connect(lambda index: self._on_patient_choice("DOB"))
        for widget in (self._trial_activity, self._trial_modifier, self._assistive_device,
                       self._fwd_dir, self._static_frame_num):
            widget.setToolTip("Local static configuration: this PAF has no equivalent shared metadata field.")
        shared = set(self._anthro_widgets.values()) | {self._first_name, self._patient_number, self._sex,
                                                      self._dob_day, self._dob_month, self._dob_year, self._file_path_edit}
        for widget in (self._config_widget.findChildren(QLineEdit) + self._config_widget.findChildren(QComboBox)
                       + self._config_widget.findChildren(QCheckBox) + self._config_widget.findChildren(QRadioButton)):
            if widget in shared:
                continue
            signal = (widget.textEdited if isinstance(widget, QLineEdit) else
                      widget.activated if isinstance(widget, QComboBox) else widget.clicked)
            signal.connect(self._on_local_calibration_edited)
        self._stack.currentChanged.connect(self._on_anthro_view_changed)

    def _sync_value(self, name):
        if name in self._anthro_widgets:
            return self._anthro_widgets[name].text().strip()
        if name == "DOB":
            day, month, year = (w.currentText() for w in self._patient_widgets[name])
            if not day and not month and not year:
                return ""
            return f"{year}-{MONTH_NAMES.index(month) + 1:02d}-{day}" if month in MONTH_NAMES else ""
        widget = self._patient_widgets[name]
        return widget.text().strip() if isinstance(widget, QLineEdit) else widget.currentText()

    def _set_sync_value(self, name, value):
        if name in self._anthro_widgets:
            with QSignalBlocker(self._anthro_widgets[name]):
                self._anthro_widgets[name].setText(format_measurement(name, value))
        elif name in {"Name", "ID"}:
            with QSignalBlocker(self._patient_widgets[name]):
                self._patient_widgets[name].setText(str(value))
        else:
            values = self._parse_date_components(value) if name == "DOB" else (str(value),)
            widgets = self._patient_widgets[name] if name == "DOB" else (self._sex,)
            for widget, text in zip(widgets, values):
                with QSignalBlocker(widget):
                    if widget.findText(text) < 0:
                        widget.addItem(text)
                    widget.setCurrentIndex(widget.findText(text))

    def _on_patient_choice(self, name):
        if not getattr(self, "_is_populating", False):
            self._anthro_dirty.add(name)
            self._anthro_revisions[name] += 1
            self._sync_field_to_xml_and_qtm(name)

    def _on_anthro_commit(self, name):
        if not getattr(self, "_is_populating", False):
            if hasattr(self, "_auto_sync_timer"):
                self._auto_sync_timer.stop()
            self._sync_field_to_xml_and_qtm(name)

    def _on_auto_sync_timer_timeout(self):
        if not getattr(self, "_is_populating", False) and self._anthro_dirty:
            self._sync_fields_to_xml_and_qtm({name: self._sync_value(name) for name in list(self._anthro_dirty)})

    def _poll_external_qtm_sync(self):
        """
        Background poll: check if session parameters in QTM or session.xml have been
        modified externally, and automatically sync them with the GUI.
        """
        if getattr(self, "_is_populating", False):
            return
        if not self._session_path or not Path(self._session_path).is_file():
            return
        if hasattr(self, "_stack") and self._stack.currentWidget() is not self._config_widget:
            return

        session_xml = Path(self._session_path)
        session_dir = session_xml.parent
        qpr_file = session_dir / "data.qpr"

        xml_mtime = session_xml.stat().st_mtime if session_xml.is_file() else 0
        qpr_mtime = qpr_file.stat().st_mtime if qpr_file.is_file() else 0

        last_xml = self._last_external_mtime.get("xml")
        last_qpr = self._last_external_mtime.get("qpr")

        if last_xml is None:
            self._last_external_mtime["xml"] = xml_mtime
            self._last_external_mtime["qpr"] = qpr_mtime
            return

        changed = False
        if xml_mtime > last_xml:
            self._last_external_mtime["xml"] = xml_mtime
            changed = True
        if qpr_mtime > last_qpr:
            self._last_external_mtime["qpr"] = qpr_mtime
            changed = True

        if changed:
            self._sync_from_external_sources()

    def _sync_from_external_sources(self):
        """Reload external session changes into GUI and sync all measurement blocks."""
        if getattr(self, "_is_populating", False) or not self._session_path:
            return
        try:
            tree = ET.parse(self._session_path)
            root = tree.getroot()
            fields_elem = root.find("Fields")
            if fields_elem is not None:
                updated_fields = {}
                for child in fields_elem:
                    val = child.text
                    if val is not None and child.tag in self._sync_fields:
                        updated_fields[child.tag] = val

                for name, val in updated_fields.items():
                    if name in self._anthro_dirty:
                        continue
                    current_gui_val = self._sync_value(name)
                    if not same_field_value(name, current_gui_val, val):
                        self._set_sync_value(name, val)
                        self._manual_baseline[name] = self._sync_value(name)

                # Ensure all Measurement blocks in session.xml match the session fields
                update_session_xml(self._session_path, updated_fields)
        except Exception as e:
            logger.debug("External sync parse error: %s", e)

        # If QTM is connected and idle, trigger background fetch to get live QTM in-memory values as well
        if self._anthro_connected and self._anthro_sync.operation is None and not self._anthro_dirty:
            self._start_manual_sync()

    def _sync_field_to_xml_and_qtm(self, name: str) -> None:
        self._sync_fields_to_xml_and_qtm({name: self._sync_value(name)})

    def _sync_fields_to_xml_and_qtm(self, fields_to_sync: dict) -> None:
        if getattr(self, "_is_populating", False) or not self._session_path:
            return
        valid = {}
        for name, val in fields_to_sync.items():
            if val is None or str(val).strip() == "":
                continue
            try:
                if name in ANTHROPOMETRIC_FIELDS:
                    validate_parameter(name, val)
                elif name in PATIENT_FIELDS:
                    validate_patient_field(name, val)
                valid[name] = val
            except ValueError:
                continue

        if not valid:
            return

        update_session_xml(self._session_path, valid)
        session_dir = Path(self._session_path).resolve().parent
        self._anthro_sync.write_async(session_dir, valid, self._anthro_generation)

        for name in valid:
            self._anthro_dirty.discard(name)
            self._manual_baseline[name] = self._sync_value(name)

        synced_names = ", ".join(sorted(valid.keys()))
        self._anthro_status(f"Updated {synced_names} in XML & QTM.")

    def _on_anthro_write_finished(self, result: dict) -> None:
        if result.get("generation") != self._anthro_generation:
            return
        if result.get("success"):
            logger.info("QTM synced successfully for generation %s: %s", result.get("generation"), list(result.get("fields", {}).keys()))
        else:
            logger.warning("QTM sync warning: %s", result.get("error"))

    def _prepare_anthro_context(self, session_dir):
        context = (os.path.normcase(str(session_dir.resolve())),)
        if context != self._anthro_context:
            self._anthro_sync.cancel()
            self._anthro_generation += 1
            self._anthro_context = context
            self._anthro_connected = False
            self._manual_baseline = {}
            self._anthro_dirty.clear()
            self._manual_local_dirty = False
            self._anthro_status("Session selected. Calibration edits are saved locally.")

    def _on_anthro_edited(self, name):
        self._anthro_dirty.add(name)
        self._anthro_revisions[name] += 1
        self._anthro_status(f"Editing {name}… Click Save Parameters to save all.")
        if not getattr(self, "_is_populating", False) and hasattr(self, "_auto_sync_timer"):
            self._auto_sync_timer.start()

    def _anthro_status(self, message, error=False):
        self._sync_details = {}
        self._sync_details_btn.hide()
        self._config_status.setToolTip(message)
        self._config_status.setText(message)
        self._config_status.setStyleSheet(
            "color: #EF4444;" if error else "color: #22C55E; font-weight: bold;"
        )
        self._metadata_status.setToolTip(message)
        self._metadata_status.setText(message)
        self._metadata_status.setStyleSheet("color: #EF4444;" if error else "")

    def _sync_feedback(self, message, details, error=False):
        self._anthro_status(message, error=error)
        self._sync_details = details
        self._sync_details_btn.setVisible(bool(details))

    def _sync_details_text(self):
        return json.dumps(self._sync_details, indent=2, ensure_ascii=False, default=str)

    def _show_sync_details(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Calibration parameters — Details")
        dialog.resize(720, 480)
        layout = QVBoxLayout(dialog)
        text = QPlainTextEdit(dialog)
        text.setReadOnly(True)
        text.setPlainText(self._sync_details_text())
        layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=dialog)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def _gui_session_identity(self):
        identity = {"normalized_session_path": self._anthro_context[0] if self._anthro_context else None,
                    "measurement": self._filename, "session_xml": self._session_path}
        if self._session_path:
            try:
                root = ET.parse(self._session_path).getroot()
                identity["xml_metadata"] = {"attributes": root.attrib, "fields": {
                    name: root.findtext("Fields/" + name) for name in
                    ("Name", "ID", "Sex", "DOB", "Session_ID", "BodyMass", "Height")}}
            except (OSError, ET.ParseError) as error:
                identity["xml_error"] = str(error)
        return identity

    def _has_unsaved_sync_edits(self):
        return self._manual_local_dirty or bool(self._anthro_dirty) or any(
            not same_field_value(name, self._sync_value(name), value)
            for name, value in self._manual_baseline.items())

    def _on_local_calibration_edited(self, *args):
        if not self._is_populating:
            self._manual_local_dirty = True

    def _on_fetch_clicked(self):
        if self._anthro_sync.operation is not None:
            self._anthro_status("A QTM operation is still running. Please wait.")
            return
        if self._has_unsaved_sync_edits():
            answer = QMessageBox.question(
                self, "Fetch QTM", "Fetching QTM parameters will replace your unsaved changes. Continue?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        self._start_manual_sync()

    def _start_manual_sync(self):
        self._manual_inflight_values = {name: self._sync_value(name) for name in self._sync_fields}
        self._manual_requested_identity = self._gui_session_identity()
        self._anthro_inflight_revisions = dict(self._anthro_revisions)
        context = self._anthro_context[0] if self._anthro_context else ""
        if self._anthro_sync.request(context, self._anthro_generation):
            self._save_btn.setEnabled(False)
            self._fetch_btn.setEnabled(False)
            self._anthro_status("Fetching QTM parameters…")

    def _on_anthro_sync_finished(self, result):
        if result["generation"] != self._anthro_generation:
            return
        self._anthro_sync.operation = None
        self._save_btn.setEnabled(bool(self._session_path))
        self._fetch_btn.setEnabled(bool(self._session_path))
        snapshot = result["snapshot"]
        details = {"attempted_operation": "Fetch QTM", "gui_session": self._manual_requested_identity,
                   "qtm_measurement": result.get("measurement"), "failed_parameters": {}}
        if snapshot is None:
            self._anthro_connected = False
            details.update(result.get("diagnostics", {}))
            reason = {"ambiguous_read_source": "QTM read source is ambiguous.",
                      "connection_failure": "QTM is unavailable.",
                      "invalid_data": "QTM returned invalid values.",
                      "session_not_found": "the selected QTM session was not found."}.get(
                          details.get("error_type"), "QTM could not complete Fetch.")
            self._sync_feedback(f"Parameters not fetched — {reason}", details, error=True)
            return
        details.update(snapshot.get("resolution", {}))
        switched = self._anthro_context is None or snapshot["context"] != self._anthro_context[0]
        if switched:
            folder = Path(snapshot["context"])
            if not (folder / "session.xml").is_file():
                self._sync_feedback("Parameters not fetched — the QTM session has no session.xml.", details, error=True)
                return
            self.set_session(str(folder / "session.xml"))
        self._anthro_connected = True
        errors = dict(snapshot["errors"])
        missing = self._sync_fields - snapshot["fields"].keys()
        errors.update({name: "QTM does not expose this field" for name in missing})
        fetched = []
        for name in self._sync_fields:
            if name in errors:
                continue
            unchanged = (self._anthro_revisions[name] == self._anthro_inflight_revisions.get(name)
                         and same_field_value(name, self._sync_value(name), self._manual_inflight_values.get(name)))
            if unchanged or switched:
                self._set_sync_value(name, snapshot["fields"][name])
                self._anthro_dirty.discard(name)
                self._manual_baseline[name] = self._sync_value(name)
            fetched.append(name)
        # Fetch supplies values for review; it does not persist them to local calibration.
        details["failed_parameters"] = errors
        details["fetched_parameters"] = sorted(fetched)
        message = "Some QTM parameters could not be fetched." if errors else "Parameters fetched."
        if self._anthro_dirty:
            message += " New edits retained."
        self._sync_feedback(message, details, error=bool(errors))

    def _on_anthro_view_changed(self, index):
        if hasattr(self, "_anthro_sync") and self._stack.currentWidget() is not self._config_widget:
            self._anthro_sync.cancel()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "_external_sync_timer"):
            self._external_sync_timer.start()

    def hideEvent(self, event):
        if hasattr(self, "_external_sync_timer"):
            self._external_sync_timer.stop()
        self._anthro_sync.cancel()
        super().hideEvent(event)

    def closeEvent(self, event):
        if hasattr(self, "_external_sync_timer"):
            self._external_sync_timer.stop()
        self._anthro_sync.cancel()
        super().closeEvent(event)

    def _get_hip_model_value(self) -> str:
        data = self._hip_combo.currentData()
        if data:
            return str(data)
        txt = self._hip_combo.currentText().strip()
        if "harrington2" in txt.lower():
            return "Harrington2"
        if "harrington" in txt.lower():
            return "Harrington"
        if "newington" in txt.lower() or "davis" in txt.lower():
            return "Newington"
        return "Harrington2"

    def _get_shank_coord_value(self) -> str:
        data = self._coord_combo.currentData()
        if data:
            return str(data)
        txt = self._coord_combo.currentText().strip()
        if "proximal" in txt.lower():
            return "Proximal"
        return "Distal"

    def _save_static_parameters(self) -> str | None:
        """Persist calibration to the existing session-local Static_*.py format."""
        if not self._session_path or not Path(self._session_path).is_file():
            self._anthro_status("Select a valid calibration XML before saving.", error=True)
            return None
        selected_path = self._file_path_edit.text().strip().strip('"\'')
        if not selected_path or Path(selected_path).resolve() != Path(self._session_path):
            self._anthro_status("Parameters not saved — choose a valid calibration XML first.", error=True)
            return None
        session_dir = Path(self._session_path).resolve().parent
        try:
            root = ET.parse(self._session_path).getroot()
            for name, widget in self._anthro_widgets.items():
                validate_parameter(name, widget.text().strip())
            for name in self._patient_widgets:
                if self._sync_value(name):
                    validate_patient_field(name, self._sync_value(name))
            dates = (self._dob_day.currentText(), self._dob_month.currentText(), self._dob_year.currentText())
            if any(dates) and not all(dates):
                raise ValueError("DOB: select a complete date or leave all date fields empty.")
            optional_measurements = [(name.replace("_", " ").capitalize(), widget, "degrees")
                                     for name, widget in self._foot_inputs.items()]
            optional_measurements.extend([("Left sole thickness", self._left_sole, "m"),
                                          ("Right sole thickness", self._right_sole, "m")])
            for name, widget, unit in optional_measurements:
                if widget.text().strip():
                    validate_parameter(name, widget.text().strip(), unit)
            frame = self._static_frame_num.text().strip()
            if not frame or int(frame) < 1:
                raise ValueError("Static frame: enter a positive whole frame number.")
        except (ValueError, OSError, ET.ParseError) as error:
            self._anthro_status(f"Parameters not saved — {error}", error=True)
            return None

        first_name = self._first_name.text().strip()
        last_name = self._last_name.text().strip()
        patient_number = self._patient_number.text().strip()
        # The export's subject identity names the processing file, independently of edited display values.
        source_name = root.findtext("Fields/Name") or session_dir.parent.name
        subject_name = "".join("_" if char in '<>:"/\\|?*' else char for char in source_name)
        if subject_name in {"", ".", ".."}:
            self._anthro_status("Parameters not saved — invalid calibration identity.", error=True)
            return None

        modifier = self._trial_modifier.currentText().strip()
        condition = "BF" if modifier == "Barefoot" else modifier.replace(" ", "_")

        calib_dir = session_dir / "Calibration"
        if calib_dir.is_dir() or (self._loaded_py_path and Path(self._loaded_py_path).parent == calib_dir):
            target_file = calib_dir / f"Static_{condition}_{subject_name}.py"
        elif self._loaded_py_path and Path(self._loaded_py_path).is_file() and Path(self._loaded_py_path).parent == session_dir:
            target_file = Path(self._loaded_py_path)
        else:
            target_file = session_dir / f"Static_{condition}_{subject_name}.py"

        # Resolving Calibration here would let a directory link expand the allowed destinations.
        allowed_target_parents = {session_dir, calib_dir}
        if target_file.resolve().parent not in allowed_target_parents:
            self._anthro_status("Parameters not saved — calibration destination is outside this session.", error=True)
            return None
        values = {
            "StaticForwardDirection": self._fwd_dir.currentText().strip(),
            "HipModelName": self._get_hip_model_value(),
            "ShankCoordinateSystem": self._get_shank_coord_value(),
            "valueFirstName": first_name,
            "valueMeasurementUnits": "m",
            "valueLastName": last_name,
            "valuePatientNumber": patient_number,
            "valueSex": self._sex.currentText(),
            "valueDateOfBirth_Day": self._dob_day.currentText().strip(),
            "valueDateOfBirth_Month": self._dob_month.currentText().strip(),
            "valueDateOfBirth_Year": self._dob_year.currentText().strip(),
            "valueTrialActivity": self._trial_activity.currentText().strip(),
            "valueTrialModifier": modifier,
            "valueAssistiveDevice": self._assistive_device.currentText().strip(),
            "valueStaticFile": Path(self._filename).stem if self._filename else "Static 1",
            "valueAnthropometricFile": target_file.stem,
            "valueDataCollectionDate_Day": self._cap_day.currentText().strip(),
            "valueDataCollectionDate_Month": self._cap_month.currentText().strip(),
            "valueDataCollectionDate_Year": self._cap_year.currentText().strip(),
            "valueBodyMass": self._body_mass.text().strip(),
            "valueHeight": self._height.text().strip(),
            "valueASISdist": self._asis_dist.text().strip(),
            "valueLeftLegLength": self._anthro_inputs.get("left_leg_length", QLineEdit()).text().strip(),
            "valueRightLegLength": self._anthro_inputs.get("right_leg_length", QLineEdit()).text().strip(),
            "valueLeftKneeWidth": self._anthro_inputs.get("left_knee_width", QLineEdit()).text().strip(),
            "valueRightKneeWidth": self._anthro_inputs.get("right_knee_width", QLineEdit()).text().strip(),
            "valueLeftAnkleWidth": self._anthro_inputs.get("left_ankle_width", QLineEdit()).text().strip(),
            "valueRightAnkleWidth": self._anthro_inputs.get("right_ankle_width", QLineEdit()).text().strip(),
            "valueLeftASIStoGTdist": self._anthro_inputs.get("left_asis_gt", QLineEdit()).text().strip(),
            "valueRightASIStoGTdist": self._anthro_inputs.get("right_asis_gt", QLineEdit()).text().strip(),
            "valueLeftFootModelCheck": "1" if self._left_foot_check.isChecked() else "0",
            "valueRightFootModelCheck": "1" if self._right_foot_check.isChecked() else "0",
            "valueLeftHindfootVarus": self._foot_inputs.get("left_hindfoot_varus", QLineEdit()).text().strip(),
            "valueLeftCalcanealPitch": self._foot_inputs.get("left_calcaneal_pitch", QLineEdit()).text().strip(),
            "valueLeftHindfootProgression": self._foot_inputs.get("left_hindfoot_progression", QLineEdit()).text().strip(),
            "valueLeftFirstMetatarsalPitch": self._foot_inputs.get("left_first_metatarsal_pitch", QLineEdit()).text().strip(),
            "valueRightHindfootVarus": self._foot_inputs.get("right_hindfoot_varus", QLineEdit()).text().strip(),
            "valueRightCalcanealPitch": self._foot_inputs.get("right_calcaneal_pitch", QLineEdit()).text().strip(),
            "valueRightHindfootProgression": self._foot_inputs.get("right_hindfoot_progression", QLineEdit()).text().strip(),
            "valueRightFirstMetatarsalPitch": self._foot_inputs.get("right_first_metatarsal_pitch", QLineEdit()).text().strip(),
            "valueLeftPlantigradeCheck": "1" if self._left_plantigrade.isChecked() else "0",
            "valueRightPlantigradeCheck": "1" if self._right_plantigrade.isChecked() else "0",
            "valueSujectShodCheck": "1" if self._subject_shod.isChecked() else "0",
            "valueLeftSoleThickness": self._left_sole.text().strip(),
            "valueRightSoleThickness": self._right_sole.text().strip(),
            "valuePelvicFixCheck": "1" if self._pelvic_iliac.isChecked() else ("2" if self._pelvic_triad.isChecked() else "0"),
            "valueKneeAlignmentCheck": "1" if self._knee_ml.isChecked() else "0",
            "valueStaticFrameNumber": frame,
        }

        try:
            existing = target_file if target_file.is_file() else Path(self._loaded_py_path) if self._loaded_py_path else None
            if existing is not None and existing.resolve().parent not in allowed_target_parents:
                raise ValueError("Loaded calibration belongs to a different session.")
            lines = existing.read_text(encoding="utf8").splitlines(True) if existing is not None else DEFAULT_STATIC_TEMPLATE_HEADER.splitlines(True)
            content = self._build_updated_static_py(lines, values)
            compile(content, str(target_file), "exec")
            output = QSaveFile(str(target_file))
            if not output.open(QIODevice.WriteOnly):
                raise OSError(output.errorString())
            encoded = content.encode("utf8")
            if output.write(encoded) != len(encoded):
                output.cancelWriting()
                raise OSError(output.errorString())
            if not output.commit():
                raise OSError(output.errorString())
        except (OSError, ValueError, SyntaxError) as error:
            self._anthro_status(f"Parameters not saved — {error}", error=True)
            return None
        self._loaded_py_path = str(target_file)
        self._anthro_file_label.setText(target_file.stem)
        self._anthro_dirty.clear()
        self._manual_local_dirty = False
        self._manual_baseline = {name: self._sync_value(name) for name in self._sync_fields}

        return str(target_file)

    def _on_save_clicked(self) -> None:
        if self._anthro_sync.operation is not None:
            self._anthro_status("Fetch QTM is still running. Please wait.")
            return
        if self._save_static_parameters() is not None:
            self._sync_fields_to_xml_and_qtm({name: self._sync_value(name) for name in self._sync_fields})
            self._anthro_status("Parameters saved successfully.")

    # ═══════════════════════════════════════════════════════════════════
    #  Processing Workflow
    # ═══════════════════════════════════════════════════════════════════

    def _on_run_clicked(self) -> None:
        if not self._session_path or not Path(self._session_path).is_file() or not self._filename:
            self._anthro_status("Select an XML session with a static trial before running analysis.", error=True)
            return

        # 1. Save all edited parameters to Static_<Condition>_<SubjectName>.py
        if self._save_static_parameters() is None:
            return
        # Save & Run uses the same local persistence as Save Parameters.
        self._start_static_processing()

    def _start_static_processing(self):
        # 2. Transition to processing view with animation
        self._stack.setCurrentWidget(self._processing_widget)
        self.scroll_to_top()
        self._progress_bar.setValue(10)
        self._step_desc.setText("Initializing static calibration...")
        self._live_status.setText("● Processing")
        self._live_status.setStyleSheet("color: #ED8B00; border: none;")

        mod = self._trial_modifier.currentText().strip()
        cond = "BF" if mod == "Barefoot" else mod.replace(" ", "_")

        logger.info("Starting static analysis for session: %s, file: %s, condition: %s", self._session_path, self._filename, cond)
        self._service.process_static(self._session_path, self._filename, condition=cond)


    def scroll_to_top(self) -> None:
        """Reset scroll area to top, stopping any smooth scroll momentum."""
        if hasattr(self, "_smooth_scroll") and self._smooth_scroll:
            self._smooth_scroll.reset(0)
        self.verticalScrollBar().setValue(0)
        QTimer.singleShot(0, self._do_scroll_to_top)
        QTimer.singleShot(40, self._do_scroll_to_top)

    def _do_scroll_to_top(self) -> None:
        if hasattr(self, "_smooth_scroll") and self._smooth_scroll:
            self._smooth_scroll.reset(0)
        self.verticalScrollBar().setValue(0)

    def _on_started(self, script_name: str) -> None:
        self._progress_bar.setValue(25)
        self._step_desc.setText("Analyzing marker trajectories & joint centers...")

    def _on_progress(self, status: ProcessingStatus) -> None:
        self._progress_bar.setValue(max(status.progress, 30))
        if status.message:
            self._step_desc.setText(status.message)

    def _on_finished(self, status: ProcessingStatus) -> None:
        if status.step == "complete" or status.completed:
            self._progress_bar.setValue(100)
            self._update_completion_details()
            QTimer.singleShot(300, lambda g=self._analysis_generation: self._show_completion_view() if g == self._analysis_generation else None)
        elif status.step == "error":
            self._live_status.setText("● Error")
            self._live_status.setObjectName("badge")
            err_msg = status.message
            if status.errors:
                err_msg += f"\n{status.errors[-1]}"
            self._step_desc.setText(err_msg)

    def _show_completion_view(self) -> None:
        self._stack.setCurrentWidget(self._completion_widget)
        self.scroll_to_top()

    def _update_completion_details(self) -> None:
        fname = self._filename or (os.path.basename(self._file_path_edit.text().strip()) if self._file_path_edit.text().strip() else "Static Trial")
        self._comp_subtitle.setText(f"Static trial '{fname}' processed successfully. Anatomical reference frames established.")
        self._comp_trial_lbl.setText(fname)

        first = self._first_name.text().strip()
        last = self._last_name.text().strip()
        patient_name = f"{first} {last}".strip()
        mrn = self._patient_number.text().strip()
        if patient_name and mrn:
            self._comp_patient_lbl.setText(f"{patient_name} (MRN {mrn})")
        elif patient_name:
            self._comp_patient_lbl.setText(patient_name)
        elif mrn:
            self._comp_patient_lbl.setText(f"MRN: {mrn}")
        else:
            self._comp_patient_lbl.setText("—")

        activity = self._trial_activity.currentText()
        modifier = self._trial_modifier.currentText()
        self._comp_activity_lbl.setText(f"{activity} — {modifier}")

        frame = self._static_frame_num.text().strip() or "20"
        self._comp_frame_lbl.setText(f"Frame {frame} (Static Center)")

        self._comp_hjc_lbl.setText(self._hip_combo.currentText())
        self._comp_coord_lbl.setText(self._coord_combo.currentText())

    def _on_error(self, err_msg: str) -> None:
        self._live_status.setText("● Error")
        self._live_status.setStyleSheet("color: #404040; border: none;")
        self._step_desc.setText(err_msg)

    def _on_cancel_clicked(self) -> None:
        self._service.cancel()
        self._stack.setCurrentWidget(self._config_widget)
        self.scroll_to_top()

    def _on_continue_clicked(self) -> None:
        self.proceed_to_dynamic.emit(self._session_path, self._filename)
