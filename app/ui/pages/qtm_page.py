# -*- coding: utf-8 -*-
"""
QTM Monitor Page — wraps the existing QTM-GRPC integration.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import threading
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot, QObject, QTimer
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.data_models import QTMConnectionInfo
from app.ui.theme.design_tokens import (
    FONT_FAMILY,
    FONT_FAMILY_MONO,
    FONT_SIZE_H2,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
)
from app.ui.widgets.components import MetricCard, NotificationBanner, SectionCard, StatusIndicator
from app.ui.widgets.smooth_scroll import apply_smooth_scroll

logger = logging.getLogger(__name__)


class QTMMonitorPage(QScrollArea):
    """QTM connection monitoring and command interface."""

    connection_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self._smooth_scroll = apply_smooth_scroll(self)

        self._connection_info = QTMConnectionInfo()
        self._grpc_server_thread: Optional[threading.Thread] = None

        container = QWidget()
        self.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        layout.setSpacing(SPACE_LG)

        # Header
        header_row = QHBoxLayout()
        header = QLabel("QTM Monitor")
        header.setObjectName("headerTitle")
        header.setStyleSheet(f"font-size: {FONT_SIZE_H2}px; font-weight: 700;")
        header_row.addWidget(header)
        header_row.addStretch()
        self._status_indicator = StatusIndicator("disconnected", "Disconnected")
        header_row.addWidget(self._status_indicator)
        layout.addLayout(header_row)

        self._notification = NotificationBanner()
        layout.addWidget(self._notification)

        # ── Connection card ────────────────────────────────────────
        conn_card = SectionCard("QTM Connection")
        conn_grid = QHBoxLayout()

        conn_grid.addWidget(QLabel("Server:"))
        self._server_input = QLineEdit("localhost")
        self._server_input.setFixedWidth(150)
        conn_grid.addWidget(self._server_input)

        conn_grid.addWidget(QLabel("Port:"))
        self._port_input = QLineEdit("50051")
        self._port_input.setFixedWidth(80)
        conn_grid.addWidget(self._port_input)

        self._connect_btn = QPushButton("Start Server")
        self._connect_btn.setObjectName("primaryButton")
        self._connect_btn.clicked.connect(self._toggle_connection)
        conn_grid.addWidget(self._connect_btn)

        conn_grid.addStretch()
        conn_card.add_layout(conn_grid)

        self._conn_note = QLabel(
            "Two-way gRPC Bridge: App listens on port 50051 (receives frame metadata from QTM) • "
            "QTM script listens on port 50052 (receives commands & event sync from App)."
        )
        self._conn_note.setWordWrap(True)
        conn_card.add_widget(self._conn_note)
        layout.addWidget(conn_card)

        # ── QTM Integration Scripts (Copy to QTM) ───────────────────
        scripts_card = SectionCard("QTM Startup Scripts")

        info_label = QLabel(
            "Auto-detected script paths for Qualisys Track Manager. "
            "Copy and paste these paths into QTM (Project Options → Scripts) to run the gRPC server and tools:"
        )
        info_label.setWordWrap(True)
        self._scripts_info_lbl = info_label
        scripts_card.add_widget(info_label)

        tools_path_str, demo_path_str = self._resolve_qtm_script_paths()

        # Script 1: startup_tools.py
        r1_layout = QVBoxLayout()
        r1_layout.setSpacing(SPACE_XS)
        r1_lbl = QLabel("Startup Tools Script (startup_tools.py):")
        r1_lbl.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self._tools_lbl = r1_lbl

        r1_box = QHBoxLayout()
        r1_box.setSpacing(SPACE_SM)

        self._tools_path_input = QLineEdit(tools_path_str)
        self._tools_path_input.setReadOnly(True)
        self._tools_path_input.setFont(QFont(FONT_FAMILY_MONO, 10))
        r1_box.addWidget(self._tools_path_input, 1)

        self._copy_tools_btn = QPushButton("Copy Path")
        self._copy_tools_btn.setCursor(Qt.PointingHandCursor)
        self._copy_tools_btn.setFixedHeight(34)
        self._copy_tools_btn.setMinimumWidth(110)
        self._copy_tools_btn.clicked.connect(
            lambda: self._copy_path_to_clipboard(self._tools_path_input.text(), self._copy_tools_btn)
        )
        r1_box.addWidget(self._copy_tools_btn)

        r1_layout.addWidget(r1_lbl)
        r1_layout.addLayout(r1_box)
        scripts_card.add_layout(r1_layout)

        # Script 2: startup_demo_scripts.py
        r2_layout = QVBoxLayout()
        r2_layout.setSpacing(SPACE_XS)
        r2_lbl = QLabel("Startup Demo Scripts (startup_demo_scripts.py):")
        r2_lbl.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self._demo_lbl = r2_lbl

        r2_box = QHBoxLayout()
        r2_box.setSpacing(SPACE_SM)

        self._demo_path_input = QLineEdit(demo_path_str)
        self._demo_path_input.setReadOnly(True)
        self._demo_path_input.setFont(QFont(FONT_FAMILY_MONO, 10))
        r2_box.addWidget(self._demo_path_input, 1)

        self._copy_demo_btn = QPushButton("Copy Path")
        self._copy_demo_btn.setCursor(Qt.PointingHandCursor)
        self._copy_demo_btn.setFixedHeight(34)
        self._copy_demo_btn.setMinimumWidth(110)
        self._copy_demo_btn.clicked.connect(
            lambda: self._copy_path_to_clipboard(self._demo_path_input.text(), self._copy_demo_btn)
        )
        r2_box.addWidget(self._copy_demo_btn)

        r2_layout.addWidget(r2_lbl)
        r2_layout.addLayout(r2_box)
        scripts_card.add_layout(r2_layout)

        layout.addWidget(scripts_card)
        self._scripts_card = scripts_card
        self._update_scripts_style(dark=False)

        # ── Data display ───────────────────────────────────────────
        data_row = QHBoxLayout()
        data_row.setSpacing(SPACE_MD)

        self._frames_card = MetricCard("Frames", "—", "Total frames", icon_name="camera.svg")
        data_row.addWidget(self._frames_card)

        self._freq_card = MetricCard("Capture Frequency", "—", "Hz", icon_name="radio.svg")
        data_row.addWidget(self._freq_card)

        self._range_card = MetricCard("Frame Range", "—", "First – Last", icon_name="sliders.svg")
        data_row.addWidget(self._range_card)

        layout.addLayout(data_row)

        # ── Command section ────────────────────────────────────────
        cmd_card = SectionCard("Send Command to QTM")
        cmd_row1 = QHBoxLayout()
        cmd_row1.addWidget(QLabel("Command:"))
        self._cmd_name = QLineEdit("PrintMessage")
        cmd_row1.addWidget(self._cmd_name, 1)
        cmd_card.add_layout(cmd_row1)

        cmd_row2 = QHBoxLayout()
        cmd_row2.addWidget(QLabel("Args (JSON):"))
        self._cmd_args = QLineEdit('{"text": "Hello from PySide6!"}')
        cmd_row2.addWidget(self._cmd_args, 1)
        cmd_card.add_layout(cmd_row2)

        send_btn = QPushButton("Send Command")
        send_btn.setObjectName("primaryButton")
        send_btn.clicked.connect(self._send_command)
        cmd_card.add_widget(send_btn)
        layout.addWidget(cmd_card)

        # ── Message log ────────────────────────────────────────────
        log_card = SectionCard("Message Log")
        self._log_output = QTextEdit()
        self._log_output.setReadOnly(True)
        self._log_output.setFixedHeight(200)
        self._update_log_style(dark=False)
        log_card.add_widget(self._log_output)
        layout.addWidget(log_card)

        layout.addStretch()

    def _toggle_connection(self) -> None:
        if self._connection_info.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self) -> None:
        """Start the gRPC server to receive data from QTM."""
        try:
            import grpc
            from concurrent import futures
            import sys
            import os

            # Add QTM-GRPC to path for imports
            from app.services.settings_service import SettingsService
            cfg_qtm = SettingsService().load_app_settings().qtm_grpc_location
            qtm_dir = cfg_qtm if cfg_qtm and os.path.isdir(cfg_qtm) else os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                 "QTM_GRPC"
            )
            if qtm_dir not in sys.path:
                sys.path.insert(0, qtm_dir)

            # pyrefly: ignore [missing-import]
            import qtm_data_transfer_pb2
            # pyrefly: ignore [missing-import]
            import qtm_data_transfer_pb2_grpc

            class BridgeServicer(qtm_data_transfer_pb2_grpc.QtmTkinterBridgeServicer):
                def __init__(self, page):
                    self.page = page

                def SendQtmFieldsToApp(self, request, context):
                    # Use signal to safely update GUI from gRPC thread
                    self.page._update_from_qtm(request)
                    return qtm_data_transfer_pb2.Ack(
                        message="Data received", success=True
                    )

                def SendCommandToQtm(self, request, context):
                    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
                    return qtm_data_transfer_pb2.Ack()

            port = int(self._port_input.text())
            server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            qtm_data_transfer_pb2_grpc.add_QtmTkinterBridgeServicer_to_server(
                BridgeServicer(self), server
            )
            server.add_insecure_port(f"[::]:{port}")
            server.start()

            self._grpc_server = server
            self._connection_info.connected = True
            self._connection_info.port = port
            self._connect_btn.setText("Stop Server")
            self._status_indicator.set_status("connected", "Bridge Listening")
            self.connection_changed.emit(True)
            self._notification.show_message(f"gRPC server started on port {port}", "success")
            self._log(f"Server started on port {port}")

        except ImportError as e:
            self._notification.show_message(
                f"gRPC modules not available: {e}", "error"
            )
        except Exception as e:
            self._notification.show_message(f"Failed to start server: {e}", "error")
            self._log(f"ERROR: {e}")

    def _disconnect(self) -> None:
        if hasattr(self, "_grpc_server"):
            self._grpc_server.stop(0)
        self._connection_info.connected = False
        self._connect_btn.setText("Start Server")
        self._status_indicator.set_status("disconnected", "Disconnected")
        self.connection_changed.emit(False)
        self._log("Server stopped")

    def _update_from_qtm(self, data) -> None:
        """Called from gRPC thread — must use invokeMethod or signal."""
        from PySide6.QtCore import QMetaObject, Q_ARG
        # Safe cross-thread update
        QMetaObject.invokeMethod(
            self, "_apply_qtm_data",
            Qt.QueuedConnection,
            Q_ARG(int, data.frames),
            Q_ARG(float, data.capture_frequency),
            Q_ARG(int, data.first_frame),
            Q_ARG(int, data.last_frame),
        )

    @Slot(int, float, int, int)
    def _apply_qtm_data(self, frames: int, freq: float, first: int, last: int) -> None:
        self._frames_card.set_value(str(frames))
        self._freq_card.set_value(f"{freq:.2f}")
        self._range_card.set_value(f"{first} – {last}")
        self._log(f"Received: frames={frames}, freq={freq:.2f}")

    def _send_command(self) -> None:
        """Send a command to QTM via gRPC client."""
        cmd = self._cmd_name.text()
        args = self._cmd_args.text()

        if not cmd:
            self._notification.show_message("Command name required", "warning")
            return

        try:
            if args:
                json.loads(args)
        except json.JSONDecodeError:
            self._notification.show_message("Invalid JSON arguments", "error")
            return

        try:
            import grpc
            import sys, os
            from app.services.settings_service import SettingsService
            cfg_qtm = SettingsService().load_app_settings().qtm_grpc_location
            qtm_dir = cfg_qtm if cfg_qtm and os.path.isdir(cfg_qtm) else os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                "QTM-GRPC"
            )
            if qtm_dir not in sys.path:
                sys.path.insert(0, qtm_dir)
            # pyrefly: ignore [missing-import]
            import qtm_data_transfer_pb2
            # pyrefly: ignore [missing-import]
            import qtm_data_transfer_pb2_grpc

            with grpc.insecure_channel(f"localhost:50052") as channel:
                stub = qtm_data_transfer_pb2_grpc.QtmTkinterBridgeStub(channel)
                request = qtm_data_transfer_pb2.CommandToQtm(
                    command_name=cmd,
                    command_args_json=args,
                )
                response = stub.SendCommandToQtm(request, timeout=5)
                self._notification.show_message(
                    f"Response: {response.message}", "success"
                )
                self._log(f"Sent: {cmd}, Response: {response.message}")

        except Exception as e:
            self._notification.show_message(f"Failed: {e}", "error")
            self._log(f"ERROR sending command: {e}")

    def _log(self, msg: str) -> None:
        self._log_output.append(msg)

    def _update_log_style(self, dark: bool = False) -> None:
        if dark:
            self._log_output.setStyleSheet(
                "font-family: Consolas, monospace; font-size: 12px; "
                "background-color: #0F172A; color: #14B8A6; "
                "border: 1.5px solid #334155; border-radius: 8px; padding: 10px;"
            )
        else:
            self._log_output.setStyleSheet(
                "font-family: Consolas, monospace; font-size: 12px; "
                "background-color: #F8FAFC; color: #0F172A; "
                "border: 1.5px solid #CBD5E1; border-radius: 8px; padding: 10px;"
            )

    @staticmethod
    def _resolve_qtm_script_paths() -> tuple[str, str]:
        """Auto-detect the absolute paths of startup_tools.py and startup_demo_scripts.py in QTM-GRPC."""
        curr = Path(__file__).resolve().parent
        project_root = None
        for _ in range(6):
            if (curr / "app.py").is_file():
                project_root = curr
                break
            curr = curr.parent

        if not project_root:
            project_root = Path(__file__).resolve().parents[3]

        qtm_grpc_dir = project_root / "Gait-lab-Vicon-to-QTM" / "QTM_GRPC"

        # 1. startup_tools.py (or startup_tool.py)
        tools_path = qtm_grpc_dir / "startup_tools.py"
        if not tools_path.is_file():
            alt_tools = qtm_grpc_dir / "startup_tool.py"
            if alt_tools.is_file():
                tools_path = alt_tools

        # 2. startup_demo_scripts.py (or startup_demo_script.py)
        demo_path = qtm_grpc_dir / "startup_demo_scripts.py"
        if not demo_path.is_file():
            alt_demo = qtm_grpc_dir / "startup_demo_script.py"
            if alt_demo.is_file():
                demo_path = alt_demo

        return (
            str(tools_path.resolve()) if tools_path.exists() else str(tools_path),
            str(demo_path.resolve()) if demo_path.exists() else str(demo_path),
        )

    def _copy_path_to_clipboard(self, path_text: str, button: QPushButton) -> None:
        """Copy the path text to the system clipboard and show animated button confirmation."""
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(path_text)
        orig_text = button.text()
        button.setText("✓ Copied!")
        if getattr(self, "_is_dark", False):
            button.setStyleSheet(
                "QPushButton { background: #065F46; color: #6EE7B7; border: 1.5px solid #10B981; "
                "border-radius: 6px; padding: 6px 14px; font-weight: 700; font-size: 11px; }"
            )
        else:
            button.setStyleSheet(
                "QPushButton { background: #ECFDF5; color: #047857; border: 1.5px solid #10B981; "
                "border-radius: 6px; padding: 6px 14px; font-weight: 700; font-size: 11px; }"
            )
        self._notification.show_message(f"Copied script path to clipboard: {Path(path_text).name}", "success")
        QTimer.singleShot(1800, lambda: (
            button.setText(orig_text),
            self._update_scripts_style(dark=getattr(self, "_is_dark", False))
        ))

    def _update_scripts_style(self, dark: bool = False) -> None:
        """Style script paths inputs and copy buttons for light or dark theme."""
        if not hasattr(self, "_scripts_info_lbl"):
            return

        if dark:
            if hasattr(self, "_conn_note"):
                self._conn_note.setStyleSheet("color: #94A3B8; font-size: 11px; margin-top: 6px; line-height: 1.4;")
            self._scripts_info_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; margin-bottom: 2px;")
            self._tools_lbl.setStyleSheet("color: #E2E8F0; font-size: 12px; font-weight: bold;")
            self._demo_lbl.setStyleSheet("color: #E2E8F0; font-size: 12px; font-weight: bold;")

            input_style = (
                "QLineEdit { background-color: #0F172A; color: #2DD4BF; border: 1.5px solid #334155; "
                "border-radius: 6px; padding: 6px 10px; font-family: Consolas, monospace; font-size: 11px; }"
                "QLineEdit:focus { border-color: #14B8A6; }"
            )
            self._tools_path_input.setStyleSheet(input_style)
            self._demo_path_input.setStyleSheet(input_style)

            btn_style = (
                "QPushButton { background: #1E293B; color: #2DD4BF; border: 1.5px solid #14B8A6; "
                "border-radius: 6px; padding: 6px 14px; font-weight: 700; font-size: 11px; }"
                "QPushButton:hover { background: #134E4A; color: #FFFFFF; border-color: #2DD4BF; }"
                "QPushButton:pressed { background: #0F766E; }"
            )
            self._copy_tools_btn.setStyleSheet(btn_style)
            self._copy_demo_btn.setStyleSheet(btn_style)
        else:
            if hasattr(self, "_conn_note"):
                self._conn_note.setStyleSheet("color: #64748B; font-size: 11px; margin-top: 6px; line-height: 1.4;")
            self._scripts_info_lbl.setStyleSheet("color: #64748B; font-size: 12px; margin-bottom: 2px;")
            self._tools_lbl.setStyleSheet("color: #1E293B; font-size: 12px; font-weight: bold;")
            self._demo_lbl.setStyleSheet("color: #1E293B; font-size: 12px; font-weight: bold;")

            input_style = (
                "QLineEdit { background-color: #F8FAFC; color: #0F766E; border: 1.5px solid #CBD5E1; "
                "border-radius: 6px; padding: 6px 10px; font-family: Consolas, monospace; font-size: 11px; }"
                "QLineEdit:focus { border-color: #0D9488; }"
            )
            self._tools_path_input.setStyleSheet(input_style)
            self._demo_path_input.setStyleSheet(input_style)

            btn_style = (
                "QPushButton { background: #FFFFFF; color: #0F766E; border: 1.5px solid #0F766E; "
                "border-radius: 6px; padding: 6px 14px; font-weight: 700; font-size: 11px; }"
                "QPushButton:hover { background: #F0FDFA; color: #115E59; border-color: #0D9488; }"
                "QPushButton:pressed { background: #CCFBF1; }"
            )
            self._copy_tools_btn.setStyleSheet(btn_style)
            self._copy_demo_btn.setStyleSheet(btn_style)

    def apply_theme(self, palette=None, dark: bool = False) -> None:
        """Update QTM monitor metric cards and message log for theme change."""
        self._is_dark = dark
        cards = [self._frames_card, self._freq_card, self._range_card]
        for card in cards:
            card.apply_theme(palette, dark)
        self._update_log_style(dark=dark)
        self._update_scripts_style(dark=dark)


