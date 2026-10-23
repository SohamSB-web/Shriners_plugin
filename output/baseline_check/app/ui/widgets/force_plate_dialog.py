# -*- coding: utf-8 -*-
"""
Force Plate Configuration Dialog — PySide6 Clinical Workstation.

Allows clinicians to inspect and adjust force plate parameters:
- Detection of force plates from trial C3D file (FP0, FP1, ...)
- Assignment of Left and Right foot force plates
- Modification of Origin, World Center, and Offset (X, Y, Z)
- Live display of Force, Moment, and Center of Pressure (COP) ranges
- Persistence to session configuration.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme.design_tokens import (
    FONT_FAMILY,
    FONT_FAMILY_MONO,
    FONT_SIZE_BODY,
    FONT_SIZE_CAPTION,
    FONT_SIZE_H3,
    FONT_SIZE_SMALL,
    FONT_WEIGHT_BOLD,
    FONT_WEIGHT_SEMIBOLD,
    RADIUS_MD,
    RADIUS_SM,
    SPACE_LG,
    SPACE_MD,
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
from app.ui.widgets.smooth_scroll import apply_smooth_scroll

logger = logging.getLogger(__name__)


class ForcePlateConfigDialog(QDialog):
    """
    Modal dialog to inspect, select, and adjust force plates for dynamic gait trials.
    """

    configuration_saved = Signal(dict)  # {plate_id: {left, right, origin, world_center, offset}}

    def __init__(
        self,
        session_dir: str,
        trial_filename: str,
        current_left: str = "FP0",
        current_right: str = "0",
        parent: QWidget | None = None,
        is_dark: Optional[bool] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Force Plate Alignment & Assignment — Shriners Workstation")
        self.resize(880, 680)
        self.setMinimumSize(780, 560)

        if is_dark is not None:
            self._is_dark = is_dark
        else:
            from app.services.settings_service import SettingsService
            try:
                self._is_dark = SettingsService().load_app_settings().dark_mode
            except Exception:
                self._is_dark = False

        bg_dlg = "#0F172A" if self._is_dark else COLOR_BACKGROUND
        fg_dlg = "#F8FAFC" if self._is_dark else COLOR_TEXT
        lbl_col = "#CBD5E1" if self._is_dark else "#334155"
        self.setStyleSheet(
            f"QDialog {{ background-color: {bg_dlg}; color: {fg_dlg}; }}"
            f"QLabel {{ color: {lbl_col}; }}"
            f"QRadioButton {{ color: {lbl_col}; font-weight: 500; }}"
        )

        self._session_dir = Path(session_dir)
        self._trial_filename = trial_filename
        self._left_plate = current_left
        self._right_plate = current_right
        self._payload: Dict = {}
        self._entries: Dict[str, Dict[str, list[QLineEdit]]] = {}
        self._left_radios: Dict[str, QRadioButton] = {}
        self._right_radios: Dict[str, QRadioButton] = {}

        self._init_data()
        self._init_ui()

    def _init_data(self) -> None:
        """Extract force plate data from C3D file."""
        c3d_name = Path(self._trial_filename).stem + ".c3d"
        c3d_path = self._session_dir / c3d_name
        if not c3d_path.is_file():
            # Try finding any dynamic c3d
            c3d_files = list(self._session_dir.glob("Dynamic*.c3d"))
            if c3d_files:
                c3d_path = c3d_files[0]

        if c3d_path.is_file():
            try:
                # pyrefly: ignore [missing-import]
                from ezc3d import c3d
                import sys

                gait_dir = str(Path(__file__).resolve().parent.parent.parent.parent / "Gait-lab-Vicon-to-QTM")
                if gait_dir not in sys.path:
                    sys.path.insert(0, gait_dir)
                # pyrefly: ignore [missing-import]
                from Py3_Utils import ProcessForceplateData

                reader = c3d(str(c3d_path), extract_forceplat_data=True)
                self._payload = ProcessForceplateData(reader)
                logger.info("Loaded force plates for %s: %s", c3d_path.name, list(self._payload.keys()))
            except Exception as e:
                logger.warning("Error reading C3D platforms from %s: %s", c3d_path, e)

        # Fallback dummy plate if extraction was empty
        if not self._payload:
            self._payload = {
                "FP0": {
                    "Force": {"X": [0.0], "Y": [0.0], "Z": [-850.0]},
                    "Moment": {"X": [0.0], "Y": [0.0], "Z": [0.0]},
                    "Center_of_Pressure": {"X": [254.0], "Y": [232.0], "Z": [0.0]},
                    "Origin": [0.0, 0.0, 0.0],
                    "WorldCenter": [254.0, 232.0, 0.0],
                    "Offset": {"X": 254.0, "Y": 232.0, "Z": 0.0},
                }
            }

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        layout.setSpacing(SPACE_MD)

        # ── Header ─────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        icon_path = Path(__file__).resolve().parent.parent.parent.parent / "resources" / "icons" / "force_plate.svg"
        if icon_path.is_file():
            icon_lbl = QLabel()
            if self._is_dark:
                try:
                    import re
                    from PySide6.QtSvg import QSvgRenderer
                    from PySide6.QtCore import QByteArray
                    from PySide6.QtGui import QPixmap, QPainter
                    raw = icon_path.read_text(encoding="utf-8")
                    recolored = re.sub(r'stroke="[^"]*"', 'stroke="#FAFAFA"', raw)
                    recolored = re.sub(r'fill="(?!none)[^"]*"', 'fill="#FAFAFA"', recolored)
                    rend = QSvgRenderer(QByteArray(recolored.encode("utf-8")))
                    pix = QPixmap(64, 64)
                    pix.fill(Qt.transparent)
                    p = QPainter(pix)
                    rend.render(p)
                    p.end()
                    pix.setDevicePixelRatio(2.0)
                    icon_lbl.setPixmap(pix)
                except Exception:
                    icon_lbl.setPixmap(QIcon(str(icon_path)).pixmap(32, 32))
            else:
                icon_lbl.setPixmap(QIcon(str(icon_path)).pixmap(32, 32))
            header_row.addWidget(icon_lbl)

        v_head = QVBoxLayout()
        title = QLabel(f"Force Plate Calibration — {self._trial_filename}")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZE_H3, QFont.Bold))
        title_col = "#FAFAFA" if self._is_dark else "#0F172A"
        title.setStyleSheet(f"color: {title_col}; font-weight: 800;")
        v_head.addWidget(title)

        sub = QLabel("Assign Left/Right limb hits, adjust plate origins, world center, and COP offsets")
        sub.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL))
        sub_col = "#A1A1AA" if self._is_dark else "#808080"
        sub.setStyleSheet(f"color: {sub_col};")
        v_head.addWidget(sub)
        header_row.addLayout(v_head)
        header_row.addStretch()

        layout.addLayout(header_row)

        # ── Scroll Area for Force Plates ────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._smooth_scroll = apply_smooth_scroll(scroll)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(SPACE_MD)

        for plate_id, pdata in self._payload.items():
            card = self._create_plate_card(plate_id, pdata)
            scroll_layout.addWidget(card)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        # ── Bottom Action Buttons ───────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(SPACE_SM)

        self._status_lbl = QLabel("")
        self._status_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL))
        status_col = "#A1A1AA" if self._is_dark else "#404040"
        self._status_lbl.setStyleSheet(f"color: {status_col}; font-weight: 500;")
        btn_row.addWidget(self._status_lbl)

        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        if self._is_dark:
            cancel_btn.setStyleSheet(
                "QPushButton { background: #18181B; color: #D4D4D8; border: 1px solid #27272A; "
                "border-radius: 4px; padding: 6px 18px; }"
                "QPushButton:hover { background: #27272A; }"
            )
        else:
            cancel_btn.setStyleSheet(
                "QPushButton { background: #F5F5F5; color: #606060; border: 1px solid #E0E0E0; "
                "border-radius: 4px; padding: 6px 18px; }"
                "QPushButton:hover { background: #EBEBEB; }"
            )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        apply_all_btn = QPushButton("Apply to All Trials")
        apply_all_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        if self._is_dark:
            apply_all_btn.setStyleSheet(
                "QPushButton { background: #1E293B; color: #14B8A6; border: 1.5px solid #14B8A6; "
                "border-radius: 4px; padding: 6px 18px; font-weight: 600; }"
                "QPushButton:hover { background: #334155; }"
            )
        else:
            apply_all_btn.setStyleSheet(
                f"QPushButton {{ background: {COLOR_SURFACE}; color: {COLOR_PRIMARY}; border: 1.5px solid {COLOR_PRIMARY}; "
                f"border-radius: 4px; padding: 6px 18px; font-weight: 600; }}"
                f"QPushButton:hover {{ background: #F0FDFA; }}"
            )
        apply_all_btn.clicked.connect(lambda: self._on_save(apply_to_all=True))
        btn_row.addWidget(apply_all_btn)

        save_btn = QPushButton("Save & Apply")
        save_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        if self._is_dark:
            save_btn.setStyleSheet(
                "QPushButton { background: #0F766E; color: #FFFFFF; border: 1px solid #14B8A6; "
                "border-radius: 4px; padding: 6px 22px; font-weight: 600; }"
                "QPushButton:hover { background: #115E59; }"
            )
        else:
            save_btn.setStyleSheet(
                f"QPushButton {{ background: {COLOR_PRIMARY}; color: #FFFFFF; border: 1px solid {COLOR_PRIMARY}; "
                f"border-radius: 4px; padding: 6px 22px; font-weight: 600; }}"
                f"QPushButton:hover {{ background: #115E59; }}"
            )
        save_btn.clicked.connect(lambda: self._on_save(apply_to_all=False))
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _create_plate_card(self, plate_id: str, pdata: Dict) -> QGroupBox:
        """Create configuration card for an individual force plate."""
        box = QGroupBox(f" Force Platform: {plate_id} ")
        box.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        box_bg = "#0F172A" if self._is_dark else COLOR_SURFACE
        box_border = "#334155" if self._is_dark else COLOR_BORDER
        box_title_col = "#14B8A6" if self._is_dark else COLOR_PRIMARY
        box.setStyleSheet(
            f"QGroupBox {{ background-color: {box_bg}; border: 1px solid {box_border}; "
            f"border-radius: 6px; margin-top: 14px; padding: 16px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {box_title_col}; font-weight: 700; }}"
        )
        card_layout = QVBoxLayout(box)
        card_layout.setSpacing(SPACE_MD)

        # ── Foot assignment row
        assign_row = QHBoxLayout()
        assign_lbl = QLabel("Assigned Limb:")
        assign_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        assign_col = "#14B8A6" if self._is_dark else COLOR_PRIMARY
        assign_lbl.setStyleSheet(f"color: {assign_col}; font-weight: 700;")
        assign_row.addWidget(assign_lbl)

        none_r = QRadioButton("None (Unused)")
        left_r = QRadioButton("Left Leg")
        right_r = QRadioButton("Right Leg")
        if self._is_dark:
            none_r.setStyleSheet("QRadioButton { color: #94A3B8; font-size: 13px; font-weight: 500; }")
            left_r.setStyleSheet("QRadioButton { color: #14B8A6; font-size: 13px; font-weight: 600; }")
            right_r.setStyleSheet("QRadioButton { color: #CBD5E1; font-size: 13px; font-weight: 600; }")
        else:
            none_r.setStyleSheet(f"QRadioButton {{ color: {COLOR_MUTED}; font-size: 13px; font-weight: 500; }}")
            left_r.setStyleSheet(f"QRadioButton {{ color: {COLOR_PRIMARY}; font-size: 13px; font-weight: 600; }}")
            right_r.setStyleSheet(f"QRadioButton {{ color: {COLOR_TEXT}; font-size: 13px; font-weight: 600; }}")

        # Set initial checks
        if self._left_plate == plate_id:
            left_r.setChecked(True)
        elif self._right_plate == plate_id:
            right_r.setChecked(True)
        else:
            none_r.setChecked(True)

        self._left_radios[plate_id] = left_r
        self._right_radios[plate_id] = right_r

        assign_row.addWidget(none_r)
        assign_row.addWidget(left_r)
        assign_row.addWidget(right_r)
        assign_row.addStretch()

        card_layout.addLayout(assign_row)

        # ── Coordinate parameters (Origin, World Center, Offset)
        grid = QGridLayout()
        grid.setSpacing(6)

        headers = ["Coordinate Parameter", "X (mm)", "Y (mm)", "Z (mm)"]
        header_col = "#94A3B8" if self._is_dark else "#334155"
        for col, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
            lbl.setStyleSheet(f"color: {header_col}; font-weight: 700;")
            grid.addWidget(lbl, 0, col)

        self._entries[plate_id] = {}

        if self._is_dark:
            entry_qss = (
                "QLineEdit { background: #0F172A; color: #F8FAFC; border: 1px solid #334155; "
                "border-radius: 4px; padding: 4px; font-weight: 600; }"
                "QLineEdit:focus { border: 2px solid #14B8A6; background: #1E293B; }"
            )
            param_lbl_col = "#CBD5E1"
            stats_bg = "#0F172A"
            stats_border = "#334155"
        else:
            entry_qss = (
                f"QLineEdit {{ background: {COLOR_SURFACE}; color: {COLOR_TEXT}; border: 1px solid {COLOR_BORDER}; "
                "border-radius: 4px; padding: 4px; font-weight: 600; }"
                f"QLineEdit:focus {{ border: 2px solid {COLOR_PRIMARY}; background: {COLOR_SURFACE}; }}"
            )
            param_lbl_col = "#334155"
            stats_bg = COLOR_BACKGROUND
            stats_border = COLOR_BORDER

        def add_param_row(row_idx: int, label_text: str, key_name: str):
            lbl = QLabel(label_text)
            lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
            lbl.setStyleSheet(f"color: {param_lbl_col}; font-weight: 500;")
            grid.addWidget(lbl, row_idx, 0)

            data = pdata.get(key_name, [0.0, 0.0, 0.0])
            if isinstance(data, dict):
                vals = [data.get("X", 0.0), data.get("Y", 0.0), data.get("Z", 0.0)]
            else:
                vals = list(data) if hasattr(data, "__iter__") else [0.0, 0.0, 0.0]

            field_list = []
            for col_idx in range(3):
                val = vals[col_idx] if col_idx < len(vals) else 0.0
                entry = QLineEdit(f"{val:.3f}")
                entry.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_SMALL))
                entry.setAlignment(Qt.AlignCenter)
                entry.setStyleSheet(entry_qss)
                grid.addWidget(entry, row_idx, col_idx + 1)
                field_list.append(entry)

            self._entries[plate_id][key_name] = field_list

        add_param_row(1, "Origin (Local)", "Origin")
        add_param_row(2, "World Center", "WorldCenter")
        add_param_row(3, "COP Offset", "Offset")

        card_layout.addLayout(grid)

        # ── Statistics summary (Force max/min, Moment max/min)
        stats_frame = QFrame()
        stats_frame.setStyleSheet(f"background-color: {stats_bg}; border: 1px solid {stats_border}; border-radius: 6px; padding: 8px;")
        stats_layout = QGridLayout(stats_frame)
        stats_layout.setSpacing(4)

        stats_hdr_col = "#94A3B8" if self._is_dark else COLOR_MUTED
        stats_sig_col = "#CBD5E1" if self._is_dark else "#334155"
        stats_val_col = "#F8FAFC" if self._is_dark else COLOR_TEXT

        for col, h in enumerate(["Signal", "X Min / Max", "Y Min / Max", "Z Min / Max"]):
            lbl = QLabel(h)
            lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, QFont.Bold))
            lbl.setStyleSheet(f"color: {stats_hdr_col}; font-weight: 700; background: transparent;")
            stats_layout.addWidget(lbl, 0, col)

        def calc_min_max(arr):
            try:
                a = np.array(arr, dtype=float)
                finite = a[np.isfinite(a)]
                if len(finite) == 0:
                    return 0.0, 0.0
                return float(np.nanmin(finite)), float(np.nanmax(finite))
            except Exception:
                return 0.0, 0.0

        for r_idx, sig_name in enumerate(["Force", "Moment", "Center_of_Pressure"], start=1):
            lbl = QLabel(sig_name.replace("_", " "))
            lbl.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, QFont.Bold))
            lbl.setStyleSheet(f"color: {stats_sig_col}; font-weight: 600; background: transparent;")
            stats_layout.addWidget(lbl, r_idx, 0)

            for col_idx, axis in enumerate(["X", "Y", "Z"], start=1):
                raw = pdata.get(sig_name, {}).get(axis, [0.0])
                mn, mx = calc_min_max(raw)
                val_lbl = QLabel(f"{mn:.1f} / {mx:.1f}")
                val_lbl.setFont(QFont(FONT_FAMILY_MONO, FONT_SIZE_CAPTION))
                val_lbl.setStyleSheet(f"color: {stats_val_col}; font-weight: 600; background: transparent;")
                stats_layout.addWidget(val_lbl, r_idx, col_idx)

        card_layout.addWidget(stats_frame)
        return box

    def _on_save(self, apply_to_all: bool = False) -> None:
        """Parse user inputs, update payload and selected plates."""
        selected_left = "0"
        selected_right = "0"

        for plate_id in self._payload:
            if self._left_radios[plate_id].isChecked():
                selected_left = plate_id
            if self._right_radios[plate_id].isChecked():
                selected_right = plate_id

            # Parse entries
            try:
                origin_fields = self._entries[plate_id]["Origin"]
                self._payload[plate_id]["Origin"] = [
                    float(origin_fields[0].text()),
                    float(origin_fields[1].text()),
                    float(origin_fields[2].text()),
                ]

                wc_fields = self._entries[plate_id]["WorldCenter"]
                self._payload[plate_id]["WorldCenter"] = [
                    float(wc_fields[0].text()),
                    float(wc_fields[1].text()),
                    float(wc_fields[2].text()),
                ]

                off_fields = self._entries[plate_id]["Offset"]
                self._payload[plate_id]["Offset"] = {
                    "X": float(off_fields[0].text()),
                    "Y": float(off_fields[1].text()),
                    "Z": float(off_fields[2].text()),
                }
            except ValueError:
                QMessageBox.warning(self, "Invalid Value", "Please enter valid floating point numbers for coordinates.")
                return

        self._left_plate = selected_left
        self._right_plate = selected_right

        result = {
            "left_plate": self._left_plate,
            "right_plate": self._right_plate,
            "payload": self._payload,
            "apply_to_all": apply_to_all,
        }
        self.configuration_saved.emit(result)
        logger.info("Saved force plate configuration: Left=%s, Right=%s", self._left_plate, self._right_plate)
        self.accept()

    def get_assignment(self) -> Tuple[str, str, Dict]:
        """Returns (left_plate_id, right_plate_id, payload)"""
        return self._left_plate, self._right_plate, self._payload
