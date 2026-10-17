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
  Page 5: Temporal-Spatial Parameters & Clinical Summary Table
"""

from __future__ import annotations

import logging
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

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
    ) -> str:
        """
        Generate a multi-page vector clinical PDF report.

        Args:
            session_path: Directory containing the session or path to session.xml.
            output_pdf_path: Path where the PDF should be written.
            trials_data: Preloaded dict of trial GCDData (e.g. {"L1": gcd, ...}).
            norm_data: Preloaded normative GCDData.
            patient_info: Optional dict with metadata keys: mrn, session_date, condition.

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

            # Page 5: Temporal-Spatial Summary & Clinical Overview Table
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

        # Top Clinical Header
        fig.text(
            0.05, 0.965,
            p_info["hospital"].upper(),
            fontsize=10.5,
            fontweight="bold",
            color="#0A0A0A",
            family="sans-serif",
        )
        fig.text(
            0.05, 0.942,
            page_title,
            fontsize=12,
            fontweight="bold",
            color="#0A0A0A",
            family="sans-serif",
        )
        fig.text(
            0.05, 0.923,
            f"Patient MRN: {p_info['mrn']}    |    Session Date: {p_info['session_date']}    |    Condition: {p_info['condition']}    |    Exported: {p_info['export_time']}",
            fontsize=8.5,
            color="#52525B",
            family="sans-serif",
        )

        # Legend Banner on the right
        legend_txt = "— L1..L10 (Left)   |   - - R1..R10 (Right)   |   ░ Norm (±1 SD)   |   | Toe-Off"
        fig.text(
            0.52, 0.942,
            legend_txt,
            fontsize=8,
            fontweight="medium",
            color="#27272A",
            family="sans-serif",
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

            # Plot Left Trials (Solid lines)
            for ti, t_key in enumerate([f"L{i}" for i in range(1, 11)]):
                gcd = trials.get(t_key)
                if gcd and l_var and gcd.has_variable(l_var):
                    arr = GCDService.get_variable_array(gcd, l_var)
                    if arr is not None and len(arr) == 101:
                        c = cls.TRIAL_COLORS[ti % len(cls.TRIAL_COLORS)]
                        ax.plot(x, arr, color=c, lw=1.1, ls="-", zorder=4)
                        to = GCDService.get_toe_off(gcd, "Left")
                        if 0 < to < 100:
                            ax.axvline(to, lw=0.6, color=c, ls="--", zorder=3)

            # Plot Right Trials (Dashed lines)
            for ti, t_key in enumerate([f"R{i}" for i in range(1, 11)]):
                gcd = trials.get(t_key)
                if gcd and r_var and gcd.has_variable(r_var):
                    arr = GCDService.get_variable_array(gcd, r_var)
                    if arr is not None and len(arr) == 101:
                        c = cls.TRIAL_COLORS[ti % len(cls.TRIAL_COLORS)]
                        ax.plot(x, arr, color=c, lw=1.0, ls=(0, (3, 2)), zorder=4)
                        to = GCDService.get_toe_off(gcd, "Right")
                        if 0 < to < 100:
                            ax.axvline(to, lw=0.5, color=c, ls=":", zorder=3)

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
        """Create temporal-spatial parameters summary table page."""
        fig = Figure(figsize=(11, 8.5), dpi=150)
        fig.patch.set_facecolor("white")

        # Header
        fig.text(
            0.05, 0.965,
            p_info["hospital"].upper(),
            fontsize=10.5,
            fontweight="bold",
            color="#0A0A0A",
            family="sans-serif",
        )
        fig.text(
            0.05, 0.942,
            "STRIDE & TEMPORAL-SPATIAL SUMMARY",
            fontsize=12,
            fontweight="bold",
            color="#0A0A0A",
            family="sans-serif",
        )
        fig.text(
            0.05, 0.923,
            f"Patient MRN: {p_info['mrn']}    |    Session Date: {p_info['session_date']}    |    Condition: {p_info['condition']}",
            fontsize=8.5,
            color="#52525B",
            family="sans-serif",
        )

        # Collect metrics from active trials
        trial_keys = [k for k in [f"L{i}" for i in range(1, 11)] if k in trials]
        if not trial_keys:
            trial_keys = ["L1"]

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
        for tk in trial_keys:
            num = tk[1:]
            col_headers.append(f"L{num}")
            col_headers.append(f"R{num}")
        col_headers.extend(["L Mean", "R Mean", "Norm TD"])

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

            for tk in trial_keys:
                gcd = trials.get(tk)
                # Left
                lv = cls._get_scalar(gcd, l_var)
                row.append(f"{lv:.2f}" if lv is not None else "--")
                if lv is not None:
                    l_vals.append(lv)

                # Right
                rk = "R" + tk[1:]
                rgcd = trials.get(rk, gcd)
                rv = cls._get_scalar(rgcd, r_var)
                row.append(f"{rv:.2f}" if rv is not None else "--")
                if rv is not None:
                    r_vals.append(rv)

            # Left Mean
            row.append(f"{np.mean(l_vals):.2f}" if l_vals else "--")
            # Right Mean
            row.append(f"{np.mean(r_vals):.2f}" if r_vals else "--")
            # Norm
            row.append(td_norms.get(name, "--"))

            table_data.append(row)

        # Draw Table
        ax = fig.add_axes([0.05, 0.40, 0.90, 0.48])
        ax.axis("off")

        # Custom column widths proportional to content
        total_cols = len(col_headers)
        # 0: Parameter (~0.22), 1: Unit (~0.08), trial cols (~0.05 each), Means (~0.08 each), Norm (~0.10)
        n_trial_cols = len(trial_keys) * 2
        trial_col_w = max(0.045, (1.0 - (0.22 + 0.08 + 0.16 + 0.10)) / max(1, n_trial_cols))
        col_widths = [0.22, 0.08] + [trial_col_w] * n_trial_cols + [0.08, 0.08, 0.10]
        # Normalize sum to 1.0
        w_sum = sum(col_widths)
        col_widths = [w / w_sum for w in col_widths]

        table = ax.table(
            cellText=table_data,
            colLabels=col_headers,
            colWidths=col_widths,
            loc="center",
            cellLoc="center",
        )

        table.auto_set_font_size(False)
        table.set_fontsize(8.0)
        table.scale(1.0, 1.45)

        # Style Header Row and alternating cells
        for (r, c), cell in table.get_celld().items():
            cell.set_edgecolor("#D4D4D8")
            cell.set_linewidth(0.6)
            if r == 0:
                cell.set_facecolor("#18181B")
                cell.get_text().set_color("#FFFFFF")
                cell.get_text().set_weight("bold")
                cell.get_text().set_fontsize(8.2)
            elif c == 0:
                cell.set_facecolor("#F4F4F5")
                cell.get_text().set_weight("bold")
                cell.get_text().set_ha("left")
            elif r % 2 == 1:
                cell.set_facecolor("#FFFFFF")
            else:
                cell.set_facecolor("#FAFAFA")

        # Clinical Sign-off & Interpretation Box
        ax_box = fig.add_axes([0.05, 0.08, 0.90, 0.26])
        ax_box.axis("off")

        # Border for Clinical Notes
        rect = plt.Rectangle((0, 0), 1, 1, fill=False, edgecolor="#A1A1AA", lw=0.7, transform=ax_box.transAxes)
        ax_box.add_patch(rect)

        ax_box.text(
            0.02, 0.86,
            "CLINICAL INTERPRETATION & BIOMECHANICAL OBSERVATIONS:",
            fontsize=8.5,
            fontweight="bold",
            color="#0A0A0A",
            transform=ax_box.transAxes,
        )
        bullets = [
            "• Kinematic & kinetic waveforms conform to Shriners 3D Gait Model (Plug-in Gait PAF v1.0).",
            "• Temporal-spatial parameters calculated across accepted dynamic walking trials.",
            "• Shaded normative band indicates age-matched typically developing (TD) control corridor (± 1 SD).",
        ]
        for bi, bullet in enumerate(bullets):
            ax_box.text(
                0.02, 0.66 - bi * 0.22,
                bullet,
                fontsize=7.8,
                color="#27272A",
                transform=ax_box.transAxes,
            )

        # Signature lines comfortably inside right side without overlap
        ax_box.plot([0.62, 0.96], [0.55, 0.55], color="#52525B", lw=0.8, transform=ax_box.transAxes)
        ax_box.text(0.62, 0.43, "Motion Analysis Physical Therapist / Biomechanist", fontsize=7.5, color="#52525B", transform=ax_box.transAxes)

        ax_box.plot([0.62, 0.96], [0.22, 0.22], color="#52525B", lw=0.8, transform=ax_box.transAxes)
        ax_box.text(0.62, 0.10, "Reviewing Medical Director / Orthopaedic Surgeon", fontsize=7.5, color="#52525B", transform=ax_box.transAxes)

        pdf.savefig(fig)
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
