# -*- coding: utf-8 -*-
"""
Clinical Plot Widget — reusable Matplotlib chart embedded in PySide6.

Provides a consistent, professional look for all gait-cycle plots
(kinematics, kinetics, EMG, muscle analysis) with normative bands,
toe-off markers, and clinical styling.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import matplotlib
matplotlib.use("QtAgg")

from PySide6.QtCore import Qt, Signal, QSize
from shiboken6 import isValid
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme.design_tokens import (
    CHART_GRID_ALPHA,
    CHART_LABEL_SIZE,
    CHART_LINE_WIDTH,
    CHART_NORM_ALPHA,
    CHART_TICK_SIZE,
    CHART_TITLE_SIZE,
    FONT_FAMILY,
    LIGHT_PALETTE,
    DARK_PALETTE,
    SPACE_SM,
    SPACE_XS,
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
from app.ui.theme.theme_manager import apply_native_titlebar_theme
from app.ui.widgets.components import create_tinted_icon

logger = logging.getLogger(__name__)


def calculate_dynamic_y_limits(
    y_data: List[np.ndarray],
    y_min: float,
    y_max: float,
    y_ticks: list | None = None,
    norm_y_low: np.ndarray | None = None,
    norm_y_high: np.ndarray | None = None,
) -> Tuple[float, float, list | None]:
    """
    Calculate optimal y-axis limits and tick marks so that peaks and troughs
    are fully visible within the plot area while preserving standard clinical
    scaling when data is within nominal boundaries.
    """
    valid_pts = []
    if y_data:
        for arr in y_data:
            if arr is not None and len(arr) > 0:
                data = np.asarray(arr, dtype=float)
                finite_vals = data[np.isfinite(data)]
                if len(finite_vals) > 0:
                    valid_pts.append(float(np.min(finite_vals)))
                    valid_pts.append(float(np.max(finite_vals)))

    if norm_y_low is not None:
        data = np.asarray(norm_y_low, dtype=float)
        finite_vals = data[np.isfinite(data)]
        if len(finite_vals) > 0:
            valid_pts.append(float(np.min(finite_vals)))

    if norm_y_high is not None:
        data = np.asarray(norm_y_high, dtype=float)
        finite_vals = data[np.isfinite(data)]
        if len(finite_vals) > 0:
            valid_pts.append(float(np.max(finite_vals)))

    if not valid_pts:
        return float(y_min), float(y_max), y_ticks

    d_min = min(valid_pts)
    d_max = max(valid_pts)

    orig_ticks = [float(t) for t in y_ticks] if (y_ticks and len(y_ticks) >= 2) else []
    if orig_ticks:
        orig_ticks.sort()
        diffs = [orig_ticks[j + 1] - orig_ticks[j] for j in range(len(orig_ticks) - 1)]
        step = float(np.median(diffs))
        is_int = all(float(t).is_integer() for t in orig_ticks)
    else:
        span = float(y_max - y_min) if y_max > y_min else 10.0
        step = span / 4.0
        is_int = float(y_min).is_integer() and float(y_max).is_integer()

    if step <= 0:
        step = 10.0

    eff_min = orig_ticks[0] if orig_ticks else float(y_min)
    eff_max = orig_ticks[-1] if orig_ticks else float(y_max)

    # If all curves fit inside nominal clinical bounds, keep standard view
    if d_min >= eff_min and d_max <= eff_max:
        return float(y_min), float(y_max), y_ticks

    margin = 0.02 * step

    # Expand top limit until peak is fully visible with comfortable clearance
    while eff_max < d_max + margin:
        eff_max = round(eff_max + step, 4)
        if (eff_max - eff_min) / step > 100:
            break

    # Expand bottom limit until trough is fully visible with comfortable clearance
    while eff_min > d_min - margin:
        eff_min = round(eff_min - step, 4)
        if (eff_max - eff_min) / step > 100:
            break

    total_steps = int(round((eff_max - eff_min) / step))
    # If there are more than 8 ticks, thin them out nicely using canonical clinical strides
    if total_steps > 8:
        ticks = compute_clinical_ticks(eff_min, eff_max, step, max_ticks=8)
        eff_min = min(eff_min, float(ticks[0]))
        eff_max = max(eff_max, float(ticks[-1]))
    else:
        ticks = [round(eff_min + j * step, 4) for j in range(total_steps + 1)]

    if is_int:
        ticks = [int(round(t)) for t in ticks]
        eff_min = min(eff_min, float(ticks[0]))
        eff_max = max(eff_max, float(ticks[-1]))
    else:
        decimals = max(1, len(str(step).split(".")[1]) if "." in str(step) else 1)
        ticks = [round(t, decimals) for t in ticks]
        eff_min = min(eff_min, float(ticks[0]))
        eff_max = max(eff_max, float(ticks[-1]))

    return eff_min, eff_max, ticks


def compute_nice_ticks(ymin: float, ymax: float, max_ticks: int = 7) -> list:
    """Generate clean, evenly-spaced tick values including 0 if within range."""
    span = ymax - ymin
    if span <= 0:
        return [ymin, ymax]
    raw_step = span / max(2, max_ticks - 1)
    exponent = np.floor(np.log10(raw_step))
    fraction = raw_step / (10 ** exponent)
    if fraction < 1.5:
        nice_fraction = 1.0
    elif fraction < 3.0:
        nice_fraction = 2.0
    elif fraction < 7.0:
        nice_fraction = 5.0
    else:
        nice_fraction = 10.0
    step = nice_fraction * (10 ** exponent)
    for std_step in [5.0, 10.0, 15.0, 20.0, 25.0, 30.0]:
        if 0.7 * raw_step <= std_step <= 1.4 * raw_step:
            step = std_step
            break
    if ymin <= 0 <= ymax:
        neg_ticks = list(np.arange(0, ymin - 0.5 * step, -step))[::-1]
        pos_ticks = list(np.arange(step, ymax + 0.5 * step, step))
        raw_ticks = [t for t in neg_ticks + pos_ticks if ymin <= t <= ymax]
    else:
        first_tick = np.ceil(ymin / step) * step
        raw_ticks = [t for t in np.arange(first_tick, ymax + 0.5 * step, step) if ymin <= t <= ymax]
    if len(raw_ticks) < 2:
        raw_ticks = [ymin, ymax]
    if all(abs(t - round(t)) < 1e-5 for t in raw_ticks):
        return [int(round(t)) for t in raw_ticks]
    return [round(float(t), 2) for t in raw_ticks]


def compute_clinical_ticks(
    ymin: float,
    ymax: float,
    step: Optional[float] = None,
    max_ticks: int = 8,
) -> list:
    """
    Generate clean, evenly-spaced clinical tick values aligned to canonical steps and 0.
    Dynamically thins ticks to prevent overcrowding and overlapping labels when the
    axis range is expanded.
    """
    if ymin >= ymax:
        return [ymin, ymax]

    span = float(ymax - ymin)
    if span <= 0:
        return [ymin, ymax]

    # Establish canonical base step
    if step is None or step <= 0:
        if span <= 20:
            base_step = 5.0
        elif span <= 60:
            base_step = 10.0
        elif span <= 100:
            base_step = 15.0
        else:
            base_step = 20.0
    else:
        base_step = float(step)

    # Choose clean multiplier strides based on clinical unit conventions
    if abs(base_step - 15.0) < 1e-4:
        strides = [1, 2, 3, 4, 6, 8, 12, 16, 20, 24, 30, 40, 50, 60, 80, 100]
    elif abs(base_step - 5.0) < 1e-4:
        strides = [1, 2, 3, 4, 5, 10, 20, 30, 40, 50, 100]
    elif abs(base_step - 10.0) < 1e-4 or abs(base_step - 20.0) < 1e-4:
        strides = [1, 2, 3, 4, 5, 10, 20, 30, 40, 50, 100]
    else:
        strides = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]

    def _calc_ticks_for_step(s_step: float) -> list:
        if ymin <= 0 <= ymax:
            neg = list(np.arange(0, ymin - 0.5 * s_step, -s_step))[::-1]
            pos = list(np.arange(s_step, ymax + 0.5 * s_step, s_step))
            raw = [round(t, 6) for t in neg + pos if ymin - 1e-4 <= t <= ymax + 1e-4]
        else:
            first = np.ceil((ymin - 1e-4) / s_step) * s_step
            raw = [round(t, 6) for t in np.arange(first, ymax + 0.5 * s_step, s_step) if ymin - 1e-4 <= t <= ymax + 1e-4]
        return raw

    chosen_ticks = None
    chosen_step = base_step
    for s in strides:
        cand_step = base_step * s
        cand_ticks = _calc_ticks_for_step(cand_step)
        if len(cand_ticks) <= max_ticks:
            chosen_ticks = cand_ticks
            chosen_step = cand_step
            break

    if chosen_ticks is None:
        needed_stride = int(np.ceil((span / max(2, max_ticks - 1)) / base_step))
        chosen_step = base_step * max(1, needed_stride)
        chosen_ticks = _calc_ticks_for_step(chosen_step)

    if len(chosen_ticks) < 2:
        chosen_ticks = [ymin, ymax]

    if all(abs(t - round(t)) < 1e-4 for t in chosen_ticks):
        return [int(round(t)) for t in chosen_ticks]
    else:
        decimals = max(1, len(str(chosen_step).split(".")[1]) if "." in str(chosen_step) else 1)
        return [round(float(t), decimals) for t in chosen_ticks]



def get_data_y_extents(
    y_data: List[np.ndarray] | None = None,
    norm_y_low: np.ndarray | None = None,
    norm_y_high: np.ndarray | None = None,
) -> Tuple[float, float] | None:
    """Calculate the absolute minimum and maximum values across all curves and normative bounds."""
    pts = []
    if y_data:
        for arr in y_data:
            if arr is not None and len(arr) > 0:
                data = np.asarray(arr, dtype=float)
                finite_vals = data[np.isfinite(data)]
                if len(finite_vals) > 0:
                    pts.append(float(np.min(finite_vals)))
                    pts.append(float(np.max(finite_vals)))
    if norm_y_low is not None:
        data = np.asarray(norm_y_low, dtype=float)
        finite_vals = data[np.isfinite(data)]
        if len(finite_vals) > 0:
            pts.append(float(np.min(finite_vals)))
    if norm_y_high is not None:
        data = np.asarray(norm_y_high, dtype=float)
        finite_vals = data[np.isfinite(data)]
        if len(finite_vals) > 0:
            pts.append(float(np.max(finite_vals)))
    if not pts:
        return None
    return min(pts), max(pts)



def _full_graph_limits(y_data, norm_y_low, norm_y_high, ymin, ymax, step):
    extents = get_data_y_extents(y_data, norm_y_low, norm_y_high)
    if extents:
        d_min, d_max = extents
        margin = max(0.02 * (ymax - ymin), 0.5)
        while ymax <= d_max + margin:
            ymax = round(ymax + step, 4)
            if (ymax - ymin) / step > 50:
                break
        while ymin >= d_min - margin:
            ymin = round(ymin - step, 4)
            if (ymax - ymin) / step > 50:
                break
    return ymin, ymax


def format_clinical_coords(x: float, y: float) -> str:
    """
    Format cursor hover coordinates cleanly for clinical gait charts as (x, y).
    Ensures both x (% gait cycle) and y (curve value) are cleanly visible without blank values.
    """
    try:
        if x is None or y is None:
            return ""
        if isinstance(x, (int, float, np.floating)) and (np.isnan(x) or not np.isfinite(x)):
            return ""
        if isinstance(y, (int, float, np.floating)) and (np.isnan(y) or not np.isfinite(y)):
            return ""
        return f"(x, y) = ({float(x):.1f}, {float(y):.1f})"
    except Exception:
        return f"(x, y) = ({x}, {y})"


class ClinicalPlotCanvas(FigureCanvasQTAgg):
    """A single Matplotlib subplot canvas for clinical gait-cycle plots."""

    def _draw_idle(self):
        # Qt can destroy a dialog's child canvas before its queued draw runs.
        if not isValid(self):
            self._draw_pending = False
            return
        super()._draw_idle()

    def __init__(
        self,
        width: float = 3.2,
        height: float = 2.2,
        dpi: int = 100,
        parent: QWidget | None = None,
    ):
        self._is_dark = False
        self._scale_states = {}
        self._graph_id = None
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor("white")
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(165)
        self.setMinimumWidth(230)
        self._configure_defaults()

    def _configure_defaults(self):
        """Set professional clinical chart defaults."""
        bg = "#0F172A" if self._is_dark else COLOR_SURFACE
        fg = "#F8FAFC" if self._is_dark else COLOR_TEXT
        grid = "#1E293B" if self._is_dark else COLOR_BORDER
        spine_col = "#334155" if self._is_dark else COLOR_BORDER

        self.fig.patch.set_facecolor(bg)
        self.axes.set_facecolor(bg)
        ax = self.axes
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.tick_params(axis="both", which="major", labelsize=CHART_TICK_SIZE, direction="in", colors=fg)
        ax.format_coord = format_clinical_coords
        ax.grid(True, alpha=CHART_GRID_ALPHA, linewidth=0.5, color=grid)
        ax.spines["top"].set_visible(True)
        ax.spines["right"].set_visible(True)
        for spine in ax.spines.values():
            spine.set_linewidth(0.5)
            spine.set_color(spine_col)

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        """Update canvas background, spines, and ticks for theme."""
        self._is_dark = dark
        self._configure_defaults()
        self._apply_scale_state()
        self.draw_idle()

    def _apply_scale_state(self):
        state = self._scale_states.get(self._graph_id, {})
        if state.get("y_mode") == "manual":
            if state.get("y_ticks") is not None:
                self.axes.set_yticks(state["y_ticks"])
            self.axes.set_ylim(state["ylim"])
        if state.get("x_mode") == "manual":
            self.axes.set_xlim(state["xlim"])

    def set_scale_limits(self, *, xlim=None, ylim=None, y_ticks=None, mode="manual"):
        """Store limits for this graph and update only this canvas. Closing controls is inert."""
        state = self._scale_states.setdefault(self._graph_id, {})
        if xlim is not None:
            state.update(x_mode=mode, xlim=tuple(xlim))
            self.axes.set_xlim(xlim)
        if ylim is not None:
            if y_ticks is None or len(y_ticks) > 8:
                step = ClinicalPlotDetailDialog._determine_step_size(*ylim)
                y_ticks = compute_clinical_ticks(ylim[0], ylim[1], step)
            state.update(y_mode=mode, ylim=tuple(ylim), y_ticks=y_ticks)
            if y_ticks is not None:
                self.axes.set_yticks(y_ticks)
            self.axes.set_ylim(ylim)
            low, high = ylim
            inset = 0.05 * (high - low)
            if hasattr(self, "_top_direction"):
                self._top_direction.set_y(high - inset)
            if hasattr(self, "_bottom_direction"):
                self._bottom_direction.set_y(low + inset)
            for group in getattr(self, "_trial_artists", {}).values():
                for name in ("opposite_off", "opposite_contact"):
                    marker = group.get(name)
                    if marker is not None and marker.get_segments():
                        x = marker.get_segments()[0][0][0]
                        marker.set_segments([[(x, high - inset), (x, high)]])
            layout_key = (getattr(self, "_scene_key", None), low, high,
                          tuple(y_ticks if y_ticks is not None else self.axes.get_yticks()),
                          getattr(self, "_legend_key", ()), tuple(self.fig.get_size_inches()))
            if layout_key != getattr(self, "_layout_key", None):
                self.fig.tight_layout(pad=0.7)
                self._layout_key = layout_key
        self.draw_idle()

    def clear_plot(self):
        """Clear all data from the axes while keeping defaults."""
        self.axes.clear()
        self._scene_key = None
        self._layout_key = None
        self._trial_artists = {}
        self._last_plot_kwargs = None
        self._configure_defaults()

    def plot_gait_data(
        self,
        x_data: List[np.ndarray],
        y_data: List[np.ndarray],
        colors: List[str],
        toe_offs: List[float] | None = None,
        opposite_toe_offs: List[float] | None = None,
        opposite_foot_contacts: List[float] | None = None,
        norm_x: np.ndarray | None = None,
        norm_y_low: np.ndarray | None = None,
        norm_y_high: np.ndarray | None = None,
        norm_y_mean: np.ndarray | None = None,
        norm_toe_off: float | None = None,
        y_min: float = -30,
        y_max: float = 30,
        title: str = "",
        y_ticks: list | None = None,
        y_label_top: str = "",
        y_label_bottom: str = "",
        show_x_labels: bool = True,
        line_width: float = CHART_LINE_WIDTH,
        line_widths: List[float] | None = None,
        line_styles: List[str] | None = None,
        legend_entries: List[Tuple[str, str, str]] | None = None,
        force_y_limits: bool = False,
        curve_ids: List[str] | None = None,
        graph_id=None,
        **kwargs,
    ) -> None:
        """
        Plot one or more gait-cycle traces with normative ideal range band and mean curve.
        """
        ax = self.axes
        self._graph_id = graph_id if graph_id is not None else (title, y_label_top, y_label_bottom)
        scale = self._scale_states.get(self._graph_id, {})
        # A scene changes only with category, reference data, labels or theme.
        def array_key(values):
            return None if values is None else np.asarray(values).tobytes()

        scene_key = (title, y_label_top, y_label_bottom, show_x_labels, self._is_dark,
                     array_key(norm_x), array_key(norm_y_low), array_key(norm_y_high),
                     array_key(norm_y_mean), norm_toe_off)
        new_scene = scene_key != getattr(self, "_scene_key", None)
        if new_scene:
            self.clear_plot()
            self._scene_key = scene_key

        palette = DARK_PALETTE if self._is_dark else LIGHT_PALETTE
        fg = "#F8FAFC" if self._is_dark else COLOR_TEXT

        if new_scene:
            # Normative ideal range band & dotted mean curve
            if norm_x is not None and norm_y_low is not None and norm_y_high is not None:
                norm_fill = getattr(palette, "chart_norm_fill", "#134E4A" if self._is_dark else "#CCFBF1")
                norm_alpha = getattr(palette, "chart_norm_alpha", CHART_NORM_ALPHA)
                ax.fill_between(
                    norm_x, norm_y_high, norm_y_low,
                    color=norm_fill,
                    alpha=norm_alpha,
                    zorder=1,
                )
                # Dotted ideal center / mean line
                mean_curve = norm_y_mean if norm_y_mean is not None else (norm_y_high + norm_y_low) / 2.0
                norm_line_color = getattr(palette, "chart_norm_line", "#14B8A6" if self._is_dark else COLOR_PRIMARY)
                ax.plot(
                    norm_x, mean_curve,
                    color=norm_line_color,
                    lw=0.8,
                    linestyle=":",
                    zorder=2,
                )
                if norm_toe_off is not None and norm_toe_off > 0:
                    ax.axvline(norm_toe_off, lw=0.8, color=norm_line_color, linestyle=":", zorder=2)

            # Zero reference line
            zero_line_color = "#334155" if self._is_dark else COLOR_MUTED
            ax.axhline(0, lw=0.6, color=zero_line_color, zorder=2)

        # Dynamic or explicit y-axis scaling: ensure peaks and troughs are fully visible
        if force_y_limits:
            eff_y_min = float(y_min)
            eff_y_max = float(y_max)
            eff_y_ticks = y_ticks if (y_ticks and 2 <= len(y_ticks) <= 8) else compute_clinical_ticks(
                eff_y_min, eff_y_max, ClinicalPlotDetailDialog._determine_step_size(y_min, y_max, y_ticks)
            )
        else:
            limits_key = (y_min, y_max, tuple(y_ticks or ()),
                          tuple(array_key(y) for y in y_data),
                          array_key(norm_y_low), array_key(norm_y_high))
            if limits_key != getattr(self, "_limits_key", None):
                self._limits_value = calculate_dynamic_y_limits(
                    y_data=y_data, y_min=y_min, y_max=y_max, y_ticks=y_ticks,
                    norm_y_low=norm_y_low, norm_y_high=norm_y_high,
                )
                self._limits_key = limits_key
            eff_y_min, eff_y_max, eff_y_ticks = self._limits_value

        if scale.get("y_mode") == "auto" and scale.get("fit_full"):
            eff_y_min, eff_y_max = _full_graph_limits(
                y_data, norm_y_low, norm_y_high, y_min, y_max,
                ClinicalPlotDetailDialog._determine_step_size(y_min, y_max, y_ticks),
            )
            eff_y_ticks = compute_clinical_ticks(eff_y_min, eff_y_max,
                ClinicalPlotDetailDialog._determine_step_size(y_min, y_max, y_ticks))
        elif scale.get("y_mode") == "manual":
            eff_y_min, eff_y_max = scale["ylim"]
            eff_y_ticks = scale.get("y_ticks")
            if eff_y_ticks is None or len(eff_y_ticks) > 8:
                step = ClinicalPlotDetailDialog._determine_step_size(eff_y_min, eff_y_max, eff_y_ticks)
                eff_y_ticks = compute_clinical_ticks(eff_y_min, eff_y_max, step)
                scale["y_ticks"] = eff_y_ticks

        # Keep one bounded group of artists per trial/mean while controls change.
        groups = self._trial_artists
        for group in groups.values():
            for artist in group.values():
                artist.set_visible(False)
        for i, (x, y) in enumerate(zip(x_data, y_data)):
            key = curve_ids[i] if curve_ids is not None else str(i)
            group = groups.setdefault(key, {})
            color = colors[i] if i < len(colors) else palette.chart_trial_colors[i % len(palette.chart_trial_colors)]
            lw = line_widths[i] if (line_widths and i < len(line_widths)) else line_width
            ls = line_styles[i] if (line_styles and i < len(line_styles)) else "-"
            zo = 4 if lw > line_width else 3
            if "curve" not in group:
                group["curve"], = ax.plot([], [])
            line = group["curve"]
            line.set_data(x, y)
            line.set(color=color, linewidth=lw, linestyle=ls, zorder=zo, visible=True)
            if toe_offs and i < len(toe_offs) and toe_offs[i] is not None and toe_offs[i] > 0:
                prominent = (line_widths and i < len(line_widths) and line_widths[i] > 2.0) or (line_styles and i < len(line_styles) and line_styles[i] == "--")
                crowded = len(y_data) > 3 and not prominent
                if "toe" not in group:
                    group["toe"] = ax.axvline(toe_offs[i])
                toe = group["toe"]
                toe.set_xdata([toe_offs[i], toe_offs[i]])
                toe.set(color=color, linewidth=0.6 if crowded else (1.2 if prominent else 0.8),
                        linestyle=":" if crowded else "--", alpha=0.35 if crowded else 0.85,
                        zorder=2 if crowded else 3, visible=True)
            for name, values in (("opposite_off", opposite_toe_offs), ("opposite_contact", opposite_foot_contacts)):
                if values and i < len(values) and values[i] is not None and values[i] > 0:
                    low = eff_y_max - 0.05 * (eff_y_max - eff_y_min)
                    if name not in group:
                        group[name] = ax.vlines(values[i], low, eff_y_max, linewidth=0.8, color=color, zorder=3)
                    marker = group[name]
                    marker.set_segments([[(values[i], low), (values[i], eff_y_max)]])
                    marker.set_color(color)
                    marker.set_visible(True)

        # Limits and labels
        ax.set_xlim(scale["xlim"] if scale.get("x_mode") == "manual" else (0, 100))
        ax.set_ylim(eff_y_min, eff_y_max)

        if title:
            ax.set_title(title, fontsize=CHART_TITLE_SIZE, fontweight="bold", fontfamily=FONT_FAMILY, color=fg)

        if eff_y_ticks:
            ax.set_yticks(eff_y_ticks)

        ax.set_xticks([0, 25, 50, 75, 100])
        if scale.get("x_mode") == "manual":
            ax.set_xlim(scale["xlim"])
        if scale.get("y_mode") == "manual":
            ax.set_ylim(scale["ylim"])
        ax.tick_params(axis="x", labelbottom=show_x_labels)
        ax.format_coord = format_clinical_coords

        # Y-axis direction labels
        if new_scene and y_label_top:
            self._top_direction = ax.text(
                -2, eff_y_max - 0.05 * (eff_y_max - eff_y_min), y_label_top,
                fontsize=CHART_LABEL_SIZE, ha="right", va="top",
                fontfamily=FONT_FAMILY,
            )
        if new_scene and y_label_bottom:
            self._bottom_direction = ax.text(
                -2, eff_y_min + 0.05 * (eff_y_max - eff_y_min), y_label_bottom,
                fontsize=CHART_LABEL_SIZE, ha="right", va="bottom",
                fontfamily=FONT_FAMILY,
            )

        if y_label_top:
            self._top_direction.set_y(eff_y_max - 0.05 * (eff_y_max - eff_y_min))
        if y_label_bottom:
            self._bottom_direction.set_y(eff_y_min + 0.05 * (eff_y_max - eff_y_min))

        # Legend for Mean curves or key features if requested
        legend_key = tuple(legend_entries or ())
        if legend_key != getattr(self, "_legend_key", None) or new_scene:
            if ax.get_legend() is not None:
                ax.get_legend().remove()
        if legend_entries and (legend_key != getattr(self, "_legend_key", None) or new_scene):
            leg_handles = [
                Line2D([0], [0], color=c, linestyle=ls, lw=2.2, label=lbl)
                for lbl, c, ls in legend_entries
            ]
            ax.legend(
                handles=leg_handles,
                loc="best",
                fontsize=6.5,
                framealpha=0.88,
                facecolor="#1E293B" if self._is_dark else "#FFFFFF",
                edgecolor="#334155" if self._is_dark else "#CBD5E1",
                labelcolor="#F8FAFC" if self._is_dark else "#0F172A",
                borderpad=0.25,
                handlelength=1.3,
                handletextpad=0.35,
            )

        self._legend_key = legend_key
        self._last_plot_kwargs = {
            "graph_id": self._graph_id,
            "curve_ids": curve_ids,
            "x_data": x_data,
            "y_data": y_data,
            "colors": colors,
            "toe_offs": toe_offs,
            "opposite_toe_offs": opposite_toe_offs,
            "opposite_foot_contacts": opposite_foot_contacts,
            "norm_x": norm_x,
            "norm_y_low": norm_y_low,
            "norm_y_high": norm_y_high,
            "norm_y_mean": norm_y_mean,
            "norm_toe_off": norm_toe_off,
            "y_min": eff_y_min,
            "y_max": eff_y_max,
            "nominal_y_min": y_min,
            "nominal_y_max": y_max,
            "nominal_y_ticks": y_ticks,
            "title": title,
            "y_ticks": eff_y_ticks,
            "y_label_top": y_label_top,
            "y_label_bottom": y_label_bottom,
            "show_x_labels": show_x_labels,
            "line_width": line_width,
            "line_widths": line_widths,
            "line_styles": line_styles,
            "legend_entries": legend_entries,
            "force_y_limits": force_y_limits,
        }

        layout_key = (scene_key, eff_y_min, eff_y_max, tuple(eff_y_ticks or ()),
                      legend_key, tuple(self.fig.get_size_inches()))
        if layout_key != getattr(self, "_layout_key", None):
            self.fig.tight_layout(pad=0.7)
            self._layout_key = layout_key
        self.draw_idle()

    def get_data_y_extents(self) -> Tuple[float, float] | None:
        """Return the (min, max) y values across all current plot curves and normative bands."""
        kw = getattr(self, "_last_plot_kwargs", None)
        if not kw:
            return None
        return get_data_y_extents(
            y_data=kw.get("y_data"),
            norm_y_low=kw.get("norm_y_low"),
            norm_y_high=kw.get("norm_y_high"),
        )

    def mouseDoubleClickEvent(self, event):
        """Open enlarged interactive inspection dialog on double click."""
        if getattr(self, "_last_plot_kwargs", None):
            dlg = ClinicalPlotDetailDialog(
                self._last_plot_kwargs,
                is_dark=self._is_dark,
                parent=self.window(),
                source_canvas=self,
            )
            dlg.exec()
        super().mouseDoubleClickEvent(event)


class ClinicalPlotDetailDialog(QDialog):
    """Enlarged modal view of a single clinical gait plot with interactive zoom/pan toolbar and Y-axis range adjustment."""

    @staticmethod
    def _determine_step_size(ymin: float, ymax: float, ticks: list | None = None) -> float:
        """Determine canonical clinical step increment from ticks or span."""
        if ticks and len(ticks) >= 2:
            try:
                sorted_ticks = sorted(float(t) for t in ticks)
                diffs = [sorted_ticks[i + 1] - sorted_ticks[i] for i in range(len(sorted_ticks) - 1)]
                if diffs:
                    median_diff = float(np.median(diffs))
                    if median_diff > 0:
                        return median_diff
            except Exception:
                pass
        span = float(ymax - ymin) if ymax > ymin else 10.0
        if span <= 25.0:
            return 5.0
        elif span <= 60.0:
            return 10.0
        elif span <= 100.0:
            return 15.0
        else:
            return 20.0

    def __init__(self, kwargs: dict, is_dark: bool = False, parent: QWidget | None = None,
                 source_canvas: ClinicalPlotCanvas | None = None):
        super().__init__(parent)
        self._is_dark = is_dark
        self._source_canvas = source_canvas
        self._updating_scale = False
        self._initial_kwargs = dict(kwargs)
        self._plot_kwargs = dict(kwargs)
        # Extract metadata keys so they don't get passed to plot_gait_data
        self._nominal_ymin = float(self._plot_kwargs.pop("nominal_y_min", kwargs.get("y_min", -30.0)))
        self._nominal_ymax = float(self._plot_kwargs.pop("nominal_y_max", kwargs.get("y_max", 30.0)))
        self._nominal_ticks = self._plot_kwargs.pop("nominal_y_ticks", kwargs.get("y_ticks"))
        self._step_size = self._determine_step_size(self._nominal_ymin, self._nominal_ymax, self._nominal_ticks)
        self._plot_kwargs["show_x_labels"] = True
        self._plot_kwargs["line_width"] = 2.0
        self._ylim_cid = None

        title = kwargs.get("title", "Clinical Plot Detail")
        self.setWindowTitle(f"Interactive Clinical Detail — {title}")

        # Responsive dialog sizing according to available desktop geometry
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            dlg_w = min(960, max(680, int(avail.width() * 0.85)))
            dlg_h = min(680, max(460, int(avail.height() * 0.85)))
            self.resize(dlg_w, dlg_h)
            self.setMinimumSize(min(680, int(avail.width() * 0.70)), min(460, int(avail.height() * 0.70)))
        else:
            self.resize(900, 600)
            self.setMinimumSize(680, 460)

        bg_dlg = "#0F172A" if is_dark else COLOR_SURFACE
        fg_dlg = "#F8FAFC" if is_dark else COLOR_TEXT
        self.setStyleSheet(
            f"background: {bg_dlg}; color: {fg_dlg}; font-family: '{FONT_FAMILY}';"
        )
        apply_native_titlebar_theme(self, dark=is_dark, bg_color=bg_dlg, fg_color=fg_dlg)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Large canvas
        self.canvas = ClinicalPlotCanvas(width=8.0, height=5.0, dpi=110, parent=self)
        self.canvas.apply_theme(dark=is_dark)

        # Check if curve extents touch or exceed default limits
        extents = get_data_y_extents(
            y_data=self._plot_kwargs.get("y_data"),
            norm_y_low=self._plot_kwargs.get("norm_y_low"),
            norm_y_high=self._plot_kwargs.get("norm_y_high"),
        )
        init_ymin = float(self._nominal_ymin)
        init_ymax = float(self._nominal_ymax)

        # Anchor to canonical clinical bounds and expand outward in proper clinical steps
        # Never shrink or cramp the baseline Y-axis into a smaller subrange!
        if extents and source_canvas is None:
            d_min, d_max = extents
            margin = max(0.02 * (init_ymax - init_ymin), 0.5)

            # Expand top limit outward in clinical steps until peak has clear headroom
            while init_ymax <= d_max + margin:
                init_ymax = round(init_ymax + self._step_size, 4)
                if (init_ymax - init_ymin) / self._step_size > 50:
                    break

            # Expand bottom limit outward in clinical steps until trough has clear headroom
            while init_ymin >= d_min - margin:
                init_ymin = round(init_ymin - self._step_size, 4)
                if (init_ymax - init_ymin) / self._step_size > 50:
                    break

            if init_ymin != self._nominal_ymin or init_ymax != self._nominal_ymax:
                self._plot_kwargs["y_min"] = init_ymin
                self._plot_kwargs["y_max"] = init_ymax
                self._plot_kwargs["y_ticks"] = compute_clinical_ticks(init_ymin, init_ymax, self._step_size)
                self._plot_kwargs["force_y_limits"] = True

        if source_canvas is not None:
            self.canvas._scale_states = source_canvas._scale_states
        self.canvas.plot_gait_data(**self._plot_kwargs)
        if source_canvas is not None:
            self.canvas.axes.set_xlim(source_canvas.axes.get_xlim())
            self.canvas.axes.set_ylim(source_canvas.axes.get_ylim())
            src_ticks = source_canvas.axes.get_yticks()
            if src_ticks is not None and len(src_ticks) > 0:
                self.canvas.axes.set_yticks(src_ticks)
        layout.addWidget(self.canvas, 1)

        # Dedicated Y-Axis Range Control Bar
        range_card = QFrame(self)
        range_card.setObjectName("range_card")
        bg_card = "#1E293B" if is_dark else "#F8FAFC"
        border_card = "#334155" if is_dark else COLOR_BORDER
        range_card.setStyleSheet(f"""
            QFrame#range_card {{
                background-color: {bg_card};
                border: 1px solid {border_card};
                border-radius: 8px;
            }}
        """)
        range_layout = QHBoxLayout(range_card)
        range_layout.setContentsMargins(12, 6, 12, 6)
        range_layout.setSpacing(10)

        lbl_title = QLabel("Y-Axis Range:")
        lbl_title.setStyleSheet(f"font-weight: 700; font-size: 12px; color: {'#F8FAFC' if is_dark else COLOR_TEXT};")
        range_layout.addWidget(lbl_title)

        lbl_min = QLabel("Min:")
        lbl_min.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {'#94A3B8' if is_dark else COLOR_MUTED};")
        range_layout.addWidget(lbl_min)

        cur_ymin, cur_ymax = self.canvas.axes.get_ylim()

        self._spin_ymin = QDoubleSpinBox(self)
        self._spin_ymin.setRange(-10000.0, 10000.0)
        self._spin_ymin.setSingleStep(self._step_size)
        self._spin_ymin.setDecimals(1)
        self._spin_ymin.setValue(cur_ymin)
        self._spin_ymin.setFixedWidth(85)
        self._style_spinbox(self._spin_ymin, is_dark)
        self._spin_ymin.editingFinished.connect(self._apply_custom_range)
        range_layout.addWidget(self._spin_ymin)

        lbl_max = QLabel("Max:")
        lbl_max.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {'#94A3B8' if is_dark else COLOR_MUTED};")
        range_layout.addWidget(lbl_max)

        self._spin_ymax = QDoubleSpinBox(self)
        self._spin_ymax.setRange(-10000.0, 10000.0)
        self._spin_ymax.setSingleStep(self._step_size)
        self._spin_ymax.setDecimals(1)
        self._spin_ymax.setValue(cur_ymax)
        self._spin_ymax.setFixedWidth(85)
        self._style_spinbox(self._spin_ymax, is_dark)
        self._spin_ymax.editingFinished.connect(self._apply_custom_range)
        range_layout.addWidget(self._spin_ymax)

        apply_btn = QPushButton("Apply")
        apply_btn.setToolTip("Apply specified Y-axis range to the plot")
        apply_btn.setCursor(Qt.PointingHandCursor)
        self._style_button(apply_btn, is_primary=True, is_dark=is_dark)
        apply_btn.clicked.connect(self._apply_custom_range)
        range_layout.addWidget(apply_btn)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet(f"color: {border_card};")
        range_layout.addWidget(sep1)

        autofit_btn = QPushButton("  Auto-Fit Full Graph")
        autofit_btn.setToolTip("Automatically adjust Y range outward to display all curves with comfortable clearance")
        self._style_button(autofit_btn, is_primary=False, is_dark=is_dark, is_accent=True)
        autofit_btn.setIcon(create_tinted_icon("auto_event.svg", "#FFFFFF", 14))
        autofit_btn.setIconSize(QSize(14, 14))
        autofit_btn.setCursor(Qt.PointingHandCursor)
        autofit_btn.clicked.connect(self._autofit_range)
        range_layout.addWidget(autofit_btn)

        step_lbl = f"{int(self._step_size)}°" if self._step_size.is_integer() else f"{self._step_size:g}°"
        expand_btn = QPushButton(f"  Expand (+{step_lbl})")
        expand_btn.setToolTip(f"Expand current Y-axis range outward by {step_lbl} in both directions")
        self._style_button(expand_btn, is_primary=False, is_dark=is_dark)
        expand_icon_color = "#94A3B8" if is_dark else "#475569"
        expand_btn.setIcon(create_tinted_icon("plus.svg", expand_icon_color, 14))
        expand_btn.setIconSize(QSize(14, 14))
        expand_btn.setCursor(Qt.PointingHandCursor)
        expand_btn.clicked.connect(self._expand_range)
        range_layout.addWidget(expand_btn)

        reset_btn = QPushButton("  Reset Range")
        reset_btn.setToolTip("Reset to nominal clinical range")
        self._style_button(reset_btn, is_primary=False, is_dark=is_dark)
        reset_icon_color = "#94A3B8" if is_dark else "#475569"
        reset_btn.setIcon(create_tinted_icon("refresh.svg", reset_icon_color, 14))
        reset_btn.setIconSize(QSize(14, 14))
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.clicked.connect(self._reset_range)
        range_layout.addWidget(reset_btn)

        range_layout.addStretch()
        layout.addWidget(range_card)

        # Interactive Toolbar with Zoom, Pan, Home, Save
        toolbar_box = QHBoxLayout()
        self._toolbar = NavigationToolbar2QT(self.canvas, self)
        coord_fg = "#94A3B8" if is_dark else "#334155"
        btn_hover = "#334155" if is_dark else "#E2E8F0"
        self._toolbar.setStyleSheet(f"""
            QToolBar {{ background: transparent; border: none; }}
            QToolButton {{ background: transparent; border: none; border-radius: 4px; margin: 1px; padding: 4px; }}
            QToolButton:hover {{ background: {btn_hover}; }}
            QToolButton:checked {{ background: {btn_hover}; border: 1px solid {COLOR_PRIMARY}; }}
            QLabel {{ color: {coord_fg}; font-family: {FONT_FAMILY}; font-size: 13px; font-weight: 600; padding: 4px 12px; }}
        """)
        toolbar_box.addWidget(self._toolbar)
        toolbar_box.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(
            f"QPushButton {{ background: {COLOR_PRIMARY}; color: #FFFFFF; border: 1px solid {COLOR_ACCENT}; border-radius: 4px; padding: 6px 20px; font-weight: 600; }}"
            "QPushButton:hover { background: #115E59; }"
            if is_dark else
            f"QPushButton {{ background: {COLOR_PRIMARY}; color: #FFFFFF; border: 1px solid {COLOR_PRIMARY}; border-radius: 4px; padding: 6px 20px; font-weight: 600; }}"
            "QPushButton:hover { background: #115E59; }"
        )
        close_btn.clicked.connect(self.accept)
        toolbar_box.addWidget(close_btn)
        layout.addLayout(toolbar_box)

        # Listen to axes limits change (e.g. navigation toolbar pan/zoom/home)
        self._ylim_cid = self.canvas.axes.callbacks.connect("ylim_changed", self._on_axes_ylim_changed)
        self._xlim_cid = self.canvas.axes.callbacks.connect("xlim_changed", self._on_axes_xlim_changed)

    def _style_spinbox(self, spinbox: QDoubleSpinBox, is_dark: bool) -> None:
        bg = "#0F172A" if is_dark else "#FFFFFF"
        fg = "#F8FAFC" if is_dark else COLOR_TEXT
        border = "#334155" if is_dark else COLOR_BORDER
        border_focus = COLOR_ACCENT if is_dark else COLOR_PRIMARY
        spinbox.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 12px;
                font-weight: 600;
            }}
            QDoubleSpinBox:focus {{
                border: 1px solid {border_focus};
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 14px;
                background: {'#1E293B' if is_dark else '#F1F5F9'};
                border: none;
            }}
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
                background: {'#334155' if is_dark else '#E2E8F0'};
            }}
        """)

    def _style_button(
        self,
        btn: QPushButton,
        is_primary: bool = False,
        is_dark: bool = False,
        is_accent: bool = False,
    ) -> None:
        if is_primary:
            bg = COLOR_PRIMARY
            hover = "#115E59"
            fg = "#FFFFFF"
            border = COLOR_ACCENT if is_dark else COLOR_PRIMARY
        elif is_accent:
            bg = "#0D9488" if is_dark else "#0F766E"
            hover = "#14B8A6" if is_dark else "#115E59"
            fg = "#FFFFFF"
            border = "transparent"
        else:
            bg = "#1E293B" if is_dark else "#FFFFFF"
            hover = "#334155" if is_dark else "#F1F5F9"
            fg = "#F8FAFC" if is_dark else COLOR_TEXT
            border = "#334155" if is_dark else COLOR_BORDER

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """)

    def _on_axes_ylim_changed(self, ax) -> None:
        """Update spinboxes and the shared graph when the toolbar changes Y limits."""
        if not self._updating_scale:
            self._publish_scale(ylim=ax.get_ylim(), y_ticks=compute_clinical_ticks(
                *ax.get_ylim(), self._step_size))
        try:
            ymin, ymax = ax.get_ylim()
            self._spin_ymin.blockSignals(True)
            self._spin_ymin.setValue(round(ymin, 1))
            self._spin_ymin.blockSignals(False)
            self._spin_ymax.blockSignals(True)
            self._spin_ymax.setValue(round(ymax, 1))
            self._spin_ymax.blockSignals(False)
        except Exception:
            pass

    def _on_axes_xlim_changed(self, ax) -> None:
        if not self._updating_scale:
            self._publish_scale(xlim=ax.get_xlim())

    def _publish_scale(self, *, mode="manual", xlim=None, ylim=None, y_ticks=None):
        self._updating_scale = True
        try:
            self.canvas.set_scale_limits(xlim=xlim, ylim=ylim, y_ticks=y_ticks, mode=mode)
            if (self._source_canvas is not None and isValid(self._source_canvas)
                    and self._source_canvas._graph_id == self.canvas._graph_id):
                self._source_canvas.set_scale_limits(xlim=xlim, ylim=ylim, y_ticks=y_ticks, mode=mode)
        finally:
            self._updating_scale = False

    def _apply_custom_range(self) -> None:
        """Apply limits without rebuilding curves or refreshing the grid."""
        ymin = self._spin_ymin.value()
        ymax = self._spin_ymax.value()
        if ymin >= ymax:
            ymax = ymin + self._step_size
            self._spin_ymax.setValue(ymax)
        ticks = compute_clinical_ticks(ymin, ymax, self._step_size)
        self._publish_scale(ylim=(ymin, ymax), y_ticks=ticks)
        self.canvas._scale_states[self.canvas._graph_id].pop("fit_full", None)
        if hasattr(self, "_toolbar"):
            self._toolbar.update()

    def _autofit_range(self) -> None:
        """Keep existing clinical headroom, allowing subsequent data changes to auto-fit."""
        ymin, ymax = _full_graph_limits(
            self._plot_kwargs.get("y_data"), self._plot_kwargs.get("norm_y_low"),
            self._plot_kwargs.get("norm_y_high"), self._nominal_ymin,
            self._nominal_ymax, self._step_size,
        )
        self._publish_scale(mode="auto", ylim=(ymin, ymax),
                            y_ticks=compute_clinical_ticks(ymin, ymax, self._step_size))
        self.canvas._scale_states[self.canvas._graph_id]["fit_full"] = True
        self._on_axes_ylim_changed_safely()
        if hasattr(self, "_toolbar"):
            self._toolbar.update()

    def _on_axes_ylim_changed_safely(self):
        self._updating_scale = True
        try:
            self._on_axes_ylim_changed(self.canvas.axes)
        finally:
            self._updating_scale = False

    def _expand_range(self) -> None:
        """Expand current Y range outward by one clinical step in both directions."""
        ymin = self._spin_ymin.value()
        ymax = self._spin_ymax.value()
        step = self._step_size
        new_min = round(ymin - step, 4)
        new_max = round(ymax + step, 4)

        self._spin_ymin.blockSignals(True)
        self._spin_ymin.setValue(new_min)
        self._spin_ymin.blockSignals(False)

        self._spin_ymax.blockSignals(True)
        self._spin_ymax.setValue(new_max)
        self._spin_ymax.blockSignals(False)

        self._apply_custom_range()

    def _reset_range(self) -> None:
        """Restore the existing dynamic clinical default and reset toolbar X zoom."""
        ymin, ymax, ticks = calculate_dynamic_y_limits(
            self._plot_kwargs.get("y_data"), self._nominal_ymin, self._nominal_ymax,
            self._nominal_ticks, self._plot_kwargs.get("norm_y_low"),
            self._plot_kwargs.get("norm_y_high"),
        )
        self._publish_scale(mode="reset", xlim=(0, 100), ylim=(ymin, ymax), y_ticks=ticks)
        self.canvas._scale_states[self.canvas._graph_id].pop("fit_full", None)
        self._on_axes_ylim_changed_safely()
        if hasattr(self, "_toolbar"):
            self._toolbar.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        bg = "#0F172A" if self._is_dark else COLOR_SURFACE
        fg = "#F8FAFC" if self._is_dark else COLOR_TEXT
        apply_native_titlebar_theme(self, dark=self._is_dark, bg_color=bg, fg_color=fg)

    def closeEvent(self, event):
        """Clean up callback connections; closing does not change shared limits."""
        self.canvas.axes.callbacks.disconnect(self._xlim_cid)
        if hasattr(self, "_ylim_cid") and self._ylim_cid is not None:
            try:
                self.canvas.axes.callbacks.disconnect(self._ylim_cid)
            except Exception:
                pass
        super().closeEvent(event)



class ClinicalPlotWidget(QFrame):
    """
    Complete clinical plot widget with toolbar and controls.

    Embeds a ``ClinicalPlotCanvas`` with navigation toolbar, zoom/pan,
    and export functionality.
    """

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_SM, SPACE_SM, SPACE_SM, SPACE_SM)
        layout.setSpacing(SPACE_XS)

        # Canvas
        self.canvas = ClinicalPlotCanvas(parent=self)
        layout.addWidget(self.canvas, 1)

        # Toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(SPACE_XS)

        self._toolbar = NavigationToolbar2QT(self.canvas, self)
        self._toolbar.setStyleSheet(f"""
            QToolBar {{ background: transparent; border: none; }}
            QToolButton {{ background: transparent; border: none; border-radius: 4px; margin: 1px; padding: 4px; }}
            QLabel {{ color: #475569; font-family: {FONT_FAMILY}; font-size: 12px; font-weight: 600; padding: 2px 6px; }}
        """)
        toolbar_layout.addWidget(self._toolbar)
        toolbar_layout.addStretch()

        layout.addLayout(toolbar_layout)

    def plot(self, **kwargs) -> None:
        """Forward to the canvas plot method."""
        self.canvas.plot_gait_data(**kwargs)

    def clear(self) -> None:
        self.canvas.clear_plot()
        self.canvas.draw_idle()

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        self.canvas.apply_theme(palette, dark)


class MultiPlotGrid(QWidget):
    """
    A grid of ClinicalPlotCanvas widgets for displaying a page of
    clinical plots (e.g. 5 rows × 3 columns for kinematics).
    """

    def __init__(
        self,
        rows: int = 5,
        cols: int = 3,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._rows = rows
        self._cols = cols

        from PySide6.QtWidgets import QGridLayout
        self._grid = QGridLayout(self)
        self._grid.setSpacing(6)
        self._grid.setContentsMargins(4, 4, 4, 4)

        self._canvases: List[List[ClinicalPlotCanvas]] = []
        self._scale_states = {}
        for r in range(rows):
            row_canvases = []
            for c in range(cols):
                canvas = ClinicalPlotCanvas(
                    width=2.4, height=1.6, dpi=100, parent=self,
                )
                canvas._scale_states = self._scale_states
                self._grid.addWidget(canvas, r, c)
                row_canvases.append(canvas)
            self._canvases.append(row_canvases)

    def get_canvas(self, row: int, col: int) -> ClinicalPlotCanvas:
        return self._canvases[row][col]

    def get_all_canvases(self) -> List[ClinicalPlotCanvas]:
        """Return a flat list of all ClinicalPlotCanvas instances in the grid."""
        canvases: List[ClinicalPlotCanvas] = []
        for row in self._canvases:
            canvases.extend(row)
        return canvases

    def clear_all(self) -> None:
        for row in self._canvases:
            for canvas in row:
                canvas.clear_plot()
                canvas.draw_idle()

    def plot_at(self, row: int, col: int, **kwargs) -> None:
        self._canvases[row][col].plot_gait_data(**kwargs)

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        for row in self._canvases:
            for canvas in row:
                canvas.apply_theme(palette, dark)

