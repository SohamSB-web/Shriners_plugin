# -*- coding: utf-8 -*-
"""
QSS Theme Generator — Minimal Monochrome B&W.

Builds Qt Style Sheets from *design_tokens* palettes, so style definitions
live in one place and support live light ↔ dark switching.
"""

from __future__ import annotations

import logging
import sys

from app.ui.theme.design_tokens import (
    ColorPalette,
    DARK_PALETTE,
    FONT_FAMILY,
    FONT_FAMILY_MONO,
    FONT_SIZE_BODY,
    FONT_SIZE_CAPTION,
    FONT_SIZE_H1,
    FONT_SIZE_H2,
    FONT_SIZE_H3,
    FONT_SIZE_SMALL,
    LIGHT_PALETTE,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
    SPACE_XXS,
    SIDEBAR_WIDTH_EXPANDED,
)


def generate_qss(palette: ColorPalette) -> str:
    """Return the complete application QSS for the given *palette*."""

    return f"""
/* ================================================================
   SHRINERS GAIT ANALYSIS PLATFORM — Minimal Monochrome QSS
   ================================================================ */

/* ── Global ─────────────────────────────────────────────────────── */
QWidget {{
    font-family: "{FONT_FAMILY}";
    font-size: {FONT_SIZE_BODY}px;
    color: {palette.text_primary};
    background-color: {palette.bg_primary};
}}

QMainWindow {{
    background-color: {palette.bg_primary};
}}

/* ── Scroll Area ────────────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 2px 1px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {palette.border};
    border-radius: 3px;
    min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{
    background: {palette.primary};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 1px 2px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {palette.border};
    border-radius: 3px;
    min-width: 40px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {palette.primary};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

/* ── Labels ─────────────────────────────────────────────────────── */
QLabel {{
    background: transparent;
    padding: 0;
}}
QLabel#headerTitle {{
    font-size: {FONT_SIZE_H3}px;
    font-weight: 600;
    color: {palette.text_primary};
    letter-spacing: 0.5px;
}}
QLabel#sectionTitle {{
    font-size: {FONT_SIZE_BODY}px;
    font-weight: 600;
    color: {palette.primary};
    letter-spacing: 0.8px;
    text-transform: uppercase;
    padding-bottom: {SPACE_XS}px;
}}
QLabel#captionLabel {{
    font-size: {FONT_SIZE_CAPTION}px;
    color: {palette.text_muted};
}}
QLabel#cardTitle {{
    font-size: {FONT_SIZE_BODY}px;
    font-weight: 600;
    color: {palette.text_primary};
}}
QLabel#cardValue {{
    font-size: {FONT_SIZE_H2}px;
    font-weight: 700;
    color: {palette.primary};
}}
QLabel#cardSubtext {{
    font-size: {FONT_SIZE_SMALL}px;
    color: {palette.text_muted};
}}

/* ── Buttons ────────────────────────────────────────────────────── */
QPushButton {{
    font-size: {FONT_SIZE_BODY}px;
    font-weight: 500;
    padding: {SPACE_XS}px {SPACE_MD}px;
    border-radius: {RADIUS_MD}px;
    border: 1px solid {palette.border};
    background-color: {palette.bg_surface};
    color: {palette.text_primary};
    min-height: 32px;
}}
QPushButton:hover {{
    background-color: {palette.bg_surface_hover};
    border-color: {palette.primary};
}}
QPushButton:pressed {{
    background-color: {palette.primary_light};
    border-color: {palette.primary_dark};
}}
QPushButton:disabled {{
    color: {palette.text_muted};
    background-color: {palette.bg_primary};
    border-color: {palette.border_light};
    opacity: 0.5;
}}
QPushButton#primaryButton {{
    background-color: {palette.primary};
    color: {palette.text_on_primary};
    border: 1px solid {palette.primary};
    font-weight: 600;
    letter-spacing: 0.3px;
}}
QPushButton#primaryButton:hover {{
    background-color: {palette.primary_hover};
    border-color: {palette.primary_hover};
}}
QPushButton#primaryButton:pressed {{
    background-color: {palette.primary_dark};
    border-color: {palette.primary_dark};
}}
QPushButton#dangerButton {{
    background-color: {palette.error};
    color: #FFFFFF;
    border: none;
    font-weight: 600;
}}
QPushButton#dangerButton:hover {{
    background-color: #B91C1C;
}}
QPushButton#iconButton {{
    background: transparent;
    border: none;
    border-radius: {RADIUS_SM}px;
    padding: {SPACE_XXS}px;
    min-height: 0;
    min-width: 0;
}}
QPushButton#iconButton:hover {{
    background-color: {palette.bg_surface_hover};
}}
QPushButton#sidebarButton {{
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0;
    color: {palette.text_on_sidebar};
    text-align: left;
    padding: 10px {SPACE_MD}px;
    font-size: {FONT_SIZE_BODY}px;
    font-weight: 500;
    min-height: 38px;
    letter-spacing: 0.2px;
}}
QPushButton#sidebarButton:hover {{
    background-color: {palette.bg_sidebar_hover};
    color: {palette.primary};
    border-left: 3px solid {palette.accent};
}}
QPushButton#sidebarButton[active="true"] {{
    background-color: {palette.bg_sidebar_active};
    color: {palette.text_on_sidebar_active};
    border-left: 3px solid {palette.accent};
    font-weight: 600;
}}
QPushButton#tabButton {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    padding: {SPACE_XS}px {SPACE_MD}px;
    font-size: {FONT_SIZE_BODY}px;
    color: {palette.text_muted};
    min-height: 34px;
}}
QPushButton#tabButton:hover {{
    color: {palette.primary};
    border-bottom-color: {palette.accent};
}}
QPushButton#tabButton[active="true"] {{
    color: {palette.primary};
    border-bottom-color: {palette.primary};
    font-weight: 600;
}}

/* ── Inputs ─────────────────────────────────────────────────────── */
QLineEdit {{
    padding: {SPACE_XS}px {SPACE_SM}px;
    border: 1.5px solid {palette.border_input};
    border-radius: {RADIUS_MD}px;
    background-color: {palette.bg_input};
    color: {palette.text_primary};
    font-size: {FONT_SIZE_BODY}px;
    min-height: 32px;
    selection-background-color: {palette.primary_light};
}}
QLineEdit:hover {{
    border-color: {palette.border_input_hover};
}}
QLineEdit:focus {{
    border: 1.5px solid {palette.border_focus};
    background-color: {palette.primary_light};
}}
QLineEdit:disabled {{
    background-color: {palette.bg_surface_hover};
    color: {palette.text_muted};
    border-color: {palette.border};
}}
QLineEdit#searchBar {{
    padding-left: {SPACE_XL}px;
    border-radius: {RADIUS_LG}px;
}}

/* ── Text Edits & Logs ─────────────────────────────────────────── */
QTextEdit, QPlainTextEdit {{
    font-family: "{FONT_FAMILY_MONO}", Consolas, monospace;
    font-size: 12px;
    padding: {SPACE_SM}px;
    border: 1.5px solid {palette.accent};
    border-radius: {RADIUS_MD}px;
    background-color: {palette.primary_light};
    color: {palette.text_primary};
    selection-background-color: {palette.primary};
    selection-color: {palette.text_on_primary};
}}
QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {palette.primary};
    border-width: 1.5px;
}}


/* ── Combo Box ──────────────────────────────────────────────────── */
QComboBox {{
    padding: {SPACE_XS}px {SPACE_SM}px;
    border: 1.5px solid {palette.border_input};
    border-radius: {RADIUS_MD}px;
    background-color: {palette.bg_input};
    color: {palette.text_primary};
    min-height: 32px;
}}
QComboBox:hover {{
    border-color: {palette.border_input_hover};
}}
QComboBox:focus {{
    border: 1.5px solid {palette.border_focus};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: {SPACE_SM}px;
}}
QComboBox QAbstractItemView {{
    background-color: {palette.bg_surface};
    border: 1px solid {palette.border};
    border-radius: {RADIUS_MD}px;
    selection-background-color: {palette.primary_light};
    selection-color: {palette.text_primary};
    padding: {SPACE_XXS}px;
}}

/* ── Check Box / Radio ──────────────────────────────────────────── */
QCheckBox {{
    spacing: {SPACE_XS}px;
    color: {palette.text_primary};
    background: transparent;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid {palette.border};
    border-radius: 3px;
    background: {palette.bg_input};
}}
QCheckBox::indicator:hover {{
    border-color: {palette.text_muted};
}}
QCheckBox::indicator:checked {{
    background: {palette.primary};
    border-color: {palette.primary};
}}
QRadioButton {{
    spacing: {SPACE_XS}px;
    color: {palette.text_primary};
    background: transparent;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid {palette.border};
    border-radius: 8px;
    background: {palette.bg_input};
}}
QRadioButton::indicator:hover {{
    border-color: {palette.text_muted};
}}
QRadioButton::indicator:checked {{
    background: {palette.primary};
    border-color: {palette.primary};
}}

/* ── Tables ─────────────────────────────────────────────────────── */
QTableWidget, QTableView {{
    background-color: {palette.bg_surface};
    alternate-background-color: {palette.bg_surface_hover};
    border: 1px solid {palette.border};
    border-radius: {RADIUS_MD}px;
    gridline-color: {palette.border_light};
    selection-background-color: {palette.primary_light};
    selection-color: {palette.text_primary};
}}
QHeaderView::section {{
    background-color: {palette.bg_surface};
    color: {palette.text_muted};
    font-weight: 600;
    font-size: {FONT_SIZE_CAPTION}px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: {SPACE_XS}px {SPACE_SM}px;
    border: none;
    border-bottom: 1px solid {palette.border};
}}

/* ── Tab Widget ─────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {palette.border};
    border-radius: {RADIUS_MD}px;
    background: {palette.bg_surface};
    top: -1px;
}}
QTabBar::tab {{
    padding: {SPACE_XS}px {SPACE_LG}px;
    background: transparent;
    color: {palette.text_muted};
    border-bottom: 2px solid transparent;
    font-size: {FONT_SIZE_BODY}px;
    min-width: 80px;
}}
QTabBar::tab:hover {{
    color: {palette.text_primary};
}}
QTabBar::tab:selected {{
    color: {palette.primary};
    border-bottom-color: {palette.primary};
    font-weight: 600;
}}

/* ── Progress Bar ───────────────────────────────────────────────── */
QProgressBar {{
    border: none;
    border-radius: 3px;
    background-color: {palette.border_light};
    text-align: center;
    font-size: {FONT_SIZE_SMALL}px;
    color: {palette.text_muted};
    max-height: 4px;
    min-height: 4px;
}}
QProgressBar::chunk {{
    border-radius: 3px;
    background-color: {palette.primary};
}}

/* ── Splitter ───────────────────────────────────────────────────── */
QSplitter::handle {{
    background: {palette.border_light};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}

/* ── Status Bar ─────────────────────────────────────────────────── */
QStatusBar {{
    background-color: {palette.bg_surface};
    border-top: 1px solid {palette.border_light};
    color: {palette.text_muted};
    font-size: {FONT_SIZE_SMALL}px;
    padding: 2px {SPACE_SM}px;
    max-height: 24px;
}}
QStatusBar::item {{
    border: none;
}}

/* ── Tool Tip ───────────────────────────────────────────────────── */
QToolTip {{
    background-color: {palette.bg_tooltip};
    color: {palette.text_on_primary};
    border: none;
    border-radius: {RADIUS_SM}px;
    padding: {SPACE_XXS}px {SPACE_XS}px;
    font-size: {FONT_SIZE_SMALL}px;
}}

/* ── Group Box ──────────────────────────────────────────────────── */
QGroupBox {{
    font-size: {FONT_SIZE_BODY}px;
    font-weight: 600;
    color: {palette.text_primary};
    border: 1px solid {palette.border};
    border-radius: {RADIUS_MD}px;
    padding-top: {SPACE_XL}px;
    margin-top: {SPACE_SM}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 {SPACE_XS}px;
    letter-spacing: 0.3px;
}}

/* ── Dialogs ─────────────────────────────────────────────────────── */
QDialog {{
    background-color: {palette.bg_primary};
    color: {palette.text_primary};
}}

/* ── Card Frames ─────────────────────────────────────────────────── */
QFrame#card, QFrame#sectionCard, QFrame#sessionBox, QFrame#optionsBox, QFrame#procPanel, QFrame#detailsCard {{
    background-color: {palette.bg_card};
    border: 1px solid {palette.border};
    border-radius: {RADIUS_MD}px;
}}
QFrame#card:hover, QFrame#sectionCard:hover {{
    border-color: {palette.border_focus};
}}

/* ── Custom Labels ───────────────────────────────────────────────── */
QLabel#pageHeaderTitle {{
    font-size: {FONT_SIZE_H2}px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: {palette.text_primary};
    background: transparent;
}}
QLabel#pageHeaderSub {{
    font-size: {FONT_SIZE_BODY}px;
    color: {palette.text_muted};
    background: transparent;
}}
QLabel#cardSectionTitle {{
    font-size: {FONT_SIZE_SMALL}px;
    font-weight: 700;
    color: {palette.text_muted};
    letter-spacing: 1px;
    text-transform: uppercase;
    border: none;
    background: transparent;
}}
QLabel#fieldLabel {{
    color: {palette.text_secondary};
    font-size: {FONT_SIZE_CAPTION}px;
    font-weight: 500;
    border: none;
    background: transparent;
}}
QLabel#valueLabel {{
    color: {palette.text_primary};
    font-weight: 600;
    border: none;
    background: transparent;
}}
QLabel#badge, QLabel#metaBadge {{
    background-color: {palette.primary_light};
    color: {palette.primary};
    border: 1px solid {palette.accent};
    border-radius: 12px;
    padding: 4px 12px;
    min-height: 20px;
    font-size: {FONT_SIZE_CAPTION}px;
    font-weight: 600;
}}

/* ── Custom Buttons ──────────────────────────────────────────────── */
QPushButton#secondaryButton {{
    background-color: {palette.primary_light};
    color: {palette.primary};
    border: 1px solid {palette.accent};
    border-radius: {RADIUS_SM}px;
    padding: 6px 14px;
    font-weight: 600;
}}
QPushButton#secondaryButton:hover {{
    background-color: {palette.accent};
    border-color: {palette.primary};
    color: {palette.primary_dark};
}}
QPushButton#outlineButton {{
    background-color: transparent;
    color: {palette.primary};
    border: 1.5px solid {palette.primary};
    border-radius: {RADIUS_SM}px;
    padding: 5px 12px;
    font-weight: 600;
}}
QPushButton#outlineButton:hover {{
    background-color: {palette.primary_light};
    border-color: {palette.primary_hover};
    color: {palette.primary_dark};
}}
QPushButton#ghostButton {{
    background: transparent;
    border: none;
    color: {palette.text_muted};
    padding: 4px 8px;
}}
QPushButton#ghostButton:hover {{
    color: {palette.text_primary};
}}
QPushButton#linkToggle {{
    background: transparent;
    border: none;
    text-align: left;
    color: {palette.text_primary};
    padding: 8px 0;
    font-weight: 600;
}}
QPushButton#linkToggle:hover {{
    color: {palette.text_muted};
}}

/* ── Sidebar frame ──────────────────────────────────────────────── */
QFrame#sidebar {{
    background-color: {palette.bg_sidebar};
    border: none;
    border-right: 1px solid {palette.border};
}}

/* ── Header frame ───────────────────────────────────────────────── */
QFrame#header {{
    background-color: {palette.bg_header};
    border: none;
    border-bottom: 1px solid {palette.border_light};
}}

/* ── Notification banner ────────────────────────────────────────── */
QFrame#notificationSuccess {{
    background-color: {palette.success_bg};
    border: 1px solid {palette.border};
    border-radius: {RADIUS_MD}px;
}}
QFrame#notificationWarning {{
    background-color: {palette.warning_bg};
    border: 1px solid {palette.border};
    border-radius: {RADIUS_MD}px;
}}
QFrame#notificationError {{
    background-color: {palette.error_bg};
    border: 1px solid {palette.border};
    border-radius: {RADIUS_MD}px;
}}
QFrame#notificationInfo {{
    background-color: {palette.info_bg};
    border: 1px solid {palette.border};
    border-radius: {RADIUS_MD}px;
}}
"""


def get_light_qss() -> str:
    """Return the light-theme QSS."""
    return generate_qss(LIGHT_PALETTE)


def get_dark_qss() -> str:
    """Return the dark-theme QSS."""
    return generate_qss(DARK_PALETTE)


def apply_native_titlebar_theme(
    window,
    dark: bool = False,
    bg_color: str | None = None,
    fg_color: str | None = None,
) -> None:
    """
    Apply native OS window title bar styling (Windows DWM) matching the active theme.

    Sets DWM immersive dark mode and Windows 11 caption/text/border colors so the
    title bar seamlessly matches the application palette instead of displaying a harsh black bar.
    """
    if sys.platform != "win32":
        return

    try:
        import ctypes
        if not hasattr(window, "winId"):
            return
        hwnd = int(window.winId())
        if not hwnd:
            return

        dwmapi = ctypes.windll.dwmapi

        # 1. DWMWA_USE_IMMERSIVE_DARK_MODE (20 on Windows 11/10 20H1+, 19 on older Windows 10)
        dark_val = ctypes.c_int(1 if dark else 0)
        dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_val), ctypes.sizeof(dark_val))
        dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(dark_val), ctypes.sizeof(dark_val))

        # 2. Windows 11 Build 22000+ support:
        # DWMWA_BORDER_COLOR = 34, DWMWA_CAPTION_COLOR = 35, DWMWA_TEXT_COLOR = 36
        # COLORREF encoding in Win32 is 0x00BBGGRR
        def _to_colorref(hex_str: str) -> int:
            clean = hex_str.lstrip("#")
            if len(clean) == 6:
                r = int(clean[0:2], 16)
                g = int(clean[2:4], 16)
                b = int(clean[4:6], 16)
                return r | (g << 8) | (b << 16)
            return 0x00FFFFFF

        if dark:
            caption_col = _to_colorref(bg_color or "#0F172A")
            text_col = _to_colorref(fg_color or "#F8FAFC")
            border_col = _to_colorref("#334155")
        else:
            caption_col = _to_colorref(bg_color or "#FFFFFF")
            text_col = _to_colorref(fg_color or "#0F172A")
            border_col = _to_colorref("#E2E8F0")

        c_caption = ctypes.c_int(caption_col)
        c_text = ctypes.c_int(text_col)
        c_border = ctypes.c_int(border_col)

        dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(c_caption), ctypes.sizeof(c_caption))
        dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(c_text), ctypes.sizeof(c_text))
        dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(c_border), ctypes.sizeof(c_border))
    except Exception:
        # Non-critical fallback for environments without DWM support
        pass
