import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from gapi import (
    SetTrajectory,
    CreateModeledMarker,
    GetForcePlate,
    GetEvents,
    getTimeLineMeasure,
)
import os
import sys

if sys.platform == "win32":
    import ctypes
    _sys32_icu = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "icuuc.dll")
    if os.path.exists(_sys32_icu):
        try:
            ctypes.WinDLL(_sys32_icu)
        except Exception:
            pass

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QCheckBox,
    QGroupBox, QScrollArea, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
import json


class SimModlOutput:
    def __init__(self):
        """
        Model Format
        Markers={
                MarkerName:
                {
                    "X": [],
                    "Y": [],
                    "Z": [],
                    "Exists": []
                }
                }
        model={


            Groupname1={
                ModelOutputName1={
                    Name=["ComponentName1", "ComponentName2", ...]
                    QuantityTypes=["QuantityType1", "QuantityType2", ...]
                    ComponentName1=Any
                    ComponentName2=Any
                    ...
                }
                ModelOutputName2={
                    Name=["ComponentName1", "ComponentName2", ...]
                    QuantityTypes=["QuantityType1", "QuantityType2", ...]
                    ComponentName1=Any
                    ComponentName2=Any
                    ...
                }
            }

        }
        """
        self.model = {}
        self.modelOutputs = set()
        self.Markers = {}
        self.leftPlate = "0"
        self.rightPlate = "0"

    def CreateModelOutput(
        self, modelOutputName, groupName, componentNames, QuantityTypes
    ):
        if groupName not in self.model:
            self.model[groupName] = {}
        if modelOutputName not in self.model[groupName]:
            self.modelOutputs.add(modelOutputName)
            self.model[groupName][modelOutputName] = {}
            self.model[groupName][modelOutputName]["Name"] = componentNames
            self.model[groupName][modelOutputName]["QuantityTypes"] = QuantityTypes
            for componentName in componentNames:
                self.model[groupName][modelOutputName][componentName] = None

    def getContents(self):
        return list(self.modelOutputs)

    def CreateModeledMarker(self, name):
        if name not in self.Markers:
            self.Markers[name] = {}
            CreateModeledMarker(name)
        else:
            print(f"Marker '{name}' already exists.")

    def SetModelOutput(self, modelOutputName, components, e,start,end,offset=0):
        if modelOutputName in self.Markers:
            self.Markers[modelOutputName]["X"] = components[0]
            self.Markers[modelOutputName]["Y"] = components[1]
            self.Markers[modelOutputName]["Z"] = components[2]
            self.Markers[modelOutputName]["Exists"] = e
            SetTrajectory(
                modelOutputName, components[0], components[1], components[2], e,start,end,offset
            )
            return
        for key, val in self.model.items():
            if modelOutputName in val:
                for componentName, value in zip(
                    val[modelOutputName]["Name"], components
                ):
                    val[modelOutputName][componentName] = value
                return

    def GetModelOutput(self, ModelName):
        arr = []
        for i in self.model.keys():
            if ModelName in self.model[i]:
                for componentName in self.model[i][ModelName]["Name"]:
                    arr.append(self.model[i][ModelName][componentName])

                return arr, [True] * len(arr)

    def printItem(self, name):
        if name in self.Markers:
            print(f"Marker: {name}")
            return
        for key, val in self.model.items():
            if name in val:
                print(f"Group: {key}, Model Output: {name}")
                for componentName, value in val[name].items():
                    print(f"  {componentName}: {value}")
                return
        print(f"Item '{name}' not found in model.")

    def saveAsJson(self, filename):
        with open(Path(__file__).parent / filename, "w") as f:
            json.dump(self.model, f, indent=4)


class ForcePlateGUI:
    def __init__(self, payload):
        self.payload = payload
        self._app = QApplication.instance() or QApplication(sys.argv)

        # Register fonts (Inter) if available
        fonts_dir = Path(__file__).resolve().parent.parent / "resources" / "fonts"
        if fonts_dir.is_dir():
            for font_file in fonts_dir.glob("*.ttf"):
                QFontDatabase.addApplicationFont(str(font_file))

        self.window = QMainWindow()
        self.window.setWindowTitle("Force Plate Selector")
        self.window.resize(950, 750)
        self.window.setStyleSheet("""
            QMainWindow, QWidget#centralWidget, QScrollArea, QWidget#scrollContent {
                background-color: #F8FAFC;
                color: #0F172A;
            }
            QScrollArea {
                border: none;
                background-color: #F8FAFC;
            }
            QLabel {
                color: #0F172A;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                background: transparent;
            }
            QLabel#titleLabel {
                font-size: 18pt;
                font-weight: 700;
                color: #0F172A;
                margin-bottom: 2px;
            }
            QLabel#instructionsLabel {
                font-size: 11pt;
                color: #475569;
                line-height: 1.4;
                margin-bottom: 8px;
            }
            QGroupBox {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                margin-top: 18px;
                padding: 16px;
                font: bold 13pt 'Inter';
                color: #0F172A;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 14px;
                padding: 2px 10px;
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                color: #0F172A;
                font-weight: 700;
            }
            QCheckBox {
                color: #0F172A;
                font: 12pt 'Inter';
                font-weight: 600;
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1.5px solid #94A3B8;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:hover {
                border-color: #0284C7;
            }
            QCheckBox::indicator:checked {
                background-color: #0284C7;
                border-color: #0284C7;
            }
            QLineEdit {
                font-family: 'Consolas', monospace;
                font-size: 9.5pt;
                padding: 5px 8px;
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border: 1.5px solid #0284C7;
                background-color: #F0F9FF;
            }
            QPushButton {
                font: bold 12pt 'Inter';
                padding: 8px 24px;
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
            QPushButton:pressed {
                background-color: #075985;
            }
        """)

        # Variables to track selected left and right force plates
        self.left_var = "0"
        self.right_var = "0"
        self._left_checkboxes = {}
        self._right_checkboxes = {}

        self._create_widgets()

    def calculate_max_min(self, data_list):
        """Calculate max and min values from a list of data, filtering non-finite values."""
        try:
            arr = np.array(data_list, dtype=float)
            finite = arr[np.isfinite(arr)]
            if len(finite) == 0:
                return 0.0, 0.0
            return float(np.nanmax(finite)), float(np.nanmin(finite))
        except Exception:
            return 0.0, 0.0

    def _create_widgets(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.window.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 20, 24, 20)

        # Header
        title = QLabel("Force Plate Selection")
        title.setObjectName("titleLabel")
        title.setFont(QFont("Inter", 18, QFont.Bold))
        main_layout.addWidget(title)

        instructions = QLabel(
            "1. Open Data Info Window in QTM (Right Click > Display Force Data).\n"
            "2. Compare Max/Min values of Force (X,Y) with the plots below.\n"
            "3. Select the corresponding checkbox (Left/Right) if values match.\n"
            "Note: Only one Left and one Right plate can be selected."
        )
        instructions.setObjectName("instructionsLabel")
        instructions.setWordWrap(True)
        main_layout.addWidget(instructions)

        # Scrollable area
        scroll = QScrollArea()
        scroll.setObjectName("scrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        self._scroll_layout = QVBoxLayout(scroll_content)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

        # Create widgets for each force plate ID
        for plate_id in self.payload:
            self._create_plate_widget(self._scroll_layout, plate_id)

        self._scroll_layout.addStretch()

        # Footer
        footer = QHBoxLayout()
        self.result_label = QLabel("")
        self.result_label.setStyleSheet("font: italic 10pt 'Segoe UI'; color: #64748B;")
        footer.addWidget(self.result_label)
        footer.addStretch()
        confirm_btn = QPushButton("Confirm Selection")
        confirm_btn.setFixedWidth(200)
        confirm_btn.clicked.connect(self.show_results)
        footer.addWidget(confirm_btn)
        main_layout.addLayout(footer)

    def _create_center_mod(self, parent_layout, plate_id):
        """Configuration section for origin, world center, offset"""
        config_grid = QGridLayout()
        config_grid.setSpacing(6)
        config_grid.setContentsMargins(0, 8, 0, 8)

        headers = ["Parameter", "X", "Y", "Z"]
        for i, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setFont(QFont("Inter", 11, QFont.Bold))
            lbl.setStyleSheet("color: #475569; font-weight: 700; background: transparent;")
            config_grid.addWidget(lbl, 0, i)

        def create_input_row(row, label, data_key, update_cb):
            param_lbl = QLabel(label)
            param_lbl.setStyleSheet("color: #334155; font-weight: 600; background: transparent;")
            config_grid.addWidget(param_lbl, row, 0)
            data = self.payload[plate_id][data_key]
            if isinstance(data, dict):
                vals = [data['X'], data['Y'], data['Z']]
            else:
                vals = data

            entries = []
            for i, val in enumerate(vals):
                e = QLineEdit(f"{val:.6f}")
                e.setAlignment(Qt.AlignCenter)
                e.setMaximumWidth(120)
                config_grid.addWidget(e, row, i + 1)
                entries.append(e)

            def on_change():
                combined = f"{entries[0].text()},{entries[1].text()},{entries[2].text()}"
                update_cb(plate_id, combined)

            for e in entries:
                e.editingFinished.connect(on_change)

        # Ensure Offset exists
        if "Offset" not in self.payload[plate_id]:
            self.payload[plate_id]["Offset"] = {"X": 0.0, "Y": 0.0, "Z": 0.0}

        create_input_row(1, "Origin", "Origin", self.update_origin)
        create_input_row(2, "World Center", "WorldCenter", self.update_world_center)
        create_input_row(3, "Offset", "Offset", self.update_offset)

        parent_layout.addLayout(config_grid)

    def update_offset(self, plate_id, value_str):
        """Update offset data in payload"""
        try:
            values = value_str.split(",")
            if len(values) == 3:
                offset = [float(val) for val in values]
                if "Offset" not in self.payload[plate_id]:
                    self.payload[plate_id]["Offset"] = {}
                self.payload[plate_id]["Offset"] = {"X": offset[0], "Y": offset[1], "Z": offset[2]}
                print(f"Updated offset for {plate_id}: {offset}")
            else:
                QMessageBox.critical(self.window, "Invalid Format", "Offset must be in format: X,Y,Z")
        except ValueError:
            QMessageBox.critical(self.window, "Invalid Values", "Please enter valid numeric values")

    def update_origin(self, plate_id, value_str):
        """Update origin data in payload"""
        try:
            values = value_str.split(",")
            if len(values) == 3:
                origin = [float(val) for val in values]
                self.payload[plate_id]["Origin"] = origin
                print(f"Updated origin for {plate_id}: {origin}")
            else:
                QMessageBox.critical(self.window, "Invalid Format", "Origin must be in format: X,Y,Z")
        except ValueError:
            QMessageBox.critical(self.window, "Invalid Values", "Please enter valid numeric values")

    def update_world_center(self, plate_id, value_str):
        """Update world center data in payload"""
        try:
            values = value_str.split(",")
            if len(values) == 3:
                world_center = [float(val) for val in values]
                self.payload[plate_id]["WorldCenter"] = world_center
                print(f"Updated world center for {plate_id}: {world_center}")
            else:
                QMessageBox.critical(self.window, "Invalid Format", "World Center must be in format: X,Y,Z")
        except ValueError:
            QMessageBox.critical(self.window, "Invalid Values", "Please enter valid numeric values")

    def _create_plate_widget(self, parent_layout, plate_id):
        """Create widget for individual force plate"""
        card = QGroupBox(f" Force Plate ID: {plate_id} ")
        card_layout = QVBoxLayout(card)

        # Selection area
        select_layout = QHBoxLayout()
        left_cb = QCheckBox("Left Force Plate")
        right_cb = QCheckBox("Right Force Plate")

        self._left_checkboxes[plate_id] = left_cb
        self._right_checkboxes[plate_id] = right_cb

        left_cb.stateChanged.connect(lambda state, pid=plate_id: self.on_left_selected(pid, state))
        right_cb.stateChanged.connect(lambda state, pid=plate_id: self.on_right_selected(pid, state))

        select_layout.addWidget(left_cb)
        select_layout.addSpacing(24)
        select_layout.addWidget(right_cb)
        select_layout.addStretch()
        card_layout.addLayout(select_layout)

        # Configuration inputs
        self._create_center_mod(card_layout, plate_id)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #E2E8F0; max-height: 1px; border: none; margin: 8px 0;")
        card_layout.addWidget(sep)

        # Data statistics
        stats_grid = QGridLayout()
        stats_grid.setSpacing(6)
        stats_grid.setContentsMargins(0, 4, 0, 4)
        headers = ["Metric", "X (Max/Min)", "Y (Max/Min)", "Z (Max/Min)"]
        for i, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setFont(QFont("Inter", 11, QFont.Bold))
            lbl.setStyleSheet("color: #475569; font-weight: 700; background: transparent;")
            stats_grid.addWidget(lbl, 0, i)

        row = 1
        for data_type in ["Force", "Moment", "Center_of_Pressure"]:
            type_lbl = QLabel(data_type.replace("_", " "))
            type_lbl.setStyleSheet("color: #334155; font-weight: 600; background: transparent;")
            stats_grid.addWidget(type_lbl, row, 0)
            for col, axis in enumerate(["X", "Y", "Z"]):
                data = self.payload[plate_id][data_type][axis]
                max_val, min_val = self.calculate_max_min(data)
                scale = 1000.0 if data_type == 'Moment' else 1.0
                val_str = f"{max_val/scale:.2f} / {min_val/scale:.2f}"
                val_lbl = QLabel(val_str)
                val_lbl.setFont(QFont("Consolas", 9))
                val_lbl.setStyleSheet("color: #0F172A; font-family: 'Consolas'; background: transparent;")
                val_lbl.setAlignment(Qt.AlignRight)
                stats_grid.addWidget(val_lbl, row, col + 1)
            row += 1

        card_layout.addLayout(stats_grid)
        parent_layout.addWidget(card)

    def on_left_selected(self, plate_id, state):
        """Handle left force plate selection"""
        if state == Qt.Checked.value:
            # If right is also checked on this plate, uncheck right
            right_cb = self._right_checkboxes[plate_id]
            if right_cb.isChecked():
                right_cb.blockSignals(True)
                right_cb.setChecked(False)
                right_cb.blockSignals(False)
                self.right_var = "0"

            # Uncheck all other left checkboxes
            for other_id, other_cb in self._left_checkboxes.items():
                if other_id != plate_id and other_cb.isChecked():
                    other_cb.blockSignals(True)
                    other_cb.setChecked(False)
                    other_cb.blockSignals(False)

            self.left_var = str(plate_id)
        else:
            self.left_var = "0"

    def on_right_selected(self, plate_id, state):
        """Handle right force plate selection"""
        if state == Qt.Checked.value:
            # If left is also checked on this plate, uncheck left
            left_cb = self._left_checkboxes[plate_id]
            if left_cb.isChecked():
                left_cb.blockSignals(True)
                left_cb.setChecked(False)
                left_cb.blockSignals(False)
                self.left_var = "0"

            # Uncheck all other right checkboxes
            for other_id, other_cb in self._right_checkboxes.items():
                if other_id != plate_id and other_cb.isChecked():
                    other_cb.blockSignals(True)
                    other_cb.setChecked(False)
                    other_cb.blockSignals(False)

            self.right_var = str(plate_id)
        else:
            self.right_var = "0"

    def show_results(self):
        """Display selected force plate IDs and exit event loop cleanly"""
        left_id = self.left_var
        right_id = self.right_var

        # Store results
        self.result_left = left_id
        self.result_right = right_id

        self.window.close()
        try:
            self._app.quit()
        except Exception:
            pass
        return left_id, right_id

    def get_selected_plates(self):
        """Return the selected force plate IDs"""
        return self.left_var, self.right_var

    def run(self):
        """Start the GUI"""
        if not self.payload:
            return self.get_selected_plates()
        if os.environ.get("SHRINERS_NON_INTERACTIVE") == "1" and os.environ.get("SHRINERS_FORCEPLATE_INTERACTIVE") != "1":
            if self.left_var == "0" and self.right_var == "0" and self.payload:
                keys = list(sorted(self.payload.keys()))
                self.left_var = keys[0] if keys else "0"
                self.right_var = keys[1] if len(keys) > 1 else "0"
            return self.get_selected_plates()
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        self._app.exec()
        return self.get_selected_plates()


def normalize_zeroes(payload,key):
    payload[key]["X"][np.isclose(payload[key]["X"], 0.0)] = 0.0
    payload[key]["Y"][np.isclose(payload[key]["Y"], 0.0)] = 0.0
    payload[key]["Z"][np.isclose(payload[key]["Z"], 0.0)] = 0.0

def ProcessForceplateData(reader):
    # forcePlateIds = qtm.data.series.force.get_series_ids()
    tmp = GetForcePlate()
    n = len(reader["data"]["platform"])
    payload = {}
    # QTM returns the COP series for the whole (uncropped) measurement, while
    # the c3d force/moment arrays start at the crop. Shift the QTM COP by the
    # crop offset so both index the same samples; otherwise the COP is read
    # from before the foot lands and collapses to the plate centre.
    first_frame = reader["header"]["points"]["first_frame"]
    point_rate = reader["parameters"]["POINT"]["RATE"]["value"][0]
    analog_rate = reader["parameters"]["ANALOG"]["RATE"]["value"][0]
    crop_start = int(round(first_frame * analog_rate / point_rate))

    def align_to_c3d(series, target_len):
        series = np.array(series)
        if len(series) > target_len:
            series = series[crop_start:crop_start + target_len]
        return series

    qids = sorted(map(lambda x: int(x), tmp.keys())) if tmp else []
    for id in range(n):
        qid = qids[id] if id < len(qids) else None
        n_samples = len(reader["data"]["platform"][id]["force"][0])
        center = np.mean(reader["data"]["platform"][id]["corners"], axis=1)

        # Force components
        force_x = -reader["data"]["platform"][id]["force"][0]
        force_y = -reader["data"]["platform"][id]["force"][1]
        force_z = -reader["data"]["platform"][id]["force"][2]

        # Moment components
        moment_x = reader["data"]["platform"][id]["moment"][0]
        moment_y = reader["data"]["platform"][id]["moment"][1]
        moment_z = -reader["data"]["platform"][id]["moment"][2]

        # Center of pressure
        if qid is not None and str(qid) in tmp and "Center_of_Pressure" in tmp[str(qid)]:
            cop_x = align_to_c3d(tmp[str(qid)]["Center_of_Pressure"]["X"], n_samples) + center[0]
            cop_y = -align_to_c3d(tmp[str(qid)]["Center_of_Pressure"]["Y"], n_samples) + center[1]
            cop_z = align_to_c3d(tmp[str(qid)]["Center_of_Pressure"]["Z"], n_samples) + center[2] / 2
            exists = tmp[str(qid)].get("Exists", [])
            freq = tmp[str(qid)].get("Frequency", reader["parameters"]["ANALOG"]["RATE"]["value"][0])
        else:
            cop_data = reader["data"]["platform"][id]["center_of_pressure"]
            cop_x = np.array(cop_data[1], dtype=float)
            cop_y = -np.array(cop_data[0], dtype=float)
            cop_z = -np.array(cop_data[2], dtype=float)
            exists = [True] * n_samples
            freq = reader["parameters"]["ANALOG"]["RATE"]["value"][0]

        payload[f"FP{id}"] = {
            "Force": {
                "X": force_x,
                "Y": force_y,
                "Z": force_z,
            },
            "Moment": {
                "X": moment_x,
                "Y": moment_y,
                "Z": moment_z,
            },
            "Center_of_Pressure": {
                "X": cop_x,
                "Y": cop_y,
                "Z": cop_z,
            },
            "Exists": exists,
            "Frequency": freq,
            "Origin": reader["data"]["platform"][id]["origin"],
            "WorldCenter": center,

            "Offset": {"X": np.round(center[0]), "Y": np.round(center[1]), "Z": np.round(center[2])/2}  # Initialize offset with default zeros
        }
        normalize_zeroes(payload[f"FP{id}"], "Force")
        normalize_zeroes(payload[f"FP{id}"], "Moment")
        normalize_zeroes(payload[f"FP{id}"], "Center_of_Pressure")

    print(payload.keys())
    return payload


# Example usage
def main():
    # Sample payload data
    payload = {
        "1": {
            "Force": {
                "X": [10.5, 15.2, 8.9, 12.1],
                "Y": [5.3, 7.8, 4.2, 6.9],
                "Z": [25.1, 30.4, 22.7, 28.3],
            },
            "Moment": {
                "X": [2.1, 3.5, 1.8, 2.9],
                "Y": [1.7, 2.3, 1.2, 2.0],
                "Z": [4.2, 5.1, 3.8, 4.7],
            },
            "Center_of_Pressure": {
                "X": [0.15, 0.22, 0.08, 0.18],
                "Y": [0.12, 0.19, 0.06, 0.14],
                "Z": [0.0, 0.0, 0.0, 0.0],
            },
            "Exists": [True, True, True, True],
            "Origin": [0.0, 0.0, 0.0],
            "WorldCenter": [0.0, 0.0, 0.0],
        },
        "2": {
            "Force": {
                "X": [8.3, 11.7, 6.9, 9.5],
                "Y": [4.1, 6.2, 3.5, 5.1],
                "Z": [20.8, 26.3, 18.9, 23.7],
            },
            "Moment": {
                "X": [1.9, 2.8, 1.4, 2.3],
                "Y": [1.5, 2.1, 1.0, 1.8],
                "Z": [3.7, 4.5, 3.2, 4.1],
            },
            "Center_of_Pressure": {
                "X": [0.13, 0.20, 0.07, 0.16],
                "Y": [0.10, 0.17, 0.05, 0.12],
                "Z": [0.0, 0.0, 0.0, 0.0],
            },
            "Exists": [True, True, True, True],
            "Origin": [0.0, 0.0, 0.0],
            "WorldCenter": [0.0, 0.0, 0.0],
        },
        "3": {
            "Force": {
                "X": [8.3, 11.7, 6.9, 9.5],
                "Y": [4.1, 6.2, 3.5, 5.1],
                "Z": [20.8, 26.3, 18.9, 23.7],
            },
            "Moment": {
                "X": [1.9, 2.8, 1.4, 2.3],
                "Y": [1.5, 2.1, 1.0, 1.8],
                "Z": [3.7, 4.5, 3.2, 4.1],
            },
            "Center_of_Pressure": {
                "X": [0.13, 0.20, 0.07, 0.16],
                "Y": [0.10, 0.17, 0.05, 0.12],
                "Z": [0.0, 0.0, 0.0, 0.0],
            },
            "Exists": [True, True, True, True],
            "Origin": [0.0, 0.0, 0.0],
            "WorldCenter": [0.0, 0.0, 0.0],
        },
    }

    # Create and run the GUI
    app = ForcePlateGUI(payload)
    left_id, right_id = app.run()

    print(f"Final selection - Left: {left_id}, Right: {right_id}")
    return left_id, right_id


def GetTrajectoryAtFrame(fields, model: SimModlOutput, markerName, Frame):
    if markerName in fields["Points"]:
        return (
            fields[markerName]["X"][Frame],
            fields[markerName]["Y"][Frame],
            fields[markerName]["Z"][Frame],
            fields[markerName]["Exists"][Frame],
        )
    if markerName in model.Markers:
        return (
            model.Markers[markerName]["X"][Frame],
            model.Markers[markerName]["Y"][Frame],
            model.Markers[markerName]["Z"][Frame],
            model.Markers[markerName]["Exists"][Frame],
        )


if __name__ == "__main__":
    # print(GetEvents("RSTRIKE"))
    print()
    #main()
