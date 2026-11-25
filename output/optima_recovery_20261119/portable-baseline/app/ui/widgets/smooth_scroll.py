# -*- coding: utf-8 -*-
"""
High-Performance Kinetic Smooth Scrolling Engine for PySide6 / Qt.

Provides continuous, 60fps physics-interpolated smooth scrolling for all QScrollArea
containers in the application, and prevents child widgets (like closed dropdowns)
from swallowing mouse wheel events and halting scrolling.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLineEdit,
    QScrollBar,
    QScrollArea,
)

logger = logging.getLogger(__name__)

# Global singleton filter so it's installed on QApplication only once
_GLOBAL_WHEEL_FILTER: Optional[_GlobalWheelEventFilter] = None


class _GlobalWheelEventFilter(QObject):
    """
    Application-level event filter that prevents closed QComboBoxes and SpinBoxes
    from capturing mouse wheel events and blocking page scroll.

    If a combobox popup is closed, casual mouse wheel scrolling over it is
    forwarded to the enclosing QScrollArea rather than altering the selection.
    """

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Wheel:
            # Check for dropdowns
            if isinstance(watched, QComboBox):
                # Only allow combobox to handle wheel if its popup view is currently open
                if not watched.view() or not watched.view().isVisible():
                    scroll_area = self._find_parent_scroll_area(watched)
                    if scroll_area:
                        QApplication.sendEvent(scroll_area.viewport(), event)
                    return True  # Consume event on closed combobox

            # Check for spin boxes and line edits
            elif isinstance(watched, (QAbstractSpinBox, QLineEdit)):
                scroll_area = self._find_parent_scroll_area(watched)
                if scroll_area:
                    QApplication.sendEvent(scroll_area.viewport(), event)
                    return True

        return super().eventFilter(watched, event)

    @staticmethod
    def _find_parent_scroll_area(widget: QObject) -> Optional[QScrollArea]:
        parent = widget.parentWidget() if hasattr(widget, "parentWidget") else None
        while parent:
            if isinstance(parent, QScrollArea):
                return parent
            parent = parent.parentWidget()
        return None


def _ensure_global_wheel_filter() -> None:
    """Ensure the global wheel filter is installed on the application instance."""
    global _GLOBAL_WHEEL_FILTER
    app = QApplication.instance()
    if app and _GLOBAL_WHEEL_FILTER is None:
        _GLOBAL_WHEEL_FILTER = _GlobalWheelEventFilter(app)
        app.installEventFilter(_GLOBAL_WHEEL_FILTER)


class SmoothScrollFilter(QObject):
    """
    60 FPS physics-interpolated smooth scrolling filter for QScrollArea.

    Replaces abrupt QPropertyAnimation restarts with continuous exponential-decay
    interpolation (friction spring), providing natural momentum acceleration
    when spinning the mouse wheel and seamless 1:1 response on precision touchpads.
    """

    def __init__(
        self,
        scroll_area: QScrollArea,
        step_size: int = 110,
        friction: float = 0.22,
        duration_ms: int = 220,  # Kept for backward compatibility
        parent: QObject | None = None,
        **kwargs,
    ):
        super().__init__(parent or scroll_area)
        self._scroll_area = scroll_area
        self._step_size = step_size
        self._friction = friction

        vbar = scroll_area.verticalScrollBar()
        self._vbar = vbar
        self._target_value = float(vbar.value())
        self._current_value = float(vbar.value())
        self._last_event_time = 0.0

        # Continuous 60fps interpolation timer
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 FPS
        self._timer.timeout.connect(self._on_tick)

        # Track manual scrollbar thumb drags so target doesn't desync
        self._vbar.valueChanged.connect(self._on_vbar_manual)

        # Install on scroll area's viewport
        viewport = scroll_area.viewport()
        if viewport:
            viewport.installEventFilter(self)

        # Also register global wheel filter for combobox forwarding
        _ensure_global_wheel_filter()

    def _on_vbar_manual(self, val: int) -> None:
        """Keep internal state in sync when user drags scrollbar thumb manually."""
        if not self._timer.isActive():
            self._current_value = float(val)
            self._target_value = float(val)

    def _on_tick(self) -> None:
        """Advance smooth scroll position towards target on each 60fps frame."""
        diff = self._target_value - self._current_value
        if abs(diff) < 0.6:
            self._current_value = self._target_value
            self._vbar.setValue(int(round(self._target_value)))
            self._timer.stop()
            return

        self._current_value += diff * self._friction
        self._vbar.setValue(int(round(self._current_value)))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Wheel:
            vbar = self._vbar
            if vbar.maximum() <= 0:
                return False

            # Ignore wheel events if Ctrl is pressed (e.g. zooming)
            if event.modifiers() & Qt.ControlModifier:
                return False

            delta_y = event.angleDelta().y()
            if delta_y == 0:
                # Horizontal scroll fallback
                delta_x = event.angleDelta().x()
                if delta_x != 0:
                    hbar = self._scroll_area.horizontalScrollBar()
                    if hbar and hbar.isVisible() and hbar.maximum() > 0:
                        hbar.setValue(hbar.value() - int(delta_x))
                        return True
                return False

            now = time.time()
            dt = now - self._last_event_time
            self._last_event_time = now

            if abs(delta_y) >= 120:
                # Standard mouse notch (deliver ~1 notch per 120 delta)
                steps = delta_y / 120.0
                # Kinetic momentum: if spinning quickly, amplify smoothly
                momentum = 1.0
                if dt < 0.08:
                    momentum = 1.35
                elif dt < 0.15:
                    momentum = 1.15
                offset = -steps * self._step_size * momentum
            else:
                # High-precision trackpad or free-spinning smooth wheel
                offset = -float(delta_y) * 1.5

            if not self._timer.isActive():
                self._current_value = float(vbar.value())
                self._target_value = float(vbar.value())

            new_target = max(0.0, min(self._target_value + offset, float(vbar.maximum())))
            self._target_value = new_target

            if not self._timer.isActive():
                self._timer.start()

            return True

        return super().eventFilter(watched, event)

    def stop(self) -> None:
        """Immediately stop any ongoing smooth scroll animation."""
        if self._timer.isActive():
            self._timer.stop()
        self._current_value = float(self._vbar.value())
        self._target_value = float(self._vbar.value())

    def reset(self, val: int = 0) -> None:
        """Immediately stop animation and snap to specified scroll value."""
        if self._timer.isActive():
            self._timer.stop()
        self._current_value = float(val)
        self._target_value = float(val)
        self._vbar.setValue(val)


def apply_smooth_scroll(
    scroll_area: QScrollArea,
    duration_ms: int = 220,
    step_size: int = 110,
    **kwargs,
) -> SmoothScrollFilter:
    """Convenience helper to attach kinetic smooth scrolling to any QScrollArea."""
    return SmoothScrollFilter(scroll_area, step_size=step_size, duration_ms=duration_ms, **kwargs)
