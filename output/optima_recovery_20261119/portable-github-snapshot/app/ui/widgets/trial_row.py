# -*- coding: utf-8 -*-
"""
Modern Selectable Trial Row Widget for Shriners Gait Analysis.

Provides a clean, scientific row representation for gait trials:
- ID badge (e.g. L1, R2, Dynamic 1)
- Trial title & frame count metadata
- Status indicator pill (READY, SELECTED, PROCESSING, PROCESSED)
- Selection arrow
- Interactive hover and selected states matching app design tokens.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPen, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.components import create_tinted_icon

from app.ui.theme.design_tokens import (
    FONT_FAMILY,
    FONT_FAMILY_MONO,
    FONT_SIZE_BODY,
    FONT_SIZE_CAPTION,
    FONT_SIZE_SMALL,
    FONT_WEIGHT_MEDIUM,
    FONT_WEIGHT_SEMIBOLD,
    RADIUS_MD,
    RADIUS_SM,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
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


class TrialRowWidget(QFrame):
    """
    Minimal modern selectable trial row.
    Avoids raw checkboxes, offering a clinical workstation list item with:
    - Forceplate strike badge (R / L / ! / —)
    - Trial filename & strike chip (e.g. Right, Left, Bad FP Strike, Crouch)
    - Live frame count, frequency, duration metadata
    - Event count button & processing status indicator
    """

    toggled = Signal(bool)
    clicked = Signal(str)  # trial_id or filename
    view_events_clicked = Signal(str)  # filename
    auto_label_clicked = Signal(str)   # filename
    push_to_qtm_clicked = Signal(str)  # filename
    pull_from_qtm_clicked = Signal(str)  # filename

    def __init__(
        self,
        trial_id: str = "",
        name: str = "",
        metadata: str = "",
        status: str = "READY",
        selected: bool = False,
        strike: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.trial_id = trial_id
        self.filename = name
        self._strike = strike
        self._selected = selected
        self._status = status
        self._hovered = False
        self._events_info: dict | None = None
        self._appearance_key: tuple | None = None  # dirty-check fingerprint

        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(62)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_MD, SPACE_XS, SPACE_MD, SPACE_XS)
        layout.setSpacing(14)

        # 1. Forceplate Strike Badge (R / L / ! / —)
        self._badge = QLabel("")
        self._badge.setFixedSize(38, 38)
        self._badge.setAlignment(Qt.AlignCenter)
        self._badge.setFont(QFont(FONT_FAMILY_MONO, 13, QFont.Bold))
        layout.addWidget(self._badge, alignment=Qt.AlignVCenter)

        # 2. Name + Strike Chip + Metadata
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignVCenter)

        # Title row: Filename + Strike Tag Chip
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)
        title_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._name_label = QLabel(self.filename)
        self._name_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, FONT_WEIGHT_SEMIBOLD))
        title_layout.addWidget(self._name_label)

        self._strike_chip = QLabel("")
        self._strike_chip.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self._strike_chip.setFixedHeight(20)
        self._strike_chip.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(self._strike_chip)

        info_layout.addLayout(title_layout)

        self._meta_label = QLabel(metadata)
        self._meta_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL))
        info_layout.addWidget(self._meta_label)
        layout.addLayout(info_layout, 1)

        # 3. Events Badge Button
        self._events_btn = QPushButton(" Auto-Label")
        self._events_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_CAPTION, QFont.Bold))
        self._events_btn.setCursor(Qt.PointingHandCursor)
        self._events_btn.setMinimumWidth(106)
        self._events_btn.setFixedHeight(26)
        self._events_btn.setIcon(create_tinted_icon("auto_event.svg", "#606060", 13))
        self._events_btn.setIconSize(QSize(13, 13))
        self._events_btn.clicked.connect(self._on_events_btn_clicked)
        self._events_btn.setContextMenuPolicy(Qt.CustomContextMenu)
        self._events_btn.customContextMenuRequested.connect(self._on_events_context_menu)
        layout.addWidget(self._events_btn, alignment=Qt.AlignVCenter)

        # 4. Status Pill
        self._status_pill = QLabel(self._status)
        self._status_pill.setAlignment(Qt.AlignCenter)
        self._status_pill.setFixedWidth(118)
        self._status_pill.setFixedHeight(26)
        self._status_pill.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL, QFont.Bold))
        layout.addWidget(self._status_pill, alignment=Qt.AlignVCenter)

        # 5. Trailing selection indicator arrow
        self._arrow = QLabel("→")
        self._arrow.setFont(QFont(FONT_FAMILY, FONT_SIZE_BODY, QFont.Bold))
        self._arrow.setFixedWidth(20)
        self._arrow.setFixedHeight(26)
        self._arrow.setAlignment(Qt.AlignCenter)
        self._arrow.setStyleSheet("color: #9CA3AF; background: transparent;")
        layout.addWidget(self._arrow, alignment=Qt.AlignVCenter)

        self._is_dark = False
        self._resolve_strike_display()
        self._update_appearance()

    @property
    def strike(self) -> str:
        return self._strike

    def set_strike(self, strike: str) -> None:
        """Update forceplate strike comment."""
        self._strike = strike
        self._resolve_strike_display()
        self._update_appearance()

    def _resolve_strike_display(self) -> None:
        """Resolve strike text, badge character, and tooltip."""
        s = self._strike.strip().lower()
        if not s and self.trial_id:
            # Fallback if strike is not provided but trial_id is
            tid = self.trial_id.strip()
            if tid.upper().startswith("R"):
                s = "right"
            elif tid.upper().startswith("L"):
                s = "left"

        if "right" in s:
            self._badge_text = "R"
            self._badge_type = "right"
            self._badge.setToolTip("Forceplate Strike: Right Limb")
            if "crouch" in s:
                self._chip_text = "Right Crouch"
            else:
                self._chip_text = "Right"
        elif "left" in s:
            self._badge_text = "L"
            self._badge_type = "left"
            self._badge.setToolTip("Forceplate Strike: Left Limb")
            if "crouch" in s:
                self._chip_text = "Left Crouch"
            else:
                self._chip_text = "Left"
        elif "bad" in s:
            self._badge_text = "!"
            self._badge_type = "bad"
            self._badge.setToolTip("Bad Forceplate Strike")
            self._chip_text = "Bad FP Strike"
        elif "no" in s or "none" in s or "miss" in s:
            self._badge_text = "—"
            self._badge_type = "none"
            self._badge.setToolTip("No Forceplate Strike")
            self._chip_text = "No FP Strike"
        elif self._strike:
            self._badge_text = self._strike[:2].upper()
            self._badge_type = "custom"
            self._badge.setToolTip(f"Strike: {self._strike}")
            self._chip_text = self._strike.title()
        else:
            self._badge_text = self.trial_id if self.trial_id and not (self.trial_id.startswith("L") or self.trial_id.startswith("R")) else "—"
            self._badge_type = "empty"
            self._badge.setToolTip("No strike comment recorded")
            self._chip_text = ""

        self._badge.setText(self._badge_text)
        if self._chip_text:
            self._strike_chip.setText(self._chip_text)
            self._strike_chip.setVisible(True)
        else:
            self._strike_chip.setVisible(False)

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        """Update row styling for light or dark mode."""
        self._is_dark = dark
        self._update_appearance()

    @property
    def is_selected(self) -> bool:
        return self._selected

    @property
    def events_info(self) -> dict | None:
        return self._events_info

    def set_selected(self, selected: bool) -> None:
        if self._selected != selected:
            self._selected = selected
            if selected and self._status == "READY":
                self.set_status("SELECTED")
            elif not selected and self._status == "SELECTED":
                self.set_status("READY")
            self._update_appearance()
            self.toggled.emit(self._selected)

    def set_status(self, status: str) -> None:
        self._status = status.upper()
        self._status_pill.setText(self._status)
        self._update_appearance()

    def set_metadata(self, meta: str) -> None:
        self._meta_label.setText(meta)

    def set_events_info(self, info: dict | None) -> None:
        # Skip full repaint when the relevant parts of info haven't changed.
        old = self._events_info
        if info is old:
            return
        if (info is not None and old is not None
                and info.get("total_events") == old.get("total_events")
                and info.get("summary_text") == old.get("summary_text")
                and info.get("meta", {}).get("event_sync_status") == old.get("meta", {}).get("event_sync_status")
                and info.get("meta", {}).get("event_revision") == old.get("meta", {}).get("event_revision")):
            self._events_info = info  # update reference but skip repaint
            return
        self._events_info = info
        self._update_appearance()

    def _on_events_btn_clicked(self) -> None:
        if self._events_info and (self._events_info.get("total_events", 0) > 0
                                 or self._events_info.get("meta", {}).get("event_revision")):
            self.view_events_clicked.emit(self.filename)
        else:
            self.auto_label_clicked.emit(self.filename)

    def _on_events_context_menu(self, pos) -> None:
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        action_manual = menu.addAction("✎ View / Edit Events (Chronology)...")
        action_pull = menu.addAction("⬇ Sync / Pull Events from QTM Timeline")
        action_push = menu.addAction("⇄ Push Events to QTM Timeline Now")
        action_auto = menu.addAction(create_tinted_icon("auto_event.svg", "#0F766E", 14), "Run Automated Event Labeling")
        action = menu.exec(self._events_btn.mapToGlobal(pos))
        if action == action_manual:
            self.view_events_clicked.emit(self.filename)
        elif action == action_pull:
            self.pull_from_qtm_clicked.emit(self.filename)
        elif action == action_push:
            self.push_to_qtm_clicked.emit(self.filename)
        elif action == action_auto:
            self.auto_label_clicked.emit(self.filename)

    def _update_appearance(self) -> None:
        # Build a cheap fingerprint of all state that drives visual output.
        # If nothing changed, skip the expensive setStyleSheet / setIcon calls.
        ev_tot = self._events_info.get("total_events", 0) if self._events_info else 0
        ev_status = (self._events_info or {}).get("meta", {}).get("event_sync_status", "")
        ev_rev = (self._events_info or {}).get("meta", {}).get("event_revision")
        new_key = (self._is_dark, self._selected, self._hovered, self._status,
                   getattr(self, "_badge_type", "empty"), ev_tot, ev_status, ev_rev)
        if new_key == self._appearance_key:
            return
        self._appearance_key = new_key
        b_type = getattr(self, "_badge_type", "empty")

        if self._is_dark:
            # ── Dark Mode ──
            if self._selected:
                bg_color = "#134E4A"
                border_color = "#14B8A6"
                badge_bg = "#14B8A6"
                badge_color = "#0B1320"
                badge_border = "#14B8A6"
                arrow_color = "#2DD4BF"
            elif self._hovered:
                bg_color = "#1E293B"
                border_color = "#0F766E"
                badge_bg = "#134E4A"
                badge_color = "#2DD4BF"
                badge_border = "#0F766E"
                arrow_color = "#2DD4BF"
            else:
                bg_color = "#0F172A"
                border_color = "#334155"
                badge_bg = "#1E293B"
                badge_color = "#94A3B8"
                badge_border = "#334155"
                arrow_color = "#64748B"

            if b_type == "bad":
                badge_bg = "#451A03"
                badge_color = "#FDE68A"
                badge_border = "#78350F"
                chip_style = "background-color: #451A03; color: #FDE68A; border: 1px solid #78350F; border-radius: 4px; padding: 1px 7px;"
            elif b_type in ("right", "left"):
                chip_style = "background-color: #134E4A; color: #F8FAFC; border: 1px solid #14B8A6; border-radius: 4px; padding: 1px 7px;"
            elif b_type == "none":
                badge_color = "#94A3B8"
                chip_style = "background-color: #0F172A; color: #94A3B8; border: 1px solid #334155; border-radius: 4px; padding: 1px 7px;"
            else:
                chip_style = "background-color: #1E293B; color: #CBD5E1; border: 1px solid #334155; border-radius: 4px; padding: 1px 7px;"

            self._name_label.setStyleSheet("font-weight: 600; color: #F8FAFC; background: transparent; padding: 0px; margin: 0px;")
            self._meta_label.setStyleSheet("color: #94A3B8; background: transparent; padding: 0px; margin: 0px;")
            self._strike_chip.setStyleSheet(chip_style)

            if self._status in ("COMPLETE", "PROCESSED"):
                pill_bg = "#052E16"
                pill_fg = "#4ADE80"
            elif self._status in ("EVENTS LABELED", "EVENTS_LABELED"):
                pill_bg = "#134E4A"
                pill_fg = "#2DD4BF"
            elif self._status in ("PROCESSING", "LABELING"):
                pill_bg = "#083344"
                pill_fg = "#22D3EE"
            elif self._status == "SELECTED":
                pill_bg = "#0F766E"
                pill_fg = "#FFFFFF"
            elif self._status == "ERROR":
                pill_bg = "#450A0A"
                pill_fg = "#F87171"
            else:  # READY
                pill_bg = "#1E293B"
                pill_fg = "#94A3B8"

            if self._events_info and self._events_info.get("total_events", 0) > 0:
                tot = self._events_info.get("total_events", 0)
                summary = self._events_info.get("summary_text", f"{tot} Events")
                self._events_btn.setText(f" {tot} Events")
                self._events_btn.setIcon(create_tinted_icon("auto_event.svg", "#2DD4BF", 13))
                self._events_btn.setToolTip(f"{summary}\nClick to inspect event timeline and pairing.")
                self._events_btn.setStyleSheet(
                    "QPushButton {"
                    "  background-color: #134E4A; color: #2DD4BF; border: 1px solid #14B8A6; "
                    "  border-radius: 13px; padding: 2px 8px; font-weight: 600;"
                    "}"
                    "QPushButton:hover { background-color: #115E59; border-color: #2DD4BF; }"
                )
            else:
                self._events_btn.setText(" Auto-Label")
                self._events_btn.setIcon(create_tinted_icon("auto_event.svg", "#94A3B8", 13))
                self._events_btn.setToolTip("Click to run automated gait event labeling on this trial.")
                self._events_btn.setStyleSheet(
                    "QPushButton {"
                    "  background-color: #0F172A; color: #94A3B8; border: 1px dashed #334155; "
                    "  border-radius: 13px; padding: 2px 8px; font-weight: 500;"
                    "}"
                    "QPushButton:hover { background-color: #1E293B; color: #2DD4BF; border-style: solid; border-color: #14B8A6; }"
                )
        else:
            # ── Light Mode ──
            if self._selected:
                bg_color = "#F0FDFA"
                border_color = COLOR_PRIMARY
                badge_bg = COLOR_PRIMARY
                badge_color = COLOR_SURFACE
                badge_border = COLOR_PRIMARY
                arrow_color = COLOR_PRIMARY
            elif self._hovered:
                bg_color = COLOR_BACKGROUND
                border_color = COLOR_ACCENT
                badge_bg = "#CCFBF1"
                badge_color = COLOR_PRIMARY
                badge_border = COLOR_ACCENT
                arrow_color = COLOR_PRIMARY
            else:
                bg_color = COLOR_SURFACE
                border_color = COLOR_BORDER
                badge_bg = "#F1F5F9"
                badge_color = COLOR_TEXT
                badge_border = COLOR_BORDER
                arrow_color = COLOR_MUTED

            if b_type == "bad":
                badge_bg = "#FEF3C7"
                badge_color = "#92400E"
                badge_border = COLOR_WARNING
                chip_style = f"background-color: #FFFBEB; color: #B45309; border: 1px solid {COLOR_WARNING}; border-radius: 4px; padding: 1px 7px;"
            elif b_type in ("right", "left"):
                chip_style = f"background-color: #F0FDFA; color: {COLOR_PRIMARY}; border: 1px solid #CCFBF1; border-radius: 4px; padding: 1px 7px;"
            elif b_type == "none":
                badge_color = COLOR_MUTED
                chip_style = f"background-color: {COLOR_BACKGROUND}; color: {COLOR_MUTED}; border: 1px solid {COLOR_BORDER}; border-radius: 4px; padding: 1px 7px;"
            else:
                chip_style = f"background-color: {COLOR_BACKGROUND}; color: {COLOR_MUTED}; border: 1px solid {COLOR_BORDER}; border-radius: 4px; padding: 1px 7px;"

            self._name_label.setStyleSheet(f"font-weight: 600; color: {COLOR_TEXT}; background: transparent; padding: 0px; margin: 0px;")
            self._meta_label.setStyleSheet(f"color: {COLOR_MUTED}; background: transparent; padding: 0px; margin: 0px;")
            self._strike_chip.setStyleSheet(chip_style)

            if self._status in ("COMPLETE", "PROCESSED"):
                pill_bg = "#F0FDF4"
                pill_fg = COLOR_NORMAL
            elif self._status in ("EVENTS LABELED", "EVENTS_LABELED"):
                pill_bg = "#F0FDFA"
                pill_fg = COLOR_PRIMARY
            elif self._status in ("PROCESSING", "LABELING"):
                pill_bg = "#ECFEFF"
                pill_fg = COLOR_MOTION
            elif self._status == "SELECTED":
                pill_bg = "#F0FDFA"
                pill_fg = COLOR_PRIMARY
            elif self._status == "ERROR":
                pill_bg = "#FEF2F2"
                pill_fg = COLOR_CRITICAL
            else:  # READY
                pill_bg = COLOR_BACKGROUND
                pill_fg = COLOR_MUTED

            if self._events_info and self._events_info.get("total_events", 0) > 0:
                tot = self._events_info.get("total_events", 0)
                summary = self._events_info.get("summary_text", f"{tot} Events")
                self._events_btn.setText(f" {tot} Events")
                self._events_btn.setIcon(create_tinted_icon("auto_event.svg", COLOR_PRIMARY, 13))
                self._events_btn.setToolTip(f"{summary}\nClick to inspect event timeline and pairing.")
                self._events_btn.setStyleSheet(
                    f"QPushButton {{"
                    f"  background-color: #F0FDFA; color: {COLOR_PRIMARY}; border: 1px solid {COLOR_ACCENT}; "
                    f"  border-radius: 13px; padding: 2px 8px; font-weight: 600;"
                    f"}}"
                    f"QPushButton:hover {{ background-color: #CCFBF1; border-color: {COLOR_PRIMARY}; }}"
                )
            else:
                self._events_btn.setText(" Auto-Label")
                self._events_btn.setIcon(create_tinted_icon("auto_event.svg", COLOR_MUTED, 13))
                self._events_btn.setToolTip("Click to run automated gait event labeling on this trial.")
                self._events_btn.setStyleSheet(
                    f"QPushButton {{"
                    f"  background-color: {COLOR_SURFACE}; color: {COLOR_TEXT}; border: 1px dashed {COLOR_BORDER}; "
                    f"  border-radius: 13px; padding: 2px 8px; font-weight: 500;"
                    f"}}"
                    f"QPushButton:hover {{ background-color: #F0FDFA; color: {COLOR_PRIMARY}; border-style: solid; border-color: {COLOR_PRIMARY}; }}"
                )

        self.setStyleSheet(
            f"TrialRowWidget {{"
            f"  background-color: {bg_color};"
            f"  border: 1px solid {border_color};"
            f"  border-radius: {RADIUS_MD}px;"
            f"}}"
        )
        self._badge.setStyleSheet(
            f"background-color: {badge_bg}; color: {badge_color}; "
            f"border: 1px solid {badge_border}; border-radius: 8px; font-weight: 700;"
        )
        self._arrow.setStyleSheet(f"color: {arrow_color}; background: transparent;")
        self._status_pill.setStyleSheet(
            f"background-color: {pill_bg}; color: {pill_fg}; "
            f"border-radius: 13px; padding: 2px 10px; border: none; font-weight: 500;"
        )
        if self._events_info and self._events_info.get("meta", {}).get("event_revision"):
            meta = self._events_info["meta"]
            tot = self._events_info.get("total_events", 0)
            if tot > 0:
                self._events_btn.setText(f" {tot} Events")
                self._events_btn.setToolTip(f"{tot} gait events labeled for {self.filename}")
            else:
                self._events_btn.setText(" Auto-Label")
                self._events_btn.setToolTip("Click to run automated gait event labeling on this trial.")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.set_selected(not self._selected)
            self.clicked.emit(self.filename)
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self._update_appearance()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._update_appearance()
        super().leaveEvent(event)
