# -*- coding: utf-8 -*-
"""
Event Details Dialog — Clinical inspection, manual editing, and QTM synchronization of gait events.

Allows clinicians to:
- Review auto-detected and manual gait events (RSTRIKE, ROFF, LSTRIKE, LOFF)
- Manually add new gait events with specific frame and time
- Modify or remove existing auto-labeled events
- Verify stride pairing integrity
- Directly synchronize updated events with Qualisys Track Manager (QTM) over gRPC
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.event_service import check_event_pairing, fetch_events_from_qtm, save_trial_events, send_events_to_qtm
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
    SPACE_XL,
    SPACE_XS,
)
from app.ui.widgets.smooth_scroll import apply_smooth_scroll

logger = logging.getLogger(__name__)


from app.services.frame_coordinates import frame_to_time, frame_to_index, normalize_saved_events, recording_start_frame, trace_event, sample_index_to_frame


class EventDetailsDialog(QDialog):
    """
    Modal dialog displaying comprehensive gait event detection results
    with full manual editing capabilities and direct QTM synchronization.
    """

    rerun_requested = Signal(str)  # trial_filename
    events_updated = Signal(str, dict)  # trial_filename, updated_events_dict

    # Event styling map: (badge_bg, badge_fg, description, limb)
    EVENT_META = {
        "RSTRIKE": ("#F0FDF4", "#166534", "Right Heel Strike (Initial Contact)", "Right"),
        "AUTO_RHS": ("#F0FDF4", "#166534", "Right Heel Strike (Initial Contact)", "Right"),
        "ROFF": ("#FEF3C7", "#92400E", "Right Foot Off (Toe Off)", "Right"),
        "AUTO_ROF": ("#FEF3C7", "#92400E", "Right Foot Off (Toe Off)", "Right"),
        "LSTRIKE": ("#EFF6FF", "#1E40AF", "Left Heel Strike (Initial Contact)", "Left"),
        "AUTO_LHS": ("#EFF6FF", "#1E40AF", "Left Heel Strike (Initial Contact)", "Left"),
        "LOFF": ("#F5F3FF", "#5B21B6", "Left Foot Off (Toe Off)", "Left"),
        "AUTO_LOF": ("#F5F3FF", "#5B21B6", "Left Foot Off (Toe Off)", "Left"),
    }

    EVENT_OPTIONS = [
        ("RSTRIKE", "RSTRIKE — Right Heel Strike (Initial Contact)"),
        ("ROFF", "ROFF — Right Foot Off (Toe Off)"),
        ("LSTRIKE", "LSTRIKE — Left Heel Strike (Initial Contact)"),
        ("LOFF", "LOFF — Left Foot Off (Toe Off)"),
    ]

    def __init__(
        self,
        trial_filename: str,
        events_info: Optional[Dict[str, Any]] = None,
        frame_rate: float = 100.0,
        session_dir: Optional[str | Path] = None,
        parent: Optional[QWidget] = None,
        is_dark: Optional[bool] = None,
    ):
        super().__init__(parent)
        self.trial_filename = trial_filename
        self.events_info = events_info or {}
        meta = self.events_info.get("meta", {})
        if "frame_rate" in meta and float(meta["frame_rate"]) > 0:
            self.frame_rate = float(meta["frame_rate"])
        elif "frequency" in meta and float(meta["frequency"]) > 0:
            self.frame_rate = float(meta["frequency"])
        else:
            self.frame_rate = max(1.0, float(frame_rate or 100.0))
        self._offset = int(meta.get("initial_frame_offset", 0))
        self._qtm_base = recording_start_frame(meta)

        # Determine session directory
        if session_dir is not None:
            self.session_dir = Path(session_dir)
        elif self.events_info.get("filepath"):
            self.session_dir = Path(self.events_info["filepath"]).parent
        elif parent and hasattr(parent, "_session_path") and parent._session_path:
            self.session_dir = Path(parent._session_path).parent
        else:
            self.session_dir = Path(".")

        # Resolve exact trial frame rate from corresponding C3D if available
        if self.session_dir and self.trial_filename:
            stem = Path(self.trial_filename).stem
            c3d_candidates = [
                self.session_dir / f"{stem}.c3d",
                self.session_dir / f"{stem.lower()}.c3d",
            ]
            for cand in c3d_candidates:
                if cand.is_file():
                    try:
                        import ezc3d
                        c_obj = ezc3d.c3d(str(cand))
                        c_freq = float(c_obj["header"]["points"]["frame_rate"])
                        self._offset = int(c_obj["header"]["points"]["first_frame"])
                        meta = dict(meta, initial_frame_offset=self._offset, recording_start_frame=sample_index_to_frame(self._offset),
                                    total_frames=int(c_obj["data"]["points"].shape[2]))
                        self.events_info["meta"] = meta
                        if c_freq > 0:
                            self.frame_rate = c_freq
                        break
                    except Exception:
                        pass

        # In-memory working copy of events
        self._qtm_base = recording_start_frame(meta)
        raw_events = normalize_saved_events(self.events_info.get("events", []), meta)
        self._events: List[Dict[str, Any]] = []
        for e in raw_events:
            f = int(e.get("frame", 0))
            lbl = str(e.get("label", "")).upper()
            rel_f = frame_to_index(f, self._qtm_base)
            trace_event("UI_display", lbl, f, self.frame_rate, self._qtm_base)
            t_s = frame_to_time(f, self.frame_rate)
            self._events.append({
                "frame": f,
                "label": lbl,
                "time": float(t_s),
                "relative_frame": int(rel_f),
                "side": e.get("side") or ("R" if "R" in lbl else ("L" if "L" in lbl else "")),
                "type": e.get("type") or ("STRIKE" if ("STRIKE" in lbl or "HS" in lbl) else ("OFF" if ("OFF" in lbl or "OF" in lbl) else "")),
            })
        self._events.sort(key=lambda x: x["frame"])
        self._original_events: List[Dict[str, Any]] = [dict(e) for e in self._events]
        self._has_unsaved_changes = False

        self.setWindowTitle(f"Gait Event Details & QTM Sync — {self.trial_filename}")
        self.setMinimumSize(880, 720)
        self.resize(960, 820)

        if is_dark is not None:
            self._is_dark = is_dark
        else:
            from app.services.settings_service import SettingsService
            try:
                self._is_dark = SettingsService().load_app_settings().dark_mode
            except Exception:
                self._is_dark = False

        bg_dlg = "#0F172A" if self._is_dark else "#F8FAFC"
        fg_dlg = "#F8FAFC" if self._is_dark else "#0F172A"
        input_bg = "#1E293B" if self._is_dark else "#FFFFFF"
        input_fg = "#F8FAFC" if self._is_dark else "#0F172A"
        input_bdr = "#475569" if self._is_dark else "#CBD5E1"

        self.setStyleSheet(
            f"QDialog {{ background-color: {bg_dlg}; color: {fg_dlg}; font-family: '{FONT_FAMILY}'; }}"
            f"QComboBox {{ background-color: {input_bg}; color: {input_fg}; border: 1px solid {input_bdr}; border-radius: 4px; padding: 4px 8px; font-size: 12px; }}"
            f"QComboBox::drop-down {{ border: none; width: 20px; }}"
            f"QComboBox QAbstractItemView {{ background-color: {input_bg}; color: {input_fg}; selection-background-color: #0D9488; selection-color: #FFFFFF; }}"
            f"QSpinBox {{ background-color: {input_bg}; color: {input_fg}; border: 1px solid {input_bdr}; border-radius: 4px; padding: 4px 8px; font-size: 13px; font-weight: 600; }}"
        )

        self._init_ui()
        self._setup_shortcuts()
        self._refresh_all_views()

    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts for fast clinical workflow."""
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self._on_save_and_update_qtm)

        del_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self)
        del_shortcut.activated.connect(self._on_delete_selected_event)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(8)

        # ── 1. Header ──────────────────────────────────────────────────────────
        header_layout = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        title = QLabel(f"GAIT EVENTS: {self.trial_filename}")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZE_H3, QFont.Bold))
        title_color = "#F8FAFC" if self._is_dark else "#0F172A"
        title.setStyleSheet(f"letter-spacing: 0.5px; color: {title_color};")
        title_col.addWidget(title)

        sub = QLabel("Kinematic detection, manual event refinement, and direct QTM timeline synchronization.")
        sub.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL))
        sub_color = "#94A3B8" if self._is_dark else "#64748B"
        sub.setStyleSheet(f"color: {sub_color};")
        title_col.addWidget(sub)
        header_layout.addLayout(title_col)

        header_layout.addStretch()

        # Status pills column
        pill_row = QHBoxLayout()
        pill_row.setSpacing(SPACE_SM)

        self._status_pill = QLabel("● Stride Pairing: PASS")
        self._status_pill.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, FONT_WEIGHT_SEMIBOLD))
        pill_row.addWidget(self._status_pill)

        self._sync_badge = QLabel("● Synced")
        self._sync_badge.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, FONT_WEIGHT_SEMIBOLD))
        pill_row.addWidget(self._sync_badge)

        header_layout.addLayout(pill_row)
        layout.addLayout(header_layout)

        # ── 2. Metric Cards Grid ───────────────────────────────────────────────
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(SPACE_MD)

        self._metric_labels: Dict[str, QLabel] = {}
        metrics = [
            ("R. HEEL STRIKE", "r_hs", "RSTRIKE", "#14B8A6"),
            ("R. FOOT OFF", "r_to", "ROFF", "#F59E0B"),
            ("L. HEEL STRIKE", "l_hs", "LSTRIKE", "#3B82F6"),
            ("L. FOOT OFF", "l_to", "LOFF", "#8B5CF6"),
        ]

        card_bg = "#1E293B" if self._is_dark else "#FFFFFF"
        card_border = "#334155" if self._is_dark else "#E2E8F0"

        for title_str, key_name, code, accent_color in metrics:
            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{"
                f"  background-color: {card_bg};"
                f"  border: 1px solid {card_border};"
                f"  border-radius: {RADIUS_MD}px;"
                f"  padding: 4px 10px;"
                f"}}"
            )
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(8, 4, 8, 4)
            c_layout.setSpacing(1)

            t_lbl = QLabel(title_str)
            t_lbl.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
            t_col = "#94A3B8" if self._is_dark else "#64748B"
            t_lbl.setStyleSheet(f"color: {t_col}; letter-spacing: 0.5px; border: none;")
            c_layout.addWidget(t_lbl)

            val_row = QHBoxLayout()
            v_lbl = QLabel("0")
            v_lbl.setFont(QFont(FONT_FAMILY, 17, QFont.Bold))
            v_col = "#F8FAFC" if self._is_dark else "#0F172A"
            v_lbl.setStyleSheet(f"color: {v_col}; border: none;")
            self._metric_labels[key_name] = v_lbl
            val_row.addWidget(v_lbl)

            code_badge = QLabel(code)
            code_badge.setFont(QFont(FONT_FAMILY_MONO, 9, QFont.Bold))
            code_badge.setStyleSheet(
                f"background: transparent; color: {accent_color}; "
                f"border: 1px solid {accent_color}; border-radius: 4px; padding: 2px 6px;"
            )
            val_row.addWidget(code_badge)
            val_row.addStretch()

            c_layout.addLayout(val_row)
            cards_layout.addWidget(card)

        layout.addLayout(cards_layout)

        # ── 3. Manual Event Entry & Editing Workstation Card ─────────────────────
        manual_card = QFrame()
        manual_card.setObjectName("manualCard")
        manual_card.setStyleSheet(
            f"QFrame#manualCard {{"
            f"  background-color: {card_bg};"
            f"  border: 1px solid {card_border};"
            f"  border-radius: {RADIUS_MD}px;"
            f"}}"
        )
        m_layout = QVBoxLayout(manual_card)
        m_layout.setContentsMargins(14, 8, 14, 8)
        m_layout.setSpacing(6)

        # 3a. Header Row & Live Mode Status
        m_head_row = QHBoxLayout()
        m_head_row.setSpacing(SPACE_SM)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        m_header = QLabel("MANUAL GAIT EVENT REFINEMENT")
        m_header.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        m_head_col = "#14B8A6" if self._is_dark else "#0D9488"
        m_header.setStyleSheet(f"color: {m_head_col}; letter-spacing: 0.8px; border: none;")
        title_box.addWidget(m_header)

        m_sub = QLabel("Select event phase, adjust frame position, and commit changes.")
        m_sub.setFont(QFont(FONT_FAMILY, 9))
        m_sub_col = "#94A3B8" if self._is_dark else "#64748B"
        m_sub.setStyleSheet(f"color: {m_sub_col}; border: none;")
        title_box.addWidget(m_sub)
        m_head_row.addLayout(title_box)

        m_head_row.addStretch()

        self._mode_pill = QLabel("● Ready: Add New Event")
        self._mode_pill.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self._set_mode_pill_style(is_editing=False)
        m_head_row.addWidget(self._mode_pill)

        # Clear Selection button (shown only when a table row is actively selected)
        self._clear_btn = QPushButton("✕ Clear Selection")
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self._clear_btn.setFixedHeight(24)
        clear_fg = "#94A3B8" if self._is_dark else "#64748B"
        clear_bdr = "#334155" if self._is_dark else "#CBD5E1"
        self._clear_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {clear_fg}; border: 1px solid {clear_bdr}; "
            f"border-radius: 12px; padding: 2px 10px; }}"
            f"QPushButton:hover {{ color: {'#F8FAFC' if self._is_dark else '#0F172A'}; background: {'#334155' if self._is_dark else '#F1F5F9'}; }}"
        )
        self._clear_btn.clicked.connect(self._on_clear_selection_clicked)
        self._clear_btn.setVisible(False)
        m_head_row.addWidget(self._clear_btn)

        m_layout.addLayout(m_head_row)

        # 3b. Interactive Event Phase Selector (Segmented Cards)
        event_selector_row = QHBoxLayout()
        event_selector_row.setSpacing(SPACE_SM)

        self._event_btn_defs = [
            ("RSTRIKE", "R. Heel Strike", "RSTRIKE"),
            ("ROFF", "R. Foot Off", "ROFF"),
            ("LSTRIKE", "L. Heel Strike", "LSTRIKE"),
            ("LOFF", "L. Foot Off", "LOFF"),
        ]
        self._event_buttons: Dict[str, QPushButton] = {}
        self._selected_event_code = "RSTRIKE"

        for code, label_text, badge_code in self._event_btn_defs:
            btn = QPushButton(f"{label_text}  ({badge_code})")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda _, c=code: self._set_active_event_type(c))
            self._event_buttons[code] = btn
            event_selector_row.addWidget(btn, 1)

        m_layout.addLayout(event_selector_row)

        # Hidden QComboBox for backward compatibility with automated test suites
        self._combo_event = QComboBox()
        for code, disp in self.EVENT_OPTIONS:
            self._combo_event.addItem(disp, code)
        self._combo_event.currentIndexChanged.connect(self._on_combo_index_changed)
        self._combo_event.setVisible(False)
        m_layout.addWidget(self._combo_event)

        # 3c. Frame Stepper, Timing Badge & Workstation Action Controls
        controls_row = QHBoxLayout()
        controls_row.setSpacing(SPACE_MD)

        # Frame Stepper Group
        stepper_box = QHBoxLayout()
        stepper_box.setSpacing(4)

        frame_lbl = QLabel("Frame:")
        frame_lbl.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        frame_lbl.setFixedWidth(46)
        frame_lbl_col = "#94A3B8" if self._is_dark else "#64748B"
        frame_lbl.setStyleSheet(f"color: {frame_lbl_col}; border: none; letter-spacing: 0.5px;")
        stepper_box.addWidget(frame_lbl)

        btn_step_style = (
            "QPushButton { background: #1E293B; color: #CBD5E1; border: 1px solid #475569; "
            "border-radius: 4px; font-weight: 700; font-size: 11px; padding: 0px; }"
            "QPushButton:hover { background: #334155; color: #F8FAFC; border-color: #64748B; }"
            if self._is_dark
            else
            "QPushButton { background: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; "
            "border-radius: 4px; font-weight: 700; font-size: 11px; padding: 0px; }"
            "QPushButton:hover { background: #E2E8F0; color: #0F172A; border-color: #94A3B8; }"
        )

        btn_m10 = QPushButton("-10")
        btn_m10.setFont(QFont(FONT_FAMILY_MONO, 10, QFont.Bold))
        btn_m10.setCursor(Qt.PointingHandCursor)
        btn_m10.setStyleSheet(btn_step_style)
        btn_m10.setFixedSize(30, 32)
        btn_m10.setToolTip("Step back 10 frames")
        btn_m10.clicked.connect(lambda: self._nudge_frame(-10))
        stepper_box.addWidget(btn_m10)

        btn_m1 = QPushButton("-1")
        btn_m1.setFont(QFont(FONT_FAMILY_MONO, 10, QFont.Bold))
        btn_m1.setCursor(Qt.PointingHandCursor)
        btn_m1.setStyleSheet(btn_step_style)
        btn_m1.setFixedSize(26, 32)
        btn_m1.setToolTip("Step back 1 frame")
        btn_m1.clicked.connect(lambda: self._nudge_frame(-1))
        stepper_box.addWidget(btn_m1)

        self._spin_frame = QSpinBox()
        self._spin_frame.setFont(QFont(FONT_FAMILY_MONO, 12, QFont.Bold))
        self._spin_frame.setRange(self._qtm_base, self._qtm_base + int(self.events_info.get("meta", {}).get("total_frames") or 1000000) - 1)
        self._spin_frame.setSingleStep(1)
        self._spin_frame.setFixedSize(70, 32)
        self._spin_frame.setAlignment(Qt.AlignCenter)
        self._spin_frame.setButtonSymbols(QSpinBox.NoButtons)
        spin_bg = "#0F172A" if self._is_dark else "#FFFFFF"
        spin_fg = "#F8FAFC" if self._is_dark else "#0F172A"
        spin_bdr = "#475569" if self._is_dark else "#CBD5E1"
        self._spin_frame.setStyleSheet(
            f"QSpinBox {{ background-color: {spin_bg}; color: {spin_fg}; border: 1.5px solid {spin_bdr}; "
            f"border-radius: 4px; padding: 2px 2px; }}"
            f"QSpinBox:focus {{ border-color: #0D9488; }}"
        )
        self._spin_frame.valueChanged.connect(self._on_spin_frame_changed)
        stepper_box.addWidget(self._spin_frame)

        btn_p1 = QPushButton("+1")
        btn_p1.setFont(QFont(FONT_FAMILY_MONO, 10, QFont.Bold))
        btn_p1.setCursor(Qt.PointingHandCursor)
        btn_p1.setStyleSheet(btn_step_style)
        btn_p1.setFixedSize(26, 32)
        btn_p1.setToolTip("Step forward 1 frame")
        btn_p1.clicked.connect(lambda: self._nudge_frame(1))
        stepper_box.addWidget(btn_p1)

        btn_p10 = QPushButton("+10")
        btn_p10.setFont(QFont(FONT_FAMILY_MONO, 10, QFont.Bold))
        btn_p10.setCursor(Qt.PointingHandCursor)
        btn_p10.setStyleSheet(btn_step_style)
        btn_p10.setFixedSize(30, 32)
        btn_p10.setToolTip("Step forward 10 frames")
        btn_p10.clicked.connect(lambda: self._nudge_frame(10))
        stepper_box.addWidget(btn_p10)

        controls_row.addLayout(stepper_box)

        # Timing Badge Pill
        time_pill_bg = "#0F172A" if self._is_dark else "#F8FAFC"
        time_pill_bdr = "#334155" if self._is_dark else "#E2E8F0"
        time_pill_fg = "#2DD4BF" if self._is_dark else "#0F766E"

        self._calc_time_lbl = QLabel("t = 0.000 s")
        self._calc_time_lbl.setFont(QFont(FONT_FAMILY_MONO, 11, QFont.Bold))
        self._calc_time_lbl.setAlignment(Qt.AlignCenter)
        self._calc_time_lbl.setFixedSize(95, 32)
        self._calc_time_lbl.setStyleSheet(
            f"background-color: {time_pill_bg}; color: {time_pill_fg}; border: 1px solid {time_pill_bdr}; "
            f"border-radius: 4px; padding: 2px 6px;"
        )
        controls_row.addWidget(self._calc_time_lbl)

        controls_row.addStretch()

        # Action: Add Event
        self._add_btn = QPushButton("+ Add Event")
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self._add_btn.setFixedSize(115, 34)
        self._add_btn.setStyleSheet(
            "QPushButton { background: #0D9488; color: #FFFFFF; border: none; "
            "border-radius: 4px; padding: 6px 14px; font-weight: 700; }"
            "QPushButton:hover { background: #14B8A6; }"
            "QPushButton:pressed { background: #0F766E; }"
        )
        self._add_btn.clicked.connect(self._on_add_event_clicked)
        controls_row.addWidget(self._add_btn)

        # Action: Update Event
        self._update_btn = QPushButton("✎ Update")
        self._update_btn.setCursor(Qt.PointingHandCursor)
        self._update_btn.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self._update_btn.setFixedSize(95, 34)
        self._set_update_btn_style(enabled=False)
        self._update_btn.clicked.connect(self._on_update_selected_clicked)
        controls_row.addWidget(self._update_btn)

        # Action: Delete Event
        self._del_selected_btn = QPushButton("✕ Delete")
        self._del_selected_btn.setCursor(Qt.PointingHandCursor)
        self._del_selected_btn.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self._del_selected_btn.setFixedSize(90, 34)
        self._set_del_btn_style(enabled=False)
        self._del_selected_btn.clicked.connect(self._on_delete_selected_event)
        controls_row.addWidget(self._del_selected_btn)

        m_layout.addLayout(controls_row)
        layout.addWidget(manual_card)

        # Initial button active styling
        self._update_event_buttons_style()

        # ── 4. Chronological Events Table ──────────────────────────────────────
        table_card = QFrame()
        table_card.setObjectName("tableCard")
        table_card.setStyleSheet(
            f"QFrame#tableCard {{"
            f"  background-color: {card_bg};"
            f"  border: 1px solid {card_border};"
            f"  border-radius: {RADIUS_MD}px;"
            f"}}"
        )
        tc_layout = QVBoxLayout(table_card)
        tc_layout.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        tc_layout.setSpacing(SPACE_SM)

        table_header_row = QHBoxLayout()
        t_header = QLabel("EVENT TIMELINE & CHRONOLOGY")
        t_header.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        t_head_col = "#94A3B8" if self._is_dark else "#64748B"
        t_header.setStyleSheet(f"color: {t_head_col}; letter-spacing: 0.8px; border: none;")
        table_header_row.addWidget(t_header)

        hint = QLabel("Select a row to edit or delete | Frame updates sync directly to QTM")
        hint.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION))
        hint.setStyleSheet("color: #94A3B8; border: none;")
        table_header_row.addStretch()
        table_header_row.addWidget(hint)
        tc_layout.addLayout(table_header_row)

        self._table = QTableWidget()
        self._table_smooth = apply_smooth_scroll(self._table)
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["#", "Frame", "Time (s)", "Event Label", "Description / Limb", "Actions"])
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(38)
        self._table.setMinimumHeight(240)
        self._table.setShowGrid(False)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.itemSelectionChanged.connect(self._on_table_selection_changed)

        if self._is_dark:
            self._table.setStyleSheet(
                "QTableWidget { border: none; background-color: #0F172A; alternate-background-color: #1E293B; color: #F8FAFC; }"
                "QHeaderView::section { background-color: #1E293B; color: #CBD5E1; font-weight: 700; font-size: 11px; padding: 8px 6px; border: none; border-bottom: 1px solid #334155; }"
                "QTableWidget::item:selected { background-color: #0F766E; color: #FFFFFF; }"
            )
        else:
            self._table.setStyleSheet(
                "QTableWidget { border: none; background-color: #FFFFFF; alternate-background-color: #F8FAFC; color: #0F172A; }"
                "QHeaderView::section { background-color: #F8FAFC; color: #475569; font-weight: 700; font-size: 11px; padding: 8px 6px; border: none; border-bottom: 1px solid #E2E8F0; }"
                "QTableWidget::item:selected { background-color: #CCFBF1; color: #0F766E; }"
            )

        tc_layout.setContentsMargins(12, 8, 12, 8)
        tc_layout.setSpacing(4)
        tc_layout.addWidget(self._table, 1)
        layout.addWidget(table_card, 1)

        # ── 5. Status Toast Banner ─────────────────────────────────────────────
        self._toast_banner = QFrame()
        self._toast_banner.setVisible(False)
        self._toast_banner.setStyleSheet(
            f"border-radius: {RADIUS_SM}px; padding: 4px 10px; margin-top: 0px;"
        )
        tb_layout = QHBoxLayout(self._toast_banner)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        self._toast_label = QLabel("")
        self._toast_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        tb_layout.addWidget(self._toast_label)
        layout.addWidget(self._toast_banner)

        # ── 6. Action Buttons Footer ───────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(SPACE_MD)

        relabel_btn = QPushButton("  Re-run Auto-Labeling for this Trial")
        ev_icon = Path(__file__).resolve().parent.parent.parent.parent / "resources" / "icons" / "auto_event.svg"
        if ev_icon.is_file():
            relabel_btn.setIcon(QIcon(str(ev_icon)))
        relabel_btn.setCursor(Qt.PointingHandCursor)
        relabel_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        if self._is_dark:
            relabel_btn.setStyleSheet(
                "QPushButton { background: #1E293B; color: #F8FAFC; border: 1px solid #475569; "
                "border-radius: 4px; padding: 8px 16px; }"
                "QPushButton:hover { background: #334155; }"
            )
        else:
            relabel_btn.setStyleSheet(
                "QPushButton { background: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; "
                "border-radius: 4px; padding: 8px 16px; }"
                "QPushButton:hover { background: #F1F5F9; }"
            )
        relabel_btn.clicked.connect(self._on_rerun_clicked)
        btn_row.addWidget(relabel_btn)

        btn_row.addStretch()

        # Discard Changes Button
        self._discard_btn = QPushButton("Discard Changes")
        self._discard_btn.setCursor(Qt.PointingHandCursor)
        self._discard_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL))
        self._discard_btn.setEnabled(False)
        self._discard_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #94A3B8; border: 1px solid #475569; "
            "border-radius: 4px; padding: 8px 16px; }"
            "QPushButton:hover:enabled { background: #334155; color: #F8FAFC; }"
        )
        self._discard_btn.clicked.connect(self._on_discard_clicked)
        btn_row.addWidget(self._discard_btn)

        # Fetch from QTM Button
        self._fetch_qtm_btn = QPushButton("  Fetch from QTM")
        self._fetch_qtm_btn.setCursor(Qt.PointingHandCursor)
        self._fetch_qtm_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        self._fetch_qtm_btn.setToolTip("Fetch live event markers currently labeled on QTM timeline for this trial")
        if self._is_dark:
            self._fetch_qtm_btn.setStyleSheet(
                "QPushButton { background: #1E293B; color: #2DD4BF; border: 1.5px solid #14B8A6; "
                "border-radius: 4px; padding: 8px 18px; font-weight: 700; }"
                "QPushButton:hover { background: #134E4A; }"
            )
        else:
            self._fetch_qtm_btn.setStyleSheet(
                "QPushButton { background: #FFFFFF; color: #0F766E; border: 1.5px solid #0F766E; "
                "border-radius: 4px; padding: 8px 18px; font-weight: 700; }"
                "QPushButton:hover { background: #F0FDFA; }"
            )
        self._fetch_qtm_btn.clicked.connect(self._on_fetch_from_qtm)
        btn_row.addWidget(self._fetch_qtm_btn)

        # Save & Sync to QTM Button
        self._save_qtm_btn = QPushButton("  Save && Update QTM")
        self._save_qtm_btn.setCursor(Qt.PointingHandCursor)
        self._save_qtm_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        self._save_qtm_btn.setStyleSheet(
            "QPushButton { background: #0D9488; color: #FFFFFF; border: none; "
            "border-radius: 4px; padding: 8px 22px; font-weight: 700; }"
            "QPushButton:hover { background: #14B8A6; }"
        )
        self._save_qtm_btn.clicked.connect(self._on_save_and_update_qtm)
        btn_row.addWidget(self._save_qtm_btn)

        # Close Button
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        if self._is_dark:
            close_btn.setStyleSheet(
                "QPushButton { background: #334155; color: #F8FAFC; border: none; "
                "border-radius: 4px; padding: 8px 20px; }"
                "QPushButton:hover { background: #475569; }"
            )
        else:
            close_btn.setStyleSheet(
                "QPushButton { background: #E2E8F0; color: #0F172A; border: none; "
                "border-radius: 4px; padding: 8px 20px; }"
                "QPushButton:hover { background: #CBD5E1; }"
            )
        close_btn.clicked.connect(self._on_close_clicked)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    # ═══════════════════════════════════════════════════════════════════
    #  UI Refresh & Table Synchronization
    # ═══════════════════════════════════════════════════════════════════

    def _on_spin_frame_changed(self, frame_val: int) -> None:
        """Update calculated time as frame number changes."""
        time_s = frame_to_time(frame_val, self.frame_rate)
        self._calc_time_lbl.setText(f"t = {time_s:.3f} s")

    def _nudge_frame(self, delta: int) -> None:
        """Nudge current frame spinbox value by delta."""
        new_val = max(0, min(self._spin_frame.maximum(), self._spin_frame.value() + delta))
        self._spin_frame.setValue(new_val)

    def _on_combo_index_changed(self, index: int) -> None:
        """Keep segmented selector buttons in sync if QComboBox changes."""
        code = self._combo_event.itemData(index)
        if code and code != self._selected_event_code:
            self._set_active_event_type(code, update_combo=False)

    def _set_active_event_type(self, code: str, update_combo: bool = True) -> None:
        """Select an active gait event type and update button styles."""
        self._selected_event_code = code
        self._update_event_buttons_style()
        if update_combo:
            self._combo_event.blockSignals(True)
            for idx in range(self._combo_event.count()):
                if self._combo_event.itemData(idx) == code:
                    self._combo_event.setCurrentIndex(idx)
                    break
            self._combo_event.blockSignals(False)

    def _update_event_buttons_style(self) -> None:
        """Apply active/inactive styling to the 4 segmented event buttons."""
        styles_map = {
            "RSTRIKE": {
                "active_bg_light": "#CCFBF1", "active_fg_light": "#0F766E", "active_bdr_light": "#0D9488",
                "active_bg_dark": "#134E4A", "active_fg_dark": "#5EEAD4", "active_bdr_dark": "#2DD4BF",
            },
            "ROFF": {
                "active_bg_light": "#FEF3C7", "active_fg_light": "#92400E", "active_bdr_light": "#D97706",
                "active_bg_dark": "#451A03", "active_fg_dark": "#FDE68A", "active_bdr_dark": "#F59E0B",
            },
            "LSTRIKE": {
                "active_bg_light": "#DBEAFE", "active_fg_light": "#1D4ED8", "active_bdr_light": "#2563EB",
                "active_bg_dark": "#1E3A8A", "active_fg_dark": "#93C5FD", "active_bdr_dark": "#3B82F6",
            },
            "LOFF": {
                "active_bg_light": "#EDE9FE", "active_fg_light": "#6D28D9", "active_bdr_light": "#7C3AED",
                "active_bg_dark": "#4C1D95", "active_fg_dark": "#DDD6FE", "active_bdr_dark": "#8B5CF6",
            },
        }

        for code, btn in self._event_buttons.items():
            conf = styles_map.get(code, styles_map["RSTRIKE"])
            if code == self._selected_event_code:
                if self._is_dark:
                    btn.setStyleSheet(
                        f"QPushButton {{ background-color: {conf['active_bg_dark']}; color: {conf['active_fg_dark']}; "
                        f"border: 2px solid {conf['active_bdr_dark']}; border-radius: 6px; padding: 4px 10px; font-weight: 700; font-size: 11px; }}"
                    )
                else:
                    btn.setStyleSheet(
                        f"QPushButton {{ background-color: {conf['active_bg_light']}; color: {conf['active_fg_light']}; "
                        f"border: 2px solid {conf['active_bdr_light']}; border-radius: 6px; padding: 4px 10px; font-weight: 700; font-size: 11px; }}"
                    )
            else:
                if self._is_dark:
                    btn.setStyleSheet(
                        "QPushButton { background-color: #0F172A; color: #94A3B8; "
                        "border: 1px solid #334155; border-radius: 6px; padding: 5px 10px; font-weight: 600; font-size: 11px; }"
                        "QPushButton:hover { background-color: #1E293B; border-color: #475569; color: #F8FAFC; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton { background-color: #F8FAFC; color: #475569; "
                        "border: 1px solid #CBD5E1; border-radius: 6px; padding: 5px 10px; font-weight: 600; font-size: 11px; }"
                        "QPushButton:hover { background-color: #F1F5F9; border-color: #94A3B8; color: #0F172A; }"
                    )

    def _set_mode_pill_style(self, is_editing: bool) -> None:
        """Update style for the mode status badge."""
        if is_editing:
            bg = "#451A03" if self._is_dark else "#FFFBEB"
            fg = "#FDE68A" if self._is_dark else "#B45309"
            bdr = "#78350F" if self._is_dark else "#FCD34D"
        else:
            bg = "#134E4A" if self._is_dark else "#F0FDF4"
            fg = "#2DD4BF" if self._is_dark else "#166534"
            bdr = "#14B8A6" if self._is_dark else "#BBF7D0"

        self._mode_pill.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border: 1px solid {bdr}; "
            f"border-radius: 11px; padding: 3px 10px; font-size: 10px; font-weight: 700;"
        )

    def _set_update_btn_style(self, enabled: bool) -> None:
        """Update visual styling for the Update button."""
        self._update_btn.setEnabled(enabled)
        if enabled:
            if self._is_dark:
                self._update_btn.setStyleSheet(
                    "QPushButton { background: #1E293B; color: #F8FAFC; border: 1.5px solid #14B8A6; "
                    "border-radius: 4px; padding: 6px 14px; font-weight: 700; }"
                    "QPushButton:hover { background: #134E4A; }"
                )
            else:
                self._update_btn.setStyleSheet(
                    "QPushButton { background: #FFFFFF; color: #0F172A; border: 1.5px solid #0D9488; "
                    "border-radius: 4px; padding: 6px 14px; font-weight: 700; }"
                    "QPushButton:hover { background: #F0FDFA; }"
                )
        else:
            if self._is_dark:
                self._update_btn.setStyleSheet(
                    "QPushButton { background: #1E293B; color: #64748B; border: 1px solid #334155; "
                    "border-radius: 4px; padding: 6px 14px; }"
                )
            else:
                self._update_btn.setStyleSheet(
                    "QPushButton { background: #F1F5F9; color: #94A3B8; border: 1px solid #E2E8F0; "
                    "border-radius: 4px; padding: 6px 14px; }"
                )

    def _set_del_btn_style(self, enabled: bool) -> None:
        """Update visual styling for the Delete button."""
        self._del_selected_btn.setEnabled(enabled)
        if enabled:
            self._del_selected_btn.setStyleSheet(
                "QPushButton { background: transparent; color: #EF4444; border: 1.5px solid #EF4444; "
                "border-radius: 4px; padding: 6px 12px; font-weight: 700; }"
                "QPushButton:hover { background: #EF4444; color: #FFFFFF; }"
            )
        else:
            bdr = "#334155" if self._is_dark else "#E2E8F0"
            fg = "#475569" if self._is_dark else "#CBD5E1"
            self._del_selected_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {fg}; border: 1px solid {bdr}; "
                f"border-radius: 4px; padding: 6px 12px; }}"
            )

    def _on_clear_selection_clicked(self) -> None:
        """Deselect currently highlighted row in the timeline table."""
        self._table.clearSelection()

    def _refresh_all_views(self) -> None:
        """Refresh table rows, metric cards, pairing status, and sync badge."""
        self._populate_table()
        self._update_metric_cards()
        self._update_sync_badge()

    def _populate_table(self) -> None:
        """Populate table widget with sorted events."""
        self._table.blockSignals(True)
        self._table.setRowCount(len(self._events))

        for row_idx, ev in enumerate(self._events):
            frame = int(ev.get("frame", 0))
            # Stored frames already use the absolute QTM timeline coordinates.
            display_frame = frame
            time_s = frame_to_time(frame, self.frame_rate)
            label = str(ev.get("label", "")).upper()

            meta_info = self.EVENT_META.get(label, ("#F3F4F6", "#374151", label, "Unknown"))
            bg_c, fg_c, desc, limb = meta_info
            if self._is_dark:
                bg_c = "#1E293B"
                fg_c = "#F8FAFC"

            # 1. Index
            item_idx = QTableWidgetItem(f"{row_idx + 1}")
            item_idx.setTextAlignment(Qt.AlignCenter)
            item_idx.setFlags(item_idx.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row_idx, 0, item_idx)

            # 2. Absolute QTM frame
            item_frame = QTableWidgetItem(f"{display_frame}")
            item_frame.setFont(QFont(FONT_FAMILY_MONO, 11))
            item_frame.setTextAlignment(Qt.AlignCenter)
            item_frame.setFlags(item_frame.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row_idx, 1, item_frame)

            # 3. Time (s)
            item_time = QTableWidgetItem(f"{time_s:.3f} s")
            item_time.setFont(QFont(FONT_FAMILY_MONO, 11))
            item_time.setTextAlignment(Qt.AlignCenter)
            item_time.setFlags(item_time.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row_idx, 2, item_time)

            # 4. Label Badge
            label_cell = QTableWidgetItem(f" {label} ")
            label_cell.setFont(QFont(FONT_FAMILY_MONO, 10, QFont.Bold))
            label_cell.setTextAlignment(Qt.AlignCenter)
            label_cell.setBackground(QColor(bg_c))
            label_cell.setForeground(QColor(fg_c))
            label_cell.setFlags(label_cell.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row_idx, 3, label_cell)

            # 5. Description
            item_desc = QTableWidgetItem(f"{desc} ({limb})")
            item_desc.setFlags(item_desc.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row_idx, 4, item_desc)

            # Explicit row height so every row has guaranteed vertical breathing room
            self._table.setRowHeight(row_idx, 38)

            # 6. Action button (Remove event) wrapped in a centered container to prevent overlap
            del_wrap = QWidget()
            del_wrap.setStyleSheet("background: transparent;")
            del_layout = QHBoxLayout(del_wrap)
            del_layout.setContentsMargins(4, 2, 4, 2)
            del_layout.setAlignment(Qt.AlignCenter)

            del_btn = QPushButton("✕ Remove")
            del_btn.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedHeight(26)
            del_btn.setMinimumWidth(82)
            if self._is_dark:
                del_btn.setStyleSheet(
                    "QPushButton { background: transparent; color: #F87171; border: 1.5px solid #EF4444; border-radius: 4px; padding: 1px 8px; margin: 1px 2px; }"
                    "QPushButton:hover { background: rgba(239, 68, 68, 0.2); color: #FFFFFF; border-color: #F87171; }"
                    "QPushButton:pressed { background: rgba(239, 68, 68, 0.35); border-color: #EF4444; }"
                )
            else:
                del_btn.setStyleSheet(
                    "QPushButton { background: transparent; color: #DC2626; border: 1.5px solid #FCA5A5; border-radius: 4px; padding: 1px 8px; margin: 1px 2px; }"
                    "QPushButton:hover { background: #FEF2F2; color: #991B1B; border-color: #EF4444; }"
                    "QPushButton:pressed { background: #FEE2E2; border-color: #DC2626; }"
                )
            del_btn.clicked.connect(lambda _, r=row_idx: self._on_delete_row_event(r))
            del_layout.addWidget(del_btn)
            self._table.setCellWidget(row_idx, 5, del_wrap)

        self._table.blockSignals(False)

    def _update_metric_cards(self) -> None:
        """Compute counts by label and update cards + stride pairing pill."""
        r_hs, r_to, l_hs, l_to = 0, 0, 0, 0
        for ev in self._events:
            lbl = ev.get("label", "").upper()
            if lbl in ("RSTRIKE", "AUTO_RHS"):
                r_hs += 1
            elif lbl in ("ROFF", "AUTO_ROF"):
                r_to += 1
            elif lbl in ("LSTRIKE", "AUTO_LHS"):
                l_hs += 1
            elif lbl in ("LOFF", "AUTO_LOF"):
                l_to += 1

        self._metric_labels["r_hs"].setText(str(r_hs))
        self._metric_labels["r_to"].setText(str(r_to))
        self._metric_labels["l_hs"].setText(str(l_hs))
        self._metric_labels["l_to"].setText(str(l_to))

        pairing_valid = check_event_pairing(self._events)
        total_events = len(self._events)

        if pairing_valid and total_events > 0:
            status_text = "● Stride Pairing: PASS"
            status_bg = "#134E4A" if self._is_dark else "#F0FDF4"
            status_fg = "#2DD4BF" if self._is_dark else "#166534"
            status_border = "#14B8A6" if self._is_dark else "#BBF7D0"
        else:
            status_text = "● Stride Pairing: REVIEW"
            status_bg = "#451A03" if self._is_dark else "#FFFBEB"
            status_fg = "#FDE68A" if self._is_dark else "#B45309"
            status_border = "#78350F" if self._is_dark else "#FDE68A"

        self._status_pill.setText(status_text)
        self._status_pill.setStyleSheet(
            f"background-color: {status_bg}; color: {status_fg}; "
            f"border-radius: 12px; padding: 4px 12px; border: 1px solid {status_border};"
        )

    def _update_sync_badge(self) -> None:
        """Update unsaved status and enable/disable save/discard buttons."""
        self._discard_btn.setEnabled(self._has_unsaved_changes)

        if self._has_unsaved_changes:
            self._sync_badge.setText("● Unsaved Changes")
            s_bg = "#451A03" if self._is_dark else "#FEF3C7"
            s_fg = "#FDE68A" if self._is_dark else "#92400E"
            s_bdr = "#78350F" if self._is_dark else "#FCD34D"
        else:
            self._sync_badge.setText("● Synced")
            s_bg = "#134E4A" if self._is_dark else "#F0FDF4"
            s_fg = "#2DD4BF" if self._is_dark else "#166534"
            s_bdr = "#14B8A6" if self._is_dark else "#BBF7D0"

        self._sync_badge.setStyleSheet(
            f"background-color: {s_bg}; color: {s_fg}; "
            f"border-radius: 12px; padding: 4px 12px; border: 1px solid {s_bdr};"
        )

    def _show_toast(self, message: str, status_type: str = "success") -> None:
        """Display an inline status banner with message."""
        if status_type == "success":
            bg = "#064E3B" if self._is_dark else "#ECFDF5"
            fg = "#6EE7B7" if self._is_dark else "#065F46"
            bdr = "#059669" if self._is_dark else "#A7F3D0"
        elif status_type == "warning":
            bg = "#451A03" if self._is_dark else "#FFFBEB"
            fg = "#FDE68A" if self._is_dark else "#92400E"
            bdr = "#D97706" if self._is_dark else "#FDE68A"
        else:  # error
            bg = "#450A0A" if self._is_dark else "#FEF2F2"
            fg = "#FCA5A5" if self._is_dark else "#991B1B"
            bdr = "#DC2626" if self._is_dark else "#FECACA"

        self._toast_banner.setStyleSheet(
            f"background-color: {bg}; border: 1px solid {bdr}; border-radius: {RADIUS_SM}px; padding: 6px 12px;"
        )
        self._toast_label.setStyleSheet(f"color: {fg}; border: none;")
        self._toast_label.setText(message)
        self._toast_banner.setVisible(True)

    # ═══════════════════════════════════════════════════════════════════
    #  Manual Editing Actions
    # ═══════════════════════════════════════════════════════════════════

    def _on_table_selection_changed(self) -> None:
        """When a row is selected in the table, populate controls."""
        selected_rows = self._table.selectionModel().selectedRows()
        if selected_rows:
            row_idx = selected_rows[0].row()
            if 0 <= row_idx < len(self._events):
                ev = self._events[row_idx]
                frame = ev["frame"]
                display_frame = frame
                label = ev["label"]

                canon_label = label
                if canon_label == "AUTO_RHS":
                    canon_label = "RSTRIKE"
                elif canon_label == "AUTO_ROF":
                    canon_label = "ROFF"
                elif canon_label == "AUTO_LHS":
                    canon_label = "LSTRIKE"
                elif canon_label == "AUTO_LOF":
                    canon_label = "LOFF"

                self._set_active_event_type(canon_label)

                self._spin_frame.blockSignals(True)
                self._spin_frame.setValue(frame)
                self._on_spin_frame_changed(frame)
                self._spin_frame.blockSignals(False)

                self._mode_pill.setText(f"● Editing Row #{row_idx + 1}: {canon_label} @ Frame {frame}")
                self._set_mode_pill_style(is_editing=True)
                self._clear_btn.setVisible(True)
                self._set_update_btn_style(enabled=True)
                self._set_del_btn_style(enabled=True)
                return

        self._mode_pill.setText("● Ready: Add New Event")
        self._set_mode_pill_style(is_editing=False)
        self._clear_btn.setVisible(False)
        self._set_update_btn_style(enabled=False)
        self._set_del_btn_style(enabled=False)

    def _on_add_event_clicked(self) -> None:
        """Add a new gait event manually."""
        frame = self._spin_frame.value()
        label = self._selected_event_code or self._combo_event.currentData() or "RSTRIKE"
        time_s = frame_to_time(frame, self.frame_rate)
        rel_f = frame_to_index(frame, self._qtm_base)
        side = "R" if "R" in label else ("L" if "L" in label else "")
        etype = "STRIKE" if ("STRIKE" in label or "HS" in label) else ("OFF" if ("OFF" in label or "OF" in label) else "")

        # Check if identical event already exists
        for ev in self._events:
            if ev["frame"] == frame and ev["label"] == label:
                self._show_toast(f"Event {label} at frame {frame} already exists.", "warning")
                return

        self._events.append({
            "frame": frame,
            "label": label,
            "time": time_s,
            "relative_frame": int(rel_f),
            "side": side,
            "type": etype,
        })
        self._events.sort(key=lambda x: x["frame"])
        self._has_unsaved_changes = True

        self._refresh_all_views()
        self._show_toast(f"Added {label} at frame {frame} (t = {time_s:.3f} s).", "success")

        # Scroll to newly added row
        for i, ev in enumerate(self._events):
            if ev["frame"] == frame and ev["label"] == label:
                self._table.selectRow(i)
                self._table.scrollToItem(self._table.item(i, 0))
                break

    def _on_update_selected_clicked(self) -> None:
        """Update the selected event in-place with current inputs."""
        selected_rows = self._table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row_idx = selected_rows[0].row()
        if not (0 <= row_idx < len(self._events)):
            return

        frame = self._spin_frame.value()
        label = self._selected_event_code or self._combo_event.currentData() or "RSTRIKE"
        time_s = frame_to_time(frame, self.frame_rate)
        rel_f = frame_to_index(frame, self._qtm_base)
        side = "R" if "R" in label else ("L" if "L" in label else "")
        etype = "STRIKE" if ("STRIKE" in label or "HS" in label) else ("OFF" if ("OFF" in label or "OF" in label) else "")

        self._events[row_idx] = {
            "frame": frame,
            "label": label,
            "time": time_s,
            "relative_frame": int(rel_f),
            "side": side,
            "type": etype,
        }
        self._events.sort(key=lambda x: x["frame"])
        self._has_unsaved_changes = True

        self._refresh_all_views()
        self._show_toast(f"Updated event to {label} at frame {frame}.", "success")

        # Re-select row
        for i, ev in enumerate(self._events):
            if ev["frame"] == frame and ev["label"] == label:
                self._table.selectRow(i)
                break

    def _on_delete_row_event(self, row_idx: int) -> None:
        """Delete an event by row index from the action button."""
        if 0 <= row_idx < len(self._events):
            ev = self._events.pop(row_idx)
            self._has_unsaved_changes = True
            self._refresh_all_views()
            self._show_toast(f"Removed {ev.get('label')} at frame {int(ev.get('frame', 0))}.", "warning")

    def _on_delete_selected_event(self) -> None:
        """Delete currently selected table row."""
        selected_rows = self._table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row_idx = selected_rows[0].row()
        self._on_delete_row_event(row_idx)

    def _on_discard_clicked(self) -> None:
        """Revert in-memory events to originally loaded state."""
        self._events = [dict(e) for e in self._original_events]
        self._has_unsaved_changes = False
        self._refresh_all_views()
        self._show_toast("Reverted all manual changes to original trial events.", "warning")

    # ═══════════════════════════════════════════════════════════════════
    #  Saving & Direct QTM Synchronization
    # ═══════════════════════════════════════════════════════════════════

    def _on_fetch_from_qtm(self) -> None:
        """Fetch live events from QTM timeline and populate the dialog."""
        ok, msg, active_trial, clean_events, meta = fetch_events_from_qtm(
            trial_filename=self.trial_filename,
            default_frame_rate=self.frame_rate,
            session_dir=self.session_dir,
        )
        if not ok:
            QMessageBox.warning(self, "QTM Synchronization", f"{msg}\n\nPlease ensure QTM is running with '{self.trial_filename}' open.")
            return

        if not clean_events:
            QMessageBox.information(self, "QTM Synchronization", f"QTM has '{active_trial}' open, but no events were found on its timeline.")
            return

        self.events_info["meta"] = dict(meta)
        self.frame_rate = float(meta.get("frame_rate") or self.frame_rate)
        self._offset = int(meta.get("initial_frame_offset", self._offset))
        self._qtm_base = recording_start_frame(meta)
        self._spin_frame.setRange(self._qtm_base, self._qtm_base + int(meta.get("total_frames") or 1000000) - 1)
        self._events = [dict(e) for e in clean_events]
        self._original_events = [dict(e) for e in self._events]
        self._has_unsaved_changes = True
        self._discard_btn.setEnabled(True)
        self._refresh_all_views()
        self._show_toast(f"✓ Fetched {len(clean_events)} event(s) from QTM timeline for {self.trial_filename}!", "success")

    def _on_save_and_update_qtm(self) -> None:
        """Save events to session results JSON and directly update QTM via gRPC."""
        meta = dict(self.events_info.get("meta", {}))
        meta["frame_rate"] = self.frame_rate
        meta["initial_frame_offset"] = self._offset

        # 1. Save to session results JSON
        updated_dict = save_trial_events(
            session_dir=self.session_dir,
            trial_filename=self.trial_filename,
            events_list=self._events,
            meta=meta,
        )

        # 2. Directly send to QTM timeline over gRPC
        qtm_success, qtm_msg = send_events_to_qtm(
            events_list=self._events,
            frame_rate=self.frame_rate,
            offset=self._offset,
            trial_filename=self.trial_filename,
        )

        self._has_unsaved_changes = False
        self._original_events = [dict(e) for e in self._events]
        self._update_sync_badge()

        # 3. Notify parent workstation page so row badge & counters update immediately
        self.events_updated.emit(self.trial_filename, updated_dict)

        # 4. Show feedback
        if qtm_success:
            self._show_toast(
                f"✓ Successfully synchronized {len(self._events)} events with QTM timeline & saved to session.",
                "success",
            )
        else:
            self._show_toast(
                f"✓ Saved {len(self._events)} events to session file. Note: {qtm_msg}",
                "warning",
            )

    def _on_rerun_clicked(self) -> None:
        self.rerun_requested.emit(self.trial_filename)
        self.accept()

    def _on_close_clicked(self) -> None:
        if self._has_unsaved_changes:
            res = QMessageBox.question(
                self,
                "Unsaved Event Modifications",
                "You have modified gait events without updating QTM.\n\nWould you like to save and update QTM now?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if res == QMessageBox.Save:
                self._on_save_and_update_qtm()
                self.accept()
                return
            elif res == QMessageBox.Cancel:
                return

        self.accept()
