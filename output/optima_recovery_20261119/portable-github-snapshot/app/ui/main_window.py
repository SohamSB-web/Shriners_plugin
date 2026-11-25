# -*- coding: utf-8 -*-
"""
Main Window — the application shell with workflow navigation, header,
content area, and status bar.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict

from PySide6.QtCore import Qt, QSize, Signal, Slot, QTimer, QSignalBlocker
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.models.data_models import AppSettings
from app.services.settings_service import SettingsService
from app.ui.pages.case_presentation_page import CasePresentationPage, NO_PRESENTATION_SELECTION, NO_PROCESSED_TRIALS
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.dynamic_analysis_page import DynamicAnalysisPage
from app.ui.pages.patients_page import PatientsPage
from app.ui.pages.qtm_page import QTMMonitorPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.static_analysis_page import StaticAnalysisPage
from app.ui.theme.design_tokens import (
    FONT_FAMILY,
    FONT_SIZE_BODY,
    FONT_SIZE_CAPTION,
    FONT_SIZE_H3,
    FONT_SIZE_SMALL,
    LIGHT_PALETTE,
    DARK_PALETTE,
    ColorPalette,
    SIDEBAR_ICON_SIZE,
    SIDEBAR_WIDTH_EXPANDED,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
)
from app.ui.theme.theme_manager import (
    apply_native_titlebar_theme,
    get_dark_qss,
    get_light_qss,
)
from app.ui.widgets.components import StatusIndicator, LoadingOverlay
from app.ui.widgets.workflow_bar import WorkflowBar

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  Sidebar
# ═══════════════════════════════════════════════════════════════════

class AppSidebar(QFrame):
    """Left sidebar — minimal monochrome navigation."""

    page_selected = Signal(str)

    NAV_ITEMS = [
        ("dashboard", "Overview", "dashboard.svg"),
        ("static_analysis", "Static Analysis", "static_analysis.svg"),
        ("dynamic_analysis", "Dynamic Analysis", "dynamic_analysis.svg"),
        ("patients", "Patients && Sessions", "patients.svg"),
        ("case_presentation", "Case Presentation", "case_presentation.svg"),
        ("qtm", "QTM Bridge", "qtm_bridge.svg"),
        ("settings", "Settings", "settings.svg"),
    ]

    @staticmethod
    def _create_tinted_icon(svg_path: Path, stroke_color: str, size: int = 18) -> QIcon:
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

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH_EXPANDED)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Brand Header — clean, minimal
        icons_dir = Path(__file__).resolve().parent.parent.parent / "resources" / "icons"
        self._icons_dir = icons_dir

        brand_frame = QFrame()
        brand_frame.setStyleSheet("background: transparent; border: none;")
        brand_frame.setFixedHeight(64)
        brand_layout = QHBoxLayout(brand_frame)
        brand_layout.setContentsMargins(SPACE_MD, SPACE_SM, SPACE_MD, SPACE_SM)
        brand_layout.setSpacing(SPACE_SM)

        emblem_path = icons_dir / "shriners_emblem.svg"
        self._emblem_path = emblem_path
        if emblem_path.is_file():
            self._emblem_lbl = QLabel()
            self._emblem_lbl.setPixmap(self._create_tinted_icon(emblem_path, LIGHT_PALETTE.text_primary, 32).pixmap(32, 32))
            self._emblem_lbl.setStyleSheet("background: transparent; border: none;")
            brand_layout.addWidget(self._emblem_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)

        self._logo = QLabel("SHRINERS")
        self._logo.setStyleSheet(
            f"color: {LIGHT_PALETTE.text_primary}; font-size: 15px; font-weight: 700; "
            f"background: transparent; padding: 0;"
        )
        title_col.addWidget(self._logo)

        self._subtitle = QLabel("CHILDRENS HOSPITAL")
        self._subtitle.setStyleSheet(
            f"color: {LIGHT_PALETTE.text_muted}; font-size: 11px; font-weight: 600; "
            f"background: transparent; padding: 0;"
        )
        title_col.addWidget(self._subtitle)

        brand_layout.addLayout(title_col)
        brand_layout.addStretch()
        layout.addWidget(brand_frame)

        # Thin separator
        self._sep = QFrame()
        self._sep.setFrameShape(QFrame.HLine)
        self._sep.setStyleSheet(f"background-color: {LIGHT_PALETTE.border}; max-height: 1px; border: none;")
        layout.addWidget(self._sep)

        # Spacer above nav
        layout.addSpacing(SPACE_XS)

        # ── Navigation Buttons
        self._buttons: Dict[str, QPushButton] = {}
        self._normal_icons: Dict[str, QIcon] = {}
        self._active_icons: Dict[str, QIcon] = {}

        for key, label, icon_name in self.NAV_ITEMS:
            btn = QPushButton(f"  {label}")
            btn.setObjectName("sidebarButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(label.replace("&&", "&"))

            icon_file = icons_dir / icon_name
            if icon_file.is_file():
                normal_ico = self._create_tinted_icon(icon_file, LIGHT_PALETTE.text_on_sidebar, SIDEBAR_ICON_SIZE)
                active_ico = self._create_tinted_icon(icon_file, LIGHT_PALETTE.text_on_sidebar_active, SIDEBAR_ICON_SIZE)
                self._normal_icons[key] = normal_ico
                self._active_icons[key] = active_ico
                btn.setIcon(normal_ico)
                btn.setIconSize(QSize(SIDEBAR_ICON_SIZE, SIDEBAR_ICON_SIZE))

            btn.clicked.connect(lambda checked, k=key: self._on_click(k))
            layout.addWidget(btn)
            self._buttons[key] = btn

        layout.addStretch()

        # ── Bottom status — ultra minimal
        self._v_lbl = QLabel("  v2.0")
        self._v_lbl.setStyleSheet(
            f"color: {LIGHT_PALETTE.text_muted}; font-size: 10px; "
            f"background: transparent; padding: 4px {SPACE_MD}px 8px {SPACE_MD}px;"
        )
        layout.addWidget(self._v_lbl)

        self._active_key = ""

    def apply_theme(self, palette: ColorPalette | None = None, dark: bool = False) -> None:
        """Dynamically re-tint logos, text, and navigation icons on theme toggle."""
        pal = palette or (DARK_PALETTE if dark else LIGHT_PALETTE)
        self._is_dark = dark

        # Emblem SVG: in dark mode, accent (#14B8A6); in light mode, primary (#0F766E)
        emblem_col = pal.accent if dark else pal.primary
        if hasattr(self, "_emblem_lbl") and hasattr(self, "_emblem_path") and self._emblem_path.is_file():
            self._emblem_lbl.setPixmap(self._create_tinted_icon(self._emblem_path, emblem_col, 32).pixmap(32, 32))

        if hasattr(self, "_logo"):
            self._logo.setStyleSheet(
                f"color: {pal.primary if not dark else pal.text_primary}; font-size: 15px; font-weight: 700; "
                f"background: transparent; padding: 0;"
            )
        if hasattr(self, "_subtitle"):
            self._subtitle.setStyleSheet(
                f"color: {pal.text_muted}; font-size: 11px; font-weight: 600; "
                f"background: transparent; padding: 0;"
            )
        if hasattr(self, "_sep"):
            self._sep.setStyleSheet(f"background-color: {pal.border}; max-height: 1px; border: none;")
        if hasattr(self, "_v_lbl"):
            self._v_lbl.setStyleSheet(
                f"color: {pal.text_muted}; font-size: 10px; "
                f"background: transparent; padding: 4px {SPACE_MD}px 8px {SPACE_MD}px;"
            )

        # Re-tint navigation icons for crisp high contrast
        for key, label, icon_name in self.NAV_ITEMS:
            icon_file = self._icons_dir / icon_name
            if icon_file.is_file():
                norm_ico = self._create_tinted_icon(icon_file, pal.text_on_sidebar, SIDEBAR_ICON_SIZE)
                act_ico = self._create_tinted_icon(icon_file, pal.text_on_sidebar_active, SIDEBAR_ICON_SIZE)
                self._normal_icons[key] = norm_ico
                self._active_icons[key] = act_ico
                btn = self._buttons.get(key)
                if btn:
                    btn.setIcon(act_ico if key == self._active_key else norm_ico)
                    btn.style().unpolish(btn)
                    btn.style().polish(btn)

    def _on_click(self, key: str) -> None:
        self.set_active(key)
        self.page_selected.emit(key)

    def set_active(self, key: str) -> None:
        self._active_key = key
        for k, btn in self._buttons.items():
            is_active = (k == key)
            btn.setProperty("active", is_active)
            if is_active and k in self._active_icons:
                btn.setIcon(self._active_icons[k])
            elif not is_active and k in self._normal_icons:
                btn.setIcon(self._normal_icons[k])
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def update_status(self, status: str, text: str) -> None:
        pass


# ═══════════════════════════════════════════════════════════════════
#  Header Bar
# ═══════════════════════════════════════════════════════════════════

class AppHeader(QFrame):
    """Top header — minimal with workflow stepper."""

    def __init__(self, workflow_bar: WorkflowBar, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("header")
        self.setFixedHeight(52)
        self.setStyleSheet(
            f"QFrame#header {{ background-color: {LIGHT_PALETTE.bg_header}; "
            f"border-bottom: 1px solid {LIGHT_PALETTE.border}; }}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_LG, 0, SPACE_LG, 0)
        layout.setSpacing(SPACE_MD)

        # Embedded Clinical Workflow Stepper
        self.workflow_bar = workflow_bar
        layout.addWidget(self.workflow_bar)

        layout.addStretch()

        # Patient indicator
        self._patient_label = QLabel("")
        self._patient_label.setStyleSheet(
            f"font-size: {FONT_SIZE_CAPTION}px; color: {LIGHT_PALETTE.text_muted}; background: transparent;"
        )
        layout.addWidget(self._patient_label)

        # Connection status dot
        self._connection = StatusIndicator("disconnected", "QTM")
        layout.addWidget(self._connection)

    def apply_theme(self, palette: ColorPalette | None = None, dark: bool = False) -> None:
        """Update header background, border, text, and workflow bar."""
        pal = palette or (DARK_PALETTE if dark else LIGHT_PALETTE)
        self.setStyleSheet(
            f"QFrame#header {{ background-color: {pal.bg_header}; "
            f"border-bottom: 1px solid {pal.border}; }}"
        )
        self._patient_label.setStyleSheet(
            f"font-size: {FONT_SIZE_CAPTION}px; color: {pal.text_muted}; background: transparent;"
        )
        self.workflow_bar.apply_theme(pal, dark)

    def set_patient(self, mrn: str) -> None:
        self._patient_label.setText(f"Patient: {mrn}" if mrn else "")

    def set_connection_status(self, connected: bool) -> None:
        if connected:
            self._connection.set_status("connected", "QTM Bridge Listening")
        else:
            self._connection.set_status("disconnected", "QTM")


# ═══════════════════════════════════════════════════════════════════
#  Main Window
# ═══════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    """
    Main application shell for Shriners Gait Analysis workstation.
    """

    def __init__(self, settings: AppSettings | None = None, splash: QWidget | None = None):
        super().__init__()
        self._settings = settings or AppSettings()
        self._settings_svc = SettingsService()
        self._active_analysis_context = None
        self._splash = splash
        self._should_maximize = False

        self._setup_window()
        self._create_ui()
        self._connect_signals()
        self._navigate_to("static_analysis")

        # Apply theme
        self._apply_theme(self._settings.dark_mode)

    def show(self) -> None:
        """Show window, maximizing if appropriate for display resolution."""
        if getattr(self, "_should_maximize", False):
            self.showMaximized()
        else:
            super().show()

    def _setup_window(self) -> None:
        self.setWindowTitle(
            f"Shriners Gait Analysis Platform — {self._settings.institute_name}"
        )

        # Set official window icon
        icon_path = Path(__file__).resolve().parent.parent.parent / "resources" / "icons" / "shriners_logo.png"
        if not icon_path.is_file():
            icon_path = Path(__file__).resolve().parent.parent.parent / "resources" / "icons" / "shriners_emblem.svg"
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Responsive window sizing according to active display geometry and DPI scaling
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            # Adaptive minimum size so it fits on 125%/150% scaled displays and compact laptops
            min_w = min(1000, max(750, int(avail.width() * 0.75)))
            min_h = min(600, max(450, int(avail.height() * 0.75)))
            self.setMinimumSize(min_w, min_h)

            # Target size: fit comfortably within available desktop area with margins
            target_w = min(1500, max(min_w, avail.width() - 40))
            target_h = min(920, max(min_h, avail.height() - 50))
            self.resize(target_w, target_h)

            # Center safely inside available screen geometry (never negative coordinates!)
            pos_x = avail.x() + max(0, (avail.width() - target_w) // 2)
            pos_y = avail.y() + max(0, (avail.height() - target_h) // 2)
            self.move(pos_x, pos_y)

            # For scaled or compact displays (e.g. 1080p @ 125% where avail height <= 880),
            # maximizing ensures zero clipping and fits perfectly within the taskbar boundaries
            if avail.width() <= 1550 or avail.height() <= 880:
                self._should_maximize = True
        else:
            self.setMinimumSize(950, 600)
            self.resize(1300, 800)

    def _create_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self._sidebar = AppSidebar()
        main_layout.addWidget(self._sidebar)

        # Right side: header + content
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        self._workflow_bar = WorkflowBar(current_stage="static_analysis")
        self._header = AppHeader(self._workflow_bar)
        right.addWidget(self._header)

        # Stacked pages
        self._pages = QStackedWidget()
        self._page_map: Dict[str, QWidget] = {}

        # Primary Workflow Pages
        self._static_page = StaticAnalysisPage()
        self._dynamic_page = DynamicAnalysisPage()
        self._presentation_page = CasePresentationPage()

        # Supporting Pages
        self._dashboard = DashboardPage()
        self._patients = PatientsPage()
        if self._settings.patients_data_location:
            self._static_page.set_data_root(self._settings.patients_data_location)
            self._patients.set_patients_data_root(self._settings.patients_data_location)
        self._qtm = QTMMonitorPage()
        self._settings_page = SettingsPage(self._settings)

        for key, page in [
            ("dashboard", self._dashboard),
            ("static_analysis", self._static_page),
            ("dynamic_analysis", self._dynamic_page),
            ("patients", self._patients),
            ("case_presentation", self._presentation_page),
            ("qtm", self._qtm),
            ("settings", self._settings_page),
        ]:
            self._pages.addWidget(page)
            self._page_map[key] = page

        right.addWidget(self._pages, 1)
        main_layout.addLayout(right, 1)

        # Global loading overlay for background tasks and long-running analysis
        self._loading_overlay = LoadingOverlay(central)

        # Status bar
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        self._status_label = QLabel("Clinical workstation ready")
        status_bar.addPermanentWidget(self._status_label)

    def _connect_signals(self) -> None:
        # Sidebar navigation
        self._sidebar.page_selected.connect(self._navigate_to)

        # Workflow stepper navigation
        self._workflow_bar.stage_selected.connect(self._navigate_to)

        # Pipeline flow connections
        self._static_page.proceed_to_dynamic.connect(self._on_static_to_dynamic)
        self._dynamic_page.proceed_to_patients.connect(self._on_dynamic_to_patients)

        # Dashboard navigation
        self._dashboard.navigate_to.connect(self._navigate_to)

        # Patient selection flow
        self._patients.patient_selected.connect(self._on_patient_selected)
        self._patients.analysis_context_selected.connect(self._on_analysis_context_selected)
        self._static_page.session_selected.connect(self._on_calibration_session_selected)
        self._patients.proceed_to_analysis.connect(self._on_proceed_from_patients)
        self._patients.open_session_presentation.connect(self._on_open_single_session_presentation)
        self._presentation_page.presentation_unavailable.connect(self._redirect_from_presentation)

        # QTM connection
        self._qtm.connection_changed.connect(self._on_qtm_connection)

        # Settings
        self._settings_page.theme_changed.connect(self._apply_theme)
        self._settings_page.settings_saved.connect(self._on_settings_saved)

    # ── Navigation ──────────────────────────────────────────────────

    PAGE_TITLES = {
        "dashboard": "Overview",
        "static_analysis": "Static Analysis",
        "dynamic_analysis": "Dynamic Analysis",
        "patients": "Patient & Session Selection",
        "case_presentation": "Case Presentation",
        "qtm": "QTM Bridge",
        "settings": "Settings",
    }

    @Slot(str)
    def _navigate_to(self, page_key: str) -> None:
        if page_key == "case_presentation" and (
                not self._patients.has_selected_patient() or not self._presentation_page._trial_data
                or not self._presentation_page._session_path
                or not any(Path(gcd.file_path).is_file() for gcd in self._presentation_page._trial_data.values())):
            message = (NO_PROCESSED_TRIALS if self._patients.has_selected_patient()
                       and getattr(self, "_presentation_requested_directory", "") else NO_PRESENTATION_SELECTION)
            self._redirect_from_presentation(message)
            return
        page = self._page_map.get(page_key)
        if page:
            self._pages.setCurrentWidget(page)
            self._sidebar.set_active(page_key)
            if page_key in ["static_analysis", "dynamic_analysis", "patients", "case_presentation"]:
                self._workflow_bar.set_active_stage(page_key)
            self._status_label.setText(f"{self.PAGE_TITLES.get(page_key, page_key.title())} active")
            logger.info("Navigated to: %s", page_key)

    def _redirect_from_presentation(self, message: str) -> None:
        self._presentation_page.clear_session()
        self._patients.show_presentation_notice(message)
        self._presentation_notice_message = message
        if not getattr(self, "_presentation_redirect_pending", False):
            self._presentation_redirect_pending = True
            QTimer.singleShot(0, self._show_patients_for_presentation)

    def _show_patients_for_presentation(self) -> None:
        self._presentation_redirect_pending = False
        if self._presentation_page._trial_data:
            return  # A valid explicit selection supersedes an older queued redirect.
        self._navigate_to("patients")
        self._status_label.setText(self._presentation_notice_message)

    # ── Workflow Transitions ────────────────────────────────────────

    @Slot(str, str)
    def _on_static_to_dynamic(self, session_path: str, static_file: str) -> None:
        """Handle completion of static calibration and transition to dynamic trials."""
        self._workflow_bar.mark_completed("static_analysis")
        self._dynamic_page.load_session(session_path)
        self._navigate_to("dynamic_analysis")

    @Slot(str)
    def _on_dynamic_to_patients(self, session_path: str) -> None:
        """Handle completion of dynamic processing and transition to Patients & Sessions."""
        self._workflow_bar.mark_completed("dynamic_analysis")
        self._patients.load_session(session_path)
        self._navigate_to("patients")

    @Slot(str)
    def _on_dynamic_to_presentation(self, session_path: str) -> None:
        """Fallback direct transition to MAC Case Presentation (for tests / legacy callers)."""
        self._workflow_bar.mark_completed("dynamic_analysis")
        self._patients.load_session(session_path)
        self._on_proceed_from_patients()

    @Slot(str)
    def _on_patient_selected(self, mrn: str) -> None:
        if mrn != getattr(self, "_presentation_patient", ""):
            self._presentation_page.clear_session()
            self._presentation_requested_directory = ""
            self._presentation_patient = mrn
            if self._pages.currentWidget() is self._presentation_page:
                self._redirect_from_presentation(NO_PRESENTATION_SELECTION)
        self._header.set_patient(mrn)
        self._dashboard.update_patient(mrn)
        self._status_label.setText(f"Patient: {mrn}")

    def _on_analysis_context_selected(self, patient: str, session_dir: str, session_xml: str | None = None) -> None:
        patient_identity = os.path.normcase(str(Path(patient).resolve())) if patient and os.path.isdir(patient) else (patient.casefold() if patient else "")
        session_identity = os.path.normcase(str(Path(session_dir).resolve())) if session_dir else ""
        identity = (patient_identity, session_identity)
        if identity == self._active_analysis_context:
            return
        self._active_analysis_context = identity
        self._presentation_page.clear_session()
        self._presentation_requested_directory = ""
        self._dynamic_page.clear_session()
        self._workflow_bar.mark_completed("static_analysis", False)
        self._workflow_bar.mark_completed("dynamic_analysis", False)

        xml = Path(session_xml).resolve() if session_xml else None
        if (xml is None or not xml.is_file()) and session_dir:
            cand = Path(session_dir).resolve() / "session.xml"
            if cand.is_file():
                xml = cand

        curr_static = (
            Path(self._static_page._session_path).resolve()
            if self._static_page._session_path
            else None
        )

        if curr_static is not None and curr_static != xml:
            self._static_page.clear_session()

    def _on_calibration_session_selected(self, session_xml: str) -> None:
        if not session_xml:
            return
        p = Path(session_xml).resolve()
        if p.is_file():
            session_dir = p.parent
            xml_path = str(p)
        elif p.is_dir():
            session_dir = p
            cand = session_dir / "session.xml"
            xml_path = str(cand) if cand.is_file() else None
        else:
            return

        patient_dir = session_dir.parent
        self._on_patient_selected(patient_dir.name)
        self._on_analysis_context_selected(str(patient_dir), str(session_dir), xml_path)

    @Slot()
    def _on_proceed_from_patients(self) -> None:
        """User configured sessions in Patients page -> route to MAC Case Presentation."""
        sessions = self._patients.get_all_sessions()
        index = next((i for i, session in enumerate(sessions) if session.directory), 0)
        self._on_open_single_session_presentation(index)

    @Slot(int)
    def _on_open_single_session_presentation(self, session_idx: int) -> None:
        """User clicked 'View MAC Case' for a specific session row."""
        sessions = self._patients.get_all_sessions()
        if not self._patients.has_selected_patient():
            self._redirect_from_presentation(NO_PRESENTATION_SELECTION)
            return
        self._presentation_requested_directory = sessions[session_idx].directory if 0 <= session_idx < len(sessions) else ""
        display_mode = self._patients.get_display_mode()
        if not self._presentation_page.load_session_data(
            sessions, active_session_index=session_idx, display_mode=display_mode
        ):
            return
        self._patients.show_presentation_notice("")
        self._workflow_bar.mark_completed("patients")
        self._navigate_to("case_presentation")

    @Slot(bool)
    def _on_qtm_connection(self, connected: bool) -> None:
        self._header.set_connection_status(connected)
        self._dashboard.update_qtm_status(connected)

    @Slot(bool)
    def _apply_theme(self, dark: bool) -> None:
        palette = DARK_PALETTE if dark else LIGHT_PALETTE
        qss = get_dark_qss() if dark else get_light_qss()
        QApplication.instance().setStyleSheet(qss)
        self._settings.dark_mode = dark

        if hasattr(self, "_sidebar"):
            self._sidebar.apply_theme(palette, dark)
        if hasattr(self, "_header"):
            self._header.apply_theme(palette, dark)
        if hasattr(self, "_static_page") and hasattr(self._static_page, "apply_theme"):
            self._static_page.apply_theme(palette, dark)
        if hasattr(self, "_dynamic_page") and hasattr(self._dynamic_page, "apply_theme"):
            self._dynamic_page.apply_theme(palette, dark)
        if hasattr(self, "_presentation_page") and hasattr(self._presentation_page, "apply_theme"):
            self._presentation_page.apply_theme(palette, dark)
        if hasattr(self, "_dashboard") and hasattr(self._dashboard, "apply_theme"):
            self._dashboard.apply_theme(palette, dark)
        if hasattr(self, "_qtm") and hasattr(self._qtm, "apply_theme"):
            self._qtm.apply_theme(palette, dark)
        if hasattr(self, "_patients") and hasattr(self._patients, "apply_theme"):
            self._patients.apply_theme(palette, dark)
        if hasattr(self, "_update_measurements_page") and hasattr(self._update_measurements_page, "apply_theme"):
            self._update_measurements_page.apply_theme(palette, dark)
        if hasattr(self, "_settings_page") and hasattr(self._settings_page, "apply_theme"):
            self._settings_page.apply_theme(palette, dark)
        if hasattr(self, "_loading_overlay") and hasattr(self._loading_overlay, "apply_theme"):
            self._loading_overlay.apply_theme(palette, dark)

        # Synchronize native OS title bar with active UI theme
        apply_native_titlebar_theme(
            self,
            dark=dark,
            bg_color=palette.bg_header,
            fg_color=palette.text,
        )

        logger.info("Theme changed to %s", "dark" if dark else "light")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        palette = DARK_PALETTE if self._settings.dark_mode else LIGHT_PALETTE
        apply_native_titlebar_theme(
            self,
            dark=self._settings.dark_mode,
            bg_color=palette.bg_header,
            fg_color=palette.text,
        )

        # Force initial layout and first-frame widget render
        QApplication.processEvents()

        # If splash screen is active, finish progress and dismiss cleanly once rendered
        if hasattr(self, "_splash") and self._splash is not None:
            self._splash.set_progress(100, "Workstation ready.", "Rendering completed.")
            QTimer.singleShot(250, self._dismiss_splash)
        else:
            if hasattr(self, "_loading_overlay") and self._loading_overlay.isVisible():
                self._loading_overlay.hide_loading()

    def _dismiss_splash(self) -> None:
        """Dismiss startup splash screen once the main window layout has fully settled."""
        if hasattr(self, "_splash") and self._splash is not None:
            try:
                self._splash.close()
                self._splash.deleteLater()
            except Exception:
                pass
            self._splash = None
        if hasattr(self, "_loading_overlay") and self._loading_overlay.isVisible():
            self._loading_overlay.hide_loading()

    def show_loading(self, message: str = "Please wait...", title: str = "Loading") -> None:
        """Public method to display workstation loading screen."""
        if hasattr(self, "_loading_overlay"):
            self._loading_overlay.show_loading(message=message, title=title, determinate=False)

    def hide_loading(self) -> None:
        """Public method to hide workstation loading screen."""
        if hasattr(self, "_loading_overlay"):
            self._loading_overlay.hide_loading()

    @Slot(AppSettings)
    def _on_settings_saved(self, settings: AppSettings) -> None:
        self._settings = settings
        self.setWindowTitle(
            f"Shriners Gait Analysis Platform — {settings.institute_name}"
        )
        if hasattr(self, "_patients"):
            self._patients.set_patients_data_root(settings.patients_data_location)
        if hasattr(self, "_static_page"):
            self._static_page.set_data_root(settings.patients_data_location)
        self._status_label.setText("Settings saved")
