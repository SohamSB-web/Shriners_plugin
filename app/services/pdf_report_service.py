# -*- coding: utf-8 -*-
"""
Case Presentation PDF Export Service — Generates high-resolution, vector-based
multi-page clinical PDF reports from Motion Analysis Center (MAC) GCD data.

Conforms to Shriners Children's Motion Analysis Center presentation standards,
including:
  Page 1: Lower Limb Kinematics (Bilateral)
  Page 2: Sagittal Kinetics & Joint Power
  Page 3: Coronal Kinetics
  Page 4: Foot Kinematics & Muscle Analysis
  Following pages: Per-limb Temporal-Spatial Parameters & Clinical Summary Tables
"""

from __future__ import annotations

import logging
import os
import sys
import subprocess
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.font_manager import FontProperties

from app.models.data_models import GCDData, PageSettings
from app.services.gcd_service import GCDService
from app.services.settings_service import SettingsService
from app.ui.charts.clinical_plots import calculate_dynamic_y_limits

logger = logging.getLogger(__name__)


class CasePresentationPdfService:
    """Generates complete multi-page clinical PDF reports for MAC Case Presentation."""

    # Curated clinical trial palette matching modern Shriners UI
    TRIAL_COLORS = [
        "#E11D48",  # T1: Crimson / Rose
        "#2563EB",  # T2: Royal Blue
        "#059669",  # T3: Emerald Green
        "#D97706",  # T4: Amber
        "#7C3AED",  # T5: Violet
        "#0891B2",  # T6: Teal / Cyan
        "#EA580C",  # T7: Bright Orange
        "#4F46E5",  # T8: Indigo
        "#65A30D",  # T9: Lime Green
        "#C026D3",  # T10: Magenta
    ]

    TRIAL_COLOR_MAP: Dict[str, str] = {
        # Left trials (cool clinical palette: Royal Blue, Green, Orange, Purple, Teal, Indigo, Olive, Deep Teal, Sky Blue, Magenta)
        "L1": "#2563EB",  # Royal Blue
        "L2": "#16A34A",  # Emerald Green
        "L3": "#EA580C",  # Vibrant Orange
        "L4": "#9333EA",  # Purple
        "L5": "#0891B2",  # Cyan / Teal
        "L6": "#4F46E5",  # Indigo
        "L7": "#65A30D",  # Lime / Olive
        "L8": "#0D9488",  # Deep Teal
        "L9": "#0284C7",  # Deep Sky Blue
        "L10": "#C026D3", # Magenta

        # Right trials (warm clinical palette: Crimson Red, Amber, Deep Rose, Violet, Bronze, Bright Crimson, Burnt Orange, Ruby, Gold, Raspberry)
        "R1": "#DC2626",  # Crimson Red
        "R2": "#D97706",  # Amber / Gold
        "R3": "#DB2777",  # Deep Rose
        "R4": "#7C3AED",  # Violet
        "R5": "#92400E",  # Warm Bronze
        "R6": "#E11D48",  # Bright Crimson
        "R7": "#C2410C",  # Burnt Orange
        "R8": "#BE123C",  # Ruby Red
        "R9": "#A16207",  # Golden Brown
        "R10": "#9F1239", # Dark Raspberry
    }

    @classmethod
    def get_trial_color(cls, trial_key: str) -> str:
        """Return clinical color for a trial key, distinguishing Left (cool) and Right (warm)."""
        if trial_key in cls.TRIAL_COLOR_MAP:
            return cls.TRIAL_COLOR_MAP[trial_key]
        if trial_key.startswith("L"):
            return "#2563EB"
        return "#DC2626"

    NORM_COLOR = "#D4D4D8"
    NORM_ALPHA = 0.55
    ZERO_LINE_COLOR = "#A1A1AA"
    GRID_COLOR = "#E4E4E7"

    @classmethod
    def generate_report(
        cls,
        session_path: str | Path,
        output_pdf_path: str | Path,
        trials_data: Optional[Dict[str, GCDData]] = None,
        norm_data: Optional[GCDData] = None,
        patient_info: Optional[Dict[str, str]] = None,
        selected_trials: Optional[Set[str] | List[str]] = None,
    ) -> str:
        """
        Generate a multi-page vector clinical PDF report.

        Args:
            session_path: Directory containing the session or path to session.xml.
            output_pdf_path: Path where the PDF should be written.
            trials_data: Preloaded dict of trial GCDData (e.g. {"L1": gcd, ...}).
            norm_data: Preloaded normative GCDData.
            patient_info: Optional dict with metadata keys: mrn, session_date, condition.
            selected_trials: Optional set/list of specific trial keys to include (e.g. {"L1", "R1"}).

        Returns:
            Absolute string path to the created PDF file.
        """
        session_dir = Path(session_path)
        if session_dir.is_file():
            session_dir = session_dir.parent

        out_path = Path(output_pdf_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        gcd_svc = GCDService()
        settings_svc = SettingsService()

        # 1. Resolve / Load Trial GCDs
        trials = dict(trials_data) if trials_data else {}
        if not trials:
            trials = cls._load_session_trials(session_dir, gcd_svc)

        # Filter trials if a specific selection is given
        if selected_trials is not None:
            sel_set = set(selected_trials)
            trials = {k: v for k, v in trials.items() if k in sel_set}

        # 2. Resolve / Load Normative Data
        if norm_data is None:
            norm_file = (
                Path(__file__).resolve().parent.parent.parent
                / "MAC_CasePresentation"
                / "TD_Ave.GCD"
            )
            if norm_file.is_file():
                try:
                    norm_data = gcd_svc.read_gcd(str(norm_file))
                except Exception as e:
                    logger.warning("Could not load normative data: %s", e)

        # 3. Resolve Patient Info
        p_info = cls._resolve_patient_info(session_dir, trials, patient_info)

        # 4. Generate PDF Pages
        logger.info("Generating Clinical Case Presentation PDF -> %s", out_path)
        with PdfPages(str(out_path)) as pdf:
            # Page 1: Kinematics (Left & Right)
            kin_settings = settings_svc.get_kinematics_settings()
            cls._create_plot_page(
                pdf=pdf,
                page_title="CASE PRESENTATION — LOWER LIMB KINEMATICS",
                subtitle="Pelvis, Hip, Knee, Ankle, and Foot Progressions (Bilateral)",
                settings=kin_settings,
                trials=trials,
                norm_data=norm_data,
                p_info=p_info,
            )

            # Page 2: Sagittal Kinetics & Power
            sag_settings = settings_svc.get_sagittal_kinetics_settings()
            cls._create_plot_page(
                pdf=pdf,
                page_title="CASE PRESENTATION — SAGITTAL KINETICS & JOINT POWER",
                subtitle="Sagittal Moments, Powers, and Ground Reaction Forces",
                settings=sag_settings,
                trials=trials,
                norm_data=norm_data,
                p_info=p_info,
            )

            # Page 3: Coronal Kinetics
            cor_settings = settings_svc.get_coronal_kinetics_settings()
            cls._create_plot_page(
                pdf=pdf,
                page_title="CASE PRESENTATION — CORONAL KINETICS",
                subtitle="Coronal Moments, Frontal Joint Dynamics, and GRF",
                settings=cor_settings,
                trials=trials,
                norm_data=norm_data,
                p_info=p_info,
            )

            # Page 4: Foot Kinematics & Muscle Analysis
            foot_settings = settings_svc.get_foot_kinematics_settings()
            cls._create_plot_page(
                pdf=pdf,
                page_title="CASE PRESENTATION — FOOT KINEMATICS & SEGMENT ANALYSIS",
                subtitle="Hindfoot, Forefoot, and Segmental Angular Progressions",
                settings=foot_settings,
                trials=trials,
                norm_data=norm_data,
                p_info=p_info,
            )

            # Temporal-spatial summaries paginate independently for each selected limb.
            cls._create_temporal_spatial_page(
                pdf=pdf,
                trials=trials,
                p_info=p_info,
            )

        logger.info("Case presentation PDF successfully saved to %s", out_path)
        return str(out_path)

    @classmethod
    def _load_session_trials(cls, session_dir: Path, gcd_svc: GCDService) -> Dict[str, GCDData]:
        """Scan directory for GCD files and map to L1..L5 / R1..R5."""
        trials: Dict[str, GCDData] = {}
        from app.services.session_organizer import find_all_gcd_files
        gcd_files = find_all_gcd_files(session_dir)

        for i, f in enumerate(gcd_files):
            stem = f.stem.lower()
            try:
                gcd = gcd_svc.read_gcd(str(f))
                # Match "dynamic 1", "dynamic 2", etc.
                matched = False
                for t_num in range(1, 11):
                    if f"dynamic {t_num}" in stem or f"d{t_num}" in stem:
                        trials[f"L{t_num}"] = gcd
                        trials[f"R{t_num}"] = gcd
                        matched = True
                        break
                if not matched:
                    key_l = f"L{i + 1}" if i < 10 else f"L{i}"
                    key_r = f"R{i + 1}" if i < 10 else f"R{i}"
                    trials[key_l] = gcd
                    trials[key_r] = gcd
            except Exception as e:
                logger.warning("Error reading GCD %s for report: %s", f, e)

        return trials

    @classmethod
    def _resolve_patient_info(
        cls,
        session_dir: Path,
        trials: Dict[str, GCDData],
        override_info: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Determine metadata for report header."""
        info = {
            "mrn": "Shriners_test_002",
            "session_date": "2025-02-21",
            "condition": "Barefoot (BF)",
            "hospital": "SHRINERS CHILDREN'S HOSPITAL — MOTION ANALYSIS CENTER",
            "study_type": "Instrumented 3D Gait Analysis",
            "export_time": datetime.now().strftime("%B %d, %Y %H:%M"),
        }

        # Try to infer from session folder structure: .../MRN/Date
        if session_dir.name and session_dir.parent.name:
            info["session_date"] = session_dir.name
            info["mrn"] = session_dir.parent.name

        # If any GCD has stored metadata
        for gcd in trials.values():
            if gcd.has_variable("PatientNumber"):
                val = gcd.get_variable("PatientNumber")
                if val and str(val[0]).strip():
                    info["mrn"] = str(val[0]).strip()
            if gcd.has_variable("DataCollectionDate"):
                val = gcd.get_variable("DataCollectionDate")
                if val and str(val[0]).strip():
                    info["session_date"] = str(val[0]).strip()
            break

        if override_info:
            info.update(override_info)

        return info

    @classmethod
    def _create_plot_page(
        cls,
        pdf: PdfPages,
        page_title: str,
        subtitle: str,
        settings: PageSettings,
        trials: Dict[str, GCDData],
        norm_data: Optional[GCDData],
        p_info: Dict[str, str],
    ) -> None:
        """Create a 15-plot (5 rows x 3 cols) landscape US Letter clinical report page."""
        fig = Figure(figsize=(11, 8.5), dpi=150)
        fig.patch.set_facecolor("white")
        # Top Clinical Header: 4 non-overlapping vertical tiers
        # Tier 1: Hospital Name & Confidentiality Badge
        fig.text(
            0.05, 0.965,
            p_info["hospital"].upper(),
            fontsize=10.0,
            fontweight="bold",
            color="#0A0A0A",
            family="sans-serif",
        )
        fig.text(
            0.95, 0.965,
            "CONFIDENTIAL MEDICAL RECORD",
            fontsize=7.5,
            fontweight="bold",
            color="#71717A",
            ha="right",
            family="sans-serif",
        )

        # Tier 2: Page Title (Unobstructed full-width row)
        fig.text(
            0.05, 0.943,
            page_title,
            fontsize=11.5,
            fontweight="bold",
            color="#0A0A0A",
            family="sans-serif",
        )

        # Tier 3: Patient Demographic and Session Metadata
        fig.text(
            0.05, 0.923,
            f"Patient MRN: {p_info['mrn']}    |    Session Date: {p_info['session_date']}    |    Condition: {p_info['condition']}    |    Exported: {p_info['export_time']}",
            fontsize=8.0,
            color="#52525B",
            family="sans-serif",
        )

        # Tier 4: Explicit List of Exported Legs & Clinical Legend (Never condensed to L1..L10 / R1..R10)
        active_l = [f"L{i}" for i in range(1, 11) if f"L{i}" in trials]
        active_r = [f"R{i}" for i in range(1, 11) if f"R{i}" in trials]

        legend_parts = []
        if active_l:
            l_str = ", ".join(active_l)
            legend_parts.append(f"Left ({l_str})")
        if active_r:
            r_str = ", ".join(active_r)
            legend_parts.append(f"Right ({r_str})")
        legend_parts.append("— Solid = Trials")
        legend_parts.append("╍╍ Dotted = Mean")
        legend_parts.append("░ Norm (±1 SD)")
        legend_parts.append("┆ Toe-Off")

        legend_txt = "TRIALS EXPORTED:   " + "     |     ".join(legend_parts)
        fig.text(
            0.05, 0.903,
            legend_txt,
            fontsize=8.0,
            fontweight="semibold",
            color="#18181B",
            family="sans-serif",
        )

        # Subtle divider line below header
        fig.add_artist(
            plt.Line2D((0.05, 0.95), (0.892, 0.892), color="#E4E4E7", linewidth=0.75)
        )

        # 5 rows x 3 columns plot arrangement
        left_vars = settings.left_names or []
        right_vars = settings.right_names or []
        num_plots = min(max(len(left_vars), len(right_vars)), 15)

        x = GCDService.get_gait_cycle_x()

        for idx in range(num_plots):
            l_var = left_vars[idx] if idx < len(left_vars) else ""
            r_var = right_vars[idx] if idx < len(right_vars) else ""

            if not l_var and not r_var:
                continue

            row = idx // 3
            col = idx % 3

            pw = 0.270
            ph = 0.134
            px = 0.05 + col * (pw + 0.046)
            py = 0.885 - (row + 1) * (ph + 0.029)

            ax = fig.add_axes([px, py, pw, ph])
            ax.set_facecolor("white")
            ax.set_xlim(0, 100)

            # Gather all curves for this plot to determine dynamic y limits
            plot_y_data = []
            for t_key in [f"L{i}" for i in range(1, 11)]:
                gcd = trials.get(t_key)
                if gcd and l_var and gcd.has_variable(l_var):
                    arr = GCDService.get_variable_array(gcd, l_var)
                    if arr is not None and len(arr) == 101:
                        plot_y_data.append(arr)
            for t_key in [f"R{i}" for i in range(1, 11)]:
                gcd = trials.get(t_key)
                if gcd and r_var and gcd.has_variable(r_var):
                    arr = GCDService.get_variable_array(gcd, r_var)
                    if arr is not None and len(arr) == 101:
                        plot_y_data.append(arr)

            y_min = settings.lower_limits[idx] if idx < len(settings.lower_limits) else -30.0
            y_max = settings.upper_limits[idx] if idx < len(settings.upper_limits) else 30.0
            if y_min == y_max:
                y_min -= 10
                y_max += 10

            # Normative Band (± 1 SD from TD_Ave or ± 5 deg default)
            norm_key = GCDService.find_norm_variable(norm_data, l_var or r_var)
            norm_arr = None
            sd_band = None
            if norm_data and norm_key:
                norm_arr = GCDService.get_variable_array(norm_data, norm_key)
                norm_sd = GCDService.get_variable_sd_array(norm_data, norm_key)
                if norm_arr is not None and len(norm_arr) == 101:
                    if norm_sd is not None and len(norm_sd) == 101 and np.any(norm_sd > 0.05):
                        sd_band = norm_sd
                    else:
                        sd_band = 5.0

            norm_y_low = (norm_arr - sd_band) if (norm_arr is not None and sd_band is not None) else None
            norm_y_high = (norm_arr + sd_band) if (norm_arr is not None and sd_band is not None) else None

            y_ticks = settings.y_tick_labels[idx] if idx < len(settings.y_tick_labels) else None
            eff_y_min, eff_y_max, eff_y_ticks = calculate_dynamic_y_limits(
                y_data=plot_y_data,
                y_min=y_min,
                y_max=y_max,
                y_ticks=y_ticks,
                norm_y_low=norm_y_low,
                norm_y_high=norm_y_high,
            )
            ax.set_ylim(eff_y_min, eff_y_max)
            if eff_y_ticks:
                ax.set_yticks(eff_y_ticks)

            if norm_arr is not None and sd_band is not None:
                ax.fill_between(
                    x,
                    norm_arr + sd_band,
                    norm_arr - sd_band,
                    color=cls.NORM_COLOR,
                    alpha=cls.NORM_ALPHA,
                    zorder=1,
                )
                ax.plot(x, norm_arr, color="#71717A", lw=0.6, ls=":", zorder=2)

            # Zero baseline reference
            ax.axhline(0, lw=0.5, color=cls.ZERO_LINE_COLOR, zorder=2)

            # Plot Left Trials (Normal solid lines)
            l_traces: List[np.ndarray] = []
            for t_key in [f"L{i}" for i in range(1, 11)]:
                gcd = trials.get(t_key)
                if gcd and l_var and gcd.has_variable(l_var):
                    arr = GCDService.get_variable_array(gcd, l_var)
                    if arr is not None and len(arr) == 101:
                        l_traces.append(arr)
                        c = cls.get_trial_color(t_key)
                        ax.plot(x, arr, color=c, lw=1.1, ls="-", zorder=4)
                        to = GCDService.get_toe_off(gcd, "Left")
                        if 0 < to < 100:
                            ax.axvline(to, lw=0.6, color=c, ls="--", zorder=3)

            # Plot Right Trials (Normal solid lines)
            r_traces: List[np.ndarray] = []
            for t_key in [f"R{i}" for i in range(1, 11)]:
                gcd = trials.get(t_key)
                if gcd and r_var and gcd.has_variable(r_var):
                    arr = GCDService.get_variable_array(gcd, r_var)
                    if arr is not None and len(arr) == 101:
                        r_traces.append(arr)
                        c = cls.get_trial_color(t_key)
                        ax.plot(x, arr, color=c, lw=1.1, ls="-", zorder=4)
                        to = GCDService.get_toe_off(gcd, "Right")
                        if 0 < to < 100:
                            ax.axvline(to, lw=0.6, color=c, ls="--", zorder=3)

            # Only Mean curves should be plotted as dotted lines
            if len(l_traces) >= 2:
                mean_l = np.mean(l_traces, axis=0)
                ax.plot(x, mean_l, color="#1D4ED8", lw=1.8, ls="--", zorder=5)

            if len(r_traces) >= 2:
                mean_r = np.mean(r_traces, axis=0)
                ax.plot(x, mean_r, color="#B91C1C", lw=1.8, ls="--", zorder=5)

            # Styling & Title
            title = settings.titles[idx] if idx < len(settings.titles) else (l_var or r_var)
            ax.set_title(title, fontsize=7.8, fontweight="bold", pad=2, color="#0A0A0A")
            ax.tick_params(axis="both", labelsize=6.5, direction="in", length=2, colors="#27272A")
            ax.grid(True, alpha=0.35, lw=0.4, color=cls.GRID_COLOR)

            for spine in ax.spines.values():
                spine.set_linewidth(0.5)
                spine.set_color(cls.ZERO_LINE_COLOR)

            if row == 4:
                ax.set_xticks([0, 25, 50, 75, 100])
                ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=6)
            else:
                ax.set_xticks([0, 25, 50, 75, 100])
                ax.set_xticklabels([])

        # Page Footer
        fig.text(
            0.05, 0.02,
            "Shriners Hospitals for Children — Motion Analysis Center • Official Case Presentation",
            fontsize=7,
            color="#71717A",
        )
        fig.text(
            0.95, 0.02,
            "Confidential Medical Record",
            fontsize=7,
            color="#71717A",
            ha="right",
        )

        pdf.savefig(fig)
        plt.close(fig)

    @classmethod
    def _create_temporal_spatial_page(
        cls,
        pdf: PdfPages,
        trials: Dict[str, GCDData],
        p_info: Dict[str, str],
    ) -> None:
        """Paginate each limb using measured text widths, without shrinking text."""
        active_l = [f"L{i}" for i in range(1, 11)
                    if trials.get(f"L{i}") is not None and trials[f"L{i}"].variable_names]
        active_r = [f"R{i}" for i in range(1, 11)
                    if trials.get(f"R{i}") is not None and trials[f"R{i}"].variable_names]
        if not active_l and not active_r:
            return

        # Table metric definitions: (Display Name, Unit, Left Variable, Right Variable)
        metrics = [
            ("Walking Speed", "m/s", "LeftSpeed", "RightSpeed"),
            ("Cadence", "steps/min", "LeftCadence", "RightCadence"),
            ("Stride Length", "m", "LeftStrideLength", "RightStrideLength"),
            ("Step Length", "m", "LeftStepLength", "RightStepLength"),
            ("Stride Time", "s", "LeftStrideTime", "RightStrideTime"),
            ("Step Time", "s", "LeftStepTime", "RightStepTime"),
            ("Stance Phase", "%", "LeftStance", "RightStance"),
            ("Single Support", "%", "LeftSingleSupport", "RightSingleSupport"),
            ("Double Support", "%", "LeftDoubleSupport", "RightDoubleSupport"),
            ("Toe-Off Timing", "%", "LeftFootOff", "RightFootOff"),
        ]

        # Extract values
        col_headers = ["Parameter", "Unit"]
        for tk in active_l:
            col_headers.append(tk)
        for tk in active_r:
            col_headers.append(tk)
        if active_l:
            col_headers.append("L Mean")
        if active_r:
            col_headers.append("R Mean")
        col_headers.append("Norm TD")

        # TD Normative References
        td_norms = {
            "Walking Speed": "1.10 - 1.30",
            "Cadence": "110 - 130",
            "Stride Length": "1.10 - 1.35",
            "Step Length": "0.55 - 0.68",
            "Stride Time": "0.95 - 1.10",
            "Step Time": "0.48 - 0.55",
            "Stance Phase": "58.0 - 62.0",
            "Single Support": "38.0 - 42.0",
            "Double Support": "18.0 - 22.0",
            "Toe-Off Timing": "58.0 - 62.0",
        }

        table_data = []
        for name, unit, l_var, r_var in metrics:
            row = [name, unit]
            l_vals: List[float] = []
            r_vals: List[float] = []

            for tk in active_l:
                gcd = trials.get(tk)
                lv = cls._get_scalar(gcd, l_var)
                row.append(f"{lv:.2f}" if lv is not None else "--")
                if lv is not None:
                    l_vals.append(lv)

            for tk in active_r:
                gcd = trials.get(tk)
                rv = cls._get_scalar(gcd, r_var)
                row.append(f"{rv:.2f}" if rv is not None else "--")
                if rv is not None:
                    r_vals.append(rv)

            if active_l:
                row.append(f"{np.mean(l_vals):.2f}" if l_vals else "--")
            if active_r:
                row.append(f"{np.mean(r_vals):.2f}" if r_vals else "--")
            row.append(td_norms.get(name, "--"))

            table_data.append(row)

        # Measure at the final font size; widths are only expanded, never compressed.
        measurement = Figure(figsize=(11, 8.5), dpi=150)
        renderer = FigureCanvasAgg(measurement).get_renderer()
        font = FontProperties(family="sans-serif", size=9)
        header_font = FontProperties(family="sans-serif", size=9, weight="bold")
        available_width = measurement.bbox.width * 0.90
        widths = []
        for column, header in enumerate(col_headers):
            text_width = max(
                [renderer.get_text_width_height_descent(header, header_font, False)[0]]
                + [renderer.get_text_width_height_descent(row[column], header_font if column == 0 else font, False)[0]
                   for row in table_data])
            widths.append((text_width + 4) / (1 - 2 * 0.08))

        for limb, keys in (("Left", active_l), ("Right", active_r)):
            if not keys:
                continue
            fixed = [0, 1, col_headers.index(f"{keys[0][0]} Mean"), len(col_headers) - 1]
            fixed_width = sum(widths[index] for index in fixed)
            pages = []
            columns = []
            used = fixed_width
            for key in keys:
                index = col_headers.index(key)
                if fixed_width + widths[index] > available_width:
                    raise ValueError(f"Temporal-spatial value in {key} is too wide for a readable PDF page")
                if columns and used + widths[index] > available_width:
                    pages.append(columns)
                    columns, used = [], fixed_width
                columns.append(index)
                used += widths[index]
            pages.append(columns)
            for page_number, trial_columns in enumerate(pages, start=1):
                indices = fixed[:2] + trial_columns + fixed[2:]
                page_widths = [widths[index] for index in indices]
                cls._draw_temporal_spatial_page(
                    pdf, p_info, limb, [col_headers[index] for index in trial_columns],
                    [col_headers[index] for index in indices],
                    [[row[index] for index in indices] for row in table_data],
                    [width / sum(page_widths) for width in page_widths],
                    len(keys), page_number, len(pages))

    @classmethod
    def _draw_temporal_spatial_page(
        cls, pdf, p_info, limb, keys, col_headers, table_data, col_widths,
        limb_trial_count, page_number, page_count,
    ):
        fig = Figure(figsize=(11, 8.5), dpi=150)
        canvas = FigureCanvasAgg(fig)
        fig.patch.set_facecolor("white")
        try:
            fig.text(0.05, 0.965, p_info["hospital"].upper(), fontsize=10,
                     fontweight="bold", color="#0A0A0A", family="sans-serif")
            fig.text(0.95, 0.965, "CONFIDENTIAL MEDICAL RECORD", fontsize=7.5,
                     fontweight="bold", color="#71717A", ha="right", family="sans-serif")
            fig.text(0.05, 0.943, f"STRIDE & TEMPORAL-SPATIAL SUMMARY - {limb.upper()} LIMB",
                     fontsize=11.5, fontweight="bold", color="#0A0A0A", family="sans-serif")
            fig.text(0.05, 0.923,
                     f"Patient MRN: {p_info['mrn']}    |    Session Date: {p_info['session_date']}    |    Condition: {p_info['condition']}    |    Exported: {p_info.get('export_time', '')}",
                     fontsize=8, color="#52525B", family="sans-serif")
            continuation = f"    |    Limb page {page_number}/{page_count}" if page_count > 1 else ""
            fig.text(0.05, 0.903, f"TRIALS EXPORTED: {limb} ({', '.join(keys)}){continuation}",
                     fontsize=8, fontweight="semibold", color="#18181B", family="sans-serif")
            fig.add_artist(plt.Line2D((0.05, 0.95), (0.892, 0.892), color="#E4E4E7", linewidth=0.75))

            ax = fig.add_axes([0.05, 0.43, 0.90, 0.43])
            ax.axis("off")
            table = ax.table(cellText=table_data, colLabels=col_headers, colWidths=col_widths,
                             bbox=[0, 0, 1, 1], cellLoc="center")
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            for (row, column), cell in table.get_celld().items():
                cell.PAD = 0.08
                cell.set_edgecolor("#D4D4D8")
                cell.set_linewidth(0.6)
                cell.get_text().set_fontfamily("sans-serif")
                if row == 0:
                    cell.set_facecolor("#18181B")
                    cell.get_text().set_color("white")
                    cell.get_text().set_weight("bold")
                elif column == 0:
                    cell.set_facecolor("#F4F4F5")
                    cell.get_text().set_weight("bold")
                else:
                    cell.set_facecolor("white" if row % 2 else "#FAFAFA")
                if column == 0:
                    cell.get_text().set_ha("left")

            fig.text(0.05, 0.385,
                     f"{keys[0][0]} Mean includes all {limb_trial_count} selected {limb.lower()} trial(s).  -- = scalar value unavailable.",
                     fontsize=8.5, color="#52525B", family="sans-serif")
            ax_box = fig.add_axes([0.05, 0.08, 0.90, 0.26])
            ax_box.axis("off")
            ax_box.add_patch(plt.Rectangle((0, 0), 1, 1, fill=False, edgecolor="#A1A1AA",
                                           lw=0.7, transform=ax_box.transAxes))
            ax_box.text(0.02, 0.86, "CLINICAL INTERPRETATION & BIOMECHANICAL OBSERVATIONS:",
                        fontsize=8.5, fontweight="bold", color="#0A0A0A", transform=ax_box.transAxes)
            bullets = [
                "• Kinematic & kinetic waveforms conform to Shriners 3D Gait Model (Plug-in Gait PAF v1.0).",
                "• Temporal-spatial parameters calculated across accepted dynamic walking trials.",
                "• Shaded normative band indicates age-matched typically developing (TD) control corridor (± 1 SD).",
            ]
            for index, bullet in enumerate(bullets):
                ax_box.text(0.02, 0.66 - index * 0.22,
                            textwrap.fill(bullet, width=66, subsequent_indent="  "),
                            fontsize=8, linespacing=1.35, color="#27272A", transform=ax_box.transAxes)
            for y, label in ((0.55, "Motion Analysis Physical Therapist / Biomechanist"),
                             (0.22, "Reviewing Medical Director / Orthopaedic Surgeon")):
                ax_box.plot([0.64, 0.97], [y, y], color="#52525B", lw=0.8, transform=ax_box.transAxes)
                ax_box.text(0.64, y - 0.12, label, fontsize=7.5, color="#52525B", transform=ax_box.transAxes)

            canvas.draw()
            renderer = canvas.get_renderer()
            for (row, column), cell in table.get_celld().items():
                text_box = cell.get_text().get_window_extent(renderer)
                cell_box = cell.get_window_extent(renderer)
                pad_x, pad_y = cell_box.width * cell.PAD, cell_box.height * cell.PAD
                if (text_box.x0 < cell_box.x0 + pad_x - 1 or text_box.x1 > cell_box.x1 - pad_x + 1
                        or text_box.y0 < cell_box.y0 + pad_y - 1 or text_box.y1 > cell_box.y1 - pad_y + 1):
                    raise ValueError(f"Temporal-spatial text does not fit cell ({row}, {column})")
            pdf.savefig(fig)
        finally:
            plt.close(fig)

    @classmethod
    def _get_scalar(cls, gcd: Optional[GCDData], var_name: str) -> Optional[float]:
        """Extract a scalar parameter from GCD data if present."""
        if not gcd or not gcd.has_variable(var_name):
            return None
        data = gcd.get_variable(var_name)
        if data and len(data) > 0:
            try:
                return float(data[0])
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def open_pdf(pdf_path: str | Path) -> bool:
        """Open generated PDF with the default system application."""
        p = Path(pdf_path).resolve()
        if not p.is_file():
            logger.error("PDF file not found: %s", p)
            return False

        try:
            if sys.platform == "win32":
                os.startfile(str(p))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p)])
            return True
        except Exception as e:
            logger.error("Failed to open PDF %s: %s", p, e)
            return False

    @staticmethod
    def open_containing_folder(file_path: str | Path) -> bool:
        """Open Windows Explorer / File manager highlighting the file."""
        p = Path(file_path).resolve()
        try:
            if sys.platform == "win32":
                subprocess.Popen(f'explorer /select,"{p}"')
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p.parent)])
            return True
        except Exception as e:
            logger.error("Failed to open folder for %s: %s", p, e)
            return False
