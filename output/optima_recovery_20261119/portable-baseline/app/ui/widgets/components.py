# -*- coding: utf-8 -*-
"""
Reusable UI widgets for the Shriners Gait Analysis Platform.

Every composite widget used across multiple pages is defined here so that the
visual language stays consistent and changes propagate automatically.
"""

from __future__ import annotations

from pathlib import Path
import re

from PySide6.QtCore import QByteArray, Qt, Signal, QSize, QPropertyAnimation, QEasingCurve, Property, QTimer, QEvent
from PySide6.QtGui import QFont, QColor, QPainter, QPainterPath, QIcon, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QGraphicsDropShadowEffect,
    QProgressBar,
)

from app.ui.theme.design_tokens import (
    FONT_FAMILY,
    FONT_FAMILY_MONO,
    FONT_SIZE_BODY,
    FONT_SIZE_CAPTION,
    FONT_SIZE_H1,
    FONT_SIZE_H2,
    FONT_SIZE_H3,
    FONT_SIZE_SMALL,
    RADIUS_LG,
    RADIUS_MD,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
    SPACE_XXS,
    LIGHT_PALETTE,
    COLOR_PRIMARY,
    COLOR_ACCENT,
    COLOR_MOTION,
    COLOR_NORMAL,
    COLOR_WARNING,
    COLOR_CRITICAL,
    COLOR_BACKGROUND,
    COLOR_SURFACE,
    COLOR_TEXT,
    COLOR_MUTED,
    COLOR_BORDER,
)
_cand1 = Path(__file__).resolve().parent.parent.parent.parent / "resources" / "icons"
_cand2 = Path(__file__).resolve().parent.parent.parent / "resources" / "icons"
ICONS_DIR = _cand1 if _cand1.is_dir() else _cand2

# ── Icon cache ──────────────────────────────────────────────────────────────
# SVG read + regex recolor + QPainter render is expensive. Cache keyed by
# (resolved_path, color, size) so every hover/poll reuse the same QIcon.
_icon_cache: dict = {}


def create_tinted_icon(svg_name_or_path: str | Path, stroke_color: str = "#404040", size: int = 16) -> QIcon:
    """Load an SVG icon from resources/icons, recolor stroke/fill cleanly, and return QIcon.
    Results are cached in-process so repeated calls for the same (path, color, size) are free.
    """
    try:
        p = Path(svg_name_or_path)
        if not p.is_file():
            p = ICONS_DIR / str(svg_name_or_path)
            if not p.is_file():
                return QIcon()

        cache_key = (str(p), stroke_color, size)
        cached = _icon_cache.get(cache_key)
        if cached is not None:
            return cached

        raw = p.read_text(encoding="utf-8")
        recolored = re.sub(r'stroke="[^"]*"', f'stroke="{stroke_color}"', raw)
        recolored = re.sub(r'fill="(?!none)[^"]*"', f'fill="{stroke_color}"', recolored)
        renderer = QSvgRenderer(QByteArray(recolored.encode("utf-8")))
        if not renderer.isValid():
            icon = QIcon(str(p))
            _icon_cache[cache_key] = icon
            return icon
        pix = QPixmap(size * 2, size * 2)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()
        pix.setDevicePixelRatio(2.0)
        icon = QIcon(pix)
        _icon_cache[cache_key] = icon
        return icon
    except Exception:
        return QIcon(str(svg_name_or_path))


def create_tinted_pixmap(svg_name_or_path: str | Path, stroke_color: str = "#404040", size: int = 16) -> QPixmap:
    """Load an SVG icon from resources/icons, recolor cleanly, and return QPixmap."""
    try:
        p = Path(svg_name_or_path)
        if not p.is_file():
            p = ICONS_DIR / str(svg_name_or_path)
            if not p.is_file():
                return QPixmap()

        raw = p.read_text(encoding="utf-8")
        recolored = re.sub(r'stroke="[^"]*"', f'stroke="{stroke_color}"', raw)
        recolored = re.sub(r'fill="(?!none)[^"]*"', f'fill="{stroke_color}"', recolored)
        renderer = QSvgRenderer(QByteArray(recolored.encode("utf-8")))
        if not renderer.isValid():
            return QPixmap(str(p))
        pix = QPixmap(size * 2, size * 2)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()
        pix.setDevicePixelRatio(2.0)
        return pix
    except Exception:
        return QPixmap(str(svg_name_or_path))



# ═══════════════════════════════════════════════════════════════════
#  StatusIndicator — coloured dot + label
# ═══════════════════════════════════════════════════════════════════

class StatusIndicator(QWidget):
    """Small status dot with accompanying text label."""

    _STATUS_COLORS = {
        "connected": COLOR_NORMAL,
        "disconnected": COLOR_MUTED,
        "processing": COLOR_MOTION,
        "ready": COLOR_PRIMARY,
        "idle": COLOR_MUTED,
        "error": COLOR_CRITICAL,
        "warning": COLOR_WARNING,
        "success": COLOR_NORMAL,
    }

    def __init__(self, status: str = "idle", text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._status = status
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_XS)

        self._dot = QLabel()
        self._dot.setFixedSize(10, 10)
        self._update_dot()

        self._label = QLabel(text or status.capitalize())
        self._label.setObjectName("captionLabel")

        layout.addWidget(self._dot)
        layout.addWidget(self._label)
        layout.addStretch()

    def set_status(self, status: str, text: str | None = None) -> None:
        self._status = status
        self._update_dot()
        if text is not None:
            self._label.setText(text)
        else:
            self._label.setText(status.capitalize())

    def _update_dot(self) -> None:
        color = self._STATUS_COLORS.get(self._status, "#808080")
        self._dot.setStyleSheet(
            f"background-color: {color}; border-radius: 5px; border: none;"
        )


# ═══════════════════════════════════════════════════════════════════
#  MetricCard — compact information card with title / value / subtext
# ═══════════════════════════════════════════════════════════════════

class MetricCard(QFrame):
    """Dashboard info card displaying a metric value."""

    clicked = Signal()

    # Automatic emoji to clean monochrome SVG icon mapping
    _EMOJI_SVG_MAP = {
        "👤": "patients.svg",
        "📁": "folder.svg",
        "🦶": "dynamic_analysis.svg",
        "⚙": "settings.svg",
        "⚙️": "settings.svg",
        "📊": "chart.svg",
        "📄": "file_text.svg",
        "🔌": "qtm_bridge.svg",
        "🎞": "camera.svg",
        "🎞️": "camera.svg",
        "📡": "radio.svg",
        "📏": "sliders.svg",
    }

    def __init__(
        self,
        title: str = "",
        value: str = "—",
        subtext: str = "",
        icon_text: str = "",
        icon_name: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("card")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        layout.setSpacing(SPACE_XXS)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(SPACE_SM)

        svg_target = icon_name or self._EMOJI_SVG_MAP.get(icon_text, "")
        self._svg_target = svg_target
        self._icon_lbl: QLabel | None = None
        self._is_dark = False

        if svg_target:
            self._icon_lbl = QLabel()
            self._icon_lbl.setFixedSize(18, 18)
            self._icon_lbl.setStyleSheet("background: transparent; border: none;")
            self._render_icon(COLOR_PRIMARY)
            header.addWidget(self._icon_lbl)
        elif icon_text:
            icon_lbl = QLabel(icon_text)
            icon_lbl.setObjectName("cardIconText")
            icon_lbl.setStyleSheet("font-size: 16px; background: transparent;")
            header.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("cardTitle")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        # Value
        self._value_label = QLabel(value)
        self._value_label.setObjectName("cardValue")
        layout.addWidget(self._value_label)

        # Subtext
        self._subtext_label = QLabel(subtext)
        self._subtext_label.setObjectName("cardSubtext")
        layout.addWidget(self._subtext_label)

    def _render_icon(self, color: str) -> None:
        if not self._svg_target or not self._icon_lbl:
            return
        from pathlib import Path
        icon_path = Path(__file__).resolve().parent.parent.parent.parent / "resources" / "icons" / self._svg_target
        if not icon_path.is_file():
            return
        try:
            import re
            from PySide6.QtSvg import QSvgRenderer
            from PySide6.QtCore import QByteArray
            from PySide6.QtGui import QPixmap, QPainter
            raw = icon_path.read_text(encoding="utf-8")
            recolored = re.sub(r'stroke="[^"]*"', f'stroke="{color}"', raw)
            recolored = re.sub(r'fill="(?!none)[^"]*"', f'fill="{color}"', recolored)
            renderer = QSvgRenderer(QByteArray(recolored.encode("utf-8")))
            if renderer.isValid():
                pix = QPixmap(36, 36)
                pix.fill(Qt.transparent)
                painter = QPainter(pix)
                renderer.render(painter)
                painter.end()
                pix.setDevicePixelRatio(2.0)
                self._icon_lbl.setPixmap(pix)
        except Exception:
            pass

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        self._is_dark = dark
        color = palette.accent if (palette and dark) else (palette.primary if palette else (COLOR_ACCENT if dark else COLOR_PRIMARY))
        self._render_icon(color)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)

    def set_subtext(self, text: str) -> None:
        self._subtext_label.setText(text)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


# ═══════════════════════════════════════════════════════════════════
#  SectionCard — titled container with border
# ═══════════════════════════════════════════════════════════════════

class SectionCard(QFrame):
    """A titled card container for grouping related controls."""

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        self._layout.setSpacing(SPACE_SM)

        if title:
            lbl = QLabel(title)
            lbl.setObjectName("sectionTitle")
            self._layout.addWidget(lbl)

        # Content area — callers add widgets to this
        self._content = QVBoxLayout()
        self._content.setSpacing(SPACE_SM)
        self._layout.addLayout(self._content)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content

    def add_widget(self, widget: QWidget) -> None:
        self._content.addWidget(widget)

    def add_layout(self, layout) -> None:
        self._content.addLayout(layout)


# ═══════════════════════════════════════════════════════════════════
#  CollapsibleSectionCard — titled container with expandable content
# ═══════════════════════════════════════════════════════════════════

class CollapsibleSectionCard(QFrame):
    """A titled card container with an expandable/collapsible content section."""

    toggled = Signal(bool)  # Emits True when expanded, False when collapsed

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        collapsed: bool = True,
        expand_text: str = "Configure File Paths ▾",
        collapse_text: str = "Hide File Paths ▴",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self._expand_text = expand_text
        self._collapse_text = collapse_text
        self._is_collapsed = collapsed

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        self._main_layout.setSpacing(SPACE_SM)

        # Header row (Title + Subtitle on left, Toggle Button on right)
        header_row = QHBoxLayout()
        header_row.setSpacing(SPACE_MD)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        if title:
            self._title_lbl = QLabel(title)
            self._title_lbl.setObjectName("sectionTitle")
            title_col.addWidget(self._title_lbl)
        if subtitle:
            self._subtitle_lbl = QLabel(subtitle)
            self._subtitle_lbl.setObjectName("pageHeaderSub")
            self._subtitle_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION))
            self._subtitle_lbl.setWordWrap(True)
            title_col.addWidget(self._subtitle_lbl)
        header_row.addLayout(title_col, 1)

        self._toggle_btn = QPushButton(self._expand_text if collapsed else self._collapse_text)
        self._toggle_btn.setObjectName("secondaryButton")
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.setFixedHeight(30)
        self._toggle_btn.setToolTip("Click to expand or collapse section")
        self._toggle_btn.clicked.connect(self.toggle)
        header_row.addWidget(self._toggle_btn, 0, Qt.AlignVCenter)

        self._main_layout.addLayout(header_row)

        # Collapsible container widget
        self._container = QWidget()
        self._content = QVBoxLayout(self._container)
        self._content.setContentsMargins(0, SPACE_SM, 0, 0)
        self._content.setSpacing(SPACE_SM)
        self._main_layout.addWidget(self._container)

        self._container.setVisible(not collapsed)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content

    def add_widget(self, widget: QWidget) -> None:
        self._content.addWidget(widget)

    def add_layout(self, layout) -> None:
        self._content.addLayout(layout)

    def is_collapsed(self) -> bool:
        return self._is_collapsed

    def set_collapsed(self, collapsed: bool) -> None:
        self._is_collapsed = collapsed
        self._container.setVisible(not collapsed)
        self._toggle_btn.setText(self._expand_text if collapsed else self._collapse_text)
        self.toggled.emit(not collapsed)

    def toggle(self) -> None:
        self.set_collapsed(not self._is_collapsed)


# ═══════════════════════════════════════════════════════════════════
#  SearchBar — line edit with placeholder
# ═══════════════════════════════════════════════════════════════════

class SearchBar(QLineEdit):
    """Styled search input."""

    def __init__(self, placeholder: str = "Search...", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("searchBar")
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.setMinimumHeight(36)


# ═══════════════════════════════════════════════════════════════════
#  Notification Banner — inline toast-like message
# ═══════════════════════════════════════════════════════════════════

class NotificationBanner(QFrame):
    """Inline notification that auto-hides after a configurable timeout."""

    dismissed = Signal()

    _STYLE_MAP = {
        "success": ("notificationSuccess", "✓"),
        "warning": ("notificationWarning", "⚠"),
        "error": ("notificationError", "✕"),
        "info": ("notificationInfo", "ℹ"),
    }

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("notificationInfo")
        self.setVisible(False)
        self.setFixedHeight(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_MD, SPACE_XS, SPACE_MD, SPACE_XS)
        layout.setSpacing(SPACE_SM)

        self._icon = QLabel()
        self._icon.setStyleSheet("background: transparent; font-size: 16px;")
        layout.addWidget(self._icon)

        self._message = QLabel()
        self._message.setStyleSheet("background: transparent;")
        layout.addWidget(self._message, 1)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("iconButton")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.hide)
        layout.addWidget(close_btn)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._auto_hide)

    def show_message(
        self, message: str, level: str = "info", timeout_ms: int = 5000
    ) -> None:
        obj_name, icon = self._STYLE_MAP.get(level, self._STYLE_MAP["info"])
        self.setObjectName(obj_name)
        # Force style recalculation
        self.style().unpolish(self)
        self.style().polish(self)
        self._icon.setText(icon)
        self._message.setText(message)
        self.setVisible(True)
        if timeout_ms > 0:
            self._timer.start(timeout_ms)

    def _auto_hide(self) -> None:
        self.setVisible(False)
        self.dismissed.emit()


# ═══════════════════════════════════════════════════════════════════
#  EmptyState — placeholder for pages with no data loaded
# ═══════════════════════════════════════════════════════════════════

class EmptyState(QWidget):
    """Centered placeholder shown when a page has no content yet."""

    action_clicked = Signal()

    def __init__(
        self,
        icon_text: str = "",
        icon_name: str = "folder.svg",
        title: str = "No data",
        description: str = "",
        action_label: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(SPACE_SM)

        self._icon_lbl = QLabel()
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setStyleSheet("background: transparent; border: none;")

        svg_target = icon_name or ("chart.svg" if "📊" in icon_text else ("folder.svg" if "📂" in icon_text or "📁" in icon_text else ""))
        if svg_target:
            self._icon_lbl.setPixmap(create_tinted_pixmap(svg_target, COLOR_MUTED, 48))
        elif icon_text:
            self._icon_lbl.setText(icon_text)
            self._icon_lbl.setStyleSheet("font-size: 40px; background: transparent;")
        layout.addWidget(self._icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(
            f"font-size: {FONT_SIZE_H3}px; font-weight: 600; background: transparent;"
        )
        layout.addWidget(title_lbl)

        if description:
            desc_lbl = QLabel(description)
            desc_lbl.setAlignment(Qt.AlignCenter)
            desc_lbl.setWordWrap(True)
            desc_lbl.setObjectName("captionLabel")
            layout.addWidget(desc_lbl)

        if action_label:
            btn = QPushButton(action_label)
            btn.setObjectName("primaryButton")
            btn.setFixedWidth(200)
            btn.clicked.connect(self.action_clicked.emit)
            layout.addWidget(btn, alignment=Qt.AlignCenter)


# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
#  LoadingOverlay — translucent clinical overlay with progress & status
# ═══════════════════════════════════════════════════════════════════

class LoadingOverlay(QWidget):
    """
    Translucent, medical-grade loading screen overlay with progress bar,
    clinical title, dynamic status details, and theme responsiveness.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setVisible(False)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self._is_dark = False

        # Outer layout: centers the loading dialog card
        outer_layout = QVBoxLayout(self)
        outer_layout.setAlignment(Qt.AlignCenter)
        outer_layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)

        # Centered elevated modal-style card
        self._card = QFrame()
        self._card.setObjectName("loadingCard")
        self._card.setFixedWidth(520)
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        card_layout.setSpacing(SPACE_MD)
        card_layout.setAlignment(Qt.AlignCenter)

        # Pulse / Activity badge indicator
        self._spinner_badge = QLabel("● PROCESSING GAIT DATA")
        self._spinner_badge.setObjectName("badge")
        self._spinner_badge.setAlignment(Qt.AlignCenter)
        self._spinner_badge.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, QFont.Bold))
        card_layout.addWidget(self._spinner_badge)

        # Title
        self._title_label = QLabel("Loading Presentation Graphs")
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setWordWrap(True)
        self._title_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_H3, QFont.Bold))
        card_layout.addWidget(self._title_label)

        # Detailed step message
        self._message = QLabel("Processing GCD trials and rendering plots...")
        self._message.setAlignment(Qt.AlignCenter)
        self._message.setWordWrap(True)
        self._message.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        card_layout.addWidget(self._message)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setFixedHeight(8)
        self._progress.setTextVisible(False)
        self._progress.setRange(0, 100)
        card_layout.addWidget(self._progress)

        # Step count / percentage status caption
        self._status_caption = QLabel("Please wait...")
        self._status_caption.setAlignment(Qt.AlignCenter)
        self._status_caption.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_CAPTION))
        card_layout.addWidget(self._status_caption)

        outer_layout.addWidget(self._card)

        if parent:
            parent.installEventFilter(self)
            self.resize(parent.size())

        self.apply_theme(dark=False)

    def eventFilter(self, watched, event):
        if watched == self.parent() and event.type() == QEvent.Resize:
            self.resize(watched.size())
            self.raise_()
        return super().eventFilter(watched, event)

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        self._is_dark = dark
        if dark:
            card_bg = "#1E293B"
            card_border = "#334155"
            title_col = "#F8FAFC"
            msg_col = "#94A3B8"
            caption_col = "#64748B"
            badge_bg = "#134E4A"
            badge_fg = "#2DD4BF"
            badge_border = "#14B8A6"
            prog_bg = "#334155"
            prog_fg = "#2DD4BF"
        else:
            card_bg = "#FFFFFF"
            card_border = "#CBD5E1"
            title_col = "#0F172A"
            msg_col = "#475569"
            caption_col = "#94A3B8"
            badge_bg = "#F0FDFA"
            badge_fg = "#0F766E"
            badge_border = "#99F6E4"
            prog_bg = "#E2E8F0"
            prog_fg = "#0D9488"

        self._card.setStyleSheet(f"""
            QFrame#loadingCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: {RADIUS_LG}px;
            }}
        """)
        self._spinner_badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_fg};
            border: 1px solid {badge_border};
            border-radius: 10px;
            padding: 3px 14px;
            font-weight: 700;
        """)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {prog_bg};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {prog_fg};
                border-radius: 4px;
            }}
        """)
        self._title_label.setStyleSheet(f"color: {title_col}; background: transparent; border: none;")
        self._message.setStyleSheet(f"color: {msg_col}; background: transparent; border: none;")
        self._status_caption.setStyleSheet(f"color: {caption_col}; background: transparent; border: none;")
        self.update()

    def show_loading(
        self,
        message: str = "Processing GCD trials and rendering plots...",
        determinate: bool = True,
        title: str = "Loading Presentation Graphs",
    ) -> None:
        if self.parent():
            self.resize(self.parent().size())
        self._title_label.setText(title)
        self._message.setText(message)
        if determinate:
            self._progress.setRange(0, 100)
            self._progress.setValue(0)
            self._status_caption.setText("0%")
        else:
            self._progress.setRange(0, 0)
            self._status_caption.setText("Processing in progress...")
        self.setVisible(True)
        self.raise_()
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

    def set_progress(self, value: int, message: str | None = None, caption: str | None = None) -> None:
        self._progress.setValue(value)
        if message:
            self._message.setText(message)
        if caption:
            self._status_caption.setText(caption)
        else:
            self._status_caption.setText(f"{value}%")
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

    def hide_loading(self) -> None:
        self.setVisible(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._is_dark:
            painter.fillRect(self.rect(), QColor(15, 23, 42, 220))
        else:
            painter.fillRect(self.rect(), QColor(255, 255, 255, 220))
        super().paintEvent(event)


# ═══════════════════════════════════════════════════════════════════
#  TrialCheckbox — styled checkbox for L/R trial selection
# ═══════════════════════════════════════════════════════════════════

from PySide6.QtWidgets import QCheckBox


class TrialCheckbox(QCheckBox):
    """Checkbox styled for trial selection (L1-L5, R1-R5)."""

    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(label, parent)
        self.setMinimumHeight(28)


# ═══════════════════════════════════════════════════════════════════
#  ProcessingStep — single pipeline step indicator
# ═══════════════════════════════════════════════════════════════════

class ProcessingStep(QFrame):
    """One row of the processing pipeline status display."""

    def __init__(
        self,
        step_number: int,
        title: str,
        status: str = "pending",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_SM, SPACE_XS, SPACE_SM, SPACE_XS)
        layout.setSpacing(SPACE_SM)

        self._status_icons = {
            "pending": "○",
            "running": "●",
            "complete": "✓",
            "error": "✕",
        }

        self._num_label = QLabel(f"{step_number:02d}")
        self._num_label.setStyleSheet(
            f"font-size: {FONT_SIZE_CAPTION}px; color: {COLOR_MUTED}; font-weight: 600; background: transparent;"
        )
        self._num_label.setFixedWidth(28)
        layout.addWidget(self._num_label)

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("background: transparent;")
        layout.addWidget(self._title_label, 1)

        self._status_label = QLabel(self._status_icons.get(status, "○"))
        self._status_label.setFixedWidth(24)
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setStyleSheet("background: transparent; font-size: 16px;")
        layout.addWidget(self._status_label)

        self.set_status(status)

    def set_status(self, status: str) -> None:
        self.status = status
        icon = self._status_icons.get(status, "○")
        color_map = {
            "pending": COLOR_MUTED,
            "running": COLOR_MOTION,
            "complete": COLOR_NORMAL,
            "error": COLOR_CRITICAL,
        }
        color = color_map.get(status, COLOR_MUTED)
        self._status_label.setText(icon)
        self._status_label.setStyleSheet(
            f"background: transparent; font-size: 16px; color: {color}; font-weight: bold;"
        )
