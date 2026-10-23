# -*- coding: utf-8 -*-
"""
<One of the file associated with the Program to compute lower extremity Shrine Gait Model kinematics and kinetics>
Copyright (C) 2023  <Anas Fodkar>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

"""
# Static Model computes posture and stores Technical to Anatomical Coordinate Transformaion

Created on Thu Feb 01 11:09:51 2018
Last Update: Aug 26, 2024

@author: psaraswat
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""
VersionNumber = "Py3_v1.3"

import os.path
import sys
import datetime

import threading
import os as _os
import sys as _sys

if _sys.platform == "win32":
    import ctypes as _ctypes
    _sys32_icu = _os.path.join(_os.environ.get("SystemRoot", r"C:\Windows"), "System32", "icuuc.dll")
    if _os.path.exists(_sys32_icu):
        try:
            _ctypes.WinDLL(_sys32_icu)
        except Exception:
            pass

from pyside6_compat import tk, ttk, filedialog, messagebox
from PySide6.QtWidgets import QStackedWidget, QApplication, QVBoxLayout, QFileDialog

from Py3_varExtractor import extract_fields_by_filename
from gapi import run_tkinter_grpc_server, SetTrajectory, CreateModeledMarker

# import tkFileDialog

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import reportlab.lib.colors as reportlabColors

import numpy as np
from numpy import array, nan

# import Vicon Nexus Subroutines
# from viconnexusapi import ViconNexus
vicon = None  # ViconNexus.ViconNexus()

# import Common Vector/Matrix Operations Modules
import Py3_MathModules as math
import Py3_GaitModules as gait
from pathlib import Path
import argparse

UserPreferencesFileName = Path(__file__).parent / "Py3_UserPreferences.py"
MILLIMETERS_PER_METER = 1000.0


def qtm_measurement_to_meters(value):
    numeric_value = float(value)
    # QTM sometimes reports these fields already in meters (small values like
    # 0.246) and sometimes in millimeters (large values like 246.0). Only
    # convert when the magnitude indicates millimeters, same heuristic used
    # for previously-persisted values below.
    return round(numeric_value / MILLIMETERS_PER_METER if abs(numeric_value) > 10 else numeric_value, 3)


def persisted_measurement_to_meters(value):
    numeric_value = float(value)
    return round(numeric_value / MILLIMETERS_PER_METER if abs(numeric_value) > 10 else numeric_value, 3)


def normalize_processing_measurements(owner):
    measurement_names = (
        "valueHeight", "valueASISdist", "valueLeftLegLength", "valueRightLegLength",
        "valueLeftKneeWidth", "valueRightKneeWidth", "valueLeftAnkleWidth",
        "valueRightAnkleWidth", "valueLeftASIStoGTdist", "valueRightASIStoGTdist",
        "valueLeftSoleThickness", "valueRightSoleThickness",
    )
    for measurement_name in measurement_names:
        value = float(getattr(owner, measurement_name))
        explicit_meters = getattr(owner, "valueMeasurementUnits", "") == "m"
        setattr(owner, measurement_name, value * MILLIMETERS_PER_METER if explicit_meters else
                value if abs(value) > 10 else value * MILLIMETERS_PER_METER)


def write_setting(file_handle, name, value):
    file_handle.write(f"self.{name} = {value!r}\n")


def display_measurement_meters(value):
    return f"{float(value) / MILLIMETERS_PER_METER:.3f}"
# First Argument is the command name, second argument is the testing condition

DefaultTestingCondition = "BF"
# TestingCondition = DefaultTestingCondition


#Create argument parser
parser = argparse.ArgumentParser(description='Process gait analysis data')
parser.add_argument('--TestingCondition', '-t', default="BF", help='Testing condition parameter (default: BF)')
parser.add_argument('--sessionPath', '-s', required=True, help='Path to the session directory')
parser.add_argument('--filename', '-f', required=True, help='Name of the file to process')
parser.add_argument('--headless', action='store_true', default=False,
                    help='Run without GUI — auto-process and save results, then exit')

# Parse arguments
args = parser.parse_args()

# Use the parsed arguments
TestingCondition = args.TestingCondition   # "BF"
sessionPath = args.sessionPath
filename = args.filename


fields = extract_fields_by_filename(sessionPath, filename,True)

# print(vicon.GetSubjectNames())
SubjectName = fields["Name"]
FilePath, FileName = fields["Path"], fields["Filename"]
# StaticDataFileName = FilePath + 'Static_BF_' + SubjectName + '.py'
calib_dir = Path(FilePath) / "Calibration"
calib_dir.mkdir(parents=True, exist_ok=True)
_calib_cand = calib_dir / ("Static_" + TestingCondition + "_" + SubjectName + ".py")
if _calib_cand.exists():
    StaticDataFileName = _calib_cand
elif (Path(FilePath) / ("Static_" + TestingCondition + "_" + SubjectName + ".py")).exists():
    StaticDataFileName = Path(FilePath) / ("Static_" + TestingCondition + "_" + SubjectName + ".py")
else:
    StaticDataFileName = _calib_cand

_sitting_cand = calib_dir / ("SittingFootStatic_" + TestingCondition + "_" + SubjectName + ".py")
if _sitting_cand.exists():
    SittingFootStaticDataFileName = _sitting_cand
elif (Path(FilePath) / ("SittingFootStatic_" + TestingCondition + "_" + SubjectName + ".py")).exists():
    SittingFootStaticDataFileName = Path(FilePath) / ("SittingFootStatic_" + TestingCondition + "_" + SubjectName + ".py")
else:
    SittingFootStaticDataFileName = _sitting_cand

# Height and Width of App Display (base dimensions, will scale with DPI)
AppHeight = 950
AppWidth = 800
# Default font for display
Large_Font = "Calibri 14 bold"  # ("Calibri", 20)
Small_Font_Bold = "Calibri 12 bold"
Small_Font = ("Calibri", 12)
Smaller_Font = ("Calibri", 10)
Bold_Small_Font = "Calibri 14 bold"

# Enable DPI awareness
try:
    _ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except:
    try:
        _ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass


# This is the main function and has references to all the forms
class Static_Main(tk.Tk):
    # This __init__ part of the code runs everytime
    def __init__(self, headless=False):
        tk.Tk.__init__(self)
        self._headless = headless
        # Specify title of Form
        tk.Tk.wm_title(self, "Static Analysis")
        
        # Make window responsive to screen size
        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Set window size to 80% of screen size but with limits
        window_width = min(int(screen_width * 0.8), 1000)
        window_height = min(int(screen_height * 0.85), 900)
        
        # Center the window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.minsize(800, 600)
        # Start maximized (skip in headless mode)
        if not headless:
            try:
                self.state("zoomed")
            except:
                self.attributes("-fullscreen", True)
        
        # Use QStackedWidget for page navigation (replaces tkinter grid overlay)
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Create a dictionary of frames/forms
        self.frames = {}
        frames = (PatientInfo_Page, QAreport_Page, StaticSubjectCalibrationReport_Page)
        # Specify all the form names
        for F in frames:
            frame = F(self)
            self._stack.addWidget(frame)
            self.frames[F] = frame

        # Initialize the first form
        self._stack.setCurrentWidget(self.frames[PatientInfo_Page])
        self.frames[PatientInfo_Page].build_UI()



class PatientInfo_Page(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.grid(sticky="nsew")
        
        # Configure grid for responsiveness
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Create scrollable canvas that wraps the entire content
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Grid layout
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Create inner frame that will hold all content
        self.inner_frame = tk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        
        # Bind mousewheel
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Update scroll region when inner frame changes
        def _configure_inner(event):
            pass  # Scroll region handled by PySide6
        self.inner_frame.bind("<Configure>", _configure_inner)
        
        # Make canvas window width match canvas width
        def _configure_canvas(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        self.canvas.bind("<Configure>", _configure_canvas)

    def HasTrajectory(self, subjectName, markerName):
        return markerName in fields

    def build_UI(self):
        import os # Ensure os is imported for file operations
        
        # =============================================================================
        # Layout Configuration: Split Scrollable Left vs Fixed Right
        # =============================================================================
        # Configure the main frame grid to hold the canvas (left) and buttons (right)
        self.grid_columnconfigure(0, weight=1)  # Canvas takes all extra space
        self.grid_columnconfigure(1, weight=0)  # Scrollbar size
        self.grid_columnconfigure(2, weight=0)  # Button Panel fixed size
        
        # Ensure scrollbar is correctly placed
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Create a dedicated frame for the fixed buttons on the right
        # We check if it exists to avoid duplication on refresh
        if hasattr(self, 'button_frame'):
            self.button_frame.destroy()
            
        self.button_frame = tk.Frame(self, bg="SystemButtonFace")
        self.button_frame.grid(row=0, column=2, sticky="ns", padx=5, pady=5)
        
        # Fixed Buttons anchored to the right
        ProceedButton = tk.Button(
            self.button_frame,
            text="Save &" + "\n" + "Proceed",
            font=Small_Font,
            justify="center",
            bg="#e1e1e1", 
            command=lambda: [
                saveSubjectData(),
                self.parent._stack.setCurrentWidget(self.parent.frames[QAreport_Page]),
                self.parent.frames[QAreport_Page].build_UI(),
            ],
        )
        ProceedButton.pack(side="top", pady=20, ipadx=5, ipady=5, fill="x")

        QuitButton = tk.Button(
            self.button_frame, 
            text="Quit", 
            font=Small_Font,
            bg="#e1e1e1",
            command=lambda: quit()
        )
        # Moved Quit button to 'top' to sit just below ProceedButton
        QuitButton.pack(side="top", pady=20, ipadx=5, ipady=5, fill="x")

        # =============================================================================
        # Scrollable Form Content Setup
        # =============================================================================
        # Use inner_frame as the parent for all form widgets
        parent_frame = self.inner_frame
        
        # Clear existing widgets in the scrollable frame if rebuilding
        # Clear existing widgets in parent_frame

        # PySide6 handles this via layout replacement

        # Define padding for grid cells
        pad_options = {'padx': 5, 'pady': 5}
        
        # --- SECTION 1: Patient Information ---
        # Fixed: padding=10 replaced with padx=10, pady=10 for tk.LabelFrame
        patient_frame = tk.LabelFrame(parent_frame, text="Patient Information", font=Large_Font, padx=10, pady=10)
        patient_frame.pack(fill="x", expand=True, padx=10, pady=5)
        
        # Grid layout for Patient Info
        patient_frame.columnconfigure(1, weight=1)
        patient_frame.columnconfigure(3, weight=1)

        tk.Label(patient_frame, text="First Name", font=Small_Font).grid(row=0, column=0, sticky="e", **pad_options)
        FirstName = tk.Entry(patient_frame)
        FirstName.grid(row=0, column=1, sticky="ew", **pad_options)

        tk.Label(patient_frame, text="Last Name", font=Small_Font).grid(row=0, column=2, sticky="e", **pad_options)
        LastName = tk.Entry(patient_frame)
        LastName.grid(row=0, column=3, sticky="ew", **pad_options)

        tk.Label(patient_frame, text="Patient Number", font=Small_Font).grid(row=1, column=0, sticky="e", **pad_options)
        PatientNumber = tk.Entry(patient_frame)
        PatientNumber.grid(row=1, column=1, sticky="ew", **pad_options)

        tk.Label(patient_frame, text="Date Of Birth", font=Small_Font).grid(row=1, column=2, sticky="e", **pad_options)
        dob_frame = tk.Frame(patient_frame)
        dob_frame.grid(row=1, column=3, sticky="ew", **pad_options)
        dob_frame.columnconfigure(0, weight=1)
        dob_frame.columnconfigure(1, weight=1)
        dob_frame.columnconfigure(2, weight=1)
        dob=fields.get("DOB","1990-01-01").split("-")
        DateOptions = [f"{i:02d}" for i in range(1, 32)]
        Date = tk.StringVar(self)
        Date.set(dob[2] if len(dob) > 2 else DateOptions[0])
        tk.OptionMenu(dob_frame, Date, *DateOptions).grid(row=0, column=0, sticky="ew")

        MonthOptions = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        Month = tk.StringVar(self)
        Month.set(MonthOptions[int(dob[1]) - 1] if len(dob) > 1 else MonthOptions[0])
        tk.OptionMenu(dob_frame, Month, *MonthOptions).grid(row=0, column=1, sticky="ew")

        YearOptions = [str(y) for y in range(1981, 2031)]
        Year = tk.StringVar(self)
        Year.set(dob[0] if len(dob) > 0 else YearOptions[0])
        tk.OptionMenu(dob_frame, Year, *YearOptions).grid(row=0, column=2, sticky="ew")

        tk.Label(patient_frame, text="Trial Activity", font=Small_Font).grid(row=2, column=0, sticky="e", **pad_options)
        TrialActivityOptions = ["Static", "Walking - Fast", "Walking - Heel-Toe", "Running", "Sprinting", 
                                "Stair Ascent", "Stair Descent", "Sit-To-Stand", "Other"]
        TrialActivity = tk.StringVar(self)
        TrialActivity.set(TrialActivityOptions[0])
        tk.OptionMenu(patient_frame, TrialActivity, *TrialActivityOptions).grid(row=2, column=1, sticky="ew", **pad_options)

        tk.Label(patient_frame, text="Trial Modifier", font=Small_Font).grid(row=2, column=2, sticky="e", **pad_options)
        TrialModifierOptions = ["Barefoot", "B AFO-PLS", "L AFO-PLS", "R AFO-PLS", "B AFO-Solid", 
                                "L AFO-Solid", "R AFO-Solid", "B AFO-FR", "L AFO-FR", "R AFO-FR", 
                                "B AFO-Artic", "L AFO-Artic", "R AFO-Artic", "L LIFT", "R LIFT", 
                                "B SMO", "L SMO", "R SMO", "B UCBL", "L UCBL", "R UCBL", "KAFO", 
                                "HKAFO", "RGO", "Parawalker", "Shoes Only", "Other"]
        TrialModifier = tk.StringVar(self)
        TrialModifier.set(TrialModifierOptions[0])
        tk.OptionMenu(patient_frame, TrialModifier, *TrialModifierOptions).grid(row=2, column=3, sticky="ew", **pad_options)

        tk.Label(patient_frame, text="Static Fwd Dir", font=Small_Font).grid(row=3, column=0, sticky="e", **pad_options)
        StaticForwardDirectionOptions = ["+X", "-X", "+Y", "-Y"]
        StaticForwardDirection = tk.StringVar(self)
        if os.path.exists(StaticDataFileName):
            exec(open(StaticDataFileName).read())
        else:
            exec(open(UserPreferencesFileName).read())
        # Safety check if attribute exists after exec
        if not hasattr(self, 'StaticForwardDirection'):
            self.StaticForwardDirection = StaticForwardDirectionOptions[0]
        StaticForwardDirection.set(self.StaticForwardDirection)
        tk.OptionMenu(patient_frame, StaticForwardDirection, *StaticForwardDirectionOptions).grid(row=3, column=1, sticky="ew", **pad_options)

        tk.Label(patient_frame, text="Assistive Device", font=Small_Font).grid(row=3, column=2, sticky="e", **pad_options)
        AssistiveDeviceOptions = ["None", "Walker", "Walker - Wheeled", "Walker - Pickup", "Crutches", 
                                  "Crutches - Axillary", "Crutches - Loftstrand", "Cane", "Bobath Poles", "Hand-Held", "Other"]
        AssistiveDevice = tk.StringVar(self)
        AssistiveDevice.set(AssistiveDeviceOptions[0])
        tk.OptionMenu(patient_frame, AssistiveDevice, *AssistiveDeviceOptions).grid(row=3, column=3, sticky="ew", **pad_options)

        tk.Label(patient_frame, text="Static Frame Num.", font=Small_Font).grid(row=4, column=2, sticky="e", **pad_options)
        StaticFrameNumber = tk.Entry(patient_frame, justify="center")
        StaticFrameNumber.grid(row=4, column=3, sticky="w", **pad_options)

        # --- SECTION 2: Anthropometric Parameters ---
        # Fixed: padding=10 replaced with padx=10, pady=10
        anthro_frame = tk.LabelFrame(parent_frame, text="Anthropometric Parameters", font=Large_Font, padx=10, pady=10)
        anthro_frame.pack(fill="x", expand=True, padx=10, pady=5)
        anthro_frame.columnconfigure(1, weight=1)
        anthro_frame.columnconfigure(3, weight=1)

        tk.Label(anthro_frame, text="Static File", font=Small_Font).grid(row=0, column=0, sticky="e", **pad_options)
        StaticFile = tk.Entry(anthro_frame)
        StaticFile.grid(row=0, column=1, sticky="ew", **pad_options)

        tk.Label(anthro_frame, text="Anthro File", font=Small_Font).grid(row=0, column=2, sticky="e", **pad_options)
        AnthropometricFile = tk.Label(anthro_frame, text="-", font=Smaller_Font)
        AnthropometricFile.grid(row=0, column=3, sticky="w", **pad_options)

        tk.Label(anthro_frame, text="Date Captured", font=Small_Font).grid(row=1, column=0, sticky="e", **pad_options)
        date_col_frame = tk.Frame(anthro_frame)
        date_col_frame.grid(row=1, column=1, columnspan=3, sticky="w", **pad_options)
        
        # Find current date
        now = datetime.datetime.now()
        DataCollectionDate = tk.StringVar(self)
        DataCollectionDate.set(DateOptions[int(now.day) - 1])
        tk.OptionMenu(date_col_frame, DataCollectionDate, *DateOptions).pack(side="left")

        DataCollectionMonth = tk.StringVar(self)
        DataCollectionMonth.set(MonthOptions[int(now.month) - 1])
        tk.OptionMenu(date_col_frame, DataCollectionMonth, *MonthOptions).pack(side="left")

        DataCollectionYearOptions = [str(y) for y in range(1991, 2031)]
        DataCollectionYear = tk.StringVar(self)
        DataCollectionYear.set(YearOptions[int(now.year) - 1981])
        tk.OptionMenu(date_col_frame, DataCollectionYear, *DataCollectionYearOptions).pack(side="left")

        # Basic Measurements
        tk.Label(anthro_frame, text="BodyMass (kg)", font=Small_Font).grid(row=2, column=0, sticky="e", **pad_options)
        BodyMass = tk.Entry(anthro_frame, justify="center")
        BodyMass.grid(row=2, column=1, sticky="w", **pad_options)

        tk.Label(anthro_frame, text="Height (m)", font=Small_Font).grid(row=2, column=2, sticky="e", **pad_options)
        Height = tk.Entry(anthro_frame, justify="center")
        Height.grid(row=2, column=3, sticky="w", **pad_options)

        tk.Label(anthro_frame, text="ASIS-to-ASIS (m)", font=Small_Font).grid(row=3, column=0, sticky="e", **pad_options)
        ASISdist = tk.Entry(anthro_frame, justify="center")
        ASISdist.grid(row=3, column=1, sticky="w", **pad_options)

        # Left / Right Table Header
        tk.Label(anthro_frame, text="Left", font=Bold_Small_Font).grid(row=4, column=1, **pad_options)
        tk.Label(anthro_frame, text="Right", font=Bold_Small_Font).grid(row=4, column=3, **pad_options)

        tk.Label(anthro_frame, text="Leg Length (m)", font=Small_Font).grid(row=5, column=0, sticky="e", **pad_options)
        LeftLegLength = tk.Entry(anthro_frame, justify="center")
        LeftLegLength.grid(row=5, column=1, sticky="ew", **pad_options)
        RightLegLength = tk.Entry(anthro_frame, justify="center")
        RightLegLength.grid(row=5, column=3, sticky="ew", **pad_options)

        tk.Label(anthro_frame, text="Knee Width (m)", font=Small_Font).grid(row=6, column=0, sticky="e", **pad_options)
        LeftKneeWidth = tk.Entry(anthro_frame, justify="center")
        LeftKneeWidth.grid(row=6, column=1, sticky="ew", **pad_options)
        RightKneeWidth = tk.Entry(anthro_frame, justify="center")
        RightKneeWidth.grid(row=6, column=3, sticky="ew", **pad_options)

        tk.Label(anthro_frame, text="Ankle Width (m)", font=Small_Font).grid(row=7, column=0, sticky="e", **pad_options)
        LeftAnkleWidth = tk.Entry(anthro_frame, justify="center")
        LeftAnkleWidth.grid(row=7, column=1, sticky="ew", **pad_options)
        RightAnkleWidth = tk.Entry(anthro_frame, justify="center")
        RightAnkleWidth.grid(row=7, column=3, sticky="ew", **pad_options)

        tk.Label(anthro_frame, text="ASIS-to-GT (m)", font=Small_Font).grid(row=8, column=0, sticky="e", **pad_options)
        LeftASIStoGTdist = tk.Entry(anthro_frame, justify="center")
        LeftASIStoGTdist.grid(row=8, column=1, sticky="ew", **pad_options)
        RightASIStoGTdist = tk.Entry(anthro_frame, justify="center")
        RightASIStoGTdist.grid(row=8, column=3, sticky="ew", **pad_options)

        # --- SECTION 3: Foot Model ---
        # Fixed: padding=10 replaced with padx=10, pady=10
        foot_frame = tk.LabelFrame(parent_frame, text="Foot Model", font=Large_Font, padx=10, pady=10)
        foot_frame.pack(fill="x", expand=True, padx=10, pady=5)
        foot_frame.columnconfigure(1, weight=1)
        foot_frame.columnconfigure(3, weight=1)
        
        # Headers
        self.LeftFootModelCheck = tk.IntVar(value=0)
        self.RightFootModelCheck = tk.IntVar(value=0)
        
        tk.Checkbutton(foot_frame, text="Left", variable=self.LeftFootModelCheck, font=Bold_Small_Font).grid(row=0, column=1, **pad_options)
        tk.Checkbutton(foot_frame, text="Right", variable=self.RightFootModelCheck, font=Bold_Small_Font).grid(row=0, column=3, **pad_options)

        tk.Label(foot_frame, text="Hindfoot Varus/Valgus (deg)", font=Small_Font).grid(row=1, column=0, sticky="e", **pad_options)
        LeftHindfootVarus = tk.Entry(foot_frame, justify="center")
        LeftHindfootVarus.grid(row=1, column=1, sticky="ew", **pad_options)
        RightHindfootVarus = tk.Entry(foot_frame, justify="center")
        RightHindfootVarus.grid(row=1, column=3, sticky="ew", **pad_options)

        tk.Label(foot_frame, text="Calcaneal Pitch (deg)", font=Small_Font).grid(row=2, column=0, sticky="e", **pad_options)
        LeftCalcanealPitch = tk.Entry(foot_frame, justify="center")
        LeftCalcanealPitch.grid(row=2, column=1, sticky="ew", **pad_options)
        RightCalcanealPitch = tk.Entry(foot_frame, justify="center")
        RightCalcanealPitch.grid(row=2, column=3, sticky="ew", **pad_options)

        tk.Label(foot_frame, text="Hindfoot Progression (deg)", font=Small_Font).grid(row=3, column=0, sticky="e", **pad_options)
        LeftHindfootProgression = tk.Entry(foot_frame, justify="center")
        LeftHindfootProgression.grid(row=3, column=1, sticky="ew", **pad_options)
        RightHindfootProgression = tk.Entry(foot_frame, justify="center")
        RightHindfootProgression.grid(row=3, column=3, sticky="ew", **pad_options)

        tk.Label(foot_frame, text="1st Metatarsal Pitch (deg)", font=Small_Font).grid(row=4, column=0, sticky="e", **pad_options)
        LeftFirstMetatarsalPitch = tk.Entry(foot_frame, justify="center")
        LeftFirstMetatarsalPitch.grid(row=4, column=1, sticky="ew", **pad_options)
        RightFirstMetatarsalPitch = tk.Entry(foot_frame, justify="center")
        RightFirstMetatarsalPitch.grid(row=4, column=3, sticky="ew", **pad_options)

        # --- SECTION 4: Special Test Conditions ---
        # Fixed: padding=10 replaced with padx=10, pady=10
        cond_frame = tk.LabelFrame(parent_frame, text="Special Test Conditions", font=Large_Font, padx=10, pady=10)
        cond_frame.pack(fill="x", expand=True, padx=10, pady=5)
        
        # Plantigrade
        tk.Label(cond_frame, text="Subject Plantigrade:", font=Small_Font).grid(row=0, column=0, sticky="e", **pad_options)
        self.LeftPlantigradeCheck = tk.IntVar(value=1)
        self.RightPlantigradeCheck = tk.IntVar(value=1)
        tk.Checkbutton(cond_frame, text="Left", variable=self.LeftPlantigradeCheck, font=Small_Font).grid(row=0, column=1, sticky="w")
        tk.Checkbutton(cond_frame, text="Right", variable=self.RightPlantigradeCheck, font=Small_Font).grid(row=0, column=2, sticky="w")

        # Shod
        self.SubjectShodCheck = tk.IntVar()
        tk.Checkbutton(cond_frame, text="Subject Shod", variable=self.SubjectShodCheck, font=Small_Font).grid(row=1, column=0, sticky="e", **pad_options)
        
        tk.Label(cond_frame, text="Sole Diff (m):", font=Smaller_Font).grid(row=1, column=1, sticky="e")
        
        sole_frame = tk.Frame(cond_frame)
        sole_frame.grid(row=1, column=2, columnspan=2, sticky="w", **pad_options)
        tk.Label(sole_frame, text="L:", font=Small_Font).pack(side="left")
        LeftSoleThickness = tk.Entry(sole_frame, width=5, justify="center")
        LeftSoleThickness.pack(side="left", padx=5)
        tk.Label(sole_frame, text="R:", font=Small_Font).pack(side="left")
        RightSoleThickness = tk.Entry(sole_frame, width=5, justify="center")
        RightSoleThickness.pack(side="left", padx=5)

        # Knee Options
        tk.Label(cond_frame, text="Knee Option:", font=Small_Font).grid(row=2, column=0, sticky="e", **pad_options)
        self.KneeAlignmentCheck = tk.IntVar(value=1)
        tk.Radiobutton(cond_frame, text="KAD", variable=self.KneeAlignmentCheck, value=0, font=Small_Font).grid(row=2, column=1, sticky="w")
        tk.Radiobutton(cond_frame, text="M/L Markers", variable=self.KneeAlignmentCheck, value=1, font=Small_Font).grid(row=2, column=2, sticky="w")

        # Pelvic Fix
        tk.Label(cond_frame, text="Pelvic Fix:", font=Small_Font).grid(row=3, column=0, sticky="e", **pad_options)
        self.PelvicFixCheck = tk.IntVar(value=0)
        pelvic_frame = tk.Frame(cond_frame)
        pelvic_frame.grid(row=3, column=1, columnspan=3, sticky="w", **pad_options)
        tk.Radiobutton(pelvic_frame, text="N/A", variable=self.PelvicFixCheck, value=0, font=Small_Font).pack(side="left", padx=5)
        tk.Radiobutton(pelvic_frame, text="Iliac", variable=self.PelvicFixCheck, value=1, font=Small_Font).pack(side="left", padx=5)
        tk.Radiobutton(pelvic_frame, text="Triad", variable=self.PelvicFixCheck, value=2, font=Small_Font).pack(side="left", padx=5)

        # =========================================================================================
        #       Read Parameters from Nexus or existing Static Parameters File
        # =========================================================================================
        #       Read Parameters from QTM (session.xml) or existing Static Parameters File
        # =========================================================================================
        SubjectName = fields["Name"]
        ID = fields.get("ID", "")
        FilePath, FileName = fields["Path"], fields["Filename"]
        StartFrame, EndFrame = fields["First Frame"], fields["Last Frame"]

        if os.path.exists(StaticDataFileName):
            # Execute Static File to read stored parameters values
            exec(open(StaticDataFileName).read())
            TrialActivity.set(getattr(self, "valueTrialActivity", TrialActivityOptions[0]))
            TrialModifier.set(getattr(self, "valueTrialModifier", TrialModifierOptions[0]))
            AssistiveDevice.set(getattr(self, "valueAssistiveDevice", AssistiveDeviceOptions[0]))
            self.LeftFootModelCheck.set(getattr(self, "valueLeftFootModelCheck", 0))
            self.RightFootModelCheck.set(getattr(self, "valueRightFootModelCheck", 0))
            if hasattr(self, "valueLeftHindfootVarus"):
                LeftHindfootVarus.insert(0, self.valueLeftHindfootVarus)
            if hasattr(self, "valueRightHindfootVarus"):
                RightHindfootVarus.insert(0, self.valueRightHindfootVarus)
            if hasattr(self, "valueLeftHindfootProgression"):
                LeftHindfootProgression.insert(0, self.valueLeftHindfootProgression)
            if hasattr(self, "valueRightHindfootProgression"):
                RightHindfootProgression.insert(0, self.valueRightHindfootProgression)
            if hasattr(self, "valueLeftFirstMetatarsalPitch"):
                LeftFirstMetatarsalPitch.insert(0, self.valueLeftFirstMetatarsalPitch)
            if hasattr(self, "valueRightFirstMetatarsalPitch"):
                RightFirstMetatarsalPitch.insert(0, self.valueRightFirstMetatarsalPitch)
            if hasattr(self, "valueLeftCalcanealPitch"):
                LeftCalcanealPitch.insert(0, self.valueLeftCalcanealPitch)
            if hasattr(self, "valueRightCalcanealPitch"):
                RightCalcanealPitch.insert(0, self.valueRightCalcanealPitch)
            self.LeftPlantigradeCheck.set(getattr(self, "valueLeftPlantigradeCheck", 1))
            self.RightPlantigradeCheck.set(getattr(self, "valueRightPlantigradeCheck", 1))
            if getattr(self, "valueSujectShodCheck", "0") == "1":
                self.SubjectShodCheck.set(self.valueSujectShodCheck)
                LeftSoleThickness.insert(0, getattr(self, "valueLeftSoleThickness", "0"))
                RightSoleThickness.insert(0, getattr(self, "valueRightSoleThickness", "0"))
            self.PelvicFixCheck.set(getattr(self, "valuePelvicFixCheck", 0))
            try:
                self.KneeAlignmentCheck.set(self.valueKneeAlignmentCheck)
            except:
                self.KneeAlignmentCheck.set("0")
            try:
                StaticFrameNumber.insert(0, self.valueStaticFrameNumber)
            except:
                StaticFrameNumber.insert(0, StartFrame + 20)
        else:
            StaticFrameNumber.insert(0, StartFrame + 20)  # Default to 20th frame.
            # Read Foot Model Parameters
            if "LeftVarValAngle" in fields and fields["LeftVarValAngle"] is not None:
                LeftHindfootVarus.insert(0, int(round(fields["LeftVarValAngle"], 0)))
                self.LeftFootModelCheck.set("1")
            if "RightVarValAngle" in fields and fields["RightVarValAngle"] is not None:
                RightHindfootVarus.insert(0, int(round(fields["RightVarValAngle"], 0)))
                self.RightFootModelCheck.set("1")
            if "Left1stRayPitch" in fields and fields["Left1stRayPitch"] is not None:
                LeftFirstMetatarsalPitch.insert(0, int(fields["Left1stRayPitch"]))
            if "Right1stRayPitch" in fields and fields["Right1stRayPitch"] is not None:
                RightFirstMetatarsalPitch.insert(0, int(fields["Right1stRayPitch"]))
            if (
                "LeftCalcanealPitch" in fields
                and fields["LeftCalcanealPitch"] is not None
            ):
                LeftCalcanealPitch.insert(0, int(fields["LeftCalcanealPitch"]))
            if (
                "RightCalcanealPitch" in fields
                and fields["RightCalcanealPitch"] is not None
            ):
                RightCalcanealPitch.insert(0, int(fields["RightCalcanealPitch"]))

            # Read Calcaneal Pitch and Varus Valgus from Sitting Foot Static, if exists
            if os.path.exists(SittingFootStaticDataFileName):
                exec(open(SittingFootStaticDataFileName).read())
                LeftCalcanealPitch.delete(0, tk.END)
                RightCalcanealPitch.delete(0, tk.END)
                LeftCalcanealPitch.insert(0, self.valueLeftCalcanealPitch)
                RightCalcanealPitch.insert(0, self.valueRightCalcanealPitch)

                LeftHindfootVarus.delete(0, tk.END)
                RightHindfootVarus.delete(0, tk.END)
                LeftHindfootVarus.insert(0, self.valueLeftHindfootVarus)
                RightHindfootVarus.insert(0, self.valueRightHindfootVarus)

                LeftHindfootProgression.delete(0, tk.END)
                RightHindfootProgression.delete(0, tk.END)
                try:
                    LeftHindfootProgression.insert(0, self.valueLeftHindfootProgression)
                except:
                    pass
                try:
                    RightHindfootProgression.insert(0, self.valueRightHindfootProgression)
                except:
                    pass

        # Static File & Anthro File display
        StaticFile.insert(0, FileName)
        AnthropometricFile["text"] = getattr(
            self, "valueAnthropometricFile", "Static_" + TestingCondition + "_" + SubjectName
        )

        # Patient Info (ID / Name)
        local_saved = self.parent._headless and getattr(self, "valueMeasurementUnits", "") == "m"
        if local_saved and hasattr(self, "valuePatientNumber"):
            PatientNumber.insert(0, self.valuePatientNumber)
        elif ID:
            PatientNumber.insert(0, ID)
        elif hasattr(self, "valuePatientNumber") and self.valuePatientNumber:
            PatientNumber.insert(0, self.valuePatientNumber)
        else:
            PatientNumber.insert(0, SubjectName)

        if hasattr(self, "valueFirstName") and (self.valueFirstName or local_saved):
            FirstName.insert(0, self.valueFirstName)
        else:
            FirstName.insert(0, SubjectName)

        if hasattr(self, "valueLastName") and self.valueLastName:
            LastName.insert(0, self.valueLastName)

        # Date Captured
        creation_date = fields.get("Creation date") or fields.get("Creation_date")
        date_captured_set = False
        if creation_date:
            try:
                dt = datetime.datetime.strptime(str(creation_date).strip()[:10], "%Y-%m-%d")
                DataCollectionDate.set(DateOptions[dt.day - 1])
                DataCollectionMonth.set(MonthOptions[dt.month - 1])
                DataCollectionYear.set(str(dt.year))
                date_captured_set = True
            except Exception:
                pass
        if not date_captured_set:
            SystemFileName = FileName + ".c3d"
            try:
                now = datetime.datetime.fromtimestamp(
                    os.path.getmtime(os.path.join(FilePath, SystemFileName))
                )
                DataCollectionDate.set(DateOptions[int(now.day) - 1])
                DataCollectionMonth.set(MonthOptions[int(now.month) - 1])
                DataCollectionYear.set(YearOptions[int(now.year) - 1981])
                date_captured_set = True
            except Exception:
                pass
        if not date_captured_set and hasattr(self, "valueDataCollectionDate_Day"):
            DataCollectionDate.set(self.valueDataCollectionDate_Day)
            DataCollectionMonth.set(self.valueDataCollectionDate_Month)
            DataCollectionYear.set(self.valueDataCollectionDate_Year)

        if local_saved:
            for variable, name in ((Date, "valueDateOfBirth_Day"), (Month, "valueDateOfBirth_Month"),
                                   (Year, "valueDateOfBirth_Year"), (DataCollectionDate, "valueDataCollectionDate_Day"),
                                   (DataCollectionMonth, "valueDataCollectionDate_Month"),
                                   (DataCollectionYear, "valueDataCollectionDate_Year")):
                if hasattr(self, name):
                    variable.set(getattr(self, name))

        # Headless GUI runs prioritize reviewed local measurements; legacy runs retain their fallback.
        def get_qtm_or_persisted(field_key, persisted_attr, is_mass=False):
            if self.parent._headless and getattr(self, "valueMeasurementUnits", "") == "m" and hasattr(self, persisted_attr):
                # GUI Save & Run uses the reviewed local calibration, not stale export values.
                return getattr(self, persisted_attr)
            qtm_val = fields.get(field_key)
            if qtm_val is not None:
                try:
                    num_val = float(qtm_val)
                    if num_val > 0:
                        return round(num_val, 2) if is_mass else qtm_measurement_to_meters(num_val)
                except (ValueError, TypeError):
                    pass
            if hasattr(self, persisted_attr):
                val = getattr(self, persisted_attr)
                if val is not None and str(val).strip() != "":
                    try:
                        return round(float(val), 2) if is_mass else persisted_measurement_to_meters(val)
                    except (ValueError, TypeError):
                        return val
            return ""

        body_mass_val = get_qtm_or_persisted("Bodymass", "valueBodyMass", is_mass=True)
        if not body_mass_val:
            body_mass_val = get_qtm_or_persisted("BodyMass", "valueBodyMass", is_mass=True)
        if body_mass_val != "":
            BodyMass.insert(0, body_mass_val)

        for widget, f_key, p_attr in [
            (Height, "Height", "valueHeight"),
            (ASISdist, "InterAsisDistance", "valueASISdist"),
            (LeftLegLength, "LeftLegLength", "valueLeftLegLength"),
            (RightLegLength, "RightLegLength", "valueRightLegLength"),
            (LeftKneeWidth, "LeftKneeWidth", "valueLeftKneeWidth"),
            (RightKneeWidth, "RightKneeWidth", "valueRightKneeWidth"),
            (LeftAnkleWidth, "LeftAnkleWidth", "valueLeftAnkleWidth"),
            (RightAnkleWidth, "RightAnkleWidth", "valueRightAnkleWidth"),
            (LeftASIStoGTdist, "LeftAsisTrocanterDistance", "valueLeftASIStoGTdist"),
            (RightASIStoGTdist, "RightAsisTrocanterDistance", "valueRightASIStoGTdist"),
        ]:
            val = get_qtm_or_persisted(f_key, p_attr)
            if val != "":
                widget.insert(0, val)

        # AFO Condition- Populate Subject Information from Barefoot
        if TestingCondition != DefaultTestingCondition:
            _default_calib = os.path.join(
                FilePath,
                "Calibration",
                "Static_"
                + DefaultTestingCondition
                + "_"
                + SubjectName
                + ".py",
            )
            if os.path.exists(_default_calib):
                DefaultStaticDataFileName = _default_calib
            else:
                DefaultStaticDataFileName = (
                    FilePath
                    + "Static_"
                    + DefaultTestingCondition
                    + "_"
                    + SubjectName
                    + ".py"
                )
            if os.path.exists(DefaultStaticDataFileName):
                exec(open(DefaultStaticDataFileName).read())
                # Clear Widgets before overwriting
                FirstName.delete(0, tk.END)
                LastName.delete(0, tk.END)
                PatientNumber.delete(0, tk.END)
                BodyMass.delete(0, tk.END)
                Height.delete(0, tk.END)
                ASISdist.delete(0, tk.END)
                LeftLegLength.delete(0, tk.END)
                RightLegLength.delete(0, tk.END)
                # Put in stored values onto display
                FirstName.insert(0, self.valueFirstName)
                LastName.insert(0, self.valueLastName)
                PatientNumber.insert(0, self.valuePatientNumber)
                #Date.set(self.valueDateOfBirth_Day)
                #Month.set(self.valueDateOfBirth_Month)
                #Year.set(self.valueDateOfBirth_Year)
                DataCollectionDate.set(self.valueDataCollectionDate_Day)
                DataCollectionMonth.set(self.valueDataCollectionDate_Month)
                DataCollectionYear.set(self.valueDataCollectionDate_Year)
                BodyMass.insert(0, self.valueBodyMass)
                Height.insert(0, persisted_measurement_to_meters(self.valueHeight))
                ASISdist.insert(0, persisted_measurement_to_meters(self.valueASISdist))
                LeftLegLength.insert(0, persisted_measurement_to_meters(self.valueLeftLegLength))
                RightLegLength.insert(0, persisted_measurement_to_meters(self.valueRightLegLength))

        # =============================================================================
        #       Function to save Subject parameters
        # =============================================================================
        def saveSubjectData():
            if os.path.exists(StaticDataFileName):
                # Read Current File
                StaticDataFile = open(StaticDataFileName, "r")
                lines = StaticDataFile.readlines()
                StaticDataFile.close()

                # Open Static py File
                StaticDataFile = open(StaticDataFileName, "w+")
                # Restore the UserPreferences
                UserPreferencesBlockEnds = 0
                for line in lines:
                    words = line.split()
                    # SAFETY CHECK: skip empty lines to prevent crash
                    if len(words) == 0:
                        StaticDataFile.write(line)
                        continue
                        
                    if words[0] == "self.valueFirstName":
                        UserPreferencesBlockEnds = 1
                    if UserPreferencesBlockEnds == 0:
                        if words[0] == "self.StaticForwardDirection":
                            StaticDataFile.write(
                                "self.StaticForwardDirection = "
                                + "'"
                                + StaticForwardDirection.get()
                                + "'\n"
                            )
                        else:
                            StaticDataFile.write(line)

                # Write Subject Data into Static Anthropometric File
                write_setting(StaticDataFile, "valueFirstName", FirstName.get())
                write_setting(StaticDataFile, "valueLastName", LastName.get())
                write_setting(StaticDataFile, "valuePatientNumber", PatientNumber.get())
                if hasattr(self, "valueSex"):
                    write_setting(StaticDataFile, "valueSex", self.valueSex)
                StaticDataFile.write("self.valueDateOfBirth_Day = " + "'" + Date.get() + "'" + "\n")
                StaticDataFile.write("self.valueDateOfBirth_Month = " + "'" + Month.get() + "'" + "\n")
                StaticDataFile.write("self.valueDateOfBirth_Year = " + "'" + Year.get() + "'" + "\n")
                StaticDataFile.write("self.valueTrialActivity = " + "'" + TrialActivity.get() + "'" + "\n")
                StaticDataFile.write("self.valueTrialModifier = " + "'" + TrialModifier.get() + "'" + "\n")
                StaticDataFile.write("self.valueAssistiveDevice = " + "'" + AssistiveDevice.get() + "'" + "\n")
                StaticDataFile.write("self.valueStaticFile = " + "'" + StaticFile.get() + "'" + "\n")
                StaticDataFile.write("self.valueAnthropometricFile = " + "'" + "Static_" + TestingCondition + "_" + SubjectName + "'" + "\n")
                StaticDataFile.write("self.valueDataCollectionDate_Day = " + "'" + DataCollectionDate.get() + "'" + "\n")
                StaticDataFile.write("self.valueDataCollectionDate_Month = " + "'" + DataCollectionMonth.get() + "'" + "\n")
                StaticDataFile.write("self.valueDataCollectionDate_Year = " + "'" + DataCollectionYear.get() + "'" + "\n")
                write_setting(StaticDataFile, "valueBodyMass", BodyMass.get() if local_saved else float(BodyMass.get()))
                if getattr(self, "valueMeasurementUnits", "") == "m":
                    write_setting(StaticDataFile, "valueMeasurementUnits", "m")
                write_setting(StaticDataFile, "valueHeight", Height.get())
                write_setting(StaticDataFile, "valueASISdist", ASISdist.get())
                write_setting(StaticDataFile, "valueLeftLegLength", LeftLegLength.get())
                write_setting(StaticDataFile, "valueRightLegLength", RightLegLength.get())
                write_setting(StaticDataFile, "valueLeftKneeWidth", LeftKneeWidth.get())
                write_setting(StaticDataFile, "valueRightKneeWidth", RightKneeWidth.get())
                write_setting(StaticDataFile, "valueLeftAnkleWidth", LeftAnkleWidth.get())
                write_setting(StaticDataFile, "valueRightAnkleWidth", RightAnkleWidth.get())
                write_setting(StaticDataFile, "valueLeftASIStoGTdist", LeftASIStoGTdist.get())
                write_setting(StaticDataFile, "valueRightASIStoGTdist", RightASIStoGTdist.get())
                StaticDataFile.write("self.valueLeftFootModelCheck = " + "'" + str(self.LeftFootModelCheck.get()) + "'" + "\n")
                StaticDataFile.write("self.valueRightFootModelCheck = " + "'" + str(self.RightFootModelCheck.get()) + "'" + "\n")
                StaticDataFile.write("self.valueLeftHindfootVarus = " + "'" + LeftHindfootVarus.get() + "'" + "\n")
                StaticDataFile.write("self.valueLeftCalcanealPitch = " + "'" + LeftCalcanealPitch.get() + "'" + "\n")
                StaticDataFile.write("self.valueLeftHindfootProgression = " + "'" + LeftHindfootProgression.get() + "'" + "\n")
                StaticDataFile.write("self.valueLeftFirstMetatarsalPitch = " + "'" + LeftFirstMetatarsalPitch.get() + "'" + "\n")
                StaticDataFile.write("self.valueRightHindfootVarus = " + "'" + RightHindfootVarus.get() + "'" + "\n")
                StaticDataFile.write("self.valueRightCalcanealPitch = " + "'" + RightCalcanealPitch.get() + "'" + "\n")
                StaticDataFile.write("self.valueRightHindfootProgression = " + "'" + RightHindfootProgression.get() + "'" + "\n")
                StaticDataFile.write("self.valueRightFirstMetatarsalPitch = " + "'" + RightFirstMetatarsalPitch.get() + "'" + "\n")
                StaticDataFile.write("self.valueLeftPlantigradeCheck = " + "'" + str(self.LeftPlantigradeCheck.get()) + "'" + "\n")
                StaticDataFile.write("self.valueRightPlantigradeCheck = " + "'" + str(self.RightPlantigradeCheck.get()) + "'" + "\n")
                StaticDataFile.write("self.valueSujectShodCheck = " + "'" + str(self.SubjectShodCheck.get()) + "'" + "\n")
                if str(self.SubjectShodCheck.get()) == "1":
                    write_setting(StaticDataFile, "valueLeftSoleThickness", LeftSoleThickness.get())
                    write_setting(StaticDataFile, "valueRightSoleThickness", RightSoleThickness.get())
                else:
                    write_setting(StaticDataFile, "valueLeftSoleThickness", "0")
                    write_setting(StaticDataFile, "valueRightSoleThickness", "0")
                StaticDataFile.write("self.valuePelvicFixCheck = " + "'" + str(self.PelvicFixCheck.get()) + "'" + "\n")
                StaticDataFile.write("self.valueKneeAlignmentCheck = " + "'" + str(self.KneeAlignmentCheck.get()) + "'" + "\n")
                StaticDataFile.write("self.valueStaticFrameNumber = " + "'" + str(StaticFrameNumber.get()) + "'" + "\n")
                
                # If File Exists, then restore the Transformation Matrices Section
                PatientInformationBlockEnds = 0
                for line in lines:
                    words = line.split()
                    
                    if len(words) >= 2:
                        if words[0] == "#" and words[1] == "Pelfix":
                            PatientInformationBlockEnds = 1
                        elif words[0] == "#" and words[1] == "Transformation":
                            PatientInformationBlockEnds = 1
                    
                    if PatientInformationBlockEnds == 1:
                        StaticDataFile.write(line)
                StaticDataFile.close()
            else:
                # Open Static py file
                StaticDataFile = open(StaticDataFileName, "w+")
                # Copy User Preferences
                UserPreferencesFile = open(UserPreferencesFileName, "r")
                lines = UserPreferencesFile.readlines()
                UserPreferencesFile.close()
                for line in lines:
                    words = line.split()
                    # SAFETY CHECK: skip empty lines
                    if len(words) == 0:
                        StaticDataFile.write(line)
                        continue
                        
                    if words[0] == "self.StaticForwardDirection":
                        StaticDataFile.write("self.StaticForwardDirection = " + "'" + StaticForwardDirection.get() + "'\n")
                    else:
                        StaticDataFile.write(line)
                
                # Write Subject Data into Static Anthropometric File (New File logic)
                write_setting(StaticDataFile, "valueFirstName", FirstName.get())
                write_setting(StaticDataFile, "valueLastName", LastName.get())
                write_setting(StaticDataFile, "valuePatientNumber", PatientNumber.get())
                if hasattr(self, "valueSex"):
                    write_setting(StaticDataFile, "valueSex", self.valueSex)
                StaticDataFile.write("self.valueDateOfBirth_Day = " + "'" + Date.get() + "'" + "\n")
                StaticDataFile.write("self.valueDateOfBirth_Month = " + "'" + Month.get() + "'" + "\n")
                StaticDataFile.write("self.valueDateOfBirth_Year = " + "'" + Year.get() + "'" + "\n")
                StaticDataFile.write("self.valueTrialActivity = " + "'" + TrialActivity.get() + "'" + "\n")
                StaticDataFile.write("self.valueTrialModifier = " + "'" + TrialModifier.get() + "'" + "\n")
                StaticDataFile.write("self.valueAssistiveDevice = " + "'" + AssistiveDevice.get() + "'" + "\n")
                StaticDataFile.write("self.valueStaticFile = " + "'" + StaticFile.get() + "'" + "\n")
                StaticDataFile.write("self.valueAnthropometricFile = " + "'" + "Static_" + TestingCondition + "_" + SubjectName + "'" + "\n")
                StaticDataFile.write("self.valueDataCollectionDate_Day = " + "'" + DataCollectionDate.get() + "'" + "\n")
                StaticDataFile.write("self.valueDataCollectionDate_Month = " + "'" + DataCollectionMonth.get() + "'" + "\n")
                StaticDataFile.write("self.valueDataCollectionDate_Year = " + "'" + DataCollectionYear.get() + "'" + "\n")
                write_setting(StaticDataFile, "valueBodyMass", BodyMass.get() if local_saved else float(BodyMass.get()))
                if getattr(self, "valueMeasurementUnits", "") == "m":
                    write_setting(StaticDataFile, "valueMeasurementUnits", "m")
                write_setting(StaticDataFile, "valueHeight", Height.get())
                write_setting(StaticDataFile, "valueASISdist", ASISdist.get())
                write_setting(StaticDataFile, "valueLeftLegLength", LeftLegLength.get())
                write_setting(StaticDataFile, "valueRightLegLength", RightLegLength.get())
                write_setting(StaticDataFile, "valueLeftKneeWidth", LeftKneeWidth.get())
                write_setting(StaticDataFile, "valueRightKneeWidth", RightKneeWidth.get())
                write_setting(StaticDataFile, "valueLeftAnkleWidth", LeftAnkleWidth.get())
                write_setting(StaticDataFile, "valueRightAnkleWidth", RightAnkleWidth.get())
                write_setting(StaticDataFile, "valueLeftASIStoGTdist", LeftASIStoGTdist.get())
                write_setting(StaticDataFile, "valueRightASIStoGTdist", RightASIStoGTdist.get())
                StaticDataFile.write("self.valueLeftFootModelCheck = " + "'" + str(self.LeftFootModelCheck.get()) + "'" + "\n")
                StaticDataFile.write("self.valueRightFootModelCheck = " + "'" + str(self.RightFootModelCheck.get()) + "'" + "\n")
                StaticDataFile.write("self.valueLeftHindfootVarus = " + "'" + LeftHindfootVarus.get() + "'" + "\n")
                StaticDataFile.write("self.valueLeftCalcanealPitch = " + "'" + LeftCalcanealPitch.get() + "'" + "\n")
                StaticDataFile.write("self.valueLeftHindfootProgression = " + "'" + LeftHindfootProgression.get() + "'" + "\n")
                StaticDataFile.write("self.valueLeftFirstMetatarsalPitch = " + "'" + LeftFirstMetatarsalPitch.get() + "'" + "\n")
                StaticDataFile.write("self.valueRightHindfootVarus = " + "'" + RightHindfootVarus.get() + "'" + "\n")
                StaticDataFile.write("self.valueRightCalcanealPitch = " + "'" + RightCalcanealPitch.get() + "'" + "\n")
                StaticDataFile.write("self.valueRightHindfootProgression = " + "'" + RightHindfootProgression.get() + "'" + "\n")
                StaticDataFile.write("self.valueRightFirstMetatarsalPitch = " + "'" + RightFirstMetatarsalPitch.get() + "'" + "\n")
                StaticDataFile.write("self.valueLeftPlantigradeCheck = " + "'" + str(self.LeftPlantigradeCheck.get()) + "'" + "\n")
                StaticDataFile.write("self.valueRightPlantigradeCheck = " + "'" + str(self.RightPlantigradeCheck.get()) + "'" + "\n")
                StaticDataFile.write("self.valueSujectShodCheck = " + "'" + str(self.SubjectShodCheck.get()) + "'" + "\n")
                if str(self.SubjectShodCheck.get()) == "1":
                    write_setting(StaticDataFile, "valueLeftSoleThickness", LeftSoleThickness.get())
                    write_setting(StaticDataFile, "valueRightSoleThickness", RightSoleThickness.get())
                else:
                    write_setting(StaticDataFile, "valueLeftSoleThickness", "0")
                    write_setting(StaticDataFile, "valueRightSoleThickness", "0")
                StaticDataFile.write("self.valuePelvicFixCheck = " + "'" + str(self.PelvicFixCheck.get()) + "'" + "\n")
                StaticDataFile.write("self.valueKneeAlignmentCheck = " + "'" + str(self.KneeAlignmentCheck.get()) + "'" + "\n")
                StaticDataFile.write("self.valueStaticFrameNumber = " + "'" + str(StaticFrameNumber.get()) + "'" + "\n")
                
                # If File Exists, then restore the Transformation Matrices Section
                PatientInformationBlockEnds = 0
                for line in lines:
                    words = line.split()
                    
                    if len(words) >= 2:
                        if words[0] == "#" and words[1] == "Pelfix":
                            PatientInformationBlockEnds = 1
                        elif words[0] == "#" and words[1] == "Transformation":
                            PatientInformationBlockEnds = 1
                    
                    if PatientInformationBlockEnds == 1:
                        StaticDataFile.write(line)
                StaticDataFile.close()


class QAreport_Page(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.grid(sticky="nsew")

        # Configure grid weights for responsiveness
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create scrollable canvas
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # Create inner frame
        self.inner_frame = tk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        # Event bindings
        self.inner_frame.bind("<Configure>", self._configure_inner)
        self.canvas.bind("<Configure>", self._configure_canvas)
        self.bind("<Enter>", self._bind_mousewheel)
        self.bind("<Leave>", self._unbind_mousewheel)

    def _configure_inner(self, event):
        pass  # Scroll region handled by PySide6

    def _configure_canvas(self, event):
        if self.inner_frame.winfo_width() != event.width:
            self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def HasTrajectory(self, subjectName, markerName):
        return markerName in fields

    def build_UI(self):
        # Clear existing widgets in inner_frame
        # Clear existing widgets

        if self.inner_frame.layout():

            old = self.inner_frame.layout()

            while old.count():

                item = old.takeAt(0)

                if item.widget():

                    item.widget().deleteLater()

                elif item.layout():

                    while item.layout().count():

                        sub = item.layout().takeAt(0)

                        if sub.widget():

                            sub.widget().deleteLater()

        self._inner_layout = QVBoxLayout(self.inner_frame) if not self.inner_frame.layout() else self.inner_frame.layout()

        # =============================================================================
        # Layout Configuration
        # =============================================================================
        # Layout columns handled by inner layout
        

        # Create Content Frame
        ContentFrame = tk.Frame(self.inner_frame)
        ContentFrame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        ContentFrame.columnconfigure(0, weight=1)

        # Create Button Frame
        ButtonFrame = tk.Frame(self.inner_frame, bg="SystemButtonFace")
        ButtonFrame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Buttons
        ProceedButton = tk.Button(
            ButtonFrame,
            text="Proceed",
            font=Small_Font,
            command=lambda: [
                self.parent._stack.setCurrentWidget(self.parent.frames[StaticSubjectCalibrationReport_Page]),
                self.parent.frames[StaticSubjectCalibrationReport_Page].build_UI(),
            ],
        )
        ProceedButton.pack(side="top", pady=20, ipadx=5, ipady=5, fill="x")

        BackButton = tk.Button(
            ButtonFrame,
            text="Back",
            font=Small_Font,
            command=lambda: [
                self.parent._stack.setCurrentWidget(self.parent.frames[PatientInfo_Page]),
                self.parent.frames[PatientInfo_Page].build_UI(),
                ErrorMessagesLabel.place_forget(),
                ErrorMessagesText.place_forget(),
            ],
        )
        BackButton.pack(side="top", pady=5, ipadx=5, ipady=5, fill="x")

        QuitButton = tk.Button(
            ButtonFrame, text="Quit", font=Small_Font, command=lambda: quit()
        )
        QuitButton.pack(side="top", pady=20, ipadx=5, ipady=5, fill="x")

        # =============================================================================
        # Patient Information Section
        # =============================================================================
        # Get file path and name from Nexus
        SubjectName = fields["Name"]
        FilePath, FileName = fields["Path"], fields["Filename"]

        InfoFrame = tk.Frame(ContentFrame)
        InfoFrame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        InfoFrame.columnconfigure(1, weight=1)

        tk.Label(InfoFrame, text="Static File-", font=Small_Font).grid(row=0, column=0, sticky="w", padx=5)
        tk.Label(InfoFrame, text=str(FileName + ".c3d"), font=Small_Font).grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(InfoFrame, text="Model-", font=Small_Font).grid(row=1, column=0, sticky="w", padx=5)
        FilePath, FileName = fields["Path"], fields["Filename"]
        tk.Label(InfoFrame, text="Shriners Gait Model", font=Small_Font).grid(row=1, column=1, sticky="w", padx=5)

        tk.Label(InfoFrame, text="User Preference", font=Small_Font).grid(row=2, column=0, sticky="w", padx=5)
        tk.Label(InfoFrame, text=UserPreferencesFileName, font=Smaller_Font, anchor="w").grid(row=2, column=1, sticky="w", padx=5)

        # Warnings Area
        WarningFrame = tk.LabelFrame(ContentFrame, text="Warnings", font=Bold_Small_Font, fg="red")
        WarningFrame.grid(row=1, column=0, sticky="ew", pady=10)
        WarningFrame.columnconfigure(0, weight=1)

        # Create Error Label and Text widgets (Globally accessible as they are used in MarkerCheck)
        # Defining without global, assuming closure scope works for nested MarkerCheck
        ErrorMessagesLabel = tk.Label(WarningFrame, text="", font=Bold_Small_Font, fg="red") 
        
        ErrorMessagesText = tk.Text(WarningFrame, height=5, state="disabled", fg="red", bg="#f0f0f0") 
        ErrorMessagesText.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # =============================================================================
        # Clinical Exam - Marker Data Section
        # =============================================================================
        ClinicalFrame = tk.LabelFrame(ContentFrame, text="Clinical Exam - Marker Data", font=Large_Font)
        ClinicalFrame.grid(row=2, column=0, sticky="nsew", pady=10)
        for i in range(5): ClinicalFrame.columnconfigure(i, weight=1)

        # Headers
        tk.Label(ClinicalFrame, text="Clinical", font=Small_Font).grid(row=0, column=1)
        tk.Label(ClinicalFrame, text="Markers", font=Small_Font).grid(row=0, column=2)
        tk.Label(ClinicalFrame, text="Difference", font=Small_Font).grid(row=0, column=3)

        # Rows
        row_idx = 1
        pad_opts = {'padx': 5, 'pady': 5}
        
        # ASIS
        tk.Label(ClinicalFrame, text="ASIS-to-ASIS Distance (m)", font=Small_Font).grid(row=row_idx, column=0, sticky="e", **pad_opts)
        ASISdistClinical = tk.Label(ClinicalFrame, text="-", font=Small_Font)
        ASISdistClinical.grid(row=row_idx, column=1, **pad_opts)
        ASISdistMarkers = tk.Label(ClinicalFrame, text="-", font=Small_Font)
        ASISdistMarkers.grid(row=row_idx, column=2, **pad_opts)
        ASISdistDiff = tk.Entry(ClinicalFrame, justify="center", width=10)
        ASISdistDiff.grid(row=row_idx, column=3, **pad_opts)
        row_idx += 1

        # Knee Width Left
        tk.Label(ClinicalFrame, text="Knee Width (m)- Left", font=Small_Font).grid(row=row_idx, column=0, sticky="e", **pad_opts)
        LeftKneeWidthClinical = tk.Label(ClinicalFrame, text="-", font=Small_Font)
        LeftKneeWidthClinical.grid(row=row_idx, column=1, **pad_opts)
        LeftKneeWidthMarkers = tk.Label(ClinicalFrame, text="-", font=Small_Font)
        LeftKneeWidthMarkers.grid(row=row_idx, column=2, **pad_opts)
        LeftKneeWidthDiff = tk.Entry(ClinicalFrame, justify="center", width=10)
        LeftKneeWidthDiff.grid(row=row_idx, column=3, **pad_opts)
        row_idx += 1

        # Knee Width Right
        tk.Label(ClinicalFrame, text="Knee Width (m)- Right", font=Small_Font).grid(row=row_idx, column=0, sticky="e", **pad_opts)
        RightKneeWidthClinical = tk.Label(ClinicalFrame, text="-", font=Small_Font)
        RightKneeWidthClinical.grid(row=row_idx, column=1, **pad_opts)
        RightKneeWidthMarkers = tk.Label(ClinicalFrame, text="-", font=Small_Font)
        RightKneeWidthMarkers.grid(row=row_idx, column=2, **pad_opts)
        RightKneeWidthDiff = tk.Entry(ClinicalFrame, justify="center", width=10)
        RightKneeWidthDiff.grid(row=row_idx, column=3, **pad_opts)
        row_idx += 1

        # Ankle Width Left
        tk.Label(ClinicalFrame, text="Ankle Width (m)- Left", font=Small_Font).grid(row=row_idx, column=0, sticky="e", **pad_opts)
        LeftAnkleWidthClinical = tk.Label(ClinicalFrame, text="-", font=Small_Font)
        LeftAnkleWidthClinical.grid(row=row_idx, column=1, **pad_opts)
        LeftAnkleWidthMarkers = tk.Label(ClinicalFrame, text="-", font=Small_Font)
        LeftAnkleWidthMarkers.grid(row=row_idx, column=2, **pad_opts)
        LeftAnkleWidthDiff = tk.Entry(ClinicalFrame, justify="center", width=10)
        LeftAnkleWidthDiff.grid(row=row_idx, column=3, **pad_opts)
        row_idx += 1

        # Ankle Width Right
        tk.Label(ClinicalFrame, text="Ankle Width (m)- Right", font=Small_Font).grid(row=row_idx, column=0, sticky="e", **pad_opts)
        RightAnkleWidthClinical = tk.Label(ClinicalFrame, text="-", font=Small_Font)
        RightAnkleWidthClinical.grid(row=row_idx, column=1, **pad_opts)
        RightAnkleWidthMarkers = tk.Label(ClinicalFrame, text="-", font=Small_Font)
        RightAnkleWidthMarkers.grid(row=row_idx, column=2, **pad_opts)
        RightAnkleWidthDiff = tk.Entry(ClinicalFrame, justify="center", width=10)
        RightAnkleWidthDiff.grid(row=row_idx, column=3, **pad_opts)
        row_idx += 1

        # =============================================================================
        # Knee Alignment Fixture Marker Data Section
        # =============================================================================
        KADFrame = tk.LabelFrame(ContentFrame, text="Knee Alignment Fixture Marker Data", font=Large_Font)
        KADFrame.grid(row=3, column=0, sticky="nsew", pady=10)
        KADFrame.columnconfigure(1, weight=1) # Left col
        KADFrame.columnconfigure(2, weight=1) # Right col

        # Sub-header: Distance
        tk.Label(KADFrame, text="Inter Markers Distance (m)", font=Bold_Small_Font).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        # Headers
        tk.Label(KADFrame, text="Left", font=Small_Font).grid(row=1, column=1)
        tk.Label(KADFrame, text="Range", font=Small_Font).grid(row=1, column=2, sticky="w") # Align close to left column
        tk.Label(KADFrame, text="Right", font=Small_Font).grid(row=1, column=3)
        tk.Label(KADFrame, text="Range", font=Small_Font).grid(row=1, column=4, sticky="w")

        row_idx = 2
        
        # Upper & Lateral
        tk.Label(KADFrame, text="Upper & Lateral Marker", font=Small_Font).grid(row=row_idx, column=0, sticky="e", **pad_opts)
        LeftUpperLateral = tk.Label(KADFrame, text="-", font=Small_Font)
        LeftUpperLateral.grid(row=row_idx, column=1, **pad_opts)
        RightUpperLateral = tk.Label(KADFrame, text="-", font=Small_Font)
        RightUpperLateral.grid(row=row_idx, column=3, **pad_opts)
        row_idx += 1

        # Upper & Lower
        tk.Label(KADFrame, text="Upper & Lower Marker", font=Small_Font).grid(row=row_idx, column=0, sticky="e", **pad_opts)
        LeftUpperLower = tk.Label(KADFrame, text="-", font=Small_Font)
        LeftUpperLower.grid(row=row_idx, column=1, **pad_opts)
        LeftDistRange = tk.Entry(KADFrame, justify="center", width=5)
        LeftDistRange.grid(row=row_idx, column=2, sticky="w", **pad_opts)
        
        RightUpperLower = tk.Label(KADFrame, text="-", font=Small_Font)
        RightUpperLower.grid(row=row_idx, column=3, **pad_opts)
        RightDistRange = tk.Entry(KADFrame, justify="center", width=5)
        RightDistRange.grid(row=row_idx, column=4, sticky="w", **pad_opts)
        row_idx += 1

        # Lateral & Lower
        tk.Label(KADFrame, text="Lateral & Lower Marker", font=Small_Font).grid(row=row_idx, column=0, sticky="e", **pad_opts)
        LeftLateralLower = tk.Label(KADFrame, text="-", font=Small_Font)
        LeftLateralLower.grid(row=row_idx, column=1, **pad_opts)
        RightLateralLower = tk.Label(KADFrame, text="-", font=Small_Font)
        RightLateralLower.grid(row=row_idx, column=3, **pad_opts)
        row_idx += 1

        # Sub-header: Angles
        tk.Label(KADFrame, text="Inter Markers Angles (deg)", font=Bold_Small_Font).grid(row=row_idx, column=0, sticky="w", padx=5, pady=10)
        row_idx += 1

        # Upper-Lateral-Lower
        tk.Label(KADFrame, text="Upper-Lateral-Lower", font=Small_Font).grid(row=row_idx, column=0, sticky="e", **pad_opts)
        LeftUpperLateralLower = tk.Label(KADFrame, text="-", font=Small_Font)
        LeftUpperLateralLower.grid(row=row_idx, column=1, **pad_opts)
        RightUpperLateralLower = tk.Label(KADFrame, text="-", font=Small_Font)
        RightUpperLateralLower.grid(row=row_idx, column=3, **pad_opts)
        row_idx += 1

        # Lateral-Upper-Lower
        tk.Label(KADFrame, text="Lateral-Upper-Lower", font=Small_Font).grid(row=row_idx, column=0, sticky="e", **pad_opts)
        LeftLateralUpperLower = tk.Label(KADFrame, text="-", font=Small_Font)
        LeftLateralUpperLower.grid(row=row_idx, column=1, **pad_opts)
        LeftAngleRange = tk.Entry(KADFrame, justify="center", width=5)
        LeftAngleRange.grid(row=row_idx, column=2, sticky="w", **pad_opts)

        RightLateralUpperLower = tk.Label(KADFrame, text="-", font=Small_Font)
        RightLateralUpperLower.grid(row=row_idx, column=3, **pad_opts)
        RightAngleRange = tk.Entry(KADFrame, justify="center", width=5)
        RightAngleRange.grid(row=row_idx, column=4, sticky="w", **pad_opts)
        row_idx += 1

        # Upper-Lower-Lateral
        tk.Label(KADFrame, text="Upper-Lower-Lateral", font=Small_Font).grid(row=row_idx, column=0, sticky="e", **pad_opts)
        LeftUpperLowerLateral = tk.Label(KADFrame, text="-", font=Small_Font)
        LeftUpperLowerLateral.grid(row=row_idx, column=1, **pad_opts)
        RightUpperLowerLateral = tk.Label(KADFrame, text="-", font=Small_Font)
        RightUpperLowerLateral.grid(row=row_idx, column=3, **pad_opts)


        # =============================================================================
        #       Compute QA based on Clinical Measures and Marker Data
        # =============================================================================
        # Extract Clinical Values
        exec(open(StaticDataFileName).read())
        normalize_processing_measurements(self)
        # Extract Nexus first frame
        StartFrame, EndFrame = fields["First Frame"], fields["Last Frame"]

        # =============================================================================
        #         Read Marker data from Start Frame (First Frame) for Static Check
        #         Dispplay Warning if marker not found
        # =============================================================================
        def HasTrajectory(self, subjectName, markerName):
            return markerName in fields

        # Function to extract markerdata and check if data exists
        def MarkerCheck(Subject, MarkerName, FirstFrame):
            # Check if marker exists at all
            if MarkerName in fields and fields[MarkerName]:
                MarkerData = np.array(
                    (
                        fields[MarkerName]["X"][FirstFrame],
                        fields[MarkerName]["Y"][FirstFrame],
                        fields[MarkerName]["Z"][FirstFrame],
                    )
                )
                # Check if marker is labeled at the first frame
                if MarkerData[0] == 0 or MarkerData[1] == 0 or MarkerData[2] == 0:
                    ErrorMessagesLabel.place(x=50, y=100, width=130, height=85)
                    ErrorMessagesText.place(x=195, y=95, width=490, height=85)
                    ErrorMessage = (
                        "Marker "
                        + MarkerName
                        + " is not labeled at frame "
                        + str(FirstFrame)
                        + "\n"
                    )
                    ErrorMessagesText.config(state="normal")
                    ErrorMessagesText.insert(tk.END, ErrorMessage)
                    ErrorMessagesText.config(state="disabled")
            else:
                MarkerData = np.array([0.0, 0.0, 0.0])
                # Dont show error for Trunk Markers
                ExcludedForErrorMarkerNames = [
                    self.C7MarkerName,
                    self.LeftClavicleMarkerName,
                    self.RightClavicleMarkerName,
                ]
                if (
                    MarkerName not in ExcludedForErrorMarkerNames
                    and MarkerName.split(".")[0] not in ExcludedForErrorMarkerNames
                ):
                    ErrorMessagesLabel.place(x=50, y=100, width=130, height=85)
                    ErrorMessagesText.place(x=195, y=95, width=490, height=85)
                    ErrorMessage = "Marker " + MarkerName + " is not Found " + "\n"
                    ErrorMessagesText.config(state="normal")
                    ErrorMessagesText.insert(tk.END, ErrorMessage)
                    ErrorMessagesText.config(state="disabled")
            return MarkerData

        # Function to extract markerdata into an array and check if data exists
        def MarkerArrayCheck(Subject, MarkerName):
            # Check if marker exists at all
            if MarkerName in fields and fields[MarkerName]:
                MarkerDataX = fields[MarkerName]["X"]
                MarkerDataY = fields[MarkerName]["Y"]
                MarkerDataZ = fields[MarkerName]["Z"]
                MarkerDataExists = fields[MarkerName]["Exists"]
            else:
                framecount = fields["Frames"]
                MarkerDataX = [0 for m in range(framecount)]
                MarkerDataY = [0 for m in range(framecount)]
                MarkerDataZ = [0 for m in range(framecount)]
                MarkerDataExists = [False] * framecount
                ErrorMessagesLabel.place(x=50, y=100, width=130, height=85)
                ErrorMessagesText.place(x=195, y=95, width=490, height=85)
                ErrorMessage = "Marker " + MarkerName + " is not Found " + "\n"
                ErrorMessagesText.config(state="normal")
                ErrorMessagesText.insert(tk.END, ErrorMessage)
                ErrorMessagesText.config(state="disabled")
            return MarkerDataX, MarkerDataY, MarkerDataZ, MarkerDataExists

        # =============================================================================
        #       If Pelvic Fix Option used then compute ASIS markers
        # =============================================================================
        if not self.valuePelvicFixCheck == "0":  # Pelfix Option is Used
            if self.valuePelvicFixCheck == "1":
                (
                    LeftIliacMarkerX,
                    LeftIliacMarkerY,
                    LeftIliacMarkerZ,
                    LeftIliacMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.LeftIliacMarkerName)
                (
                    RightIliacMarkerX,
                    RightIliacMarkerY,
                    RightIliacMarkerZ,
                    RightIliacMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.RightIliacMarkerName)
                try:
                    SacralMarkerX, SacralMarkerY, SacralMarkerZ, SacralMarkerExists = (
                        MarkerArrayCheck(SubjectName, self.SacralMarkerName)
                    )
                except:
                    (
                        LeftPSISMarkerX,
                        LeftPSISMarkerY,
                        LeftPSISMarkerZ,
                        LeftPSISMarkerExists,
                    ) = MarkerArrayCheck(SubjectName, self.LeftPSISMarkerName)
                    (
                        RightPSISMarkerX,
                        RightPSISMarkerY,
                        RightPSISMarkerZ,
                        RightPSISMarkerExists,
                    ) = MarkerArrayCheck(SubjectName, self.RightPSISMarkerName)
                    SacralMarkerX = (LeftPSISMarkerX + RightPSISMarkerX) / 2
                    SacralMarkerY = (LeftPSISMarkerY + RightPSISMarkerY) / 2
                    SacralMarkerZ = (LeftPSISMarkerZ + RightPSISMarkerZ) / 2

            if self.valuePelvicFixCheck == "2":
                (
                    LeftPSISMarkerX,
                    LeftPSISMarkerY,
                    LeftPSISMarkerZ,
                    LeftPSISMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.LeftPSISMarkerName)
                (
                    RightPSISMarkerX,
                    RightPSISMarkerY,
                    RightPSISMarkerZ,
                    RightPSISMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.RightPSISMarkerName)
                (
                    SacralTriadMarkerX,
                    SacralTriadMarkerY,
                    SacralTriadMarkerZ,
                    SacralTriadMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.SacralTriadMarkerName)

            _default_calib = os.path.join(
                FilePath,
                "Calibration",
                "Static_"
                + DefaultTestingCondition
                + "_"
                + SubjectName
                + ".py",
            )
            if os.path.exists(_default_calib):
                DefaultStaticDataFileName = _default_calib
            else:
                DefaultStaticDataFileName = (
                    FilePath
                    + "Static_"
                    + DefaultTestingCondition
                    + "_"
                    + SubjectName
                    + ".py"
                )
            if (
                os.path.exists(DefaultStaticDataFileName)
                and self.PointerTipMarkerName not in fields
                and self.PointerTailMarkerName not in fields
            ):
                # =============================================================================
                #       AFO Condition Check- Read Pelfix Information from Barefoot Trials
                # =============================================================================
                f = open(DefaultStaticDataFileName, "r")
                lines = f.readlines()  # read all lines
                import tempfile
                TempPelfixFileName = os.path.join(tempfile.gettempdir(), "Pelfix.py")
                TempPelfixFile = open(TempPelfixFileName, "w+")
                for line in lines:
                    words = line.split()
                    if (
                        words[0] == "self.valueLeftASISMarkerPelvis"
                        or words[0] == "self.valueRightASISMarkerPelvis"
                    ):
                        TempPelfixFile.write(line)
                TempPelfixFile.close()
                exec(open(TempPelfixFileName).read())
                try:
                    os.remove(TempPelfixFileName)
                except:
                    pass
                LeftASISMarkerPelvis = self.valueLeftASISMarkerPelvis
                RightASISMarkerPelvis = self.valueRightASISMarkerPelvis
            else:
                # Compute Max and Min Pointer Disance
                (
                    PointerTipMarkerX,
                    PointerTipMarkerY,
                    PointerTipMarkerZ,
                    PointerTipMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.PointerTipMarkerName)
                (
                    PointerTailMarkerX,
                    PointerTailMarkerY,
                    PointerTailMarkerZ,
                    PointerTailMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.PointerTailMarkerName)

                MinPointerDist = 1000
                MaxPointerDist = -1000
                framecount = fields["Frames"]
                for FrameNumber in range(StartFrame, EndFrame):
                    PointerTipMarker = np.array(
                        [
                            PointerTipMarkerX[FrameNumber],
                            PointerTipMarkerY[FrameNumber],
                            PointerTipMarkerZ[FrameNumber],
                        ]
                    )
                    PointerTailMarker = np.array(
                        [
                            PointerTailMarkerX[FrameNumber],
                            PointerTailMarkerY[FrameNumber],
                            PointerTailMarkerZ[FrameNumber],
                        ]
                    )
                    if (
                        PointerTipMarkerExists[FrameNumber] is True
                        and PointerTailMarkerExists[FrameNumber] is True
                    ):
                        PointerDist = round(
                            np.linalg.norm(PointerTipMarker - PointerTailMarker), 0
                        )
                        if PointerDist > MaxPointerDist:
                            MaxPointerDist = PointerDist
                        if PointerDist < MinPointerDist:
                            MinPointerDist = PointerDist

                # Compute Threshold Distance for Pointer Press
                Threshold_Distance = round((MaxPointerDist + MinPointerDist) / 2, 0)
                # print(Threshold_Distance)

                # Compute Frames when Pointer was pressed
                FrameA = 0  # First Press Frame
                FrameB = 0  # Second Press Frame
                FrameX = 0  # Frame when First Press is released
                for FrameNumber in range(StartFrame, EndFrame):
                    PointerTipMarker = np.array(
                        [
                            PointerTipMarkerX[FrameNumber],
                            PointerTipMarkerY[FrameNumber],
                            PointerTipMarkerZ[FrameNumber],
                        ]
                    )
                    PointerTailMarker = np.array(
                        [
                            PointerTailMarkerX[FrameNumber],
                            PointerTailMarkerY[FrameNumber],
                            PointerTailMarkerZ[FrameNumber],
                        ]
                    )
                    PointerDist = round(
                        np.linalg.norm(PointerTipMarker - PointerTailMarker), 0
                    )
                    # print(PointerDist)
                    if PointerDist < Threshold_Distance and FrameA == 0:
                        FrameA = FrameNumber
                    if PointerDist > Threshold_Distance and FrameA != 0 and FrameX == 0:
                        FrameX = FrameNumber
                    if (
                        PointerDist < Threshold_Distance
                        and FrameA != 0
                        and FrameX != 0
                        and FrameB == 0
                    ):
                        FrameB = FrameNumber
                # print(FrameA,FrameB)

                for FrameNumber in (FrameA, FrameB):
                    if self.valuePelvicFixCheck == "1":  # Iliac Markers Option
                        # Pelvis Technical coordinate system based on LILC, RILC, SACR
                        LeftIliacMarker = np.array(
                            [
                                LeftIliacMarkerX[FrameNumber],
                                LeftIliacMarkerY[FrameNumber],
                                LeftIliacMarkerZ[FrameNumber],
                            ]
                        )
                        RightIliacMarker = np.array(
                            [
                                RightIliacMarkerX[FrameNumber],
                                RightIliacMarkerY[FrameNumber],
                                RightIliacMarkerZ[FrameNumber],
                            ]
                        )
                        SacralMarker = np.array(
                            [
                                SacralMarkerX[FrameNumber],
                                SacralMarkerY[FrameNumber],
                                SacralMarkerZ[FrameNumber],
                            ]
                        )
                        [EPelvisTech, MidASISLab] = gait.TechCS_Pelvis_Newington(
                            LeftIliacMarker, RightIliacMarker, SacralMarker
                        )

                        PointerTipMarker = np.array(
                            [
                                PointerTipMarkerX[FrameNumber],
                                PointerTipMarkerY[FrameNumber],
                                PointerTipMarkerZ[FrameNumber],
                            ]
                        )
                        PointerTailMarker = np.array(
                            [
                                PointerTailMarkerX[FrameNumber],
                                PointerTailMarkerY[FrameNumber],
                                PointerTailMarkerZ[FrameNumber],
                            ]
                        )
                        Pointer_UnitVector = math.ComputeUnitVecFromPts(
                            PointerTailMarker, PointerTipMarker
                        )

                        valueASISMarkerLab = np.array([0.0, 0.0, 0.0])
                        valueASISMarkerLab = (
                            PointerTipMarker
                            + Pointer_UnitVector * float(self.PointerMarkerTipDistance)
                        )

                        # Transform ASIS Marker in Pelvic Technical Coordinate System
                        valueASISMarkerPelvis = math.TransformPointIntoMovingCoors(
                            valueASISMarkerLab, EPelvisTech, MidASISLab
                        )

                    if self.valuePelvicFixCheck == "2":  # Pelvic Triad Option
                        # Pelvis Technical coordinate system based on LPSI, RPSI, SACT
                        LeftPSISMarker = np.array(
                            [
                                LeftPSISMarkerX[FrameNumber],
                                LeftPSISMarkerY[FrameNumber],
                                LeftPSISMarkerZ[FrameNumber],
                            ]
                        )
                        RightPSISMarker = np.array(
                            [
                                RightPSISMarkerX[FrameNumber],
                                RightPSISMarkerY[FrameNumber],
                                RightPSISMarkerZ[FrameNumber],
                            ]
                        )
                        SacralTriadMarker = np.array(
                            [
                                SacralTriadMarkerX[FrameNumber],
                                SacralTriadMarkerY[FrameNumber],
                                SacralTriadMarkerZ[FrameNumber],
                            ]
                        )
                        SacralMarker = (LeftPSISMarker + RightPSISMarker) / 2
                        [EPelvisTech, MidASISLab] = gait.TechCS_Pelvis_Newington(
                            LeftPSISMarker, RightPSISMarker, SacralTriadMarker
                        )

                        PointerTipMarker = np.array(
                            [
                                PointerTipMarkerX[FrameNumber],
                                PointerTipMarkerY[FrameNumber],
                                PointerTipMarkerZ[FrameNumber],
                            ]
                        )
                        PointerTailMarker = np.array(
                            [
                                PointerTailMarkerX[FrameNumber],
                                PointerTailMarkerY[FrameNumber],
                                PointerTailMarkerZ[FrameNumber],
                            ]
                        )
                        Pointer_UnitVector = math.ComputeUnitVecFromPts(
                            PointerTailMarker, PointerTipMarker
                        )

                        valueASISMarkerLab = np.array([0.0, 0.0, 0.0])
                        valueASISMarkerLab = (
                            PointerTipMarker
                            + Pointer_UnitVector * float(self.PointerMarkerTipDistance)
                        )

                        # Transform ASIS Marker in Pelvic Technical Coordinate System
                        valueASISMarkerPelvis = math.TransformPointIntoMovingCoors(
                            valueASISMarkerLab, EPelvisTech, MidASISLab
                        )

                    if FrameNumber == FrameA:
                        valueASISMarkerPelvis_FrameA = valueASISMarkerPelvis
                        SACRtoASIS_FrameA = math.ComputeUnitVecFromPts(
                            SacralMarker, valueASISMarkerLab
                        )
                    else:
                        valueASISMarkerPelvis_FrameB = valueASISMarkerPelvis
                        SACRtoASIS_FrameB = math.ComputeUnitVecFromPts(
                            SacralMarker, valueASISMarkerLab
                        )

                # Determine which ASIS is being identified by Pointer and save to C3D
                CrossVector = np.cross(SACRtoASIS_FrameA, SACRtoASIS_FrameB)
                if CrossVector[2] > 0:
                    RightASISMarkerPelvis = valueASISMarkerPelvis_FrameA
                    LeftASISMarkerPelvis = valueASISMarkerPelvis_FrameB
                else:
                    RightASISMarkerPelvis = valueASISMarkerPelvis_FrameB
                    LeftASISMarkerPelvis = valueASISMarkerPelvis_FrameA

            # Write Marker into C3D
            framecount = fields["Frames"]
            arrayLASISMarkerX = [0 for m in range(framecount)]
            arrayLASISMarkerY = [0 for m in range(framecount)]
            arrayLASISMarkerZ = [0 for m in range(framecount)]
            arrayRASISMarkerX = [0 for m in range(framecount)]
            arrayRASISMarkerY = [0 for m in range(framecount)]
            arrayRASISMarkerZ = [0 for m in range(framecount)]
            exists = [True] * framecount

            for FrameNumber in range(StartFrame, EndFrame):
                # Compute Pelvis Tech Coordinates
                if self.valuePelvicFixCheck == "1":
                    # Pelvis Technical coordinate system based on LILC, RILC, SACR
                    LeftIliacMarker = np.array(
                        [
                            LeftIliacMarkerX[FrameNumber],
                            LeftIliacMarkerY[FrameNumber],
                            LeftIliacMarkerZ[FrameNumber],
                        ]
                    )
                    RightIliacMarker = np.array(
                        [
                            RightIliacMarkerX[FrameNumber],
                            RightIliacMarkerY[FrameNumber],
                            RightIliacMarkerZ[FrameNumber],
                        ]
                    )
                    SacralMarker = np.array(
                        [
                            SacralMarkerX[FrameNumber],
                            SacralMarkerY[FrameNumber],
                            SacralMarkerZ[FrameNumber],
                        ]
                    )
                    [EPelvisTech, MidASISLab] = gait.TechCS_Pelvis_Newington(
                        LeftIliacMarker, RightIliacMarker, SacralMarker
                    )

                if self.valuePelvicFixCheck == "2":  # Pelvic Triad Option
                    # Pelvis Technical coordinate system based on LPSI, RPSI, SACT
                    LeftPSISMarker = np.array(
                        [
                            LeftPSISMarkerX[FrameNumber],
                            LeftPSISMarkerY[FrameNumber],
                            LeftPSISMarkerZ[FrameNumber],
                        ]
                    )
                    RightPSISMarker = np.array(
                        [
                            RightPSISMarkerX[FrameNumber],
                            RightPSISMarkerY[FrameNumber],
                            RightPSISMarkerZ[FrameNumber],
                        ]
                    )
                    SacralTriadMarker = np.array(
                        [
                            SacralTriadMarkerX[FrameNumber],
                            SacralTriadMarkerY[FrameNumber],
                            SacralTriadMarkerZ[FrameNumber],
                        ]
                    )
                    [EPelvisTech, MidASISLab] = gait.TechCS_Pelvis_Newington(
                        LeftPSISMarker, RightPSISMarker, SacralTriadMarker
                    )

                LeftASISMarkerLab = math.TransformPointIntoLabCoors(
                    LeftASISMarkerPelvis, EPelvisTech, MidASISLab
                )
                RightASISMarkerLab = math.TransformPointIntoLabCoors(
                    RightASISMarkerPelvis, EPelvisTech, MidASISLab
                )
                arrayLASISMarkerX[FrameNumber] = LeftASISMarkerLab[0]
                arrayLASISMarkerY[FrameNumber] = LeftASISMarkerLab[1]
                arrayLASISMarkerZ[FrameNumber] = LeftASISMarkerLab[2]
                arrayRASISMarkerX[FrameNumber] = RightASISMarkerLab[0]
                arrayRASISMarkerY[FrameNumber] = RightASISMarkerLab[1]
                arrayRASISMarkerZ[FrameNumber] = RightASISMarkerLab[2]

            # vicon.SetTrajectory(SubjectName, self.LeftASISMarkerName, arrayLASISMarkerX, arrayLASISMarkerY, arrayLASISMarkerZ, exists )
            SetTrajectory(
                self.LeftASISMarkerName,
                arrayLASISMarkerX,
                arrayLASISMarkerY,
                arrayLASISMarkerZ,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )
            # vicon.SetTrajectory self.RightASISMarkerName, arrayRASISMarkerX, arrayRASISMarkerY, arrayRASISMarkerZ, exists )
            SetTrajectory(
                self.RightASISMarkerName,
                arrayRASISMarkerX,
                arrayRASISMarkerY,
                arrayRASISMarkerZ,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )

        # =============================================================================

        # =============================================================================
        #       If FootModel is used then write HEEL and TOE markers
        # =============================================================================

        if self.LeftToeMarkerName not in fields:
            if self.Left23MetatarsalHeadMarkerName in fields:
                (
                    arrayLeft23MetatarsalHeadMarkerX,
                    arrayLeft23MetatarsalHeadMarkerY,
                    arrayLeft23MetatarsalHeadMarkerZ,
                    arrayLeft23MetatarsalHeadMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.Left23MetatarsalHeadMarkerName)
                # vicon.SetTrajectory(SubjectName, self.LeftToeMarkerName, arrayLeft23MetatarsalHeadMarkerX, arrayLeft23MetatarsalHeadMarkerY, arrayLeft23MetatarsalHeadMarkerZ, arrayLeft23MetatarsalHeadMarkerExists)
                SetTrajectory(
                    self.LeftToeMarkerName,
                    arrayLeft23MetatarsalHeadMarkerX,
                    arrayLeft23MetatarsalHeadMarkerY,
                    arrayLeft23MetatarsalHeadMarkerZ,
                    arrayLeft23MetatarsalHeadMarkerExists,
                    fields["First Frame"],
                    fields["Last Frame"],
                    fields["initial_frame_offset"],
                )
            else:
                if os.path.exists(SittingFootStaticDataFileName):
                    exec(open(SittingFootStaticDataFileName).read())
                    (
                        LeftFirstMetarsalBaseMarkerX,
                        LeftFirstMetarsalBaseMarkerY,
                        LeftFirstMetarsalBaseMarkerZ,
                        LeftFirstMetarsalBaseMarkerExists,
                    ) = MarkerArrayCheck(
                        SubjectName, self.LeftFirstMetarsalBaseMarkerName
                    )
                    (
                        LeftFirstMetarsalHeadMarkerX,
                        LeftFirstMetarsalHeadMarkerY,
                        LeftFirstMetarsalHeadMarkerZ,
                        LeftFirstMetarsalHeadMarkerExists,
                    ) = MarkerArrayCheck(
                        SubjectName, self.LeftFirstMetarsalHeadMarkerName
                    )
                    (
                        LeftFifthMetarsalHeadMarkerX,
                        LeftFifthMetarsalHeadMarkerY,
                        LeftFifthMetarsalHeadMarkerZ,
                        LeftFifthMetarsalHeadMarkerExists,
                    ) = MarkerArrayCheck(
                        SubjectName, self.LeftFifthMetarsalHeadMarkerName
                    )
                    # Compute markers for each frame
                    framecount = fields["Frames"]
                    arrayLMT23HMarkerX = [0 for m in range(framecount)]
                    arrayLMT23HMarkerY = [0 for m in range(framecount)]
                    arrayLMT23HMarkerZ = [0 for m in range(framecount)]
                    exists = [True] * framecount
                    for FrameNumber in range(StartFrame, EndFrame):
                        # Compute Technical Coordinate System: Left Foot Segments
                        LeftFirstMetarsalBaseMarker = np.array(
                            [
                                LeftFirstMetarsalBaseMarkerX[FrameNumber],
                                LeftFirstMetarsalBaseMarkerY[FrameNumber],
                                LeftFirstMetarsalBaseMarkerZ[FrameNumber],
                            ]
                        )
                        LeftFirstMetarsalHeadMarker = np.array(
                            [
                                LeftFirstMetarsalHeadMarkerX[FrameNumber],
                                LeftFirstMetarsalHeadMarkerY[FrameNumber],
                                LeftFirstMetarsalHeadMarkerZ[FrameNumber],
                            ]
                        )
                        LeftFifthMetarsalHeadMarker = np.array(
                            [
                                LeftFifthMetarsalHeadMarkerX[FrameNumber],
                                LeftFifthMetarsalHeadMarkerY[FrameNumber],
                                LeftFifthMetarsalHeadMarkerZ[FrameNumber],
                            ]
                        )
                        LeftEForefootTech = gait.TechCS_Forefoot_mSHCG(
                            "Left",
                            LeftFirstMetarsalBaseMarker,
                            LeftFirstMetarsalHeadMarker,
                            LeftFifthMetarsalHeadMarker,
                        )
                        LeftMT23HMarkerLab = math.TransformPointIntoLabCoors(
                            self.valueLeft23MetatarsalHeadMarkerForefoot,
                            LeftEForefootTech,
                            LeftFirstMetarsalBaseMarker,
                        )
                        arrayLMT23HMarkerX[FrameNumber] = LeftMT23HMarkerLab[0]
                        arrayLMT23HMarkerY[FrameNumber] = LeftMT23HMarkerLab[1]
                        arrayLMT23HMarkerZ[FrameNumber] = LeftMT23HMarkerLab[2]
                    SetTrajectory(
                        self.LeftToeMarkerName,
                        arrayLMT23HMarkerX,
                        arrayLMT23HMarkerY,
                        arrayLMT23HMarkerZ,
                        exists,
                        fields["First Frame"],
                        fields["Last Frame"],
                        fields["initial_frame_offset"],
                    )
                    # vicon.SetTrajectory(SubjectName, self.LeftToeMarkerName, arrayLMT23HMarkerX, arrayLMT23HMarkerY, arrayLMT23HMarkerZ, exists)

        if (
            self.LeftHeelMarkerName not in fields
            and self.LeftPosteriorCalcaneusMarkerName in fields
        ):
            (
                arrayLeftPosteriorCalcaneusMarkerX,
                arrayLeftPosteriorCalcaneusMarkerY,
                arrayLeftPosteriorCalcaneusMarkerZ,
                arrayLeftPosteriorCalcaneusMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftPosteriorCalcaneusMarkerName)
            # vicon.SetTrajectory(SubjectName, self.LeftHeelMarkerName, arrayLeftPosteriorCalcaneusMarkerX, arrayLeftPosteriorCalcaneusMarkerY, arrayLeftPosteriorCalcaneusMarkerZ, arrayLeftPosteriorCalcaneusMarkerExists)
            SetTrajectory(
                self.LeftHeelMarkerName,
                arrayLeftPosteriorCalcaneusMarkerX,
                arrayLeftPosteriorCalcaneusMarkerY,
                arrayLeftPosteriorCalcaneusMarkerZ,
                arrayLeftPosteriorCalcaneusMarkerExists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )
        if self.RightToeMarkerName not in fields:
            if self.Right23MetatarsalHeadMarkerName in fields:
                (
                    arrayRight23MetatarsalHeadMarkerX,
                    arrayRight23MetatarsalHeadMarkerY,
                    arrayRight23MetatarsalHeadMarkerZ,
                    arrayRight23MetatarsalHeadMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.Right23MetatarsalHeadMarkerName)
                # vicon.SetTrajectory(SubjectName, self.RightToeMarkerName, arrayRight23MetatarsalHeadMarkerX, arrayRight23MetatarsalHeadMarkerY, arrayRight23MetatarsalHeadMarkerZ, arrayRight23MetatarsalHeadMarkerExists)
                SetTrajectory(
                    self.RightToeMarkerName,
                    arrayRight23MetatarsalHeadMarkerX,
                    arrayRight23MetatarsalHeadMarkerY,
                    arrayRight23MetatarsalHeadMarkerZ,
                    arrayRight23MetatarsalHeadMarkerExists,
                    fields["First Frame"],
                    fields["Last Frame"],
                    fields["initial_frame_offset"],
                )
            else:
                if os.path.exists(SittingFootStaticDataFileName):
                    exec(open(SittingFootStaticDataFileName).read())
                    (
                        RightFirstMetarsalBaseMarkerX,
                        RightFirstMetarsalBaseMarkerY,
                        RightFirstMetarsalBaseMarkerZ,
                        RightFirstMetarsalBaseMarkerExists,
                    ) = MarkerArrayCheck(
                        SubjectName, self.RightFirstMetarsalBaseMarkerName
                    )
                    (
                        RightFirstMetarsalHeadMarkerX,
                        RightFirstMetarsalHeadMarkerY,
                        RightFirstMetarsalHeadMarkerZ,
                        RightFirstMetarsalHeadMarkerExists,
                    ) = MarkerArrayCheck(
                        SubjectName, self.RightFirstMetarsalHeadMarkerName
                    )
                    (
                        RightFifthMetarsalHeadMarkerX,
                        RightFifthMetarsalHeadMarkerY,
                        RightFifthMetarsalHeadMarkerZ,
                        RightFifthMetarsalHeadMarkerExists,
                    ) = MarkerArrayCheck(
                        SubjectName, self.RightFifthMetarsalHeadMarkerName
                    )
                    # Compute markers for each frame
                    framecount = fields["Frames"]
                    arrayRMT23HMarkerX = [0 for m in range(framecount)]
                    arrayRMT23HMarkerY = [0 for m in range(framecount)]
                    arrayRMT23HMarkerZ = [0 for m in range(framecount)]
                    exists = [True] * framecount
                    for FrameNumber in range(StartFrame, EndFrame):
                        # Compute Technical Coordinate System: Right Foot Segments
                        RightFirstMetarsalBaseMarker = np.array(
                            [
                                RightFirstMetarsalBaseMarkerX[FrameNumber],
                                RightFirstMetarsalBaseMarkerY[FrameNumber],
                                RightFirstMetarsalBaseMarkerZ[FrameNumber],
                            ]
                        )
                        RightFirstMetarsalHeadMarker = np.array(
                            [
                                RightFirstMetarsalHeadMarkerX[FrameNumber],
                                RightFirstMetarsalHeadMarkerY[FrameNumber],
                                RightFirstMetarsalHeadMarkerZ[FrameNumber],
                            ]
                        )
                        RightFifthMetarsalHeadMarker = np.array(
                            [
                                RightFifthMetarsalHeadMarkerX[FrameNumber],
                                RightFifthMetarsalHeadMarkerY[FrameNumber],
                                RightFifthMetarsalHeadMarkerZ[FrameNumber],
                            ]
                        )
                        RightEForefootTech = gait.TechCS_Forefoot_mSHCG(
                            "Right",
                            RightFirstMetarsalBaseMarker,
                            RightFirstMetarsalHeadMarker,
                            RightFifthMetarsalHeadMarker,
                        )
                        RightMT23HMarkerLab = math.TransformPointIntoLabCoors(
                            self.valueRight23MetatarsalHeadMarkerForefoot,
                            RightEForefootTech,
                            RightFirstMetarsalBaseMarker,
                        )
                        arrayRMT23HMarkerX[FrameNumber] = RightMT23HMarkerLab[0]
                        arrayRMT23HMarkerY[FrameNumber] = RightMT23HMarkerLab[1]
                        arrayRMT23HMarkerZ[FrameNumber] = RightMT23HMarkerLab[2]
                    # vicon.SetTrajectory(SubjectName, self.RightToeMarkerName, arrayRMT23HMarkerX, arrayRMT23HMarkerY, arrayRMT23HMarkerZ, exists)
                    SetTrajectory(
                        self.RightToeMarkerName,
                        arrayRMT23HMarkerX,
                        arrayRMT23HMarkerY,
                        arrayRMT23HMarkerZ,
                        exists,
                        fields["First Frame"],
                        fields["Last Frame"],
                        fields["initial_frame_offset"],
                    )

        if (
            self.RightHeelMarkerName not in fields
            and self.RightPosteriorCalcaneusMarkerName in fields
        ):
            (
                arrayRightPosteriorCalcaneusMarkerX,
                arrayRightPosteriorCalcaneusMarkerY,
                arrayRightPosteriorCalcaneusMarkerZ,
                arrayRightPosteriorCalcaneusMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightPosteriorCalcaneusMarkerName)
            # vicon.SetTrajectory(SubjectName, self.RightHeelMarkerName, arrayRightPosteriorCalcaneusMarkerX, arrayRightPosteriorCalcaneusMarkerY, arrayRightPosteriorCalcaneusMarkerZ, arrayRightPosteriorCalcaneusMarkerExists)
            SetTrajectory(
                self.RightHeelMarkerName,
                arrayRightPosteriorCalcaneusMarkerX,
                arrayRightPosteriorCalcaneusMarkerY,
                arrayRightPosteriorCalcaneusMarkerZ,
                arrayRightPosteriorCalcaneusMarkerExists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )

        # =============================================================================
        LeftASISMarker = MarkerCheck(
            SubjectName, self.LeftASISMarkerName, int(self.valueStaticFrameNumber)
        )
        LeftLateralAnkleMarker = MarkerCheck(
            SubjectName,
            self.LeftLateralAnkleMarkerName,
            int(self.valueStaticFrameNumber),
        )
        LeftMedialAnkleMarker = MarkerCheck(
            SubjectName,
            self.LeftMedialAnkleMarkerName,
            int(self.valueStaticFrameNumber),
        )
        if self.valueKneeAlignmentCheck == "0":
            LeftLateralKADMarker = MarkerCheck(
                SubjectName,
                self.LeftLateralKADMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftUpperKADMarker = MarkerCheck(
                SubjectName,
                self.LeftUpperKADMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftLowerKADMarker = MarkerCheck(
                SubjectName,
                self.LeftLowerKADMarkerName,
                int(self.valueStaticFrameNumber),
            )
        else:
            LeftLateralKneeMarker = MarkerCheck(
                SubjectName,
                self.LeftLateralKneeMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftMedialKneeMarker = MarkerCheck(
                SubjectName,
                self.LeftMedialKneeMarkerName,
                int(self.valueStaticFrameNumber),
            )

        RightASISMarker = MarkerCheck(
            SubjectName, self.RightASISMarkerName, int(self.valueStaticFrameNumber)
        )
        RightLateralAnkleMarker = MarkerCheck(
            SubjectName,
            self.RightLateralAnkleMarkerName,
            int(self.valueStaticFrameNumber),
        )
        RightMedialAnkleMarker = MarkerCheck(
            SubjectName,
            self.RightMedialAnkleMarkerName,
            int(self.valueStaticFrameNumber),
        )
        if self.valueKneeAlignmentCheck == "0":
            RightLateralKADMarker = MarkerCheck(
                SubjectName,
                self.RightLateralKADMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightUpperKADMarker = MarkerCheck(
                SubjectName,
                self.RightUpperKADMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightLowerKADMarker = MarkerCheck(
                SubjectName,
                self.RightLowerKADMarkerName,
                int(self.valueStaticFrameNumber),
            )
        else:
            RightLateralKneeMarker = MarkerCheck(
                SubjectName,
                self.RightLateralKneeMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightMedialKneeMarker = MarkerCheck(
                SubjectName,
                self.RightMedialKneeMarkerName,
                int(self.valueStaticFrameNumber),
            )

        if self.valueKneeAlignmentCheck == "0":
            # Check of Upper/Lower KAD Marker labeling
            if LeftLowerKADMarker[2] > LeftUpperKADMarker[2]:
                ErrorMessagesLabel.place(x=50, y=100, width=130, height=85)
                ErrorMessagesText.place(x=195, y=95, width=490, height=85)
                ErrorMessage = (
                    "Markers on the Left KAD do not appear to be properly labeled"
                    + "\n"
                )
                ErrorMessagesText.insert(tk.END, ErrorMessage)
            if RightLowerKADMarker[2] > RightUpperKADMarker[2]:
                ErrorMessagesLabel.place(x=50, y=100, width=130, height=85)
                ErrorMessagesText.place(x=195, y=95, width=490, height=85)
                ErrorMessage = (
                    "Markers on the Right KAD do not appear to be properly labeled"
                    + "\n"
                )
                ErrorMessagesText.insert(tk.END, ErrorMessage)
            # =============================================================================

        ASISdistClinical["text"] = f"{self.valueASISdist / MILLIMETERS_PER_METER:.3f}"
        #print(SubjectName, self.LeftASISMarkerName)
        if (
            self.HasTrajectory(SubjectName, self.LeftASISMarkerName) is True
            and self.HasTrajectory(SubjectName, self.RightASISMarkerName) is True
        ):
            valueASISdistMarkers = np.linalg.norm(LeftASISMarker - RightASISMarker)

            print(
                f"ASIS clinical:{self.valueASISdist} ASIS Markers:{valueASISdistMarkers}"
            )
            ASISdistMarkers["text"] = f"{valueASISdistMarkers / MILLIMETERS_PER_METER:.3f}"
            ASISdistDiff.insert(
                0, f"{abs(valueASISdistMarkers - self.valueASISdist) / MILLIMETERS_PER_METER:.3f}"
            )

        LeftKneeWidthClinical["text"] = f"{self.valueLeftKneeWidth / MILLIMETERS_PER_METER:.3f}"
        if self.valueKneeAlignmentCheck == "1":
            valueLeftKneeWidthMarkers = (
                np.linalg.norm(LeftLateralKneeMarker - LeftMedialKneeMarker)
                - self.MarkerDiameter
            )
            print(
                f"Left Knee Width clinical:{self.valueLeftKneeWidth} Left Knee Width Markers:{valueLeftKneeWidthMarkers}"
            )
            LeftKneeWidthMarkers["text"] = f"{valueLeftKneeWidthMarkers / MILLIMETERS_PER_METER:.3f}"
            LeftKneeWidthDiff.insert(
                0, f"{abs(valueLeftKneeWidthMarkers - self.valueLeftKneeWidth) / MILLIMETERS_PER_METER:.3f}"
            )

        RightKneeWidthClinical["text"] = f"{self.valueRightKneeWidth / MILLIMETERS_PER_METER:.3f}"
        if self.valueKneeAlignmentCheck == "1":
            valueRightKneeWidthMarkers = (
                np.linalg.norm(RightLateralKneeMarker - RightMedialKneeMarker)
                - self.MarkerDiameter
            )
            print(
                f"Right Knee Width clinical:{self.valueRightKneeWidth} Right Knee Width Markers:{valueRightKneeWidthMarkers}"
            )
            RightKneeWidthMarkers["text"] = f"{valueRightKneeWidthMarkers / MILLIMETERS_PER_METER:.3f}"
            RightKneeWidthDiff.insert(
                0,
                f"{abs(valueRightKneeWidthMarkers - self.valueRightKneeWidth) / MILLIMETERS_PER_METER:.3f}",
            )

        LeftAnkleWidthClinical["text"] = f"{self.valueLeftAnkleWidth / MILLIMETERS_PER_METER:.3f}"
        if (
            self.HasTrajectory(SubjectName, self.LeftLateralAnkleMarkerName) is True
            and self.HasTrajectory(SubjectName, self.LeftMedialAnkleMarkerName) is True
        ):
            valueLeftAnkleWidthMarkers = (
                np.linalg.norm(LeftLateralAnkleMarker - LeftMedialAnkleMarker)
                - self.MarkerDiameter
            )
            print(
                f"Left Ankle Width clinical:{self.valueLeftAnkleWidth} Left Ankle Width Markers:{valueLeftAnkleWidthMarkers}"
            )
            LeftAnkleWidthMarkers["text"] = f"{valueLeftAnkleWidthMarkers / MILLIMETERS_PER_METER:.3f}"
            LeftAnkleWidthDiff.insert(
                0,
                f"{abs(valueLeftAnkleWidthMarkers - self.valueLeftAnkleWidth) / MILLIMETERS_PER_METER:.3f}",
            )

        RightAnkleWidthClinical["text"] = f"{self.valueRightAnkleWidth / MILLIMETERS_PER_METER:.3f}"
        if (
            self.HasTrajectory(SubjectName, self.RightLateralAnkleMarkerName) is True
            and self.HasTrajectory(SubjectName, self.RightMedialAnkleMarkerName) is True
        ):
            valueRightAnkleWidthMarkers = (
                np.linalg.norm(RightLateralAnkleMarker - RightMedialAnkleMarker)
                - self.MarkerDiameter
            )
            print(
                f"Right Ankle Width clinical:{self.valueRightAnkleWidth} Right Ankle Width Markers:{valueRightAnkleWidthMarkers}"
            )
            RightAnkleWidthMarkers["text"] = f"{valueRightAnkleWidthMarkers / MILLIMETERS_PER_METER:.3f}"
            RightAnkleWidthDiff.insert(
                0,
                f"{abs(valueRightAnkleWidthMarkers - self.valueRightAnkleWidth) / MILLIMETERS_PER_METER:.3f}",
            )

        if (
            self.HasTrajectory(SubjectName, self.LeftLateralKADMarkerName) is True
            and self.HasTrajectory(SubjectName, self.LeftUpperKADMarkerName) is True
            and self.HasTrajectory(SubjectName, self.LeftLowerKADMarkerName) is True
        ):
            # Distances
            valueLeftUpperLateral = np.linalg.norm(
                LeftUpperKADMarker - LeftLateralKADMarker
            )
            valueLeftUpperLower = np.linalg.norm(
                LeftUpperKADMarker - LeftLowerKADMarker
            )
            valueLeftLateralLower = np.linalg.norm(
                LeftLateralKADMarker - LeftLowerKADMarker
            )
            LeftUpperLateral["text"] = int(round(valueLeftUpperLateral))
            LeftUpperLower["text"] = int(round(valueLeftUpperLower))
            LeftLateralLower["text"] = int(round(valueLeftLateralLower))
            LeftDistRange.insert(
                0,
                int(
                    round(
                        max(
                            valueLeftUpperLateral,
                            valueLeftUpperLower,
                            valueLeftLateralLower,
                        )
                        - min(
                            valueLeftUpperLateral,
                            valueLeftUpperLower,
                            valueLeftLateralLower,
                        )
                    )
                ),
            )
            # Angles
            valueLeftUpperLateralLower = (
                math.Compute3DAngle(
                    LeftUpperKADMarker, LeftLateralKADMarker, LeftLowerKADMarker
                )
                * 180
                / np.pi
            )
            valueLeftLateralUpperLower = (
                math.Compute3DAngle(
                    LeftLateralKADMarker, LeftUpperKADMarker, LeftLowerKADMarker
                )
                * 180
                / np.pi
            )
            valueLeftUpperLowerLateral = (
                math.Compute3DAngle(
                    LeftUpperKADMarker, LeftLowerKADMarker, LeftLateralKADMarker
                )
                * 180
                / np.pi
            )
            LeftUpperLateralLower["text"] = int(round(valueLeftUpperLateralLower))
            LeftLateralUpperLower["text"] = int(round(valueLeftLateralUpperLower))
            LeftUpperLowerLateral["text"] = int(round(valueLeftUpperLowerLateral))
            LeftAngleRange.insert(
                0,
                int(
                    round(
                        max(
                            valueLeftUpperLateralLower,
                            valueLeftLateralUpperLower,
                            valueLeftUpperLowerLateral,
                        )
                        - min(
                            valueLeftUpperLateralLower,
                            valueLeftLateralUpperLower,
                            valueLeftUpperLowerLateral,
                        )
                    )
                ),
            )

        if (
            self.HasTrajectory(SubjectName, self.RightLateralKADMarkerName) is True
            and self.HasTrajectory(SubjectName, self.RightUpperKADMarkerName) is True
            and self.HasTrajectory(SubjectName, self.RightLowerKADMarkerName) is True
        ):
            # Distances
            valueRightUpperLateral = np.linalg.norm(
                RightUpperKADMarker - RightLateralKADMarker
            )
            valueRightUpperLower = np.linalg.norm(
                RightUpperKADMarker - RightLowerKADMarker
            )
            valueRightLateralLower = np.linalg.norm(
                RightLateralKADMarker - RightLowerKADMarker
            )
            RightUpperLateral["text"] = int(round(valueRightUpperLateral))
            RightUpperLower["text"] = int(round((valueRightUpperLower)))
            RightLateralLower["text"] = int(round((valueRightLateralLower)))
            RightDistRange.insert(
                0,
                int(
                    round(
                        max(
                            valueRightUpperLateral,
                            valueRightUpperLower,
                            valueRightLateralLower,
                        )
                        - min(
                            valueRightUpperLateral,
                            valueRightUpperLower,
                            valueRightLateralLower,
                        )
                    )
                ),
            )
            # Angles
            valueRightUpperLateralLower = (
                math.Compute3DAngle(
                    RightUpperKADMarker, RightLateralKADMarker, RightLowerKADMarker
                )
                * 180
                / np.pi
            )
            valueRightLateralUpperLower = (
                math.Compute3DAngle(
                    RightLateralKADMarker, RightUpperKADMarker, RightLowerKADMarker
                )
                * 180
                / np.pi
            )
            valueRightUpperLowerLateral = (
                math.Compute3DAngle(
                    RightUpperKADMarker, RightLowerKADMarker, RightLateralKADMarker
                )
                * 180
                / np.pi
            )
            RightUpperLateralLower["text"] = int(round(valueRightUpperLateralLower))
            RightLateralUpperLower["text"] = int(round(valueRightLateralUpperLower))
            RightUpperLowerLateral["text"] = int(round(valueRightUpperLowerLateral))
            RightAngleRange.insert(
                0,
                int(
                    round(
                        max(
                            valueRightUpperLateralLower,
                            valueRightLateralUpperLower,
                            valueRightUpperLowerLateral,
                        )
                        - min(
                            valueRightUpperLateralLower,
                            valueRightLateralUpperLower,
                            valueRightUpperLowerLateral,
                        )
                    )
                ),
            )

        # Make Calculated Fields Uneditable
        ASISdistDiff.configure(state="readonly")
        LeftKneeWidthDiff.configure(state="readonly")
        RightKneeWidthDiff.configure(state="readonly")
        LeftAnkleWidthDiff.configure(state="readonly")
        RightAnkleWidthDiff.configure(state="readonly")
        LeftDistRange.configure(state="readonly")
        RightDistRange.configure(state="readonly")
        LeftAngleRange.configure(state="readonly")
        RightAngleRange.configure(state="readonly")

        # =============================================================================
        #       Function to save Transformation matrics in Static_BF_MRN.py file.
        # =============================================================================
        if not self.valuePelvicFixCheck == "0":
            # Read Current File
            StaticDataFile = open(StaticDataFileName, "r")
            lines = StaticDataFile.readlines()
            StaticDataFile.close()

            # Write Subject Data into Static Anthropometric File
            StaticDataFile = open(StaticDataFileName, "w+")
            # Rewrite Subject Information
            PelfixInformationBlockStarts = 0
            TransformationMatricesBlockStarts = 0
            for line in lines:
                words = line.split()
                if words[0] == "#" and words[1] == "Pelfix":
                    PelfixInformationBlockStarts = 1
                if words[0] == "#" and words[1] == "Transformation":
                    TransformationMatricesBlockStarts = 1
                if (
                    PelfixInformationBlockStarts == 0
                    and TransformationMatricesBlockStarts == 0
                ):
                    StaticDataFile.write(line)

            # Write Pelfix Information
            StaticDataFile.write("# Pelfix Information" + "\n")
            StaticDataFile.write(
                "self.valueLeftASISMarkerPelvis = np.array(["
                + str(LeftASISMarkerPelvis[0])
                + ","
                + str(LeftASISMarkerPelvis[1])
                + ","
                + str(LeftASISMarkerPelvis[2])
                + "])"
                + "\n"
            )
            StaticDataFile.write(
                "self.valueRightASISMarkerPelvis = np.array(["
                + str(RightASISMarkerPelvis[0])
                + ","
                + str(RightASISMarkerPelvis[1])
                + ","
                + str(RightASISMarkerPelvis[2])
                + "])"
                + "\n"
            )

            # ReWrite Transformation Block if exists
            TransformationMatricesBlockStarts = 0
            for line in lines:
                words = line.split()
                if words[0] == "#" and words[1] == "Transformation":
                    TransformationMatricesBlockStarts = 1
                if TransformationMatricesBlockStarts == 1:
                    StaticDataFile.write(line)
            # print('FileUpdate- QA Report')
            StaticDataFile.close()


class StaticSubjectCalibrationReport_Page(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.grid(sticky="nsew")

        # Configure grid weights for responsiveness
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create scrollable canvas
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # Create inner frame
        self.inner_frame = tk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        # Event bindings
        self.inner_frame.bind("<Configure>", self._configure_inner)
        self.canvas.bind("<Configure>", self._configure_canvas)
        self.bind("<Enter>", self._bind_mousewheel)
        self.bind("<Leave>", self._unbind_mousewheel)

    def _configure_inner(self, event):
        pass  # Scroll region handled by PySide6

    def _configure_canvas(self, event):
        if self.inner_frame.winfo_width() != event.width:
            self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def HasTrajectory(self, subjectName, markerName):
        return markerName in fields

    def build_UI(self):
        # Clear existing widgets in inner_frame
        # Clear existing widgets

        if self.inner_frame.layout():

            old = self.inner_frame.layout()

            while old.count():

                item = old.takeAt(0)

                if item.widget():

                    item.widget().deleteLater()

                elif item.layout():

                    while item.layout().count():

                        sub = item.layout().takeAt(0)

                        if sub.widget():

                            sub.widget().deleteLater()

        self._inner_layout = QVBoxLayout(self.inner_frame) if not self.inner_frame.layout() else self.inner_frame.layout()

        # =============================================================================
        # Layout Configuration
        # =============================================================================
        # Layout columns handled by inner layout
        

        # Create Content Frame
        ContentFrame = tk.Frame(self.inner_frame)
        ContentFrame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        ContentFrame.columnconfigure(0, weight=1)

        # Create Button Frame
        ButtonFrame = tk.Frame(self.inner_frame, bg="SystemButtonFace")
        ButtonFrame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Buttons
        SavePdfButton = tk.Button(
            ButtonFrame,
            text="Save PDF",
            font=Small_Font,
            command=lambda: [
                saveTransformationMatrices(),
                saveResultsinC3D(),
                savePdf(),
                self.parent.frames[StaticSubjectCalibrationReport_Page].build_UI(),
            ],
        )
        SavePdfButton.pack(side="top", pady=(0, 5), ipadx=5, ipady=5, fill="x")

        SaveResultsButton = tk.Button(
            ButtonFrame,
            text="Save Results",
            wraplength=80,
            font=Small_Font,
            command=lambda: [saveTransformationMatrices(), saveResultsinC3D()],
        )
        SaveResultsButton.pack(side="top", pady=5, ipadx=5, ipady=5, fill="x")

        BackButton = tk.Button(
            ButtonFrame,
            text="Back",
            font=Small_Font,
            command=lambda: [
                self.parent._stack.setCurrentWidget(self.parent.frames[QAreport_Page]),
                self.parent.frames[QAreport_Page].build_UI(),
                ErrorMessagesLabel.place_forget(),
                ErrorMessagesText.place_forget(),
            ],
        )
        BackButton.pack(side="top", pady=5, ipadx=5, ipady=5, fill="x")

        QuitButton = tk.Button(
            ButtonFrame, text="Quit", font=Small_Font, command=lambda: [quit()]
        )
        QuitButton.pack(side="top", pady=20, ipadx=5, ipady=5, fill="x")

        # =============================================================================
        # Patient Information Section
        # =============================================================================
        SubjectName = fields["Name"]
        FilePath, FileName = fields["Path"], fields["Filename"]

        InfoFrame = tk.Frame(ContentFrame)
        InfoFrame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        InfoFrame.columnconfigure(1, weight=1)

        tk.Label(InfoFrame, text="Static File-", font=Small_Font).grid(row=0, column=0, sticky="w", padx=5)
        StaticFile = tk.Label(InfoFrame, text=str(FileName + ".c3d"), font=Small_Font)
        StaticFile.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(InfoFrame, text="Model-", font=Small_Font).grid(row=1, column=0, sticky="w", padx=5)
        FilePath, FileName = fields["Path"], fields["Filename"]
        Model = tk.Label(InfoFrame, text="Shriners Gait Model", font=Small_Font)
        Model.grid(row=1, column=1, sticky="w", padx=5)

        tk.Label(InfoFrame, text="User Preference", font=Small_Font).grid(row=2, column=0, sticky="w", padx=5)
        UserPreference = tk.Label(
            InfoFrame, text=UserPreferencesFileName, font=Smaller_Font, anchor="w"
        )
        UserPreference.grid(row=2, column=1, sticky="w", padx=5)

        # Warnings Area
        WarningFrame = tk.LabelFrame(ContentFrame, text="Warnings", font=Bold_Small_Font, fg="red")
        WarningFrame.grid(row=1, column=0, sticky="ew", pady=10)
        WarningFrame.columnconfigure(0, weight=1)

        ErrorMessagesLabel = tk.Label(WarningFrame, text="", font=Bold_Small_Font, fg="red")
        # ErrorMessagesLabel.grid(row=0, column=0) 
        
        ErrorMessagesText = tk.Text(WarningFrame, height=3, state="disabled", fg="red", bg="#f0f0f0")
        ErrorMessagesText.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        SaveErrorMessagesLabel = tk.Label(
            WarningFrame, text="Warning", font=Small_Font, anchor="w", fg="red"
        )
        # SaveErrorMessagesLabel.grid(row=1, column=0, sticky="w")

        # =============================================================================
        # Posture Information Form
        # =============================================================================
        PostureFrame = tk.LabelFrame(ContentFrame, text="Standing Posture (degrees)", font=Large_Font)
        PostureFrame.grid(row=2, column=0, sticky="nsew", pady=10)
        PostureFrame.columnconfigure(1, weight=1) # Left
        PostureFrame.columnconfigure(2, weight=1) # Right

        # Headers
        tk.Label(PostureFrame, text="Left", font=Bold_Small_Font).grid(row=0, column=1)
        tk.Label(PostureFrame, text="Right", font=Bold_Small_Font).grid(row=0, column=2)

        row_idx = 1
        pad_opts = {'padx': 5, 'pady': 2}
        entry_opts = {'justify': 'center', 'width': 10}

        def add_row(label_text, var_left_name, var_right_name, row):
            tk.Label(PostureFrame, text=label_text, font=Small_Font, anchor="e").grid(row=row, column=0, sticky="e", **pad_opts, ipadx=5)
            left_entry = tk.Entry(PostureFrame, **entry_opts)
            left_entry.grid(row=row, column=1, **pad_opts)
            right_entry = tk.Entry(PostureFrame, **entry_opts)
            right_entry.grid(row=row, column=2, **pad_opts)
            return left_entry, right_entry

        # Trunk
        LeftTrunkObliquity, RightTrunkObliquity = add_row("Trunk Obliquity", "LeftTrunkObliquity", "RightTrunkObliquity", row_idx); row_idx += 1
        LeftTrunkTilt, RightTrunkTilt = add_row("Trunk Tilt", "LeftTrunkTilt", "RightTrunkTilt", row_idx); row_idx += 1
        LeftTrunkRotation, RightTrunkRotation = add_row("Trunk Rotation", "LeftTrunkRotation", "RightTrunkRotation", row_idx); row_idx += 1

        # Pelvis
        LeftPelvisObliquity, RightPelvisObliquity = add_row("Pelvic Obliquity", "LeftPelvisObliquity", "RightPelvisObliquity", row_idx); row_idx += 1
        LeftPelvisTilt, RightPelvisTilt = add_row("Pelvic Tilt", "LeftPelvisTilt", "RightPelvisTilt", row_idx); row_idx += 1
        LeftPelvisRotation, RightPelvisRotation = add_row("Pelvic Rotation", "LeftPelvisRotation", "RightPelvisRotation", row_idx); row_idx += 1

        # Hip
        LeftHipAbAdduction, RightHipAbAdduction = add_row("Hip Ab/Adduction", "LeftHipAbAdduction", "RightHipAbAdduction", row_idx); row_idx += 1
        LeftHipFlexExtension, RightHipFlexExtension = add_row("Hip Flex/Extension", "LeftHipFlexExtension", "RightHipFlexExtension", row_idx); row_idx += 1
        LeftHipIntExtRotation, RightHipIntExtRotation = add_row("Hip Int/Ext Rotation", "LeftHipIntExtRotation", "RightHipIntExtRotation", row_idx); row_idx += 1

        # Knee
        LeftKneeVarusValgus, RightKneeVarusValgus = add_row("Knee Varus/Valgus", "LeftKneeVarusValgus", "RightKneeVarusValgus", row_idx); row_idx += 1
        LeftKneeFlexExtension, RightKneeFlexExtension = add_row("Knee Flex/Extension", "LeftKneeFlexExtension", "RightKneeFlexExtension", row_idx); row_idx += 1
        LeftKneeIntExtRotation, RightKneeIntExtRotation = add_row("Knee Int/Ext Rotation", "LeftKneeIntExtRotation", "RightKneeIntExtRotation", row_idx); row_idx += 1
        LeftKneeProgression, RightKneeProgression = add_row("Knee Progression", "LeftKneeProgression", "RightKneeProgression", row_idx); row_idx += 1

        # Ankle
        LeftAnklePlantarDorsiflexion, RightAnklePlantarDorsiflexion = add_row("Ankle Plantar/Dorsiflexion", "LeftAnklePlantarDorsiflexion", "RightAnklePlantarDorsiflexion", row_idx); row_idx += 1
        LeftAnkleIntExtRotation, RightAnkleIntExtRotation = add_row("Ankle Int/Ext Rotation", "LeftAnkleIntExtRotation", "RightAnkleIntExtRotation", row_idx); row_idx += 1

        # Foot
        LeftFootProgression, RightFootProgression = add_row("Foot Progression", "LeftFootProgression", "RightFootProgression", row_idx); row_idx += 1

        # Foot Segments Header
        tk.Label(PostureFrame, text="Foot Segments", font=Bold_Small_Font, anchor="w").grid(row=row_idx, column=0, sticky="w", padx=5, pady=(10, 5))
        row_idx += 1

        # Hindfoot
        LeftHindfootPitch, RightHindfootPitch = add_row("Hindfoot Pitch", "LeftHindfootPitch", "RightHindfootPitch", row_idx); row_idx += 1
        LeftHindfootProgression, RightHindfootProgression = add_row("Hindfoot Progression", "LeftHindfootProgression", "RightHindfootProgression", row_idx); row_idx += 1
        LeftHindfootInvEversion, RightHindfootInvEversion = add_row("Hindfoot Varus/Valgus", "LeftHindfootInvEversion", "RightHindfootInvEversion", row_idx); row_idx += 1

        # Ankle Complex
        LeftAnkleComplexInvEversion, RightAnkleComplexInvEversion = add_row("Ankle Complex Varus/Valgus", "LeftAnkleComplexInvEversion", "RightAnkleComplexInvEversion", row_idx); row_idx += 1

        # Forefoot
        LeftForefootPitch, RightForefootPitch = add_row("Forefoot Pitch", "LeftForefootPitch", "RightForefootPitch", row_idx); row_idx += 1
        LeftForefootProgression, RightForefootProgression = add_row("Forefoot Progression", "LeftForefootProgression", "RightForefootProgression", row_idx); row_idx += 1

        # Midfoot
        LeftMidfootAbAdduction, RightMidfootAbAdduction = add_row("Midfoot Complex Ab/Adduction", "LeftMidfootAbAdduction", "RightMidfootAbAdduction", row_idx); row_idx += 1

        # Hallux
        LeftHalluxProgression, RightHalluxProgression = add_row("MTP1 Varus/Valgus", "LeftHalluxProgression", "RightHalluxProgression", row_idx); row_idx += 1

        # Tibial Torsion
        tk.Label(PostureFrame, text="Tibial Torsion", font=Bold_Small_Font, anchor="w").grid(row=row_idx, column=0, sticky="w", padx=5, pady=(10, 5))
        row_idx += 1
        LeftTibiaTorsion, RightTibiaTorsion = add_row("Tibial Torsion (degrees)", "LeftTibiaTorsion", "RightTibiaTorsion", row_idx); row_idx += 1
        # =============================================================================

        # =============================================================================
        #       Posture Measures are computed from Marker data
        # =============================================================================
        # Extract Nexus first frame
        StartFrame, EndFrame = fields["First Frame"], fields["Last Frame"]

        # Extract Clinical Values
        exec(open(StaticDataFileName).read())
        normalize_processing_measurements(self)

        # For Sacral Triad Case, delete Sacral Marker Name
        # Explanation: When Sacral marker is used and exists in the UserPreferences, then
        # Sacral Marker Name is deleted to push the code towards using PSIS markers.
        if self.valuePelvicFixCheck == "2":
            try:
                del self.SacralMarkerName
            except:
                pass
        else:
            pass

        # =============================================================================
        #         Read Marker data from Start Frame (First Frame) for Static Check
        #         Dispplay Warning if marker not found
        # =============================================================================
        def HasTrajectory(self, subjectName, markerName):
            return markerName in fields

        # Function to extract markerdata into an array and check if data exists
        def MarkerCheck(Subject, MarkerName, FirstFrame):
            # Check if marker exists at all
            if self.HasTrajectory(Subject, MarkerName) is True:
                MarkerData = np.array(
                    (
                        fields[MarkerName]["X"][FirstFrame],
                        fields[MarkerName]["Y"][FirstFrame],
                        fields[MarkerName]["Z"][FirstFrame],
                    )
                )
                # Check if marker is labeled at the first frame
                if MarkerData[0] == 0 or MarkerData[1] == 0 or MarkerData[2] == 0:
                    ErrorMessagesLabel.place(x=50, y=100, width=130, height=85)
                    ErrorMessagesText.place(x=195, y=95, width=490, height=85)
                    ErrorMessage = (
                        "Marker "
                        + MarkerName
                        + " is not labeled at frame "
                        + str(FirstFrame)
                        + "\n"
                    )
                    ErrorMessagesText.insert(tk.END, ErrorMessage)
            else:
                MarkerData = np.array([0, 0, 0])
                # Dont show error for Trunk Markers
                ExcludedForErrorMarkerNames = [
                    self.C7MarkerName,
                    self.LeftClavicleMarkerName,
                    self.RightClavicleMarkerName,
                ]
                # Add anatomical foot model markers to Excluded list if Sitting Foot Static.py exists
                if os.path.exists(SittingFootStaticDataFileName):
                    ExcludedForErrorMarkerNames = [
                        self.C7MarkerName,
                        self.LeftClavicleMarkerName,
                        self.RightClavicleMarkerName,
                        self.Left23MetatarsalBaseMarkerName,
                        self.Left23MetatarsalHeadMarkerName,
                        self.LeftFirstMetatarsalMedialBaseMarkerName,
                        self.LeftFirstMetatarsalMedialHeadMarkerName,
                        self.LeftCalcanealPeronealTrochleaMarkerName,
                        self.LeftFirstMetatarsoPhalangealJointMarkerName,
                        self.Right23MetatarsalBaseMarkerName,
                        self.Right23MetatarsalHeadMarkerName,
                        self.RightFirstMetatarsalMedialBaseMarkerName,
                        self.RightFirstMetatarsalMedialHeadMarkerName,
                        self.RightCalcanealPeronealTrochleaMarkerName,
                        self.RightFirstMetatarsoPhalangealJointMarkerName,
                    ]
                if (
                    MarkerName not in ExcludedForErrorMarkerNames
                    and MarkerName.split(".")[0] not in ExcludedForErrorMarkerNames
                ):
                    ErrorMessagesLabel.place(x=50, y=100, width=130, height=85)
                    ErrorMessagesText.place(x=195, y=95, width=490, height=85)
                    ErrorMessage = "Marker " + MarkerName + " is not Found " + "\n"
                    ErrorMessagesText.insert(tk.END, ErrorMessage)
            return MarkerData

        C7Marker = MarkerCheck(
            SubjectName, self.C7MarkerName, int(self.valueStaticFrameNumber)
        )
        LeftClavicleMarker = MarkerCheck(
            SubjectName, self.LeftClavicleMarkerName, int(self.valueStaticFrameNumber)
        )
        RightClavicleMarker = MarkerCheck(
            SubjectName, self.RightClavicleMarkerName, int(self.valueStaticFrameNumber)
        )
        # =============================================================================
        #       Determine if Trunk Data is Available
        # =============================================================================
        if (C7Marker[2] * LeftClavicleMarker[2] * RightClavicleMarker[2]) > 0:
            TrunkFlag = 1
        else:
            TrunkFlag = 0
        ##############################################################################
        try:
            SacralMarker = MarkerCheck(
                SubjectName, self.SacralMarkerName, int(self.valueStaticFrameNumber)
            )
        except:
            # Compute Sacral Marker as mid point of PSIS markers
            LeftPSISMarker = MarkerCheck(
                SubjectName, self.LeftPSISMarkerName, int(self.valueStaticFrameNumber)
            )
            RightPSISMarker = MarkerCheck(
                SubjectName, self.RightPSISMarkerName, int(self.valueStaticFrameNumber)
            )
            SacralMarker = (LeftPSISMarker + RightPSISMarker) / 2
        LeftASISMarker = MarkerCheck(
            SubjectName, self.LeftASISMarkerName, int(self.valueStaticFrameNumber)
        )
        LeftThighMarker = MarkerCheck(
            SubjectName, self.LeftThighMarkerName, int(self.valueStaticFrameNumber)
        )
        LeftTibialMarker = MarkerCheck(
            SubjectName, self.LeftTibialMarkerName, int(self.valueStaticFrameNumber)
        )
        LeftLateralAnkleMarker = MarkerCheck(
            SubjectName,
            self.LeftLateralAnkleMarkerName,
            int(self.valueStaticFrameNumber),
        )
        LeftToeMarker = MarkerCheck(
            SubjectName, self.LeftToeMarkerName, int(self.valueStaticFrameNumber)
        )
        LeftMedialAnkleMarker = MarkerCheck(
            SubjectName,
            self.LeftMedialAnkleMarkerName,
            int(self.valueStaticFrameNumber),
        )
        LeftHeelMarker = MarkerCheck(
            SubjectName, self.LeftHeelMarkerName, int(self.valueStaticFrameNumber)
        )
        if self.valueKneeAlignmentCheck == "0":
            LeftLateralKADMarker = MarkerCheck(
                SubjectName,
                self.LeftLateralKADMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftUpperKADMarker = MarkerCheck(
                SubjectName,
                self.LeftUpperKADMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftLowerKADMarker = MarkerCheck(
                SubjectName,
                self.LeftLowerKADMarkerName,
                int(self.valueStaticFrameNumber),
            )
        else:
            LeftLateralKneeMarker = MarkerCheck(
                SubjectName,
                self.LeftLateralKneeMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftMedialKneeMarker = MarkerCheck(
                SubjectName,
                self.LeftMedialKneeMarkerName,
                int(self.valueStaticFrameNumber),
            )

        # Read Left Foot Markers
        if self.valueLeftFootModelCheck == "1":
            LeftLateralCalcaneusMarker = MarkerCheck(
                SubjectName,
                self.LeftLateralCalcaneusMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftMedialCalcaneusMarker = MarkerCheck(
                SubjectName,
                self.LeftMedialCalcaneusMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftPosteriorCalcaneusMarker = MarkerCheck(
                SubjectName,
                self.LeftPosteriorCalcaneusMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftFirstMetarsalBaseMarker = MarkerCheck(
                SubjectName,
                self.LeftFirstMetarsalBaseMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftFirstMetarsalHeadMarker = MarkerCheck(
                SubjectName,
                self.LeftFirstMetarsalHeadMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftFifthMetarsalHeadMarker = MarkerCheck(
                SubjectName,
                self.LeftFifthMetarsalHeadMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftHalluxMarker = MarkerCheck(
                SubjectName, self.LeftHalluxMarkerName, int(self.valueStaticFrameNumber)
            )
            Left23MetatarsalBaseMarker = MarkerCheck(
                SubjectName,
                self.Left23MetatarsalBaseMarkerName,
                int(self.valueStaticFrameNumber),
            )
            Left23MetatarsalHeadMarker = MarkerCheck(
                SubjectName,
                self.Left23MetatarsalHeadMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftFirstMetatarsalMedialBaseMarker = MarkerCheck(
                SubjectName,
                self.LeftFirstMetatarsalMedialBaseMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftFirstMetatarsalMedialHeadMarker = MarkerCheck(
                SubjectName,
                self.LeftFirstMetatarsalMedialHeadMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftCalcanealPeronealTrochleaMarker = MarkerCheck(
                SubjectName,
                self.LeftCalcanealPeronealTrochleaMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftFirstMetatarsoPhalangealJointMarker = MarkerCheck(
                SubjectName,
                self.LeftFirstMetatarsoPhalangealJointMarkerName,
                int(self.valueStaticFrameNumber),
            )

        RightASISMarker = MarkerCheck(
            SubjectName, self.RightASISMarkerName, int(self.valueStaticFrameNumber)
        )
        RightThighMarker = MarkerCheck(
            SubjectName, self.RightThighMarkerName, int(self.valueStaticFrameNumber)
        )
        RightTibialMarker = MarkerCheck(
            SubjectName, self.RightTibialMarkerName, int(self.valueStaticFrameNumber)
        )
        RightLateralAnkleMarker = MarkerCheck(
            SubjectName,
            self.RightLateralAnkleMarkerName,
            int(self.valueStaticFrameNumber),
        )
        RightToeMarker = MarkerCheck(
            SubjectName, self.RightToeMarkerName, int(self.valueStaticFrameNumber)
        )
        RightMedialAnkleMarker = MarkerCheck(
            SubjectName,
            self.RightMedialAnkleMarkerName,
            int(self.valueStaticFrameNumber),
        )
        RightHeelMarker = MarkerCheck(
            SubjectName, self.RightHeelMarkerName, int(self.valueStaticFrameNumber)
        )
        if self.valueKneeAlignmentCheck == "0":
            RightLateralKADMarker = MarkerCheck(
                SubjectName,
                self.RightLateralKADMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightUpperKADMarker = MarkerCheck(
                SubjectName,
                self.RightUpperKADMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightLowerKADMarker = MarkerCheck(
                SubjectName,
                self.RightLowerKADMarkerName,
                int(self.valueStaticFrameNumber),
            )
        else:
            RightLateralKneeMarker = MarkerCheck(
                SubjectName,
                self.RightLateralKneeMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightMedialKneeMarker = MarkerCheck(
                SubjectName,
                self.RightMedialKneeMarkerName,
                int(self.valueStaticFrameNumber),
            )

        # Read Right Foot Markers
        if self.valueRightFootModelCheck == "1":
            RightLateralCalcaneusMarker = MarkerCheck(
                SubjectName,
                self.RightLateralCalcaneusMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightMedialCalcaneusMarker = MarkerCheck(
                SubjectName,
                self.RightMedialCalcaneusMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightPosteriorCalcaneusMarker = MarkerCheck(
                SubjectName,
                self.RightPosteriorCalcaneusMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightFirstMetarsalBaseMarker = MarkerCheck(
                SubjectName,
                self.RightFirstMetarsalBaseMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightFirstMetarsalHeadMarker = MarkerCheck(
                SubjectName,
                self.RightFirstMetarsalHeadMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightFifthMetarsalHeadMarker = MarkerCheck(
                SubjectName,
                self.RightFifthMetarsalHeadMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightHalluxMarker = MarkerCheck(
                SubjectName,
                self.RightHalluxMarkerName,
                int(self.valueStaticFrameNumber),
            )
            Right23MetatarsalBaseMarker = MarkerCheck(
                SubjectName,
                self.Right23MetatarsalBaseMarkerName,
                int(self.valueStaticFrameNumber),
            )
            Right23MetatarsalHeadMarker = MarkerCheck(
                SubjectName,
                self.Right23MetatarsalHeadMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightFirstMetatarsalMedialBaseMarker = MarkerCheck(
                SubjectName,
                self.RightFirstMetatarsalMedialBaseMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightFirstMetatarsalMedialHeadMarker = MarkerCheck(
                SubjectName,
                self.RightFirstMetatarsalMedialHeadMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightCalcanealPeronealTrochleaMarker = MarkerCheck(
                SubjectName,
                self.RightCalcanealPeronealTrochleaMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightFirstMetatarsoPhalangealJointMarker = MarkerCheck(
                SubjectName,
                self.RightFirstMetatarsoPhalangealJointMarkerName,
                int(self.valueStaticFrameNumber),
            )
        # =============================================================================

        # Read orientation of the Standing patient relative to laboratory coordinate system
        # print(self.StaticForwardDirection)
        if self.StaticForwardDirection == "+X":
            RotationMatrix = np.array(
                [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
            )
        if self.StaticForwardDirection == "-X":
            RotationMatrix = np.array(
                [[-1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0]]
            )
        if self.StaticForwardDirection == "+Y":
            RotationMatrix = np.array(
                [[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
            )
        if self.StaticForwardDirection == "-Y":
            RotationMatrix = np.array(
                [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
            )

        # Transform marker data if necessary based on direction that the patient is facing
        C7Marker = RotationMatrix.dot(C7Marker)
        LeftClavicleMarker = RotationMatrix.dot(LeftClavicleMarker)
        RightClavicleMarker = RotationMatrix.dot(RightClavicleMarker)
        SacralMarker = RotationMatrix.dot(SacralMarker)
        LeftASISMarker = RotationMatrix.dot(LeftASISMarker)
        LeftThighMarker = RotationMatrix.dot(LeftThighMarker)
        LeftTibialMarker = RotationMatrix.dot(LeftTibialMarker)
        LeftLateralAnkleMarker = RotationMatrix.dot(LeftLateralAnkleMarker)
        LeftToeMarker = RotationMatrix.dot(LeftToeMarker)
        LeftMedialAnkleMarker = RotationMatrix.dot(LeftMedialAnkleMarker)
        LeftHeelMarker = RotationMatrix.dot(LeftHeelMarker)
        if self.valueKneeAlignmentCheck == "0":
            LeftLateralKADMarker = RotationMatrix.dot(LeftLateralKADMarker)
            LeftUpperKADMarker = RotationMatrix.dot(LeftUpperKADMarker)
            LeftLowerKADMarker = RotationMatrix.dot(LeftLowerKADMarker)
        else:
            LeftLateralKneeMarker = RotationMatrix.dot(LeftLateralKneeMarker)
            LeftMedialKneeMarker = RotationMatrix.dot(LeftMedialKneeMarker)

        if self.valueLeftFootModelCheck == "1":
            LeftLateralCalcaneusMarker = RotationMatrix.dot(LeftLateralCalcaneusMarker)
            LeftMedialCalcaneusMarker = RotationMatrix.dot(LeftMedialCalcaneusMarker)
            LeftPosteriorCalcaneusMarker = RotationMatrix.dot(
                LeftPosteriorCalcaneusMarker
            )
            LeftFirstMetarsalBaseMarker = RotationMatrix.dot(
                LeftFirstMetarsalBaseMarker
            )
            LeftFirstMetarsalHeadMarker = RotationMatrix.dot(
                LeftFirstMetarsalHeadMarker
            )
            LeftFifthMetarsalHeadMarker = RotationMatrix.dot(
                LeftFifthMetarsalHeadMarker
            )
            LeftHalluxMarker = RotationMatrix.dot(LeftHalluxMarker)
            Left23MetatarsalBaseMarker = RotationMatrix.dot(Left23MetatarsalBaseMarker)
            Left23MetatarsalHeadMarker = RotationMatrix.dot(Left23MetatarsalHeadMarker)
            LeftFirstMetatarsalMedialBaseMarker = RotationMatrix.dot(
                LeftFirstMetatarsalMedialBaseMarker
            )
            LeftFirstMetatarsalMedialHeadMarker = RotationMatrix.dot(
                LeftFirstMetatarsalMedialHeadMarker
            )
            LeftCalcanealPeronealTrochleaMarker = RotationMatrix.dot(
                LeftCalcanealPeronealTrochleaMarker
            )
            LeftFirstMetatarsoPhalangealJointMarker = RotationMatrix.dot(
                LeftFirstMetatarsoPhalangealJointMarker
            )

        RightASISMarker = RotationMatrix.dot(RightASISMarker)
        RightThighMarker = RotationMatrix.dot(RightThighMarker)
        RightTibialMarker = RotationMatrix.dot(RightTibialMarker)
        RightLateralAnkleMarker = RotationMatrix.dot(RightLateralAnkleMarker)
        RightToeMarker = RotationMatrix.dot(RightToeMarker)
        RightMedialAnkleMarker = RotationMatrix.dot(RightMedialAnkleMarker)
        RightHeelMarker = RotationMatrix.dot(RightHeelMarker)
        if self.valueKneeAlignmentCheck == "0":
            RightLateralKADMarker = RotationMatrix.dot(RightLateralKADMarker)
            RightUpperKADMarker = RotationMatrix.dot(RightUpperKADMarker)
            RightLowerKADMarker = RotationMatrix.dot(RightLowerKADMarker)
        else:
            RightLateralKneeMarker = RotationMatrix.dot(RightLateralKneeMarker)
            RightMedialKneeMarker = RotationMatrix.dot(RightMedialKneeMarker)

        if self.valueRightFootModelCheck == "1":
            RightLateralCalcaneusMarker = RotationMatrix.dot(
                RightLateralCalcaneusMarker
            )
            RightMedialCalcaneusMarker = RotationMatrix.dot(RightMedialCalcaneusMarker)
            RightPosteriorCalcaneusMarker = RotationMatrix.dot(
                RightPosteriorCalcaneusMarker
            )
            RightFirstMetarsalBaseMarker = RotationMatrix.dot(
                RightFirstMetarsalBaseMarker
            )
            RightFirstMetarsalHeadMarker = RotationMatrix.dot(
                RightFirstMetarsalHeadMarker
            )
            RightFifthMetarsalHeadMarker = RotationMatrix.dot(
                RightFifthMetarsalHeadMarker
            )
            RightHalluxMarker = RotationMatrix.dot(RightHalluxMarker)
            Right23MetatarsalBaseMarker = RotationMatrix.dot(
                Right23MetatarsalBaseMarker
            )
            Right23MetatarsalHeadMarker = RotationMatrix.dot(
                Right23MetatarsalHeadMarker
            )
            RightFirstMetatarsalMedialBaseMarker = RotationMatrix.dot(
                RightFirstMetatarsalMedialBaseMarker
            )
            RightFirstMetatarsalMedialHeadMarker = RotationMatrix.dot(
                RightFirstMetatarsalMedialHeadMarker
            )
            RightCalcanealPeronealTrochleaMarker = RotationMatrix.dot(
                RightCalcanealPeronealTrochleaMarker
            )
            RightFirstMetatarsoPhalangealJointMarker = RotationMatrix.dot(
                RightFirstMetatarsoPhalangealJointMarker
            )

        # Compute Technical Coordinate System: Trunk
        if TrunkFlag == 1:
            if (
                C7Marker[2] != 0
                and LeftClavicleMarker[2] != 0
                and RightClavicleMarker[2] != 0
                and LeftASISMarker[2] != 0
                and RightASISMarker[2] != 0
                and SacralMarker[2] != 0
            ):
                [ETrunkTech, PelvicCenterLab, ShouldersCenterLab] = (
                    gait.TechCS_Trunk_Newington(
                        C7Marker,
                        LeftClavicleMarker,
                        RightClavicleMarker,
                        LeftASISMarker,
                        RightASISMarker,
                        SacralMarker,
                    )
                )
        else:
            ETrunkTech = np.eye(3)
        # print(ETrunkTech)
        # print(PelvicCenterLab)
        # print(ShouldersCenterLab)

        # Compute Technical Coordinate System: Pelvis
        [EPelvisTech, MidASISLab] = gait.TechCS_Pelvis_Newington(
            LeftASISMarker, RightASISMarker, SacralMarker
        )
        # print(EPelvisTech)
        # print(MidASISLab)

        # Normalize HipModelName and ShankCoordinateSystem
        _hip_name = str(getattr(self, "HipModelName", "Harrington2")).strip()
        if "harrington2" in _hip_name.lower():
            self.HipModelName = "Harrington2"
        elif "harrington" in _hip_name.lower():
            self.HipModelName = "Harrington"
        elif "newington" in _hip_name.lower() or "davis" in _hip_name.lower():
            self.HipModelName = "Newington"
        else:
            self.HipModelName = "Harrington2"

        _shank_name = str(getattr(self, "ShankCoordinateSystem", "Distal")).strip()
        if "proximal" in _shank_name.lower():
            self.ShankCoordinateSystem = "Proximal"
        else:
            self.ShankCoordinateSystem = "Distal"

        # Compute Hip Center Location, relative to midASIS point and expressed relative to pelvic coor system
        if self.HipModelName == "Newington":
            # Newington
            [LeftHipCenterPelvis, LeftHipCenterLab] = (
                gait.JointCenterModel_Hip_Newington(
                    "Left",
                    self.MarkerDiameter,
                    self.valueASISdist,
                    self.valueLeftASIStoGTdist,
                    self.valueLeftLegLength,
                    self.valueRightLegLength,
                    RightASISMarker,
                    LeftASISMarker,
                    EPelvisTech,
                    MidASISLab,
                )
            )
            [RightHipCenterPelvis, RightHipCenterLab] = (
                gait.JointCenterModel_Hip_Newington(
                    "Right",
                    self.MarkerDiameter,
                    self.valueASISdist,
                    self.valueRightASIStoGTdist,
                    self.valueLeftLegLength,
                    self.valueRightLegLength,
                    RightASISMarker,
                    LeftASISMarker,
                    EPelvisTech,
                    MidASISLab,
                )
            )
        if self.HipModelName == "Harrington":
            # Harrington Hip Model
            [LeftHipCenterPelvis, LeftHipCenterLab] = (
                gait.JointCenterModel_Hip_Harrington(
                    "Left",
                    self.valueASISdist,
                    RightASISMarker,
                    LeftASISMarker,
                    SacralMarker,
                    EPelvisTech,
                    MidASISLab,
                )
            )
            [RightHipCenterPelvis, RightHipCenterLab] = (
                gait.JointCenterModel_Hip_Harrington(
                    "Right",
                    self.valueASISdist,
                    RightASISMarker,
                    LeftASISMarker,
                    SacralMarker,
                    EPelvisTech,
                    MidASISLab,
                )
            )
        if self.HipModelName == "Harrington2":
            # Harrington Hip Model- 2 variable
            [LeftHipCenterPelvis, LeftHipCenterLab] = (
                gait.JointCenterModel_Hip_Harrington2(
                    "Left",
                    self.valueASISdist,
                    self.valueLeftLegLength,
                    self.valueRightLegLength,
                    RightASISMarker,
                    LeftASISMarker,
                    SacralMarker,
                    EPelvisTech,
                    MidASISLab,
                )
            )
            [RightHipCenterPelvis, RightHipCenterLab] = (
                gait.JointCenterModel_Hip_Harrington2(
                    "Right",
                    self.valueASISdist,
                    self.valueLeftLegLength,
                    self.valueRightLegLength,
                    RightASISMarker,
                    LeftASISMarker,
                    SacralMarker,
                    EPelvisTech,
                    MidASISLab,
                )
            )
        # print(LeftHipCenterPelvis)
        # print(LeftHipCenterLab)
        # print(RightHipCenterPelvis)
        # print(RightHipCenterLab)

        if self.valueKneeAlignmentCheck == "0":
            # Compute Location of Virtual Knee Marker (based on cluster-type knee fixture)
            LeftVirtualKneeMarkerLab = gait.ComputeVirtualKneeMarker_Newington(
                "Left",
                self.MarkerDiameter,
                LeftUpperKADMarker,
                LeftLateralKADMarker,
                LeftLowerKADMarker,
            )
            RightVirtualKneeMarkerLab = gait.ComputeVirtualKneeMarker_Newington(
                "Right",
                self.MarkerDiameter,
                RightUpperKADMarker,
                RightLateralKADMarker,
                RightLowerKADMarker,
            )
            # print(LeftVirtualKneeMarkerLab)
            # print(RightVirtualKneeMarkerLab)
        else:
            LeftVirtualKneeMarkerLab = LeftLateralKneeMarker
            RightVirtualKneeMarkerLab = RightLateralKneeMarker

        # Compute Technical Coordinate System: Thigh
        LeftEThighTech = gait.TechCS_Thigh_Newington(
            "Left", LeftHipCenterLab, LeftThighMarker, LeftVirtualKneeMarkerLab
        )
        RightEThighTech = gait.TechCS_Thigh_Newington(
            "Right", RightHipCenterLab, RightThighMarker, RightVirtualKneeMarkerLab
        )
        # print(LeftEThighTech)
        # print(RightEThighTech)

        if self.valueKneeAlignmentCheck == "0":
            # Compute Location of Knee Center (in lab space)
            LeftKneeCenterLab = gait.JointCenterModel_Knee_Newington(
                "Left",
                self.MarkerDiameter,
                self.valueLeftKneeWidth,
                LeftVirtualKneeMarkerLab,
                LeftLateralKADMarker,
            )
            RightKneeCenterLab = gait.JointCenterModel_Knee_Newington(
                "Right",
                self.MarkerDiameter,
                self.valueRightKneeWidth,
                RightVirtualKneeMarkerLab,
                RightLateralKADMarker,
            )
            # print(LeftKneeCenterLab)
            # print(RightKneeCenterLab)
        else:
            E1 = math.ComputeUnitVecFromPts(LeftLateralKneeMarker, LeftMedialKneeMarker)
            LeftKneeCenterLab = (
                LeftLateralKneeMarker
                + (float(self.valueLeftKneeWidth) / 2 + float(self.MarkerDiameter) / 2)
                * E1
            )
            E1 = math.ComputeUnitVecFromPts(
                RightLateralKneeMarker, RightMedialKneeMarker
            )
            RightKneeCenterLab = (
                RightLateralKneeMarker
                + (float(self.valueRightKneeWidth) / 2 + float(self.MarkerDiameter) / 2)
                * E1
            )

        # Compute Knee Center Location Relative to the Thigh Coordinates
        LeftKneeCenterThigh = math.TransformPointIntoMovingCoors(
            LeftKneeCenterLab, LeftEThighTech, LeftVirtualKneeMarkerLab
        )
        RightKneeCenterThigh = math.TransformPointIntoMovingCoors(
            RightKneeCenterLab, RightEThighTech, RightVirtualKneeMarkerLab
        )
        # print(LeftKneeCenterThigh)
        # print(RightKneeCenterThigh)

        # Compute Technical Coordinate System: Shank
        # Use Tibial triad if markers available
        if (
            self.HasTrajectory(SubjectName, self.LeftTibialMarkerName) is True
            and self.HasTrajectory(SubjectName, self.LeftTibialUpperMarkerName) is True
            and self.HasTrajectory(SubjectName, self.LeftTibialLowerMarkerName) is True
        ):
            LeftTibialTriadCheck = True
            LeftTibialUpperMarker = MarkerCheck(
                SubjectName,
                self.LeftTibialUpperMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftTibialLowerMarker = MarkerCheck(
                SubjectName,
                self.LeftTibialLowerMarkerName,
                int(self.valueStaticFrameNumber),
            )
            LeftTibialUpperMarker = RotationMatrix.dot(LeftTibialUpperMarker)
            LeftTibialLowerMarker = RotationMatrix.dot(LeftTibialLowerMarker)
            LeftEShankTech = gait.TechCS_Shank_Newington(
                "Left", LeftTibialUpperMarker, LeftTibialLowerMarker, LeftTibialMarker
            )
        else:
            LeftTibialTriadCheck = False
            LeftEShankTech = gait.TechCS_Shank_Newington(
                "Left", LeftKneeCenterLab, LeftTibialMarker, LeftLateralAnkleMarker
            )
        if (
            self.HasTrajectory(SubjectName, self.RightTibialMarkerName) is True
            and self.HasTrajectory(SubjectName, self.RightTibialUpperMarkerName) is True
            and self.HasTrajectory(SubjectName, self.RightTibialLowerMarkerName) is True
        ):
            RightTibialTriadCheck = True
            RightTibialUpperMarker = MarkerCheck(
                SubjectName,
                self.RightTibialUpperMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightTibialLowerMarker = MarkerCheck(
                SubjectName,
                self.RightTibialLowerMarkerName,
                int(self.valueStaticFrameNumber),
            )
            RightTibialUpperMarker = RotationMatrix.dot(RightTibialUpperMarker)
            RightTibialLowerMarker = RotationMatrix.dot(RightTibialLowerMarker)
            RightEShankTech = gait.TechCS_Shank_Newington(
                "Right",
                RightTibialUpperMarker,
                RightTibialLowerMarker,
                RightTibialMarker,
            )
        else:
            RightTibialTriadCheck = False
            RightEShankTech = gait.TechCS_Shank_Newington(
                "Right", RightKneeCenterLab, RightTibialMarker, RightLateralAnkleMarker
            )
        # print(LeftEShankTech)
        # print(RightEShankTech)

        # Compute Location of Ankle Center (in lab space)
        LeftAnkleCenterLab = gait.JointCenterModel_Ankle_Newington(
            "Left",
            self.MarkerDiameter,
            self.valueLeftAnkleWidth,
            LeftLateralAnkleMarker,
            LeftMedialAnkleMarker,
        )
        RightAnkleCenterLab = gait.JointCenterModel_Ankle_Newington(
            "Right",
            self.MarkerDiameter,
            self.valueRightAnkleWidth,
            RightLateralAnkleMarker,
            RightMedialAnkleMarker,
        )
        # print(LeftAnkleCenterLab)
        # print(RightAnkleCenterLab)

        # Compute Ankle Center Location Relative to Shank Coordinates and Lateral Ankle [Compared to Tibial Marker if Tibial Triad is used]
        if LeftTibialTriadCheck == True:
            LeftAnkleCenterShank = math.TransformPointIntoMovingCoors(
                LeftAnkleCenterLab, LeftEShankTech, LeftTibialMarker
            )
        else:
            LeftAnkleCenterShank = math.TransformPointIntoMovingCoors(
                LeftAnkleCenterLab, LeftEShankTech, LeftLateralAnkleMarker
            )
        if RightTibialTriadCheck == True:
            RightAnkleCenterShank = math.TransformPointIntoMovingCoors(
                RightAnkleCenterLab, RightEShankTech, RightTibialMarker
            )
        else:
            RightAnkleCenterShank = math.TransformPointIntoMovingCoors(
                RightAnkleCenterLab, RightEShankTech, RightLateralAnkleMarker
            )
        # print(LeftAnkleCenterShank)
        # print(RightAnkleCenterShank)

        # Compute Virtual Heel Marker
        LeftVirtualHeelMarkerLab = gait.ComputeVirtualHeelMarkerLab(
            self.valueLeftPlantigradeCheck,
            self.valueSujectShodCheck,
            self.valueLeftSoleThickness,
            LeftAnkleCenterLab,
            LeftToeMarker,
            LeftHeelMarker,
        )
        RightVirtualHeelMarkerLab = gait.ComputeVirtualHeelMarkerLab(
            self.valueRightPlantigradeCheck,
            self.valueSujectShodCheck,
            self.valueRightSoleThickness,
            RightAnkleCenterLab,
            RightToeMarker,
            RightHeelMarker,
        )
        # print(LeftVirtualHeelMarkerLab)
        # print(RightVirtualHeelMarkerLab)

        # Compute Technical Coordinate System: Foot
        LeftEFootTech = gait.TechCS_Foot_Newington(
            "Left", LeftKneeCenterLab, LeftAnkleCenterLab, LeftToeMarker
        )
        RightEFootTech = gait.TechCS_Foot_Newington(
            "Right", RightKneeCenterLab, RightAnkleCenterLab, RightToeMarker
        )
        # print(LeftEFootTech)
        # print(RightEFootTech)

        # Compute Technical Coordinate System: Left Foot Segments
        if self.valueLeftFootModelCheck == "1":
            LeftEHindfootTech = gait.TechCS_Hindfoot_mSHCG(
                "Left",
                LeftLateralCalcaneusMarker,
                LeftMedialCalcaneusMarker,
                LeftPosteriorCalcaneusMarker,
            )
            LeftEForefootTech = gait.TechCS_Forefoot_mSHCG(
                "Left",
                LeftFirstMetarsalBaseMarker,
                LeftFirstMetarsalHeadMarker,
                LeftFifthMetarsalHeadMarker,
            )
            if os.path.exists(SittingFootStaticDataFileName):
                exec(open(SittingFootStaticDataFileName).read())
                Left23MetatarsalHeadMarker = math.TransformPointIntoLabCoors(
                    self.valueLeft23MetatarsalHeadMarkerForefoot,
                    LeftEForefootTech,
                    LeftFirstMetarsalBaseMarker,
                )
                LeftFirstMetatarsoPhalangealJointMarker = (
                    math.TransformPointIntoLabCoors(
                        self.valueLeftFirstMetatarsoPhalangealJointMarkerForefoot,
                        LeftEForefootTech,
                        LeftFirstMetarsalBaseMarker,
                    )
                )
                exec(open(StaticDataFileName).read())
            LeftEHalluxTech = gait.TechCS_Hallux_mSHCG(
                "Left",
                LeftHalluxMarker,
                LeftFirstMetatarsoPhalangealJointMarker,
                Left23MetatarsalHeadMarker,
            )

            # print(LeftEHindfootTech)
            # print(LeftEForefootTech)
            # print(LeftEHalluxTech)

        # Compute Technical Coordinate System: Right Foot Segments
        if self.valueRightFootModelCheck == "1":
            RightEHindfootTech = gait.TechCS_Hindfoot_mSHCG(
                "Right",
                RightLateralCalcaneusMarker,
                RightMedialCalcaneusMarker,
                RightPosteriorCalcaneusMarker,
            )
            RightEForefootTech = gait.TechCS_Forefoot_mSHCG(
                "Right",
                RightFirstMetarsalBaseMarker,
                RightFirstMetarsalHeadMarker,
                RightFifthMetarsalHeadMarker,
            )
            if os.path.exists(SittingFootStaticDataFileName):
                exec(open(SittingFootStaticDataFileName).read())
                Right23MetatarsalHeadMarker = math.TransformPointIntoLabCoors(
                    self.valueRight23MetatarsalHeadMarkerForefoot,
                    RightEForefootTech,
                    RightFirstMetarsalBaseMarker,
                )
                RightFirstMetatarsoPhalangealJointMarker = (
                    math.TransformPointIntoLabCoors(
                        self.valueRightFirstMetatarsoPhalangealJointMarkerForefoot,
                        RightEForefootTech,
                        RightFirstMetarsalBaseMarker,
                    )
                )
                exec(open(StaticDataFileName).read())
            RightEHalluxTech = gait.TechCS_Hallux_mSHCG(
                "Right",
                RightHalluxMarker,
                RightFirstMetatarsoPhalangealJointMarker,
                Right23MetatarsalHeadMarker,
            )
            # print(RightEHindfootTech)
            # print(RightEForefootTech)
            # print(RightEHalluxTech)

        # Compute Anatomical Coordinate System: Trunk and Pelvis
        ETrunkAnat = ETrunkTech
        EPelvisAnat = EPelvisTech

        # Compute Anatomical Coordinate System: Thigh
        LeftEThighAnat = gait.AnatCS_Thigh_Newington(
            "Left", LeftHipCenterLab, LeftVirtualKneeMarkerLab, LeftKneeCenterLab
        )
        RightEThighAnat = gait.AnatCS_Thigh_Newington(
            "Right", RightHipCenterLab, RightVirtualKneeMarkerLab, RightKneeCenterLab
        )
        # print(LeftEThighAnat)
        # print(RightEThighAnat)

        # Compute Anatomical Coordinate System: Proximal Shank
        LeftEShankProximalAnat = gait.AnatCS_Shank_Proximal_Newington(
            "Left", LeftKneeCenterLab, LeftVirtualKneeMarkerLab, LeftAnkleCenterLab
        )
        RightEShankProximalAnat = gait.AnatCS_Shank_Proximal_Newington(
            "Right", RightKneeCenterLab, RightVirtualKneeMarkerLab, RightAnkleCenterLab
        )
        # print(LeftEShankProximalAnat)
        # print(RightEShankProximalAnat)

        # Compute Anatomical Coordinate System: Distal Shank
        LeftEShankDistalAnat = gait.AnatCS_Shank_Distal_VCM(
            "Left", LeftKneeCenterLab, LeftAnkleCenterLab, LeftLateralAnkleMarker
        )
        RightEShankDistalAnat = gait.AnatCS_Shank_Distal_VCM(
            "Right", RightKneeCenterLab, RightAnkleCenterLab, RightLateralAnkleMarker
        )
        # print(LeftEShankDistalAnat)
        # print(RightEShankDistalAnat)

        # Compute Anatomical Coordinate System (or Vector):  Foot
        LeftEFootAnat = gait.AnatCS_Foot_Newington(
            "Left",
            LeftLateralAnkleMarker,
            LeftAnkleCenterLab,
            LeftToeMarker,
            LeftVirtualHeelMarkerLab,
        )
        RightEFootAnat = gait.AnatCS_Foot_Newington(
            "Right",
            RightLateralAnkleMarker,
            RightAnkleCenterLab,
            RightToeMarker,
            RightVirtualHeelMarkerLab,
        )
        # print(LeftEFootAnat)
        # print(RightEFootAnat)

        # Compute Anatomical Coodttinate System: Second Foot CS for Ankle Joint Reaction force [Uses Knee Center Instead of lateral Ankle Marker]
        LeftEFootAnat2 = gait.AnatCS_Foot_ShrineGaitModel(
            "Left",
            LeftKneeCenterLab,
            LeftAnkleCenterLab,
            LeftToeMarker,
            LeftVirtualHeelMarkerLab,
        )
        RightEFootAnat2 = gait.AnatCS_Foot_ShrineGaitModel(
            "Right",
            RightKneeCenterLab,
            RightAnkleCenterLab,
            RightToeMarker,
            RightVirtualHeelMarkerLab,
        )

        # Compute Anatomical Coordinate System: Left Foot Segments
        if self.valueLeftFootModelCheck == "1":
            if os.path.exists(SittingFootStaticDataFileName):
                exec(open(SittingFootStaticDataFileName).read())
                LeftEHindfootAnat = math.TransformAnatCoorSysFromTechCoors(
                    self.valueLeftEHindfootAnatRelTech, LeftEHindfootTech
                )
                LeftEForefootAnat = math.TransformAnatCoorSysFromTechCoors(
                    self.valueLeftEForefootAnatRelTech, LeftEForefootTech
                )
                LeftEHalluxAnat = math.TransformAnatCoorSysFromTechCoors(
                    self.valueLeftEHalluxAnatRelTech, LeftEHalluxTech
                )
                exec(open(StaticDataFileName).read())
            else:
                LeftEHindfootAnat = gait.AnatCS_Hindfoot_mSHCG(
                    "Left",
                    LeftLateralCalcaneusMarker,
                    LeftMedialCalcaneusMarker,
                    LeftPosteriorCalcaneusMarker,
                    LeftCalcanealPeronealTrochleaMarker,
                    self.valueLeftHindfootVarus,
                    self.valueLeftCalcanealPitch,
                    self.valueLeftHindfootProgression,
                    self.HindfootValgusIsNegative,
                )
                LeftEForefootAnat = gait.AnatCS_Forefoot_mSHCG(
                    "Left",
                    Left23MetatarsalBaseMarker,
                    Left23MetatarsalHeadMarker,
                    LeftFirstMetatarsalMedialBaseMarker,
                    LeftFirstMetatarsalMedialHeadMarker,
                    self.valueLeftFirstMetatarsalPitch,
                )
                LeftEHalluxAnat = LeftEHalluxTech
            # print(LeftEHindfootAnat)
            # print(LeftEForefootAnat)
            # print(LeftEHalluxAnat)

        # Compute Anatomical Coordinate System: Right Foot Segments
        if self.valueRightFootModelCheck == "1":
            if os.path.exists(SittingFootStaticDataFileName):
                exec(open(SittingFootStaticDataFileName).read())
                RightEHindfootAnat = math.TransformAnatCoorSysFromTechCoors(
                    self.valueRightEHindfootAnatRelTech, RightEHindfootTech
                )
                RightEForefootAnat = math.TransformAnatCoorSysFromTechCoors(
                    self.valueRightEForefootAnatRelTech, RightEForefootTech
                )
                RightEHalluxAnat = math.TransformAnatCoorSysFromTechCoors(
                    self.valueRightEHalluxAnatRelTech, RightEHalluxTech
                )
                exec(open(StaticDataFileName).read())
            else:
                RightEHindfootAnat = gait.AnatCS_Hindfoot_mSHCG(
                    "Right",
                    RightLateralCalcaneusMarker,
                    RightMedialCalcaneusMarker,
                    RightPosteriorCalcaneusMarker,
                    RightCalcanealPeronealTrochleaMarker,
                    self.valueRightHindfootVarus,
                    self.valueRightCalcanealPitch,
                    self.valueRightHindfootProgression,
                    self.HindfootValgusIsNegative,
                )
                RightEForefootAnat = gait.AnatCS_Forefoot_mSHCG(
                    "Right",
                    Right23MetatarsalBaseMarker,
                    Right23MetatarsalHeadMarker,
                    RightFirstMetatarsalMedialBaseMarker,
                    RightFirstMetatarsalMedialHeadMarker,
                    self.valueRightFirstMetatarsalPitch,
                )
                RightEHalluxAnat = RightEHalluxTech
            # print(RightEHindfootAnat)
            # print(RightEForefootAnat)
            # print(RightEHalluxAnat)

        # Compute Attitude of Anatomical Coordinate Systems Relative to their respective Technical Coordinate System
        ETrunkAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
            ETrunkAnat, ETrunkTech
        )
        EPelvisAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
            EPelvisAnat, EPelvisTech
        )
        LeftEThighAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
            LeftEThighAnat, LeftEThighTech
        )
        LeftEShankProximalAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
            LeftEShankProximalAnat, LeftEShankTech
        )
        LeftEShankDistalAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
            LeftEShankDistalAnat, LeftEShankTech
        )
        LeftEFootAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
            LeftEFootAnat, LeftEFootTech
        )
        RightEThighAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
            RightEThighAnat, RightEThighTech
        )
        RightEShankProximalAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
            RightEShankProximalAnat, RightEShankTech
        )
        RightEShankDistalAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
            RightEShankDistalAnat, RightEShankTech
        )
        RightEFootAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
            RightEFootAnat, RightEFootTech
        )
        # Foot CS for Ankle Joint Reaction Force
        LeftEFootAnat2RelTech = math.TransformAnatCoorSysIntoTechCoors(
            LeftEFootAnat2, LeftEFootTech
        )
        RightEFootAnat2RelTech = math.TransformAnatCoorSysIntoTechCoors(
            RightEFootAnat2, RightEFootTech
        )
        if self.valueLeftFootModelCheck == "1":
            LeftEHindfootAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
                LeftEHindfootAnat, LeftEHindfootTech
            )
            LeftEForefootAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
                LeftEForefootAnat, LeftEForefootTech
            )
            LeftEHalluxAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
                LeftEHalluxAnat, LeftEHalluxTech
            )
            Left23MetatarsalHeadMarkerForefoot = math.TransformPointIntoMovingCoors(
                Left23MetatarsalHeadMarker,
                LeftEForefootTech,
                LeftFirstMetarsalBaseMarker,
            )
            LeftFirstMetatarsoPhalangealJointMarkerForefoot = (
                math.TransformPointIntoMovingCoors(
                    LeftFirstMetatarsoPhalangealJointMarker,
                    LeftEForefootTech,
                    LeftFirstMetarsalBaseMarker,
                )
            )

        if self.valueRightFootModelCheck == "1":
            RightEHindfootAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
                RightEHindfootAnat, RightEHindfootTech
            )
            RightEForefootAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
                RightEForefootAnat, RightEForefootTech
            )
            RightEHalluxAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(
                RightEHalluxAnat, RightEHalluxTech
            )
            Right23MetatarsalHeadMarkerForefoot = math.TransformPointIntoMovingCoors(
                Right23MetatarsalHeadMarker,
                RightEForefootTech,
                RightFirstMetarsalBaseMarker,
            )
            RightFirstMetatarsoPhalangealJointMarkerForefoot = (
                math.TransformPointIntoMovingCoors(
                    RightFirstMetatarsoPhalangealJointMarker,
                    RightEForefootTech,
                    RightFirstMetarsalBaseMarker,
                )
            )

        # print(ETrunkAnatRelTech)
        # print(EPelvisAnatRelTech)
        # print(LeftEThighAnatRelTech)
        # print(LeftEShankProximalAnatRelTech)
        # print(LeftEShankDistalAnatRelTech)
        # print(LeftEFootAnatRelTech)
        # print(RightEThighAnatRelTech)
        # print(RightEShankProximalAnatRelTech)
        # print(RightEShankDistalAnatRelTech)
        # print(RightEFootAnatRelTech)

        # initialize the global or lab coordinate system
        ELab = np.eye(3)

        # Compute trunk kinematics
        TrunkAnglesTORRad = math.EulerAngles_YXZ(ETrunkAnat, ELab)
        TrunkAnglesROTRad = math.EulerAngles_ZXY(ETrunkAnat, ELab)
        if self.TrunkRotationSequence == "TOR":
            TrunkAnglesRad = TrunkAnglesTORRad
        if self.TrunkRotationSequence == "ROT":
            TrunkAnglesRad = TrunkAnglesROTRad
        # Compute pelvic kinematics
        PelvisAnglesTORRad = math.EulerAngles_YXZ(EPelvisAnat, ELab)
        PelvisAnglesROTRad = math.EulerAngles_ZXY(EPelvisAnat, ELab)
        if self.PelvisRotationSequence == "TOR":
            PelvisAnglesRad = PelvisAnglesTORRad
        if self.PelvisRotationSequence == "ROT":
            PelvisAnglesRad = PelvisAnglesROTRad
        # Compute thigh kinematics
        LeftThighAnglesRad = math.EulerAngles_YXZ(LeftEThighAnat, ELab)
        RightThighAnglesRad = math.EulerAngles_YXZ(RightEThighAnat, ELab)
        # Compute shank kinematics
        LeftShankAnglesRad = math.EulerAngles_YXZ(
            LeftEShankDistalAnat,
            ELab,
        )
        RightShankAnglesRad = math.EulerAngles_YXZ(
            RightEShankDistalAnat,
            ELab,
        )
        # Compute foot kinematics
        LeftFootAnglesRad = math.EulerAngles_YXZ(
            LeftEFootAnat,
            ELab,
        )
        RightFootAnglesRad = math.EulerAngles_YXZ(
            RightEFootAnat,
            ELab,
        )
        # Compute hip kinematics
        LeftHipAnglesRad = math.EulerAngles_YXZ(LeftEThighAnat, EPelvisAnat)
        RightHipAnglesRad = math.EulerAngles_YXZ(RightEThighAnat, EPelvisAnat)
        # Compute knee kinematics
        if self.ShankCoordinateSystem == "Distal":
            LeftKneeAnglesRad = math.EulerAngles_YXZ(
                LeftEShankDistalAnat, LeftEThighAnat
            )
            RightKneeAnglesRad = math.EulerAngles_YXZ(
                RightEShankDistalAnat, RightEThighAnat
            )
        if self.ShankCoordinateSystem == "Proximal":
            LeftKneeAnglesRad = math.EulerAngles_YXZ(
                LeftEShankProximalAnat, LeftEThighAnat
            )
            RightKneeAnglesRad = math.EulerAngles_YXZ(
                RightEShankProximalAnat, RightEThighAnat
            )
        # Compute ankle kinematics
        LeftAnkleAnglesRad = math.EulerAngles_YXZ(LeftEFootAnat, LeftEShankDistalAnat)
        RightAnkleAnglesRad = math.EulerAngles_YXZ(
            RightEFootAnat, RightEShankDistalAnat
        )
        # Compute Left Foot kinematics
        if self.valueLeftFootModelCheck == "1":
            LeftHindfootAnglesRad = math.EulerAngles_ZYX(LeftEHindfootAnat, ELab)
            LeftForefootAnglesRad = math.EulerAngles_ZYX(LeftEForefootAnat, ELab)
            # LeftHindfootAnglesRad = math.EulerAngles_YXZ(LeftEHindfootAnat,ELab)
            # LeftForefootAnglesRad = math.EulerAngles_YXZ(LeftEForefootAnat,ELab)
            LeftHalluxAnglesRad = math.EulerAngles_YXZ(LeftEHalluxAnat, ELab)
            LeftAnkleComplexAnglesRad = math.EulerAngles_YXZ(
                LeftEHindfootAnat, LeftEShankDistalAnat
            )
            LeftMidfootAnglesRad = math.EulerAngles_YXZ(
                LeftEForefootAnat, LeftEHindfootAnat
            )
            LeftToesAnglesRad = math.EulerAngles_YXZ(LeftEHalluxAnat, LeftEForefootAnat)
            # print LeftHindfootAnglesRad
            # print LeftForefootAnglesRad
            # print LeftHalluxAnglesRad
            # print LeftAnkleComplexAnglesRad
            # print LeftMidfootAnglesRad
            # print LeftToesAnglesRad
        # Compute Right Foot kinematics
        if self.valueRightFootModelCheck == "1":
            RightHindfootAnglesRad = math.EulerAngles_ZYX(RightEHindfootAnat, ELab)
            RightForefootAnglesRad = math.EulerAngles_ZYX(RightEForefootAnat, ELab)
            # RightHindfootAnglesRad = math.EulerAngles_YXZ(RightEHindfootAnat,ELab)
            # RightForefootAnglesRad = math.EulerAngles_YXZ(RightEForefootAnat,ELab)
            RightHalluxAnglesRad = math.EulerAngles_YXZ(RightEHalluxAnat, ELab)
            RightAnkleComplexAnglesRad = math.EulerAngles_YXZ(
                RightEHindfootAnat, RightEShankDistalAnat
            )
            RightMidfootAnglesRad = math.EulerAngles_YXZ(
                RightEForefootAnat, RightEHindfootAnat
            )
            RightToesAnglesRad = math.EulerAngles_YXZ(
                RightEHalluxAnat, RightEForefootAnat
            )
            # print RightHindfootAnglesRad
            # print RightForefootAnglesRad
            # print RightHalluxAnglesRad
            # print RightAnkleComplexAnglesRad
            # print RightMidfootAnglesRad
            # print RightToesAnglesRad
        #        print(TrunkAnglesRad)
        #        print(PelvisAnglesRad)
        #        print(LeftThighAnglesRad)
        #        print(LeftShankAnglesRad)
        #        print(LeftFootAnglesRad)
        #        print(LeftHipAnglesRad)
        #        print(LeftKneeAnglesRad)
        #        print(LeftAnkleAnglesRad)
        #        print(RightThighAnglesRad)
        #        print(RightShankAnglesRad)
        #        print(RightFootAnglesRad)
        #        print(RightHipAnglesRad)
        #        print(RightKneeAnglesRad)
        #        print(RightAnkleAnglesRad)

        # Convert units of angles from radians to degrees & set sign based on side and plotting convention
        Sign = -1  # For Left Side

        T1, T1[0, 0], T1[1, 1], T1[2, 2] = np.eye(3), -Sign, +1, Sign
        T2, T2[0, 0], T2[1, 1], T2[2, 2] = np.eye(3), Sign, -1, Sign
        T3, T3[0, 0], T3[1, 1], T3[2, 2] = np.eye(3), Sign, +1, Sign

        LeftTrunkAnglesDeg = T1.dot(TrunkAnglesRad) * 180 / np.pi
        LeftPelvisAnglesDeg = T1.dot(PelvisAnglesRad) * 180 / np.pi
        LeftThighAnglesDeg = T1.dot(LeftThighAnglesRad) * 180 / np.pi
        LeftShankAnglesDeg = T1.dot(LeftShankAnglesRad) * 180 / np.pi
        LeftFootAnglesDeg = T1.dot(LeftFootAnglesRad) * 180 / np.pi
        LeftHipAnglesDeg = T2.dot(LeftHipAnglesRad) * 180 / np.pi
        LeftKneeAnglesDeg = T3.dot(LeftKneeAnglesRad) * 180 / np.pi
        LeftAnkleAnglesDeg = T2.dot(LeftAnkleAnglesRad) * 180 / np.pi
        if self.valueLeftFootModelCheck == "1":
            LeftHindfootAnglesDeg = T1.dot(LeftHindfootAnglesRad) * 180 / np.pi
            LeftForefootAnglesDeg = T1.dot(LeftForefootAnglesRad) * 180 / np.pi
            LeftHalluxAnglesDeg = T1.dot(LeftHalluxAnglesRad) * 180 / np.pi
            LeftAnkleComplexAnglesDeg = T2.dot(LeftAnkleComplexAnglesRad) * 180 / np.pi
            LeftMidfootAnglesDeg = T2.dot(LeftMidfootAnglesRad) * 180 / np.pi
            LeftToesAnglesDeg = T2.dot(LeftToesAnglesRad) * 180 / np.pi
        # print(LeftTrunkAnglesDeg)
        # print(LeftPelvisAnglesDeg)
        # print(LeftThighAnglesDeg)
        # print(LeftShankAnglesDeg)
        # print(LeftFootAnglesDeg)
        # print(LeftHipAnglesDeg)
        # print(LeftKneeAnglesDeg)
        # print(LeftAnkleAnglesDeg)

        Sign = 1  # For Right Side

        T1, T1[0, 0], T1[1, 1], T1[2, 2] = np.eye(3), -Sign, +1, Sign
        T2, T2[0, 0], T2[1, 1], T2[2, 2] = np.eye(3), Sign, -1, Sign
        T3, T3[0, 0], T3[1, 1], T3[2, 2] = np.eye(3), Sign, +1, Sign

        RightTrunkAnglesDeg = T1.dot(TrunkAnglesRad) * 180 / np.pi
        RightPelvisAnglesDeg = T1.dot(PelvisAnglesRad) * 180 / np.pi
        RightThighAnglesDeg = T1.dot(RightThighAnglesRad) * 180 / np.pi
        RightShankAnglesDeg = T1.dot(RightShankAnglesRad) * 180 / np.pi
        RightFootAnglesDeg = T1.dot(RightFootAnglesRad) * 180 / np.pi
        RightHipAnglesDeg = T2.dot(RightHipAnglesRad) * 180 / np.pi
        RightKneeAnglesDeg = T3.dot(RightKneeAnglesRad) * 180 / np.pi
        RightAnkleAnglesDeg = T2.dot(RightAnkleAnglesRad) * 180 / np.pi
        if self.valueRightFootModelCheck == "1":
            RightHindfootAnglesDeg = T1.dot(RightHindfootAnglesRad) * 180 / np.pi
            RightForefootAnglesDeg = T1.dot(RightForefootAnglesRad) * 180 / np.pi
            RightHalluxAnglesDeg = T1.dot(RightHalluxAnglesRad) * 180 / np.pi
            RightAnkleComplexAnglesDeg = (
                T2.dot(RightAnkleComplexAnglesRad) * 180 / np.pi
            )
            RightMidfootAnglesDeg = T2.dot(RightMidfootAnglesRad) * 180 / np.pi
            RightToesAnglesDeg = T2.dot(RightToesAnglesRad) * 180 / np.pi
        # print(RightTrunkAnglesDeg)
        # print(RightPelvisAnglesDeg)
        # print(RightThighAnglesDeg)
        # print(RightShankAnglesDeg)
        # print(RightFootAnglesDeg)
        # print(RightHipAnglesDeg)
        # print(RightKneeAnglesDeg)
        # print(RightAnkleAnglesDeg)

        # Compute Ankle Plantar/Dorsiflexion based on the ankle-to-knee center axis and long axis of foot
        LeftAnkleKneeVector = math.ComputeUnitVecFromPts(
            LeftAnkleCenterLab, LeftKneeCenterLab
        )
        LeftEFootAnatX = np.array(
            (LeftEFootAnat[0][0], LeftEFootAnat[1][0], LeftEFootAnat[2][0])
        )
        LeftAnkleAnglesDeg[1] = (
            90 - np.arccos(np.dot(LeftAnkleKneeVector, LeftEFootAnatX)) * 180 / np.pi
        )
        RightAnkleKneeVector = math.ComputeUnitVecFromPts(
            RightAnkleCenterLab, RightKneeCenterLab
        )
        RightEFootAnatX = np.array(
            (RightEFootAnat[0][0], RightEFootAnat[1][0], RightEFootAnat[2][0])
        )
        RightAnkleAnglesDeg[1] = (
            90 - np.arccos(np.dot(RightAnkleKneeVector, RightEFootAnatX)) * 180 / np.pi
        )
        # print(LeftAnkleAnglesDeg[1])
        # print(RightAnkleAnglesDeg[1])

        # Compute Foot Progression as the sin of the angle between long axis of foot and the y-axis of lab
        LeftFootAnglesDeg[2] = -1 * np.arcsin(LeftEFootAnat[1][0]) * 180 / np.pi
        RightFootAnglesDeg[2] = 1 * np.arcsin(RightEFootAnat[1][0]) * 180 / np.pi
        # print(LeftFootAnglesDeg[2])
        # print(RightFootAnglesDeg[2])

        # Compute Tibial Torsion based on the Ankle Flexion-Extension Axis
        LeftTibialTorsion = gait.Compute_TibialTorsion(
            "Left",
            LeftEShankProximalAnat,
            LeftLateralAnkleMarker,
            LeftMedialAnkleMarker,
        )
        RightTibialTorsion = gait.Compute_TibialTorsion(
            "Right",
            RightEShankProximalAnat,
            RightLateralAnkleMarker,
            RightMedialAnkleMarker,
        )
        # print(LeftTibialTorsion)
        # print(RightTibialTorsion)

        # =============================================================================
        #       Fille in Posture Display Measurements
        # =============================================================================
        # Left
        if TrunkFlag == 1:
            if round(LeftTrunkAnglesDeg[0], 0) > 0:
                LeftTrunkObliquity.insert(
                    0, str(int(abs(round(LeftTrunkAnglesDeg[0], 0)))) + " Up"
                )
            if round(LeftTrunkAnglesDeg[0], 0) < 0:
                LeftTrunkObliquity.insert(
                    0, str(int(abs(round(LeftTrunkAnglesDeg[0], 0)))) + " Down"
                )
            if round(LeftTrunkAnglesDeg[0], 0) == 0:
                LeftTrunkObliquity.insert(
                    0, str(int(abs(round(LeftTrunkAnglesDeg[0], 0)))) + ""
                )
            if round(LeftTrunkAnglesDeg[1], 0) > 0:
                LeftTrunkTilt.insert(
                    0, str(int(abs(round(LeftTrunkAnglesDeg[1], 0)))) + " Forw"
                )
            if round(LeftTrunkAnglesDeg[1], 0) < 0:
                LeftTrunkTilt.insert(
                    0, str(int(abs(round(LeftTrunkAnglesDeg[1], 0)))) + " Back"
                )
            if round(LeftTrunkAnglesDeg[1], 0) == 0:
                LeftTrunkTilt.insert(
                    0, str(int(abs(round(LeftTrunkAnglesDeg[1], 0)))) + ""
                )
            if round(LeftTrunkAnglesDeg[2], 0) > 0:
                LeftTrunkRotation.insert(
                    0, str(int(abs(round(LeftTrunkAnglesDeg[2], 0)))) + " Int"
                )
            if round(LeftTrunkAnglesDeg[2], 0) < 0:
                LeftTrunkRotation.insert(
                    0, str(int(abs(round(LeftTrunkAnglesDeg[2], 0)))) + " Ext"
                )
            if round(LeftTrunkAnglesDeg[2], 0) == 0:
                LeftTrunkRotation.insert(
                    0, str(int(abs(round(LeftTrunkAnglesDeg[2], 0)))) + ""
                )

        if round(LeftPelvisAnglesDeg[0], 0) > 0:
            LeftPelvisObliquity.insert(
                0, str(int(abs(round(LeftPelvisAnglesDeg[0], 0)))) + " Up"
            )
        if round(LeftPelvisAnglesDeg[0], 0) < 0:
            LeftPelvisObliquity.insert(
                0, str(int(abs(round(LeftPelvisAnglesDeg[0], 0)))) + " Down"
            )
        if round(LeftPelvisAnglesDeg[0], 0) == 0:
            LeftPelvisObliquity.insert(
                0, str(int(abs(round(LeftPelvisAnglesDeg[0], 0)))) + ""
            )
        if round(LeftPelvisAnglesDeg[1], 0) > 0:
            LeftPelvisTilt.insert(
                0, str(int(abs(round(LeftPelvisAnglesDeg[1], 0)))) + " Ant"
            )
        if round(LeftPelvisAnglesDeg[1], 0) < 0:
            LeftPelvisTilt.insert(
                0, str(int(abs(round(LeftPelvisAnglesDeg[1], 0)))) + " Post"
            )
        if round(LeftPelvisAnglesDeg[1], 0) == 0:
            LeftPelvisTilt.insert(
                0, str(int(abs(round(LeftPelvisAnglesDeg[1], 0)))) + ""
            )
        if round(LeftPelvisAnglesDeg[2], 0) > 0:
            LeftPelvisRotation.insert(
                0, str(int(abs(round(LeftPelvisAnglesDeg[2], 0)))) + " Int"
            )
        if round(LeftPelvisAnglesDeg[2], 0) < 0:
            LeftPelvisRotation.insert(
                0, str(int(abs(round(LeftPelvisAnglesDeg[2], 0)))) + " Ext"
            )
        if round(LeftPelvisAnglesDeg[2], 0) == 0:
            LeftPelvisRotation.insert(
                0, str(int(abs(round(LeftPelvisAnglesDeg[2], 0)))) + ""
            )

        if round(LeftHipAnglesDeg[0], 0) > 0:
            LeftHipAbAdduction.insert(
                0, str(int(abs(round(LeftHipAnglesDeg[0], 0)))) + " Add"
            )
        if round(LeftHipAnglesDeg[0], 0) < 0:
            LeftHipAbAdduction.insert(
                0, str(int(abs(round(LeftHipAnglesDeg[0], 0)))) + " Abd"
            )
        if round(LeftHipAnglesDeg[0], 0) == 0:
            LeftHipAbAdduction.insert(
                0, str(int(abs(round(LeftHipAnglesDeg[0], 0)))) + ""
            )
        if round(LeftHipAnglesDeg[1], 0) > 0:
            LeftHipFlexExtension.insert(
                0, str(int(abs(round(LeftHipAnglesDeg[1], 0)))) + " Flex"
            )
        if round(LeftHipAnglesDeg[1], 0) < 0:
            LeftHipFlexExtension.insert(
                0, str(int(abs(round(LeftHipAnglesDeg[1], 0)))) + " Ext"
            )
        if round(LeftHipAnglesDeg[1], 0) == 0:
            LeftHipFlexExtension.insert(
                0, str(int(abs(round(LeftHipAnglesDeg[1], 0)))) + ""
            )
        if round(LeftHipAnglesDeg[2], 0) > 0:
            LeftHipIntExtRotation.insert(
                0, str(int(abs(round(LeftHipAnglesDeg[2], 0)))) + " Int"
            )
        if round(LeftHipAnglesDeg[2], 0) < 0:
            LeftHipIntExtRotation.insert(
                0, str(int(abs(round(LeftHipAnglesDeg[2], 0)))) + " Ext"
            )
        if round(LeftHipAnglesDeg[2], 0) == 0:
            LeftHipIntExtRotation.insert(
                0, str(int(abs(round(LeftHipAnglesDeg[2], 0)))) + ""
            )

        if round(LeftKneeAnglesDeg[0], 0) > 0:
            LeftKneeVarusValgus.insert(
                0, str(int(abs(round(LeftKneeAnglesDeg[0], 0)))) + " Var"
            )
        if round(LeftKneeAnglesDeg[0], 0) < 0:
            LeftKneeVarusValgus.insert(
                0, str(int(abs(round(LeftKneeAnglesDeg[0], 0)))) + " Val"
            )
        if round(LeftKneeAnglesDeg[0], 0) == 0:
            LeftKneeVarusValgus.insert(
                0, str(int(abs(round(LeftKneeAnglesDeg[0], 0)))) + ""
            )
        if round(LeftKneeAnglesDeg[1], 0) > 0:
            LeftKneeFlexExtension.insert(
                0, str(int(abs(round(LeftKneeAnglesDeg[1], 0)))) + " Flex"
            )
        if round(LeftKneeAnglesDeg[1], 0) < 0:
            LeftKneeFlexExtension.insert(
                0, str(int(abs(round(LeftKneeAnglesDeg[1], 0)))) + " Ext"
            )
        if round(LeftKneeAnglesDeg[1], 0) == 0:
            LeftKneeFlexExtension.insert(
                0, str(int(abs(round(LeftKneeAnglesDeg[1], 0)))) + ""
            )
        if round(LeftKneeAnglesDeg[2], 0) > 0:
            LeftKneeIntExtRotation.insert(
                0, str(int(abs(round(LeftKneeAnglesDeg[2], 0)))) + " Int"
            )
        if round(LeftKneeAnglesDeg[2], 0) < 0:
            LeftKneeIntExtRotation.insert(
                0, str(int(abs(round(LeftKneeAnglesDeg[2], 0)))) + " Ext"
            )
        if round(LeftKneeAnglesDeg[2], 0) == 0:
            LeftKneeIntExtRotation.insert(
                0, str(int(abs(round(LeftKneeAnglesDeg[2], 0)))) + ""
            )

        if round(LeftThighAnglesDeg[2], 0) > 0:
            LeftKneeProgression.insert(
                0, str(int(abs(round(LeftThighAnglesDeg[2], 0)))) + " Int"
            )
        if round(LeftThighAnglesDeg[2], 0) < 0:
            LeftKneeProgression.insert(
                0, str(int(abs(round(LeftThighAnglesDeg[2], 0)))) + " Ext"
            )
        if round(LeftThighAnglesDeg[2], 0) == 0:
            LeftKneeProgression.insert(
                0, str(int(abs(round(LeftThighAnglesDeg[2], 0)))) + ""
            )

        if round(LeftAnkleAnglesDeg[1], 0) > 0:
            LeftAnklePlantarDorsiflexion.insert(
                0, str(int(abs(round(LeftAnkleAnglesDeg[1], 0)))) + " Dorsi"
            )
        if round(LeftAnkleAnglesDeg[1], 0) < 0:
            LeftAnklePlantarDorsiflexion.insert(
                0, str(int(abs(round(LeftAnkleAnglesDeg[1], 0)))) + " Plant"
            )
        if round(LeftAnkleAnglesDeg[1], 0) == 0:
            LeftAnklePlantarDorsiflexion.insert(
                0, str(int(abs(round(LeftAnkleAnglesDeg[1], 0)))) + ""
            )
        if round(LeftAnkleAnglesDeg[2], 0) > 0:
            LeftAnkleIntExtRotation.insert(
                0, str(int(abs(round(LeftAnkleAnglesDeg[2], 0)))) + " Int"
            )
        if round(LeftAnkleAnglesDeg[2], 0) < 0:
            LeftAnkleIntExtRotation.insert(
                0, str(int(abs(round(LeftAnkleAnglesDeg[2], 0)))) + " Ext"
            )
        if round(LeftAnkleAnglesDeg[2], 0) == 0:
            LeftAnkleIntExtRotation.insert(
                0, str(int(abs(round(LeftAnkleAnglesDeg[2], 0)))) + ""
            )

        if round(LeftFootAnglesDeg[2], 0) > 0:
            LeftFootProgression.insert(
                0, str(int(abs(round(LeftFootAnglesDeg[2], 0)))) + " Int"
            )
        if round(LeftFootAnglesDeg[2], 0) < 0:
            LeftFootProgression.insert(
                0, str(int(abs(round(LeftFootAnglesDeg[2], 0)))) + " Ext"
            )
        if round(LeftFootAnglesDeg[2], 0) == 0:
            LeftFootProgression.insert(
                0, str(int(abs(round(LeftFootAnglesDeg[2], 0)))) + ""
            )

        if round(LeftTibialTorsion, 0) > 0:
            LeftTibiaTorsion.insert(
                0, str(int(abs(round(LeftTibialTorsion, 0)))) + " Ext"
            )
        if round(LeftTibialTorsion, 0) < 0:
            LeftTibiaTorsion.insert(
                0, str(int(abs(round(LeftTibialTorsion, 0)))) + " Int"
            )
        if round(LeftTibialTorsion, 0) == 0:
            LeftTibiaTorsion.insert(0, str(int(abs(round(LeftTibialTorsion, 0)))) + "")

        if self.valueLeftFootModelCheck == "1":
            if round(LeftHindfootAnglesDeg[0], 0) > 0:
                LeftHindfootInvEversion.insert(
                    0, str(int(abs(round(LeftHindfootAnglesDeg[0], 0)))) + " Val"
                )
            if round(LeftHindfootAnglesDeg[0], 0) < 0:
                LeftHindfootInvEversion.insert(
                    0, str(int(abs(round(LeftHindfootAnglesDeg[0], 0)))) + " Var"
                )
            if round(LeftHindfootAnglesDeg[0], 0) == 0:
                LeftHindfootInvEversion.insert(
                    0, str(int(abs(round(LeftHindfootAnglesDeg[0], 0)))) + ""
                )
            if round(LeftHindfootAnglesDeg[1], 0) > 0:
                LeftHindfootPitch.insert(
                    0, str(int(abs(round(LeftHindfootAnglesDeg[1], 0)))) + " Down"
                )
            if round(LeftHindfootAnglesDeg[1], 0) < 0:
                LeftHindfootPitch.insert(
                    0, str(int(abs(round(LeftHindfootAnglesDeg[1], 0)))) + " Up"
                )
            if round(LeftHindfootAnglesDeg[1], 0) == 0:
                LeftHindfootPitch.insert(
                    0, str(int(abs(round(LeftHindfootAnglesDeg[1], 0)))) + ""
                )
            if round(LeftHindfootAnglesDeg[2], 0) > 0:
                LeftHindfootProgression.insert(
                    0, str(int(abs(round(LeftHindfootAnglesDeg[2], 0)))) + " Int"
                )
            if round(LeftHindfootAnglesDeg[2], 0) < 0:
                LeftHindfootProgression.insert(
                    0, str(int(abs(round(LeftHindfootAnglesDeg[2], 0)))) + " Ext"
                )
            if round(LeftHindfootAnglesDeg[2], 0) == 0:
                LeftHindfootProgression.insert(
                    0, str(int(abs(round(LeftHindfootAnglesDeg[2], 0)))) + ""
                )

            if round(LeftAnkleComplexAnglesDeg[0], 0) > 0:
                LeftAnkleComplexInvEversion.insert(
                    0, str(int(abs(round(LeftAnkleComplexAnglesDeg[0], 0)))) + " Var"
                )
            if round(LeftAnkleComplexAnglesDeg[0], 0) < 0:
                LeftAnkleComplexInvEversion.insert(
                    0, str(int(abs(round(LeftAnkleComplexAnglesDeg[0], 0)))) + " Val"
                )
            if round(LeftAnkleComplexAnglesDeg[0], 0) == 0:
                LeftAnkleComplexInvEversion.insert(
                    0, str(int(abs(round(LeftAnkleComplexAnglesDeg[0], 0)))) + ""
                )

            #            if round(LeftForefootAnglesDeg[0], 0) > 0:
            #                LeftForefootInvEversion.insert(0, str(int(abs(round(LeftForefootAnglesDeg[0], 0)))) +  " Inv")
            #            if round(LeftForefootAnglesDeg[0], 0) < 0:
            #                LeftForefootInvEversion.insert(0, str(int(abs(round(LeftForefootAnglesDeg[0], 0)))) +  " Ev")
            #            if round(LeftForefootAnglesDeg[0], 0) == 0:
            #                LeftForefootInvEversion.insert(0, str(int(abs(round(LeftForefootAnglesDeg[0], 0)))) +  "")
            if round(LeftForefootAnglesDeg[1], 0) > 0:
                LeftForefootPitch.insert(
                    0, str(int(abs(round(LeftForefootAnglesDeg[1], 0)))) + " Down"
                )
            if round(LeftForefootAnglesDeg[1], 0) < 0:
                LeftForefootPitch.insert(
                    0, str(int(abs(round(LeftForefootAnglesDeg[1], 0)))) + " Up"
                )
            if round(LeftForefootAnglesDeg[1], 0) == 0:
                LeftForefootPitch.insert(
                    0, str(int(abs(round(LeftForefootAnglesDeg[1], 0)))) + ""
                )
            if round(LeftForefootAnglesDeg[2], 0) > 0:
                LeftForefootProgression.insert(
                    0, str(int(abs(round(LeftForefootAnglesDeg[2], 0)))) + " Int"
                )
            if round(LeftForefootAnglesDeg[2], 0) < 0:
                LeftForefootProgression.insert(
                    0, str(int(abs(round(LeftForefootAnglesDeg[2], 0)))) + " Ext"
                )
            if round(LeftForefootAnglesDeg[2], 0) == 0:
                LeftForefootProgression.insert(
                    0, str(int(abs(round(LeftForefootAnglesDeg[2], 0)))) + ""
                )

            if round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0) > 0:
                LeftMidfootAbAdduction.insert(
                    0,
                    str(
                        int(
                            abs(
                                round(
                                    LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2],
                                    0,
                                )
                            )
                        )
                    )
                    + " Add",
                )
            if round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0) < 0:
                LeftMidfootAbAdduction.insert(
                    0,
                    str(
                        int(
                            abs(
                                round(
                                    LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2],
                                    0,
                                )
                            )
                        )
                    )
                    + " Abd",
                )
            if round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0) == 0:
                LeftMidfootAbAdduction.insert(
                    0,
                    str(
                        int(
                            abs(
                                round(
                                    LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2],
                                    0,
                                )
                            )
                        )
                    )
                    + "",
                )

            if round(LeftHalluxAnglesDeg[2], 0) > 0:
                LeftHalluxProgression.insert(
                    0, str(int(abs(round(LeftToesAnglesDeg[2], 0)))) + " Var"
                )
            if round(LeftHalluxAnglesDeg[2], 0) < 0:
                LeftHalluxProgression.insert(
                    0, str(int(abs(round(LeftToesAnglesDeg[2], 0)))) + " Val"
                )
            if round(LeftHalluxAnglesDeg[2], 0) == 0:
                LeftHalluxProgression.insert(
                    0, str(int(abs(round(LeftToesAnglesDeg[2], 0)))) + ""
                )

        # Right
        if TrunkFlag == 1:
            if round(RightTrunkAnglesDeg[0], 0) > 0:
                RightTrunkObliquity.insert(
                    0, str(int(abs(round(RightTrunkAnglesDeg[0], 0)))) + " Up"
                )
            if round(RightTrunkAnglesDeg[0], 0) < 0:
                RightTrunkObliquity.insert(
                    0, str(int(abs(round(RightTrunkAnglesDeg[0], 0)))) + " Down"
                )
            if round(RightTrunkAnglesDeg[0], 0) == 0:
                RightTrunkObliquity.insert(
                    0, str(int(abs(round(RightTrunkAnglesDeg[0], 0)))) + ""
                )
            if round(RightTrunkAnglesDeg[1], 0) > 0:
                RightTrunkTilt.insert(
                    0, str(int(abs(round(RightTrunkAnglesDeg[1], 0)))) + " Forw"
                )
            if round(RightTrunkAnglesDeg[1], 0) < 0:
                RightTrunkTilt.insert(
                    0, str(int(abs(round(RightTrunkAnglesDeg[1], 0)))) + " Back"
                )
            if round(RightTrunkAnglesDeg[1], 0) == 0:
                RightTrunkTilt.insert(
                    0, str(int(abs(round(RightTrunkAnglesDeg[1], 0)))) + ""
                )
            if round(RightTrunkAnglesDeg[2], 0) > 0:
                RightTrunkRotation.insert(
                    0, str(int(abs(round(RightTrunkAnglesDeg[2], 0)))) + " Int"
                )
            if round(RightTrunkAnglesDeg[2], 0) < 0:
                RightTrunkRotation.insert(
                    0, str(int(abs(round(RightTrunkAnglesDeg[2], 0)))) + " Ext"
                )
            if round(RightTrunkAnglesDeg[2], 0) == 0:
                RightTrunkRotation.insert(
                    0, str(int(abs(round(RightTrunkAnglesDeg[2], 0)))) + ""
                )

        if round(RightPelvisAnglesDeg[0], 0) > 0:
            RightPelvisObliquity.insert(
                0, str(int(abs(round(RightPelvisAnglesDeg[0], 0)))) + " Up"
            )
        if round(RightPelvisAnglesDeg[0], 0) < 0:
            RightPelvisObliquity.insert(
                0, str(int(abs(round(RightPelvisAnglesDeg[0], 0)))) + " Down"
            )
        if round(RightPelvisAnglesDeg[0], 0) == 0:
            RightPelvisObliquity.insert(
                0, str(int(abs(round(RightPelvisAnglesDeg[0], 0)))) + ""
            )
        if round(RightPelvisAnglesDeg[1], 0) > 0:
            RightPelvisTilt.insert(
                0, str(int(abs(round(RightPelvisAnglesDeg[1], 0)))) + " Ant"
            )
        if round(RightPelvisAnglesDeg[1], 0) < 0:
            RightPelvisTilt.insert(
                0, str(int(abs(round(RightPelvisAnglesDeg[1], 0)))) + " Post"
            )
        if round(RightPelvisAnglesDeg[1], 0) == 0:
            RightPelvisTilt.insert(
                0, str(int(abs(round(RightPelvisAnglesDeg[1], 0)))) + ""
            )
        if round(RightPelvisAnglesDeg[2], 0) > 0:
            RightPelvisRotation.insert(
                0, str(int(abs(round(RightPelvisAnglesDeg[2], 0)))) + " Int"
            )
        if round(RightPelvisAnglesDeg[2], 0) < 0:
            RightPelvisRotation.insert(
                0, str(int(abs(round(RightPelvisAnglesDeg[2], 0)))) + " Ext"
            )
        if round(RightPelvisAnglesDeg[2], 0) == 0:
            RightPelvisRotation.insert(
                0, str(int(abs(round(RightPelvisAnglesDeg[2], 0)))) + ""
            )

        if round(RightHipAnglesDeg[0], 0) > 0:
            RightHipAbAdduction.insert(
                0, str(int(abs(round(RightHipAnglesDeg[0], 0)))) + " Add"
            )
        if round(RightHipAnglesDeg[0], 0) < 0:
            RightHipAbAdduction.insert(
                0, str(int(abs(round(RightHipAnglesDeg[0], 0)))) + " Abd"
            )
        if round(RightHipAnglesDeg[0], 0) == 0:
            RightHipAbAdduction.insert(
                0, str(int(abs(round(RightHipAnglesDeg[0], 0)))) + ""
            )
        if round(RightHipAnglesDeg[1], 0) > 0:
            RightHipFlexExtension.insert(
                0, str(int(abs(round(RightHipAnglesDeg[1], 0)))) + " Flex"
            )
        if round(RightHipAnglesDeg[1], 0) < 0:
            RightHipFlexExtension.insert(
                0, str(int(abs(round(RightHipAnglesDeg[1], 0)))) + " Ext"
            )
        if round(RightHipAnglesDeg[1], 0) == 0:
            RightHipFlexExtension.insert(
                0, str(int(abs(round(RightHipAnglesDeg[1], 0)))) + ""
            )
        if round(RightHipAnglesDeg[2], 0) > 0:
            RightHipIntExtRotation.insert(
                0, str(int(abs(round(RightHipAnglesDeg[2], 0)))) + " Int"
            )
        if round(RightHipAnglesDeg[2], 0) < 0:
            RightHipIntExtRotation.insert(
                0, str(int(abs(round(RightHipAnglesDeg[2], 0)))) + " Ext"
            )
        if round(RightHipAnglesDeg[2], 0) == 0:
            RightHipIntExtRotation.insert(
                0, str(int(abs(round(RightHipAnglesDeg[2], 0)))) + ""
            )

        if round(RightKneeAnglesDeg[0], 0) > 0:
            RightKneeVarusValgus.insert(
                0, str(int(abs(round(RightKneeAnglesDeg[0], 0)))) + " Var"
            )
        if round(RightKneeAnglesDeg[0], 0) < 0:
            RightKneeVarusValgus.insert(
                0, str(int(abs(round(RightKneeAnglesDeg[0], 0)))) + " Val"
            )
        if round(RightKneeAnglesDeg[0], 0) == 0:
            RightKneeVarusValgus.insert(
                0, str(int(abs(round(RightKneeAnglesDeg[0], 0)))) + ""
            )
        if round(RightKneeAnglesDeg[1], 0) > 0:
            RightKneeFlexExtension.insert(
                0, str(int(abs(round(RightKneeAnglesDeg[1], 0)))) + " Flex"
            )
        if round(RightKneeAnglesDeg[1], 0) < 0:
            RightKneeFlexExtension.insert(
                0, str(int(abs(round(RightKneeAnglesDeg[1], 0)))) + " Ext"
            )
        if round(RightKneeAnglesDeg[1], 0) == 0:
            RightKneeFlexExtension.insert(
                0, str(int(abs(round(RightKneeAnglesDeg[1], 0)))) + ""
            )
        if round(RightKneeAnglesDeg[2], 0) > 0:
            RightKneeIntExtRotation.insert(
                0, str(int(abs(round(RightKneeAnglesDeg[2], 0)))) + " Int"
            )
        if round(RightKneeAnglesDeg[2], 0) < 0:
            RightKneeIntExtRotation.insert(
                0, str(int(abs(round(RightKneeAnglesDeg[2], 0)))) + " Ext"
            )
        if round(RightKneeAnglesDeg[2], 0) == 0:
            RightKneeIntExtRotation.insert(
                0, str(int(abs(round(RightKneeAnglesDeg[2], 0)))) + ""
            )

        if round(RightThighAnglesDeg[2], 0) > 0:
            RightKneeProgression.insert(
                0, str(int(abs(round(RightThighAnglesDeg[2], 0)))) + " Int"
            )
        if round(RightThighAnglesDeg[2], 0) < 0:
            RightKneeProgression.insert(
                0, str(int(abs(round(RightThighAnglesDeg[2], 0)))) + " Ext"
            )
        if round(RightThighAnglesDeg[2], 0) == 0:
            RightKneeProgression.insert(
                0, str(int(abs(round(RightThighAnglesDeg[2], 0)))) + ""
            )

        if round(RightAnkleAnglesDeg[1], 0) > 0:
            RightAnklePlantarDorsiflexion.insert(
                0, str(int(abs(round(RightAnkleAnglesDeg[1], 0)))) + " Dorsi"
            )
        if round(RightAnkleAnglesDeg[1], 0) < 0:
            RightAnklePlantarDorsiflexion.insert(
                0, str(int(abs(round(RightAnkleAnglesDeg[1], 0)))) + " Plant"
            )
        if round(RightAnkleAnglesDeg[1], 0) == 0:
            RightAnklePlantarDorsiflexion.insert(
                0, str(int(abs(round(RightAnkleAnglesDeg[1], 0)))) + ""
            )
        if round(RightAnkleAnglesDeg[2], 0) > 0:
            RightAnkleIntExtRotation.insert(
                0, str(int(abs(round(RightAnkleAnglesDeg[2], 0)))) + " Int"
            )
        if round(RightAnkleAnglesDeg[2], 0) < 0:
            RightAnkleIntExtRotation.insert(
                0, str(int(abs(round(RightAnkleAnglesDeg[2], 0)))) + " Ext"
            )
        if round(RightAnkleAnglesDeg[2], 0) == 0:
            RightAnkleIntExtRotation.insert(
                0, str(int(abs(round(RightAnkleAnglesDeg[2], 0)))) + ""
            )

        if round(RightFootAnglesDeg[2], 0) > 0:
            RightFootProgression.insert(
                0, str(int(abs(round(RightFootAnglesDeg[2], 0)))) + " Int"
            )
        if round(RightFootAnglesDeg[2], 0) < 0:
            RightFootProgression.insert(
                0, str(int(abs(round(RightFootAnglesDeg[2], 0)))) + " Ext"
            )
        if round(RightFootAnglesDeg[2], 0) == 0:
            RightFootProgression.insert(
                0, str(int(abs(round(RightFootAnglesDeg[2], 0)))) + ""
            )

        if round(RightTibialTorsion, 0) > 0:
            RightTibiaTorsion.insert(
                0, str(int(abs(round(RightTibialTorsion, 0)))) + " Ext"
            )
        if round(RightTibialTorsion, 0) < 0:
            RightTibiaTorsion.insert(
                0, str(int(abs(round(RightTibialTorsion, 0)))) + " Int"
            )
        if round(RightTibialTorsion, 0) == 0:
            RightTibiaTorsion.insert(
                0, str(int(abs(round(RightTibialTorsion, 0)))) + ""
            )

        if self.valueRightFootModelCheck == "1":
            if round(RightHindfootAnglesDeg[0], 0) > 0:
                RightHindfootInvEversion.insert(
                    0, str(int(abs(round(RightHindfootAnglesDeg[0], 0)))) + " Val"
                )
            if round(RightHindfootAnglesDeg[0], 0) < 0:
                RightHindfootInvEversion.insert(
                    0, str(int(abs(round(RightHindfootAnglesDeg[0], 0)))) + " Var"
                )
            if round(RightHindfootAnglesDeg[0], 0) == 0:
                RightHindfootInvEversion.insert(
                    0, str(int(abs(round(RightHindfootAnglesDeg[0], 0)))) + ""
                )
            if round(RightHindfootAnglesDeg[1], 0) > 0:
                RightHindfootPitch.insert(
                    0, str(int(abs(round(RightHindfootAnglesDeg[1], 0)))) + " Down"
                )
            if round(RightHindfootAnglesDeg[1], 0) < 0:
                RightHindfootPitch.insert(
                    0, str(int(abs(round(RightHindfootAnglesDeg[1], 0)))) + " Up"
                )
            if round(RightHindfootAnglesDeg[1], 0) == 0:
                RightHindfootPitch.insert(
                    0, str(int(abs(round(RightHindfootAnglesDeg[1], 0)))) + ""
                )
            if round(RightHindfootAnglesDeg[2], 0) > 0:
                RightHindfootProgression.insert(
                    0, str(int(abs(round(RightHindfootAnglesDeg[2], 0)))) + " Int"
                )
            if round(RightHindfootAnglesDeg[2], 0) < 0:
                RightHindfootProgression.insert(
                    0, str(int(abs(round(RightHindfootAnglesDeg[2], 0)))) + " Ext"
                )
            if round(RightHindfootAnglesDeg[2], 0) == 0:
                RightHindfootProgression.insert(
                    0, str(int(abs(round(RightHindfootAnglesDeg[2], 0)))) + ""
                )

            if round(RightAnkleComplexAnglesDeg[0], 0) > 0:
                RightAnkleComplexInvEversion.insert(
                    0, str(int(abs(round(RightAnkleComplexAnglesDeg[0], 0)))) + " Var"
                )
            if round(RightAnkleComplexAnglesDeg[0], 0) < 0:
                RightAnkleComplexInvEversion.insert(
                    0, str(int(abs(round(RightAnkleComplexAnglesDeg[0], 0)))) + " Val"
                )
            if round(RightAnkleComplexAnglesDeg[0], 0) == 0:
                RightAnkleComplexInvEversion.insert(
                    0, str(int(abs(round(RightAnkleComplexAnglesDeg[0], 0)))) + ""
                )

            #            if round(RightForefootAnglesDeg[0], 0) > 0:
            #                RightForefootInvEversion.insert(0, str(int(abs(round(RightForefootAnglesDeg[0], 0)))) +  " Inv")
            #            if round(RightForefootAnglesDeg[0], 0) < 0:
            #                RightForefootInvEversion.insert(0, str(int(abs(round(RightForefootAnglesDeg[0], 0)))) +  " Ev")
            #            if round(RightForefootAnglesDeg[0], 0) == 0:
            #                RightForefootInvEversion.insert(0, str(int(abs(round(RightForefootAnglesDeg[0], 0)))) +  "")
            if round(RightForefootAnglesDeg[1], 0) > 0:
                RightForefootPitch.insert(
                    0, str(int(abs(round(RightForefootAnglesDeg[1], 0)))) + " Down"
                )
            if round(RightForefootAnglesDeg[1], 0) < 0:
                RightForefootPitch.insert(
                    0, str(int(abs(round(RightForefootAnglesDeg[1], 0)))) + " Up"
                )
            if round(RightForefootAnglesDeg[1], 0) == 0:
                RightForefootPitch.insert(
                    0, str(int(abs(round(RightForefootAnglesDeg[1], 0)))) + ""
                )
            if round(RightForefootAnglesDeg[2], 0) > 0:
                RightForefootProgression.insert(
                    0, str(int(abs(round(RightForefootAnglesDeg[2], 0)))) + " Int"
                )
            if round(RightForefootAnglesDeg[2], 0) < 0:
                RightForefootProgression.insert(
                    0, str(int(abs(round(RightForefootAnglesDeg[2], 0)))) + " Ext"
                )
            if round(RightForefootAnglesDeg[2], 0) == 0:
                RightForefootProgression.insert(
                    0, str(int(abs(round(RightForefootAnglesDeg[2], 0)))) + ""
                )

            if round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0) > 0:
                RightMidfootAbAdduction.insert(
                    0,
                    str(
                        int(
                            abs(
                                round(
                                    RightForefootAnglesDeg[2]
                                    - RightHindfootAnglesDeg[2],
                                    0,
                                )
                            )
                        )
                    )
                    + " Add",
                )
            if round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0) < 0:
                RightMidfootAbAdduction.insert(
                    0,
                    str(
                        int(
                            abs(
                                round(
                                    RightForefootAnglesDeg[2]
                                    - RightHindfootAnglesDeg[2],
                                    0,
                                )
                            )
                        )
                    )
                    + " Abd",
                )
            if round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0) == 0:
                RightMidfootAbAdduction.insert(
                    0,
                    str(
                        int(
                            abs(
                                round(
                                    RightForefootAnglesDeg[2]
                                    - RightHindfootAnglesDeg[2],
                                    0,
                                )
                            )
                        )
                    )
                    + "",
                )

            if round(RightHalluxAnglesDeg[2], 0) > 0:
                RightHalluxProgression.insert(
                    0, str(int(abs(round(RightToesAnglesDeg[2], 0)))) + " Var"
                )
            if round(RightHalluxAnglesDeg[2], 0) < 0:
                RightHalluxProgression.insert(
                    0, str(int(abs(round(RightToesAnglesDeg[2], 0)))) + " Val"
                )
            if round(RightHalluxAnglesDeg[2], 0) == 0:
                RightHalluxProgression.insert(
                    0, str(int(abs(round(RightToesAnglesDeg[2], 0)))) + ""
                )

        # Make Calculated Fields Uneditable
        # Trunk
        LeftTrunkObliquity.configure(state="readonly")
        RightTrunkObliquity.configure(state="readonly")
        LeftTrunkTilt.configure(state="readonly")
        RightTrunkTilt.configure(state="readonly")
        LeftTrunkRotation.configure(state="readonly")
        RightTrunkRotation.configure(state="readonly")
        # Pelvis
        LeftPelvisObliquity.configure(state="readonly")
        RightPelvisObliquity.configure(state="readonly")
        LeftPelvisTilt.configure(state="readonly")
        RightPelvisTilt.configure(state="readonly")
        LeftPelvisRotation.configure(state="readonly")
        RightPelvisRotation.configure(state="readonly")
        # Hip
        LeftHipAbAdduction.configure(state="readonly")
        RightHipAbAdduction.configure(state="readonly")
        LeftHipFlexExtension.configure(state="readonly")
        RightHipFlexExtension.configure(state="readonly")
        LeftHipIntExtRotation.configure(state="readonly")
        RightHipIntExtRotation.configure(state="readonly")
        # Knee
        LeftKneeVarusValgus.configure(state="readonly")
        RightKneeVarusValgus.configure(state="readonly")
        LeftKneeFlexExtension.configure(state="readonly")
        RightKneeFlexExtension.configure(state="readonly")
        LeftKneeIntExtRotation.configure(state="readonly")
        RightKneeIntExtRotation.configure(state="readonly")
        LeftKneeProgression.configure(state="readonly")
        RightKneeProgression.configure(state="readonly")
        # Ankle
        LeftAnklePlantarDorsiflexion.configure(state="readonly")
        RightAnklePlantarDorsiflexion.configure(state="readonly")
        LeftAnkleIntExtRotation.configure(state="readonly")
        RightAnkleIntExtRotation.configure(state="readonly")
        # Foot
        LeftFootProgression.configure(state="readonly")
        RightFootProgression.configure(state="readonly")
        # Tibial Torsion
        LeftTibiaTorsion.configure(state="readonly")
        RightTibiaTorsion.configure(state="readonly")
        # Hindfoot
        LeftHindfootInvEversion.configure(state="readonly")
        RightHindfootInvEversion.configure(state="readonly")
        LeftHindfootPitch.configure(state="readonly")
        RightHindfootPitch.configure(state="readonly")
        LeftHindfootProgression.configure(state="readonly")
        RightHindfootProgression.configure(state="readonly")
        # Ankle Complex
        LeftAnkleComplexInvEversion.configure(state="readonly")
        RightAnkleComplexInvEversion.configure(state="readonly")
        # Forefoot
        LeftForefootPitch.configure(state="readonly")
        RightForefootPitch.configure(state="readonly")
        LeftForefootProgression.configure(state="readonly")
        RightForefootProgression.configure(state="readonly")
        # Midfoot
        LeftMidfootAbAdduction.configure(state="readonly")
        RightMidfootAbAdduction.configure(state="readonly")
        # Hallux
        LeftHalluxProgression.configure(state="readonly")
        RightHalluxProgression.configure(state="readonly")

        # =============================================================================
        #       Function to save Transformation matrics in Static_BF_MRN.py file. It gets executed with 'Save Pdf' and 'Save Results' Button.
        # =============================================================================
        def saveTransformationMatrices():
            # Read Current File
            StaticDataFile = open(StaticDataFileName, "r")
            lines = StaticDataFile.readlines()
            StaticDataFile.close()

            # Write Subject Data into Static Anthropometric File
            StaticDataFile = open(StaticDataFileName, "w+")
            # Rewrite Subject Information
            TransformationMatricesBlockStarts = 0
            for line in lines:
                words = line.split()
                if words[0] == "#" and words[1] == "Transformation":
                    TransformationMatricesBlockStarts = 1
                if TransformationMatricesBlockStarts == 0:
                    StaticDataFile.write(line)
            # Write Tranformation Matrices
            StaticDataFile.write("# Transformation Matrices" + "\n")

            StaticDataFile.write(
                "self.valueLeftHipCenterPelvis = np.array(["
                + str(LeftHipCenterPelvis[0])
                + ","
                + str(LeftHipCenterPelvis[1])
                + ","
                + str(LeftHipCenterPelvis[2])
                + "])"
                + "\n"
            )
            StaticDataFile.write(
                "self.valueLeftKneeCenterThigh = np.array(["
                + str(LeftKneeCenterThigh[0])
                + ","
                + str(LeftKneeCenterThigh[1])
                + ","
                + str(LeftKneeCenterThigh[2])
                + "])"
                + "\n"
            )
            StaticDataFile.write(
                "self.valueLeftAnkleCenterShank = np.array(["
                + str(LeftAnkleCenterShank[0])
                + ","
                + str(LeftAnkleCenterShank[1])
                + ","
                + str(LeftAnkleCenterShank[2])
                + "])"
                + "\n"
            )

            StaticDataFile.write(
                "self.valueRightHipCenterPelvis = np.array(["
                + str(RightHipCenterPelvis[0])
                + ","
                + str(RightHipCenterPelvis[1])
                + ","
                + str(RightHipCenterPelvis[2])
                + "])"
                + "\n"
            )
            StaticDataFile.write(
                "self.valueRightKneeCenterThigh = np.array(["
                + str(RightKneeCenterThigh[0])
                + ","
                + str(RightKneeCenterThigh[1])
                + ","
                + str(RightKneeCenterThigh[2])
                + "])"
                + "\n"
            )
            StaticDataFile.write(
                "self.valueRightAnkleCenterShank = np.array(["
                + str(RightAnkleCenterShank[0])
                + ","
                + str(RightAnkleCenterShank[1])
                + ","
                + str(RightAnkleCenterShank[2])
                + "])"
                + "\n"
            )

            # Write Tibial Torsion
            if round(LeftTibialTorsion, 0) > 0:
                StaticDataFile.write(
                    "self.valueLeftTibialTorsion =  "
                    + "'"
                    + str(abs(round(LeftTibialTorsion, 2)))
                    + " Ext"
                    + "'"
                    + "\n"
                )
            if round(LeftTibialTorsion, 0) < 0:
                StaticDataFile.write(
                    "self.valueLeftTibialTorsion =  "
                    + "'"
                    + str(abs(round(LeftTibialTorsion, 2)))
                    + " Int"
                    + "'"
                    + "\n"
                )
            if round(LeftTibialTorsion, 0) == 0:
                StaticDataFile.write(
                    "self.valueLeftTibialTorsion =  "
                    + "'"
                    + str(abs(round(LeftTibialTorsion, 2)))
                    + ""
                    + "'"
                    + "\n"
                )

            if round(RightTibialTorsion, 0) > 0:
                StaticDataFile.write(
                    "self.valueRightTibialTorsion =  "
                    + "'"
                    + str(abs(round(RightTibialTorsion, 2)))
                    + " Ext"
                    + "'"
                    + "\n"
                )
            if round(RightTibialTorsion, 0) < 0:
                StaticDataFile.write(
                    "self.valueRightTibialTorsion =  "
                    + "'"
                    + str(abs(round(RightTibialTorsion, 2)))
                    + " Int"
                    + "'"
                    + "\n"
                )
            if round(RightTibialTorsion, 0) == 0:
                StaticDataFile.write(
                    "self.valueRightTibialTorsion =  "
                    + "'"
                    + str(abs(round(RightTibialTorsion, 2)))
                    + ""
                    + "'"
                    + "\n"
                )

            StaticDataFile.write(
                "self.valueETrunkAnatRelTech = np.array([["
                + str(ETrunkAnatRelTech[0, 0])
                + ","
                + str(ETrunkAnatRelTech[0, 1])
                + ","
                + str(ETrunkAnatRelTech[0, 2])
                + "],["
                + str(ETrunkAnatRelTech[1, 0])
                + ","
                + str(ETrunkAnatRelTech[1, 1])
                + ","
                + str(ETrunkAnatRelTech[1, 2])
                + "],["
                + str(ETrunkAnatRelTech[2, 0])
                + ","
                + str(ETrunkAnatRelTech[2, 1])
                + ","
                + str(ETrunkAnatRelTech[2, 2])
                + "]])"
                + "\n"
            )

            StaticDataFile.write(
                "self.valueEPelvisAnatRelTech = np.array([["
                + str(EPelvisAnatRelTech[0, 0])
                + ","
                + str(EPelvisAnatRelTech[0, 1])
                + ","
                + str(EPelvisAnatRelTech[0, 2])
                + "],["
                + str(EPelvisAnatRelTech[1, 0])
                + ","
                + str(EPelvisAnatRelTech[1, 1])
                + ","
                + str(EPelvisAnatRelTech[1, 2])
                + "],["
                + str(EPelvisAnatRelTech[2, 0])
                + ","
                + str(EPelvisAnatRelTech[2, 1])
                + ","
                + str(EPelvisAnatRelTech[2, 2])
                + "]])"
                + "\n"
            )

            StaticDataFile.write(
                "self.valueLeftEThighAnatRelTech = np.array([["
                + str(LeftEThighAnatRelTech[0, 0])
                + ","
                + str(LeftEThighAnatRelTech[0, 1])
                + ","
                + str(LeftEThighAnatRelTech[0, 2])
                + "],["
                + str(LeftEThighAnatRelTech[1, 0])
                + ","
                + str(LeftEThighAnatRelTech[1, 1])
                + ","
                + str(LeftEThighAnatRelTech[1, 2])
                + "],["
                + str(LeftEThighAnatRelTech[2, 0])
                + ","
                + str(LeftEThighAnatRelTech[2, 1])
                + ","
                + str(LeftEThighAnatRelTech[2, 2])
                + "]])"
                + "\n"
            )

            StaticDataFile.write(
                "self.valueLeftEShankProximalAnatRelTech = np.array([["
                + str(LeftEShankProximalAnatRelTech[0, 0])
                + ","
                + str(LeftEShankProximalAnatRelTech[0, 1])
                + ","
                + str(LeftEShankProximalAnatRelTech[0, 2])
                + "],["
                + str(LeftEShankProximalAnatRelTech[1, 0])
                + ","
                + str(LeftEShankProximalAnatRelTech[1, 1])
                + ","
                + str(LeftEShankProximalAnatRelTech[1, 2])
                + "],["
                + str(LeftEShankProximalAnatRelTech[2, 0])
                + ","
                + str(LeftEShankProximalAnatRelTech[2, 1])
                + ","
                + str(LeftEShankProximalAnatRelTech[2, 2])
                + "]])"
                + "\n"
            )

            StaticDataFile.write(
                "self.valueLeftEShankDistalAnatRelTech = np.array([["
                + str(LeftEShankDistalAnatRelTech[0, 0])
                + ","
                + str(LeftEShankDistalAnatRelTech[0, 1])
                + ","
                + str(LeftEShankDistalAnatRelTech[0, 2])
                + "],["
                + str(LeftEShankDistalAnatRelTech[1, 0])
                + ","
                + str(LeftEShankDistalAnatRelTech[1, 1])
                + ","
                + str(LeftEShankDistalAnatRelTech[1, 2])
                + "],["
                + str(LeftEShankDistalAnatRelTech[2, 0])
                + ","
                + str(LeftEShankDistalAnatRelTech[2, 1])
                + ","
                + str(LeftEShankDistalAnatRelTech[2, 2])
                + "]])"
                + "\n"
            )

            StaticDataFile.write(
                "self.valueLeftEFootAnatRelTech = np.array([["
                + str(LeftEFootAnatRelTech[0, 0])
                + ","
                + str(LeftEFootAnatRelTech[0, 1])
                + ","
                + str(LeftEFootAnatRelTech[0, 2])
                + "],["
                + str(LeftEFootAnatRelTech[1, 0])
                + ","
                + str(LeftEFootAnatRelTech[1, 1])
                + ","
                + str(LeftEFootAnatRelTech[1, 2])
                + "],["
                + str(LeftEFootAnatRelTech[2, 0])
                + ","
                + str(LeftEFootAnatRelTech[2, 1])
                + ","
                + str(LeftEFootAnatRelTech[2, 2])
                + "]])"
                + "\n"
            )
            StaticDataFile.write(
                "self.valueLeftEFootAnat2RelTech = np.array([["
                + str(LeftEFootAnat2RelTech[0, 0])
                + ","
                + str(LeftEFootAnat2RelTech[0, 1])
                + ","
                + str(LeftEFootAnat2RelTech[0, 2])
                + "],["
                + str(LeftEFootAnat2RelTech[1, 0])
                + ","
                + str(LeftEFootAnat2RelTech[1, 1])
                + ","
                + str(LeftEFootAnat2RelTech[1, 2])
                + "],["
                + str(LeftEFootAnat2RelTech[2, 0])
                + ","
                + str(LeftEFootAnat2RelTech[2, 1])
                + ","
                + str(LeftEFootAnat2RelTech[2, 2])
                + "]])"
                + "\n"
            )

            if self.valueLeftFootModelCheck == "1":
                StaticDataFile.write(
                    "self.valueLeftEHindfootAnatRelTech = np.array([["
                    + str(LeftEHindfootAnatRelTech[0, 0])
                    + ","
                    + str(LeftEHindfootAnatRelTech[0, 1])
                    + ","
                    + str(LeftEHindfootAnatRelTech[0, 2])
                    + "],["
                    + str(LeftEHindfootAnatRelTech[1, 0])
                    + ","
                    + str(LeftEHindfootAnatRelTech[1, 1])
                    + ","
                    + str(LeftEHindfootAnatRelTech[1, 2])
                    + "],["
                    + str(LeftEHindfootAnatRelTech[2, 0])
                    + ","
                    + str(LeftEHindfootAnatRelTech[2, 1])
                    + ","
                    + str(LeftEHindfootAnatRelTech[2, 2])
                    + "]])"
                    + "\n"
                )

                StaticDataFile.write(
                    "self.valueLeftEForefootAnatRelTech = np.array([["
                    + str(LeftEForefootAnatRelTech[0, 0])
                    + ","
                    + str(LeftEForefootAnatRelTech[0, 1])
                    + ","
                    + str(LeftEForefootAnatRelTech[0, 2])
                    + "],["
                    + str(LeftEForefootAnatRelTech[1, 0])
                    + ","
                    + str(LeftEForefootAnatRelTech[1, 1])
                    + ","
                    + str(LeftEForefootAnatRelTech[1, 2])
                    + "],["
                    + str(LeftEForefootAnatRelTech[2, 0])
                    + ","
                    + str(LeftEForefootAnatRelTech[2, 1])
                    + ","
                    + str(LeftEForefootAnatRelTech[2, 2])
                    + "]])"
                    + "\n"
                )

                StaticDataFile.write(
                    "self.valueLeftEHalluxAnatRelTech = np.array([["
                    + str(LeftEHalluxAnatRelTech[0, 0])
                    + ","
                    + str(LeftEHalluxAnatRelTech[0, 1])
                    + ","
                    + str(LeftEHalluxAnatRelTech[0, 2])
                    + "],["
                    + str(LeftEHalluxAnatRelTech[1, 0])
                    + ","
                    + str(LeftEHalluxAnatRelTech[1, 1])
                    + ","
                    + str(LeftEHalluxAnatRelTech[1, 2])
                    + "],["
                    + str(LeftEHalluxAnatRelTech[2, 0])
                    + ","
                    + str(LeftEHalluxAnatRelTech[2, 1])
                    + ","
                    + str(LeftEHalluxAnatRelTech[2, 2])
                    + "]])"
                    + "\n"
                )

                StaticDataFile.write(
                    "self.valueLeft23MetatarsalHeadMarkerForefoot = np.array(["
                    + str(Left23MetatarsalHeadMarkerForefoot[0])
                    + ","
                    + str(Left23MetatarsalHeadMarkerForefoot[1])
                    + ","
                    + str(Left23MetatarsalHeadMarkerForefoot[2])
                    + "])"
                    + "\n"
                )
                StaticDataFile.write(
                    "self.valueLeftFirstMetatarsoPhalangealJointMarkerForefoot = np.array(["
                    + str(LeftFirstMetatarsoPhalangealJointMarkerForefoot[0])
                    + ","
                    + str(LeftFirstMetatarsoPhalangealJointMarkerForefoot[1])
                    + ","
                    + str(LeftFirstMetatarsoPhalangealJointMarkerForefoot[2])
                    + "])"
                    + "\n"
                )

            StaticDataFile.write(
                "self.valueRightEThighAnatRelTech = np.array([["
                + str(RightEThighAnatRelTech[0, 0])
                + ","
                + str(RightEThighAnatRelTech[0, 1])
                + ","
                + str(RightEThighAnatRelTech[0, 2])
                + "],["
                + str(RightEThighAnatRelTech[1, 0])
                + ","
                + str(RightEThighAnatRelTech[1, 1])
                + ","
                + str(RightEThighAnatRelTech[1, 2])
                + "],["
                + str(RightEThighAnatRelTech[2, 0])
                + ","
                + str(RightEThighAnatRelTech[2, 1])
                + ","
                + str(RightEThighAnatRelTech[2, 2])
                + "]])"
                + "\n"
            )

            StaticDataFile.write(
                "self.valueRightEShankProximalAnatRelTech = np.array([["
                + str(RightEShankProximalAnatRelTech[0, 0])
                + ","
                + str(RightEShankProximalAnatRelTech[0, 1])
                + ","
                + str(RightEShankProximalAnatRelTech[0, 2])
                + "],["
                + str(RightEShankProximalAnatRelTech[1, 0])
                + ","
                + str(RightEShankProximalAnatRelTech[1, 1])
                + ","
                + str(RightEShankProximalAnatRelTech[1, 2])
                + "],["
                + str(RightEShankProximalAnatRelTech[2, 0])
                + ","
                + str(RightEShankProximalAnatRelTech[2, 1])
                + ","
                + str(RightEShankProximalAnatRelTech[2, 2])
                + "]])"
                + "\n"
            )

            StaticDataFile.write(
                "self.valueRightEShankDistalAnatRelTech = np.array([["
                + str(RightEShankDistalAnatRelTech[0, 0])
                + ","
                + str(RightEShankDistalAnatRelTech[0, 1])
                + ","
                + str(RightEShankDistalAnatRelTech[0, 2])
                + "],["
                + str(RightEShankDistalAnatRelTech[1, 0])
                + ","
                + str(RightEShankDistalAnatRelTech[1, 1])
                + ","
                + str(RightEShankDistalAnatRelTech[1, 2])
                + "],["
                + str(RightEShankDistalAnatRelTech[2, 0])
                + ","
                + str(RightEShankDistalAnatRelTech[2, 1])
                + ","
                + str(RightEShankDistalAnatRelTech[2, 2])
                + "]])"
                + "\n"
            )

            StaticDataFile.write(
                "self.valueRightEFootAnatRelTech = np.array([["
                + str(RightEFootAnatRelTech[0, 0])
                + ","
                + str(RightEFootAnatRelTech[0, 1])
                + ","
                + str(RightEFootAnatRelTech[0, 2])
                + "],["
                + str(RightEFootAnatRelTech[1, 0])
                + ","
                + str(RightEFootAnatRelTech[1, 1])
                + ","
                + str(RightEFootAnatRelTech[1, 2])
                + "],["
                + str(RightEFootAnatRelTech[2, 0])
                + ","
                + str(RightEFootAnatRelTech[2, 1])
                + ","
                + str(RightEFootAnatRelTech[2, 2])
                + "]])"
                + "\n"
            )
            StaticDataFile.write(
                "self.valueRightEFootAnat2RelTech = np.array([["
                + str(RightEFootAnat2RelTech[0, 0])
                + ","
                + str(RightEFootAnat2RelTech[0, 1])
                + ","
                + str(RightEFootAnat2RelTech[0, 2])
                + "],["
                + str(RightEFootAnat2RelTech[1, 0])
                + ","
                + str(RightEFootAnat2RelTech[1, 1])
                + ","
                + str(RightEFootAnat2RelTech[1, 2])
                + "],["
                + str(RightEFootAnat2RelTech[2, 0])
                + ","
                + str(RightEFootAnat2RelTech[2, 1])
                + ","
                + str(RightEFootAnat2RelTech[2, 2])
                + "]])"
                + "\n"
            )
            if self.valueRightFootModelCheck == "1":
                StaticDataFile.write(
                    "self.valueRightEHindfootAnatRelTech = np.array([["
                    + str(RightEHindfootAnatRelTech[0, 0])
                    + ","
                    + str(RightEHindfootAnatRelTech[0, 1])
                    + ","
                    + str(RightEHindfootAnatRelTech[0, 2])
                    + "],["
                    + str(RightEHindfootAnatRelTech[1, 0])
                    + ","
                    + str(RightEHindfootAnatRelTech[1, 1])
                    + ","
                    + str(RightEHindfootAnatRelTech[1, 2])
                    + "],["
                    + str(RightEHindfootAnatRelTech[2, 0])
                    + ","
                    + str(RightEHindfootAnatRelTech[2, 1])
                    + ","
                    + str(RightEHindfootAnatRelTech[2, 2])
                    + "]])"
                    + "\n"
                )

                StaticDataFile.write(
                    "self.valueRightEForefootAnatRelTech = np.array([["
                    + str(RightEForefootAnatRelTech[0, 0])
                    + ","
                    + str(RightEForefootAnatRelTech[0, 1])
                    + ","
                    + str(RightEForefootAnatRelTech[0, 2])
                    + "],["
                    + str(RightEForefootAnatRelTech[1, 0])
                    + ","
                    + str(RightEForefootAnatRelTech[1, 1])
                    + ","
                    + str(RightEForefootAnatRelTech[1, 2])
                    + "],["
                    + str(RightEForefootAnatRelTech[2, 0])
                    + ","
                    + str(RightEForefootAnatRelTech[2, 1])
                    + ","
                    + str(RightEForefootAnatRelTech[2, 2])
                    + "]])"
                    + "\n"
                )

                StaticDataFile.write(
                    "self.valueRightEHalluxAnatRelTech = np.array([["
                    + str(RightEHalluxAnatRelTech[0, 0])
                    + ","
                    + str(RightEHalluxAnatRelTech[0, 1])
                    + ","
                    + str(RightEHalluxAnatRelTech[0, 2])
                    + "],["
                    + str(RightEHalluxAnatRelTech[1, 0])
                    + ","
                    + str(RightEHalluxAnatRelTech[1, 1])
                    + ","
                    + str(RightEHalluxAnatRelTech[1, 2])
                    + "],["
                    + str(RightEHalluxAnatRelTech[2, 0])
                    + ","
                    + str(RightEHalluxAnatRelTech[2, 1])
                    + ","
                    + str(RightEHalluxAnatRelTech[2, 2])
                    + "]])"
                    + "\n"
                )

                StaticDataFile.write(
                    "self.valueRight23MetatarsalHeadMarkerForefoot = np.array(["
                    + str(Right23MetatarsalHeadMarkerForefoot[0])
                    + ","
                    + str(Right23MetatarsalHeadMarkerForefoot[1])
                    + ","
                    + str(Right23MetatarsalHeadMarkerForefoot[2])
                    + "])"
                    + "\n"
                )
                StaticDataFile.write(
                    "self.valueRightFirstMetatarsoPhalangealJointMarkerForefoot = np.array(["
                    + str(RightFirstMetatarsoPhalangealJointMarkerForefoot[0])
                    + ","
                    + str(RightFirstMetatarsoPhalangealJointMarkerForefoot[1])
                    + ","
                    + str(RightFirstMetatarsoPhalangealJointMarkerForefoot[2])
                    + "])"
                    + "\n"
                )

            # print('FileUpdate- Tmatrix')
            StaticDataFile.close()

        def saveResultsinC3D():
            # Function to extract markerdata into an array and check if data exists
            def MarkerArrayCheck(Subject, MarkerName):
                # Check if marker exists at all
                if self.HasTrajectory(Subject, MarkerName) is True:
                    MarkerDataX, MarkerDataY, MarkerDataZ, MarkerDataExists = (
                        fields[MarkerName]["X"],
                        fields[MarkerName]["Y"],
                        fields[MarkerName]["Z"],
                        fields[MarkerName]["Exists"],
                    )

                else:
                    framecount = fields["Frames"]
                    MarkerDataX = [0 for m in range(framecount)]
                    MarkerDataY = [0 for m in range(framecount)]
                    MarkerDataZ = [0 for m in range(framecount)]
                    MarkerDataExists = [False] * framecount
                return MarkerDataX, MarkerDataY, MarkerDataZ, MarkerDataExists

            exec(open(StaticDataFileName).read())
            # execfile(UserPreferencesFileName)

            # Initialize arrays to write to C3D File
            framecount = fields["Frames"]
            exists = [True] * framecount

            arrayLeftHipCenter = [[0.0 for m in range(framecount)] for n in range(3)]
            arrayRightHipCenter = [[0.0 for m in range(framecount)] for n in range(3)]
            arrayLeftKneeCenter = [[0.0 for m in range(framecount)] for n in range(3)]
            arrayRightKneeCenter = [[0.0 for m in range(framecount)] for n in range(3)]
            arrayLeftAnkleCenter = [[0.0 for m in range(framecount)] for n in range(3)]
            arrayRightAnkleCenter = [[0.0 for m in range(framecount)] for n in range(3)]
            arrayLeftVirtualKneeMarker = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayRightVirtualKneeMarker = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]

            arrayLeftLateralKneeMarkerX = [0 for m in range(framecount)]
            arrayLeftLateralKneeMarkerY = [0 for m in range(framecount)]
            arrayLeftLateralKneeMarkerZ = [0 for m in range(framecount)]
            arrayRightLateralKneeMarkerX = [0 for m in range(framecount)]
            arrayRightLateralKneeMarkerY = [0 for m in range(framecount)]
            arrayRightLateralKneeMarkerZ = [0 for m in range(framecount)]

            # For Sacral Triad Case, delete Sacral Marker Name
            # Explanation: When Sacral marker is used and exists in the UserPreferences, then
            # Sacral Marker Name is deleted to push the code towards using PSIS markers.
            if self.valuePelvicFixCheck == "2":
                try:
                    del self.SacralMarkerName
                except:
                    pass
            else:
                pass

            # =============================================================================
            #      Read Marker Data
            # =============================================================================
            C7MarkerX, C7MarkerY, C7MarkerZ, C7MarkerExists = MarkerArrayCheck(
                SubjectName, self.C7MarkerName
            )
            (
                LeftClavicleMarkerX,
                LeftClavicleMarkerY,
                LeftClavicleMarkerZ,
                LeftClavicleMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftClavicleMarkerName)
            (
                RightClavicleMarkerX,
                RightClavicleMarkerY,
                RightClavicleMarkerZ,
                RightClavicleMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightClavicleMarkerName)
            try:
                SacralMarkerX, SacralMarkerY, SacralMarkerZ, SacralMarkerExists = (
                    MarkerArrayCheck(SubjectName, self.SacralMarkerName)
                )
                # print('Sacral Marker Found')
            except:
                # print('Sacral Marker Not Found')
                (
                    LeftPSISMarkerX,
                    LeftPSISMarkerY,
                    LeftPSISMarkerZ,
                    LeftPSISMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.LeftPSISMarkerName)
                (
                    RightPSISMarkerX,
                    RightPSISMarkerY,
                    RightPSISMarkerZ,
                    RightPSISMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.RightPSISMarkerName)
                framecount = fields["Frames"]
                SacralMarkerX = [0 for m in range(framecount)]
                SacralMarkerY = [0 for m in range(framecount)]
                SacralMarkerZ = [0 for m in range(framecount)]
                for FrameNumber in range(StartFrame, EndFrame):
                    SacralMarkerX[FrameNumber] = (
                        LeftPSISMarkerX[FrameNumber] + RightPSISMarkerX[FrameNumber]
                    ) / 2
                    SacralMarkerY[FrameNumber] = (
                        LeftPSISMarkerY[FrameNumber] + RightPSISMarkerY[FrameNumber]
                    ) / 2
                    SacralMarkerZ[FrameNumber] = (
                        LeftPSISMarkerZ[FrameNumber] + RightPSISMarkerZ[FrameNumber]
                    ) / 2
            LeftASISMarkerX, LeftASISMarkerY, LeftASISMarkerZ, LeftASISMarkerExists = (
                MarkerArrayCheck(SubjectName, self.LeftASISMarkerName)
            )
            (
                LeftThighMarkerX,
                LeftThighMarkerY,
                LeftThighMarkerZ,
                LeftThighMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftThighMarkerName)
            # LeftLateralKneeMarkerX, LeftLateralKneeMarkerY, LeftLateralKneeMarkerZ, LeftLateralKneeMarkerExists = MarkerArrayCheck(SubjectName, self.LeftLateralKneeMarkerName)
            (
                LeftTibialMarkerX,
                LeftTibialMarkerY,
                LeftTibialMarkerZ,
                LeftTibialMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftTibialMarkerName)
            (
                LeftLateralAnkleMarkerX,
                LeftLateralAnkleMarkerY,
                LeftLateralAnkleMarkerZ,
                LeftLateralAnkleMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftLateralAnkleMarkerName)
            LeftToeMarkerX, LeftToeMarkerY, LeftToeMarkerZ, LeftToeMarkerExists = (
                MarkerArrayCheck(SubjectName, self.LeftToeMarkerName)
            )
            (
                LeftMedialAnkleMarkerX,
                LeftMedialAnkleMarkerY,
                LeftMedialAnkleMarkerZ,
                LeftMedialAnkleMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftMedialAnkleMarkerName)
            LeftHeelMarkerX, LeftHeelMarkerY, LeftHeelMarkerZ, LeftHeelMarkerExists = (
                MarkerArrayCheck(SubjectName, self.LeftHeelMarkerName)
            )
            (
                RightASISMarkerX,
                RightASISMarkerY,
                RightASISMarkerZ,
                RightASISMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightASISMarkerName)
            (
                RightThighMarkerX,
                RightThighMarkerY,
                RightThighMarkerZ,
                RightThighMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightThighMarkerName)
            # RightLateralKneeMarkerX, RightLateralKneeMarkerY, RightLateralKneeMarkerZ, RightLateralKneeMarkerExists = MarkerArrayCheck(SubjectName, self.RightLateralKneeMarkerName)
            (
                RightTibialMarkerX,
                RightTibialMarkerY,
                RightTibialMarkerZ,
                RightTibialMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightTibialMarkerName)
            (
                RightLateralAnkleMarkerX,
                RightLateralAnkleMarkerY,
                RightLateralAnkleMarkerZ,
                RightLateralAnkleMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightLateralAnkleMarkerName)
            RightToeMarkerX, RightToeMarkerY, RightToeMarkerZ, RightToeMarkerExists = (
                MarkerArrayCheck(SubjectName, self.RightToeMarkerName)
            )
            (
                RightMedialAnkleMarkerX,
                RightMedialAnkleMarkerY,
                RightMedialAnkleMarkerZ,
                RightMedialAnkleMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightMedialAnkleMarkerName)
            (
                RightHeelMarkerX,
                RightHeelMarkerY,
                RightHeelMarkerZ,
                RightHeelMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightHeelMarkerName)

            if self.valueKneeAlignmentCheck == "0":
                (
                    LeftLateralKADMarkerX,
                    LeftLateralKADMarkerY,
                    LeftLateralKADMarkerZ,
                    LeftLateralKADMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.LeftLateralKADMarkerName)
                (
                    LeftUpperKADMarkerX,
                    LeftUpperKADMarkerY,
                    LeftUpperKADMarkerZ,
                    LeftUpperKADMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.LeftUpperKADMarkerName)
                (
                    LeftLowerKADMarkerX,
                    LeftLowerKADMarkerY,
                    LeftLowerKADMarkerZ,
                    LeftLowerKADMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.LeftLowerKADMarkerName)

                (
                    RightLateralKADMarkerX,
                    RightLateralKADMarkerY,
                    RightLateralKADMarkerZ,
                    RightLateralKADMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.RightLateralKADMarkerName)
                (
                    RightUpperKADMarkerX,
                    RightUpperKADMarkerY,
                    RightUpperKADMarkerZ,
                    RightUpperKADMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.RightUpperKADMarkerName)
                (
                    RightLowerKADMarkerX,
                    RightLowerKADMarkerY,
                    RightLowerKADMarkerZ,
                    RightLowerKADMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.RightLowerKADMarkerName)
            else:
                (
                    LeftLateralKneeMarkerX,
                    LeftLateralKneeMarkerY,
                    LeftLateralKneeMarkerZ,
                    LeftLateralKneeMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.LeftLateralKneeMarkerName)
                (
                    LeftMedialKneeMarkerX,
                    LeftMedialKneeMarkerY,
                    LeftMedialKneeMarkerZ,
                    LeftMedialKneeMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.LeftMedialKneeMarkerName)

                (
                    RightLateralKneeMarkerX,
                    RightLateralKneeMarkerY,
                    RightLateralKneeMarkerZ,
                    RightLateralKneeMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.RightLateralKneeMarkerName)
                (
                    RightMedialKneeMarkerX,
                    RightMedialKneeMarkerY,
                    RightMedialKneeMarkerZ,
                    RightMedialKneeMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.RightMedialKneeMarkerName)

            # =============================================================================
            #      Check for Medial Ankle marker drop-off
            # =============================================================================
            framecount = fields["Frames"]
            LeftMedialAnkleMarkerDropOff = 0
            RightMedialAnkleMarkerDropOff = 0
            for FrameNumber in range(StartFrame, EndFrame):
                if LeftMedialAnkleMarkerZ[FrameNumber] == 0:
                    LeftMedialAnkleMarkerDropOff = 1
                if RightMedialAnkleMarkerZ[FrameNumber] == 0:
                    RightMedialAnkleMarkerDropOff = 1

            # Tibial Triad Check
            if (
                self.HasTrajectory(SubjectName, self.LeftTibialMarkerName) is True
                and self.HasTrajectory(SubjectName, self.LeftTibialUpperMarkerName)
                is True
                and self.HasTrajectory(SubjectName, self.LeftTibialLowerMarkerName)
                is True
            ):
                LeftTibialTriadCheck = True
                (
                    LeftTibialUpperMarkerX,
                    LeftTibialUpperMarkerY,
                    LeftTibialUpperMarkerZ,
                    LeftTibialUpperMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.LeftTibialUpperMarkerName)
                (
                    LeftTibialLowerMarkerX,
                    LeftTibialLowerMarkerY,
                    LeftTibialLowerMarkerZ,
                    LeftTibialLowerMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.LeftTibialLowerMarkerName)
            else:
                LeftTibialTriadCheck = False
            if (
                self.HasTrajectory(SubjectName, self.RightTibialMarkerName) is True
                and self.HasTrajectory(SubjectName, self.RightTibialUpperMarkerName)
                is True
                and self.HasTrajectory(SubjectName, self.RightTibialLowerMarkerName)
                is True
            ):
                RightTibialTriadCheck = True
                (
                    RightTibialUpperMarkerX,
                    RightTibialUpperMarkerY,
                    RightTibialUpperMarkerZ,
                    RightTibialUpperMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.RightTibialUpperMarkerName)
                (
                    RightTibialLowerMarkerX,
                    RightTibialLowerMarkerY,
                    RightTibialLowerMarkerZ,
                    RightTibialLowerMarkerExists,
                ) = MarkerArrayCheck(SubjectName, self.RightTibialLowerMarkerName)
            else:
                RightTibialTriadCheck = False
            # print LeftTibialTriadCheck, RightTibialTriadCheck

            for FrameNumber in range(StartFrame, EndFrame):
                # Transform marker data if necessary based on direction that the patient is walking
                C7Marker = np.array(
                    [
                        C7MarkerX[FrameNumber],
                        C7MarkerY[FrameNumber],
                        C7MarkerZ[FrameNumber],
                    ]
                )
                LeftClavicleMarker = np.array(
                    [
                        LeftClavicleMarkerX[FrameNumber],
                        LeftClavicleMarkerY[FrameNumber],
                        LeftClavicleMarkerZ[FrameNumber],
                    ]
                )
                RightClavicleMarker = np.array(
                    [
                        RightClavicleMarkerX[FrameNumber],
                        RightClavicleMarkerY[FrameNumber],
                        RightClavicleMarkerZ[FrameNumber],
                    ]
                )
                SacralMarker = np.array(
                    [
                        SacralMarkerX[FrameNumber],
                        SacralMarkerY[FrameNumber],
                        SacralMarkerZ[FrameNumber],
                    ]
                )
                LeftASISMarker = np.array(
                    [
                        LeftASISMarkerX[FrameNumber],
                        LeftASISMarkerY[FrameNumber],
                        LeftASISMarkerZ[FrameNumber],
                    ]
                )
                LeftThighMarker = np.array(
                    [
                        LeftThighMarkerX[FrameNumber],
                        LeftThighMarkerY[FrameNumber],
                        LeftThighMarkerZ[FrameNumber],
                    ]
                )
                LeftTibialMarker = np.array(
                    [
                        LeftTibialMarkerX[FrameNumber],
                        LeftTibialMarkerY[FrameNumber],
                        LeftTibialMarkerZ[FrameNumber],
                    ]
                )
                if LeftTibialTriadCheck is True:
                    LeftTibialUpperMarker = np.array(
                        [
                            LeftTibialUpperMarkerX[FrameNumber],
                            LeftTibialUpperMarkerY[FrameNumber],
                            LeftTibialUpperMarkerZ[FrameNumber],
                        ]
                    )
                    LeftTibialLowerMarker = np.array(
                        [
                            LeftTibialLowerMarkerX[FrameNumber],
                            LeftTibialLowerMarkerY[FrameNumber],
                            LeftTibialLowerMarkerZ[FrameNumber],
                        ]
                    )
                LeftLateralAnkleMarker = np.array(
                    [
                        LeftLateralAnkleMarkerX[FrameNumber],
                        LeftLateralAnkleMarkerY[FrameNumber],
                        LeftLateralAnkleMarkerZ[FrameNumber],
                    ]
                )
                LeftToeMarker = np.array(
                    [
                        LeftToeMarkerX[FrameNumber],
                        LeftToeMarkerY[FrameNumber],
                        LeftToeMarkerZ[FrameNumber],
                    ]
                )
                LeftMedialAnkleMarker = np.array(
                    [
                        LeftMedialAnkleMarkerX[FrameNumber],
                        LeftMedialAnkleMarkerY[FrameNumber],
                        LeftMedialAnkleMarkerZ[FrameNumber],
                    ]
                )
                LeftHeelMarker = np.array(
                    [
                        LeftHeelMarkerX[FrameNumber],
                        LeftHeelMarkerY[FrameNumber],
                        LeftHeelMarkerZ[FrameNumber],
                    ]
                )
                RightASISMarker = np.array(
                    [
                        RightASISMarkerX[FrameNumber],
                        RightASISMarkerY[FrameNumber],
                        RightASISMarkerZ[FrameNumber],
                    ]
                )
                RightThighMarker = np.array(
                    [
                        RightThighMarkerX[FrameNumber],
                        RightThighMarkerY[FrameNumber],
                        RightThighMarkerZ[FrameNumber],
                    ]
                )
                RightTibialMarker = np.array(
                    [
                        RightTibialMarkerX[FrameNumber],
                        RightTibialMarkerY[FrameNumber],
                        RightTibialMarkerZ[FrameNumber],
                    ]
                )
                if RightTibialTriadCheck is True:
                    RightTibialUpperMarker = np.array(
                        [
                            RightTibialUpperMarkerX[FrameNumber],
                            RightTibialUpperMarkerY[FrameNumber],
                            RightTibialUpperMarkerZ[FrameNumber],
                        ]
                    )
                    RightTibialLowerMarker = np.array(
                        [
                            RightTibialLowerMarkerX[FrameNumber],
                            RightTibialLowerMarkerY[FrameNumber],
                            RightTibialLowerMarkerZ[FrameNumber],
                        ]
                    )
                RightLateralAnkleMarker = np.array(
                    [
                        RightLateralAnkleMarkerX[FrameNumber],
                        RightLateralAnkleMarkerY[FrameNumber],
                        RightLateralAnkleMarkerZ[FrameNumber],
                    ]
                )
                RightToeMarker = np.array(
                    [
                        RightToeMarkerX[FrameNumber],
                        RightToeMarkerY[FrameNumber],
                        RightToeMarkerZ[FrameNumber],
                    ]
                )
                RightMedialAnkleMarker = np.array(
                    [
                        RightMedialAnkleMarkerX[FrameNumber],
                        RightMedialAnkleMarkerY[FrameNumber],
                        RightMedialAnkleMarkerZ[FrameNumber],
                    ]
                )
                RightHeelMarker = np.array(
                    [
                        RightHeelMarkerX[FrameNumber],
                        RightHeelMarkerY[FrameNumber],
                        RightHeelMarkerZ[FrameNumber],
                    ]
                )

                if self.valueKneeAlignmentCheck == "0":
                    LeftLateralKADMarker = np.array(
                        [
                            LeftLateralKADMarkerX[FrameNumber],
                            LeftLateralKADMarkerY[FrameNumber],
                            LeftLateralKADMarkerZ[FrameNumber],
                        ]
                    )
                    LeftUpperKADMarker = np.array(
                        [
                            LeftUpperKADMarkerX[FrameNumber],
                            LeftUpperKADMarkerY[FrameNumber],
                            LeftUpperKADMarkerZ[FrameNumber],
                        ]
                    )
                    LeftLowerKADMarker = np.array(
                        [
                            LeftLowerKADMarkerX[FrameNumber],
                            LeftLowerKADMarkerY[FrameNumber],
                            LeftLowerKADMarkerZ[FrameNumber],
                        ]
                    )

                    RightLateralKADMarker = np.array(
                        [
                            RightLateralKADMarkerX[FrameNumber],
                            RightLateralKADMarkerY[FrameNumber],
                            RightLateralKADMarkerZ[FrameNumber],
                        ]
                    )
                    RightUpperKADMarker = np.array(
                        [
                            RightUpperKADMarkerX[FrameNumber],
                            RightUpperKADMarkerY[FrameNumber],
                            RightUpperKADMarkerZ[FrameNumber],
                        ]
                    )
                    RightLowerKADMarker = np.array(
                        [
                            RightLowerKADMarkerX[FrameNumber],
                            RightLowerKADMarkerY[FrameNumber],
                            RightLowerKADMarkerZ[FrameNumber],
                        ]
                    )
                else:
                    LeftLateralKneeMarker = np.array(
                        [
                            LeftLateralKneeMarkerX[FrameNumber],
                            LeftLateralKneeMarkerY[FrameNumber],
                            LeftLateralKneeMarkerZ[FrameNumber],
                        ]
                    )
                    LeftMedialKneeMarker = np.array(
                        [
                            LeftMedialKneeMarkerX[FrameNumber],
                            LeftMedialKneeMarkerY[FrameNumber],
                            LeftMedialKneeMarkerZ[FrameNumber],
                        ]
                    )

                    RightLateralKneeMarker = np.array(
                        [
                            RightLateralKneeMarkerX[FrameNumber],
                            RightLateralKneeMarkerY[FrameNumber],
                            RightLateralKneeMarkerZ[FrameNumber],
                        ]
                    )
                    RightMedialKneeMarker = np.array(
                        [
                            RightMedialKneeMarkerX[FrameNumber],
                            RightMedialKneeMarkerY[FrameNumber],
                            RightMedialKneeMarkerZ[FrameNumber],
                        ]
                    )

                # Compute Technical Coordinate System: Pelvis
                [EPelvisTech, MidASISLab] = gait.TechCS_Pelvis_Newington(
                    LeftASISMarker, RightASISMarker, SacralMarker
                )
                # Compute Anatomical Coordinate System: Pelvis
                EPelvisAnat = math.TransformAnatCoorSysFromTechCoors(
                    self.valueEPelvisAnatRelTech, EPelvisTech
                )

                # Normalize HipModelName
                _hip_name = str(getattr(self, "HipModelName", "Harrington2")).strip()
                if "harrington2" in _hip_name.lower():
                    self.HipModelName = "Harrington2"
                elif "harrington" in _hip_name.lower():
                    self.HipModelName = "Harrington"
                elif "newington" in _hip_name.lower() or "davis" in _hip_name.lower():
                    self.HipModelName = "Newington"
                else:
                    self.HipModelName = "Harrington2"

                # Compute Hip Center Location, relative to midASIS point and expressed relative to pelvic coor system
                if self.HipModelName == "Newington":
                    # Newington
                    [LeftHipCenterPelvis, LeftHipCenterLab] = (
                        gait.JointCenterModel_Hip_Newington(
                            "Left",
                            self.MarkerDiameter,
                            self.valueASISdist,
                            self.valueLeftASIStoGTdist,
                            self.valueLeftLegLength,
                            self.valueRightLegLength,
                            RightASISMarker,
                            LeftASISMarker,
                            EPelvisTech,
                            MidASISLab,
                        )
                    )
                    [RightHipCenterPelvis, RightHipCenterLab] = (
                        gait.JointCenterModel_Hip_Newington(
                            "Right",
                            self.MarkerDiameter,
                            self.valueASISdist,
                            self.valueRightASIStoGTdist,
                            self.valueLeftLegLength,
                            self.valueRightLegLength,
                            RightASISMarker,
                            LeftASISMarker,
                            EPelvisTech,
                            MidASISLab,
                        )
                    )
                if self.HipModelName == "Harrington":
                    # Harrington Hip Model
                    [LeftHipCenterPelvis, LeftHipCenterLab] = (
                        gait.JointCenterModel_Hip_Harrington(
                            "Left",
                            self.valueASISdist,
                            RightASISMarker,
                            LeftASISMarker,
                            SacralMarker,
                            EPelvisTech,
                            MidASISLab,
                        )
                    )
                    [RightHipCenterPelvis, RightHipCenterLab] = (
                        gait.JointCenterModel_Hip_Harrington(
                            "Right",
                            self.valueASISdist,
                            RightASISMarker,
                            LeftASISMarker,
                            SacralMarker,
                            EPelvisTech,
                            MidASISLab,
                        )
                    )
                if self.HipModelName == "Harrington2":
                    # Harrington Hip Model- 2 variable
                    [LeftHipCenterPelvis, LeftHipCenterLab] = (
                        gait.JointCenterModel_Hip_Harrington2(
                            "Left",
                            self.valueASISdist,
                            self.valueLeftLegLength,
                            self.valueRightLegLength,
                            RightASISMarker,
                            LeftASISMarker,
                            SacralMarker,
                            EPelvisTech,
                            MidASISLab,
                        )
                    )
                    [RightHipCenterPelvis, RightHipCenterLab] = (
                        gait.JointCenterModel_Hip_Harrington2(
                            "Right",
                            self.valueASISdist,
                            self.valueLeftLegLength,
                            self.valueRightLegLength,
                            RightASISMarker,
                            LeftASISMarker,
                            SacralMarker,
                            EPelvisTech,
                            MidASISLab,
                        )
                    )

                if self.valueKneeAlignmentCheck == "0":
                    # Compute Location of Virtual Knee Marker (based on cluster-type knee fixture)
                    LeftVirtualKneeMarkerLab = gait.ComputeVirtualKneeMarker_Newington(
                        "Left",
                        self.MarkerDiameter,
                        LeftUpperKADMarker,
                        LeftLateralKADMarker,
                        LeftLowerKADMarker,
                    )
                    RightVirtualKneeMarkerLab = gait.ComputeVirtualKneeMarker_Newington(
                        "Right",
                        self.MarkerDiameter,
                        RightUpperKADMarker,
                        RightLateralKADMarker,
                        RightLowerKADMarker,
                    )
                    # print(LeftVirtualKneeMarkerLab)
                    # print(RightVirtualKneeMarkerLab)

                    LeftLateralKneeMarker = LeftVirtualKneeMarkerLab
                    RightLateralKneeMarker = RightVirtualKneeMarkerLab
                else:
                    LeftVirtualKneeMarkerLab = LeftLateralKneeMarker
                    RightVirtualKneeMarkerLab = RightLateralKneeMarker

                # Compute Technical Coordinate System: Thigh
                LeftEThighTech = gait.TechCS_Thigh_Newington(
                    "Left", LeftHipCenterLab, LeftThighMarker, LeftLateralKneeMarker
                )
                RightEThighTech = gait.TechCS_Thigh_Newington(
                    "Right", RightHipCenterLab, RightThighMarker, RightLateralKneeMarker
                )
                # Compute Anatomical Coordinate System: Thigh
                LeftEThighAnat = math.TransformAnatCoorSysFromTechCoors(
                    self.valueLeftEThighAnatRelTech, LeftEThighTech
                )
                RightEThighAnat = math.TransformAnatCoorSysFromTechCoors(
                    self.valueRightEThighAnatRelTech, RightEThighTech
                )

                # Compute Location of Knee Center (in lab space, based on thigh anatomical frame)
                LeftKneeCenterLab = math.TransformPointIntoLabCoors(
                    self.valueLeftKneeCenterThigh, LeftEThighTech, LeftLateralKneeMarker
                )
                RightKneeCenterLab = math.TransformPointIntoLabCoors(
                    self.valueRightKneeCenterThigh,
                    RightEThighTech,
                    RightLateralKneeMarker,
                )

                # Compute Technical Coordinate System: Shank
                if LeftTibialTriadCheck is True:
                    LeftEShankTech = gait.TechCS_Shank_Newington(
                        "Left",
                        LeftTibialUpperMarker,
                        LeftTibialLowerMarker,
                        LeftTibialMarker,
                    )
                else:
                    LeftEShankTech = gait.TechCS_Shank_Newington(
                        "Left",
                        LeftKneeCenterLab,
                        LeftTibialMarker,
                        LeftLateralAnkleMarker,
                    )
                if RightTibialTriadCheck is True:
                    RightEShankTech = gait.TechCS_Shank_Newington(
                        "Right",
                        RightTibialUpperMarker,
                        RightTibialLowerMarker,
                        RightTibialMarker,
                    )
                else:
                    RightEShankTech = gait.TechCS_Shank_Newington(
                        "Right",
                        RightKneeCenterLab,
                        RightTibialMarker,
                        RightLateralAnkleMarker,
                    )

                # Compute anklejoint centers
                if LeftTibialTriadCheck is True:
                    LeftAnkleCenterLab = math.TransformPointIntoLabCoors(
                        self.valueLeftAnkleCenterShank, LeftEShankTech, LeftTibialMarker
                    )
                else:
                    LeftAnkleCenterLab = math.TransformPointIntoLabCoors(
                        self.valueLeftAnkleCenterShank,
                        LeftEShankTech,
                        LeftLateralAnkleMarker,
                    )
                if RightTibialTriadCheck is True:
                    RightAnkleCenterLab = math.TransformPointIntoLabCoors(
                        self.valueRightAnkleCenterShank,
                        RightEShankTech,
                        RightTibialMarker,
                    )
                else:
                    RightAnkleCenterLab = math.TransformPointIntoLabCoors(
                        self.valueRightAnkleCenterShank,
                        RightEShankTech,
                        RightLateralAnkleMarker,
                    )
                # print FrameNumber, LeftAnkleCenterLab

                # If Medial ankle is available,then recompute ankle joint center
                if LeftMedialAnkleMarkerDropOff == 0:
                    LeftAnkleCenterLab = gait.JointCenterModel_Ankle_Newington(
                        "Left",
                        self.MarkerDiameter,
                        self.valueLeftAnkleWidth,
                        LeftLateralAnkleMarker,
                        LeftMedialAnkleMarker,
                    )
                if RightMedialAnkleMarkerDropOff == 0:
                    RightAnkleCenterLab = gait.JointCenterModel_Ankle_Newington(
                        "Right",
                        self.MarkerDiameter,
                        self.valueRightAnkleWidth,
                        RightLateralAnkleMarker,
                        RightMedialAnkleMarker,
                    )
                # print FrameNumber, LeftAnkleCenterLab

                # Fill Arrays to write Joint Centers to C3D File
                arrayLeftHipCenter[0][FrameNumber] = LeftHipCenterLab[0]
                arrayLeftHipCenter[1][FrameNumber] = LeftHipCenterLab[1]
                arrayLeftHipCenter[2][FrameNumber] = LeftHipCenterLab[2]

                arrayRightHipCenter[0][FrameNumber] = RightHipCenterLab[0]
                arrayRightHipCenter[1][FrameNumber] = RightHipCenterLab[1]
                arrayRightHipCenter[2][FrameNumber] = RightHipCenterLab[2]

                arrayLeftKneeCenter[0][FrameNumber] = LeftKneeCenterLab[0]
                arrayLeftKneeCenter[1][FrameNumber] = LeftKneeCenterLab[1]
                arrayLeftKneeCenter[2][FrameNumber] = LeftKneeCenterLab[2]

                arrayRightKneeCenter[0][FrameNumber] = RightKneeCenterLab[0]
                arrayRightKneeCenter[1][FrameNumber] = RightKneeCenterLab[1]
                arrayRightKneeCenter[2][FrameNumber] = RightKneeCenterLab[2]

                arrayLeftVirtualKneeMarker[0][FrameNumber] = LeftVirtualKneeMarkerLab[0]
                arrayLeftVirtualKneeMarker[1][FrameNumber] = LeftVirtualKneeMarkerLab[1]
                arrayLeftVirtualKneeMarker[2][FrameNumber] = LeftVirtualKneeMarkerLab[2]

                arrayLeftLateralKneeMarkerX[FrameNumber] = arrayLeftVirtualKneeMarker[
                    0
                ][FrameNumber]
                arrayLeftLateralKneeMarkerY[FrameNumber] = arrayLeftVirtualKneeMarker[
                    1
                ][FrameNumber]
                arrayLeftLateralKneeMarkerZ[FrameNumber] = arrayLeftVirtualKneeMarker[
                    2
                ][FrameNumber]

                arrayRightVirtualKneeMarker[0][FrameNumber] = RightVirtualKneeMarkerLab[
                    0
                ]
                arrayRightVirtualKneeMarker[1][FrameNumber] = RightVirtualKneeMarkerLab[
                    1
                ]
                arrayRightVirtualKneeMarker[2][FrameNumber] = RightVirtualKneeMarkerLab[
                    2
                ]

                arrayRightLateralKneeMarkerX[FrameNumber] = arrayRightVirtualKneeMarker[
                    0
                ][FrameNumber]
                arrayRightLateralKneeMarkerY[FrameNumber] = arrayRightVirtualKneeMarker[
                    1
                ][FrameNumber]
                arrayRightLateralKneeMarkerZ[FrameNumber] = arrayRightVirtualKneeMarker[
                    2
                ][FrameNumber]

                arrayLeftAnkleCenter[0][FrameNumber] = LeftAnkleCenterLab[0]
                arrayLeftAnkleCenter[1][FrameNumber] = LeftAnkleCenterLab[1]
                arrayLeftAnkleCenter[2][FrameNumber] = LeftAnkleCenterLab[2]

                arrayRightAnkleCenter[0][FrameNumber] = RightAnkleCenterLab[0]
                arrayRightAnkleCenter[1][FrameNumber] = RightAnkleCenterLab[1]
                arrayRightAnkleCenter[2][FrameNumber] = RightAnkleCenterLab[2]

            # =============================================================================
            #         Write Kinematics Outputs to C3D File
            # =============================================================================
            ModelOutputs = fields["Points"]
            if not "LHJC" in ModelOutputs:
                CreateModeledMarker("LHJC")

            if not "RHJC" in ModelOutputs:
                CreateModeledMarker("RHJC")
            if not "LKJC" in ModelOutputs:
                CreateModeledMarker("LKJC")
            if not "RKJC" in ModelOutputs:
                CreateModeledMarker("RKJC")
            if not "LAJC" in ModelOutputs:
                CreateModeledMarker("LAJC")
            if not "RAJC" in ModelOutputs:
                CreateModeledMarker("RAJC")
            if not "LKNE" in ModelOutputs:
                CreateModeledMarker("LKNE")
            if not "RKNE" in ModelOutputs:
                CreateModeledMarker("RKNE")
            #            if not 'LKneeVirtual' in ModelOutputs:
            #                vicon.CreateModeledMarker( SubjectName, 'LKneeVirtual' )
            #            if not 'RKneeVirtual' in ModelOutputs:
            #                vicon.CreateModeledMarker( SubjectName, 'RKneeVirtual' )

            # Write Arrays to C3D Files
            # Joint Centers
            SetTrajectory(
                "LHJC",
                arrayLeftHipCenter[0],
                arrayLeftHipCenter[1],
                arrayLeftHipCenter[2],
                exists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )
            SetTrajectory(
                "RHJC",
                arrayRightHipCenter[0],
                arrayRightHipCenter[1],
                arrayRightHipCenter[2],
                exists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )
            SetTrajectory(
                "LKJC",
                arrayLeftKneeCenter[0],
                arrayLeftKneeCenter[1],
                arrayLeftKneeCenter[2],
                exists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )
            SetTrajectory(
                "RKJC",
                arrayRightKneeCenter[0],
                arrayRightKneeCenter[1],
                arrayRightKneeCenter[2],
                exists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )
            SetTrajectory(
                "LAJC",
                arrayLeftAnkleCenter[0],
                arrayLeftAnkleCenter[1],
                arrayLeftAnkleCenter[2],
                exists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )
            SetTrajectory(
                "RAJC",
                arrayRightAnkleCenter[0],
                arrayRightAnkleCenter[1],
                arrayRightAnkleCenter[2],
                exists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )
            SetTrajectory(
                "LKNE",
                arrayLeftVirtualKneeMarker[0],
                arrayLeftVirtualKneeMarker[1],
                arrayLeftVirtualKneeMarker[2],
                exists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )
            SetTrajectory(
                "RKNE",
                arrayRightVirtualKneeMarker[0],
                arrayRightVirtualKneeMarker[1],
                arrayRightVirtualKneeMarker[2],
                exists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )
            # vicon.SetModelOutput(SubjectName, 'LKneeVirtual', arrayLeftVirtualKneeMarker,  exists )
            # vicon.SetModelOutput(SubjectName, 'RKneeVirtual', arrayRightVirtualKneeMarker, exists )

            # vicon.SetTrajectory(SubjectName, self.LeftLateralKneeMarkerName, arrayLeftLateralKneeMarkerX, arrayLeftLateralKneeMarkerY, arrayLeftLateralKneeMarkerZ, exists )
            # vicon.SetTrajectory(SubjectName, self.RightLateralKneeMarkerName, arrayRightLateralKneeMarkerX, arrayRightLateralKneeMarkerY, arrayRightLateralKneeMarkerZ, exists )

        self.saveTransformationMatrices = saveTransformationMatrices
        self.saveResultsinC3D = saveResultsinC3D

        def savePdf():
            FilePath, FileName = fields["Path"], fields["Filename"]
            InitialPath = FilePath

            InitialFileName = (
                "Static "
                + TestingCondition
                + " "
                + self.valuePatientNumber[:7]
                + " "
                + self.valueDataCollectionDate_Year
                + self.valueDataCollectionDate_Month
                + self.valueDataCollectionDate_Day
                + ".pdf"
            )
            StaticResultsFilename, _ = QFileDialog.getSaveFileName(
                None,
                "Select Static Results File Location",
                str(InitialPath / InitialFileName),
                "PDF Files (*.pdf);;All Files (*.*)",
            )

            # Prepare Results Page pdf
            StaticResultsPage = canvas.Canvas(StaticResultsFilename, pagesize=letter)
            PageWidth, PageHeight = letter
            # Origin at Bottom Left
            # PageWidth = 612, PageHeight = 792
            HeightMargin = 56
            WidthMargin = 81
            DrawRegionHeight = PageHeight - 2 * HeightMargin
            DrawRegionWidth = PageWidth - 2 * WidthMargin

            # Page Title
            StaticResultsPage.setFillColor(reportlabColors.lightgrey)
            StaticResultsPage.rect(
                WidthMargin,
                HeightMargin + DrawRegionHeight,
                DrawRegionWidth,
                -30,
                stroke=0,
                fill=1,
            )
            StaticResultsPage.setFont("Times-Bold", 12)
            StaticResultsPage.setFillGray(0.0)
            StaticResultsPage.drawCentredString(
                PageWidth / 2,
                PageHeight - HeightMargin - 12,
                "Shriners Hospital for Children",
            )
            StaticResultsPage.drawCentredString(
                PageWidth / 2, PageHeight - HeightMargin - 25, "Motion Analysis Center"
            )
            StaticResultsPage.drawCentredString(
                PageWidth / 2, PageHeight - HeightMargin - 50, "-Static Report-"
            )

            # Static Settings
            StaticResultsPage.setFont("Times-Roman", 11)
            VerticalOffsetFromTitle = 70
            LineSpacing = 15
            ColumnSpacing = 120
            StaticResultsPage.drawString(
                WidthMargin,
                PageHeight - HeightMargin - VerticalOffsetFromTitle,
                "Static File:",
            )
            StaticResultsPage.drawString(
                WidthMargin + ColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle,
                FileName + ".c3d",
            )

            StaticResultsPage.drawString(
                WidthMargin,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 1 * LineSpacing,
                "Data Collection Date:",
            )
            StaticResultsPage.drawString(
                WidthMargin + ColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 1 * LineSpacing,
                self.valueDataCollectionDate_Day
                + "-"
                + self.valueDataCollectionDate_Month
                + "-"
                + self.valueDataCollectionDate_Year,
            )

            StaticResultsPage.drawString(
                WidthMargin,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 2 * LineSpacing,
                "User Preferences File:",
            )
            StaticResultsPage.drawString(
                WidthMargin + ColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 2 * LineSpacing,
                str(UserPreferencesFileName),
            )

            if self.valueLeftPlantigradeCheck == "1":
                PlantigradeText = "L    "
            if self.valueRightPlantigradeCheck == "1":
                PlantigradeText = "R    "
            if (
                self.valueLeftPlantigradeCheck == "1"
                and self.valueRightPlantigradeCheck == "1"
            ):
                PlantigradeText = "B    "
            if (
                self.valueLeftPlantigradeCheck == "0"
                and self.valueRightPlantigradeCheck == "0"
            ):
                PlantigradeText = "None    "

            StaticResultsPage.drawString(
                WidthMargin,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 3 * LineSpacing,
                "Gait Model:",
            )
            StaticResultsPage.drawString(
                WidthMargin + ColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 3 * LineSpacing,
                "Shriners",
            )
            StaticResultsPage.drawString(
                WidthMargin + 2 * ColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 3 * LineSpacing,
                "DataFrameUsed: " + str(self.valueStaticFrameNumber),
            )
            StaticResultsPage.drawString(
                WidthMargin + 3 * ColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 3 * LineSpacing,
                "Plantigrade: " + PlantigradeText,
            )

            StaticResultsPage.drawString(
                WidthMargin,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 4 * LineSpacing,
                "TestingCondition:",
            )
            StaticResultsPage.drawString(
                WidthMargin + ColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 4 * LineSpacing,
                self.valueTrialModifier,
            )
            StaticResultsPage.drawString(
                WidthMargin + 2 * ColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 4 * LineSpacing,
                "AssistiveDevice: " + self.valueAssistiveDevice,
            )

            # Static Posture- Labels
            StaticResultsPage.setFont("Times-Bold", 12)
            StaticResultsPage.setStrokeGray(0.75)
            VerticalOffsetFromTitle = 160
            LabelColumnSpacing = 150
            LeftColumnSpacing = 200
            RightColumnSpacing = 300
            StaticResultsPage.drawString(
                WidthMargin,
                PageHeight - HeightMargin - VerticalOffsetFromTitle,
                "Standing Posture (degrees)",
            )
            StaticResultsPage.drawString(
                WidthMargin + LeftColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle,
                "Left",
            )
            StaticResultsPage.drawString(
                WidthMargin + RightColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle,
                "Right",
            )
            StaticResultsPage.rect(
                WidthMargin - 5,
                PageHeight - HeightMargin - VerticalOffsetFromTitle + 15,
                DrawRegionWidth + 5,
                -(17 * LineSpacing + 5),
                stroke=1,
                fill=0,
            )

            StaticResultsPage.setFont("Times-Roman", 11)
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 1 * LineSpacing,
                "Trunk Obliquity",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 2 * LineSpacing,
                "Trunk Tilt",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 3 * LineSpacing,
                "Trunk Rotation",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 4 * LineSpacing,
                "Pelvic Obliquity",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 5 * LineSpacing,
                "Pelvic Tilt",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 6 * LineSpacing,
                "Pelvic Rotation",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 7 * LineSpacing,
                "Hip Ab/Adduction",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 8 * LineSpacing,
                "Hip Flex/Extension",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 9 * LineSpacing,
                "Hip Int/External Rotation",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 10 * LineSpacing,
                "Knee Varus/Valgus",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 11 * LineSpacing,
                "Knee Flex/Extension",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 12 * LineSpacing,
                "Knee Int/External Rotation",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 13 * LineSpacing,
                "Knee Progression",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 14 * LineSpacing,
                "Ankle Plantar/Dorsiflexion",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 15 * LineSpacing,
                "Foot Int/External Rotation",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 16 * LineSpacing,
                "Foot Progression",
            )

            # Static Posture- Left Values
            if len(str.split(LeftTrunkObliquity.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 1 * LineSpacing,
                    str.split(LeftTrunkObliquity.get())[0],
                )
            if len(str.split(LeftTrunkTilt.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 2 * LineSpacing,
                    str.split(LeftTrunkTilt.get())[0],
                )
            if len(str.split(LeftTrunkRotation.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing,
                    str.split(LeftTrunkRotation.get())[0],
                )
            if len(str.split(LeftPelvisObliquity.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing,
                    str.split(LeftPelvisObliquity.get())[0],
                )
            if len(str.split(LeftPelvisTilt.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 5 * LineSpacing,
                    str.split(LeftPelvisTilt.get())[0],
                )
            if len(str.split(LeftPelvisRotation.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 6 * LineSpacing,
                    str.split(LeftPelvisRotation.get())[0],
                )
            if len(str.split(LeftHipAbAdduction.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 7 * LineSpacing,
                    str.split(LeftHipAbAdduction.get())[0],
                )
            if len(str.split(LeftHipFlexExtension.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 8 * LineSpacing,
                    str.split(LeftHipFlexExtension.get())[0],
                )
            if len(str.split(LeftHipIntExtRotation.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 9 * LineSpacing,
                    str.split(LeftHipIntExtRotation.get())[0],
                )
            if len(str.split(LeftKneeVarusValgus.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 10 * LineSpacing,
                    str.split(LeftKneeVarusValgus.get())[0],
                )
            if len(str.split(LeftKneeFlexExtension.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 11 * LineSpacing,
                    str.split(LeftKneeFlexExtension.get())[0],
                )
            if len(str.split(LeftKneeIntExtRotation.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 12 * LineSpacing,
                    str.split(LeftKneeIntExtRotation.get())[0],
                )
            if len(str.split(LeftKneeProgression.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 13 * LineSpacing,
                    str.split(LeftKneeProgression.get())[0],
                )
            if len(str.split(LeftAnklePlantarDorsiflexion.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 14 * LineSpacing,
                    str.split(LeftAnklePlantarDorsiflexion.get())[0],
                )
            if len(str.split(LeftAnkleIntExtRotation.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 15 * LineSpacing,
                    str.split(LeftAnkleIntExtRotation.get())[0],
                )
            if len(str.split(LeftFootProgression.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 16 * LineSpacing,
                    str.split(LeftFootProgression.get())[0],
                )
            # Static Posture- Left Direction
            if len(str.split(LeftTrunkObliquity.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 1 * LineSpacing,
                    "  " + str.split(LeftTrunkObliquity.get())[1],
                )
            if len(str.split(LeftTrunkTilt.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 2 * LineSpacing,
                    "  " + str.split(LeftTrunkTilt.get())[1],
                )
            if len(str.split(LeftTrunkRotation.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing,
                    "  " + str.split(LeftTrunkRotation.get())[1],
                )
            if len(str.split(LeftPelvisObliquity.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing,
                    "  " + str.split(LeftPelvisObliquity.get())[1],
                )
            if len(str.split(LeftPelvisTilt.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 5 * LineSpacing,
                    "  " + str.split(LeftPelvisTilt.get())[1],
                )
            if len(str.split(LeftPelvisRotation.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 6 * LineSpacing,
                    "  " + str.split(LeftPelvisRotation.get())[1],
                )
            if len(str.split(LeftHipAbAdduction.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 7 * LineSpacing,
                    "  " + str.split(LeftHipAbAdduction.get())[1],
                )
            if len(str.split(LeftHipFlexExtension.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 8 * LineSpacing,
                    "  " + str.split(LeftHipFlexExtension.get())[1],
                )
            if len(str.split(LeftHipIntExtRotation.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 9 * LineSpacing,
                    "  " + str.split(LeftHipIntExtRotation.get())[1],
                )
            if len(str.split(LeftKneeVarusValgus.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 10 * LineSpacing,
                    "  " + str.split(LeftKneeVarusValgus.get())[1],
                )
            if len(str.split(LeftKneeFlexExtension.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 11 * LineSpacing,
                    "  " + str.split(LeftKneeFlexExtension.get())[1],
                )
            if len(str.split(LeftKneeIntExtRotation.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 12 * LineSpacing,
                    "  " + str.split(LeftKneeIntExtRotation.get())[1],
                )
            if len(str.split(LeftKneeProgression.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 13 * LineSpacing,
                    "  " + str.split(LeftKneeProgression.get())[1],
                )
            if len(str.split(LeftAnklePlantarDorsiflexion.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 14 * LineSpacing,
                    "  " + str.split(LeftAnklePlantarDorsiflexion.get())[1],
                )
            if len(str.split(LeftAnkleIntExtRotation.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 15 * LineSpacing,
                    "  " + str.split(LeftAnkleIntExtRotation.get())[1],
                )
            if len(str.split(LeftFootProgression.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 16 * LineSpacing,
                    "  " + str.split(LeftFootProgression.get())[1],
                )

            # Static Posture- Right Values
            if len(str.split(RightTrunkObliquity.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 1 * LineSpacing,
                    str.split(RightTrunkObliquity.get())[0],
                )
            if len(str.split(RightTrunkTilt.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 2 * LineSpacing,
                    str.split(RightTrunkTilt.get())[0],
                )
            if len(str.split(RightTrunkRotation.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing,
                    str.split(RightTrunkRotation.get())[0],
                )
            if len(str.split(RightPelvisObliquity.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing,
                    str.split(RightPelvisObliquity.get())[0],
                )
            if len(str.split(RightPelvisTilt.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 5 * LineSpacing,
                    str.split(RightPelvisTilt.get())[0],
                )
            if len(str.split(RightPelvisRotation.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 6 * LineSpacing,
                    str.split(RightPelvisRotation.get())[0],
                )
            if len(str.split(RightHipAbAdduction.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 7 * LineSpacing,
                    str.split(RightHipAbAdduction.get())[0],
                )
            if len(str.split(RightHipFlexExtension.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 8 * LineSpacing,
                    str.split(RightHipFlexExtension.get())[0],
                )
            if len(str.split(RightHipIntExtRotation.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 9 * LineSpacing,
                    str.split(RightHipIntExtRotation.get())[0],
                )
            if len(str.split(RightKneeVarusValgus.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 10 * LineSpacing,
                    str.split(RightKneeVarusValgus.get())[0],
                )
            if len(str.split(RightKneeFlexExtension.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 11 * LineSpacing,
                    str.split(RightKneeFlexExtension.get())[0],
                )
            if len(str.split(RightKneeIntExtRotation.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 12 * LineSpacing,
                    str.split(RightKneeIntExtRotation.get())[0],
                )
            if len(str.split(RightKneeProgression.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 13 * LineSpacing,
                    str.split(RightKneeProgression.get())[0],
                )
            if len(str.split(RightAnklePlantarDorsiflexion.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 14 * LineSpacing,
                    str.split(RightAnklePlantarDorsiflexion.get())[0],
                )
            if len(str.split(RightAnkleIntExtRotation.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 15 * LineSpacing,
                    str.split(RightAnkleIntExtRotation.get())[0],
                )
            if len(str.split(RightFootProgression.get())) > 0:
                StaticResultsPage.drawRightString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 16 * LineSpacing,
                    str.split(RightFootProgression.get())[0],
                )

            # Static Posture- Right Direction
            if len(str.split(RightTrunkObliquity.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 1 * LineSpacing,
                    "  " + str.split(RightTrunkObliquity.get())[1],
                )
            if len(str.split(RightTrunkTilt.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 2 * LineSpacing,
                    "  " + str.split(RightTrunkTilt.get())[1],
                )
            if len(str.split(RightTrunkRotation.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing,
                    "  " + str.split(RightTrunkRotation.get())[1],
                )
            if len(str.split(RightPelvisObliquity.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing,
                    "  " + str.split(RightPelvisObliquity.get())[1],
                )
            if len(str.split(RightPelvisTilt.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 5 * LineSpacing,
                    "  " + str.split(RightPelvisTilt.get())[1],
                )
            if len(str.split(RightPelvisRotation.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 6 * LineSpacing,
                    "  " + str.split(RightPelvisRotation.get())[1],
                )
            if len(str.split(RightHipAbAdduction.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 7 * LineSpacing,
                    "  " + str.split(RightHipAbAdduction.get())[1],
                )
            if len(str.split(RightHipFlexExtension.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 8 * LineSpacing,
                    "  " + str.split(RightHipFlexExtension.get())[1],
                )
            if len(str.split(RightHipIntExtRotation.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 9 * LineSpacing,
                    "  " + str.split(RightHipIntExtRotation.get())[1],
                )
            if len(str.split(RightKneeVarusValgus.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 10 * LineSpacing,
                    "  " + str.split(RightKneeVarusValgus.get())[1],
                )
            if len(str.split(RightKneeFlexExtension.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 11 * LineSpacing,
                    "  " + str.split(RightKneeFlexExtension.get())[1],
                )
            if len(str.split(RightKneeIntExtRotation.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 12 * LineSpacing,
                    "  " + str.split(RightKneeIntExtRotation.get())[1],
                )
            if len(str.split(RightKneeProgression.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 13 * LineSpacing,
                    "  " + str.split(RightKneeProgression.get())[1],
                )
            if len(str.split(RightAnklePlantarDorsiflexion.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 14 * LineSpacing,
                    "  " + str.split(RightAnklePlantarDorsiflexion.get())[1],
                )
            if len(str.split(RightAnkleIntExtRotation.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 15 * LineSpacing,
                    "  " + str.split(RightAnkleIntExtRotation.get())[1],
                )
            if len(str.split(RightFootProgression.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 16 * LineSpacing,
                    "  " + str.split(RightFootProgression.get())[1],
                )

            # Tibial Torsion
            StaticResultsPage.setFont("Times-Bold", 12)
            VerticalOffsetFromTitle = 430
            StaticResultsPage.drawString(
                WidthMargin,
                PageHeight - HeightMargin - VerticalOffsetFromTitle,
                "Tibial Torsion (degrees)",
            )
            StaticResultsPage.rect(
                WidthMargin - 5,
                PageHeight - HeightMargin - VerticalOffsetFromTitle + 15,
                DrawRegionWidth + 5,
                -(1 * LineSpacing + 5),
                stroke=1,
                fill=0,
            )

            StaticResultsPage.setFont("Times-Roman", 11)
            # Left
            StaticResultsPage.drawRightString(
                WidthMargin + LeftColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 0 * LineSpacing,
                str.split(LeftTibiaTorsion.get())[0],
            )
            if len(str.split(LeftTibiaTorsion.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 0 * LineSpacing,
                    "  " + str.split(LeftTibiaTorsion.get())[1],
                )
            # Right
            StaticResultsPage.drawRightString(
                WidthMargin + RightColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 0 * LineSpacing,
                str.split(RightTibiaTorsion.get())[0],
            )
            if len(str.split(RightTibiaTorsion.get())) > 1:
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 0 * LineSpacing,
                    "  " + str.split(RightTibiaTorsion.get())[1],
                )

            # =============================================================================
            #           QA Report Number are recomputed here
            #           These are not available here due to being computed in QA Report class
            # =============================================================================
            if (
                self.HasTrajectory(SubjectName, self.LeftASISMarkerName) is True
                and self.HasTrajectory(SubjectName, self.RightASISMarkerName) is True
            ):
                valueASISdistMarkers = np.linalg.norm(LeftASISMarker - RightASISMarker)

            if (
                self.HasTrajectory(SubjectName, self.LeftLateralKneeMarkerName) is True
                and self.HasTrajectory(SubjectName, self.LeftMedialKneeMarkerName)
                is True
            ):
                valueLeftKneeWidthMarkers = (
                    np.linalg.norm(LeftLateralKneeMarker - LeftMedialKneeMarker)
                    - self.MarkerDiameter
                )

            if (
                self.HasTrajectory(SubjectName, self.RightLateralKneeMarkerName) is True
                and self.HasTrajectory(SubjectName, self.RightMedialKneeMarkerName)
                is True
            ):
                valueRightKneeWidthMarkers = (
                    np.linalg.norm(RightLateralKneeMarker - RightMedialKneeMarker)
                    - self.MarkerDiameter
                )

            if (
                self.HasTrajectory(SubjectName, self.LeftLateralAnkleMarkerName) is True
                and self.HasTrajectory(SubjectName, self.LeftMedialAnkleMarkerName)
                is True
            ):
                valueLeftAnkleWidthMarkers = (
                    np.linalg.norm(LeftLateralAnkleMarker - LeftMedialAnkleMarker)
                    - self.MarkerDiameter
                )

            if (
                self.HasTrajectory(SubjectName, self.RightLateralAnkleMarkerName)
                is True
                and self.HasTrajectory(SubjectName, self.RightMedialAnkleMarkerName)
                is True
            ):
                valueRightAnkleWidthMarkers = (
                    np.linalg.norm(RightLateralAnkleMarker - RightMedialAnkleMarker)
                    - self.MarkerDiameter
                )

            if (
                self.HasTrajectory(SubjectName, self.LeftLateralKADMarkerName) is True
                and self.HasTrajectory(SubjectName, self.LeftUpperKADMarkerName) is True
                and self.HasTrajectory(SubjectName, self.LeftLowerKADMarkerName) is True
            ):
                # Distances
                valueLeftUpperLateral = np.linalg.norm(
                    LeftUpperKADMarker - LeftLateralKADMarker
                )
                valueLeftUpperLower = np.linalg.norm(
                    LeftUpperKADMarker - LeftLowerKADMarker
                )
                valueLeftLateralLower = np.linalg.norm(
                    LeftLateralKADMarker - LeftLowerKADMarker
                )
                valueLeftDistRange = int(
                    round(
                        max(
                            valueLeftUpperLateral,
                            valueLeftUpperLower,
                            valueLeftLateralLower,
                        )
                        - min(
                            valueLeftUpperLateral,
                            valueLeftUpperLower,
                            valueLeftLateralLower,
                        )
                    )
                )
                # Angles
                valueLeftUpperLateralLower = (
                    math.Compute3DAngle(
                        LeftUpperKADMarker, LeftLateralKADMarker, LeftLowerKADMarker
                    )
                    * 180
                    / np.pi
                )
                valueLeftLateralUpperLower = (
                    math.Compute3DAngle(
                        LeftLateralKADMarker, LeftUpperKADMarker, LeftLowerKADMarker
                    )
                    * 180
                    / np.pi
                )
                valueLeftUpperLowerLateral = (
                    math.Compute3DAngle(
                        LeftUpperKADMarker, LeftLowerKADMarker, LeftLateralKADMarker
                    )
                    * 180
                    / np.pi
                )
                valueLeftAngleRange = int(
                    round(
                        max(
                            valueLeftUpperLateralLower,
                            valueLeftLateralUpperLower,
                            valueLeftUpperLowerLateral,
                        )
                        - min(
                            valueLeftUpperLateralLower,
                            valueLeftLateralUpperLower,
                            valueLeftUpperLowerLateral,
                        )
                    )
                )

            if (
                self.HasTrajectory(SubjectName, self.RightLateralKADMarkerName) is True
                and self.HasTrajectory(SubjectName, self.RightUpperKADMarkerName)
                is True
                and self.HasTrajectory(SubjectName, self.RightLowerKADMarkerName)
                is True
            ):
                # Distances
                valueRightUpperLateral = np.linalg.norm(
                    RightUpperKADMarker - RightLateralKADMarker
                )
                valueRightUpperLower = np.linalg.norm(
                    RightUpperKADMarker - RightLowerKADMarker
                )
                valueRightLateralLower = np.linalg.norm(
                    RightLateralKADMarker - RightLowerKADMarker
                )
                valueRightDistRange = int(
                    round(
                        max(
                            valueRightUpperLateral,
                            valueRightUpperLower,
                            valueRightLateralLower,
                        )
                        - min(
                            valueRightUpperLateral,
                            valueRightUpperLower,
                            valueRightLateralLower,
                        )
                    )
                )
                # Angles
                valueRightUpperLateralLower = (
                    math.Compute3DAngle(
                        RightUpperKADMarker, RightLateralKADMarker, RightLowerKADMarker
                    )
                    * 180
                    / np.pi
                )
                valueRightLateralUpperLower = (
                    math.Compute3DAngle(
                        RightLateralKADMarker, RightUpperKADMarker, RightLowerKADMarker
                    )
                    * 180
                    / np.pi
                )
                valueRightUpperLowerLateral = (
                    math.Compute3DAngle(
                        RightUpperKADMarker, RightLowerKADMarker, RightLateralKADMarker
                    )
                    * 180
                    / np.pi
                )
                valueRightAngleRange = int(
                    round(
                        max(
                            valueRightUpperLateralLower,
                            valueRightLateralUpperLower,
                            valueRightUpperLowerLateral,
                        )
                        - min(
                            valueRightUpperLateralLower,
                            valueRightLateralUpperLower,
                            valueRightUpperLowerLateral,
                        )
                    )
                )
            # =============================================================================

            # QA Report- Clinical vs. Marker
            StaticResultsPage.setFont("Times-Bold", 12)
            VerticalOffsetFromTitle = 460
            LabelColumnSpacing = 150
            LeftColumnSpacing = 200
            RightColumnSpacing = 300
            DifferenceColumnSpacing = 400
            StaticResultsPage.drawString(
                WidthMargin,
                PageHeight - HeightMargin - VerticalOffsetFromTitle,
                "Comparison of Clinical Exam - Marker Data",
            )
            if self.valueKneeAlignmentCheck == "0":
                StaticResultsPage.rect(
                    WidthMargin - 5,
                    PageHeight - HeightMargin - VerticalOffsetFromTitle + 15,
                    DrawRegionWidth + 5,
                    -(5 * LineSpacing + 5),
                    stroke=1,
                    fill=0,
                )
            if self.valueKneeAlignmentCheck == "1":
                StaticResultsPage.rect(
                    WidthMargin - 5,
                    PageHeight - HeightMargin - VerticalOffsetFromTitle + 15,
                    DrawRegionWidth + 5,
                    -(7 * LineSpacing + 5),
                    stroke=1,
                    fill=0,
                )

            StaticResultsPage.setFont("Times-Roman", 11)
            StaticResultsPage.drawCentredString(
                WidthMargin + LeftColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 1 * LineSpacing,
                "Clinical Exam",
            )
            StaticResultsPage.drawCentredString(
                WidthMargin + RightColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 1 * LineSpacing,
                "Markers",
            )
            StaticResultsPage.drawCentredString(
                WidthMargin + DifferenceColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 1 * LineSpacing,
                "Diffrence",
            )
            StaticResultsPage.drawRightString(
                WidthMargin + LabelColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 2 * LineSpacing,
                "ASIS-to-ASIS Distance (m)",
            )
            if self.valueKneeAlignmentCheck == "0":
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing,
                    "Ankle Width (m)- Left",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing,
                    "Ankle Width (m)- Right",
                )
            if self.valueKneeAlignmentCheck == "1":
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing,
                    "Knee Width (m)- Left",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing,
                    "Knee Width (m)- Right",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 5 * LineSpacing,
                    "Ankle Width (m)- Left",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 6 * LineSpacing,
                    "Ankle Width (m)- Right",
                )

            # Values
            StaticResultsPage.drawCentredString(
                WidthMargin + LeftColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 2 * LineSpacing,
                display_measurement_meters(self.valueASISdist),
            )
            StaticResultsPage.drawCentredString(
                WidthMargin + RightColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 2 * LineSpacing,
                display_measurement_meters(valueASISdistMarkers),
            )
            StaticResultsPage.drawCentredString(
                WidthMargin + DifferenceColumnSpacing,
                PageHeight - HeightMargin - VerticalOffsetFromTitle - 2 * LineSpacing,
                display_measurement_meters(abs(valueASISdistMarkers - self.valueASISdist)),
            )

            if self.valueKneeAlignmentCheck == "0":
                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing,
                    display_measurement_meters(self.valueLeftAnkleWidth),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing,
                    display_measurement_meters(valueLeftAnkleWidthMarkers),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + DifferenceColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing,
                    str(
                        int(
                            round(
                                abs(
                                    valueLeftAnkleWidthMarkers
                                    - self.valueLeftAnkleWidth
                                )
                            )
                        )
                    ),
                )

                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing,
                    display_measurement_meters(self.valueRightAnkleWidth),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing,
                    display_measurement_meters(valueRightAnkleWidthMarkers),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + DifferenceColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing,
                    str(
                        int(
                            round(
                                abs(
                                    valueRightAnkleWidthMarkers
                                    - self.valueRightAnkleWidth
                                )
                            )
                        )
                    ),
                )
            if self.valueKneeAlignmentCheck == "1":
                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing,
                    display_measurement_meters(self.valueLeftKneeWidth),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing,
                    display_measurement_meters(valueLeftKneeWidthMarkers),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + DifferenceColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing,
                    str(
                        int(
                            round(
                                abs(valueLeftKneeWidthMarkers - self.valueLeftKneeWidth)
                            )
                        )
                    ),
                )

                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing,
                    display_measurement_meters(self.valueRightKneeWidth),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing,
                    display_measurement_meters(valueRightKneeWidthMarkers),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + DifferenceColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing,
                    str(
                        int(
                            round(
                                abs(
                                    valueRightKneeWidthMarkers
                                    - self.valueRightKneeWidth
                                )
                            )
                        )
                    ),
                )

                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 5 * LineSpacing,
                    str(self.valueLeftAnkleWidth),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 5 * LineSpacing,
                    str(int(round(valueLeftAnkleWidthMarkers))),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + DifferenceColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 5 * LineSpacing,
                    str(
                        int(
                            round(
                                abs(
                                    valueLeftAnkleWidthMarkers
                                    - self.valueLeftAnkleWidth
                                )
                            )
                        )
                    ),
                )

                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 6 * LineSpacing,
                    str(self.valueRightAnkleWidth),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 6 * LineSpacing,
                    str(int(round(valueRightAnkleWidthMarkers))),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + DifferenceColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 6 * LineSpacing,
                    str(
                        int(
                            round(
                                abs(
                                    valueRightAnkleWidthMarkers
                                    - self.valueRightAnkleWidth
                                )
                            )
                        )
                    ),
                )

            if self.valueKneeAlignmentCheck == "0":
                # QA Report- KAD Marker Data
                StaticResultsPage.setFont("Times-Bold", 12)
                VerticalOffsetFromTitle = 550
                LabelColumnSpacing = 150
                LeftColumnSpacing = 200
                LeftRangeColumnSpacing = 275
                RightColumnSpacing = 350
                RightRangeColumnSpacing = 425

                # Labels
                StaticResultsPage.drawString(
                    WidthMargin,
                    PageHeight - HeightMargin - VerticalOffsetFromTitle,
                    "Knee Alignment Fixture Marker Data",
                )
                StaticResultsPage.drawString(
                    WidthMargin,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 1 * LineSpacing
                    - 5,
                    "Inter Marker Distance (mm)",
                )
                StaticResultsPage.drawString(
                    WidthMargin,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 5 * LineSpacing
                    - 2 * 5,
                    "Inter Marker Angles (degrees)",
                )
                StaticResultsPage.rect(
                    WidthMargin - 5,
                    PageHeight - HeightMargin - VerticalOffsetFromTitle + 15,
                    DrawRegionWidth + 5,
                    -(9 * LineSpacing + 5 + 2 * 5),
                    stroke=1,
                    fill=0,
                )

                StaticResultsPage.setFont("Times-Roman", 11)
                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 1 * LineSpacing,
                    "Left",
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftRangeColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 1 * LineSpacing,
                    "Range",
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 1 * LineSpacing,
                    "Right",
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightRangeColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 1 * LineSpacing,
                    "Range",
                )

                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 2 * LineSpacing
                    - 5,
                    "Upper & Lateral Marker",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing
                    - 5,
                    "Upper & Lower Marker",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing
                    - 5,
                    "Lower & Lateral Marker",
                )

                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 6 * LineSpacing
                    - 2 * 5,
                    "Upper-Lateral-Lower",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 7 * LineSpacing
                    - 2 * 5,
                    "Lateral-Upper-Lower",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 8 * LineSpacing
                    - 2 * 5,
                    "Upper-Lower-Lateral",
                )

                # Values- Left
                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 2 * LineSpacing
                    - 5,
                    str(int(round(valueLeftUpperLateral))),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing
                    - 5,
                    str(int(round(valueLeftUpperLower))),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing
                    - 5,
                    str(int(round(valueLeftLateralLower))),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftRangeColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing
                    - 5,
                    str(valueLeftDistRange),
                )

                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 6 * LineSpacing
                    - 2 * 5,
                    str(int(round(valueLeftUpperLateralLower))),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 7 * LineSpacing
                    - 2 * 5,
                    str(int(round(valueLeftLateralUpperLower))),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 8 * LineSpacing
                    - 2 * 5,
                    str(int(round(valueLeftUpperLowerLateral))),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + LeftRangeColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 7 * LineSpacing
                    - 2 * 5,
                    str(valueLeftAngleRange),
                )

                # Values- Right
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 2 * LineSpacing
                    - 5,
                    str(int(round(valueRightUpperLateral))),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing
                    - 5,
                    str(int(round(valueRightUpperLower))),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing
                    - 5,
                    str(int(round(valueRightLateralLower))),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightRangeColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing
                    - 5,
                    str(valueRightDistRange),
                )

                StaticResultsPage.drawCentredString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 6 * LineSpacing
                    - 2 * 5,
                    str(int(round(valueRightUpperLateralLower))),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 7 * LineSpacing
                    - 2 * 5,
                    str(int(round(valueRightLateralUpperLower))),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 8 * LineSpacing
                    - 2 * 5,
                    str(int(round(valueRightUpperLowerLateral))),
                )
                StaticResultsPage.drawCentredString(
                    WidthMargin + RightRangeColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 7 * LineSpacing
                    - 2 * 5,
                    str(valueRightAngleRange),
                )

            StaticResultsPage.showPage()  # Finishes the Current Page

            if (
                self.valueLeftFootModelCheck == "1"
                or self.valueRightFootModelCheck == "1"
            ):
                # Add Foot Static Posture if Foot Model was used
                # Page Title
                StaticResultsPage.setFillColor(reportlabColors.lightgrey)
                StaticResultsPage.rect(
                    WidthMargin,
                    HeightMargin + DrawRegionHeight,
                    DrawRegionWidth,
                    -30,
                    stroke=0,
                    fill=1,
                )
                StaticResultsPage.setFont("Times-Bold", 12)
                StaticResultsPage.setFillGray(0.0)
                StaticResultsPage.drawCentredString(
                    PageWidth / 2,
                    PageHeight - HeightMargin - 12,
                    "Shriners Hospital for Children- Greenville, SC",
                )
                StaticResultsPage.drawCentredString(
                    PageWidth / 2,
                    PageHeight - HeightMargin - 25,
                    "Motion Analysis Center",
                )
                StaticResultsPage.drawCentredString(
                    PageWidth / 2, PageHeight - HeightMargin - 50, "-Static Report-"
                )

                # Static Posture- Labels
                StaticResultsPage.setFont("Times-Bold", 12)
                StaticResultsPage.setStrokeGray(0.75)
                VerticalOffsetFromTitle = 80
                LabelColumnSpacing = 150
                LeftColumnSpacing = 200
                RightColumnSpacing = 300
                StaticResultsPage.drawString(
                    WidthMargin,
                    PageHeight - HeightMargin - VerticalOffsetFromTitle,
                    "Foot Posture (degrees)",
                )
                StaticResultsPage.drawString(
                    WidthMargin + LeftColumnSpacing,
                    PageHeight - HeightMargin - VerticalOffsetFromTitle,
                    "Left",
                )
                StaticResultsPage.drawString(
                    WidthMargin + RightColumnSpacing,
                    PageHeight - HeightMargin - VerticalOffsetFromTitle,
                    "Right",
                )
                StaticResultsPage.rect(
                    WidthMargin - 5,
                    PageHeight - HeightMargin - VerticalOffsetFromTitle + 15,
                    DrawRegionWidth + 5,
                    -(9 * LineSpacing + 5),
                    stroke=1,
                    fill=0,
                )

                StaticResultsPage.setFont("Times-Roman", 11)
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 1 * LineSpacing,
                    "Hindfoot Pitch",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 2 * LineSpacing,
                    "Hindfoot Progression",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 3 * LineSpacing,
                    "Hindfoot Varus/Valgus",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 4 * LineSpacing,
                    "Ankle Complex Varus/Valgus",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 5 * LineSpacing,
                    "Forefoot Pitch",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 6 * LineSpacing,
                    "Forefoot Progression",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 7 * LineSpacing,
                    "Midfoot Complex Ab/Adduction",
                )
                StaticResultsPage.drawRightString(
                    WidthMargin + LabelColumnSpacing,
                    PageHeight
                    - HeightMargin
                    - VerticalOffsetFromTitle
                    - 8 * LineSpacing,
                    "MTP1 Varus/Valgus",
                )

                # Static Posture- Left Values
                if len(str.split(LeftHindfootPitch.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 1 * LineSpacing,
                        str.split(LeftHindfootPitch.get())[0],
                    )
                if len(str.split(LeftHindfootProgression.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 2 * LineSpacing,
                        str.split(LeftHindfootProgression.get())[0],
                    )
                if len(str.split(LeftHindfootInvEversion.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 3 * LineSpacing,
                        str.split(LeftHindfootInvEversion.get())[0],
                    )
                if len(str.split(LeftAnkleComplexInvEversion.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 4 * LineSpacing,
                        str.split(LeftAnkleComplexInvEversion.get())[0],
                    )
                if len(str.split(LeftForefootPitch.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 5 * LineSpacing,
                        str.split(LeftForefootPitch.get())[0],
                    )
                if len(str.split(LeftForefootProgression.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 6 * LineSpacing,
                        str.split(LeftForefootProgression.get())[0],
                    )
                if len(str.split(LeftMidfootAbAdduction.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 7 * LineSpacing,
                        str.split(LeftMidfootAbAdduction.get())[0],
                    )
                if len(str.split(LeftHalluxProgression.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 8 * LineSpacing,
                        str.split(LeftHalluxProgression.get())[0],
                    )

                # Static Posture- Left Direction
                if len(str.split(LeftHindfootPitch.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 1 * LineSpacing,
                        "  " + str.split(LeftHindfootPitch.get())[1],
                    )
                if len(str.split(LeftHindfootProgression.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 2 * LineSpacing,
                        "  " + str.split(LeftHindfootProgression.get())[1],
                    )
                if len(str.split(LeftHindfootInvEversion.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 3 * LineSpacing,
                        "  " + str.split(LeftHindfootInvEversion.get())[1],
                    )
                if len(str.split(LeftAnkleComplexInvEversion.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 4 * LineSpacing,
                        "  " + str.split(LeftAnkleComplexInvEversion.get())[1],
                    )
                if len(str.split(LeftForefootPitch.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 5 * LineSpacing,
                        "  " + str.split(LeftForefootPitch.get())[1],
                    )
                if len(str.split(LeftForefootProgression.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 6 * LineSpacing,
                        "  " + str.split(LeftForefootProgression.get())[1],
                    )
                if len(str.split(LeftMidfootAbAdduction.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 7 * LineSpacing,
                        "  " + str.split(LeftMidfootAbAdduction.get())[1],
                    )
                if len(str.split(LeftHalluxProgression.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + LeftColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 8 * LineSpacing,
                        "  " + str.split(LeftHalluxProgression.get())[1],
                    )

                # Static Posture- Right Values
                if len(str.split(RightHindfootPitch.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 1 * LineSpacing,
                        str.split(RightHindfootPitch.get())[0],
                    )
                if len(str.split(RightHindfootProgression.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 2 * LineSpacing,
                        str.split(RightHindfootProgression.get())[0],
                    )
                if len(str.split(RightHindfootInvEversion.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 3 * LineSpacing,
                        str.split(RightHindfootInvEversion.get())[0],
                    )
                if len(str.split(RightAnkleComplexInvEversion.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 4 * LineSpacing,
                        str.split(RightAnkleComplexInvEversion.get())[0],
                    )
                if len(str.split(RightForefootPitch.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 5 * LineSpacing,
                        str.split(RightForefootPitch.get())[0],
                    )
                if len(str.split(RightForefootProgression.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 6 * LineSpacing,
                        str.split(RightForefootProgression.get())[0],
                    )
                if len(str.split(RightMidfootAbAdduction.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 7 * LineSpacing,
                        str.split(RightMidfootAbAdduction.get())[0],
                    )
                if len(str.split(RightHalluxProgression.get())) > 0:
                    StaticResultsPage.drawRightString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 8 * LineSpacing,
                        str.split(RightHalluxProgression.get())[0],
                    )

                # Static Posture- Right Direction
                if len(str.split(RightHindfootPitch.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 1 * LineSpacing,
                        "  " + str.split(RightHindfootPitch.get())[1],
                    )
                if len(str.split(RightHindfootProgression.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 2 * LineSpacing,
                        "  " + str.split(RightHindfootProgression.get())[1],
                    )
                if len(str.split(RightHindfootInvEversion.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 3 * LineSpacing,
                        "  " + str.split(RightHindfootInvEversion.get())[1],
                    )
                if len(str.split(RightAnkleComplexInvEversion.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 4 * LineSpacing,
                        "  " + str.split(RightAnkleComplexInvEversion.get())[1],
                    )
                if len(str.split(RightForefootPitch.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 5 * LineSpacing,
                        "  " + str.split(RightForefootPitch.get())[1],
                    )
                if len(str.split(RightForefootProgression.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 6 * LineSpacing,
                        "  " + str.split(RightForefootProgression.get())[1],
                    )
                if len(str.split(RightMidfootAbAdduction.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 7 * LineSpacing,
                        "  " + str.split(RightMidfootAbAdduction.get())[1],
                    )
                if len(str.split(RightHalluxProgression.get())) > 1:
                    StaticResultsPage.drawString(
                        WidthMargin + RightColumnSpacing,
                        PageHeight
                        - HeightMargin
                        - VerticalOffsetFromTitle
                        - 8 * LineSpacing,
                        "  " + str.split(RightHalluxProgression.get())[1],
                    )

                StaticResultsPage.showPage()  # Finishes the Current Page

            try:
                StaticResultsPage.save()
                SaveErrorMessagesLabel.place(x=50, y=930, width=650, height=15)
                SaveErrorMessagesLabel["text"] = "Static Results file saved"
                SaveErrorMessagesLabel["fg"] = "seagreen"
            except Exception as e:
                print(f"Error saving Static Results file: {e}")
                SaveErrorMessagesLabel.place(x=50, y=930, width=650, height=15)
                SaveErrorMessagesLabel["text"] = (
                    "Warning: Results file could not be saved. Close the Pdf file and try again."
                )


# Calls the main Function
app = Static_Main(headless=getattr(args, 'headless', False))
# Centers the App on Monitor
ScreenWidth = app.winfo_screenwidth()
ScreenHeight = app.winfo_screenheight()
x = (ScreenWidth / 2) - (AppWidth / 2)
y = 0  # Put the App at Top of Monitor
app.geometry("%dx%d+%d+%d" % (AppWidth, AppHeight, x, y))
app.resizable(0, 0)

if getattr(args, 'headless', False):
    # ── Headless mode: hide window, auto-process, save results, then exit ──
    app.hide()
    print("[headless] Static Analysis running in headless mode...")
    try:
        # Step 1: Trigger PatientInfo save & navigate to QA report
        patient_page = app.frames[PatientInfo_Page]
        patient_page.build_UI()
        QApplication.processEvents()
        print("[headless] Patient Info page built, triggering save & QA...")

        # Step 2: Build QA report (runs marker checks)
        qa_page = app.frames[QAreport_Page]
        qa_page.build_UI()
        QApplication.processEvents()
        print("[headless] QA Report page built, triggering calibration...")

        # Step 3: Build Calibration Report (runs the actual calibration computation)
        calib_page = app.frames[StaticSubjectCalibrationReport_Page]
        calib_page.build_UI()
        QApplication.processEvents()
        print("[headless] Calibration Report page built, saving results...")
        if hasattr(calib_page, "saveTransformationMatrices"):
            calib_page.saveTransformationMatrices()
            print("[headless] Transformation matrices saved.")
        if hasattr(calib_page, "saveResultsinC3D"):
            try:
                calib_page.saveResultsinC3D()
                print("[headless] C3D results saved.")
            except Exception as ex_c3d:
                print(f"[headless] Notice: saveResultsinC3D: {ex_c3d}")

        print("[headless] Static analysis complete.")
    except Exception as e:
        print(f"[headless] Error during headless processing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        app.close()
        if hasattr(app, '_qapp') and app._qapp:
            app._qapp.quit()
    sys.exit(0)
else:
    grpc_server_thread = threading.Thread(target=run_tkinter_grpc_server, daemon=True)
    grpc_server_thread.start()
    print(
        f"TkinterApp gRPC server thread started. Main thread waiting. Press Ctrl+C to stop."
    )
    app.mainloop()
