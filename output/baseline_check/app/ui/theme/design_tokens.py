# -*- coding: utf-8 -*-
"""
Centralized Design Tokens for the Shriners Gait Analysis Platform.

All colors, typography, spacing, and border-radius values are defined here.
Import from this module rather than hard-coding style values.

DESIGN PHILOSOPHY: Minimal monochrome B&W with refined spacing and typography.
"""

from dataclasses import dataclass, field
from typing import List


# ── Spacing scale (px) ──────────────────────────────────────────────────────
SPACE_XXS = 4
SPACE_XS = 8
SPACE_SM = 12
SPACE_MD = 16
SPACE_LG = 24
SPACE_XL = 32
SPACE_XXL = 48

# ── Border-radius scale ─────────────────────────────────────────────────────
RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_LG = 10
RADIUS_XL = 14
RADIUS_ROUND = 9999  # pill / fully round

# ── Typography ───────────────────────────────────────────────────────────────
import sys
if sys.platform == "win32":
    FONT_FAMILY = "Segoe UI"
elif sys.platform == "darwin":
    FONT_FAMILY = "-apple-system"
else:
    FONT_FAMILY = "Inter"

FONT_FAMILY_MONO = "Consolas"

FONT_SIZE_H1 = 24
FONT_SIZE_H2 = 20
FONT_SIZE_H3 = 16
FONT_SIZE_BODY = 13
FONT_SIZE_CAPTION = 11
FONT_SIZE_SMALL = 10

FONT_WEIGHT_NORMAL = 400
FONT_WEIGHT_MEDIUM = 500
FONT_WEIGHT_SEMIBOLD = 600
FONT_WEIGHT_BOLD = 700

# ── Sidebar ──────────────────────────────────────────────────────────────────
SIDEBAR_WIDTH_EXPANDED = 200
SIDEBAR_WIDTH_COLLAPSED = 56
SIDEBAR_ICON_SIZE = 18

# ── Chart defaults ───────────────────────────────────────────────────────────
CHART_LINE_WIDTH = 1.4
CHART_NORM_ALPHA = 0.55
CHART_TITLE_SIZE = 10
CHART_LABEL_SIZE = 9
CHART_TICK_SIZE = 8
CHART_GRID_ALPHA = 0.15


# ── User Defined Color Palette ──────────────────────────────────────────────
COLOR_PRIMARY = "#0F766E"      # Deep Teal / Pine
COLOR_ACCENT = "#14B8A6"       # Teal
COLOR_MOTION = "#06B6D4"       # Cyan
COLOR_NORMAL = "#22C55E"       # Green
COLOR_WARNING = "#F59E0B"      # Amber
COLOR_CRITICAL = "#EF4444"     # Red
COLOR_BACKGROUND = "#F8FAFC"   # Slate 50
COLOR_SURFACE = "#FFFFFF"      # White
COLOR_TEXT = "#0F172A"         # Slate 900
COLOR_MUTED = "#64748B"        # Slate 500
COLOR_BORDER = "#E2E8F0"       # Slate 200


@dataclass(frozen=True)
class ColorPalette:
    """Immutable colour palette for the Shriners Clinical Workstation."""

    # Explicit User Palette Tokens
    primary: str = COLOR_PRIMARY
    accent: str = COLOR_ACCENT
    motion: str = COLOR_MOTION
    normal: str = COLOR_NORMAL
    warning: str = COLOR_WARNING
    critical: str = COLOR_CRITICAL
    background: str = COLOR_BACKGROUND
    surface: str = COLOR_SURFACE
    text: str = COLOR_TEXT
    muted: str = COLOR_MUTED
    border: str = COLOR_BORDER

    # Backgrounds
    bg_primary: str = "#F8FAFC"
    bg_surface: str = "#FFFFFF"
    bg_surface_hover: str = "#F1F5F9"
    bg_sidebar: str = "#F8FAFC"
    bg_sidebar_hover: str = "#F1F5F9"
    bg_sidebar_active: str = "#0F766E"
    bg_header: str = "#FFFFFF"
    bg_card: str = "#FFFFFF"
    bg_input: str = "#FFFFFF"
    bg_tooltip: str = "#0F172A"

    # Text
    text_primary: str = "#0F172A"
    text_secondary: str = "#334155"
    text_muted: str = "#64748B"
    text_on_primary: str = "#FFFFFF"
    text_on_sidebar: str = "#334155"
    text_on_sidebar_active: str = "#FFFFFF"
    text_link: str = "#0F766E"

    # Brand / Primary
    primary_hover: str = "#115E59"
    primary_light: str = "#F0FDFA"
    primary_dark: str = "#134E4A"

    # Secondary / Accent / Motion
    secondary: str = "#14B8A6"
    secondary_hover: str = "#0D9488"
    accent_hover: str = "#0D9488"
    motion_hover: str = "#0891B2"
    motion_light: str = "#ECFEFF"

    # Borders
    border_light: str = "#F1F5F9"
    border_focus: str = "#14B8A6"
    border_input: str = "#A7F3D0"        # Very light pastel green matching UI theme
    border_input_hover: str = "#5EEAD4"  # Soft mint teal on hover

    # Status
    success: str = "#22C55E"
    success_bg: str = "#F0FDF4"
    warning_bg: str = "#FEF3C7"
    error: str = "#EF4444"
    error_bg: str = "#FEF2F2"
    info: str = "#06B6D4"
    info_bg: str = "#ECFEFF"

    # Chart colors — vibrant differentiated trial colors
    chart_trial_colors: tuple = (
        "#2563EB",  # L1: Royal Blue
        "#16A34A",  # L2: Emerald Green
        "#EA580C",  # L3: Vibrant Orange
        "#9333EA",  # L4: Purple
        "#0891B2",  # L5: Cyan / Teal
        "#4F46E5",  # L6: Indigo
        "#65A30D",  # L7: Lime
        "#0D9488",  # L8: Deep Teal
        "#0284C7",  # L9: Deep Sky Blue
        "#C026D3",  # L10: Magenta
    )
    chart_right_colors: tuple = (
        "#DC2626",  # R1: Crimson Red
        "#D97706",  # R2: Amber / Gold
        "#DB2777",  # R3: Deep Rose
        "#7C3AED",  # R4: Violet
        "#92400E",  # R5: Warm Bronze
        "#E11D48",  # R6: Bright Crimson
        "#C2410C",  # R7: Burnt Orange
        "#BE123C",  # R8: Ruby Red
        "#A16207",  # R9: Golden Brown
        "#9F1239",  # R10: Dark Raspberry
    )
    chart_norm_color: str = "#0F766E"
    chart_norm_fill: str = "#CCFBF1"
    chart_norm_line: str = "#0F766E"
    chart_norm_alpha: float = 0.55
    chart_background: str = "#FFFFFF"
    chart_grid: str = "#E2E8F0"
    chart_axis: str = "#64748B"

    # Comparison colors
    comparison_initial: str = "#0F766E"
    comparison_followup: str = "#EF4444"


# Pre-built palettes
LIGHT_PALETTE = ColorPalette()

DARK_PALETTE = ColorPalette(
    primary="#14B8A6",
    accent="#2DD4BF",
    motion="#06B6D4",
    normal="#22C55E",
    warning="#F59E0B",
    critical="#EF4444",
    background="#0B1320",
    surface="#1E293B",
    text="#F8FAFC",
    muted="#94A3B8",
    border="#334155",
    bg_primary="#0F172A",
    bg_surface="#1E293B",
    bg_surface_hover="#334155",
    bg_sidebar="#0B1120",
    bg_sidebar_hover="#1E293B",
    bg_sidebar_active="#0F766E",
    bg_header="#0F172A",
    bg_card="#1E293B",
    bg_input="#0F172A",
    bg_tooltip="#0F766E",
    text_primary="#F8FAFC",
    text_secondary="#CBD5E1",
    text_muted="#94A3B8",
    text_on_primary="#FFFFFF",
    text_on_sidebar="#CBD5E1",
    text_on_sidebar_active="#FFFFFF",
    text_link="#14B8A6",
    primary_hover="#2DD4BF",
    primary_light="#134E4A",
    primary_dark="#0F766E",
    secondary="#06B6D4",
    secondary_hover="#22D3EE",
    accent_hover="#2DD4BF",
    motion_hover="#22D3EE",
    motion_light="#083344",
    border_light="#1E293B",
    border_focus="#14B8A6",
    border_input="#134E4A",
    border_input_hover="#2DD4BF",
    success="#22C55E",
    success_bg="#052E16",
    warning_bg="#451A03",
    error="#EF4444",
    error_bg="#450A0A",
    info="#06B6D4",
    info_bg="#083344",
    chart_trial_colors=(
        "#3B82F6",  # L1: Light Royal Blue
        "#22C55E",  # L2: Light Emerald Green
        "#FB923C",  # L3: Light Vibrant Orange
        "#A855F7",  # L4: Light Purple
        "#06B6D4",  # L5: Light Cyan
        "#818CF8",  # L6: Light Indigo
        "#A3E635",  # L7: Light Lime
        "#2DD4BF",  # L8: Light Teal
        "#38BDF8",  # L9: Sky Blue
        "#E879F9",  # L10: Light Magenta
    ),
    chart_right_colors=(
        "#EF4444",  # R1: Light Crimson Red
        "#FBBF24",  # R2: Light Amber
        "#F472B6",  # R3: Light Rose
        "#A78BFA",  # R4: Light Violet
        "#F59E0B",  # R5: Light Warm Bronze
        "#FB7185",  # R6: Light Rose Red
        "#FB923C",  # R7: Light Red Orange
        "#FDA4AF",  # R8: Light Ruby
        "#FDE047",  # R9: Light Gold
        "#F43F5E",  # R10: Light Raspberry
    ),
    chart_norm_color="#14B8A6",
    chart_norm_fill="#134E4A",
    chart_norm_line="#14B8A6",
    chart_norm_alpha=0.55,
    chart_background="#0F172A",
    chart_grid="#1E293B",
    chart_axis="#94A3B8",
    comparison_initial="#14B8A6",
    comparison_followup="#EF4444",
)

