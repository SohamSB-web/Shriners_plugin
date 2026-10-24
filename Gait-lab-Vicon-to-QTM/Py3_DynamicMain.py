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
# Dynamic model computes kinematics and kinetics

@author: The13bit (Anas Fodkar)
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""
VersionNumber = "Py3_v1.3"

import os
import sys

if sys.platform == "win32":
    _lib_bin = os.path.join(sys.prefix, "Library", "bin")
    if os.path.isdir(_lib_bin):
        if _lib_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = _lib_bin + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(_lib_bin)
            except Exception:
                pass

import argparse
import numpy as np
from numpy import array, nan
from Py3_varExtractor import extract_fields_by_filename
from gapi import (
    run_tkinter_grpc_server,
    SetTrajectory,
    CreateModeledMarker,
    GetForcePlate,
)
from pathlib import Path
from Py3_Utils import SimModlOutput, ForcePlateGUI
from Py3_CreateGCD import CreateGCD_Main
# import Vicon Nexus Subroutines

vicon = None

# import Common Vector/Matrix Operations Modules
import Py3_MathModules as math
import Py3_GaitModules as gait


# First Argument is the command name, second argument is the testing condition
DefaultTestingCondition = "BF"
TestingCondition = DefaultTestingCondition
parser = argparse.ArgumentParser(description="Process gait analysis data")
parser.add_argument(
    "--TestingCondition",
    "-t",
    default="BF",
    help="Testing condition parameter (default: BF)",
)
parser.add_argument(
    "--sessionPath", "-s", required=True, help="Path to the session directory"
)
parser.add_argument(
    "--filename", "-f", required=True, help="Name of the file to process"
)
parser.add_argument(
    "--leftPlate", default=None, help="Assigned Left Force Plate ID (e.g. FP0 or 0)"
)
parser.add_argument(
    "--rightPlate", default=None, help="Assigned Right Force Plate ID (e.g. FP0 or 0)"
)
parser.add_argument(
    "--interactiveFP", action="store_true", default=False, help="Always show interactive ForcePlateGUI"
)
parser.add_argument("--run-id", default=None, help="Numerical batch artifact identity")
args = parser.parse_args()
# Use the parsed arguments
TestingCondition = args.TestingCondition   #  "BF"
sessionPath = args.sessionPath
filename = args.filename   #  "Dynamic 1.qtm"

import gapi
from app.services.dynamic_write_manifest import trial_output_lock
_output_lock = trial_output_lock(Path(sessionPath).resolve().parent, filename)
_output_lock.__enter__()
import atexit
atexit.register(lambda: _output_lock.__exit__(None, None, None))
_write_manifest = gapi.begin_local_dynamic(Path(sessionPath).resolve().parent, filename, args.run_id)

fields = extract_fields_by_filename(sessionPath, filename,False)


def SetTrajectory(subject, name, x, y, z, exists, start, end, offset=None):
    # Reconstructions must be readable by later stages without a QTM write/read round trip.
    fields[name] = {"X": x, "Y": y, "Z": z, "Exists": exists}
    gapi.SetTrajectory(name, x, y, z, exists, start, end,
                       fields["initial_frame_offset"] if offset is None else offset)


SubjectName = fields["Name"]
FilePath, FileName = Path(fields["Path"]), fields["Filename"]
StartFrame, EndFrame = fields["First Frame"], fields["Last Frame"]
MarkerFrameRate = fields["Capture_Frequency"]
# StaticDataFileName = FilePath + 'Static_BF_' + SubjectName + '.py'
calib_file = FilePath / "Calibration" / (
    "Static_" + TestingCondition + "_" + SubjectName + ".py"
)
if calib_file.exists():
    StaticDataFileName = calib_file
else:
    StaticDataFileName = FilePath / (
        "Static_" + TestingCondition + "_" + SubjectName + ".py"
    )


class Dynamic_Main:
    def __init__(self):
        print("[DynamicMain] __init__ step 1: SimModlOutput", flush=True)
        self.Models = SimModlOutput()
        self.Models.trajectory_offset = fields["initial_frame_offset"]
        _write_manifest.bind_inputs(StaticDataFileName)

        # =============================================================================
        #       Create ASIS Markers if Pelfix Option was used
        # =============================================================================
        def HasTrajectory(subjectName, markerName):
            return markerName in fields

        # Function to extract markerdata into an array and check if data exists
        def MarkerArrayCheck(Subject, MarkerName):
            # Check if marker exists at all
            if HasTrajectory(Subject, MarkerName) is True:
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
            return MarkerDataX, MarkerDataY, MarkerDataZ, MarkerDataExists

        print(f"[DynamicMain] __init__ step 2: reading static file {StaticDataFileName}", flush=True)
        exec(open(StaticDataFileName).read())
        print("[DynamicMain] __init__ step 3: static file exec completed", flush=True)
        measurement_names = (
            "valueHeight", "valueASISdist", "valueLeftLegLength", "valueRightLegLength",
            "valueLeftKneeWidth", "valueRightKneeWidth", "valueLeftAnkleWidth",
            "valueRightAnkleWidth", "valueLeftASIStoGTdist", "valueRightASIStoGTdist",
            "valueLeftSoleThickness", "valueRightSoleThickness",
        )
        for measurement_name in measurement_names:
            value = float(getattr(self, measurement_name, 0.0))
            setattr(self, measurement_name, value if abs(value) > 10 else value * 1000.0)

        # Ensure safe defaults for options if not present in static calibration file
        for opt, default_val in [
            ("valuePelvicFixCheck", "0"),
            ("valueKneeAlignmentCheck", "0"),
            ("valueLeftFootModelCheck", "0"),
            ("valueRightFootModelCheck", "0"),
            ("valueLeftSoleThickness", "0"),
            ("valueRightSoleThickness", "0"),
        ]:
            if not hasattr(self, opt):
                setattr(self, opt, default_val)

        print("[DynamicMain] __init__ step 4: measurements & options ready", flush=True)
        # Compute ASIS Markers if Pelfix Option is Used
        if not self.valuePelvicFixCheck == "0":  # Pelfix Option is Used
            if self.valuePelvicFixCheck == "1":  # Iliac Opton
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

            if self.valuePelvicFixCheck == "2":  # Triad Opton
                # For Sacral Triad Case, delete Sacral Marker Name
                # Explanation: When Sacral marker is used and exists in the UserPreferences, then
                # Sacral Marker Name is deleted to push the code towards using PSIS markers.
                try:
                    del self.SacralMarkerName
                except:
                    pass
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

            # Compute ASIS for each frame
            framecount = fields["Frames"]
            arrayLASISMarkerX = [0 for m in range(framecount)]
            arrayLASISMarkerY = [0 for m in range(framecount)]
            arrayLASISMarkerZ = [0 for m in range(framecount)]
            arrayRASISMarkerX = [0 for m in range(framecount)]
            arrayRASISMarkerY = [0 for m in range(framecount)]
            arrayRASISMarkerZ = [0 for m in range(framecount)]
            exists = [True] * framecount

            active = slice(StartFrame, EndFrame)
            if self.valuePelvicFixCheck == "1":
                LeftPelvicMarkers = np.column_stack((LeftIliacMarkerX, LeftIliacMarkerY, LeftIliacMarkerZ))[active]
                RightPelvicMarkers = np.column_stack((RightIliacMarkerX, RightIliacMarkerY, RightIliacMarkerZ))[active]
                PosteriorPelvicMarkers = np.column_stack((SacralMarkerX, SacralMarkerY, SacralMarkerZ))[active]
            if self.valuePelvicFixCheck == "2":
                LeftPelvicMarkers = np.column_stack((LeftPSISMarkerX, LeftPSISMarkerY, LeftPSISMarkerZ))[active]
                RightPelvicMarkers = np.column_stack((RightPSISMarkerX, RightPSISMarkerY, RightPSISMarkerZ))[active]
                PosteriorPelvicMarkers = np.column_stack((SacralTriadMarkerX, SacralTriadMarkerY, SacralTriadMarkerZ))[active]
            EPelvisTech, MidASISLab = gait.TechCS_Pelvis_Newington(
                LeftPelvicMarkers, RightPelvicMarkers, PosteriorPelvicMarkers)
            reconstructed_left = np.zeros((framecount, 3))
            reconstructed_right = np.zeros((framecount, 3))
            reconstructed_left[active] = math.TransformPointIntoLabCoors(
                self.valueLeftASISMarkerPelvis, EPelvisTech, MidASISLab)
            reconstructed_right[active] = math.TransformPointIntoLabCoors(
                self.valueRightASISMarkerPelvis, EPelvisTech, MidASISLab)
            arrayLASISMarkerX, arrayLASISMarkerY, arrayLASISMarkerZ = reconstructed_left.T.tolist()
            arrayRASISMarkerX, arrayRASISMarkerY, arrayRASISMarkerZ = reconstructed_right.T.tolist()

            SetTrajectory(
                SubjectName,
                self.LeftASISMarkerName,
                arrayLASISMarkerX,
                arrayLASISMarkerY,
                arrayLASISMarkerZ,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )
            SetTrajectory(
                SubjectName,
                self.RightASISMarkerName,
                arrayRASISMarkerX,
                arrayRASISMarkerY,
                arrayRASISMarkerZ,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )
        ################################################################################################
        # Compute Heel, Toe and MTP1 Markers if Foot Model is Used
        if self.valueLeftFootModelCheck == "1":
            (
                LeftFirstMetarsalBaseMarkerX,
                LeftFirstMetarsalBaseMarkerY,
                LeftFirstMetarsalBaseMarkerZ,
                LeftFirstMetarsalBaseMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftFirstMetarsalBaseMarkerName)
            (
                LeftFirstMetarsalHeadMarkerX,
                LeftFirstMetarsalHeadMarkerY,
                LeftFirstMetarsalHeadMarkerZ,
                LeftFirstMetarsalHeadMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftFirstMetarsalHeadMarkerName)
            (
                LeftFifthMetarsalHeadMarkerX,
                LeftFifthMetarsalHeadMarkerY,
                LeftFifthMetarsalHeadMarkerZ,
                LeftFifthMetarsalHeadMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftFifthMetarsalHeadMarkerName)

        if self.valueRightFootModelCheck == "1":
            (
                RightFirstMetarsalBaseMarkerX,
                RightFirstMetarsalBaseMarkerY,
                RightFirstMetarsalBaseMarkerZ,
                RightFirstMetarsalBaseMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightFirstMetarsalBaseMarkerName)
            (
                RightFirstMetarsalHeadMarkerX,
                RightFirstMetarsalHeadMarkerY,
                RightFirstMetarsalHeadMarkerZ,
                RightFirstMetarsalHeadMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightFirstMetarsalHeadMarkerName)
            (
                RightFifthMetarsalHeadMarkerX,
                RightFifthMetarsalHeadMarkerY,
                RightFifthMetarsalHeadMarkerZ,
                RightFifthMetarsalHeadMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightFifthMetarsalHeadMarkerName)

        # Compute markers for each frame
        framecount = fields["Frames"]

        arrayLMT23HMarkerX = [0 for m in range(framecount)]
        arrayLMT23HMarkerY = [0 for m in range(framecount)]
        arrayLMT23HMarkerZ = [0 for m in range(framecount)]

        arrayRMT23HMarkerX = [0 for m in range(framecount)]
        arrayRMT23HMarkerY = [0 for m in range(framecount)]
        arrayRMT23HMarkerZ = [0 for m in range(framecount)]

        # Initlialize array for Upper Posterior Calcaneus markers for foot model (LPCALU = {0,0,30}*LHindFoot)
        if self.valueLeftFootModelCheck == "1":
            arrayLPCALUX = [0 for m in range(framecount)]
            arrayLPCALUY = [0 for m in range(framecount)]
            arrayLPCALUZ = [30 for m in range(framecount)]

        if self.valueRightFootModelCheck == "1":
            arrayRPCALUX = [0 for m in range(framecount)]
            arrayRPCALUY = [0 for m in range(framecount)]
            arrayRPCALUZ = [30 for m in range(framecount)]

        exists = [True] * framecount

        active = slice(StartFrame, EndFrame)
        if self.valueLeftFootModelCheck == "1":
            base = (
                np.column_stack((LeftFirstMetarsalBaseMarkerX, LeftFirstMetarsalBaseMarkerY,
                LeftFirstMetarsalBaseMarkerZ))[active]
            )
            head = (
                np.column_stack((LeftFirstMetarsalHeadMarkerX, LeftFirstMetarsalHeadMarkerY,
                LeftFirstMetarsalHeadMarkerZ))[active]
            )
            lateral = (
                np.column_stack((LeftFifthMetarsalHeadMarkerX, LeftFifthMetarsalHeadMarkerY,
                LeftFifthMetarsalHeadMarkerZ))[active]
            )
            forefoot = gait.TechCS_Forefoot_mSHCG("Left", base, head, lateral)
            reconstructed = np.zeros((framecount, 3))
            reconstructed[active] = math.TransformPointIntoLabCoors(
                self.valueLeft23MetatarsalHeadMarkerForefoot, forefoot, base)
            arrayLMT23HMarkerX, arrayLMT23HMarkerY, arrayLMT23HMarkerZ = reconstructed.T.tolist()
        if self.valueRightFootModelCheck == "1":
            base = (
                np.column_stack((RightFirstMetarsalBaseMarkerX, RightFirstMetarsalBaseMarkerY,
                RightFirstMetarsalBaseMarkerZ))[active]
            )
            head = (
                np.column_stack((RightFirstMetarsalHeadMarkerX, RightFirstMetarsalHeadMarkerY,
                RightFirstMetarsalHeadMarkerZ))[active]
            )
            lateral = (
                np.column_stack((RightFifthMetarsalHeadMarkerX, RightFifthMetarsalHeadMarkerY,
                RightFifthMetarsalHeadMarkerZ))[active]
            )
            forefoot = gait.TechCS_Forefoot_mSHCG("Right", base, head, lateral)
            reconstructed = np.zeros((framecount, 3))
            reconstructed[active] = math.TransformPointIntoLabCoors(
                self.valueRight23MetatarsalHeadMarkerForefoot, forefoot, base)
            arrayRMT23HMarkerX, arrayRMT23HMarkerY, arrayRMT23HMarkerZ = reconstructed.T.tolist()

        if self.valueLeftFootModelCheck == "1":
            SetTrajectory(
                SubjectName,
                self.LeftToeMarkerName,
                arrayLMT23HMarkerX,
                arrayLMT23HMarkerY,
                arrayLMT23HMarkerZ,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )
            if HasTrajectory(SubjectName, self.LeftHeelMarkerName) is False:
                LPCALx, LPCALy, LPCALz, LPCALexists = (
                    fields[self.LeftPosteriorCalcaneusMarkerName]["X"],
                    fields[self.LeftPosteriorCalcaneusMarkerName]["Y"],
                    fields[self.LeftPosteriorCalcaneusMarkerName]["Z"],
                    fields[self.LeftPosteriorCalcaneusMarkerName]["Exists"],
                )
                SetTrajectory(
                    SubjectName,
                    self.LeftHeelMarkerName,
                    LPCALx,
                    LPCALy,
                    LPCALz,
                    exists,
                    fields["First Frame"],
                    fields["Last Frame"],
                )

        if self.valueRightFootModelCheck == "1":
            SetTrajectory(
                SubjectName,
                self.RightToeMarkerName,
                arrayRMT23HMarkerX,
                arrayRMT23HMarkerY,
                arrayRMT23HMarkerZ,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
                fields["initial_frame_offset"],
            )
            if HasTrajectory(SubjectName, self.RightHeelMarkerName) is False:
                RPCALx, RPCALy, RPCALz, RPCALexists = (
                    fields[self.RightPosteriorCalcaneusMarkerName]["X"],
                    fields[self.RightPosteriorCalcaneusMarkerName]["Y"],
                    fields[self.RightPosteriorCalcaneusMarkerName]["Z"],
                    fields[self.RightPosteriorCalcaneusMarkerName]["Exists"],
                )
                SetTrajectory(
                    SubjectName,
                    self.RightHeelMarkerName,
                    RPCALx,
                    RPCALy,
                    RPCALz,
                    exists,
                    fields["First Frame"],
                    fields["Last Frame"],
                    fields["initial_frame_offset"],
                )

        ################################################################################################

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
            LeftPSISMarkerX, LeftPSISMarkerY, LeftPSISMarkerZ, LeftPSISMarkerExists = (
                MarkerArrayCheck(SubjectName, self.LeftPSISMarkerName)
            )
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
            active = slice(StartFrame, EndFrame)
            SacralMarkerX[active] = (np.asarray(LeftPSISMarkerX)[active] + np.asarray(RightPSISMarkerX)[active]) / 2
            SacralMarkerY[active] = (np.asarray(LeftPSISMarkerY)[active] + np.asarray(RightPSISMarkerY)[active]) / 2
            SacralMarkerZ[active] = (np.asarray(LeftPSISMarkerZ)[active] + np.asarray(RightPSISMarkerZ)[active]) / 2
        LeftASISMarkerX, LeftASISMarkerY, LeftASISMarkerZ, LeftASISMarkerExists = (
            MarkerArrayCheck(SubjectName, self.LeftASISMarkerName)
        )
        LeftThighMarkerX, LeftThighMarkerY, LeftThighMarkerZ, LeftThighMarkerExists = (
            MarkerArrayCheck(SubjectName, self.LeftThighMarkerName)
        )
        (
            LeftLateralKneeMarkerX,
            LeftLateralKneeMarkerY,
            LeftLateralKneeMarkerZ,
            LeftLateralKneeMarkerExists,
        ) = MarkerArrayCheck(SubjectName, self.LeftLateralKneeMarkerName)
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
        if self.valueLeftFootModelCheck == "1":
            (
                LeftLateralCalcaneusMarkerX,
                LeftLateralCalcaneusMarkerY,
                LeftLateralCalcaneusMarkerZ,
                LeftLateralCalcaneusMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftLateralCalcaneusMarkerName)
            (
                LeftMedialCalcaneusMarkerX,
                LeftMedialCalcaneusMarkerY,
                LeftMedialCalcaneusMarkerZ,
                LeftMedialCalcaneusMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftMedialCalcaneusMarkerName)
            (
                LeftPosteriorCalcaneusMarkerX,
                LeftPosteriorCalcaneusMarkerY,
                LeftPosteriorCalcaneusMarkerZ,
                LeftPosteriorCalcaneusMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftPosteriorCalcaneusMarkerName)
            (
                LeftFirstMetarsalBaseMarkerX,
                LeftFirstMetarsalBaseMarkerY,
                LeftFirstMetarsalBaseMarkerZ,
                LeftFirstMetarsalBaseMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftFirstMetarsalBaseMarkerName)
            (
                LeftFirstMetarsalHeadMarkerX,
                LeftFirstMetarsalHeadMarkerY,
                LeftFirstMetarsalHeadMarkerZ,
                LeftFirstMetarsalHeadMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftFirstMetarsalHeadMarkerName)
            (
                LeftFifthMetarsalHeadMarkerX,
                LeftFifthMetarsalHeadMarkerY,
                LeftFifthMetarsalHeadMarkerZ,
                LeftFifthMetarsalHeadMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftFifthMetarsalHeadMarkerName)
            # LeftFirstMetatarsoPhalangealJointMarkerX, LeftFirstMetatarsoPhalangealJointMarkerY, LeftFirstMetatarsoPhalangealJointMarkerZ, LeftFirstMetatarsoPhalangealJointMarkerExists = MarkerArrayCheck(SubjectName, self.LeftFirstMetatarsoPhalangealJointMarkerName)
            (
                LeftHalluxMarkerX,
                LeftHalluxMarkerY,
                LeftHalluxMarkerZ,
                LeftHalluxMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.LeftHalluxMarkerName)
        RightASISMarkerX, RightASISMarkerY, RightASISMarkerZ, RightASISMarkerExists = (
            MarkerArrayCheck(SubjectName, self.RightASISMarkerName)
        )
        (
            RightThighMarkerX,
            RightThighMarkerY,
            RightThighMarkerZ,
            RightThighMarkerExists,
        ) = MarkerArrayCheck(SubjectName, self.RightThighMarkerName)
        (
            RightLateralKneeMarkerX,
            RightLateralKneeMarkerY,
            RightLateralKneeMarkerZ,
            RightLateralKneeMarkerExists,
        ) = MarkerArrayCheck(SubjectName, self.RightLateralKneeMarkerName)
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
        RightHeelMarkerX, RightHeelMarkerY, RightHeelMarkerZ, RightHeelMarkerExists = (
            MarkerArrayCheck(SubjectName, self.RightHeelMarkerName)
        )
        if self.valueRightFootModelCheck == "1":
            (
                RightLateralCalcaneusMarkerX,
                RightLateralCalcaneusMarkerY,
                RightLateralCalcaneusMarkerZ,
                RightLateralCalcaneusMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightLateralCalcaneusMarkerName)
            (
                RightMedialCalcaneusMarkerX,
                RightMedialCalcaneusMarkerY,
                RightMedialCalcaneusMarkerZ,
                RightMedialCalcaneusMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightMedialCalcaneusMarkerName)
            (
                RightPosteriorCalcaneusMarkerX,
                RightPosteriorCalcaneusMarkerY,
                RightPosteriorCalcaneusMarkerZ,
                RightPosteriorCalcaneusMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightPosteriorCalcaneusMarkerName)
            (
                RightFirstMetarsalBaseMarkerX,
                RightFirstMetarsalBaseMarkerY,
                RightFirstMetarsalBaseMarkerZ,
                RightFirstMetarsalBaseMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightFirstMetarsalBaseMarkerName)
            (
                RightFirstMetarsalHeadMarkerX,
                RightFirstMetarsalHeadMarkerY,
                RightFirstMetarsalHeadMarkerZ,
                RightFirstMetarsalHeadMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightFirstMetarsalHeadMarkerName)
            (
                RightFifthMetarsalHeadMarkerX,
                RightFifthMetarsalHeadMarkerY,
                RightFifthMetarsalHeadMarkerZ,
                RightFifthMetarsalHeadMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightFifthMetarsalHeadMarkerName)
            # RightFirstMetatarsoPhalangealJointMarkerX, RightFirstMetatarsoPhalangealJointMarkerY, RightFirstMetatarsoPhalangealJointMarkerZ, RightFirstMetatarsoPhalangealJointMarkerExists = MarkerArrayCheck(SubjectName, self.RightFirstMetatarsoPhalangealJointMarkerName)
            (
                RightHalluxMarkerX,
                RightHalluxMarkerY,
                RightHalluxMarkerZ,
                RightHalluxMarkerExists,
            ) = MarkerArrayCheck(SubjectName, self.RightHalluxMarkerName)

        # Tibial Triad Check
        if (
            HasTrajectory(SubjectName, self.LeftTibialMarkerName) is True
            and HasTrajectory(SubjectName, self.LeftTibialUpperMarkerName) is True
            and HasTrajectory(SubjectName, self.LeftTibialLowerMarkerName) is True
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
            HasTrajectory(SubjectName, self.RightTibialMarkerName) is True
            and HasTrajectory(SubjectName, self.RightTibialUpperMarkerName) is True
            and HasTrajectory(SubjectName, self.RightTibialLowerMarkerName) is True
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

        # =============================================================================
        #       Determine if Trunk Data is Available
        # =============================================================================
        if (
            C7MarkerZ[StartFrame]
            * LeftClavicleMarkerZ[StartFrame]
            * RightClavicleMarkerZ[StartFrame]
        ) > 0:
            TrunkFlag = 1
        else:
            TrunkFlag = 0

        # =============================================================================
        #      Check for Medial Ankle marker drop-off
        # =============================================================================
        framecount = fields["Frames"]
        LeftMedialAnkleMarkerDropOff = int(np.any(np.asarray(LeftMedialAnkleMarkerZ)[StartFrame:EndFrame] == 0))
        RightMedialAnkleMarkerDropOff = int(np.any(np.asarray(RightMedialAnkleMarkerZ)[StartFrame:EndFrame] == 0))

        # =============================================================================
        #      Determine Walking Direction and lab coordinate system
        # =============================================================================

        # initialize the global or lab coordinate system
        ELab = np.eye(3)

        # Compute pelvis forward direction
        SacralMarker = np.array(
            [
                SacralMarkerX[StartFrame],
                SacralMarkerY[StartFrame],
                SacralMarkerZ[StartFrame],
            ]
        )
        CenterASIS = np.array(
            [
                (LeftASISMarkerX[StartFrame] + RightASISMarkerX[StartFrame]) / 2,
                (LeftASISMarkerY[StartFrame] + RightASISMarkerY[StartFrame]) / 2,
                (LeftASISMarkerZ[StartFrame] + RightASISMarkerZ[StartFrame]) / 2,
            ]
        )
        PelvisForwardDirectionVector = math.ComputeUnitVecFromPts(
            SacralMarker, CenterASIS
        )
        # print PelvisForwardDirectionVector
        if abs(PelvisForwardDirectionVector[1]) > abs(
            PelvisForwardDirectionVector[0]
        ):  # Forward facing direction is + Y
            if PelvisForwardDirectionVector[1] > 0:
                ELab[0, 0], ELab[1, 0], ELab[2, 0] = 0, 1, 0
                ELab[0, 1], ELab[1, 1], ELab[2, 1] = -1, 0, 0
                # Always Set to 1 to disable data manipulation
                Direction = 1
            else:
                ELab[0, 0], ELab[1, 0], ELab[2, 0] = 0, -1, 0
                ELab[0, 1], ELab[1, 1], ELab[2, 1] = 1, 0, 0
                # Always Set to 1 to disable data manipulation
                Direction = 1
        else:
            if PelvisForwardDirectionVector[0] > 0:
                Direction = 1
            else:
                Direction = -1

        # print ELab
        # print Direction

        # =============================================================================
        #       Anthropometic relationships from Demester (as reported in Winter's text) are used
        # =============================================================================
        body_mass_val = float(getattr(self, "valueBodyMass", fields.get("BodyMass", fields.get("Bodymass", 60.0))))
        if body_mass_val <= 0:
            body_mass_val = 60.0
        self.valueBodyMass = body_mass_val
        HATMass = 0.678 * body_mass_val
        ThighMass = 0.1 * body_mass_val
        ShankMass = 0.0465 * body_mass_val
        FootMass = 0.0145 * body_mass_val
        print(f"[DynamicMain] __init__ step 5: BodyMass={body_mass_val}, HATMass={HATMass:.2f}", flush=True)

        # =============================================================================
        #      Compute Kinematics & Kinetics
        # =============================================================================

        # Initialize arrays to write to C3D File
        framecount = fields["Frames"]
        exists = [True] * framecount

        arrayLeftHipCenter = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightHipCenter = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftKneeCenter = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightKneeCenter = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftAnkleCenter = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightAnkleCenter = [[0.0 for m in range(framecount)] for n in range(3)]

        # ASI, KNE, ANK for MAPS
        arrayLeftASIS = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightASIS = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftKNE = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightKNE = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftANK = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightANK = [[0.0 for m in range(framecount)] for n in range(3)]

        # Initialize array for Pelvic Origin, UpperPCAL for SLC
        arrayPelvisOrigin = [[0.0 for m in range(framecount)] for n in range(3)]
        if self.valueLeftFootModelCheck == "1":
            arrayLeftUpperPCAL = [[0.0 for m in range(framecount)] for n in range(3)]
        if self.valueRightFootModelCheck == "1":
            arrayRightUpperPCAL = [[0.0 for m in range(framecount)] for n in range(3)]

        arrayLeftTrunkAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftTrunkAnglesTOR = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftTrunkAnglesROT = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftPelvisAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftPelvisAnglesTOR = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftPelvisAnglesROT = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftThighAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftShankAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftFootAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        if self.valueLeftFootModelCheck == "1":
            arrayLeftHindfootAngles = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayLeftForefootAngles = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayLeftHalluxAngles = [[0.0 for m in range(framecount)] for n in range(3)]

        arrayRightTrunkAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightTrunkAnglesTOR = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightTrunkAnglesROT = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightPelvisAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightPelvisAnglesTOR = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightPelvisAnglesROT = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightThighAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightShankAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightFootAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        if self.valueRightFootModelCheck == "1":
            arrayRightHindfootAngles = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayRightForefootAngles = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayRightHalluxAngles = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]

        arrayLeftHipAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftKneeAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftKneeAnglesProximal = [
            [0.0 for m in range(framecount)] for n in range(3)
        ]
        arrayLeftKneeAnglesDistal = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftAnkleAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        if self.valueLeftFootModelCheck == "1":
            arrayLeftAnkleComplexAngles = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayLeftMidfootAngles = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayLeftToesAngles = [[0.0 for m in range(framecount)] for n in range(3)]

        arrayRightHipAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightKneeAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightKneeAnglesProximal = [
            [0.0 for m in range(framecount)] for n in range(3)
        ]
        arrayRightKneeAnglesDistal = [
            [0.0 for m in range(framecount)] for n in range(3)
        ]
        arrayRightAnkleAngles = [[0.0 for m in range(framecount)] for n in range(3)]
        if self.valueRightFootModelCheck == "1":
            arrayRightAnkleComplexAngles = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayRightMidfootAngles = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayRightToesAngles = [[0.0 for m in range(framecount)] for n in range(3)]

        arrayLeftTrunkAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftPelvisAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftThighAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftShankAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftFootAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        if self.valueLeftFootModelCheck == "1":
            arrayLeftHindfootAnglesRad = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayLeftForefootAnglesRad = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayLeftHalluxAnglesRad = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
        arrayRightTrunkAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightPelvisAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightThighAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightShankAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightFootAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        if self.valueRightFootModelCheck == "1":
            arrayRightHindfootAnglesRad = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayRightForefootAnglesRad = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayRightHalluxAnglesRad = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]

        arrayLeftHipAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftKneeAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftAnkleAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        if self.valueLeftFootModelCheck == "1":
            arrayLeftAnkleComplexAnglesRad = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayLeftMidfootAnglesRad = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayLeftToesAnglesRad = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]

        arrayRightHipAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightKneeAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightAnkleAnglesRad = [[0.0 for m in range(framecount)] for n in range(3)]
        if self.valueRightFootModelCheck == "1":
            arrayRightAnkleComplexAnglesRad = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayRightMidfootAnglesRad = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]
            arrayRightToesAnglesRad = [
                [0.0 for m in range(framecount)] for n in range(3)
            ]

        if self.valueLeftFootModelCheck == "1" or self.valueRightFootModelCheck == "1":
            arraySupination = [[0.0 for m in range(framecount)] for n in range(3)]
            arraySkew = [[0.0 for m in range(framecount)] for n in range(3)]

        arrayHATCenterOfMass = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftThighCenterOfMass = [
            [0.0 for m in range(framecount)] for n in range(3)
        ]
        arrayLeftShankCenterOfMass = [
            [0.0 for m in range(framecount)] for n in range(3)
        ]
        arrayLeftFootCenterOfMass = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightThighCenterOfMass = [
            [0.0 for m in range(framecount)] for n in range(3)
        ]
        arrayRightShankCenterOfMass = [
            [0.0 for m in range(framecount)] for n in range(3)
        ]
        arrayRightFootCenterOfMass = [
            [0.0 for m in range(framecount)] for n in range(3)
        ]

        arrayLeftHipMoment = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftHipPower = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftHipPowerTotal = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftKneeMoment = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftKneePower = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftKneePowerTotal = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftAnkleMoment = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftAnklePower = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftAnklePowerTotal = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightHipMoment = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightHipPower = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightHipPowerTotal = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightKneeMoment = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightKneePower = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightKneePowerTotal = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightAnkleMoment = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightAnklePower = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightAnklePowerTotal = [[0.0 for m in range(framecount)] for n in range(3)]

        # Add JRF, GRF, Moment/Power Sums
        # Joint Reaction Forces
        arrayLeftAnkleJRF = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftKneeJRF = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftHipJRF = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightAnkleJRF = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightKneeJRF = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightHipJRF = [[0.0 for m in range(framecount)] for n in range(3)]
        # Ground Reaction Forces and Moments
        arrayLeftGRF = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLeftGRM = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightGRF = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightGRM = [[0.0 for m in range(framecount)] for n in range(3)]
        # Moment and Power (MP) Sums (SagittalMomentSum, SagittalPowerSum, TotalPowerSum)
        arrayLeftMPSum = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightMPSum = [[0.0 for m in range(framecount)] for n in range(3)]
        # CoP relative to the foot CS
        arrayLeftFootCoP = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRightFootCoP = [[0.0 for m in range(framecount)] for n in range(3)]

        # Muscle Length and Velocities
        arrayGluteusMaxLength = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayIlioPsoasLength = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRectFemLength = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayMedHamstringLength = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLatHamstringLength = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayGastrocLength = [[0.0 for m in range(framecount)] for n in range(3)]
        arraySoleusLength = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayTibPostLength = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayPeronealLength = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayVastusLatLength = [[0.0 for m in range(framecount)] for n in range(3)]

        arrayGluteusMaxVelocity = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayIlioPsoasVelocity = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayRectFemVelocity = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayMedHamstringVelocity = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayLatHamstringVelocity = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayGastrocVelocity = [[0.0 for m in range(framecount)] for n in range(3)]
        arraySoleusVelocity = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayTibPostVelocity = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayPeronealVelocity = [[0.0 for m in range(framecount)] for n in range(3)]
        arrayVastusLatVelocity = [[0.0 for m in range(framecount)] for n in range(3)]

        #        arrayLeftMusclePoint1 = [[0. for m in range(framecount)] for n in range(3)]
        #        arrayLeftMusclePoint2 = [[0. for m in range(framecount)] for n in range(3)]
        #        arrayLeftMusclePoint3 = [[0. for m in range(framecount)] for n in range(3)]
        #        arrayLeftMusclePoint4 = [[0. for m in range(framecount)] for n in range(3)]
        #        arrayRightMusclePoint1 = [[0. for m in range(framecount)] for n in range(3)]
        #        arrayRightMusclePoint2 = [[0. for m in range(framecount)] for n in range(3)]
        #        arrayRightMusclePoint3 = [[0. for m in range(framecount)] for n in range(3)]
        #        arrayRightMusclePoint4 = [[0. for m in range(framecount)] for n in range(3)]

        # Muscle Length-Velocity Constants
        # Delp Pelvis Definitio is 12 deg less anteriorly tilted than Newington Gait Model
        PelvicTiltOffset = -12.0

        # Location of Femoral heads w.r.t. Delp Pelvis
        DelpLeftHJC = [-70.7, 83.5, -66.1]
        DelpRightHJC = [-70.7, -83.5, -66.1]
        # Location of KHC w.r.t. HJC at zero knee flexion
        DelpKJC0 = [-5.25, 0, -396]
        # Location of AJC w.r.t. KJC
        DelpAJC = [0, 0, -430]
        # Location of Patella w.r.r. tibia at zero knee flexion
        DelpLPat0 = [49.7, 2.4, -22.7]
        DelpRPat0 = [49.7, -2.4, -22.7]

        # Third Order Polynomial for knee and patella translation and rotation w.r.r. tibia
        # Knee Joint Center w.r.t. Femoral head *}
        # {* Anterior position vs. Knee Flexion *}
        KneeX0 = -5.251699577
        KneeX1 = 0.224993829
        KneeX2 = -0.000591743
        KneeX3 = -9.51e-06
        # {* Superior position vs. Knee Flexion *}
        KneeZ0 = -396.0286373
        KneeZ1 = -0.025460796
        KneeZ2 = -0.002797058
        KneeZ3 = 9.70e-06
        # {* Patella origin w.r.t. Tibia *}
        # {* Anterior position vs. Knee Flexion *}
        PatX0 = 49.64730717
        PatX1 = -0.116066668
        PatX2 = -0.001214601
        PatX3 = -5.31e-07
        # {* Superior position vs. Knee Flexion *}
        PatZ0 = -22.66784449
        PatZ1 = 0.028928273
        PatZ2 = 0.000507812
        PatZ3 = -5.79e-06
        # {* Flexion vs. Knee Flexion *}
        PatR0 = 2.754722372
        PatR1 = -1.019833144
        PatR2 = 0.014578827
        PatR3 = -6.28e-05
        # {* M/L position: Negative (lateral) for Right side *}
        PatY = -2.4

        # {* Calcaneal Tubercle rel. to AJC *}
        LCalC = [-48.7, 7.9, -42.0]
        RCalC = [-48.7, -7.9, -42.0]

        LToeC = [179, -1.1, -2.0]
        RToeC = [179, 1.1, -2.0]

        # {* Locally Referenced Muscle Attachments from Delp *}
        # {* x=anterior, y=left lateral, z=superior *}
        # {* Right hand coordinate system for Left leg, flip sign of y-component for Right *}

        # {*Gluteus maximus (Superior [GMaS], Middle [GMaM] and Inferior [GMaI] compartments0, 4 points*}
        GMaS = []
        GMaS.append([-119.5, 70.0, 61.2])  # {*Pel*}
        GMaS.append([-129.1, 88.6, 1.2])  # {*Pel*}
        GMaS.append([-45.7, 39.2, -24.8])  # {*Fem*}
        GMaS.append([-27.7, 47.0, -56.6])  # {*Fem*}
        GMaS_Seg = ["Pelvis", "Pelvis", "Thigh", "Thigh"]

        GMaM = []
        GMaM.append([-134.9, 56.3, 17.6])  # {*Pel*}
        GMaM.append([-137.6, 91.4, -52.0])  # {*Pel*}
        GMaM.append([-42.6, 29.3, -53.0])  # {*Fem*}
        GMaM.append([-15.6, -101.6, 41.9])  # {*Fem*}
        GMaM_Seg = ["Pelvis", "Pelvis", "Thigh", "Thigh"]

        GMaI = []
        GMaI.append([-155.6, 5.8, -31.4])  # {*Pel*}
        GMaI.append([-152.9, 40.3, -105.2])  # {*Pel*}
        GMaI.append([-29.9, 13.5, -104.1])  # {*Fem*}
        GMaI.append([-6.0, 41.1, -141.9])  # {*Fem*}
        GMaI_Seg = ["Pelvis", "Pelvis", "Thigh", "Thigh"]

        # {* Iliacus, 4 points *}
        Ilia = []
        Ilia.append([-67.4, 85.4, 36.5])  # {*Pel*}
        Ilia.append([-21.8, 85.1, -55.0])  # {*Pel*}
        Ilia.append([1.7, 5.7, -54.3])  # {*Fem*}
        Ilia.append([-19.3, 12.9, -62.1])  # {*Fem*}
        Ilia_Seg = ["Pelvis", "Pelvis", "Thigh", "Thigh"]

        # {* Psoas, 4 points *}
        Psoa = []
        Psoa.append([-64.7, 28.9, 88.7])  # {*Pel*}
        Psoa.append([-23.8, 75.9, -57.0])  # {*Pel*}
        Psoa.append([1.6, 3.8, -50.7])  # {*Fem*}
        Psoa.append([18.8, 10.4, -59.7])  # {*Fem*}
        Psoa_Seg = ["Pelvis", "Pelvis", "Thigh", "Thigh"]

        # {* Vastus Lateralis, 5 points *}
        VaLa = []
        VaLa.append([4.8, 34.9, -185.4])  # {*Fem*}
        VaLa.append([26.9, 40.9, -259.1])  # {*Fem*}
        VaLa.append([36.1, 20.5, -403.0])  # {*Fem: -172<KneeAng<-69deg*}
        VaLa.append([25.3, 18.4, -424.3])  # {*Fem: -172<KneeAng<-110deg*}
        VaLa.append([10.3, 14.1, 42.3])  # {*Pat*}
        VaLa_Seg = ["Thigh", "Thigh", "Thigh", "Thigh", "Patella"]

        # {* Semimembranosus, 2 points *}
        SeMe = []
        SeMe.append([-119.2, 69.5, -101.5])  # {*Pel*}
        SeMe.append([-24.3, -19.4, -53.6])  # {*Tib*}
        SeMe_Seg = ["Pelvis", "Shank"]

        # {* Semitendinosus, 4 points *}
        SeTe = []
        SeTe.append([-123.7, 60.3, -104.3])  # {*Pel*}
        SeTe.append([-31.4, -14.6, -54.5])  # {*Tib*}
        SeTe.append([-11.3, -24.5, -74.6])  # {*Tib*}
        SeTe.append([2.7, -19.3, -95.6])  # {*Tib*}
        SeTe_Seg = ["Pelvis", "Shank", "Shank", "Shank"]

        # {* Biceps Femoris (long and short head), 2 points *}
        BiFL = []
        BiFL.append([-124.4, 66.6, -100.1])  # {*Pel*}
        BiFL.append([-8.1, 42.3, -72.9])  # {*Tib*}
        BiFL_Seg = ["Pelvis", "Shank"]

        BiFS = []
        BiFS.append([5.0, 23.4, -211.1])  # {*Fem*}
        BiFS.append([-10.1, 40.6, -72.5])  # {*Tib*}
        BiFS_Seg = ["Thigh", "Shank"]

        # {* Rectus Femoris, 2/3 Points *}
        ReFe = []
        ReFe.append([-29.5, 96.8, -31.1])  # {*Pel*}
        # {* Wraps on Femur at large flexion angles *}
        ReFe.append([33.4, 1.9, -403.0])  # {*Fem: 83<KneeFlex<171 deg *}
        ReFe.append([12.1, -1.0, 43.7])  # {*Pat*}
        ReFe_Seg = ["Pelvis", "Thigh", "Patella"]

        # {* Gastrocnemius, Medial [GaMe] and Lateral [GaLa] heads, 3/4 points *}
        GaMe = []
        GaMe.append([-12.7, -23.5, -392.9])  # {*Fem*}
        # {* Wraps on posterior fem condyles when knee is extended *}
        GaMe.append([-23.9, -25.8, -402.2])  # {*Fem: -5<KneeFlex<44 deg*}
        GaMe.append([-21.7, -29.5, -48.7])  # {*Tib*}
        GaMe.append([4.4, -5.3, 31.0])  # {*Cal*}
        GaMe_Seg = ["Thigh", "Thigh", "Shank", "Calcaneus"]

        GaLa = []
        GaLa.append([-15.5, 27.2, -394.6])  # {*Fem*}
        # {* Wraps on posterior fem condyles when knee is extended *}
        GaLa.append([-25.4, 27.4, -401.8])  # {*Fem: -5<KneeAng<44 deg*}
        GaLa.append([-24.2, 23.5, -48.1])  # {*Tib*}
        GaLa.append([4.4, -5.3, 31.0])  # {*Cal*}
        GaLa_Seg = ["Thigh", "Thigh", "Shank", "Calcaneus"]

        # {* Soleus [Sole], 2 Points *}
        Sole = []
        Sole.append([-2.4, 7.1, -153.3])  # {*Tib*}
        Sole.append([4.4, -5.3, 31.0])  # {*Cal*}
        Sole_Seg = ["Shank", "Calcaneus"]

        # {* Tibialis Posterior [TiPo], 4 points *}
        TiPo = []
        TiPo.append([-9.4, 1.9, -134.8])  # {*Tib*}
        TiPo.append([-14.4, -22.9, -405.1])  # {*Tib*}
        TiPo.append([41.7, -28.6, 33.4])  # {*Cal*}
        TiPo.append([77.2, -28.1, 15.9])  # {*Cal*}
        TiPo_Seg = ["Shank", "Shank", "Calcaneus", "Calcaneus"]

        # {* Peroneus Brevis [PeBr] and Longus [PeLn], 5, 7 points *}
        PeBr = []
        PeBr.append([-7.0, 32.5, -264.6])  # {*Tib*}
        PeBr.append([-19.8, 28.3, -418.4])  # {*Tib*}
        PeBr.append([-14.4, 28.9, -429.5])  # {*Tib*}
        PeBr.append([47.1, 23.3, 27.0])  # {*Cal*}
        PeBr.append([67.7, 34.3, 21.9])  # {*Cal*}
        PeBr_Seg = ["Shank", "Shank", "Shank", "Calcaneus", "Calcaneus"]

        PeLn = []
        PeLn.append([0.5, 36.2, -156.8])  # {*Tib*}
        PeLn.append([-20.7, 28.6, -420.5])  # {*Tib*}
        PeLn.append([-16.2, 28.9, -431.9])  # {*Tib*}
        PeLn.append([43.8, 22.1, 23.0])  # {*Cal*}
        PeLn.append([68.1, 28.4, 10.6])  # {*Cal*}
        PeLn.append([85.2, 11.8, 6.9])  # {*Cal*}
        PeLn.append([120.3, -18.4, 8.5])  # {*Cal*}
        PeLn_Seg = [
            "Shank",
            "Shank",
            "Shank",
            "Calcaneus",
            "Calcaneus",
            "Calcaneus",
            "Calcaneus",
        ]

        print(f"[DynamicMain] __init__ step 6: Batched kinematics for frames {StartFrame} to {EndFrame}...", flush=True)
        # Batched kinematics, muscle paths and center of mass.
        _batch_frames = np.arange(StartFrame, EndFrame)
        _batch_slice = slice(StartFrame, EndFrame)
        _batch_count = len(_batch_frames)
        C7Marker = (
            math.FrameVector(_batch_count, Direction * np.asarray(C7MarkerX)[_batch_slice], Direction *
            np.asarray(C7MarkerY)[_batch_slice], np.asarray(C7MarkerZ)[_batch_slice])
        )
        LeftClavicleMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(LeftClavicleMarkerX)[_batch_slice],
            Direction * np.asarray(LeftClavicleMarkerY)[_batch_slice],
            np.asarray(LeftClavicleMarkerZ)[_batch_slice])
        )
        RightClavicleMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(RightClavicleMarkerX)[_batch_slice],
            Direction * np.asarray(RightClavicleMarkerY)[_batch_slice],
            np.asarray(RightClavicleMarkerZ)[_batch_slice])
        )
        SacralMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(SacralMarkerX)[_batch_slice], Direction *
            np.asarray(SacralMarkerY)[_batch_slice], np.asarray(SacralMarkerZ)[_batch_slice])
        )
        LeftASISMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(LeftASISMarkerX)[_batch_slice], Direction *
            np.asarray(LeftASISMarkerY)[_batch_slice], np.asarray(LeftASISMarkerZ)[_batch_slice])
        )
        LeftThighMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(LeftThighMarkerX)[_batch_slice], Direction *
            np.asarray(LeftThighMarkerY)[_batch_slice], np.asarray(LeftThighMarkerZ)[_batch_slice])
        )
        LeftLateralKneeMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(LeftLateralKneeMarkerX)[_batch_slice],
            Direction * np.asarray(LeftLateralKneeMarkerY)[_batch_slice],
            np.asarray(LeftLateralKneeMarkerZ)[_batch_slice])
        )
        LeftTibialMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(LeftTibialMarkerX)[_batch_slice], Direction *
            np.asarray(LeftTibialMarkerY)[_batch_slice], np.asarray(LeftTibialMarkerZ)[_batch_slice])
        )
        if LeftTibialTriadCheck is True:
            LeftTibialUpperMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftTibialUpperMarkerX)[_batch_slice],
                Direction * np.asarray(LeftTibialUpperMarkerY)[_batch_slice],
                np.asarray(LeftTibialUpperMarkerZ)[_batch_slice])
            )
            LeftTibialLowerMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftTibialLowerMarkerX)[_batch_slice],
                Direction * np.asarray(LeftTibialLowerMarkerY)[_batch_slice],
                np.asarray(LeftTibialLowerMarkerZ)[_batch_slice])
            )
        LeftLateralAnkleMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(LeftLateralAnkleMarkerX)[_batch_slice],
            Direction * np.asarray(LeftLateralAnkleMarkerY)[_batch_slice],
            np.asarray(LeftLateralAnkleMarkerZ)[_batch_slice])
        )
        LeftToeMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(LeftToeMarkerX)[_batch_slice], Direction *
            np.asarray(LeftToeMarkerY)[_batch_slice], np.asarray(LeftToeMarkerZ)[_batch_slice])
        )
        LeftMedialAnkleMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(LeftMedialAnkleMarkerX)[_batch_slice],
            Direction * np.asarray(LeftMedialAnkleMarkerY)[_batch_slice],
            np.asarray(LeftMedialAnkleMarkerZ)[_batch_slice])
        )
        LeftHeelMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(LeftHeelMarkerX)[_batch_slice], Direction *
            np.asarray(LeftHeelMarkerY)[_batch_slice], np.asarray(LeftHeelMarkerZ)[_batch_slice])
        )
        if self.valueLeftFootModelCheck == '1':
            LeftLateralCalcaneusMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftLateralCalcaneusMarkerX)[_batch_slice],
                Direction * np.asarray(LeftLateralCalcaneusMarkerY)[_batch_slice],
                np.asarray(LeftLateralCalcaneusMarkerZ)[_batch_slice])
            )
            LeftMedialCalcaneusMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftMedialCalcaneusMarkerX)[_batch_slice],
                Direction * np.asarray(LeftMedialCalcaneusMarkerY)[_batch_slice],
                np.asarray(LeftMedialCalcaneusMarkerZ)[_batch_slice])
            )
            LeftPosteriorCalcaneusMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftPosteriorCalcaneusMarkerX)[_batch_slice],
                Direction * np.asarray(LeftPosteriorCalcaneusMarkerY)[_batch_slice],
                np.asarray(LeftPosteriorCalcaneusMarkerZ)[_batch_slice])
            )
            LeftFirstMetarsalBaseMarker = (
                math.FrameVector(_batch_count, np.asarray(LeftFirstMetarsalBaseMarkerX)[_batch_slice],
                np.asarray(LeftFirstMetarsalBaseMarkerY)[_batch_slice],
                np.asarray(LeftFirstMetarsalBaseMarkerZ)[_batch_slice])
            )
            LeftFirstMetarsalHeadMarker = (
                math.FrameVector(_batch_count, np.asarray(LeftFirstMetarsalHeadMarkerX)[_batch_slice],
                np.asarray(LeftFirstMetarsalHeadMarkerY)[_batch_slice],
                np.asarray(LeftFirstMetarsalHeadMarkerZ)[_batch_slice])
            )
            LeftFifthMetarsalHeadMarker = (
                math.FrameVector(_batch_count, np.asarray(LeftFifthMetarsalHeadMarkerX)[_batch_slice],
                np.asarray(LeftFifthMetarsalHeadMarkerY)[_batch_slice],
                np.asarray(LeftFifthMetarsalHeadMarkerZ)[_batch_slice])
            )
            LeftEForefootTech = (
                gait.TechCS_Forefoot_mSHCG('Left', LeftFirstMetarsalBaseMarker, LeftFirstMetarsalHeadMarker,
                LeftFifthMetarsalHeadMarker)
            )
            LeftMTP1MarkerLab = (
                math.TransformPointIntoLabCoors(self.valueLeftFirstMetatarsoPhalangealJointMarkerForefoot,
                LeftEForefootTech, LeftFirstMetarsalBaseMarker)
            )
            LeftFirstMetatarsoPhalangealJointMarker = (
                math.FrameVector(_batch_count, Direction * LeftMTP1MarkerLab[..., 0], Direction *
                LeftMTP1MarkerLab[..., 1], LeftMTP1MarkerLab[..., 2])
            )
            LeftFirstMetarsalBaseMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftFirstMetarsalBaseMarkerX)[_batch_slice],
                Direction * np.asarray(LeftFirstMetarsalBaseMarkerY)[_batch_slice],
                np.asarray(LeftFirstMetarsalBaseMarkerZ)[_batch_slice])
            )
            LeftFirstMetarsalHeadMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftFirstMetarsalHeadMarkerX)[_batch_slice],
                Direction * np.asarray(LeftFirstMetarsalHeadMarkerY)[_batch_slice],
                np.asarray(LeftFirstMetarsalHeadMarkerZ)[_batch_slice])
            )
            LeftFifthMetarsalHeadMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftFifthMetarsalHeadMarkerX)[_batch_slice],
                Direction * np.asarray(LeftFifthMetarsalHeadMarkerY)[_batch_slice],
                np.asarray(LeftFifthMetarsalHeadMarkerZ)[_batch_slice])
            )
            LeftHalluxMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftHalluxMarkerX)[_batch_slice], Direction *
                np.asarray(LeftHalluxMarkerY)[_batch_slice], np.asarray(LeftHalluxMarkerZ)[_batch_slice])
            )
        RightASISMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(RightASISMarkerX)[_batch_slice], Direction *
            np.asarray(RightASISMarkerY)[_batch_slice], np.asarray(RightASISMarkerZ)[_batch_slice])
        )
        RightThighMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(RightThighMarkerX)[_batch_slice], Direction *
            np.asarray(RightThighMarkerY)[_batch_slice], np.asarray(RightThighMarkerZ)[_batch_slice])
        )
        RightLateralKneeMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(RightLateralKneeMarkerX)[_batch_slice],
            Direction * np.asarray(RightLateralKneeMarkerY)[_batch_slice],
            np.asarray(RightLateralKneeMarkerZ)[_batch_slice])
        )
        RightTibialMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(RightTibialMarkerX)[_batch_slice], Direction *
            np.asarray(RightTibialMarkerY)[_batch_slice], np.asarray(RightTibialMarkerZ)[_batch_slice])
        )
        if RightTibialTriadCheck is True:
            RightTibialUpperMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightTibialUpperMarkerX)[_batch_slice],
                Direction * np.asarray(RightTibialUpperMarkerY)[_batch_slice],
                np.asarray(RightTibialUpperMarkerZ)[_batch_slice])
            )
            RightTibialLowerMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightTibialLowerMarkerX)[_batch_slice],
                Direction * np.asarray(RightTibialLowerMarkerY)[_batch_slice],
                np.asarray(RightTibialLowerMarkerZ)[_batch_slice])
            )
        RightLateralAnkleMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(RightLateralAnkleMarkerX)[_batch_slice],
            Direction * np.asarray(RightLateralAnkleMarkerY)[_batch_slice],
            np.asarray(RightLateralAnkleMarkerZ)[_batch_slice])
        )
        RightToeMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(RightToeMarkerX)[_batch_slice], Direction *
            np.asarray(RightToeMarkerY)[_batch_slice], np.asarray(RightToeMarkerZ)[_batch_slice])
        )
        RightMedialAnkleMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(RightMedialAnkleMarkerX)[_batch_slice],
            Direction * np.asarray(RightMedialAnkleMarkerY)[_batch_slice],
            np.asarray(RightMedialAnkleMarkerZ)[_batch_slice])
        )
        RightHeelMarker = (
            math.FrameVector(_batch_count, Direction * np.asarray(RightHeelMarkerX)[_batch_slice], Direction *
            np.asarray(RightHeelMarkerY)[_batch_slice], np.asarray(RightHeelMarkerZ)[_batch_slice])
        )
        if self.valueRightFootModelCheck == '1':
            RightLateralCalcaneusMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightLateralCalcaneusMarkerX)[_batch_slice],
                Direction * np.asarray(RightLateralCalcaneusMarkerY)[_batch_slice],
                np.asarray(RightLateralCalcaneusMarkerZ)[_batch_slice])
            )
            RightMedialCalcaneusMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightMedialCalcaneusMarkerX)[_batch_slice],
                Direction * np.asarray(RightMedialCalcaneusMarkerY)[_batch_slice],
                np.asarray(RightMedialCalcaneusMarkerZ)[_batch_slice])
            )
            RightPosteriorCalcaneusMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightPosteriorCalcaneusMarkerX)[_batch_slice],
                Direction * np.asarray(RightPosteriorCalcaneusMarkerY)[_batch_slice],
                np.asarray(RightPosteriorCalcaneusMarkerZ)[_batch_slice])
            )
            RightFirstMetarsalBaseMarker = (
                math.FrameVector(_batch_count, np.asarray(RightFirstMetarsalBaseMarkerX)[_batch_slice],
                np.asarray(RightFirstMetarsalBaseMarkerY)[_batch_slice],
                np.asarray(RightFirstMetarsalBaseMarkerZ)[_batch_slice])
            )
            RightFirstMetarsalHeadMarker = (
                math.FrameVector(_batch_count, np.asarray(RightFirstMetarsalHeadMarkerX)[_batch_slice],
                np.asarray(RightFirstMetarsalHeadMarkerY)[_batch_slice],
                np.asarray(RightFirstMetarsalHeadMarkerZ)[_batch_slice])
            )
            RightFifthMetarsalHeadMarker = (
                math.FrameVector(_batch_count, np.asarray(RightFifthMetarsalHeadMarkerX)[_batch_slice],
                np.asarray(RightFifthMetarsalHeadMarkerY)[_batch_slice],
                np.asarray(RightFifthMetarsalHeadMarkerZ)[_batch_slice])
            )
            RightEForefootTech = (
                gait.TechCS_Forefoot_mSHCG('Right', RightFirstMetarsalBaseMarker, RightFirstMetarsalHeadMarker,
                RightFifthMetarsalHeadMarker)
            )
            RightMTP1MarkerLab = (
                math.TransformPointIntoLabCoors(self.valueRightFirstMetatarsoPhalangealJointMarkerForefoot,
                RightEForefootTech, RightFirstMetarsalBaseMarker)
            )
            RightFirstMetatarsoPhalangealJointMarker = (
                math.FrameVector(_batch_count, Direction * RightMTP1MarkerLab[..., 0], Direction *
                RightMTP1MarkerLab[..., 1], RightMTP1MarkerLab[..., 2])
            )
            RightFirstMetarsalBaseMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightFirstMetarsalBaseMarkerX)[_batch_slice],
                Direction * np.asarray(RightFirstMetarsalBaseMarkerY)[_batch_slice],
                np.asarray(RightFirstMetarsalBaseMarkerZ)[_batch_slice])
            )
            RightFirstMetarsalHeadMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightFirstMetarsalHeadMarkerX)[_batch_slice],
                Direction * np.asarray(RightFirstMetarsalHeadMarkerY)[_batch_slice],
                np.asarray(RightFirstMetarsalHeadMarkerZ)[_batch_slice])
            )
            RightFifthMetarsalHeadMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightFifthMetarsalHeadMarkerX)[_batch_slice],
                Direction * np.asarray(RightFifthMetarsalHeadMarkerY)[_batch_slice],
                np.asarray(RightFifthMetarsalHeadMarkerZ)[_batch_slice])
            )
            RightHalluxMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightHalluxMarkerX)[_batch_slice], Direction *
                np.asarray(RightHalluxMarkerY)[_batch_slice], np.asarray(RightHalluxMarkerZ)[_batch_slice])
            )
        if TrunkFlag == 1:
            [ETrunkTech, PelvisCenterLab, ShouldersCenterLab] = (
                gait.TechCS_Trunk_Newington(C7Marker, LeftClavicleMarker, RightClavicleMarker, LeftASISMarker,
                RightASISMarker, SacralMarker)
            )
            ETrunkAnat = math.TransformAnatCoorSysFromTechCoors(self.valueETrunkAnatRelTech, ETrunkTech)
            ETrunkAnat = ETrunkTech
        [EPelvisTech, MidASISLab] = gait.TechCS_Pelvis_Newington(LeftASISMarker, RightASISMarker, SacralMarker)
        EPelvisAnat = math.TransformAnatCoorSysFromTechCoors(self.valueEPelvisAnatRelTech, EPelvisTech)
        if self.HipModelName == 'Newington':
            [LeftHipCenterPelvis, LeftHipCenterLab] = (
                gait.JointCenterModel_Hip_Newington('Left', self.MarkerDiameter, self.valueASISdist,
                self.valueLeftASIStoGTdist, self.valueLeftLegLength, self.valueRightLegLength, RightASISMarker,
                LeftASISMarker, EPelvisTech, MidASISLab)
            )
            [RightHipCenterPelvis, RightHipCenterLab] = (
                gait.JointCenterModel_Hip_Newington('Right', self.MarkerDiameter, self.valueASISdist,
                self.valueRightASIStoGTdist, self.valueLeftLegLength, self.valueRightLegLength, RightASISMarker,
                LeftASISMarker, EPelvisTech, MidASISLab)
            )
        if self.HipModelName == 'Harrington':
            [LeftHipCenterPelvis, LeftHipCenterLab] = (
                gait.JointCenterModel_Hip_Harrington('Left', self.valueASISdist, RightASISMarker, LeftASISMarker,
                SacralMarker, EPelvisTech, MidASISLab)
            )
            [RightHipCenterPelvis, RightHipCenterLab] = (
                gait.JointCenterModel_Hip_Harrington('Right', self.valueASISdist, RightASISMarker, LeftASISMarker,
                SacralMarker, EPelvisTech, MidASISLab)
            )
        if self.HipModelName == 'Harrington2':
            [LeftHipCenterPelvis, LeftHipCenterLab] = (
                gait.JointCenterModel_Hip_Harrington2('Left', self.valueASISdist, self.valueLeftLegLength,
                self.valueRightLegLength, RightASISMarker, LeftASISMarker, SacralMarker, EPelvisTech, MidASISLab)
            )
            [RightHipCenterPelvis, RightHipCenterLab] = (
                gait.JointCenterModel_Hip_Harrington2('Right', self.valueASISdist, self.valueLeftLegLength,
                self.valueRightLegLength, RightASISMarker, LeftASISMarker, SacralMarker, EPelvisTech, MidASISLab)
            )
        LeftEThighTech = gait.TechCS_Thigh_Newington('Left', LeftHipCenterLab, LeftThighMarker, LeftLateralKneeMarker)
        RightEThighTech = gait.TechCS_Thigh_Newington('Right', RightHipCenterLab, RightThighMarker, RightLateralKneeMarker)
        LeftEThighAnat = math.TransformAnatCoorSysFromTechCoors(self.valueLeftEThighAnatRelTech, LeftEThighTech)
        RightEThighAnat = math.TransformAnatCoorSysFromTechCoors(self.valueRightEThighAnatRelTech, RightEThighTech)
        LeftKneeCenterLab = (
            math.TransformPointIntoLabCoors(self.valueLeftKneeCenterThigh, LeftEThighTech,
            LeftLateralKneeMarker)
        )
        RightKneeCenterLab = (
            math.TransformPointIntoLabCoors(self.valueRightKneeCenterThigh, RightEThighTech,
            RightLateralKneeMarker)
        )
        if LeftTibialTriadCheck is True:
            LeftEShankTech = gait.TechCS_Shank_Newington('Left', LeftTibialUpperMarker, LeftTibialLowerMarker, LeftTibialMarker)
        else:
            LeftEShankTech = gait.TechCS_Shank_Newington('Left', LeftKneeCenterLab, LeftTibialMarker, LeftLateralAnkleMarker)
        if RightTibialTriadCheck is True:
            RightEShankTech = (
                gait.TechCS_Shank_Newington('Right', RightTibialUpperMarker, RightTibialLowerMarker,
                RightTibialMarker)
            )
        else:
            RightEShankTech = gait.TechCS_Shank_Newington('Right', RightKneeCenterLab, RightTibialMarker, RightLateralAnkleMarker)
        if LeftTibialTriadCheck is True:
            LeftAnkleCenterLab = math.TransformPointIntoLabCoors(self.valueLeftAnkleCenterShank, LeftEShankTech, LeftTibialMarker)
        else:
            LeftAnkleCenterLab = (
                math.TransformPointIntoLabCoors(self.valueLeftAnkleCenterShank, LeftEShankTech,
                LeftLateralAnkleMarker)
            )
        if RightTibialTriadCheck is True:
            RightAnkleCenterLab = math.TransformPointIntoLabCoors(self.valueRightAnkleCenterShank, RightEShankTech, RightTibialMarker)
        else:
            RightAnkleCenterLab = (
                math.TransformPointIntoLabCoors(self.valueRightAnkleCenterShank, RightEShankTech,
                RightLateralAnkleMarker)
            )
        if LeftMedialAnkleMarkerDropOff == 0:
            LeftAnkleCenterLab = (
                gait.JointCenterModel_Ankle_Newington('Left', self.MarkerDiameter, self.valueLeftAnkleWidth,
                LeftLateralAnkleMarker, LeftMedialAnkleMarker)
            )
        if RightMedialAnkleMarkerDropOff == 0:
            RightAnkleCenterLab = (
                gait.JointCenterModel_Ankle_Newington('Right', self.MarkerDiameter, self.valueRightAnkleWidth,
                RightLateralAnkleMarker, RightMedialAnkleMarker)
            )
        LeftEFootTech = gait.TechCS_Foot_Newington('Left', LeftKneeCenterLab, LeftAnkleCenterLab, LeftToeMarker)
        RightEFootTech = gait.TechCS_Foot_Newington('Right', RightKneeCenterLab, RightAnkleCenterLab, RightToeMarker)
        if self.valueLeftFootModelCheck == '1':
            LeftEHindfootTech = (
                gait.TechCS_Hindfoot_mSHCG('Left', LeftLateralCalcaneusMarker, LeftMedialCalcaneusMarker,
                LeftPosteriorCalcaneusMarker)
            )
            LeftEForefootTech = (
                gait.TechCS_Forefoot_mSHCG('Left', LeftFirstMetarsalBaseMarker, LeftFirstMetarsalHeadMarker,
                LeftFifthMetarsalHeadMarker)
            )
            LeftEHalluxTech = (
                gait.TechCS_Hallux_mSHCG('Left', LeftHalluxMarker, LeftFirstMetatarsoPhalangealJointMarker,
                LeftToeMarker)
            )
        if self.valueRightFootModelCheck == '1':
            RightEHindfootTech = (
                gait.TechCS_Hindfoot_mSHCG('Right', RightLateralCalcaneusMarker, RightMedialCalcaneusMarker,
                RightPosteriorCalcaneusMarker)
            )
            RightEForefootTech = (
                gait.TechCS_Forefoot_mSHCG('Right', RightFirstMetarsalBaseMarker, RightFirstMetarsalHeadMarker,
                RightFifthMetarsalHeadMarker)
            )
            RightEHalluxTech = (
                gait.TechCS_Hallux_mSHCG('Right', RightHalluxMarker, RightFirstMetatarsoPhalangealJointMarker,
                RightToeMarker)
            )
        LeftEShankProximalAnat = math.TransformAnatCoorSysFromTechCoors(self.valueLeftEShankProximalAnatRelTech, LeftEShankTech)
        RightEShankProximalAnat = math.TransformAnatCoorSysFromTechCoors(self.valueRightEShankProximalAnatRelTech, RightEShankTech)
        LeftEShankDistalAnat = math.TransformAnatCoorSysFromTechCoors(self.valueLeftEShankDistalAnatRelTech, LeftEShankTech)
        RightEShankDistalAnat = math.TransformAnatCoorSysFromTechCoors(self.valueRightEShankDistalAnatRelTech, RightEShankTech)
        if LeftMedialAnkleMarkerDropOff == 0:
            LeftEShankProximalAnat = (
                gait.AnatCS_Shank_Proximal_Newington('Left', LeftKneeCenterLab, LeftLateralKneeMarker,
                LeftAnkleCenterLab)
            )
            LeftEShankDistalAnat = gait.AnatCS_Shank_Distal_VCM('Left', LeftKneeCenterLab, LeftAnkleCenterLab, LeftLateralAnkleMarker)
        if RightMedialAnkleMarkerDropOff == 0:
            RightEShankProximalAnat = (
                gait.AnatCS_Shank_Proximal_Newington('Right', RightKneeCenterLab, RightLateralKneeMarker,
                RightAnkleCenterLab)
            )
            RightEShankDistalAnat = (
                gait.AnatCS_Shank_Distal_VCM('Right', RightKneeCenterLab, RightAnkleCenterLab,
                RightLateralAnkleMarker)
            )
        LeftEFootAnat = math.TransformAnatCoorSysFromTechCoors(self.valueLeftEFootAnatRelTech, LeftEFootTech)
        RightEFootAnat = math.TransformAnatCoorSysFromTechCoors(self.valueRightEFootAnatRelTech, RightEFootTech)
        try:
            LeftEFootTibAnat = math.TransformAnatCoorSysFromTechCoors(self.valueLeftEFootAnat2RelTech, LeftEFootTech)
            RightEFootTibAnat = math.TransformAnatCoorSysFromTechCoors(self.valueRightEFootAnat2RelTech, RightEFootTech)
        except:
            LeftEFootTibAnat = np.matrix([[0.0 for m in range(3)] for n in range(3)])
            RightEFootTibAnat = np.matrix([[0.0 for m in range(3)] for n in range(3)])
        if self.valueLeftFootModelCheck == '1':
            LeftEHindfootAnat = math.TransformAnatCoorSysFromTechCoors(self.valueLeftEHindfootAnatRelTech, LeftEHindfootTech)
            LeftEForefootAnat = math.TransformAnatCoorSysFromTechCoors(self.valueLeftEForefootAnatRelTech, LeftEForefootTech)
            LeftEHalluxAnat = math.TransformAnatCoorSysFromTechCoors(self.valueLeftEHalluxAnatRelTech, LeftEHalluxTech)
            LeftUpperPosteriorCalcaneusHindfoot = (
                math.FrameVector(_batch_count, np.asarray(arrayLPCALUX)[_batch_slice],
                np.asarray(arrayLPCALUY)[_batch_slice], np.asarray(arrayLPCALUZ)[_batch_slice])
            )
            LeftUpperPosteriorCalcaneusMarker = (
                math.TransformPointIntoLabCoors(LeftUpperPosteriorCalcaneusHindfoot, LeftEHindfootAnat,
                LeftPosteriorCalcaneusMarker)
            )
        if self.valueRightFootModelCheck == '1':
            RightEHindfootAnat = math.TransformAnatCoorSysFromTechCoors(self.valueRightEHindfootAnatRelTech, RightEHindfootTech)
            RightEForefootAnat = math.TransformAnatCoorSysFromTechCoors(self.valueRightEForefootAnatRelTech, RightEForefootTech)
            RightEHalluxAnat = math.TransformAnatCoorSysFromTechCoors(self.valueRightEHalluxAnatRelTech, RightEHalluxTech)
            RightUpperPosteriorCalcaneusHindfoot = (
                math.FrameVector(_batch_count, np.asarray(arrayRPCALUX)[_batch_slice],
                np.asarray(arrayRPCALUY)[_batch_slice], np.asarray(arrayRPCALUZ)[_batch_slice])
            )
            RightUpperPosteriorCalcaneusMarker = (
                math.TransformPointIntoLabCoors(RightUpperPosteriorCalcaneusHindfoot, RightEHindfootAnat,
                RightPosteriorCalcaneusMarker)
            )
        if TrunkFlag == 1:
            TrunkAnglesTORRad = math.EulerAngles_YXZ(ETrunkAnat, ELab)
            TrunkAnglesROTRad = math.EulerAngles_ZXY(ETrunkAnat, ELab)
            if self.TrunkRotationSequence == 'TOR':
                TrunkAnglesRad = TrunkAnglesTORRad
            if self.TrunkRotationSequence == 'ROT':
                TrunkAnglesRad = TrunkAnglesROTRad
        else:
            TrunkAnglesTORRad = math.FrameVector(_batch_count, 0.0, 0.0, 0.0)
            TrunkAnglesROTRad = math.FrameVector(_batch_count, 0.0, 0.0, 0.0)
            TrunkAnglesRad = math.FrameVector(_batch_count, 0.0, 0.0, 0.0)
        PelvisAnglesTORRad = math.EulerAngles_YXZ(EPelvisAnat, ELab)
        PelvisAnglesROTRad = math.EulerAngles_ZXY(EPelvisAnat, ELab)
        if self.PelvisRotationSequence == 'TOR':
            PelvisAnglesRad = PelvisAnglesTORRad
        if self.PelvisRotationSequence == 'ROT':
            PelvisAnglesRad = PelvisAnglesROTRad
        LeftThighAnglesRad = math.EulerAngles_YXZ(LeftEThighAnat, ELab)
        RightThighAnglesRad = math.EulerAngles_YXZ(RightEThighAnat, ELab)
        LeftShankAnglesRad = math.EulerAngles_YXZ(LeftEShankDistalAnat, ELab)
        RightShankAnglesRad = math.EulerAngles_YXZ(RightEShankDistalAnat, ELab)
        LeftFootAnglesRad = math.EulerAngles_YXZ(LeftEFootAnat, ELab)
        RightFootAnglesRad = math.EulerAngles_YXZ(RightEFootAnat, ELab)
        if self.valueLeftFootModelCheck == '1':
            LeftHindfootAnglesRad = math.EulerAngles_YXZ(LeftEHindfootAnat, ELab)
            LeftForefootAnglesRad = math.EulerAngles_YXZ(LeftEForefootAnat, ELab)
            LeftHalluxAnglesRad = math.EulerAngles_YXZ(LeftEHalluxAnat, ELab)
            ey = math.FrameVector(_batch_count, LeftEHindfootAnat[..., 0, 1], LeftEHindfootAnat[..., 1, 1], 0)
            ey = ey / np.linalg.norm(ey, axis=-1)[..., None]
            R1 = math.FrameVector(_batch_count, 0.0, 0.0, 1.0)
            ex = np.cross(ey, R1)
            ez = np.cross(ex, ey)
            LeftEHFProgression = np.stack((ex, ey, ez), axis=-1)
            LeftHindfootAnglesRelHFProgressionRad = math.EulerAngles_YXZ(LeftEHindfootAnat, LeftEHFProgression)
            LeftForefootAnglesRelHFProgressionRad = math.EulerAngles_YXZ(LeftEForefootAnat, LeftEHFProgression)
            LeftHalluxAnglesRelHFProgressionRad = math.EulerAngles_YXZ(LeftEHalluxAnat, LeftEHFProgression)
        if self.valueRightFootModelCheck == '1':
            RightHindfootAnglesRad = math.EulerAngles_YXZ(RightEHindfootAnat, ELab)
            RightForefootAnglesRad = math.EulerAngles_YXZ(RightEForefootAnat, ELab)
            RightHalluxAnglesRad = math.EulerAngles_YXZ(RightEHalluxAnat, ELab)
            ey = math.FrameVector(_batch_count, RightEHindfootAnat[..., 0, 1], RightEHindfootAnat[..., 1, 1], 0)
            ey = ey / np.linalg.norm(ey, axis=-1)[..., None]
            R1 = math.FrameVector(_batch_count, 0.0, 0.0, 1.0)
            ex = np.cross(ey, R1)
            ez = np.cross(ex, ey)
            RightEHFProgression = np.stack((ex, ey, ez), axis=-1)
            RightHindfootAnglesRelHFProgressionRad = math.EulerAngles_YXZ(RightEHindfootAnat, RightEHFProgression)
            RightForefootAnglesRelHFProgressionRad = math.EulerAngles_YXZ(RightEForefootAnat, RightEHFProgression)
            RightHalluxAnglesRelHFProgressionRad = math.EulerAngles_YXZ(RightEHalluxAnat, RightEHFProgression)
        LeftHipAnglesRad = math.EulerAngles_YXZ(LeftEThighAnat, EPelvisAnat)
        RightHipAnglesRad = math.EulerAngles_YXZ(RightEThighAnat, EPelvisAnat)
        LeftKneeAnglesProximalRad = math.EulerAngles_YXZ(LeftEShankProximalAnat, LeftEThighAnat)
        RightKneeAnglesProximalRad = math.EulerAngles_YXZ(RightEShankProximalAnat, RightEThighAnat)
        LeftKneeAnglesDistalRad = math.EulerAngles_YXZ(LeftEShankDistalAnat, LeftEThighAnat)
        RightKneeAnglesDistalRad = math.EulerAngles_YXZ(RightEShankDistalAnat, RightEThighAnat)
        if self.ShankCoordinateSystem == 'Distal':
            LeftKneeAnglesRad = math.EulerAngles_YXZ(LeftEShankDistalAnat, LeftEThighAnat)
            RightKneeAnglesRad = math.EulerAngles_YXZ(RightEShankDistalAnat, RightEThighAnat)
        if self.ShankCoordinateSystem == 'Proximal':
            LeftKneeAnglesRad = math.EulerAngles_YXZ(LeftEShankProximalAnat, LeftEThighAnat)
            RightKneeAnglesRad = math.EulerAngles_YXZ(RightEShankProximalAnat, RightEThighAnat)
        LeftAnkleAnglesRad = math.EulerAngles_YXZ(LeftEFootAnat, LeftEShankDistalAnat)
        RightAnkleAnglesRad = math.EulerAngles_YXZ(RightEFootAnat, RightEShankDistalAnat)
        if self.valueLeftFootModelCheck == '1':
            LeftAnkleComplexAnglesRad = math.EulerAngles_YXZ(LeftEHindfootAnat, LeftEShankDistalAnat)
            LeftMidfootAnglesRad = math.EulerAngles_YXZ(LeftEForefootAnat, LeftEHindfootAnat)
            LeftToesAnglesRad = (
                np.where(np.logical_not(LeftHalluxMarker[..., 2] == 0)[..., None],
                math.EulerAngles_YXZ(LeftEHalluxAnat, LeftEForefootAnat), 0.0)
            )
        if self.valueRightFootModelCheck == '1':
            RightAnkleComplexAnglesRad = math.EulerAngles_YXZ(RightEHindfootAnat, RightEShankDistalAnat)
            RightMidfootAnglesRad = math.EulerAngles_YXZ(RightEForefootAnat, RightEHindfootAnat)
            RightToesAnglesRad = math.EulerAngles_YXZ(RightEHalluxAnat, RightEForefootAnat)
            RightToesAnglesRad = (
                np.where(np.logical_not(RightHalluxMarker[..., 2] == 0)[..., None],
                math.EulerAngles_YXZ(RightEHalluxAnat, RightEForefootAnat), 0.0)
            )
        Sign = -1
        T1, T1[..., 0, 0], T1[..., 1, 1], T1[..., 2, 2] = (np.eye(3), -Sign, +1, Sign)
        T2, T2[..., 0, 0], T2[..., 1, 1], T2[..., 2, 2] = (np.eye(3), Sign, -1, Sign)
        T3, T3[..., 0, 0], T3[..., 1, 1], T3[..., 2, 2] = (np.eye(3), Sign, +1, Sign)
        LeftTrunkAnglesDeg = math.TransformVectorIntoLabCoors(TrunkAnglesRad, T1) * 180 / np.pi
        LeftTrunkAnglesTORDeg = math.TransformVectorIntoLabCoors(TrunkAnglesTORRad, T1) * 180 / np.pi
        LeftTrunkAnglesROTDeg = math.TransformVectorIntoLabCoors(TrunkAnglesROTRad, T1) * 180 / np.pi
        LeftPelvisAnglesDeg = math.TransformVectorIntoLabCoors(PelvisAnglesRad, T1) * 180 / np.pi
        LeftPelvisAnglesTORDeg = math.TransformVectorIntoLabCoors(PelvisAnglesTORRad, T1) * 180 / np.pi
        LeftPelvisAnglesROTDeg = math.TransformVectorIntoLabCoors(PelvisAnglesROTRad, T1) * 180 / np.pi
        LeftThighAnglesDeg = math.TransformVectorIntoLabCoors(LeftThighAnglesRad, T1) * 180 / np.pi
        LeftShankAnglesDeg = math.TransformVectorIntoLabCoors(LeftShankAnglesRad, T1) * 180 / np.pi
        LeftFootAnglesDeg = math.TransformVectorIntoLabCoors(LeftFootAnglesRad, T1) * 180 / np.pi
        LeftHipAnglesDeg = math.TransformVectorIntoLabCoors(LeftHipAnglesRad, T2) * 180 / np.pi
        LeftKneeAnglesDeg = math.TransformVectorIntoLabCoors(LeftKneeAnglesRad, T3) * 180 / np.pi
        LeftKneeAnglesProximalDeg = math.TransformVectorIntoLabCoors(LeftKneeAnglesProximalRad, T3) * 180 / np.pi
        LeftKneeAnglesDistalDeg = math.TransformVectorIntoLabCoors(LeftKneeAnglesDistalRad, T3) * 180 / np.pi
        LeftAnkleAnglesDeg = math.TransformVectorIntoLabCoors(LeftAnkleAnglesRad, T2) * 180 / np.pi
        if self.valueLeftFootModelCheck == '1':
            LeftHindfootAnglesDeg = math.TransformVectorIntoLabCoors(LeftHindfootAnglesRad, T1) * 180 / np.pi
            LeftForefootAnglesDeg = math.TransformVectorIntoLabCoors(LeftForefootAnglesRad, T1) * 180 / np.pi
            LeftHalluxAnglesDeg = math.TransformVectorIntoLabCoors(LeftHalluxAnglesRad, T1) * 180 / np.pi
            LeftHindfootAnglesRelHFProgressionDeg = math.TransformVectorIntoLabCoors(LeftHindfootAnglesRelHFProgressionRad, T2) * 180 / np.pi
            LeftForefootAnglesRelHFProgressionDeg = math.TransformVectorIntoLabCoors(LeftForefootAnglesRelHFProgressionRad, T2) * 180 / np.pi
            LeftHalluxAnglesRelHFProgressionDeg = math.TransformVectorIntoLabCoors(LeftHalluxAnglesRelHFProgressionRad, T2) * 180 / np.pi
            LeftAnkleComplexAnglesDeg = math.TransformVectorIntoLabCoors(LeftAnkleComplexAnglesRad, T2) * 180 / np.pi
            LeftMidfootAnglesDeg = math.TransformVectorIntoLabCoors(LeftMidfootAnglesRad, T2) * 180 / np.pi
            LeftToesAnglesDeg = math.TransformVectorIntoLabCoors(LeftToesAnglesRad, T2) * 180 / np.pi
        T1, T2, T3 = (np.eye(3), np.eye(3), np.eye(3))
        LeftTrunkAnglesRad = math.TransformVectorIntoLabCoors(TrunkAnglesRad, T1)
        LeftPelvisAnglesRad = math.TransformVectorIntoLabCoors(PelvisAnglesRad, T1)
        LeftThighAnglesRad = math.TransformVectorIntoLabCoors(LeftThighAnglesRad, T1)
        LeftShankAnglesRad = math.TransformVectorIntoLabCoors(LeftShankAnglesRad, T1)
        LeftFootAnglesRad = math.TransformVectorIntoLabCoors(LeftFootAnglesRad, T1)
        LeftHipAnglesRad = math.TransformVectorIntoLabCoors(LeftHipAnglesRad, T2)
        LeftKneeAnglesRad = math.TransformVectorIntoLabCoors(LeftKneeAnglesRad, T3)
        LeftAnkleAnglesRad = math.TransformVectorIntoLabCoors(LeftAnkleAnglesRad, T2)
        Sign = 1
        T1, T1[..., 0, 0], T1[..., 1, 1], T1[..., 2, 2] = (np.eye(3), -Sign, +1, Sign)
        T2, T2[..., 0, 0], T2[..., 1, 1], T2[..., 2, 2] = (np.eye(3), Sign, -1, Sign)
        T3, T3[..., 0, 0], T3[..., 1, 1], T3[..., 2, 2] = (np.eye(3), Sign, +1, Sign)
        RightTrunkAnglesDeg = math.TransformVectorIntoLabCoors(TrunkAnglesRad, T1) * 180 / np.pi
        RightTrunkAnglesTORDeg = math.TransformVectorIntoLabCoors(TrunkAnglesTORRad, T1) * 180 / np.pi
        RightTrunkAnglesROTDeg = math.TransformVectorIntoLabCoors(TrunkAnglesROTRad, T1) * 180 / np.pi
        RightPelvisAnglesDeg = math.TransformVectorIntoLabCoors(PelvisAnglesRad, T1) * 180 / np.pi
        RightPelvisAnglesTORDeg = math.TransformVectorIntoLabCoors(PelvisAnglesTORRad, T1) * 180 / np.pi
        RightPelvisAnglesROTDeg = math.TransformVectorIntoLabCoors(PelvisAnglesROTRad, T1) * 180 / np.pi
        RightThighAnglesDeg = math.TransformVectorIntoLabCoors(RightThighAnglesRad, T1) * 180 / np.pi
        RightShankAnglesDeg = math.TransformVectorIntoLabCoors(RightShankAnglesRad, T1) * 180 / np.pi
        RightFootAnglesDeg = math.TransformVectorIntoLabCoors(RightFootAnglesRad, T1) * 180 / np.pi
        RightHipAnglesDeg = math.TransformVectorIntoLabCoors(RightHipAnglesRad, T2) * 180 / np.pi
        RightKneeAnglesDeg = math.TransformVectorIntoLabCoors(RightKneeAnglesRad, T3) * 180 / np.pi
        RightKneeAnglesProximalDeg = math.TransformVectorIntoLabCoors(RightKneeAnglesProximalRad, T3) * 180 / np.pi
        RightKneeAnglesDistalDeg = math.TransformVectorIntoLabCoors(RightKneeAnglesDistalRad, T3) * 180 / np.pi
        RightAnkleAnglesDeg = math.TransformVectorIntoLabCoors(RightAnkleAnglesRad, T2) * 180 / np.pi
        if self.valueRightFootModelCheck == '1':
            RightHindfootAnglesDeg = math.TransformVectorIntoLabCoors(RightHindfootAnglesRad, T1) * 180 / np.pi
            RightForefootAnglesDeg = math.TransformVectorIntoLabCoors(RightForefootAnglesRad, T1) * 180 / np.pi
            RightHalluxAnglesDeg = math.TransformVectorIntoLabCoors(RightHalluxAnglesRad, T1) * 180 / np.pi
            RightHindfootAnglesRelHFProgressionDeg = math.TransformVectorIntoLabCoors(RightHindfootAnglesRelHFProgressionRad, T2) * 180 / np.pi
            RightForefootAnglesRelHFProgressionDeg = math.TransformVectorIntoLabCoors(RightForefootAnglesRelHFProgressionRad, T2) * 180 / np.pi
            RightHalluxAnglesRelHFProgressionDeg = math.TransformVectorIntoLabCoors(RightHalluxAnglesRelHFProgressionRad, T2) * 180 / np.pi
            RightAnkleComplexAnglesDeg = math.TransformVectorIntoLabCoors(RightAnkleComplexAnglesRad, T2) * 180 / np.pi
            RightMidfootAnglesDeg = math.TransformVectorIntoLabCoors(RightMidfootAnglesRad, T2) * 180 / np.pi
            RightToesAnglesDeg = math.TransformVectorIntoLabCoors(RightToesAnglesRad, T2) * 180 / np.pi
        T1, T2, T3 = (np.eye(3), np.eye(3), np.eye(3))
        RightTrunkAnglesRad = math.TransformVectorIntoLabCoors(TrunkAnglesRad, T1)
        RightPelvisAnglesRad = math.TransformVectorIntoLabCoors(PelvisAnglesRad, T1)
        RightThighAnglesRad = math.TransformVectorIntoLabCoors(RightThighAnglesRad, T1)
        RightShankAnglesRad = math.TransformVectorIntoLabCoors(RightShankAnglesRad, T1)
        RightFootAnglesRad = math.TransformVectorIntoLabCoors(RightFootAnglesRad, T1)
        RightHipAnglesRad = math.TransformVectorIntoLabCoors(RightHipAnglesRad, T2)
        RightKneeAnglesRad = math.TransformVectorIntoLabCoors(RightKneeAnglesRad, T3)
        RightAnkleAnglesRad = math.TransformVectorIntoLabCoors(RightAnkleAnglesRad, T2)
        # Muscle polynomials and attachment masks are evaluated over all frames.
        LKF = LeftKneeAnglesProximalDeg[..., 1]
        RKF = RightKneeAnglesProximalDeg[..., 1]
        LeftKneeX = KneeX0 + KneeX1 * LKF + KneeX2 * LKF * LKF + KneeX3 * LKF * LKF * LKF
        RightKneeX = KneeX0 + KneeX1 * RKF + KneeX2 * RKF * RKF + KneeX3 * RKF * RKF * RKF
        LeftKneeZ = KneeZ0 + KneeZ1 * LKF + KneeZ2 * LKF * LKF + KneeZ3 * LKF * LKF * LKF
        RightKneeZ = KneeZ0 + KneeZ1 * RKF + KneeZ2 * RKF * RKF + KneeZ3 * RKF * RKF * RKF
        LeftDelpKJC_Polynomial = math.FrameVector(_batch_count, LeftKneeX, 0, LeftKneeZ)
        RightDelpKJC_Polynomial = math.FrameVector(_batch_count, RightKneeX, 0, RightKneeZ)
        LeftPatX = PatX0 + PatX1 * LKF + PatX2 * LKF * LKF + PatX3 * LKF * LKF * LKF
        RightPatX = PatX0 + PatX1 * RKF + PatX2 * RKF * RKF + PatX3 * RKF * RKF * RKF
        LeftPatZ = PatZ0 + PatZ1 * LKF + PatZ2 * LKF * LKF + PatZ3 * LKF * LKF * LKF
        RightPatZ = PatZ0 + PatZ1 * RKF + PatZ2 * RKF * RKF + PatZ3 * RKF * RKF * RKF
        LeftPatR = PatR0 + PatR1 * LKF + PatR2 * LKF * LKF + PatR3 * LKF * LKF * LKF
        RightPatR = PatR0 + PatR1 * RKF + PatR2 * RKF * RKF + PatR3 * RKF * RKF * RKF
        [EPelvisAnatDelp, MidASISLab] = gait.AnatCS_Pelvis_Delp(LeftASISMarker, RightASISMarker, SacralMarker, PelvicTiltOffset)
        LeftEThighAnatDelp = LeftEThighAnat
        RightEThighAnatDelp = RightEThighAnat
        LeftEShankAnatDelp = LeftEShankProximalAnat
        RightEShankAnatDelp = RightEShankProximalAnat
        LeftEPatellaAnatDelp = LeftEShankAnatDelp
        RightEPatellaAnatDelp = RightEShankAnatDelp
        LeftEPatellaAnatDelp = math.RotateCSaroundYaxis(LeftEPatellaAnatDelp, LeftPatR)
        RightEPatellaAnatDelp = math.RotateCSaroundYaxis(RightEPatellaAnatDelp, RightPatR)
        LeftECalcaneusAnatDelp = LeftEFootAnat
        RightECalcaneusAnatDelp = RightEFootAnat
        PelvisOriginDelp = math.FrameVector(_batch_count, MidASISLab[..., 0], MidASISLab[..., 1] + 1000.0, 949.0)
        LeftThighOriginDelp = math.TransformPointIntoLabCoors(DelpLeftHJC, EPelvisAnatDelp, PelvisOriginDelp)
        RightThighOriginDelp = math.TransformPointIntoLabCoors(DelpRightHJC, EPelvisAnatDelp, PelvisOriginDelp)
        LeftShankOriginDelp = math.TransformPointIntoLabCoors(LeftDelpKJC_Polynomial, LeftEThighAnatDelp, LeftThighOriginDelp)
        RightShankOriginDelp = math.TransformPointIntoLabCoors(RightDelpKJC_Polynomial, RightEThighAnatDelp, RightThighOriginDelp)
        LeftPatellaOriginDelp = (
            math.TransformPointIntoLabCoors(math.FrameVector(_batch_count, LeftPatX, -PatY, LeftPatZ),
            LeftEShankAnatDelp, LeftShankOriginDelp)
        )
        RightPatellaOriginDelp = (
            math.TransformPointIntoLabCoors(math.FrameVector(_batch_count, RightPatX, PatY, RightPatZ),
            RightEShankAnatDelp, RightShankOriginDelp)
        )
        LeftCalcaneusOriginDelp_AJC = math.TransformPointIntoLabCoors(DelpAJC, LeftEShankAnatDelp, LeftShankOriginDelp)
        RightCalcaneusOriginDelp_AJC = math.TransformPointIntoLabCoors(DelpAJC, RightEShankAnatDelp, RightShankOriginDelp)
        LeftCalcaneusOriginDelp = math.TransformPointIntoLabCoors(LCalC, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp_AJC)
        RightCalcaneusOriginDelp = math.TransformPointIntoLabCoors(RCalC, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp_AJC)
        ELabDelp = np.eye(3)
        EPelvisAnatDelp0 = ELabDelp
        LeftEThighAnatDelp0 = ELabDelp
        RightEThighAnatDelp0 = ELabDelp
        LeftEShankAnatDelp0 = ELabDelp
        RightEShankAnatDelp0 = ELabDelp
        LeftECalcaneusAnatDelp0 = ELabDelp
        RightECalcaneusAnatDelp0 = ELabDelp
        LeftEPatellaAnatDelp0 = ELabDelp
        RightEPatellaAnatDelp0 = ELabDelp
        LeftECalcaneusAnatDelp0 = math.RotateCSaroundZaxis(ELabDelp, 15.0)
        RightECalcaneusAnatDelp0 = math.RotateCSaroundZaxis(ELabDelp, -15.0)
        LeftEPatellaAnatDelp0 = math.RotateCSaroundYaxis(ELabDelp, PatR0)
        RightEPatellaAnatDelp0 = math.RotateCSaroundYaxis(ELabDelp, PatR0)
        PelvisOriginDelp0 = PelvisOriginDelp
        LeftThighOriginDelp0 = PelvisOriginDelp + DelpLeftHJC
        RightThighOriginDelp0 = PelvisOriginDelp + DelpRightHJC
        LeftShankOriginDelp0 = PelvisOriginDelp + DelpLeftHJC + DelpKJC0
        RightShankOriginDelp0 = PelvisOriginDelp + DelpRightHJC + DelpKJC0
        LeftPatellaOriginDelp0 = PelvisOriginDelp + DelpLeftHJC + DelpKJC0 + DelpLPat0
        RightPatellaOriginDelp0 = PelvisOriginDelp + DelpRightHJC + DelpKJC0 + DelpRPat0
        LeftCalcaneusOriginDelp0 = PelvisOriginDelp + DelpLeftHJC + DelpKJC0 + DelpAJC + LCalC
        RightCalcaneusOriginDelp0 = PelvisOriginDelp + DelpRightHJC + DelpKJC0 + DelpAJC + RCalC
        [LeftGMaS, LeftGMaSMusclePoints] = (
            math.ComputeMuscleLength('Left', GMaS, GMaS_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp)
        )
        [RightGMaS, RightGMaSMusclePoints] = (
            math.ComputeMuscleLength('Right', GMaS, GMaS_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp)
        )
        [LeftGMaS0, LeftGMaSMusclePoints0] = (
            math.ComputeMuscleLength('Left', GMaS, GMaS_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightGMaS0, RightGMaSMusclePoints0] = (
            math.ComputeMuscleLength('Right', GMaS, GMaS_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        [LeftGMaM, LeftGMaMMusclePoints] = (
            math.ComputeMuscleLength('Left', GMaM, GMaM_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp)
        )
        [RightGMaM, RightGMaMMusclePoints] = (
            math.ComputeMuscleLength('Right', GMaM, GMaM_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp)
        )
        [LeftGMaM0, LeftGMaMMusclePoints0] = (
            math.ComputeMuscleLength('Left', GMaM, GMaM_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightGMaM0, RightGMaMMusclePoints0] = (
            math.ComputeMuscleLength('Right', GMaM, GMaM_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        [LeftGMaI, LeftGMaIMusclePoints] = (
            math.ComputeMuscleLength('Left', GMaI, GMaI_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp)
        )
        [RightGMaI, RightGMaIMusclePoints] = (
            math.ComputeMuscleLength('Right', GMaI, GMaI_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp)
        )
        [LeftGMaI0, LeftGMaIMusclePoints0] = (
            math.ComputeMuscleLength('Left', GMaI, GMaI_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightGMaI0, RightGMaIMusclePoints0] = (
            math.ComputeMuscleLength('Right', GMaI, GMaI_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        [LeftIlia, LeftIliaMusclePoints] = (
            math.ComputeMuscleLength('Left', Ilia, Ilia_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp)
        )
        [RightIlia, RightIliaMusclePoints] = (
            math.ComputeMuscleLength('Right', Ilia, Ilia_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp)
        )
        [LeftIlia0, LeftIliaMusclePoints0] = (
            math.ComputeMuscleLength('Left', Ilia, Ilia_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightIlia0, RightIliaMusclePoints0] = (
            math.ComputeMuscleLength('Right', Ilia, Ilia_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        [LeftPsoa, LeftPsoaMusclePoints] = (
            math.ComputeMuscleLength('Left', Psoa, Psoa_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp)
        )
        [RightPsoa, RightPsoaMusclePoints] = (
            math.ComputeMuscleLength('Right', Psoa, Psoa_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp)
        )
        [LeftPsoa0, LeftPsoaMusclePoints0] = (
            math.ComputeMuscleLength('Left', Psoa, Psoa_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightPsoa0, RightPsoaMusclePoints0] = (
            math.ComputeMuscleLength('Right', Psoa, Psoa_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        [LeftSeMe, LeftSeMeMusclePoints] = (
            math.ComputeMuscleLength('Left', SeMe, SeMe_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp)
        )
        [RightSeMe, RightSeMeMusclePoints] = (
            math.ComputeMuscleLength('Right', SeMe, SeMe_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp)
        )
        [LeftSeMe0, LeftSeMeMusclePoints0] = (
            math.ComputeMuscleLength('Left', SeMe, SeMe_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightSeMe0, RightSeMeMusclePoints0] = (
            math.ComputeMuscleLength('Right', SeMe, SeMe_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        [LeftSeTe, LeftSeTeMusclePoints] = (
            math.ComputeMuscleLength('Left', SeTe, SeTe_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp)
        )
        [RightSeTe, RightSeTeMusclePoints] = (
            math.ComputeMuscleLength('Right', SeTe, SeTe_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp)
        )
        [LeftSeTe0, LeftSeTeMusclePoints0] = (
            math.ComputeMuscleLength('Left', SeTe, SeTe_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightSeTe0, RightSeTeMusclePoints0] = (
            math.ComputeMuscleLength('Right', SeTe, SeTe_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        [LeftBiFL, LeftBiFLMusclePoints] = (
            math.ComputeMuscleLength('Left', BiFL, BiFL_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp)
        )
        [RightBiFL, RightBiFLMusclePoints] = (
            math.ComputeMuscleLength('Right', BiFL, BiFL_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp)
        )
        [LeftBiFL0, LeftBiFLMusclePoints0] = (
            math.ComputeMuscleLength('Left', BiFL, BiFL_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightBiFL0, RightBiFLMusclePoints0] = (
            math.ComputeMuscleLength('Right', BiFL, BiFL_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        [LeftBiFS, LeftBiFSMusclePoints] = (
            math.ComputeMuscleLength('Left', BiFS, BiFS_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp)
        )
        [RightBiFS, RightBiFSMusclePoints] = (
            math.ComputeMuscleLength('Right', BiFS, BiFS_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp)
        )
        [LeftBiFS0, LeftBiFSMusclePoints0] = (
            math.ComputeMuscleLength('Left', BiFS, BiFS_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightBiFS0, RightBiFSMusclePoints0] = (
            math.ComputeMuscleLength('Right', BiFS, BiFS_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        [LeftSole, LeftSoleMusclePoints] = (
            math.ComputeMuscleLength('Left', Sole, Sole_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp)
        )
        [RightSole, RightSoleMusclePoints] = (
            math.ComputeMuscleLength('Right', Sole, Sole_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp)
        )
        [LeftSole0, LeftSoleMusclePoints0] = (
            math.ComputeMuscleLength('Left', Sole, Sole_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightSole0, RightSoleMusclePoints0] = (
            math.ComputeMuscleLength('Right', Sole, Sole_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        [LeftTiPo, LeftTiPoMusclePoints] = (
            math.ComputeMuscleLength('Left', TiPo, TiPo_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp)
        )
        [RightTiPo, RightTiPoMusclePoints] = (
            math.ComputeMuscleLength('Right', TiPo, TiPo_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp)
        )
        [LeftTiPo0, LeftTiPoMusclePoints0] = (
            math.ComputeMuscleLength('Left', TiPo, TiPo_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightTiPo0, RightTiPoMusclePoints0] = (
            math.ComputeMuscleLength('Right', TiPo, TiPo_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        [LeftPeBr, LeftPeBrMusclePoints] = (
            math.ComputeMuscleLength('Left', PeBr, PeBr_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp)
        )
        [RightPeBr, RightPeBrMusclePoints] = (
            math.ComputeMuscleLength('Right', PeBr, PeBr_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp)
        )
        [LeftPeBr0, LeftPeBrMusclePoints0] = (
            math.ComputeMuscleLength('Left', PeBr, PeBr_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightPeBr0, RightPeBrMusclePoints0] = (
            math.ComputeMuscleLength('Right', PeBr, PeBr_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        [LeftPeLn, LeftPeLnMusclePoints] = (
            math.ComputeMuscleLength('Left', PeLn, PeLn_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp)
        )
        [RightPeLn, RightPeLnMusclePoints] = (
            math.ComputeMuscleLength('Right', PeLn, PeLn_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp)
        )
        [LeftPeLn0, LeftPeLnMusclePoints0] = (
            math.ComputeMuscleLength('Left', PeLn, PeLn_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightPeLn0, RightPeLnMusclePoints0] = (
            math.ComputeMuscleLength('Right', PeLn, PeLn_Seg, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        Left_ReFe = []
        Left_ReFe = ReFe
        Left_ReFe_Seg = ReFe_Seg
        Right_ReFe = []
        Right_ReFe = ReFe
        Right_ReFe_Seg = ReFe_Seg
        Left_ReFe0 = []
        Left_ReFe0.append(ReFe[0])
        Left_ReFe0.append(ReFe[2])
        Left_ReFe_Seg0 = ['Pelvis', 'Patella']
        Right_ReFe0 = []
        Right_ReFe0.append(ReFe[0])
        Right_ReFe0.append(ReFe[2])
        Right_ReFe_Seg0 = ['Pelvis', 'Patella']
        [LeftReFe, LeftReFeMusclePoints] = (
            math.ComputeMuscleLength('Left', Left_ReFe, Left_ReFe_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp,
            active_points=np.column_stack((np.ones(_batch_count, dtype=bool), ~(LKF < 83),
            np.ones(_batch_count, dtype=bool))))
        )
        [RightReFe, RightReFeMusclePoints] = (
            math.ComputeMuscleLength('Right', Right_ReFe, Right_ReFe_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp,
            active_points=np.column_stack((np.ones(_batch_count, dtype=bool), ~(RKF < 83),
            np.ones(_batch_count, dtype=bool))))
        )
        [LeftReFe0, LeftReFeMusclePoints0] = (
            math.ComputeMuscleLength('Left', Left_ReFe0, Left_ReFe_Seg0, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightReFe0, RightReFeMusclePoints0] = (
            math.ComputeMuscleLength('Right', Right_ReFe0, Right_ReFe_Seg0, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        Left_VaLa = []
        Left_VaLa = VaLa
        Left_VaLa_Seg = VaLa_Seg
        Right_VaLa = []
        Right_VaLa = VaLa
        Right_VaLa_Seg = VaLa_Seg
        Left_VaLa0 = []
        Left_VaLa0.append(VaLa[0])
        Left_VaLa0.append(VaLa[1])
        Left_VaLa0.append(VaLa[4])
        Left_VaLa_Seg0 = ['Thigh', 'Thigh', 'Patella']
        Right_VaLa0 = []
        Right_VaLa0.append(VaLa[0])
        Right_VaLa0.append(VaLa[1])
        Right_VaLa0.append(VaLa[4])
        Right_VaLa_Seg0 = ['Thigh', 'Thigh', 'Patella']
        [LeftVaLa, LeftVaLaMusclePoints] = (
            math.ComputeMuscleLength('Left', Left_VaLa, Left_VaLa_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp,
            active_points=np.column_stack((np.ones(_batch_count, dtype=bool), np.ones(_batch_count,
            dtype=bool), ~(LKF < 69), ~(LKF < 110), np.ones(_batch_count, dtype=bool))))
        )
        [RightVaLa, RightVaLaMusclePoints] = (
            math.ComputeMuscleLength('Right', Right_VaLa, Right_VaLa_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp,
            active_points=np.column_stack((np.ones(_batch_count, dtype=bool), np.ones(_batch_count,
            dtype=bool), ~(RKF < 69), ~(RKF < 110), np.ones(_batch_count, dtype=bool))))
        )
        [LeftVaLa0, LeftVaLaMusclePoints0] = (
            math.ComputeMuscleLength('Left', Left_VaLa0, Left_VaLa_Seg0, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightVaLa0, RightVaLaMusclePoints0] = (
            math.ComputeMuscleLength('Right', Right_VaLa0, Right_VaLa_Seg0, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        Left_GaMe = []
        Left_GaMe = GaMe
        Left_GaMe_Seg = GaMe_Seg
        Right_GaMe = []
        Right_GaMe = GaMe
        Right_GaMe_Seg = GaMe_Seg
        Left_GaMe0 = GaMe
        Left_GaMe_Seg0 = GaMe_Seg
        Right_GaMe0 = GaMe
        Right_GaMe_Seg0 = GaMe_Seg
        [LeftGaMe, LeftGaMeMusclePoints] = (
            math.ComputeMuscleLength('Left', Left_GaMe, Left_GaMe_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp,
            active_points=np.column_stack((np.ones(_batch_count, dtype=bool), ~(LKF > 44),
            np.ones(_batch_count, dtype=bool), np.ones(_batch_count, dtype=bool))))
        )
        [RightGaMe, RightGaMeMusclePoints] = (
            math.ComputeMuscleLength('Right', Right_GaMe, Right_GaMe_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp,
            active_points=np.column_stack((np.ones(_batch_count, dtype=bool), ~(RKF > 44),
            np.ones(_batch_count, dtype=bool), np.ones(_batch_count, dtype=bool))))
        )
        [LeftGaMe0, LeftGaMeMusclePoints0] = (
            math.ComputeMuscleLength('Left', Left_GaMe0, Left_GaMe_Seg0, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightGaMe0, RightGaMeMusclePoints0] = (
            math.ComputeMuscleLength('Right', Right_GaMe0, Right_GaMe_Seg0, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        Left_GaLa = []
        Left_GaLa = GaLa
        Left_GaLa_Seg = GaLa_Seg
        Right_GaLa = []
        Right_GaLa = GaLa
        Right_GaLa_Seg = GaLa_Seg
        Left_GaLa0 = GaLa
        Left_GaLa_Seg0 = GaLa_Seg
        Right_GaLa0 = GaLa
        Right_GaLa_Seg0 = GaLa_Seg
        [LeftGaLa, LeftGaLaMusclePoints] = (
            math.ComputeMuscleLength('Left', Left_GaLa, Left_GaLa_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            LeftEThighAnatDelp, LeftThighOriginDelp, LeftEShankAnatDelp, LeftShankOriginDelp,
            LeftEPatellaAnatDelp, LeftPatellaOriginDelp, LeftECalcaneusAnatDelp, LeftCalcaneusOriginDelp,
            active_points=np.column_stack((np.ones(_batch_count, dtype=bool), ~(LKF > 44),
            np.ones(_batch_count, dtype=bool), np.ones(_batch_count, dtype=bool))))
        )
        [RightGaLa, RightGaLaMusclePoints] = (
            math.ComputeMuscleLength('Right', Right_GaLa, Right_GaLa_Seg, EPelvisAnatDelp, PelvisOriginDelp,
            RightEThighAnatDelp, RightThighOriginDelp, RightEShankAnatDelp, RightShankOriginDelp,
            RightEPatellaAnatDelp, RightPatellaOriginDelp, RightECalcaneusAnatDelp, RightCalcaneusOriginDelp,
            active_points=np.column_stack((np.ones(_batch_count, dtype=bool), ~(RKF > 44),
            np.ones(_batch_count, dtype=bool), np.ones(_batch_count, dtype=bool))))
        )
        [LeftGaLa0, LeftGaLaMusclePoints0] = (
            math.ComputeMuscleLength('Left', Left_GaLa0, Left_GaLa_Seg0, EPelvisAnatDelp0, PelvisOriginDelp0,
            LeftEThighAnatDelp0, LeftThighOriginDelp0, LeftEShankAnatDelp0, LeftShankOriginDelp0,
            LeftEPatellaAnatDelp0, LeftPatellaOriginDelp0, LeftECalcaneusAnatDelp0, LeftCalcaneusOriginDelp0)
        )
        [RightGaLa0, RightGaLaMusclePoints0] = (
            math.ComputeMuscleLength('Right', Right_GaLa0, Right_GaLa_Seg0, EPelvisAnatDelp0, PelvisOriginDelp0,
            RightEThighAnatDelp0, RightThighOriginDelp0, RightEShankAnatDelp0, RightShankOriginDelp0,
            RightEPatellaAnatDelp0, RightPatellaOriginDelp0, RightECalcaneusAnatDelp0,
            RightCalcaneusOriginDelp0)
        )
        arrayLeftHipCenter[0][_batch_slice] = np.broadcast_to(Direction * LeftHipCenterLab[..., 0], (_batch_count,))
        arrayLeftHipCenter[1][_batch_slice] = np.broadcast_to(Direction * LeftHipCenterLab[..., 1], (_batch_count,))
        arrayLeftHipCenter[2][_batch_slice] = np.broadcast_to(LeftHipCenterLab[..., 2], (_batch_count,))
        arrayRightHipCenter[0][_batch_slice] = np.broadcast_to(Direction * RightHipCenterLab[..., 0], (_batch_count,))
        arrayRightHipCenter[1][_batch_slice] = np.broadcast_to(Direction * RightHipCenterLab[..., 1], (_batch_count,))
        arrayRightHipCenter[2][_batch_slice] = np.broadcast_to(RightHipCenterLab[..., 2], (_batch_count,))
        arrayLeftKneeCenter[0][_batch_slice] = np.broadcast_to(Direction * LeftKneeCenterLab[..., 0], (_batch_count,))
        arrayLeftKneeCenter[1][_batch_slice] = np.broadcast_to(Direction * LeftKneeCenterLab[..., 1], (_batch_count,))
        arrayLeftKneeCenter[2][_batch_slice] = np.broadcast_to(LeftKneeCenterLab[..., 2], (_batch_count,))
        arrayRightKneeCenter[0][_batch_slice] = np.broadcast_to(Direction * RightKneeCenterLab[..., 0], (_batch_count,))
        arrayRightKneeCenter[1][_batch_slice] = np.broadcast_to(Direction * RightKneeCenterLab[..., 1], (_batch_count,))
        arrayRightKneeCenter[2][_batch_slice] = np.broadcast_to(RightKneeCenterLab[..., 2], (_batch_count,))
        arrayLeftAnkleCenter[0][_batch_slice] = np.broadcast_to(Direction * LeftAnkleCenterLab[..., 0], (_batch_count,))
        arrayLeftAnkleCenter[1][_batch_slice] = np.broadcast_to(Direction * LeftAnkleCenterLab[..., 1], (_batch_count,))
        arrayLeftAnkleCenter[2][_batch_slice] = np.broadcast_to(LeftAnkleCenterLab[..., 2], (_batch_count,))
        arrayRightAnkleCenter[0][_batch_slice] = np.broadcast_to(Direction * RightAnkleCenterLab[..., 0], (_batch_count,))
        arrayRightAnkleCenter[1][_batch_slice] = np.broadcast_to(Direction * RightAnkleCenterLab[..., 1], (_batch_count,))
        arrayRightAnkleCenter[2][_batch_slice] = np.broadcast_to(RightAnkleCenterLab[..., 2], (_batch_count,))
        arrayLeftASIS[0][_batch_slice] = np.broadcast_to(Direction * LeftASISMarker[..., 0], (_batch_count,))
        arrayLeftASIS[1][_batch_slice] = np.broadcast_to(Direction * LeftASISMarker[..., 1], (_batch_count,))
        arrayLeftASIS[2][_batch_slice] = np.broadcast_to(LeftASISMarker[..., 2], (_batch_count,))
        arrayRightASIS[0][_batch_slice] = np.broadcast_to(Direction * RightASISMarker[..., 0], (_batch_count,))
        arrayRightASIS[1][_batch_slice] = np.broadcast_to(Direction * RightASISMarker[..., 1], (_batch_count,))
        arrayRightASIS[2][_batch_slice] = np.broadcast_to(RightASISMarker[..., 2], (_batch_count,))
        arrayLeftKNE[0][_batch_slice] = np.broadcast_to(Direction * LeftLateralKneeMarker[..., 0], (_batch_count,))
        arrayLeftKNE[1][_batch_slice] = np.broadcast_to(Direction * LeftLateralKneeMarker[..., 1], (_batch_count,))
        arrayLeftKNE[2][_batch_slice] = np.broadcast_to(LeftLateralKneeMarker[..., 2], (_batch_count,))
        arrayRightKNE[0][_batch_slice] = np.broadcast_to(Direction * RightLateralKneeMarker[..., 0], (_batch_count,))
        arrayRightKNE[1][_batch_slice] = np.broadcast_to(Direction * RightLateralKneeMarker[..., 1], (_batch_count,))
        arrayRightKNE[2][_batch_slice] = np.broadcast_to(RightLateralKneeMarker[..., 2], (_batch_count,))
        arrayLeftANK[0][_batch_slice] = np.broadcast_to(Direction * LeftLateralAnkleMarker[..., 0], (_batch_count,))
        arrayLeftANK[1][_batch_slice] = np.broadcast_to(Direction * LeftLateralAnkleMarker[..., 1], (_batch_count,))
        arrayLeftANK[2][_batch_slice] = np.broadcast_to(LeftLateralAnkleMarker[..., 2], (_batch_count,))
        arrayRightANK[0][_batch_slice] = np.broadcast_to(Direction * RightLateralAnkleMarker[..., 0], (_batch_count,))
        arrayRightANK[1][_batch_slice] = np.broadcast_to(Direction * RightLateralAnkleMarker[..., 1], (_batch_count,))
        arrayRightANK[2][_batch_slice] = np.broadcast_to(RightLateralAnkleMarker[..., 2], (_batch_count,))
        if self.valueLeftFootModelCheck == '1':
            arrayLeftUpperPCAL[0][_batch_slice] = np.broadcast_to(Direction * LeftUpperPosteriorCalcaneusMarker[..., 0], (_batch_count,))
            arrayLeftUpperPCAL[1][_batch_slice] = np.broadcast_to(Direction * LeftUpperPosteriorCalcaneusMarker[..., 1], (_batch_count,))
            arrayLeftUpperPCAL[2][_batch_slice] = np.broadcast_to(LeftUpperPosteriorCalcaneusMarker[..., 2], (_batch_count,))
        if self.valueRightFootModelCheck == '1':
            arrayRightUpperPCAL[0][_batch_slice] = np.broadcast_to(Direction * RightUpperPosteriorCalcaneusMarker[..., 0], (_batch_count,))
            arrayRightUpperPCAL[1][_batch_slice] = np.broadcast_to(Direction * RightUpperPosteriorCalcaneusMarker[..., 1], (_batch_count,))
            arrayRightUpperPCAL[2][_batch_slice] = np.broadcast_to(RightUpperPosteriorCalcaneusMarker[..., 2], (_batch_count,))
        arrayPelvisOrigin[0][_batch_slice] = (
            np.broadcast_to((np.asarray(arrayLeftHipCenter[0])[_batch_slice] +
            np.asarray(arrayRightHipCenter[0])[_batch_slice]) / 2, (_batch_count,))
        )
        arrayPelvisOrigin[1][_batch_slice] = (
            np.broadcast_to((np.asarray(arrayLeftHipCenter[1])[_batch_slice] +
            np.asarray(arrayRightHipCenter[1])[_batch_slice]) / 2, (_batch_count,))
        )
        arrayPelvisOrigin[2][_batch_slice] = (
            np.broadcast_to((np.asarray(arrayLeftHipCenter[2])[_batch_slice] +
            np.asarray(arrayRightHipCenter[2])[_batch_slice]) / 2, (_batch_count,))
        )
        arrayLeftTrunkAngles[0][_batch_slice] = np.broadcast_to(LeftTrunkAnglesDeg[..., 0], (_batch_count,))
        arrayLeftTrunkAngles[1][_batch_slice] = np.broadcast_to(LeftTrunkAnglesDeg[..., 1], (_batch_count,))
        arrayLeftTrunkAngles[2][_batch_slice] = np.broadcast_to(LeftTrunkAnglesDeg[..., 2], (_batch_count,))
        arrayLeftTrunkAnglesTOR[0][_batch_slice] = np.broadcast_to(LeftTrunkAnglesTORDeg[..., 0], (_batch_count,))
        arrayLeftTrunkAnglesTOR[1][_batch_slice] = np.broadcast_to(LeftTrunkAnglesTORDeg[..., 1], (_batch_count,))
        arrayLeftTrunkAnglesTOR[2][_batch_slice] = np.broadcast_to(LeftTrunkAnglesTORDeg[..., 2], (_batch_count,))
        arrayLeftTrunkAnglesROT[0][_batch_slice] = np.broadcast_to(LeftTrunkAnglesROTDeg[..., 0], (_batch_count,))
        arrayLeftTrunkAnglesROT[1][_batch_slice] = np.broadcast_to(LeftTrunkAnglesROTDeg[..., 1], (_batch_count,))
        arrayLeftTrunkAnglesROT[2][_batch_slice] = np.broadcast_to(LeftTrunkAnglesROTDeg[..., 2], (_batch_count,))
        arrayLeftPelvisAngles[0][_batch_slice] = np.broadcast_to(LeftPelvisAnglesDeg[..., 0], (_batch_count,))
        arrayLeftPelvisAngles[1][_batch_slice] = np.broadcast_to(LeftPelvisAnglesDeg[..., 1], (_batch_count,))
        arrayLeftPelvisAngles[2][_batch_slice] = np.broadcast_to(LeftPelvisAnglesDeg[..., 2], (_batch_count,))
        arrayLeftPelvisAnglesTOR[0][_batch_slice] = np.broadcast_to(LeftPelvisAnglesTORDeg[..., 0], (_batch_count,))
        arrayLeftPelvisAnglesTOR[1][_batch_slice] = np.broadcast_to(LeftPelvisAnglesTORDeg[..., 1], (_batch_count,))
        arrayLeftPelvisAnglesTOR[2][_batch_slice] = np.broadcast_to(LeftPelvisAnglesTORDeg[..., 2], (_batch_count,))
        arrayLeftPelvisAnglesROT[0][_batch_slice] = np.broadcast_to(LeftPelvisAnglesROTDeg[..., 0], (_batch_count,))
        arrayLeftPelvisAnglesROT[1][_batch_slice] = np.broadcast_to(LeftPelvisAnglesROTDeg[..., 1], (_batch_count,))
        arrayLeftPelvisAnglesROT[2][_batch_slice] = np.broadcast_to(LeftPelvisAnglesROTDeg[..., 2], (_batch_count,))
        arrayLeftThighAngles[0][_batch_slice] = np.broadcast_to(LeftThighAnglesDeg[..., 0], (_batch_count,))
        arrayLeftThighAngles[1][_batch_slice] = np.broadcast_to(LeftThighAnglesDeg[..., 1], (_batch_count,))
        arrayLeftThighAngles[2][_batch_slice] = np.broadcast_to(LeftThighAnglesDeg[..., 2], (_batch_count,))
        arrayLeftShankAngles[0][_batch_slice] = np.broadcast_to(LeftShankAnglesDeg[..., 0], (_batch_count,))
        arrayLeftShankAngles[1][_batch_slice] = np.broadcast_to(LeftShankAnglesDeg[..., 1], (_batch_count,))
        arrayLeftShankAngles[2][_batch_slice] = np.broadcast_to(LeftShankAnglesDeg[..., 2], (_batch_count,))
        arrayLeftFootAngles[0][_batch_slice] = np.broadcast_to(LeftFootAnglesDeg[..., 0], (_batch_count,))
        arrayLeftFootAngles[1][_batch_slice] = np.broadcast_to(LeftFootAnglesDeg[..., 1], (_batch_count,))
        arrayLeftFootAngles[2][_batch_slice] = np.broadcast_to(LeftFootAnglesDeg[..., 2], (_batch_count,))
        if self.valueLeftFootModelCheck == '1':
            arrayLeftHindfootAngles[0][_batch_slice] = np.broadcast_to(LeftHindfootAnglesRelHFProgressionDeg[..., 0], (_batch_count,))
            arrayLeftHindfootAngles[1][_batch_slice] = np.broadcast_to(LeftHindfootAnglesRelHFProgressionDeg[..., 1], (_batch_count,))
            arrayLeftHindfootAngles[2][_batch_slice] = np.broadcast_to(LeftHindfootAnglesDeg[..., 2], (_batch_count,))
            arrayLeftForefootAngles[0][_batch_slice] = np.broadcast_to(LeftForefootAnglesRelHFProgressionDeg[..., 0], (_batch_count,))
            arrayLeftForefootAngles[1][_batch_slice] = np.broadcast_to(LeftForefootAnglesRelHFProgressionDeg[..., 1], (_batch_count,))
            arrayLeftForefootAngles[2][_batch_slice] = np.broadcast_to(LeftForefootAnglesDeg[..., 2], (_batch_count,))
            arrayLeftHalluxAngles[0][_batch_slice] = np.broadcast_to(LeftHalluxAnglesRelHFProgressionDeg[..., 0], (_batch_count,))
            arrayLeftHalluxAngles[1][_batch_slice] = np.broadcast_to(LeftHalluxAnglesRelHFProgressionDeg[..., 1], (_batch_count,))
            arrayLeftHalluxAngles[2][_batch_slice] = np.broadcast_to(LeftHalluxAnglesDeg[..., 2], (_batch_count,))
        arrayLeftTrunkAnglesRad[0][_batch_slice] = np.broadcast_to(LeftTrunkAnglesRad[..., 0], (_batch_count,))
        arrayLeftTrunkAnglesRad[1][_batch_slice] = np.broadcast_to(LeftTrunkAnglesRad[..., 1], (_batch_count,))
        arrayLeftTrunkAnglesRad[2][_batch_slice] = np.broadcast_to(LeftTrunkAnglesRad[..., 2], (_batch_count,))
        arrayLeftPelvisAnglesRad[0][_batch_slice] = np.broadcast_to(LeftPelvisAnglesRad[..., 0], (_batch_count,))
        arrayLeftPelvisAnglesRad[1][_batch_slice] = np.broadcast_to(LeftPelvisAnglesRad[..., 1], (_batch_count,))
        arrayLeftPelvisAnglesRad[2][_batch_slice] = np.broadcast_to(LeftPelvisAnglesRad[..., 2], (_batch_count,))
        arrayLeftThighAnglesRad[0][_batch_slice] = np.broadcast_to(LeftThighAnglesRad[..., 0], (_batch_count,))
        arrayLeftThighAnglesRad[1][_batch_slice] = np.broadcast_to(LeftThighAnglesRad[..., 1], (_batch_count,))
        arrayLeftThighAnglesRad[2][_batch_slice] = np.broadcast_to(LeftThighAnglesRad[..., 2], (_batch_count,))
        arrayLeftShankAnglesRad[0][_batch_slice] = np.broadcast_to(LeftShankAnglesRad[..., 0], (_batch_count,))
        arrayLeftShankAnglesRad[1][_batch_slice] = np.broadcast_to(LeftShankAnglesRad[..., 1], (_batch_count,))
        arrayLeftShankAnglesRad[2][_batch_slice] = np.broadcast_to(LeftShankAnglesRad[..., 2], (_batch_count,))
        arrayLeftFootAnglesRad[0][_batch_slice] = np.broadcast_to(LeftFootAnglesRad[..., 0], (_batch_count,))
        arrayLeftFootAnglesRad[1][_batch_slice] = np.broadcast_to(LeftFootAnglesRad[..., 1], (_batch_count,))
        arrayLeftFootAnglesRad[2][_batch_slice] = np.broadcast_to(LeftFootAnglesRad[..., 2], (_batch_count,))
        if self.valueLeftFootModelCheck == '1':
            arrayLeftHindfootAnglesRad[0][_batch_slice] = np.broadcast_to(LeftHindfootAnglesRad[..., 0], (_batch_count,))
            arrayLeftHindfootAnglesRad[1][_batch_slice] = np.broadcast_to(LeftHindfootAnglesRad[..., 1], (_batch_count,))
            arrayLeftHindfootAnglesRad[2][_batch_slice] = np.broadcast_to(LeftHindfootAnglesRad[..., 2], (_batch_count,))
            arrayLeftForefootAnglesRad[0][_batch_slice] = np.broadcast_to(LeftForefootAnglesRad[..., 0], (_batch_count,))
            arrayLeftForefootAnglesRad[1][_batch_slice] = np.broadcast_to(LeftForefootAnglesRad[..., 1], (_batch_count,))
            arrayLeftForefootAnglesRad[2][_batch_slice] = np.broadcast_to(LeftForefootAnglesRad[..., 2], (_batch_count,))
            arrayLeftHalluxAnglesRad[0][_batch_slice] = np.broadcast_to(LeftHalluxAnglesRad[..., 0], (_batch_count,))
            arrayLeftHalluxAnglesRad[1][_batch_slice] = np.broadcast_to(LeftHalluxAnglesRad[..., 1], (_batch_count,))
            arrayLeftHalluxAnglesRad[2][_batch_slice] = np.broadcast_to(LeftHalluxAnglesRad[..., 2], (_batch_count,))
        arrayRightTrunkAngles[0][_batch_slice] = np.broadcast_to(RightTrunkAnglesDeg[..., 0], (_batch_count,))
        arrayRightTrunkAngles[1][_batch_slice] = np.broadcast_to(RightTrunkAnglesDeg[..., 1], (_batch_count,))
        arrayRightTrunkAngles[2][_batch_slice] = np.broadcast_to(RightTrunkAnglesDeg[..., 2], (_batch_count,))
        arrayRightTrunkAnglesTOR[0][_batch_slice] = np.broadcast_to(RightTrunkAnglesTORDeg[..., 0], (_batch_count,))
        arrayRightTrunkAnglesTOR[1][_batch_slice] = np.broadcast_to(RightTrunkAnglesTORDeg[..., 1], (_batch_count,))
        arrayRightTrunkAnglesTOR[2][_batch_slice] = np.broadcast_to(RightTrunkAnglesTORDeg[..., 2], (_batch_count,))
        arrayRightTrunkAnglesROT[0][_batch_slice] = np.broadcast_to(RightTrunkAnglesROTDeg[..., 0], (_batch_count,))
        arrayRightTrunkAnglesROT[1][_batch_slice] = np.broadcast_to(RightTrunkAnglesROTDeg[..., 1], (_batch_count,))
        arrayRightTrunkAnglesROT[2][_batch_slice] = np.broadcast_to(RightTrunkAnglesROTDeg[..., 2], (_batch_count,))
        arrayRightPelvisAngles[0][_batch_slice] = np.broadcast_to(RightPelvisAnglesDeg[..., 0], (_batch_count,))
        arrayRightPelvisAngles[1][_batch_slice] = np.broadcast_to(RightPelvisAnglesDeg[..., 1], (_batch_count,))
        arrayRightPelvisAngles[2][_batch_slice] = np.broadcast_to(RightPelvisAnglesDeg[..., 2], (_batch_count,))
        arrayRightPelvisAnglesTOR[0][_batch_slice] = np.broadcast_to(RightPelvisAnglesTORDeg[..., 0], (_batch_count,))
        arrayRightPelvisAnglesTOR[1][_batch_slice] = np.broadcast_to(RightPelvisAnglesTORDeg[..., 1], (_batch_count,))
        arrayRightPelvisAnglesTOR[2][_batch_slice] = np.broadcast_to(RightPelvisAnglesTORDeg[..., 2], (_batch_count,))
        arrayRightPelvisAnglesROT[0][_batch_slice] = np.broadcast_to(RightPelvisAnglesROTDeg[..., 0], (_batch_count,))
        arrayRightPelvisAnglesROT[1][_batch_slice] = np.broadcast_to(RightPelvisAnglesROTDeg[..., 1], (_batch_count,))
        arrayRightPelvisAnglesROT[2][_batch_slice] = np.broadcast_to(RightPelvisAnglesROTDeg[..., 2], (_batch_count,))
        arrayRightThighAngles[0][_batch_slice] = np.broadcast_to(RightThighAnglesDeg[..., 0], (_batch_count,))
        arrayRightThighAngles[1][_batch_slice] = np.broadcast_to(RightThighAnglesDeg[..., 1], (_batch_count,))
        arrayRightThighAngles[2][_batch_slice] = np.broadcast_to(RightThighAnglesDeg[..., 2], (_batch_count,))
        arrayRightShankAngles[0][_batch_slice] = np.broadcast_to(RightShankAnglesDeg[..., 0], (_batch_count,))
        arrayRightShankAngles[1][_batch_slice] = np.broadcast_to(RightShankAnglesDeg[..., 1], (_batch_count,))
        arrayRightShankAngles[2][_batch_slice] = np.broadcast_to(RightShankAnglesDeg[..., 2], (_batch_count,))
        arrayRightFootAngles[0][_batch_slice] = np.broadcast_to(RightFootAnglesDeg[..., 0], (_batch_count,))
        arrayRightFootAngles[1][_batch_slice] = np.broadcast_to(RightFootAnglesDeg[..., 1], (_batch_count,))
        arrayRightFootAngles[2][_batch_slice] = np.broadcast_to(RightFootAnglesDeg[..., 2], (_batch_count,))
        if self.valueRightFootModelCheck == '1':
            arrayRightHindfootAngles[0][_batch_slice] = np.broadcast_to(RightHindfootAnglesRelHFProgressionDeg[..., 0], (_batch_count,))
            arrayRightHindfootAngles[1][_batch_slice] = np.broadcast_to(RightHindfootAnglesRelHFProgressionDeg[..., 1], (_batch_count,))
            arrayRightHindfootAngles[2][_batch_slice] = np.broadcast_to(RightHindfootAnglesDeg[..., 2], (_batch_count,))
            arrayRightForefootAngles[0][_batch_slice] = np.broadcast_to(RightForefootAnglesRelHFProgressionDeg[..., 0], (_batch_count,))
            arrayRightForefootAngles[1][_batch_slice] = np.broadcast_to(RightForefootAnglesRelHFProgressionDeg[..., 1], (_batch_count,))
            arrayRightForefootAngles[2][_batch_slice] = np.broadcast_to(RightForefootAnglesDeg[..., 2], (_batch_count,))
            arrayRightHalluxAngles[0][_batch_slice] = np.broadcast_to(RightHalluxAnglesRelHFProgressionDeg[..., 0], (_batch_count,))
            arrayRightHalluxAngles[1][_batch_slice] = np.broadcast_to(RightHalluxAnglesRelHFProgressionDeg[..., 1], (_batch_count,))
            arrayRightHalluxAngles[2][_batch_slice] = np.broadcast_to(RightHalluxAnglesDeg[..., 2], (_batch_count,))
        arrayRightTrunkAnglesRad[0][_batch_slice] = np.broadcast_to(RightTrunkAnglesRad[..., 0], (_batch_count,))
        arrayRightTrunkAnglesRad[1][_batch_slice] = np.broadcast_to(RightTrunkAnglesRad[..., 1], (_batch_count,))
        arrayRightTrunkAnglesRad[2][_batch_slice] = np.broadcast_to(RightTrunkAnglesRad[..., 2], (_batch_count,))
        arrayRightPelvisAnglesRad[0][_batch_slice] = np.broadcast_to(RightPelvisAnglesRad[..., 0], (_batch_count,))
        arrayRightPelvisAnglesRad[1][_batch_slice] = np.broadcast_to(RightPelvisAnglesRad[..., 1], (_batch_count,))
        arrayRightPelvisAnglesRad[2][_batch_slice] = np.broadcast_to(RightPelvisAnglesRad[..., 2], (_batch_count,))
        arrayRightThighAnglesRad[0][_batch_slice] = np.broadcast_to(RightThighAnglesRad[..., 0], (_batch_count,))
        arrayRightThighAnglesRad[1][_batch_slice] = np.broadcast_to(RightThighAnglesRad[..., 1], (_batch_count,))
        arrayRightThighAnglesRad[2][_batch_slice] = np.broadcast_to(RightThighAnglesRad[..., 2], (_batch_count,))
        arrayRightShankAnglesRad[0][_batch_slice] = np.broadcast_to(RightShankAnglesRad[..., 0], (_batch_count,))
        arrayRightShankAnglesRad[1][_batch_slice] = np.broadcast_to(RightShankAnglesRad[..., 1], (_batch_count,))
        arrayRightShankAnglesRad[2][_batch_slice] = np.broadcast_to(RightShankAnglesRad[..., 2], (_batch_count,))
        arrayRightFootAnglesRad[0][_batch_slice] = np.broadcast_to(RightFootAnglesRad[..., 0], (_batch_count,))
        arrayRightFootAnglesRad[1][_batch_slice] = np.broadcast_to(RightFootAnglesRad[..., 1], (_batch_count,))
        arrayRightFootAnglesRad[2][_batch_slice] = np.broadcast_to(RightFootAnglesRad[..., 2], (_batch_count,))
        if self.valueRightFootModelCheck == '1':
            arrayRightHindfootAnglesRad[0][_batch_slice] = np.broadcast_to(RightHindfootAnglesRad[..., 0], (_batch_count,))
            arrayRightHindfootAnglesRad[1][_batch_slice] = np.broadcast_to(RightHindfootAnglesRad[..., 1], (_batch_count,))
            arrayRightHindfootAnglesRad[2][_batch_slice] = np.broadcast_to(RightHindfootAnglesRad[..., 2], (_batch_count,))
            arrayRightForefootAnglesRad[0][_batch_slice] = np.broadcast_to(RightForefootAnglesRad[..., 0], (_batch_count,))
            arrayRightForefootAnglesRad[1][_batch_slice] = np.broadcast_to(RightForefootAnglesRad[..., 1], (_batch_count,))
            arrayRightForefootAnglesRad[2][_batch_slice] = np.broadcast_to(RightForefootAnglesRad[..., 2], (_batch_count,))
            arrayRightHalluxAnglesRad[0][_batch_slice] = np.broadcast_to(RightHalluxAnglesRad[..., 0], (_batch_count,))
            arrayRightHalluxAnglesRad[1][_batch_slice] = np.broadcast_to(RightHalluxAnglesRad[..., 1], (_batch_count,))
            arrayRightHalluxAnglesRad[2][_batch_slice] = np.broadcast_to(RightHalluxAnglesRad[..., 2], (_batch_count,))
        arrayLeftHipAngles[0][_batch_slice] = np.broadcast_to(LeftHipAnglesDeg[..., 0], (_batch_count,))
        arrayLeftHipAngles[1][_batch_slice] = np.broadcast_to(LeftHipAnglesDeg[..., 1], (_batch_count,))
        arrayLeftHipAngles[2][_batch_slice] = np.broadcast_to(LeftHipAnglesDeg[..., 2], (_batch_count,))
        arrayLeftKneeAngles[0][_batch_slice] = np.broadcast_to(LeftKneeAnglesDeg[..., 0], (_batch_count,))
        arrayLeftKneeAngles[1][_batch_slice] = np.broadcast_to(LeftKneeAnglesDeg[..., 1], (_batch_count,))
        arrayLeftKneeAngles[2][_batch_slice] = np.broadcast_to(LeftKneeAnglesDeg[..., 2], (_batch_count,))
        arrayLeftKneeAnglesProximal[0][_batch_slice] = np.broadcast_to(LeftKneeAnglesProximalDeg[..., 0], (_batch_count,))
        arrayLeftKneeAnglesProximal[1][_batch_slice] = np.broadcast_to(LeftKneeAnglesProximalDeg[..., 1], (_batch_count,))
        arrayLeftKneeAnglesProximal[2][_batch_slice] = np.broadcast_to(LeftKneeAnglesProximalDeg[..., 2], (_batch_count,))
        arrayLeftKneeAnglesDistal[0][_batch_slice] = np.broadcast_to(LeftKneeAnglesDistalDeg[..., 0], (_batch_count,))
        arrayLeftKneeAnglesDistal[1][_batch_slice] = np.broadcast_to(LeftKneeAnglesDistalDeg[..., 1], (_batch_count,))
        arrayLeftKneeAnglesDistal[2][_batch_slice] = np.broadcast_to(LeftKneeAnglesDistalDeg[..., 2], (_batch_count,))
        arrayLeftAnkleAngles[0][_batch_slice] = np.broadcast_to(LeftAnkleAnglesDeg[..., 0], (_batch_count,))
        arrayLeftAnkleAngles[1][_batch_slice] = np.broadcast_to(LeftAnkleAnglesDeg[..., 1], (_batch_count,))
        arrayLeftAnkleAngles[2][_batch_slice] = np.broadcast_to(LeftAnkleAnglesDeg[..., 2], (_batch_count,))
        if self.valueLeftFootModelCheck == '1':
            arrayLeftAnkleComplexAngles[0][_batch_slice] = np.broadcast_to(LeftAnkleComplexAnglesDeg[..., 0], (_batch_count,))
            arrayLeftAnkleComplexAngles[1][_batch_slice] = np.broadcast_to(LeftAnkleComplexAnglesDeg[..., 1], (_batch_count,))
            arrayLeftAnkleComplexAngles[2][_batch_slice] = np.broadcast_to(LeftAnkleComplexAnglesDeg[..., 2], (_batch_count,))
            arrayLeftMidfootAngles[0][_batch_slice] = np.broadcast_to(LeftMidfootAnglesDeg[..., 0], (_batch_count,))
            arrayLeftMidfootAngles[1][_batch_slice] = np.broadcast_to(LeftMidfootAnglesDeg[..., 1], (_batch_count,))
            arrayLeftMidfootAngles[2][_batch_slice] = np.broadcast_to(LeftMidfootAnglesDeg[..., 2], (_batch_count,))
            arrayLeftToesAngles[0][_batch_slice] = np.broadcast_to(LeftToesAnglesDeg[..., 0], (_batch_count,))
            arrayLeftToesAngles[1][_batch_slice] = np.broadcast_to(LeftToesAnglesDeg[..., 1], (_batch_count,))
            arrayLeftToesAngles[2][_batch_slice] = np.broadcast_to(LeftToesAnglesDeg[..., 2], (_batch_count,))
            arraySupination[0][_batch_slice] = (
                np.broadcast_to(np.cos(45 * np.pi / 180) * (LeftMidfootAnglesDeg[..., 2] +
                LeftAnkleComplexAnglesDeg[..., 0]), (_batch_count,))
            )
            arraySkew[0][_batch_slice] = (
                np.broadcast_to(np.cos(45 * np.pi / 180) * (LeftMidfootAnglesDeg[..., 2] -
                LeftAnkleComplexAnglesDeg[..., 0]), (_batch_count,))
            )
        arrayLeftHipAnglesRad[0][_batch_slice] = np.broadcast_to(LeftHipAnglesRad[..., 0], (_batch_count,))
        arrayLeftHipAnglesRad[1][_batch_slice] = np.broadcast_to(LeftHipAnglesRad[..., 1], (_batch_count,))
        arrayLeftHipAnglesRad[2][_batch_slice] = np.broadcast_to(LeftHipAnglesRad[..., 2], (_batch_count,))
        arrayLeftKneeAnglesRad[0][_batch_slice] = np.broadcast_to(LeftKneeAnglesRad[..., 0], (_batch_count,))
        arrayLeftKneeAnglesRad[1][_batch_slice] = np.broadcast_to(LeftKneeAnglesRad[..., 1], (_batch_count,))
        arrayLeftKneeAnglesRad[2][_batch_slice] = np.broadcast_to(LeftKneeAnglesRad[..., 2], (_batch_count,))
        arrayLeftAnkleAnglesRad[0][_batch_slice] = np.broadcast_to(LeftAnkleAnglesRad[..., 0], (_batch_count,))
        arrayLeftAnkleAnglesRad[1][_batch_slice] = np.broadcast_to(LeftAnkleAnglesRad[..., 1], (_batch_count,))
        arrayLeftAnkleAnglesRad[2][_batch_slice] = np.broadcast_to(LeftAnkleAnglesRad[..., 2], (_batch_count,))
        if self.valueLeftFootModelCheck == '1':
            arrayLeftAnkleComplexAnglesRad[0][_batch_slice] = np.broadcast_to(LeftAnkleComplexAnglesRad[..., 0], (_batch_count,))
            arrayLeftAnkleComplexAnglesRad[1][_batch_slice] = np.broadcast_to(LeftAnkleComplexAnglesRad[..., 1], (_batch_count,))
            arrayLeftAnkleComplexAnglesRad[2][_batch_slice] = np.broadcast_to(LeftAnkleComplexAnglesRad[..., 2], (_batch_count,))
            arrayLeftMidfootAnglesRad[0][_batch_slice] = np.broadcast_to(LeftMidfootAnglesRad[..., 0], (_batch_count,))
            arrayLeftMidfootAnglesRad[1][_batch_slice] = np.broadcast_to(LeftMidfootAnglesRad[..., 1], (_batch_count,))
            arrayLeftMidfootAnglesRad[2][_batch_slice] = np.broadcast_to(LeftMidfootAnglesRad[..., 2], (_batch_count,))
            arrayLeftToesAnglesRad[0][_batch_slice] = np.broadcast_to(LeftToesAnglesRad[..., 0], (_batch_count,))
            arrayLeftToesAnglesRad[1][_batch_slice] = np.broadcast_to(LeftToesAnglesRad[..., 1], (_batch_count,))
            arrayLeftToesAnglesRad[2][_batch_slice] = np.broadcast_to(LeftToesAnglesRad[..., 2], (_batch_count,))
        arrayRightHipAngles[0][_batch_slice] = np.broadcast_to(RightHipAnglesDeg[..., 0], (_batch_count,))
        arrayRightHipAngles[1][_batch_slice] = np.broadcast_to(RightHipAnglesDeg[..., 1], (_batch_count,))
        arrayRightHipAngles[2][_batch_slice] = np.broadcast_to(RightHipAnglesDeg[..., 2], (_batch_count,))
        arrayRightKneeAngles[0][_batch_slice] = np.broadcast_to(RightKneeAnglesDeg[..., 0], (_batch_count,))
        arrayRightKneeAngles[1][_batch_slice] = np.broadcast_to(RightKneeAnglesDeg[..., 1], (_batch_count,))
        arrayRightKneeAngles[2][_batch_slice] = np.broadcast_to(RightKneeAnglesDeg[..., 2], (_batch_count,))
        arrayRightKneeAnglesProximal[0][_batch_slice] = np.broadcast_to(RightKneeAnglesProximalDeg[..., 0], (_batch_count,))
        arrayRightKneeAnglesProximal[1][_batch_slice] = np.broadcast_to(RightKneeAnglesProximalDeg[..., 1], (_batch_count,))
        arrayRightKneeAnglesProximal[2][_batch_slice] = np.broadcast_to(RightKneeAnglesProximalDeg[..., 2], (_batch_count,))
        arrayRightKneeAnglesDistal[0][_batch_slice] = np.broadcast_to(RightKneeAnglesDistalDeg[..., 0], (_batch_count,))
        arrayRightKneeAnglesDistal[1][_batch_slice] = np.broadcast_to(RightKneeAnglesDistalDeg[..., 1], (_batch_count,))
        arrayRightKneeAnglesDistal[2][_batch_slice] = np.broadcast_to(RightKneeAnglesDistalDeg[..., 2], (_batch_count,))
        arrayRightAnkleAngles[0][_batch_slice] = np.broadcast_to(RightAnkleAnglesDeg[..., 0], (_batch_count,))
        arrayRightAnkleAngles[1][_batch_slice] = np.broadcast_to(RightAnkleAnglesDeg[..., 1], (_batch_count,))
        arrayRightAnkleAngles[2][_batch_slice] = np.broadcast_to(RightAnkleAnglesDeg[..., 2], (_batch_count,))
        if self.valueRightFootModelCheck == '1':
            arrayRightAnkleComplexAngles[0][_batch_slice] = np.broadcast_to(RightAnkleComplexAnglesDeg[..., 0], (_batch_count,))
            arrayRightAnkleComplexAngles[1][_batch_slice] = np.broadcast_to(RightAnkleComplexAnglesDeg[..., 1], (_batch_count,))
            arrayRightAnkleComplexAngles[2][_batch_slice] = np.broadcast_to(RightAnkleComplexAnglesDeg[..., 2], (_batch_count,))
            arrayRightMidfootAngles[0][_batch_slice] = np.broadcast_to(RightMidfootAnglesDeg[..., 0], (_batch_count,))
            arrayRightMidfootAngles[1][_batch_slice] = np.broadcast_to(RightMidfootAnglesDeg[..., 1], (_batch_count,))
            arrayRightMidfootAngles[2][_batch_slice] = np.broadcast_to(RightMidfootAnglesDeg[..., 2], (_batch_count,))
            arrayRightToesAngles[0][_batch_slice] = np.broadcast_to(RightToesAnglesDeg[..., 0], (_batch_count,))
            arrayRightToesAngles[1][_batch_slice] = np.broadcast_to(RightToesAnglesDeg[..., 1], (_batch_count,))
            arrayRightToesAngles[2][_batch_slice] = np.broadcast_to(RightToesAnglesDeg[..., 2], (_batch_count,))
            arraySupination[1][_batch_slice] = (
                np.broadcast_to(np.cos(45 * np.pi / 180) * (RightMidfootAnglesDeg[..., 2] +
                RightAnkleComplexAnglesDeg[..., 0]), (_batch_count,))
            )
            arraySkew[1][_batch_slice] = (
                np.broadcast_to(np.cos(45 * np.pi / 180) * (RightMidfootAnglesDeg[..., 2] -
                RightAnkleComplexAnglesDeg[..., 0]), (_batch_count,))
            )
        arrayRightHipAnglesRad[0][_batch_slice] = np.broadcast_to(RightHipAnglesRad[..., 0], (_batch_count,))
        arrayRightHipAnglesRad[1][_batch_slice] = np.broadcast_to(RightHipAnglesRad[..., 1], (_batch_count,))
        arrayRightHipAnglesRad[2][_batch_slice] = np.broadcast_to(RightHipAnglesRad[..., 2], (_batch_count,))
        arrayRightKneeAnglesRad[0][_batch_slice] = np.broadcast_to(RightKneeAnglesRad[..., 0], (_batch_count,))
        arrayRightKneeAnglesRad[1][_batch_slice] = np.broadcast_to(RightKneeAnglesRad[..., 1], (_batch_count,))
        arrayRightKneeAnglesRad[2][_batch_slice] = np.broadcast_to(RightKneeAnglesRad[..., 2], (_batch_count,))
        arrayRightAnkleAnglesRad[0][_batch_slice] = np.broadcast_to(RightAnkleAnglesRad[..., 0], (_batch_count,))
        arrayRightAnkleAnglesRad[1][_batch_slice] = np.broadcast_to(RightAnkleAnglesRad[..., 1], (_batch_count,))
        arrayRightAnkleAnglesRad[2][_batch_slice] = np.broadcast_to(RightAnkleAnglesRad[..., 2], (_batch_count,))
        if self.valueRightFootModelCheck == '1':
            arrayRightAnkleComplexAnglesRad[0][_batch_slice] = np.broadcast_to(RightAnkleComplexAnglesRad[..., 0], (_batch_count,))
            arrayRightAnkleComplexAnglesRad[1][_batch_slice] = np.broadcast_to(RightAnkleComplexAnglesRad[..., 1], (_batch_count,))
            arrayRightAnkleComplexAnglesRad[2][_batch_slice] = np.broadcast_to(RightAnkleComplexAnglesRad[..., 2], (_batch_count,))
            arrayRightMidfootAnglesRad[0][_batch_slice] = np.broadcast_to(RightMidfootAnglesRad[..., 0], (_batch_count,))
            arrayRightMidfootAnglesRad[1][_batch_slice] = np.broadcast_to(RightMidfootAnglesRad[..., 1], (_batch_count,))
            arrayRightMidfootAnglesRad[2][_batch_slice] = np.broadcast_to(RightMidfootAnglesRad[..., 2], (_batch_count,))
            arrayRightToesAnglesRad[0][_batch_slice] = np.broadcast_to(RightToesAnglesRad[..., 0], (_batch_count,))
            arrayRightToesAnglesRad[1][_batch_slice] = np.broadcast_to(RightToesAnglesRad[..., 1], (_batch_count,))
            arrayRightToesAnglesRad[2][_batch_slice] = np.broadcast_to(RightToesAnglesRad[..., 2], (_batch_count,))
        arrayGluteusMaxLength[0][_batch_slice] = (
            np.broadcast_to((LeftGMaS + LeftGMaM + LeftGMaI) / (LeftGMaS0 + LeftGMaM0 + LeftGMaI0),
            (_batch_count,))
        )
        arrayGluteusMaxLength[1][_batch_slice] = (
            np.broadcast_to((RightGMaS + RightGMaM + RightGMaI) / (RightGMaS0 + RightGMaM0 + RightGMaI0),
            (_batch_count,))
        )
        arrayIlioPsoasLength[0][_batch_slice] = np.broadcast_to((LeftIlia + LeftPsoa) / (LeftIlia0 + LeftPsoa0), (_batch_count,))
        arrayIlioPsoasLength[1][_batch_slice] = np.broadcast_to((RightIlia + RightPsoa) / (RightIlia0 + RightPsoa0), (_batch_count,))
        arrayRectFemLength[0][_batch_slice] = np.broadcast_to(LeftReFe / LeftReFe0, (_batch_count,))
        arrayRectFemLength[1][_batch_slice] = np.broadcast_to(RightReFe / RightReFe0, (_batch_count,))
        arrayMedHamstringLength[0][_batch_slice] = np.broadcast_to((LeftSeMe + LeftSeTe) / (LeftSeMe0 + LeftSeTe0), (_batch_count,))
        arrayMedHamstringLength[1][_batch_slice] = np.broadcast_to((RightSeMe + RightSeTe) / (RightSeMe0 + RightSeTe0), (_batch_count,))
        arrayLatHamstringLength[0][_batch_slice] = np.broadcast_to((LeftBiFL + LeftBiFS) / (LeftBiFL0 + LeftBiFS0), (_batch_count,))
        arrayLatHamstringLength[1][_batch_slice] = np.broadcast_to((RightBiFL + RightBiFS) / (RightBiFL0 + RightBiFS0), (_batch_count,))
        arrayGastrocLength[0][_batch_slice] = np.broadcast_to((LeftGaMe + LeftGaLa) / (LeftGaMe0 + LeftGaLa0), (_batch_count,))
        arrayGastrocLength[1][_batch_slice] = np.broadcast_to((RightGaMe + RightGaLa) / (RightGaMe0 + RightGaLa0), (_batch_count,))
        arraySoleusLength[0][_batch_slice] = np.broadcast_to(LeftSole / LeftSole0, (_batch_count,))
        arraySoleusLength[1][_batch_slice] = np.broadcast_to(RightSole / RightSole0, (_batch_count,))
        arrayTibPostLength[0][_batch_slice] = np.broadcast_to(LeftTiPo / LeftTiPo0, (_batch_count,))
        arrayTibPostLength[1][_batch_slice] = np.broadcast_to(RightTiPo / RightTiPo0, (_batch_count,))
        arrayPeronealLength[0][_batch_slice] = np.broadcast_to((LeftPeBr + LeftPeLn) / (LeftPeBr0 + LeftPeLn0), (_batch_count,))
        arrayPeronealLength[1][_batch_slice] = np.broadcast_to((RightPeBr + RightPeLn) / (RightPeBr0 + RightPeLn0), (_batch_count,))
        arrayVastusLatLength[0][_batch_slice] = np.broadcast_to(LeftVaLa / LeftVaLa0, (_batch_count,))
        arrayVastusLatLength[1][_batch_slice] = np.broadcast_to(RightVaLa / RightVaLa0, (_batch_count,))
        if TrunkFlag == 1:
            HATCenterOfMass = math.MassCenter(ShouldersCenterLab, PelvisCenterLab, 0.374)
        else:
            HATCenterOfMass = math.FrameVector(_batch_count, 0.0, 0.0, 0.0)
        LeftThighCenterOfMass = math.MassCenter(LeftHipCenterLab, LeftKneeCenterLab, 0.567)
        LeftShankCenterOfMass = math.MassCenter(LeftKneeCenterLab, LeftAnkleCenterLab, 0.567)
        LeftFootCenterOfMass = math.MassCenter(LeftAnkleCenterLab, LeftToeMarker, 0.5)
        RightThighCenterOfMass = math.MassCenter(RightHipCenterLab, RightKneeCenterLab, 0.567)
        RightShankCenterOfMass = math.MassCenter(RightKneeCenterLab, RightAnkleCenterLab, 0.567)
        RightFootCenterOfMass = math.MassCenter(RightAnkleCenterLab, RightToeMarker, 0.5)
        arrayHATCenterOfMass[0][_batch_slice] = np.broadcast_to(Direction * HATCenterOfMass[..., 0], (_batch_count,))
        arrayHATCenterOfMass[1][_batch_slice] = np.broadcast_to(Direction * HATCenterOfMass[..., 1], (_batch_count,))
        arrayHATCenterOfMass[2][_batch_slice] = np.broadcast_to(HATCenterOfMass[..., 2], (_batch_count,))
        arrayLeftThighCenterOfMass[0][_batch_slice] = np.broadcast_to(Direction * LeftThighCenterOfMass[..., 0], (_batch_count,))
        arrayLeftThighCenterOfMass[1][_batch_slice] = np.broadcast_to(Direction * LeftThighCenterOfMass[..., 1], (_batch_count,))
        arrayLeftThighCenterOfMass[2][_batch_slice] = np.broadcast_to(LeftThighCenterOfMass[..., 2], (_batch_count,))
        arrayLeftShankCenterOfMass[0][_batch_slice] = np.broadcast_to(Direction * LeftShankCenterOfMass[..., 0], (_batch_count,))
        arrayLeftShankCenterOfMass[1][_batch_slice] = np.broadcast_to(Direction * LeftShankCenterOfMass[..., 1], (_batch_count,))
        arrayLeftShankCenterOfMass[2][_batch_slice] = np.broadcast_to(LeftShankCenterOfMass[..., 2], (_batch_count,))
        arrayLeftFootCenterOfMass[0][_batch_slice] = np.broadcast_to(Direction * LeftFootCenterOfMass[..., 0], (_batch_count,))
        arrayLeftFootCenterOfMass[1][_batch_slice] = np.broadcast_to(Direction * LeftFootCenterOfMass[..., 1], (_batch_count,))
        arrayLeftFootCenterOfMass[2][_batch_slice] = np.broadcast_to(LeftFootCenterOfMass[..., 2], (_batch_count,))
        arrayRightThighCenterOfMass[0][_batch_slice] = np.broadcast_to(Direction * RightThighCenterOfMass[..., 0], (_batch_count,))
        arrayRightThighCenterOfMass[1][_batch_slice] = np.broadcast_to(Direction * RightThighCenterOfMass[..., 1], (_batch_count,))
        arrayRightThighCenterOfMass[2][_batch_slice] = np.broadcast_to(RightThighCenterOfMass[..., 2], (_batch_count,))
        arrayRightShankCenterOfMass[0][_batch_slice] = np.broadcast_to(Direction * RightShankCenterOfMass[..., 0], (_batch_count,))
        arrayRightShankCenterOfMass[1][_batch_slice] = np.broadcast_to(Direction * RightShankCenterOfMass[..., 1], (_batch_count,))
        arrayRightShankCenterOfMass[2][_batch_slice] = np.broadcast_to(RightShankCenterOfMass[..., 2], (_batch_count,))
        arrayRightFootCenterOfMass[0][_batch_slice] = np.broadcast_to(Direction * RightFootCenterOfMass[..., 0], (_batch_count,))
        arrayRightFootCenterOfMass[1][_batch_slice] = np.broadcast_to(Direction * RightFootCenterOfMass[..., 1], (_batch_count,))
        arrayRightFootCenterOfMass[2][_batch_slice] = np.broadcast_to(RightFootCenterOfMass[..., 2], (_batch_count,))

        # =============================================================================
        #         Write Kinematics Outputs to C3D File
        # =============================================================================
        ModelOutputs = self.Models.getContents()  # + fields["Points"]
        if not "LHJC" in ModelOutputs:
            self.Models.CreateModeledMarker("LHJC")
        if not "RHJC" in ModelOutputs:
            self.Models.CreateModeledMarker("RHJC")
        if not "LKJC" in ModelOutputs:
            self.Models.CreateModeledMarker("LKJC")
        if not "RKJC" in ModelOutputs:
            self.Models.CreateModeledMarker("RKJC")
        if not "LAJC" in ModelOutputs:
            self.Models.CreateModeledMarker("LAJC")
        if not "RAJC" in ModelOutputs:
            self.Models.CreateModeledMarker("RAJC")

        # ASI, KNE, ANK markers for MAPS
        if not "LASI" in ModelOutputs:
            self.Models.CreateModeledMarker("LASI")
        if not "RASI" in ModelOutputs:
            self.Models.CreateModeledMarker("RASI")
        if not "LKNE" in ModelOutputs:
            self.Models.CreateModeledMarker("LKNE")
        if not "RKNE" in ModelOutputs:
            self.Models.CreateModeledMarker("RKNE")
        if not "LANK" in ModelOutputs:
            self.Models.CreateModeledMarker("LANK")
        if not "RANK" in ModelOutputs:
            self.Models.CreateModeledMarker("RANK")

        # PELO: Pelvic Origin Defined as Center of Hip Joints
        if not "PELO" in ModelOutputs:
            self.Models.CreateModeledMarker("PELO")

        XYZNames = ["X", "Y", "Z"]
        AnglesTypes = ["Angle", "Angle", "Angle"]

        # Left Angles
        if not "LTrunkAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LTrunkAngles", "Angles", XYZNames, AnglesTypes
            )
        if not "LTrunkAnglesTOR" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LTrunkAnglesTOR", "Angles", XYZNames, AnglesTypes
            )
        if not "LTrunkAnglesROT" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LTrunkAnglesROT", "Angles", XYZNames, AnglesTypes
            )
        if not "LPelvisAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LPelvisAngles", "Angles", XYZNames, AnglesTypes
            )
        if not "LPelvisAnglesTOR" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LPelvisAnglesTOR", "Angles", XYZNames, AnglesTypes
            )
        if not "LPelvisAnglesROT" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LPelvisAnglesROT", "Angles", XYZNames, AnglesTypes
            )
        if not "LThighAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LThighAngles", "Angles", XYZNames, AnglesTypes
            )
        if not "LShankAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LShankAngles", "Angles", XYZNames, AnglesTypes
            )
        if not "LFootProgressAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LFootProgressAngles", "Angles", XYZNames, AnglesTypes
            )
        if not "LHipAngles" in ModelOutputs:
            self.Models.CreateModelOutput("LHipAngles", "Angles", XYZNames, AnglesTypes)
        if not "LKneeAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LKneeAngles", "Angles", XYZNames, AnglesTypes
            )
        if not "LKneeAnglesProximal" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LKneeAnglesProximal", "Angles", XYZNames, AnglesTypes
            )
        if not "LKneeAnglesDistal" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LKneeAnglesDistal", "Angles", XYZNames, AnglesTypes
            )
        if not "LAnkleAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LAnkleAngles", "Angles", XYZNames, AnglesTypes
            )
        if self.valueLeftFootModelCheck == "1":
            if not "LHFGA" in ModelOutputs:
                self.Models.CreateModelOutput("LHFGA", "Angles", XYZNames, AnglesTypes)
            if not "LFFGA" in ModelOutputs:
                self.Models.CreateModelOutput("LFFGA", "Angles", XYZNames, AnglesTypes)
            if not "LHXGA" in ModelOutputs:
                self.Models.CreateModelOutput("LHXGA", "Angles", XYZNames, AnglesTypes)
            if not "LANKA" in ModelOutputs:
                self.Models.CreateModelOutput("LANKA", "Angles", XYZNames, AnglesTypes)
            if not "LMDFA" in ModelOutputs:
                self.Models.CreateModelOutput("LMDFA", "Angles", XYZNames, AnglesTypes)
            if not "LHLXA" in ModelOutputs:
                self.Models.CreateModelOutput("LHLXA", "Angles", XYZNames, AnglesTypes)
            # Create Modeled Marker- Upper calcaneus markers [name too long if Left_Upper_Posterior_Calcaneus]
            if self.valueLeftFootModelCheck == "1":
                if not "Left_Superior_Calcaneus" in ModelOutputs:
                    self.Models.CreateModeledMarker("Left_Superior_Calcaneus")

        # Right Angles
        if not "RTrunkAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RTrunkAngles", "Angles", XYZNames, AnglesTypes
            )
        if not "RTrunkAnglesTOR" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RTrunkAnglesTOR", "Angles", XYZNames, AnglesTypes
            )
        if not "RTrunkAnglesROT" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RTrunkAnglesROT", "Angles", XYZNames, AnglesTypes
            )
        if not "RPelvisAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RPelvisAngles", "Angles", XYZNames, AnglesTypes
            )
        if not "RPelvisAnglesTOR" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RPelvisAnglesTOR", "Angles", XYZNames, AnglesTypes
            )
        if not "RPelvisAnglesROT" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RPelvisAnglesROT", "Angles", XYZNames, AnglesTypes
            )
        if not "RThighAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RThighAngles", "Angles", XYZNames, AnglesTypes
            )
        if not "RShankAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RShankAngles", "Angles", XYZNames, AnglesTypes
            )
        if not "RFootProgressAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RFootProgressAngles", "Angles", XYZNames, AnglesTypes
            )
        if not "RHipAngles" in ModelOutputs:
            self.Models.CreateModelOutput("RHipAngles", "Angles", XYZNames, AnglesTypes)
        if not "RKneeAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RKneeAngles", "Angles", XYZNames, AnglesTypes
            )
        if not "RKneeAnglesProximal" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RKneeAnglesProximal", "Angles", XYZNames, AnglesTypes
            )
        if not "RKneeAnglesDistal" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RKneeAnglesDistal", "Angles", XYZNames, AnglesTypes
            )
        if not "RAnkleAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RAnkleAngles", "Angles", XYZNames, AnglesTypes
            )
        if self.valueRightFootModelCheck == "1":
            if not "RHFGA" in ModelOutputs:
                self.Models.CreateModelOutput("RHFGA", "Angles", XYZNames, AnglesTypes)
            if not "RFFGA" in ModelOutputs:
                self.Models.CreateModelOutput("RFFGA", "Angles", XYZNames, AnglesTypes)
            if not "RHXGA" in ModelOutputs:
                self.Models.CreateModelOutput("RHXGA", "Angles", XYZNames, AnglesTypes)
            if not "RANKA" in ModelOutputs:
                self.Models.CreateModelOutput("RANKA", "Angles", XYZNames, AnglesTypes)
            if not "RMDFA" in ModelOutputs:
                self.Models.CreateModelOutput("RMDFA", "Angles", XYZNames, AnglesTypes)
            if not "RHLXA" in ModelOutputs:
                self.Models.CreateModelOutput("RHLXA", "Angles", XYZNames, AnglesTypes)
            # Create Modeled Marker- Upper calcaneus markers [name too long if Right_Upper_Posterior_Calcaneus]
            if self.valueRightFootModelCheck == "1":
                if not "Right_Superior_Calcaneus" in ModelOutputs:
                    self.Models.CreateModeledMarker(
                        SubjectName, "Right_Superior_Calcaneus"
                    )

        if self.valueLeftFootModelCheck == "1" or self.valueRightFootModelCheck == "1":
            if not "Supination" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "Supination", "Angles", XYZNames, AnglesTypes
                )
            if not "Skew" in ModelOutputs:
                self.Models.CreateModelOutput("Skew", "Angles", XYZNames, AnglesTypes)

        # Additional Trunk Angles for MAPS
        if not "LThoraxAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LThoraxAngles", "Angles", XYZNames, AnglesTypes
            )
        if not "RThoraxAngles" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RThoraxAngles", "Angles", XYZNames, AnglesTypes
            )

        # Muscle Lengths & Velocity
        if not "GluteusMaxLength" in ModelOutputs:
            self.Models.CreateModelOutput(
                "GluteusMaxLength", "Angles", XYZNames, AnglesTypes
            )
        if not "GluteusMaxVelocity" in ModelOutputs:
            self.Models.CreateModelOutput(
                "GluteusMaxVelocity", "Angles", XYZNames, AnglesTypes
            )
        if not "IlioPsoasLength" in ModelOutputs:
            self.Models.CreateModelOutput(
                "IlioPsoasLength", "Angles", XYZNames, AnglesTypes
            )
        if not "IlioPsoasVelocity" in ModelOutputs:
            self.Models.CreateModelOutput(
                "IlioPsoasVelocity", "Angles", XYZNames, AnglesTypes
            )
        if not "RectFemLength" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RectFemLength", "Angles", XYZNames, AnglesTypes
            )
        if not "RectFemVelocity" in ModelOutputs:
            self.Models.CreateModelOutput(
                "RectFemVelocity", "Angles", XYZNames, AnglesTypes
            )
        if not "MedHamstringLength" in ModelOutputs:
            self.Models.CreateModelOutput(
                "MedHamstringLength", "Angles", XYZNames, AnglesTypes
            )
        if not "MedHamstringVelocity" in ModelOutputs:
            self.Models.CreateModelOutput(
                "MedHamstringVelocity", "Angles", XYZNames, AnglesTypes
            )
        if not "LatHamstringLength" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LatHamstringLength", "Angles", XYZNames, AnglesTypes
            )
        if not "LatHamstringVelocity" in ModelOutputs:
            self.Models.CreateModelOutput(
                "LatHamstringVelocity", "Angles", XYZNames, AnglesTypes
            )
        if not "GastrocLength" in ModelOutputs:
            self.Models.CreateModelOutput(
                "GastrocLength", "Angles", XYZNames, AnglesTypes
            )
        if not "GastrocVelocity" in ModelOutputs:
            self.Models.CreateModelOutput(
                "GastrocVelocity", "Angles", XYZNames, AnglesTypes
            )
        if not "SoleusLength" in ModelOutputs:
            self.Models.CreateModelOutput(
                "SoleusLength", "Angles", XYZNames, AnglesTypes
            )
        if not "SoleusVelocity" in ModelOutputs:
            self.Models.CreateModelOutput(
                "SoleusVelocity", "Angles", XYZNames, AnglesTypes
            )
        if not "TibPostLength" in ModelOutputs:
            self.Models.CreateModelOutput(
                "TibPostLength", "Angles", XYZNames, AnglesTypes
            )
        if not "TibPostVelocity" in ModelOutputs:
            self.Models.CreateModelOutput(
                "TibPostVelocity", "Angles", XYZNames, AnglesTypes
            )
        if not "PeronealLength" in ModelOutputs:
            self.Models.CreateModelOutput(
                "PeronealLength", "Angles", XYZNames, AnglesTypes
            )
        if not "PeronealVelocity" in ModelOutputs:
            self.Models.CreateModelOutput(
                "PeronealVelocity", "Angles", XYZNames, AnglesTypes
            )
        if not "VastusLatLength" in ModelOutputs:
            self.Models.CreateModelOutput(
                "VastusLatLength", "Angles", XYZNames, AnglesTypes
            )
        if not "VastusLatVelocity" in ModelOutputs:
            self.Models.CreateModelOutput(
                "VastusLatVelocity", "Angles", XYZNames, AnglesTypes
            )

        # This function rearranges the array such that
        # 0- Flexion
        # 1- Ab/Adduction
        # 2- Int/Ext Rotation
        def reArrangeArray(InputArray):
            return np.asarray(InputArray)[[1, 0, 2], :framecount].tolist()

        # Rearrange Angles arrays before writing to C3D
        ReArranged_arrayLeftTrunkAngles = reArrangeArray(arrayLeftTrunkAngles)
        ReArranged_arrayLeftTrunkAnglesTOR = reArrangeArray(arrayLeftTrunkAnglesTOR)
        ReArranged_arrayLeftTrunkAnglesROT = reArrangeArray(arrayLeftTrunkAnglesROT)
        ReArranged_arrayLeftPelvisAngles = reArrangeArray(arrayLeftPelvisAngles)
        ReArranged_arrayLeftPelvisAnglesTOR = reArrangeArray(arrayLeftPelvisAnglesTOR)
        ReArranged_arrayLeftPelvisAnglesROT = reArrangeArray(arrayLeftPelvisAnglesROT)
        ReArranged_arrayLeftThighAngles = reArrangeArray(arrayLeftThighAngles)
        ReArranged_arrayLeftShankAngles = reArrangeArray(arrayLeftShankAngles)
        ReArranged_arrayLeftFootAngles = reArrangeArray(arrayLeftFootAngles)
        ReArranged_arrayLeftHipAngles = reArrangeArray(arrayLeftHipAngles)
        ReArranged_arrayLeftKneeAngles = reArrangeArray(arrayLeftKneeAngles)
        ReArranged_arrayLeftKneeAnglesProximal = reArrangeArray(
            arrayLeftKneeAnglesProximal
        )
        ReArranged_arrayLeftKneeAnglesDistal = reArrangeArray(arrayLeftKneeAnglesDistal)
        ReArranged_arrayLeftAnkleAngles = reArrangeArray(arrayLeftAnkleAngles)
        if self.valueLeftFootModelCheck == "1":
            ReArranged_arrayLeftHindfootAngles = reArrangeArray(arrayLeftHindfootAngles)
            ReArranged_arrayLeftForefootAngles = reArrangeArray(arrayLeftForefootAngles)
            ReArranged_arrayLeftHalluxAngles = reArrangeArray(arrayLeftHalluxAngles)
            ReArranged_arrayLeftAnkleComplexAngles = reArrangeArray(
                arrayLeftAnkleComplexAngles
            )
            ReArranged_arrayLeftMidfootAngles = reArrangeArray(arrayLeftMidfootAngles)
            ReArranged_arrayLeftToesAngles = reArrangeArray(arrayLeftToesAngles)
        ReArranged_arrayRightTrunkAngles = reArrangeArray(arrayRightTrunkAngles)
        ReArranged_arrayRightTrunkAnglesTOR = reArrangeArray(arrayRightTrunkAnglesTOR)
        ReArranged_arrayRightTrunkAnglesROT = reArrangeArray(arrayRightTrunkAnglesROT)
        ReArranged_arrayRightPelvisAngles = reArrangeArray(arrayRightPelvisAngles)
        ReArranged_arrayRightPelvisAnglesTOR = reArrangeArray(arrayRightPelvisAnglesTOR)
        ReArranged_arrayRightPelvisAnglesROT = reArrangeArray(arrayRightPelvisAnglesROT)
        ReArranged_arrayRightThighAngles = reArrangeArray(arrayRightThighAngles)
        ReArranged_arrayRightShankAngles = reArrangeArray(arrayRightShankAngles)
        ReArranged_arrayRightFootAngles = reArrangeArray(arrayRightFootAngles)
        ReArranged_arrayRightHipAngles = reArrangeArray(arrayRightHipAngles)
        ReArranged_arrayRightKneeAngles = reArrangeArray(arrayRightKneeAngles)
        ReArranged_arrayRightKneeAnglesProximal = reArrangeArray(
            arrayRightKneeAnglesProximal
        )
        ReArranged_arrayRightKneeAnglesDistal = reArrangeArray(
            arrayRightKneeAnglesDistal
        )
        ReArranged_arrayRightAnkleAngles = reArrangeArray(arrayRightAnkleAngles)
        if self.valueRightFootModelCheck == "1":
            ReArranged_arrayRightHindfootAngles = reArrangeArray(
                arrayRightHindfootAngles
            )
            ReArranged_arrayRightForefootAngles = reArrangeArray(
                arrayRightForefootAngles
            )
            ReArranged_arrayRightHalluxAngles = reArrangeArray(arrayRightHalluxAngles)
            ReArranged_arrayRightAnkleComplexAngles = reArrangeArray(
                arrayRightAnkleComplexAngles
            )
            ReArranged_arrayRightMidfootAngles = reArrangeArray(arrayRightMidfootAngles)
            ReArranged_arrayRightToesAngles = reArrangeArray(arrayRightToesAngles)

        # Write Arrays to C3D Files
        # Joint Centers
        self.Models.SetModelOutput(
            "LHJC",
            arrayLeftHipCenter,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
            fields["initial_frame_offset"],
        )
        self.Models.SetModelOutput(
            "RHJC",
            arrayRightHipCenter,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
            fields["initial_frame_offset"],
        )
        self.Models.SetModelOutput(
            "LKJC",
            arrayLeftKneeCenter,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
            fields["initial_frame_offset"],
        )
        self.Models.SetModelOutput(
            "RKJC",
            arrayRightKneeCenter,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
            fields["initial_frame_offset"],
        )
        self.Models.SetModelOutput(
            "LAJC",
            arrayLeftAnkleCenter,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
            fields["initial_frame_offset"],
        )
        self.Models.SetModelOutput(
            "RAJC",
            arrayRightAnkleCenter,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
            fields["initial_frame_offset"],
        )

        # ASI markers for MAPS
        self.Models.SetModelOutput(
            "LASI",
            arrayLeftASIS,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
            fields["initial_frame_offset"],
        )
        self.Models.SetModelOutput(
            "RASI",
            arrayRightASIS,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
            fields["initial_frame_offset"],
        )
        self.Models.SetModelOutput(
            "LKNE",
            arrayLeftKNE,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
            fields["initial_frame_offset"],
        )
        self.Models.SetModelOutput(
            "RKNE",
            arrayRightKNE,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
            fields["initial_frame_offset"],
        )
        self.Models.SetModelOutput(
            "LANK",
            arrayLeftANK,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
            fields["initial_frame_offset"],
        )
        self.Models.SetModelOutput(
            "RANK",
            arrayRightANK,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
            fields["initial_frame_offset"],
        )

        # Upper Calcaneus and Pelvis Origin [PELO]
        self.Models.SetModelOutput(
            "PELO",
            arrayPelvisOrigin,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
            fields["initial_frame_offset"],
        )
        if self.valueLeftFootModelCheck == "1":
            self.Models.SetModelOutput(
                "Left_Superior_Calcaneus",
                arrayLeftUpperPCAL,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
        if self.valueRightFootModelCheck == "1":
            self.Models.SetModelOutput(
                "Right_Superior_Calcaneus",
                arrayRightUpperPCAL,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )

        # Left Angles
        self.Models.SetModelOutput(
            "LTrunkAngles",
            ReArranged_arrayLeftTrunkAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        # self.Models.printItem('LTrunkAngles')
        self.Models.SetModelOutput(
            "LTrunkAnglesTOR",
            ReArranged_arrayLeftTrunkAnglesTOR,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "LTrunkAnglesROT",
            ReArranged_arrayLeftTrunkAnglesROT,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "LPelvisAngles",
            ReArranged_arrayLeftPelvisAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "LPelvisAnglesTOR",
            ReArranged_arrayLeftPelvisAnglesTOR,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "LPelvisAnglesROT",
            ReArranged_arrayLeftPelvisAnglesROT,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "LThighAngles",
            ReArranged_arrayLeftThighAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "LShankAngles",
            ReArranged_arrayLeftShankAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "LFootProgressAngles",
            ReArranged_arrayLeftFootAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "LHipAngles",
            ReArranged_arrayLeftHipAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "LKneeAngles",
            ReArranged_arrayLeftKneeAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "LKneeAnglesProximal",
            ReArranged_arrayLeftKneeAnglesProximal,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "LKneeAnglesDistal",
            ReArranged_arrayLeftKneeAnglesDistal,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "LAnkleAngles",
            ReArranged_arrayLeftAnkleAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        if self.valueLeftFootModelCheck == "1":
            self.Models.SetModelOutput(
                "LHFGA",
                ReArranged_arrayLeftHindfootAngles,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LFFGA",
                ReArranged_arrayLeftForefootAngles,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LHXGA",
                ReArranged_arrayLeftHalluxAngles,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LANKA",
                ReArranged_arrayLeftAnkleComplexAngles,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LMDFA",
                ReArranged_arrayLeftMidfootAngles,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LHLXA",
                ReArranged_arrayLeftToesAngles,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )

        # Right Angles
        self.Models.SetModelOutput(
            "RTrunkAngles",
            ReArranged_arrayRightTrunkAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "RTrunkAnglesTOR",
            ReArranged_arrayRightTrunkAnglesTOR,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "RTrunkAnglesROT",
            ReArranged_arrayRightTrunkAnglesROT,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "RPelvisAngles",
            ReArranged_arrayRightPelvisAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "RPelvisAnglesTOR",
            ReArranged_arrayRightPelvisAnglesTOR,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "RPelvisAnglesROT",
            ReArranged_arrayRightPelvisAnglesROT,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "RThighAngles",
            ReArranged_arrayRightThighAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "RShankAngles",
            ReArranged_arrayRightShankAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "RFootProgressAngles",
            ReArranged_arrayRightFootAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "RHipAngles",
            ReArranged_arrayRightHipAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "RKneeAngles",
            ReArranged_arrayRightKneeAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "RKneeAnglesProximal",
            ReArranged_arrayRightKneeAnglesProximal,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "RKneeAnglesDistal",
            ReArranged_arrayRightKneeAnglesDistal,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "RAnkleAngles",
            ReArranged_arrayRightAnkleAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        if self.valueRightFootModelCheck == "1":
            self.Models.SetModelOutput(
                "RHFGA",
                ReArranged_arrayRightHindfootAngles,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RFFGA",
                ReArranged_arrayRightForefootAngles,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RHXGA",
                ReArranged_arrayRightHalluxAngles,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RANKA",
                ReArranged_arrayRightAnkleComplexAngles,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RMDFA",
                ReArranged_arrayRightMidfootAngles,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RHLXA",
                ReArranged_arrayRightToesAngles,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )

        if self.valueLeftFootModelCheck == "1" or self.valueRightFootModelCheck == "1":
            self.Models.SetModelOutput(
                "Supination",
                arraySupination,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "Skew",
                arraySkew,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )

        # Additional Trunk Angles for MAPS
        self.Models.SetModelOutput(
            "LThoraxAngles",
            ReArranged_arrayLeftTrunkAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        self.Models.SetModelOutput(
            "RThoraxAngles",
            ReArranged_arrayRightTrunkAngles,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )

        # Write Muscle Lengths and Velocity
        MarkerFrameRate = fields["Capture_Frequency"]
        DeltaTime = 1.0 / MarkerFrameRate

        self.Models.SetModelOutput(
            "GluteusMaxLength",
            arrayGluteusMaxLength,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        [arrayGluteusMaxVelocity, arrayGluteusMaxAcceleration] = math.Differentiate(
            arrayGluteusMaxLength, StartFrame, EndFrame, framecount, DeltaTime
        )
        self.Models.SetModelOutput(
            "GluteusMaxVelocity",
            arrayGluteusMaxVelocity,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )

        self.Models.SetModelOutput(
            "IlioPsoasLength",
            arrayIlioPsoasLength,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        [arrayIlioPsoasVelocity, arrayIlioPsoasAcceleration] = math.Differentiate(
            arrayIlioPsoasLength, StartFrame, EndFrame, framecount, DeltaTime
        )
        self.Models.SetModelOutput(
            "IlioPsoasVelocity",
            arrayIlioPsoasVelocity,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )

        self.Models.SetModelOutput(
            "RectFemLength",
            arrayRectFemLength,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        [arrayRectFemVelocity, arrayRectFemAcceleration] = math.Differentiate(
            arrayRectFemLength, StartFrame, EndFrame, framecount, DeltaTime
        )
        self.Models.SetModelOutput(
            "RectFemVelocity",
            arrayRectFemVelocity,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )

        self.Models.SetModelOutput(
            "MedHamstringLength",
            arrayMedHamstringLength,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        [arrayMedHamstringVelocity, arrayMedHamstringAcceleration] = math.Differentiate(
            arrayMedHamstringLength, StartFrame, EndFrame, framecount, DeltaTime
        )
        self.Models.SetModelOutput(
            "MedHamstringVelocity",
            arrayMedHamstringVelocity,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )

        self.Models.SetModelOutput(
            "LatHamstringLength",
            arrayLatHamstringLength,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        [arrayLatHamstringVelocity, arrayLatHamstringAcceleration] = math.Differentiate(
            arrayLatHamstringLength, StartFrame, EndFrame, framecount, DeltaTime
        )
        self.Models.SetModelOutput(
            "LatHamstringVelocity",
            arrayLatHamstringVelocity,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )

        self.Models.SetModelOutput(
            "GastrocLength",
            arrayGastrocLength,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        [arrayGastrocVelocity, arrayGastrocAcceleration] = math.Differentiate(
            arrayGastrocLength, StartFrame, EndFrame, framecount, DeltaTime
        )
        self.Models.SetModelOutput(
            "GastrocVelocity",
            arrayGastrocVelocity,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )

        self.Models.SetModelOutput(
            "SoleusLength",
            arraySoleusLength,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        [arraySoleusVelocity, arraySoleusAcceleration] = math.Differentiate(
            arraySoleusLength, StartFrame, EndFrame, framecount, DeltaTime
        )
        self.Models.SetModelOutput(
            "SoleusVelocity",
            arraySoleusVelocity,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )

        self.Models.SetModelOutput(
            "TibPostLength",
            arrayTibPostLength,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        [arrayTibPostVelocity, arrayTibPostAcceleration] = math.Differentiate(
            arrayTibPostLength, StartFrame, EndFrame, framecount, DeltaTime
        )
        self.Models.SetModelOutput(
            "TibPostVelocity",
            arrayTibPostVelocity,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )

        self.Models.SetModelOutput(
            "PeronealLength",
            arrayPeronealLength,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        [arrayPeronealVelocity, arrayPeronealAcceleration] = math.Differentiate(
            arrayPeronealLength, StartFrame, EndFrame, framecount, DeltaTime
        )
        self.Models.SetModelOutput(
            "PeronealVelocity",
            arrayPeronealVelocity,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )

        self.Models.SetModelOutput(
            "VastusLatLength",
            arrayVastusLatLength,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )
        [arrayVastusLatVelocity, arrayVastusLatAcceleration] = math.Differentiate(
            arrayVastusLatLength, StartFrame, EndFrame, framecount, DeltaTime
        )
        self.Models.SetModelOutput(
            "VastusLatVelocity",
            arrayVastusLatVelocity,
            exists,
            fields["First Frame"],
            fields["Last Frame"],
        )

        # =============================================================================
        #     Kinetics
        # =============================================================================

        # Check for Force Plate Hits
        SimForcePlate = fields["FP"]

        # DeviceIDs = list(sorted(SimForcePlate.keys()))#vicon.GetDeviceIDs()

        # If user passed force plate selection explicitly via CLI and not forced interactive, use them
        if (args.leftPlate is not None or args.rightPlate is not None) and not args.interactiveFP:
            LeftForcePlate_DeviceID = args.leftPlate if args.leftPlate else "0"
            RightForcePlate_DeviceID = args.rightPlate if args.rightPlate else "0"
        elif os.environ.get("SHRINERS_NON_INTERACTIVE") == "1" and not args.interactiveFP:
            keys = list(sorted(SimForcePlate.keys())) if SimForcePlate else []
            LeftForcePlate_DeviceID = keys[0] if keys else "0"
            RightForcePlate_DeviceID = keys[1] if len(keys) > 1 else "0"
        else:
            LeftForcePlate_DeviceID, RightForcePlate_DeviceID = ForcePlateGUI(
                fields["FP"]
            ).run()

        self.Models.rightPlate = RightForcePlate_DeviceID
        self.Models.leftPlate = LeftForcePlate_DeviceID

        # Apply offset adjustments to Center of Pressure
        for fp in [LeftForcePlate_DeviceID, RightForcePlate_DeviceID]:
            if fp != "0" and fp in SimForcePlate:
                offset_delta_x = SimForcePlate[fp].get("Offset", {}).get("X", 0.0) - SimForcePlate[fp]["WorldCenter"][0]
                offset_delta_y = SimForcePlate[fp].get("Offset", {}).get("Y", 0.0) - SimForcePlate[fp]["WorldCenter"][1]
                offset_delta_z = SimForcePlate[fp].get("Offset", {}).get("Z", 0.0) - SimForcePlate[fp]["WorldCenter"][2]/2
                if offset_delta_x != 0.0:
                    SimForcePlate[fp]["Center_of_Pressure"]["X"] += offset_delta_x
                if offset_delta_y != 0.0:
                    SimForcePlate[fp]["Center_of_Pressure"]["Y"] += offset_delta_y
                if offset_delta_z != 0.0:
                    SimForcePlate[fp]["Center_of_Pressure"]["Z"] += offset_delta_z

        # LeftForcePlate_DeviceID = DeviceIDs[0] #Default Value if Force Plate Hit is not Found
        # if len(DeviceIDs)>1:
        #     RightForcePlate_DeviceID = DeviceIDs[1] #Default Value if Force Plate Hit is not Found
        # else:
        #     RightForcePlate_DeviceID = 0

        ############################################################################################
        # NO IDEA HOW To SOLVE THIS                                                                 #
        #                                                                                       #  #
        ############################################################################################

        # for DeviceID in DeviceIDs:
        #     #[name, type, rate, deviceOutputIDs, forceplate, eyetracker] = vicon.GetDeviceDetails(DeviceID)
        #     #print forceplate.Context
        #     if forceplate.Context == 'Left':
        #         LeftForcePlate_DeviceID = DeviceID
        #         Left_forceplate = forceplate
        #         #print('Left',string.split(DeviceNames[i])[0])
        #     if forceplate.Context == 'Right':
        #         RightForcePlate_DeviceID = DeviceID
        #         Right_forceplate = forceplate
        #         #print('Right',string.split(DeviceNames[i])[0])

        # print LeftForcePlate_DeviceID, RightForcePlate_DeviceID

        # =============================================================================
        #         # Compute Kinematic Derivatives
        # =============================================================================
        MarkerFrameRate = fields["Capture_Frequency"]
        DeltaTime = 1.0 / MarkerFrameRate
        # Polynomial Order for Smoothing and Differentiating
        Order = 3
        WindowWidth = 21  # Use Odd Number

        if not LeftForcePlate_DeviceID == "0":
            # ==================== Smooth Data before Differentiating ======================
            # Center of Mass
            arrayHATCenterOfMass = math.Smooth3DArray(
                arrayHATCenterOfMass, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayLeftThighCenterOfMass = math.Smooth3DArray(
                arrayLeftThighCenterOfMass, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayLeftShankCenterOfMass = math.Smooth3DArray(
                arrayLeftShankCenterOfMass, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayLeftFootCenterOfMass = math.Smooth3DArray(
                arrayLeftFootCenterOfMass, StartFrame, EndFrame, Order, WindowWidth
            )
            # Joint Centers
            arrayLeftHipCenter = math.Smooth3DArray(
                arrayLeftHipCenter, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayLeftKneeCenter = math.Smooth3DArray(
                arrayLeftKneeCenter, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayLeftAnkleCenter = math.Smooth3DArray(
                arrayLeftAnkleCenter, StartFrame, EndFrame, Order, WindowWidth
            )
            # Left Angles
            arrayLeftTrunkAngles = math.Smooth3DArray(
                arrayLeftTrunkAngles, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayLeftPelvisAngles = math.Smooth3DArray(
                arrayLeftPelvisAngles, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayLeftThighAngles = math.Smooth3DArray(
                arrayLeftThighAngles, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayLeftShankAngles = math.Smooth3DArray(
                arrayLeftShankAngles, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayLeftFootAngles = math.Smooth3DArray(
                arrayLeftFootAngles, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayLeftHipAngles = math.Smooth3DArray(
                arrayLeftHipAngles, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayLeftKneeAngles = math.Smooth3DArray(
                arrayLeftKneeAngles, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayLeftAnkleAngles = math.Smooth3DArray(
                arrayLeftAnkleAngles, StartFrame, EndFrame, Order, WindowWidth
            )

            # ======================== Translation Variables Differentiatition ===============================
            # Center of Mass
            [arrayHATLinearVelocityLab, arrayHATLinearAccelerationLab] = (
                math.Differentiate(
                    arrayHATCenterOfMass, StartFrame, EndFrame, framecount, DeltaTime
                )
            )
            [arrayLeftThighLinearVelocityLab, arrayLeftThighLinearAccelerationLab] = (
                math.Differentiate(
                    arrayLeftThighCenterOfMass,
                    StartFrame,
                    EndFrame,
                    framecount,
                    DeltaTime,
                )
            )
            [arrayLeftShankLinearVelocityLab, arrayLeftShankLinearAccelerationLab] = (
                math.Differentiate(
                    arrayLeftShankCenterOfMass,
                    StartFrame,
                    EndFrame,
                    framecount,
                    DeltaTime,
                )
            )
            [arrayLeftFootLinearVelocityLab, arrayLeftFootLinearAccelerationLab] = (
                math.Differentiate(
                    arrayLeftFootCenterOfMass,
                    StartFrame,
                    EndFrame,
                    framecount,
                    DeltaTime,
                )
            )
            # Joint Centers
            [
                arrayLeftHipCenterLinearVelocityLab,
                arrayLeftHipCenterLinearAccelerationLab,
            ] = math.Differentiate(
                arrayLeftHipCenter, StartFrame, EndFrame, framecount, DeltaTime
            )
            [
                arrayLeftKneeCenterLinearVelocityLab,
                arrayLeftKneeCenterLinearAccelerationLab,
            ] = math.Differentiate(
                arrayLeftKneeCenter, StartFrame, EndFrame, framecount, DeltaTime
            )
            [
                arrayLeftAnkleCenterLinearVelocityLab,
                arrayLeftAnkleCenterLinearAccelerationLab,
            ] = math.Differentiate(
                arrayLeftAnkleCenter, StartFrame, EndFrame, framecount, DeltaTime
            )

            # ======================== Rotational Variables Differentiatition ===============================
            # Left Angles  Derivatives. Derivatives are in Reference Coordinate System. For segment- Lab CS. For Joints- Proximal Segment CS
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayLeftTrunkAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [arrayLeftTrunkAnglesVelocityLab, arrayLeftTrunkAnglesAccelerationLab] = (
                math.AngVelAcc_Euler_YXZ(
                    arrayLeftTrunkAnglesRad,
                    arrayVelocity,
                    arrayAcceleration,
                    StartFrame,
                    EndFrame,
                    framecount,
                )
            )
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayLeftPelvisAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [arrayLeftPelvisAnglesVelocityLab, arrayLeftPelvisAnglesAccelerationLab] = (
                math.AngVelAcc_Euler_YXZ(
                    arrayLeftPelvisAnglesRad,
                    arrayVelocity,
                    arrayAcceleration,
                    StartFrame,
                    EndFrame,
                    framecount,
                )
            )
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayLeftThighAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [arrayLeftThighAnglesVelocityLab, arrayLeftThighAnglesAccelerationLab] = (
                math.AngVelAcc_Euler_YXZ(
                    arrayLeftThighAnglesRad,
                    arrayVelocity,
                    arrayAcceleration,
                    StartFrame,
                    EndFrame,
                    framecount,
                )
            )
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayLeftShankAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [arrayLeftShankAnglesVelocityLab, arrayLeftShankAnglesAccelerationLab] = (
                math.AngVelAcc_Euler_YXZ(
                    arrayLeftShankAnglesRad,
                    arrayVelocity,
                    arrayAcceleration,
                    StartFrame,
                    EndFrame,
                    framecount,
                )
            )
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayLeftFootAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [arrayLeftFootAnglesVelocityLab, arrayLeftFootAnglesAccelerationLab] = (
                math.AngVelAcc_Euler_YXZ(
                    arrayLeftFootAnglesRad,
                    arrayVelocity,
                    arrayAcceleration,
                    StartFrame,
                    EndFrame,
                    framecount,
                )
            )
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayLeftHipAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [arrayLeftHipAnglesVelocityPelvis, arrayLeftHipAnglesAccelerationPelvis] = (
                math.AngVelAcc_Euler_YXZ(
                    arrayLeftHipAnglesRad,
                    arrayVelocity,
                    arrayAcceleration,
                    StartFrame,
                    EndFrame,
                    framecount,
                )
            )
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayLeftKneeAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [arrayLeftKneeAnglesVelocityThigh, arrayLeftKneeAnglesAccelerationThigh] = (
                math.AngVelAcc_Euler_YXZ(
                    arrayLeftKneeAnglesRad,
                    arrayVelocity,
                    arrayAcceleration,
                    StartFrame,
                    EndFrame,
                    framecount,
                )
            )
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayLeftAnkleAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [
                arrayLeftAnkleAnglesVelocityShank,
                arrayLeftAnkleAnglesAccelerationShank,
            ] = math.AngVelAcc_Euler_YXZ(
                arrayLeftAnkleAnglesRad,
                arrayVelocity,
                arrayAcceleration,
                StartFrame,
                EndFrame,
                framecount,
            )

            # Extract Force Plate Data
            # GetDeviceChannelGlobal(DeviceID, DeviceOutputID, ChannelID)
            # DeviceOutputID: Force = 1, Moment =2, COP =3
            # ChannelID: X =1, Y=2, Z=3

            DeviceID = LeftForcePlate_DeviceID
            FP_Origin = fields["FP"][DeviceID]["Origin"]  # Local Origin- Usually zero
            # Assumed zero for now
            FP_Center = fields["FP"][DeviceID]["WorldCenter"]  # Force Plate Center

            # Force Plate data in Global coordinate system
            # This is the force from body to force plate going into the ground
            [arrayFx, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Force"]["X"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 1, 1)
            [arrayFy, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Force"]["Y"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 1, 2)
            [arrayFz, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Force"]["Z"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 1, 3)

            [arrayMx, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Moment"]["X"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 2, 1)
            [arrayMy, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Moment"]["Y"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 2, 2)
            [arrayMz, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Moment"]["Z"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 2, 3)

            [arrayCOPx, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Center_of_Pressure"]["X"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 3, 1)
            [arrayCOPy, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Center_of_Pressure"]["Y"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 3, 2)
            [arrayCOPz, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Center_of_Pressure"]["Z"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 3, 3)

            # The individual force/moment/COP channels can end up with slightly
            # different lengths depending on how the source data was assembled;
            # use the shortest one as the hard bound for FP_FrameNumber below.
            FP_MaxIndex = min(
                len(arrayFx), len(arrayFy), len(arrayFz),
                len(arrayMx), len(arrayMy), len(arrayMz),
                len(arrayCOPx), len(arrayCOPy), len(arrayCOPz),
            ) - 1

            GRF = np.array([0.0, 0.0, 0.0])  # Ground Reaction Force
            GRT = np.array([0.0, 0.0, 0.0])  # Ground Reaction Torque
            COP = np.array([0.0, 0.0, 0.0])  # Center of Pressure
            COP_Pelvis = np.array([0.0, 0.0, 0.0])  # Center of Pressure w.r.t. Pelvis

            LeftAnkleForceLab = np.array([0.0, 0.0, 0.0])
            LeftKneeForceLab = np.array([0.0, 0.0, 0.0])
            LeftHipForceLab = np.array([0.0, 0.0, 0.0])
            LeftAnkleMoment_Foot = np.array([0.0, 0.0, 0.0])
            LeftKneeMoment_Shank = np.array([0.0, 0.0, 0.0])
            LeftHipMoment_Thigh = np.array([0.0, 0.0, 0.0])
            LeftAnklePower = np.array([0.0, 0.0, 0.0])
            LeftKneePower = np.array([0.0, 0.0, 0.0])
            LeftHipPower = np.array([0.0, 0.0, 0.0])
            # Batched left distal-to-proximal inverse dynamics.
            _batch_frames = np.arange(StartFrame, EndFrame)
            _batch_slice = slice(StartFrame, EndFrame)
            _batch_count = len(_batch_frames)
            COP = np.broadcast_to(COP, (_batch_count, 3)).copy()
            GRF = np.broadcast_to(GRF, (_batch_count, 3)).copy()
            GRT = np.broadcast_to(GRT, (_batch_count, 3)).copy()
            LeftAnkleForceLab = np.broadcast_to(LeftAnkleForceLab, (_batch_count, 3)).copy()
            LeftAnkleMoment_Foot = np.broadcast_to(LeftAnkleMoment_Foot, (_batch_count, 3)).copy()
            LeftAnklePower = np.broadcast_to(LeftAnklePower, (_batch_count, 3)).copy()
            LeftHipForceLab = np.broadcast_to(LeftHipForceLab, (_batch_count, 3)).copy()
            LeftHipMoment_Thigh = np.broadcast_to(LeftHipMoment_Thigh, (_batch_count, 3)).copy()
            LeftHipPower = np.broadcast_to(LeftHipPower, (_batch_count, 3)).copy()
            LeftKneeForceLab = np.broadcast_to(LeftKneeForceLab, (_batch_count, 3)).copy()
            LeftKneeMoment_Shank = np.broadcast_to(LeftKneeMoment_Shank, (_batch_count, 3)).copy()
            LeftKneePower = np.broadcast_to(LeftKneePower, (_batch_count, 3)).copy()
            Sign = -1
            SacralMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(SacralMarkerX)[_batch_slice], Direction *
                np.asarray(SacralMarkerY)[_batch_slice], np.asarray(SacralMarkerZ)[_batch_slice])
            )
            LeftASISMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftASISMarkerX)[_batch_slice], Direction *
                np.asarray(LeftASISMarkerY)[_batch_slice], np.asarray(LeftASISMarkerZ)[_batch_slice])
            )
            RightASISMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightASISMarkerX)[_batch_slice], Direction *
                np.asarray(RightASISMarkerY)[_batch_slice], np.asarray(RightASISMarkerZ)[_batch_slice])
            )
            LeftThighMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftThighMarkerX)[_batch_slice], Direction *
                np.asarray(LeftThighMarkerY)[_batch_slice], np.asarray(LeftThighMarkerZ)[_batch_slice])
            )
            LeftLateralKneeMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftLateralKneeMarkerX)[_batch_slice],
                Direction * np.asarray(LeftLateralKneeMarkerY)[_batch_slice],
                np.asarray(LeftLateralKneeMarkerZ)[_batch_slice])
            )
            LeftTibialMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftTibialMarkerX)[_batch_slice], Direction *
                np.asarray(LeftTibialMarkerY)[_batch_slice], np.asarray(LeftTibialMarkerZ)[_batch_slice])
            )
            LeftLateralAnkleMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftLateralAnkleMarkerX)[_batch_slice],
                Direction * np.asarray(LeftLateralAnkleMarkerY)[_batch_slice],
                np.asarray(LeftLateralAnkleMarkerZ)[_batch_slice])
            )
            LeftToeMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftToeMarkerX)[_batch_slice], Direction *
                np.asarray(LeftToeMarkerY)[_batch_slice], np.asarray(LeftToeMarkerZ)[_batch_slice])
            )
            LeftMedialAnkleMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftMedialAnkleMarkerX)[_batch_slice],
                Direction * np.asarray(LeftMedialAnkleMarkerY)[_batch_slice],
                np.asarray(LeftMedialAnkleMarkerZ)[_batch_slice])
            )
            LeftHeelMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftHeelMarkerX)[_batch_slice], Direction *
                np.asarray(LeftHeelMarkerY)[_batch_slice], np.asarray(LeftHeelMarkerZ)[_batch_slice])
            )
            if LeftTibialTriadCheck is True:
                LeftTibialUpperMarker = (
                    math.FrameVector(_batch_count, Direction * np.asarray(LeftTibialUpperMarkerX)[_batch_slice],
                    Direction * np.asarray(LeftTibialUpperMarkerY)[_batch_slice],
                    np.asarray(LeftTibialUpperMarkerZ)[_batch_slice])
                )
                LeftTibialLowerMarker = (
                    math.FrameVector(_batch_count, Direction * np.asarray(LeftTibialLowerMarkerX)[_batch_slice],
                    Direction * np.asarray(LeftTibialLowerMarkerY)[_batch_slice],
                    np.asarray(LeftTibialLowerMarkerZ)[_batch_slice])
                )
            LeftHipCenterLab = (
                math.FrameVector(_batch_count, Direction * np.asarray(arrayLeftHipCenter[0])[_batch_slice],
                Direction * np.asarray(arrayLeftHipCenter[1])[_batch_slice],
                np.asarray(arrayLeftHipCenter[2])[_batch_slice])
            )
            LeftKneeCenterLab = (
                math.FrameVector(_batch_count, Direction * np.asarray(arrayLeftKneeCenter[0])[_batch_slice],
                Direction * np.asarray(arrayLeftKneeCenter[1])[_batch_slice],
                np.asarray(arrayLeftKneeCenter[2])[_batch_slice])
            )
            LeftAnkleCenterLab = (
                math.FrameVector(_batch_count, Direction * np.asarray(arrayLeftAnkleCenter[0])[_batch_slice],
                Direction * np.asarray(arrayLeftAnkleCenter[1])[_batch_slice],
                np.asarray(arrayLeftAnkleCenter[2])[_batch_slice])
            )
            LeftThighCenterOfMass = (
                math.FrameVector(_batch_count, Direction * np.asarray(arrayLeftThighCenterOfMass[0])[_batch_slice],
                Direction * np.asarray(arrayLeftThighCenterOfMass[1])[_batch_slice],
                np.asarray(arrayLeftThighCenterOfMass[2])[_batch_slice])
            )
            LeftShankCenterOfMass = (
                math.FrameVector(_batch_count, Direction * np.asarray(arrayLeftShankCenterOfMass[0])[_batch_slice],
                Direction * np.asarray(arrayLeftShankCenterOfMass[1])[_batch_slice],
                np.asarray(arrayLeftShankCenterOfMass[2])[_batch_slice])
            )
            LeftFootCenterOfMass = (
                math.FrameVector(_batch_count, Direction * np.asarray(arrayLeftFootCenterOfMass[0])[_batch_slice],
                Direction * np.asarray(arrayLeftFootCenterOfMass[1])[_batch_slice],
                np.asarray(arrayLeftFootCenterOfMass[2])[_batch_slice])
            )
            LeftThighRadiusOfGyration = math.RadiusOfGyration(LeftHipCenterLab, LeftKneeCenterLab, 0.323, 0.323, 0.187) / 1000.0
            LeftShankRadiusOfGyration = math.RadiusOfGyration(LeftKneeCenterLab, LeftAnkleCenterLab, 0.302, 0.302, 0.087) / 1000.0
            LeftFootRadiusOfGyration = math.RadiusOfGyration(LeftAnkleCenterLab, LeftToeMarker, 0.148, 0.475, 0.475) / 1000.0
            LeftThighMassMomentOfInertia = ThighMass * np.square(LeftThighRadiusOfGyration)
            LeftShankMassMomentOfInertia = ShankMass * np.square(LeftShankRadiusOfGyration)
            LeftFootMassMomentOfInertia = FootMass * np.square(LeftFootRadiusOfGyration)
            FP_FrameNumber = np.asarray(_batch_frames * FP_FrameRate / MarkerFrameRate, dtype=np.intp)
            FP_FrameNumber = np.minimum(FP_FrameNumber, FP_MaxIndex)
            Tz = (
                np.asarray(arrayMz)[FP_FrameNumber] + np.asarray(arrayFx)[FP_FrameNumber] *
                (np.asarray(arrayCOPy)[FP_FrameNumber] - FP_Center[1] + FP_Origin[1]) -
                np.asarray(arrayFy)[FP_FrameNumber] * (np.asarray(arrayCOPx)[FP_FrameNumber] - FP_Center[0] +
                FP_Origin[0])
            )
            GRF[..., 0] = -Direction * np.asarray(arrayFx)[FP_FrameNumber]
            GRF[..., 1] = -Direction * np.asarray(arrayFy)[FP_FrameNumber]
            GRF[..., 2] = -np.asarray(arrayFz)[FP_FrameNumber]
            GRT[..., 2] = -Tz / 1000.0
            COP[..., 0] = Direction * np.asarray(arrayCOPx)[FP_FrameNumber]
            COP[..., 1] = Direction * np.asarray(arrayCOPy)[FP_FrameNumber]
            COP[..., 2] = 0
            [EPelvisTech, MidASISLab] = gait.TechCS_Pelvis_Newington(LeftASISMarker, RightASISMarker, SacralMarker)
            EPelvisAnat = math.TransformAnatCoorSysFromTechCoors(self.valueEPelvisAnatRelTech, EPelvisTech)
            LeftEThighTech = gait.TechCS_Thigh_Newington('Left', LeftHipCenterLab, LeftThighMarker, LeftLateralKneeMarker)
            LeftEThighAnat = math.TransformAnatCoorSysFromTechCoors(self.valueLeftEThighAnatRelTech, LeftEThighTech)
            if LeftTibialTriadCheck is True:
                LeftEShankTech = gait.TechCS_Shank_Newington('Left', LeftTibialUpperMarker, LeftTibialLowerMarker, LeftTibialMarker)
            else:
                LeftEShankTech = gait.TechCS_Shank_Newington('Left', LeftKneeCenterLab, LeftTibialMarker, LeftLateralAnkleMarker)
            LeftEShankProximalAnat = math.TransformAnatCoorSysFromTechCoors(self.valueLeftEShankProximalAnatRelTech, LeftEShankTech)
            LeftEShankDistalAnat = math.TransformAnatCoorSysFromTechCoors(self.valueLeftEShankDistalAnatRelTech, LeftEShankTech)
            if LeftMedialAnkleMarkerDropOff == 0:
                LeftEShankProximalAnat = (
                    gait.AnatCS_Shank_Proximal_Newington('Left', LeftKneeCenterLab, LeftLateralKneeMarker,
                    LeftAnkleCenterLab)
                )
                LeftEShankDistalAnat = gait.AnatCS_Shank_Distal_VCM('Left', LeftKneeCenterLab, LeftAnkleCenterLab, LeftLateralAnkleMarker)
            LeftEFootTech = gait.TechCS_Foot_Newington('Left', LeftKneeCenterLab, LeftAnkleCenterLab, LeftToeMarker)
            LeftEFootAnat = math.TransformAnatCoorSysFromTechCoors(self.valueLeftEFootAnatRelTech, LeftEFootTech)
            try:
                LeftEFootTibAnat = math.TransformAnatCoorSysFromTechCoors(self.valueLeftEFootAnat2RelTech, LeftEFootTech)
            except:
                LeftEFootTibAnat = np.matrix([[0.0 for m in range(3)] for n in range(3)])
            # Ankle stage: all frames, using measured force-plate samples.
            LeftAnkleForceLab[..., 0] = (
                FootMass * Direction * np.asarray(arrayLeftFootLinearAccelerationLab[0])[_batch_slice] / 1000.0 -
                GRF[..., 0]
            )
            LeftAnkleForceLab[..., 1] = (
                FootMass * Direction * np.asarray(arrayLeftFootLinearAccelerationLab[1])[_batch_slice] / 1000.0 -
                GRF[..., 1]
            )
            LeftAnkleForceLab[..., 2] = (
                FootMass * np.asarray(arrayLeftFootLinearAccelerationLab[2])[_batch_slice] / 1000.0 - GRF[..., 2] +
                FootMass * 9.81
            )
            ProximalVector = LeftAnkleCenterLab - LeftFootCenterOfMass
            DistalVector = COP - LeftFootCenterOfMass
            MomentFromProximalForce = np.cross(ProximalVector, LeftAnkleForceLab) / 1000.0
            MomentFromDistalForce = np.cross(DistalVector, GRF) / 1000.0
            MomentFromProximalForce_Foot = math.TransformVectorIntoMovingCoors(MomentFromProximalForce, LeftEFootAnat)
            MomentfromDistalForce_Foot = math.TransformVectorIntoMovingCoors(MomentFromDistalForce, LeftEFootAnat)
            GRT_Foot = math.TransformVectorIntoMovingCoors(GRT, LeftEFootAnat)
            LeftFootAnglesVelocityLab = (
                math.FrameVector(_batch_count, np.asarray(arrayLeftFootAnglesVelocityLab[0])[_batch_slice],
                np.asarray(arrayLeftFootAnglesVelocityLab[1])[_batch_slice],
                np.asarray(arrayLeftFootAnglesVelocityLab[2])[_batch_slice])
            )
            LeftFootAnglesAccelerationLab = (
                math.FrameVector(_batch_count, np.asarray(arrayLeftFootAnglesAccelerationLab[0])[_batch_slice],
                np.asarray(arrayLeftFootAnglesAccelerationLab[1])[_batch_slice],
                np.asarray(arrayLeftFootAnglesAccelerationLab[2])[_batch_slice])
            )
            LeftAnkleAnglesVelocityShank = (
                math.FrameVector(_batch_count, np.asarray(arrayLeftAnkleAnglesVelocityShank[0])[_batch_slice],
                np.asarray(arrayLeftAnkleAnglesVelocityShank[1])[_batch_slice],
                np.asarray(arrayLeftAnkleAnglesVelocityShank[2])[_batch_slice])
            )
            LeftFootAnglesVelocity_Foot = math.TransformVectorIntoMovingCoors(LeftFootAnglesVelocityLab, LeftEFootAnat)
            LeftFootAnglesAcceleration_Foot = math.TransformVectorIntoMovingCoors(LeftFootAnglesAccelerationLab, LeftEFootAnat)
            if self.ShankCoordinateSystem == 'Distal':
                LeftAnkleAnglesVelocityLab = math.TransformVectorIntoLabCoors(LeftAnkleAnglesVelocityShank, LeftEShankDistalAnat)
            if self.ShankCoordinateSystem == 'Proximal':
                LeftAnkleAnglesVelocityLab = math.TransformVectorIntoLabCoors(LeftAnkleAnglesVelocityShank, LeftEShankProximalAnat)
            LeftAnkleAnglesVelocity_Foot = math.TransformVectorIntoMovingCoors(LeftAnkleAnglesVelocityLab, LeftEFootAnat)
            LeftAnkleMoment_Foot[..., 0] = (
                LeftFootMassMomentOfInertia[..., 0] * LeftFootAnglesAcceleration_Foot[..., 0] +
                (LeftFootMassMomentOfInertia[..., 2] - LeftFootMassMomentOfInertia[..., 1]) *
                LeftFootAnglesVelocity_Foot[..., 1] * LeftFootAnglesVelocity_Foot[..., 2] -
                MomentFromProximalForce_Foot[..., 0] - MomentfromDistalForce_Foot[..., 0] - GRT_Foot[..., 0]
            )
            LeftAnkleMoment_Foot[..., 1] = (
                LeftFootMassMomentOfInertia[..., 1] * LeftFootAnglesAcceleration_Foot[..., 1] +
                (LeftFootMassMomentOfInertia[..., 0] - LeftFootMassMomentOfInertia[..., 2]) *
                LeftFootAnglesVelocity_Foot[..., 2] * LeftFootAnglesVelocity_Foot[..., 0] -
                MomentFromProximalForce_Foot[..., 1] - MomentfromDistalForce_Foot[..., 1] - GRT_Foot[..., 1]
            )
            LeftAnkleMoment_Foot[..., 2] = (
                LeftFootMassMomentOfInertia[..., 2] * LeftFootAnglesAcceleration_Foot[..., 2] +
                (LeftFootMassMomentOfInertia[..., 1] - LeftFootMassMomentOfInertia[..., 0]) *
                LeftFootAnglesVelocity_Foot[..., 0] * LeftFootAnglesVelocity_Foot[..., 1] -
                MomentFromProximalForce_Foot[..., 2] - MomentfromDistalForce_Foot[..., 2] - GRT_Foot[..., 2]
            )
            LeftAnkleMomentLab = math.TransformVectorIntoLabCoors(LeftAnkleMoment_Foot, LeftEFootAnat)
            LeftAnklePower[..., 0] = LeftAnkleMoment_Foot[..., 0] * LeftAnkleAnglesVelocity_Foot[..., 0]
            LeftAnklePower[..., 1] = LeftAnkleMoment_Foot[..., 1] * LeftAnkleAnglesVelocity_Foot[..., 1]
            LeftAnklePower[..., 2] = LeftAnkleMoment_Foot[..., 2] * LeftAnkleAnglesVelocity_Foot[..., 2]
            LeftAnklePowerTotal = np.sum(LeftAnkleMoment_Foot * LeftAnkleAnglesVelocity_Foot, axis=-1)
            arrayLeftAnkleMoment[0][_batch_slice] = np.broadcast_to(-Sign * LeftAnkleMoment_Foot[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftAnkleMoment[1][_batch_slice] = np.broadcast_to(LeftAnkleMoment_Foot[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftAnkleMoment[2][_batch_slice] = np.broadcast_to(-Sign * LeftAnkleMoment_Foot[..., 2] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftAnklePower[0][_batch_slice] = np.broadcast_to(LeftAnklePower[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftAnklePower[1][_batch_slice] = np.broadcast_to(LeftAnklePower[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftAnklePower[2][_batch_slice] = np.broadcast_to(LeftAnklePower[..., 2] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftAnklePowerTotal[0][_batch_slice] = np.broadcast_to(0, (_batch_count,))
            arrayLeftAnklePowerTotal[1][_batch_slice] = np.broadcast_to(0, (_batch_count,))
            arrayLeftAnklePowerTotal[2][_batch_slice] = np.broadcast_to(LeftAnklePowerTotal / float(self.valueBodyMass), (_batch_count,))
            LeftAnkleForceFoot = math.TransformVectorIntoMovingCoors(LeftAnkleForceLab, LeftEFootTibAnat)
            arrayLeftAnkleJRF[0][_batch_slice] = np.broadcast_to(LeftAnkleForceFoot[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftAnkleJRF[1][_batch_slice] = np.broadcast_to(Sign * LeftAnkleForceFoot[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftAnkleJRF[2][_batch_slice] = np.broadcast_to(LeftAnkleForceFoot[..., 2] / float(self.valueBodyMass), (_batch_count,))
            LeftAnkleForceLab = -LeftAnkleForceLab
            LeftAnkleMomentLab = -LeftAnkleMomentLab
            # Knee stage depends on the completed ankle forces and moments.
            LeftKneeForceLab[..., 0] = (
                ShankMass * Direction * np.asarray(arrayLeftShankLinearAccelerationLab[0])[_batch_slice] / 1000.0 -
                LeftAnkleForceLab[..., 0]
            )
            LeftKneeForceLab[..., 1] = (
                ShankMass * Direction * np.asarray(arrayLeftShankLinearAccelerationLab[1])[_batch_slice] / 1000.0 -
                LeftAnkleForceLab[..., 1]
            )
            LeftKneeForceLab[..., 2] = (
                ShankMass * np.asarray(arrayLeftShankLinearAccelerationLab[2])[_batch_slice] / 1000.0 -
                LeftAnkleForceLab[..., 2] + FootMass * 9.81
            )
            ProximalVector = LeftKneeCenterLab - LeftShankCenterOfMass
            DistalVector = LeftAnkleCenterLab - LeftShankCenterOfMass
            MomentFromProximalForce = np.cross(ProximalVector, LeftKneeForceLab) / 1000.0
            MomentFromDistalForce = np.cross(DistalVector, LeftAnkleForceLab) / 1000.0
            if self.ShankCoordinateSystem == 'Distal':
                MomentFromProximalForce_Shank = math.TransformVectorIntoMovingCoors(MomentFromProximalForce, LeftEShankDistalAnat)
                MomentfromDistalForce_Shank = math.TransformVectorIntoMovingCoors(MomentFromDistalForce, LeftEShankDistalAnat)
                LeftAnkleMoment_Shank = math.TransformVectorIntoMovingCoors(LeftAnkleMomentLab, LeftEShankDistalAnat)
                LeftShankAnglesVelocityLab = (
                    math.FrameVector(_batch_count, np.asarray(arrayLeftShankAnglesVelocityLab[0])[_batch_slice],
                    np.asarray(arrayLeftShankAnglesVelocityLab[1])[_batch_slice],
                    np.asarray(arrayLeftShankAnglesVelocityLab[2])[_batch_slice])
                )
                LeftShankAnglesAccelerationLab = (
                    math.FrameVector(_batch_count, np.asarray(arrayLeftShankAnglesAccelerationLab[0])[_batch_slice],
                    np.asarray(arrayLeftShankAnglesAccelerationLab[1])[_batch_slice],
                    np.asarray(arrayLeftShankAnglesAccelerationLab[2])[_batch_slice])
                )
                LeftKneeAnglesVelocityThigh = (
                    math.FrameVector(_batch_count, np.asarray(arrayLeftKneeAnglesVelocityThigh[0])[_batch_slice],
                    np.asarray(arrayLeftKneeAnglesVelocityThigh[1])[_batch_slice],
                    np.asarray(arrayLeftKneeAnglesVelocityThigh[2])[_batch_slice])
                )
                LeftShankAnglesVelocity_Shank = math.TransformVectorIntoMovingCoors(LeftShankAnglesVelocityLab, LeftEShankDistalAnat)
                LeftShankAnglesAcceleration_Shank = math.TransformVectorIntoMovingCoors(LeftShankAnglesAccelerationLab, LeftEShankDistalAnat)
                LeftKneeAnglesVelocityLab = math.TransformVectorIntoLabCoors(LeftKneeAnglesVelocityThigh, LeftEThighAnat)
                LeftKneeAnglesVelocity_Shank = math.TransformVectorIntoMovingCoors(LeftKneeAnglesVelocityLab, LeftEShankDistalAnat)
            if self.ShankCoordinateSystem == 'Proximal':
                MomentFromProximalForce_Shank = math.TransformVectorIntoMovingCoors(MomentFromProximalForce, LeftEShankProximalAnat)
                MomentfromDistalForce_Shank = math.TransformVectorIntoMovingCoors(MomentFromDistalForce, LeftEShankProximalAnat)
                LeftAnkleMoment_Shank = math.TransformVectorIntoMovingCoors(LeftAnkleMomentLab, LeftEShankProximalAnat)
                LeftShankAnglesVelocityLab = (
                    math.FrameVector(_batch_count, np.asarray(arrayLeftShankAnglesVelocityLab[0])[_batch_slice],
                    np.asarray(arrayLeftShankAnglesVelocityLab[1])[_batch_slice],
                    np.asarray(arrayLeftShankAnglesVelocityLab[2])[_batch_slice])
                )
                LeftShankAnglesAccelerationLab = (
                    math.FrameVector(_batch_count, np.asarray(arrayLeftShankAnglesAccelerationLab[0])[_batch_slice],
                    np.asarray(arrayLeftShankAnglesAccelerationLab[1])[_batch_slice],
                    np.asarray(arrayLeftShankAnglesAccelerationLab[2])[_batch_slice])
                )
                LeftKneeAnglesVelocityThigh = (
                    math.FrameVector(_batch_count, np.asarray(arrayLeftKneeAnglesVelocityThigh[0])[_batch_slice],
                    np.asarray(arrayLeftKneeAnglesVelocityThigh[1])[_batch_slice],
                    np.asarray(arrayLeftKneeAnglesVelocityThigh[2])[_batch_slice])
                )
                LeftShankAnglesVelocity_Shank = math.TransformVectorIntoMovingCoors(LeftShankAnglesVelocityLab, LeftEShankProximalAnat)
                LeftShankAnglesAcceleration_Shank = math.TransformVectorIntoMovingCoors(LeftShankAnglesAccelerationLab, LeftEShankProximalAnat)
                LeftKneeAnglesVelocityLab = math.TransformVectorIntoLabCoors(LeftKneeAnglesVelocityThigh, LeftEThighAnat)
                LeftKneeAnglesVelocity_Shank = math.TransformVectorIntoMovingCoors(LeftKneeAnglesVelocityLab, LeftEShankProximalAnat)
            LeftKneeMoment_Shank[..., 0] = (
                LeftShankMassMomentOfInertia[..., 0] * LeftShankAnglesAcceleration_Shank[..., 0] +
                (LeftShankMassMomentOfInertia[..., 2] - LeftShankMassMomentOfInertia[..., 1]) *
                LeftShankAnglesVelocity_Shank[..., 1] * LeftShankAnglesVelocity_Shank[..., 2] -
                MomentFromProximalForce_Shank[..., 0] - MomentfromDistalForce_Shank[..., 0] -
                LeftAnkleMoment_Shank[..., 0]
            )
            LeftKneeMoment_Shank[..., 1] = (
                LeftShankMassMomentOfInertia[..., 1] * LeftShankAnglesAcceleration_Shank[..., 1] +
                (LeftShankMassMomentOfInertia[..., 0] - LeftShankMassMomentOfInertia[..., 2]) *
                LeftShankAnglesVelocity_Shank[..., 2] * LeftShankAnglesVelocity_Shank[..., 0] -
                MomentFromProximalForce_Shank[..., 1] - MomentfromDistalForce_Shank[..., 1] -
                LeftAnkleMoment_Shank[..., 1]
            )
            LeftKneeMoment_Shank[..., 2] = (
                LeftShankMassMomentOfInertia[..., 2] * LeftShankAnglesAcceleration_Shank[..., 2] +
                (LeftShankMassMomentOfInertia[..., 1] - LeftShankMassMomentOfInertia[..., 0]) *
                LeftShankAnglesVelocity_Shank[..., 0] * LeftShankAnglesVelocity_Shank[..., 1] -
                MomentFromProximalForce_Shank[..., 2] - MomentfromDistalForce_Shank[..., 2] -
                LeftAnkleMoment_Shank[..., 2]
            )
            if self.ShankCoordinateSystem == 'Distal':
                LeftKneeMomentLab = math.TransformVectorIntoLabCoors(LeftKneeMoment_Shank, LeftEShankDistalAnat)
            if self.ShankCoordinateSystem == 'Proximal':
                LeftKneeMomentLab = math.TransformVectorIntoLabCoors(LeftKneeMoment_Shank, LeftEShankProximalAnat)
            LeftKneePower[..., 0] = LeftKneeMoment_Shank[..., 0] * LeftKneeAnglesVelocity_Shank[..., 0]
            LeftKneePower[..., 1] = LeftKneeMoment_Shank[..., 1] * LeftKneeAnglesVelocity_Shank[..., 1]
            LeftKneePower[..., 2] = LeftKneeMoment_Shank[..., 2] * LeftKneeAnglesVelocity_Shank[..., 2]
            LeftKneePowerTotal = np.sum(LeftKneeMoment_Shank * LeftKneeAnglesVelocity_Shank, axis=-1)
            arrayLeftKneeMoment[0][_batch_slice] = np.broadcast_to(-Sign * LeftKneeMoment_Shank[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftKneeMoment[1][_batch_slice] = np.broadcast_to(-LeftKneeMoment_Shank[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftKneeMoment[2][_batch_slice] = np.broadcast_to(-Sign * LeftKneeMoment_Shank[..., 2] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftKneePower[0][_batch_slice] = np.broadcast_to(LeftKneePower[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftKneePower[1][_batch_slice] = np.broadcast_to(LeftKneePower[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftKneePower[2][_batch_slice] = np.broadcast_to(LeftKneePower[..., 2] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftKneePowerTotal[0][_batch_slice] = np.broadcast_to(0, (_batch_count,))
            arrayLeftKneePowerTotal[1][_batch_slice] = np.broadcast_to(0, (_batch_count,))
            arrayLeftKneePowerTotal[2][_batch_slice] = np.broadcast_to(LeftKneePowerTotal / float(self.valueBodyMass), (_batch_count,))
            LeftKneeForceTib = math.TransformVectorIntoMovingCoors(LeftKneeForceLab, LeftEShankProximalAnat)
            arrayLeftKneeJRF[0][_batch_slice] = np.broadcast_to(LeftKneeForceTib[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftKneeJRF[1][_batch_slice] = np.broadcast_to(Sign * LeftKneeForceTib[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftKneeJRF[2][_batch_slice] = np.broadcast_to(LeftKneeForceTib[..., 2] / float(self.valueBodyMass), (_batch_count,))
            LeftKneeForceLab = -LeftKneeForceLab
            LeftKneeMomentLab = -LeftKneeMomentLab
            # Hip stage depends on the completed knee forces and moments.
            LeftHipForceLab[..., 0] = (
                ThighMass * Direction * np.asarray(arrayLeftThighLinearAccelerationLab[0])[_batch_slice] / 1000.0 -
                LeftKneeForceLab[..., 0]
            )
            LeftHipForceLab[..., 1] = (
                ThighMass * Direction * np.asarray(arrayLeftThighLinearAccelerationLab[1])[_batch_slice] / 1000.0 -
                LeftKneeForceLab[..., 1]
            )
            LeftHipForceLab[..., 2] = (
                ThighMass * np.asarray(arrayLeftThighLinearAccelerationLab[2])[_batch_slice] / 1000.0 -
                LeftKneeForceLab[..., 2] + FootMass * 9.81
            )
            ProximalVector = LeftHipCenterLab - LeftThighCenterOfMass
            DistalVector = LeftKneeCenterLab - LeftThighCenterOfMass
            MomentFromProximalForce = np.cross(ProximalVector, LeftHipForceLab) / 1000.0
            MomentFromDistalForce = np.cross(DistalVector, LeftKneeForceLab) / 1000.0
            MomentFromProximalForce_Thigh = math.TransformVectorIntoMovingCoors(MomentFromProximalForce, LeftEThighAnat)
            MomentfromDistalForce_Thigh = math.TransformVectorIntoMovingCoors(MomentFromDistalForce, LeftEThighAnat)
            LeftKneeMoment_Thigh = math.TransformVectorIntoMovingCoors(LeftKneeMomentLab, LeftEThighAnat)
            LeftThighAnglesVelocityLab = (
                math.FrameVector(_batch_count, np.asarray(arrayLeftThighAnglesVelocityLab[0])[_batch_slice],
                np.asarray(arrayLeftThighAnglesVelocityLab[1])[_batch_slice],
                np.asarray(arrayLeftThighAnglesVelocityLab[2])[_batch_slice])
            )
            LeftThighAnglesAccelerationLab = (
                math.FrameVector(_batch_count, np.asarray(arrayLeftThighAnglesAccelerationLab[0])[_batch_slice],
                np.asarray(arrayLeftThighAnglesAccelerationLab[1])[_batch_slice],
                np.asarray(arrayLeftThighAnglesAccelerationLab[2])[_batch_slice])
            )
            LeftHipAnglesVelocityPelvis = (
                math.FrameVector(_batch_count, np.asarray(arrayLeftHipAnglesVelocityPelvis[0])[_batch_slice],
                np.asarray(arrayLeftHipAnglesVelocityPelvis[1])[_batch_slice],
                np.asarray(arrayLeftHipAnglesVelocityPelvis[2])[_batch_slice])
            )
            LeftThighAnglesVelocity_Thigh = math.TransformVectorIntoMovingCoors(LeftThighAnglesVelocityLab, LeftEThighAnat)
            LeftThighAnglesAcceleration_Thigh = math.TransformVectorIntoMovingCoors(LeftThighAnglesAccelerationLab, LeftEThighAnat)
            LeftHipAnglesVelocityLab = math.TransformVectorIntoLabCoors(LeftHipAnglesVelocityPelvis, EPelvisAnat)
            LeftHipAnglesVelocity_Thigh = math.TransformVectorIntoMovingCoors(LeftHipAnglesVelocityLab, LeftEThighAnat)
            LeftHipMoment_Thigh[..., 0] = (
                LeftThighMassMomentOfInertia[..., 0] * LeftThighAnglesAcceleration_Thigh[..., 0] +
                (LeftThighMassMomentOfInertia[..., 2] - LeftThighMassMomentOfInertia[..., 1]) *
                LeftThighAnglesVelocity_Thigh[..., 1] * LeftThighAnglesVelocity_Thigh[..., 2] -
                MomentFromProximalForce_Thigh[..., 0] - MomentfromDistalForce_Thigh[..., 0] -
                LeftKneeMoment_Thigh[..., 0]
            )
            LeftHipMoment_Thigh[..., 1] = (
                LeftThighMassMomentOfInertia[..., 1] * LeftThighAnglesAcceleration_Thigh[..., 1] +
                (LeftThighMassMomentOfInertia[..., 0] - LeftThighMassMomentOfInertia[..., 2]) *
                LeftThighAnglesVelocity_Thigh[..., 2] * LeftThighAnglesVelocity_Thigh[..., 0] -
                MomentFromProximalForce_Thigh[..., 1] - MomentfromDistalForce_Thigh[..., 1] -
                LeftKneeMoment_Thigh[..., 1]
            )
            LeftHipMoment_Thigh[..., 2] = (
                LeftThighMassMomentOfInertia[..., 2] * LeftThighAnglesAcceleration_Thigh[..., 2] +
                (LeftThighMassMomentOfInertia[..., 1] - LeftThighMassMomentOfInertia[..., 0]) *
                LeftThighAnglesVelocity_Thigh[..., 0] * LeftThighAnglesVelocity_Thigh[..., 1] -
                MomentFromProximalForce_Thigh[..., 2] - MomentfromDistalForce_Thigh[..., 2] -
                LeftKneeMoment_Thigh[..., 2]
            )
            LeftHipMomentLab = math.TransformVectorIntoLabCoors(LeftHipMoment_Thigh, LeftEThighAnat)
            LeftHipPower[..., 0] = LeftHipMoment_Thigh[..., 0] * LeftHipAnglesVelocity_Thigh[..., 0]
            LeftHipPower[..., 1] = LeftHipMoment_Thigh[..., 1] * LeftHipAnglesVelocity_Thigh[..., 1]
            LeftHipPower[..., 2] = LeftHipMoment_Thigh[..., 2] * LeftHipAnglesVelocity_Thigh[..., 2]
            LeftHipPowerTotal = np.sum(LeftHipMoment_Thigh * LeftHipAnglesVelocity_Thigh, axis=-1)
            arrayLeftHipMoment[0][_batch_slice] = np.broadcast_to(-Sign * LeftHipMoment_Thigh[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftHipMoment[1][_batch_slice] = np.broadcast_to(LeftHipMoment_Thigh[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftHipMoment[2][_batch_slice] = np.broadcast_to(-Sign * LeftHipMoment_Thigh[..., 2] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftHipPower[0][_batch_slice] = np.broadcast_to(LeftHipPower[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftHipPower[1][_batch_slice] = np.broadcast_to(LeftHipPower[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftHipPower[2][_batch_slice] = np.broadcast_to(LeftHipPower[..., 2] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftHipPowerTotal[0][_batch_slice] = np.broadcast_to(0, (_batch_count,))
            arrayLeftHipPowerTotal[1][_batch_slice] = np.broadcast_to(0, (_batch_count,))
            arrayLeftHipPowerTotal[2][_batch_slice] = np.broadcast_to(LeftHipPowerTotal / float(self.valueBodyMass), (_batch_count,))
            LeftHipForceThigh = math.TransformVectorIntoMovingCoors(LeftHipForceLab, LeftEThighAnat)
            arrayLeftHipJRF[0][_batch_slice] = np.broadcast_to(LeftHipForceThigh[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftHipJRF[1][_batch_slice] = np.broadcast_to(Sign * LeftHipForceThigh[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftHipJRF[2][_batch_slice] = np.broadcast_to(LeftHipForceThigh[..., 2] / float(self.valueBodyMass), (_batch_count,))
            GRF = math.TransformVectorIntoMovingCoors(GRF, ELab)
            arrayLeftGRF[0][_batch_slice] = np.broadcast_to(GRF[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftGRF[1][_batch_slice] = np.broadcast_to(Sign * GRF[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftGRF[2][_batch_slice] = np.broadcast_to(GRF[..., 2] / float(self.valueBodyMass), (_batch_count,))
            arrayLeftGRM[0][_batch_slice] = (
                np.broadcast_to(np.asarray(arrayCOPx)[FP_FrameNumber] -
                np.asarray(arrayPelvisOrigin[0])[_batch_slice], (_batch_count,))
            )
            arrayLeftGRM[1][_batch_slice] = (
                np.broadcast_to(np.asarray(arrayCOPy)[FP_FrameNumber] -
                np.asarray(arrayPelvisOrigin[1])[_batch_slice], (_batch_count,))
            )
            arrayLeftGRM[2][_batch_slice] = np.broadcast_to(Sign * GRT[..., 2] / float(self.valueBodyMass), (_batch_count,))
            COP_Pelvis = (
                math.FrameVector(_batch_count, np.asarray(arrayLeftGRM[0])[_batch_slice],
                np.asarray(arrayLeftGRM[1])[_batch_slice], np.asarray(arrayLeftGRM[2])[_batch_slice])
            )
            COP_Pelvis = math.TransformVectorIntoMovingCoors(COP_Pelvis, ELab)
            arrayLeftGRM[0][_batch_slice] = np.broadcast_to(100 * Direction * COP_Pelvis[..., 0] / self.valueLeftLegLength, (_batch_count,))
            arrayLeftGRM[1][_batch_slice] = (
                np.broadcast_to(100 * Direction * Sign * COP_Pelvis[..., 1] / self.valueLeftLegLength,
                (_batch_count,))
            )
            arrayLeftMPSum[0][_batch_slice] = (
                np.broadcast_to(np.asarray(arrayLeftHipMoment[0])[_batch_slice] +
                np.asarray(arrayLeftKneeMoment[0])[_batch_slice] +
                np.asarray(arrayLeftAnkleMoment[0])[_batch_slice], (_batch_count,))
            )
            arrayLeftMPSum[1][_batch_slice] = (
                np.broadcast_to(np.asarray(arrayLeftHipPower[0])[_batch_slice] +
                np.asarray(arrayLeftKneePower[0])[_batch_slice] + np.asarray(arrayLeftAnklePower[0])[_batch_slice],
                (_batch_count,))
            )
            arrayLeftMPSum[2][_batch_slice] = (
                np.broadcast_to(np.asarray(arrayLeftHipPowerTotal[2])[_batch_slice] +
                np.asarray(arrayLeftKneePowerTotal[2])[_batch_slice] +
                np.asarray(arrayLeftAnklePowerTotal[2])[_batch_slice], (_batch_count,))
            )
            AnkleCOP = COP - LeftAnkleCenterLab
            AnkleCOP[..., 2] = 0
            AnkleCOP_Foot = math.TransformVectorIntoMovingCoors(AnkleCOP, LeftEFootAnat)
            FL = np.linalg.norm(LeftToeMarker - LeftAnkleCenterLab, axis=-1)
            AnkleCOP_Foot_Normalized = 100 * AnkleCOP_Foot / FL[..., None]
            arrayLeftFootCoP[0][_batch_slice] = np.broadcast_to(AnkleCOP_Foot_Normalized[..., 0], (_batch_count,))
            arrayLeftFootCoP[1][_batch_slice] = np.broadcast_to(AnkleCOP_Foot_Normalized[..., 1], (_batch_count,))
            arrayLeftFootCoP[2][_batch_slice] = np.broadcast_to(0, (_batch_count,))

        if not RightForcePlate_DeviceID == "0":
            # ==================== Smooth Data before Differentiating ======================
            # Center of Mass
            arrayHATCenterOfMass = math.Smooth3DArray(
                arrayHATCenterOfMass, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayRightThighCenterOfMass = math.Smooth3DArray(
                arrayRightThighCenterOfMass, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayRightShankCenterOfMass = math.Smooth3DArray(
                arrayRightShankCenterOfMass, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayRightFootCenterOfMass = math.Smooth3DArray(
                arrayRightFootCenterOfMass, StartFrame, EndFrame, Order, WindowWidth
            )
            # Joint Centers
            arrayRightHipCenter = math.Smooth3DArray(
                arrayRightHipCenter, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayRightKneeCenter = math.Smooth3DArray(
                arrayRightKneeCenter, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayRightAnkleCenter = math.Smooth3DArray(
                arrayRightAnkleCenter, StartFrame, EndFrame, Order, WindowWidth
            )
            # Right Angles
            arrayRightTrunkAngles = math.Smooth3DArray(
                arrayRightTrunkAngles, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayRightPelvisAngles = math.Smooth3DArray(
                arrayRightPelvisAngles, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayRightThighAngles = math.Smooth3DArray(
                arrayRightThighAngles, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayRightShankAngles = math.Smooth3DArray(
                arrayRightShankAngles, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayRightFootAngles = math.Smooth3DArray(
                arrayRightFootAngles, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayRightHipAngles = math.Smooth3DArray(
                arrayRightHipAngles, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayRightKneeAngles = math.Smooth3DArray(
                arrayRightKneeAngles, StartFrame, EndFrame, Order, WindowWidth
            )
            arrayRightAnkleAngles = math.Smooth3DArray(
                arrayRightAnkleAngles, StartFrame, EndFrame, Order, WindowWidth
            )

            # ======================== Translation Variables Differentiatition ===============================
            # Center of Mass
            [arrayHATLinearVelocityLab, arrayHATLinearAccelerationLab] = (
                math.Differentiate(
                    arrayHATCenterOfMass, StartFrame, EndFrame, framecount, DeltaTime
                )
            )
            [arrayRightThighLinearVelocityLab, arrayRightThighLinearAccelerationLab] = (
                math.Differentiate(
                    arrayRightThighCenterOfMass,
                    StartFrame,
                    EndFrame,
                    framecount,
                    DeltaTime,
                )
            )
            [arrayRightShankLinearVelocityLab, arrayRightShankLinearAccelerationLab] = (
                math.Differentiate(
                    arrayRightShankCenterOfMass,
                    StartFrame,
                    EndFrame,
                    framecount,
                    DeltaTime,
                )
            )
            [arrayRightFootLinearVelocityLab, arrayRightFootLinearAccelerationLab] = (
                math.Differentiate(
                    arrayRightFootCenterOfMass,
                    StartFrame,
                    EndFrame,
                    framecount,
                    DeltaTime,
                )
            )
            # Joint Centers
            [
                arrayRightHipCenterLinearVelocityLab,
                arrayRightHipCenterLinearAccelerationLab,
            ] = math.Differentiate(
                arrayRightHipCenter, StartFrame, EndFrame, framecount, DeltaTime
            )
            [
                arrayRightKneeCenterLinearVelocityLab,
                arrayRightKneeCenterLinearAccelerationLab,
            ] = math.Differentiate(
                arrayRightKneeCenter, StartFrame, EndFrame, framecount, DeltaTime
            )
            [
                arrayRightAnkleCenterLinearVelocityLab,
                arrayRightAnkleCenterLinearAccelerationLab,
            ] = math.Differentiate(
                arrayRightAnkleCenter, StartFrame, EndFrame, framecount, DeltaTime
            )

            # ======================== Rotational Variables Differentiatition ===============================
            # Right Angles  Derivatives. Derivatives are in Reference Coordinate System. For segment- Lab CS. For Joints- Proximal Segment CS
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayRightTrunkAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [arrayRightTrunkAnglesVelocityLab, arrayRightTrunkAnglesAccelerationLab] = (
                math.AngVelAcc_Euler_YXZ(
                    arrayRightTrunkAnglesRad,
                    arrayVelocity,
                    arrayAcceleration,
                    StartFrame,
                    EndFrame,
                    framecount,
                )
            )
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayRightPelvisAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [
                arrayRightPelvisAnglesVelocityLab,
                arrayRightPelvisAnglesAccelerationLab,
            ] = math.AngVelAcc_Euler_YXZ(
                arrayRightPelvisAnglesRad,
                arrayVelocity,
                arrayAcceleration,
                StartFrame,
                EndFrame,
                framecount,
            )
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayRightThighAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [arrayRightThighAnglesVelocityLab, arrayRightThighAnglesAccelerationLab] = (
                math.AngVelAcc_Euler_YXZ(
                    arrayRightThighAnglesRad,
                    arrayVelocity,
                    arrayAcceleration,
                    StartFrame,
                    EndFrame,
                    framecount,
                )
            )
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayRightShankAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [arrayRightShankAnglesVelocityLab, arrayRightShankAnglesAccelerationLab] = (
                math.AngVelAcc_Euler_YXZ(
                    arrayRightShankAnglesRad,
                    arrayVelocity,
                    arrayAcceleration,
                    StartFrame,
                    EndFrame,
                    framecount,
                )
            )
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayRightFootAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [arrayRightFootAnglesVelocityLab, arrayRightFootAnglesAccelerationLab] = (
                math.AngVelAcc_Euler_YXZ(
                    arrayRightFootAnglesRad,
                    arrayVelocity,
                    arrayAcceleration,
                    StartFrame,
                    EndFrame,
                    framecount,
                )
            )
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayRightHipAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [
                arrayRightHipAnglesVelocityPelvis,
                arrayRightHipAnglesAccelerationPelvis,
            ] = math.AngVelAcc_Euler_YXZ(
                arrayRightHipAnglesRad,
                arrayVelocity,
                arrayAcceleration,
                StartFrame,
                EndFrame,
                framecount,
            )
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayRightKneeAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [
                arrayRightKneeAnglesVelocityThigh,
                arrayRightKneeAnglesAccelerationThigh,
            ] = math.AngVelAcc_Euler_YXZ(
                arrayRightKneeAnglesRad,
                arrayVelocity,
                arrayAcceleration,
                StartFrame,
                EndFrame,
                framecount,
            )
            [arrayVelocity, arrayAcceleration] = math.Differentiate(
                arrayRightAnkleAnglesRad, StartFrame, EndFrame, framecount, DeltaTime
            )
            [
                arrayRightAnkleAnglesVelocityShank,
                arrayRightAnkleAnglesAccelerationShank,
            ] = math.AngVelAcc_Euler_YXZ(
                arrayRightAnkleAnglesRad,
                arrayVelocity,
                arrayAcceleration,
                StartFrame,
                EndFrame,
                framecount,
            )

            # Extract Force Plate Data
            # GetDeviceChannelGlobal(DeviceID, DeviceOutputID, ChannelID)
            # DeviceOutputID: Force = 1, Moment = 2, COP = 3
            # ChannelID: X =1, Y=2, Z=3

            DeviceID = RightForcePlate_DeviceID

            FP_Origin = fields["FP"][DeviceID]["Origin"]  # Local Origin- Usually zero
            # Assumed zero for now
            FP_Center = fields["FP"][DeviceID]["WorldCenter"]  # Force Plate Center

            # Force Plate data in Global coordinate system
            # This is the force from body to force plate going into the ground
            [arrayFx, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Force"]["X"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 1, 1)
            [arrayFy, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Force"]["Y"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 1, 2)
            [arrayFz, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Force"]["Z"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 1, 3)

            [arrayMx, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Moment"]["X"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 2, 1)
            [arrayMy, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Moment"]["Y"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 2, 2)
            [arrayMz, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Moment"]["Z"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 2, 3)

            [arrayCOPx, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Center_of_Pressure"]["X"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 3, 1)
            [arrayCOPy, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Center_of_Pressure"]["Y"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 3, 2)
            [arrayCOPz, Ready, FP_FrameRate] = (
                SimForcePlate[DeviceID]["Center_of_Pressure"]["Z"],
                [],
                SimForcePlate[DeviceID]["Frequency"],
            )  # vicon.GetDeviceChannelGlobal(DeviceID, 3, 3)

            # The individual force/moment/COP channels can end up with slightly
            # different lengths depending on how the source data was assembled;
            # use the shortest one as the hard bound for FP_FrameNumber below.
            FP_MaxIndex = min(
                len(arrayFx), len(arrayFy), len(arrayFz),
                len(arrayMx), len(arrayMy), len(arrayMz),
                len(arrayCOPx), len(arrayCOPy), len(arrayCOPz),
            ) - 1

            GRF = np.array([0.0, 0.0, 0.0])  # Ground Reaction Force
            GRT = np.array([0.0, 0.0, 0.0])  # Ground Reaction Torque
            COP = np.array([0.0, 0.0, 0.0])  # Center of Pressure
            RightAnkleForceLab = np.array([0.0, 0.0, 0.0])
            RightKneeForceLab = np.array([0.0, 0.0, 0.0])
            RightHipForceLab = np.array([0.0, 0.0, 0.0])
            RightAnkleMoment_Foot = np.array([0.0, 0.0, 0.0])
            RightKneeMoment_Shank = np.array([0.0, 0.0, 0.0])
            RightHipMoment_Thigh = np.array([0.0, 0.0, 0.0])
            RightAnklePower = np.array([0.0, 0.0, 0.0])
            RightKneePower = np.array([0.0, 0.0, 0.0])
            RightHipPower = np.array([0.0, 0.0, 0.0])
            # Batched right distal-to-proximal inverse dynamics.
            _batch_frames = np.arange(StartFrame, EndFrame)
            _batch_slice = slice(StartFrame, EndFrame)
            _batch_count = len(_batch_frames)
            COP = np.broadcast_to(COP, (_batch_count, 3)).copy()
            GRF = np.broadcast_to(GRF, (_batch_count, 3)).copy()
            GRT = np.broadcast_to(GRT, (_batch_count, 3)).copy()
            RightAnkleForceLab = np.broadcast_to(RightAnkleForceLab, (_batch_count, 3)).copy()
            RightAnkleMoment_Foot = np.broadcast_to(RightAnkleMoment_Foot, (_batch_count, 3)).copy()
            RightAnklePower = np.broadcast_to(RightAnklePower, (_batch_count, 3)).copy()
            RightHipForceLab = np.broadcast_to(RightHipForceLab, (_batch_count, 3)).copy()
            RightHipMoment_Thigh = np.broadcast_to(RightHipMoment_Thigh, (_batch_count, 3)).copy()
            RightHipPower = np.broadcast_to(RightHipPower, (_batch_count, 3)).copy()
            RightKneeForceLab = np.broadcast_to(RightKneeForceLab, (_batch_count, 3)).copy()
            RightKneeMoment_Shank = np.broadcast_to(RightKneeMoment_Shank, (_batch_count, 3)).copy()
            RightKneePower = np.broadcast_to(RightKneePower, (_batch_count, 3)).copy()
            SacralMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(SacralMarkerX)[_batch_slice], Direction *
                np.asarray(SacralMarkerY)[_batch_slice], np.asarray(SacralMarkerZ)[_batch_slice])
            )
            LeftASISMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(LeftASISMarkerX)[_batch_slice], Direction *
                np.asarray(LeftASISMarkerY)[_batch_slice], np.asarray(LeftASISMarkerZ)[_batch_slice])
            )
            RightASISMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightASISMarkerX)[_batch_slice], Direction *
                np.asarray(RightASISMarkerY)[_batch_slice], np.asarray(RightASISMarkerZ)[_batch_slice])
            )
            Sign = 1
            RightThighMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightThighMarkerX)[_batch_slice], Direction *
                np.asarray(RightThighMarkerY)[_batch_slice], np.asarray(RightThighMarkerZ)[_batch_slice])
            )
            RightLateralKneeMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightLateralKneeMarkerX)[_batch_slice],
                Direction * np.asarray(RightLateralKneeMarkerY)[_batch_slice],
                np.asarray(RightLateralKneeMarkerZ)[_batch_slice])
            )
            RightTibialMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightTibialMarkerX)[_batch_slice], Direction *
                np.asarray(RightTibialMarkerY)[_batch_slice], np.asarray(RightTibialMarkerZ)[_batch_slice])
            )
            RightLateralAnkleMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightLateralAnkleMarkerX)[_batch_slice],
                Direction * np.asarray(RightLateralAnkleMarkerY)[_batch_slice],
                np.asarray(RightLateralAnkleMarkerZ)[_batch_slice])
            )
            RightToeMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightToeMarkerX)[_batch_slice], Direction *
                np.asarray(RightToeMarkerY)[_batch_slice], np.asarray(RightToeMarkerZ)[_batch_slice])
            )
            RightMedialAnkleMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightMedialAnkleMarkerX)[_batch_slice],
                Direction * np.asarray(RightMedialAnkleMarkerY)[_batch_slice],
                np.asarray(RightMedialAnkleMarkerZ)[_batch_slice])
            )
            RightHeelMarker = (
                math.FrameVector(_batch_count, Direction * np.asarray(RightHeelMarkerX)[_batch_slice], Direction *
                np.asarray(RightHeelMarkerY)[_batch_slice], np.asarray(RightHeelMarkerZ)[_batch_slice])
            )
            if RightTibialTriadCheck is True:
                RightTibialUpperMarker = (
                    math.FrameVector(_batch_count, Direction * np.asarray(RightTibialUpperMarkerX)[_batch_slice],
                    Direction * np.asarray(RightTibialUpperMarkerY)[_batch_slice],
                    np.asarray(RightTibialUpperMarkerZ)[_batch_slice])
                )
                RightTibialLowerMarker = (
                    math.FrameVector(_batch_count, Direction * np.asarray(RightTibialLowerMarkerX)[_batch_slice],
                    Direction * np.asarray(RightTibialLowerMarkerY)[_batch_slice],
                    np.asarray(RightTibialLowerMarkerZ)[_batch_slice])
                )
            RightHipCenterLab = (
                math.FrameVector(_batch_count, Direction * np.asarray(arrayRightHipCenter[0])[_batch_slice],
                Direction * np.asarray(arrayRightHipCenter[1])[_batch_slice],
                np.asarray(arrayRightHipCenter[2])[_batch_slice])
            )
            RightKneeCenterLab = (
                math.FrameVector(_batch_count, Direction * np.asarray(arrayRightKneeCenter[0])[_batch_slice],
                Direction * np.asarray(arrayRightKneeCenter[1])[_batch_slice],
                np.asarray(arrayRightKneeCenter[2])[_batch_slice])
            )
            RightAnkleCenterLab = (
                math.FrameVector(_batch_count, Direction * np.asarray(arrayRightAnkleCenter[0])[_batch_slice],
                Direction * np.asarray(arrayRightAnkleCenter[1])[_batch_slice],
                np.asarray(arrayRightAnkleCenter[2])[_batch_slice])
            )
            RightThighCenterOfMass = (
                math.FrameVector(_batch_count, Direction * np.asarray(arrayRightThighCenterOfMass[0])[_batch_slice],
                Direction * np.asarray(arrayRightThighCenterOfMass[1])[_batch_slice],
                np.asarray(arrayRightThighCenterOfMass[2])[_batch_slice])
            )
            RightShankCenterOfMass = (
                math.FrameVector(_batch_count, Direction * np.asarray(arrayRightShankCenterOfMass[0])[_batch_slice],
                Direction * np.asarray(arrayRightShankCenterOfMass[1])[_batch_slice],
                np.asarray(arrayRightShankCenterOfMass[2])[_batch_slice])
            )
            RightFootCenterOfMass = (
                math.FrameVector(_batch_count, Direction * np.asarray(arrayRightFootCenterOfMass[0])[_batch_slice],
                Direction * np.asarray(arrayRightFootCenterOfMass[1])[_batch_slice],
                np.asarray(arrayRightFootCenterOfMass[2])[_batch_slice])
            )
            RightThighRadiusOfGyration = math.RadiusOfGyration(RightHipCenterLab, RightKneeCenterLab, 0.323, 0.323, 0.187) / 1000.0
            RightShankRadiusOfGyration = math.RadiusOfGyration(RightKneeCenterLab, RightAnkleCenterLab, 0.302, 0.302, 0.087) / 1000.0
            RightFootRadiusOfGyration = math.RadiusOfGyration(RightAnkleCenterLab, RightToeMarker, 0.148, 0.475, 0.475) / 1000.0
            RightThighMassMomentOfInertia = ThighMass * np.square(RightThighRadiusOfGyration)
            RightShankMassMomentOfInertia = ShankMass * np.square(RightShankRadiusOfGyration)
            RightFootMassMomentOfInertia = FootMass * np.square(RightFootRadiusOfGyration)
            FP_FrameNumber = np.asarray(_batch_frames * FP_FrameRate / MarkerFrameRate, dtype=np.intp)
            FP_FrameNumber = np.minimum(FP_FrameNumber, FP_MaxIndex)
            Tz = (
                np.asarray(arrayMz)[FP_FrameNumber] + np.asarray(arrayFx)[FP_FrameNumber] *
                (np.asarray(arrayCOPy)[FP_FrameNumber] - FP_Center[1] + FP_Origin[1]) -
                np.asarray(arrayFy)[FP_FrameNumber] * (np.asarray(arrayCOPx)[FP_FrameNumber] - FP_Center[0] +
                FP_Origin[0])
            )
            GRF[..., 0] = -Direction * np.asarray(arrayFx)[FP_FrameNumber]
            GRF[..., 1] = -Direction * np.asarray(arrayFy)[FP_FrameNumber]
            GRF[..., 2] = -np.asarray(arrayFz)[FP_FrameNumber]
            GRT[..., 2] = -Tz / 1000.0
            COP[..., 0] = Direction * np.asarray(arrayCOPx)[FP_FrameNumber]
            COP[..., 1] = Direction * np.asarray(arrayCOPy)[FP_FrameNumber]
            COP[..., 2] = 0
            [EPelvisTech, MidASISLab] = gait.TechCS_Pelvis_Newington(LeftASISMarker, RightASISMarker, SacralMarker)
            EPelvisAnat = math.TransformAnatCoorSysFromTechCoors(self.valueEPelvisAnatRelTech, EPelvisTech)
            RightEThighTech = gait.TechCS_Thigh_Newington('Right', RightHipCenterLab, RightThighMarker, RightLateralKneeMarker)
            RightEThighAnat = math.TransformAnatCoorSysFromTechCoors(self.valueRightEThighAnatRelTech, RightEThighTech)
            if RightTibialTriadCheck is True:
                RightEShankTech = (
                    gait.TechCS_Shank_Newington('Right', RightTibialUpperMarker, RightTibialLowerMarker,
                    RightTibialMarker)
                )
            else:
                RightEShankTech = gait.TechCS_Shank_Newington('Right', RightKneeCenterLab, RightTibialMarker, RightLateralAnkleMarker)
            RightEShankProximalAnat = math.TransformAnatCoorSysFromTechCoors(self.valueRightEShankProximalAnatRelTech, RightEShankTech)
            RightEShankDistalAnat = math.TransformAnatCoorSysFromTechCoors(self.valueRightEShankDistalAnatRelTech, RightEShankTech)
            if RightMedialAnkleMarkerDropOff == 0:
                RightEShankProximalAnat = (
                    gait.AnatCS_Shank_Proximal_Newington('Right', RightKneeCenterLab, RightLateralKneeMarker,
                    RightAnkleCenterLab)
                )
                RightEShankDistalAnat = (
                    gait.AnatCS_Shank_Distal_VCM('Right', RightKneeCenterLab, RightAnkleCenterLab,
                    RightLateralAnkleMarker)
                )
            RightEFootTech = gait.TechCS_Foot_Newington('Right', RightKneeCenterLab, RightAnkleCenterLab, RightToeMarker)
            RightEFootAnat = math.TransformAnatCoorSysFromTechCoors(self.valueRightEFootAnatRelTech, RightEFootTech)
            try:
                RightEFootTibAnat = math.TransformAnatCoorSysFromTechCoors(self.valueRightEFootAnat2RelTech, RightEFootTech)
            except:
                RightEFootTibAnat = np.matrix([[0.0 for m in range(3)] for n in range(3)])
            # Ankle stage: all frames, using measured force-plate samples.
            RightAnkleForceLab[..., 0] = (
                FootMass * Direction * np.asarray(arrayRightFootLinearAccelerationLab[0])[_batch_slice] / 1000.0 -
                GRF[..., 0]
            )
            RightAnkleForceLab[..., 1] = (
                FootMass * Direction * np.asarray(arrayRightFootLinearAccelerationLab[1])[_batch_slice] / 1000.0 -
                GRF[..., 1]
            )
            RightAnkleForceLab[..., 2] = (
                FootMass * np.asarray(arrayRightFootLinearAccelerationLab[2])[_batch_slice] / 1000.0 - GRF[..., 2] +
                FootMass * 9.81
            )
            ProximalVector = RightAnkleCenterLab - RightFootCenterOfMass
            DistalVector = COP - RightFootCenterOfMass
            MomentFromProximalForce = np.cross(ProximalVector, RightAnkleForceLab) / 1000.0
            MomentFromDistalForce = np.cross(DistalVector, GRF) / 1000.0
            MomentFromProximalForce_Foot = math.TransformVectorIntoMovingCoors(MomentFromProximalForce, RightEFootAnat)
            MomentfromDistalForce_Foot = math.TransformVectorIntoMovingCoors(MomentFromDistalForce, RightEFootAnat)
            GRT_Foot = math.TransformVectorIntoMovingCoors(GRT, RightEFootAnat)
            RightFootAnglesVelocityLab = (
                math.FrameVector(_batch_count, np.asarray(arrayRightFootAnglesVelocityLab[0])[_batch_slice],
                np.asarray(arrayRightFootAnglesVelocityLab[1])[_batch_slice],
                np.asarray(arrayRightFootAnglesVelocityLab[2])[_batch_slice])
            )
            RightFootAnglesAccelerationLab = (
                math.FrameVector(_batch_count, np.asarray(arrayRightFootAnglesAccelerationLab[0])[_batch_slice],
                np.asarray(arrayRightFootAnglesAccelerationLab[1])[_batch_slice],
                np.asarray(arrayRightFootAnglesAccelerationLab[2])[_batch_slice])
            )
            RightAnkleAnglesVelocityShank = (
                math.FrameVector(_batch_count, np.asarray(arrayRightAnkleAnglesVelocityShank[0])[_batch_slice],
                np.asarray(arrayRightAnkleAnglesVelocityShank[1])[_batch_slice],
                np.asarray(arrayRightAnkleAnglesVelocityShank[2])[_batch_slice])
            )
            RightFootAnglesVelocity_Foot = math.TransformVectorIntoMovingCoors(RightFootAnglesVelocityLab, RightEFootAnat)
            RightFootAnglesAcceleration_Foot = math.TransformVectorIntoMovingCoors(RightFootAnglesAccelerationLab, RightEFootAnat)
            if self.ShankCoordinateSystem == 'Distal':
                RightAnkleAnglesVelocityLab = math.TransformVectorIntoLabCoors(RightAnkleAnglesVelocityShank, RightEShankDistalAnat)
            if self.ShankCoordinateSystem == 'Proximal':
                RightAnkleAnglesVelocityLab = math.TransformVectorIntoLabCoors(RightAnkleAnglesVelocityShank, RightEShankProximalAnat)
            RightAnkleAnglesVelocity_Foot = math.TransformVectorIntoMovingCoors(RightAnkleAnglesVelocityLab, RightEFootAnat)
            RightAnkleMoment_Foot[..., 0] = (
                RightFootMassMomentOfInertia[..., 0] * RightFootAnglesAcceleration_Foot[..., 0] +
                (RightFootMassMomentOfInertia[..., 2] - RightFootMassMomentOfInertia[..., 1]) *
                RightFootAnglesVelocity_Foot[..., 1] * RightFootAnglesVelocity_Foot[..., 2] -
                MomentFromProximalForce_Foot[..., 0] - MomentfromDistalForce_Foot[..., 0] - GRT_Foot[..., 0]
            )
            RightAnkleMoment_Foot[..., 1] = (
                RightFootMassMomentOfInertia[..., 1] * RightFootAnglesAcceleration_Foot[..., 1] +
                (RightFootMassMomentOfInertia[..., 0] - RightFootMassMomentOfInertia[..., 2]) *
                RightFootAnglesVelocity_Foot[..., 2] * RightFootAnglesVelocity_Foot[..., 0] -
                MomentFromProximalForce_Foot[..., 1] - MomentfromDistalForce_Foot[..., 1] - GRT_Foot[..., 1]
            )
            RightAnkleMoment_Foot[..., 2] = (
                RightFootMassMomentOfInertia[..., 2] * RightFootAnglesAcceleration_Foot[..., 2] +
                (RightFootMassMomentOfInertia[..., 1] - RightFootMassMomentOfInertia[..., 0]) *
                RightFootAnglesVelocity_Foot[..., 0] * RightFootAnglesVelocity_Foot[..., 1] -
                MomentFromProximalForce_Foot[..., 2] - MomentfromDistalForce_Foot[..., 2] - GRT_Foot[..., 2]
            )
            RightAnkleMomentLab = math.TransformVectorIntoLabCoors(RightAnkleMoment_Foot, RightEFootAnat)
            RightAnklePower[..., 0] = RightAnkleMoment_Foot[..., 0] * RightAnkleAnglesVelocity_Foot[..., 0]
            RightAnklePower[..., 1] = RightAnkleMoment_Foot[..., 1] * RightAnkleAnglesVelocity_Foot[..., 1]
            RightAnklePower[..., 2] = RightAnkleMoment_Foot[..., 2] * RightAnkleAnglesVelocity_Foot[..., 2]
            RightAnklePowerTotal = np.sum(RightAnkleMoment_Foot * RightAnkleAnglesVelocity_Foot, axis=-1)
            arrayRightAnkleMoment[0][_batch_slice] = np.broadcast_to(-Sign * RightAnkleMoment_Foot[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayRightAnkleMoment[1][_batch_slice] = np.broadcast_to(RightAnkleMoment_Foot[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayRightAnkleMoment[2][_batch_slice] = np.broadcast_to(-Sign * RightAnkleMoment_Foot[..., 2] / float(self.valueBodyMass), (_batch_count,))
            arrayRightAnklePower[0][_batch_slice] = np.broadcast_to(RightAnklePower[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayRightAnklePower[1][_batch_slice] = np.broadcast_to(RightAnklePower[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayRightAnklePower[2][_batch_slice] = np.broadcast_to(RightAnklePower[..., 2] / float(self.valueBodyMass), (_batch_count,))
            arrayRightAnklePowerTotal[0][_batch_slice] = np.broadcast_to(0, (_batch_count,))
            arrayRightAnklePowerTotal[1][_batch_slice] = np.broadcast_to(0, (_batch_count,))
            arrayRightAnklePowerTotal[2][_batch_slice] = np.broadcast_to(RightAnklePowerTotal / float(self.valueBodyMass), (_batch_count,))
            RightAnkleForceFoot = math.TransformVectorIntoMovingCoors(RightAnkleForceLab, RightEFootTibAnat)
            arrayRightAnkleJRF[0][_batch_slice] = np.broadcast_to(RightAnkleForceFoot[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayRightAnkleJRF[1][_batch_slice] = np.broadcast_to(Sign * RightAnkleForceFoot[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayRightAnkleJRF[2][_batch_slice] = np.broadcast_to(RightAnkleForceFoot[..., 2] / float(self.valueBodyMass), (_batch_count,))
            RightAnkleForceLab = -RightAnkleForceLab
            RightAnkleMomentLab = -RightAnkleMomentLab
            # Knee stage depends on the completed ankle forces and moments.
            RightKneeForceLab[..., 0] = (
                ShankMass * Direction * np.asarray(arrayRightShankLinearAccelerationLab[0])[_batch_slice] / 1000.0 -
                RightAnkleForceLab[..., 0]
            )
            RightKneeForceLab[..., 1] = (
                ShankMass * Direction * np.asarray(arrayRightShankLinearAccelerationLab[1])[_batch_slice] / 1000.0 -
                RightAnkleForceLab[..., 1]
            )
            RightKneeForceLab[..., 2] = (
                ShankMass * np.asarray(arrayRightShankLinearAccelerationLab[2])[_batch_slice] / 1000.0 -
                RightAnkleForceLab[..., 2] + FootMass * 9.81
            )
            ProximalVector = RightKneeCenterLab - RightShankCenterOfMass
            DistalVector = RightAnkleCenterLab - RightShankCenterOfMass
            MomentFromProximalForce = np.cross(ProximalVector, RightKneeForceLab) / 1000.0
            MomentFromDistalForce = np.cross(DistalVector, RightAnkleForceLab) / 1000.0
            if self.ShankCoordinateSystem == 'Distal':
                MomentFromProximalForce_Shank = math.TransformVectorIntoMovingCoors(MomentFromProximalForce, RightEShankDistalAnat)
                MomentfromDistalForce_Shank = math.TransformVectorIntoMovingCoors(MomentFromDistalForce, RightEShankDistalAnat)
                RightAnkleMoment_Shank = math.TransformVectorIntoMovingCoors(RightAnkleMomentLab, RightEShankDistalAnat)
                RightShankAnglesVelocityLab = (
                    math.FrameVector(_batch_count, np.asarray(arrayRightShankAnglesVelocityLab[0])[_batch_slice],
                    np.asarray(arrayRightShankAnglesVelocityLab[1])[_batch_slice],
                    np.asarray(arrayRightShankAnglesVelocityLab[2])[_batch_slice])
                )
                RightShankAnglesAccelerationLab = (
                    math.FrameVector(_batch_count, np.asarray(arrayRightShankAnglesAccelerationLab[0])[_batch_slice],
                    np.asarray(arrayRightShankAnglesAccelerationLab[1])[_batch_slice],
                    np.asarray(arrayRightShankAnglesAccelerationLab[2])[_batch_slice])
                )
                RightKneeAnglesVelocityThigh = (
                    math.FrameVector(_batch_count, np.asarray(arrayRightKneeAnglesVelocityThigh[0])[_batch_slice],
                    np.asarray(arrayRightKneeAnglesVelocityThigh[1])[_batch_slice],
                    np.asarray(arrayRightKneeAnglesVelocityThigh[2])[_batch_slice])
                )
                RightShankAnglesVelocity_Shank = math.TransformVectorIntoMovingCoors(RightShankAnglesVelocityLab, RightEShankDistalAnat)
                RightShankAnglesAcceleration_Shank = math.TransformVectorIntoMovingCoors(RightShankAnglesAccelerationLab, RightEShankDistalAnat)
                RightKneeAnglesVelocityLab = math.TransformVectorIntoLabCoors(RightKneeAnglesVelocityThigh, RightEThighAnat)
                RightKneeAnglesVelocity_Shank = math.TransformVectorIntoMovingCoors(RightKneeAnglesVelocityLab, RightEShankDistalAnat)
            if self.ShankCoordinateSystem == 'Proximal':
                MomentFromProximalForce_Shank = math.TransformVectorIntoMovingCoors(MomentFromProximalForce, RightEShankProximalAnat)
                MomentfromDistalForce_Shank = math.TransformVectorIntoMovingCoors(MomentFromDistalForce, RightEShankProximalAnat)
                RightAnkleMoment_Shank = math.TransformVectorIntoMovingCoors(RightAnkleMomentLab, RightEShankProximalAnat)
                RightShankAnglesVelocityLab = (
                    math.FrameVector(_batch_count, np.asarray(arrayRightShankAnglesVelocityLab[0])[_batch_slice],
                    np.asarray(arrayRightShankAnglesVelocityLab[1])[_batch_slice],
                    np.asarray(arrayRightShankAnglesVelocityLab[2])[_batch_slice])
                )
                RightShankAnglesAccelerationLab = (
                    math.FrameVector(_batch_count, np.asarray(arrayRightShankAnglesAccelerationLab[0])[_batch_slice],
                    np.asarray(arrayRightShankAnglesAccelerationLab[1])[_batch_slice],
                    np.asarray(arrayRightShankAnglesAccelerationLab[2])[_batch_slice])
                )
                RightKneeAnglesVelocityThigh = (
                    math.FrameVector(_batch_count, np.asarray(arrayRightKneeAnglesVelocityThigh[0])[_batch_slice],
                    np.asarray(arrayRightKneeAnglesVelocityThigh[1])[_batch_slice],
                    np.asarray(arrayRightKneeAnglesVelocityThigh[2])[_batch_slice])
                )
                RightShankAnglesVelocity_Shank = math.TransformVectorIntoMovingCoors(RightShankAnglesVelocityLab, RightEShankProximalAnat)
                RightShankAnglesAcceleration_Shank = math.TransformVectorIntoMovingCoors(RightShankAnglesAccelerationLab, RightEShankProximalAnat)
                RightKneeAnglesVelocityLab = math.TransformVectorIntoLabCoors(RightKneeAnglesVelocityThigh, RightEThighAnat)
                RightKneeAnglesVelocity_Shank = math.TransformVectorIntoMovingCoors(RightKneeAnglesVelocityLab, RightEShankProximalAnat)
            RightKneeMoment_Shank[..., 0] = (
                RightShankMassMomentOfInertia[..., 0] * RightShankAnglesAcceleration_Shank[..., 0] +
                (RightShankMassMomentOfInertia[..., 2] - RightShankMassMomentOfInertia[..., 1]) *
                RightShankAnglesVelocity_Shank[..., 1] * RightShankAnglesVelocity_Shank[..., 2] -
                MomentFromProximalForce_Shank[..., 0] - MomentfromDistalForce_Shank[..., 0] -
                RightAnkleMoment_Shank[..., 0]
            )
            RightKneeMoment_Shank[..., 1] = (
                RightShankMassMomentOfInertia[..., 1] * RightShankAnglesAcceleration_Shank[..., 1] +
                (RightShankMassMomentOfInertia[..., 0] - RightShankMassMomentOfInertia[..., 2]) *
                RightShankAnglesVelocity_Shank[..., 2] * RightShankAnglesVelocity_Shank[..., 0] -
                MomentFromProximalForce_Shank[..., 1] - MomentfromDistalForce_Shank[..., 1] -
                RightAnkleMoment_Shank[..., 1]
            )
            RightKneeMoment_Shank[..., 2] = (
                RightShankMassMomentOfInertia[..., 2] * RightShankAnglesAcceleration_Shank[..., 2] +
                (RightShankMassMomentOfInertia[..., 1] - RightShankMassMomentOfInertia[..., 0]) *
                RightShankAnglesVelocity_Shank[..., 0] * RightShankAnglesVelocity_Shank[..., 1] -
                MomentFromProximalForce_Shank[..., 2] - MomentfromDistalForce_Shank[..., 2] -
                RightAnkleMoment_Shank[..., 2]
            )
            if self.ShankCoordinateSystem == 'Distal':
                RightKneeMomentLab = math.TransformVectorIntoLabCoors(RightKneeMoment_Shank, RightEShankDistalAnat)
            if self.ShankCoordinateSystem == 'Proximal':
                RightKneeMomentLab = math.TransformVectorIntoLabCoors(RightKneeMoment_Shank, RightEShankProximalAnat)
            RightKneePower[..., 0] = RightKneeMoment_Shank[..., 0] * RightKneeAnglesVelocity_Shank[..., 0]
            RightKneePower[..., 1] = RightKneeMoment_Shank[..., 1] * RightKneeAnglesVelocity_Shank[..., 1]
            RightKneePower[..., 2] = RightKneeMoment_Shank[..., 2] * RightKneeAnglesVelocity_Shank[..., 2]
            RightKneePowerTotal = np.sum(RightKneeMoment_Shank * RightKneeAnglesVelocity_Shank, axis=-1)
            arrayRightKneeMoment[0][_batch_slice] = np.broadcast_to(-Sign * RightKneeMoment_Shank[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayRightKneeMoment[1][_batch_slice] = np.broadcast_to(-RightKneeMoment_Shank[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayRightKneeMoment[2][_batch_slice] = np.broadcast_to(-Sign * RightKneeMoment_Shank[..., 2] / float(self.valueBodyMass), (_batch_count,))
            arrayRightKneePower[0][_batch_slice] = np.broadcast_to(RightKneePower[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayRightKneePower[1][_batch_slice] = np.broadcast_to(RightKneePower[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayRightKneePower[2][_batch_slice] = np.broadcast_to(RightKneePower[..., 2] / float(self.valueBodyMass), (_batch_count,))
            arrayRightKneePowerTotal[0][_batch_slice] = np.broadcast_to(0, (_batch_count,))
            arrayRightKneePowerTotal[1][_batch_slice] = np.broadcast_to(0, (_batch_count,))
            arrayRightKneePowerTotal[2][_batch_slice] = np.broadcast_to(RightKneePowerTotal / float(self.valueBodyMass), (_batch_count,))
            RightKneeForceTib = math.TransformVectorIntoMovingCoors(RightKneeForceLab, RightEShankProximalAnat)
            arrayRightKneeJRF[0][_batch_slice] = np.broadcast_to(RightKneeForceTib[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayRightKneeJRF[1][_batch_slice] = np.broadcast_to(Sign * RightKneeForceTib[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayRightKneeJRF[2][_batch_slice] = np.broadcast_to(RightKneeForceTib[..., 2] / float(self.valueBodyMass), (_batch_count,))
            RightKneeForceLab = -RightKneeForceLab
            RightKneeMomentLab = -RightKneeMomentLab
            # Hip stage depends on the completed knee forces and moments.
            RightHipForceLab[..., 0] = (
                ThighMass * Direction * np.asarray(arrayRightThighLinearAccelerationLab[0])[_batch_slice] / 1000.0 -
                RightKneeForceLab[..., 0]
            )
            RightHipForceLab[..., 1] = (
                ThighMass * Direction * np.asarray(arrayRightThighLinearAccelerationLab[1])[_batch_slice] / 1000.0 -
                RightKneeForceLab[..., 1]
            )
            RightHipForceLab[..., 2] = (
                ThighMass * np.asarray(arrayRightThighLinearAccelerationLab[2])[_batch_slice] / 1000.0 -
                RightKneeForceLab[..., 2] + FootMass * 9.81
            )
            ProximalVector = RightHipCenterLab - RightThighCenterOfMass
            DistalVector = RightKneeCenterLab - RightThighCenterOfMass
            MomentFromProximalForce = np.cross(ProximalVector, RightHipForceLab) / 1000.0
            MomentFromDistalForce = np.cross(DistalVector, RightKneeForceLab) / 1000.0
            MomentFromProximalForce_Thigh = math.TransformVectorIntoMovingCoors(MomentFromProximalForce, RightEThighAnat)
            MomentfromDistalForce_Thigh = math.TransformVectorIntoMovingCoors(MomentFromDistalForce, RightEThighAnat)
            RightKneeMoment_Thigh = math.TransformVectorIntoMovingCoors(RightKneeMomentLab, RightEThighAnat)
            RightThighAnglesVelocityLab = (
                math.FrameVector(_batch_count, np.asarray(arrayRightThighAnglesVelocityLab[0])[_batch_slice],
                np.asarray(arrayRightThighAnglesVelocityLab[1])[_batch_slice],
                np.asarray(arrayRightThighAnglesVelocityLab[2])[_batch_slice])
            )
            RightThighAnglesAccelerationLab = (
                math.FrameVector(_batch_count, np.asarray(arrayRightThighAnglesAccelerationLab[0])[_batch_slice],
                np.asarray(arrayRightThighAnglesAccelerationLab[1])[_batch_slice],
                np.asarray(arrayRightThighAnglesAccelerationLab[2])[_batch_slice])
            )
            RightHipAnglesVelocityPelvis = (
                math.FrameVector(_batch_count, np.asarray(arrayRightHipAnglesVelocityPelvis[0])[_batch_slice],
                np.asarray(arrayRightHipAnglesVelocityPelvis[1])[_batch_slice],
                np.asarray(arrayRightHipAnglesVelocityPelvis[2])[_batch_slice])
            )
            RightThighAnglesVelocity_Thigh = math.TransformVectorIntoMovingCoors(RightThighAnglesVelocityLab, RightEThighAnat)
            RightThighAnglesAcceleration_Thigh = math.TransformVectorIntoMovingCoors(RightThighAnglesAccelerationLab, RightEThighAnat)
            RightHipAnglesVelocityLab = math.TransformVectorIntoLabCoors(RightHipAnglesVelocityPelvis, EPelvisAnat)
            RightHipAnglesVelocity_Thigh = math.TransformVectorIntoMovingCoors(RightHipAnglesVelocityLab, RightEThighAnat)
            RightHipMoment_Thigh[..., 0] = (
                RightThighMassMomentOfInertia[..., 0] * RightThighAnglesAcceleration_Thigh[..., 0] +
                (RightThighMassMomentOfInertia[..., 2] - RightThighMassMomentOfInertia[..., 1]) *
                RightThighAnglesVelocity_Thigh[..., 1] * RightThighAnglesVelocity_Thigh[..., 2] -
                MomentFromProximalForce_Thigh[..., 0] - MomentfromDistalForce_Thigh[..., 0] -
                RightKneeMoment_Thigh[..., 0]
            )
            RightHipMoment_Thigh[..., 1] = (
                RightThighMassMomentOfInertia[..., 1] * RightThighAnglesAcceleration_Thigh[..., 1] +
                (RightThighMassMomentOfInertia[..., 0] - RightThighMassMomentOfInertia[..., 2]) *
                RightThighAnglesVelocity_Thigh[..., 2] * RightThighAnglesVelocity_Thigh[..., 0] -
                MomentFromProximalForce_Thigh[..., 1] - MomentfromDistalForce_Thigh[..., 1] -
                RightKneeMoment_Thigh[..., 1]
            )
            RightHipMoment_Thigh[..., 2] = (
                RightThighMassMomentOfInertia[..., 2] * RightThighAnglesAcceleration_Thigh[..., 2] +
                (RightThighMassMomentOfInertia[..., 1] - RightThighMassMomentOfInertia[..., 0]) *
                RightThighAnglesVelocity_Thigh[..., 0] * RightThighAnglesVelocity_Thigh[..., 1] -
                MomentFromProximalForce_Thigh[..., 2] - MomentfromDistalForce_Thigh[..., 2] -
                RightKneeMoment_Thigh[..., 2]
            )
            RightHipMomentLab = math.TransformVectorIntoLabCoors(RightHipMoment_Thigh, RightEThighAnat)
            RightHipPower[..., 0] = RightHipMoment_Thigh[..., 0] * RightHipAnglesVelocity_Thigh[..., 0]
            RightHipPower[..., 1] = RightHipMoment_Thigh[..., 1] * RightHipAnglesVelocity_Thigh[..., 1]
            RightHipPower[..., 2] = RightHipMoment_Thigh[..., 2] * RightHipAnglesVelocity_Thigh[..., 2]
            RightHipPowerTotal = np.sum(RightHipMoment_Thigh * RightHipAnglesVelocity_Thigh, axis=-1)
            arrayRightHipMoment[0][_batch_slice] = np.broadcast_to(-Sign * RightHipMoment_Thigh[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayRightHipMoment[1][_batch_slice] = np.broadcast_to(RightHipMoment_Thigh[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayRightHipMoment[2][_batch_slice] = np.broadcast_to(-Sign * RightHipMoment_Thigh[..., 2] / float(self.valueBodyMass), (_batch_count,))
            arrayRightHipPower[0][_batch_slice] = np.broadcast_to(RightHipPower[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayRightHipPower[1][_batch_slice] = np.broadcast_to(RightHipPower[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayRightHipPower[2][_batch_slice] = np.broadcast_to(RightHipPower[..., 2] / float(self.valueBodyMass), (_batch_count,))
            arrayRightHipPowerTotal[0][_batch_slice] = np.broadcast_to(0, (_batch_count,))
            arrayRightHipPowerTotal[1][_batch_slice] = np.broadcast_to(0, (_batch_count,))
            arrayRightHipPowerTotal[2][_batch_slice] = np.broadcast_to(RightHipPowerTotal / float(self.valueBodyMass), (_batch_count,))
            RightHipForceThigh = math.TransformVectorIntoMovingCoors(RightHipForceLab, RightEThighAnat)
            arrayRightHipJRF[0][_batch_slice] = np.broadcast_to(RightHipForceThigh[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayRightHipJRF[1][_batch_slice] = np.broadcast_to(Sign * RightHipForceThigh[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayRightHipJRF[2][_batch_slice] = np.broadcast_to(RightHipForceThigh[..., 2] / float(self.valueBodyMass), (_batch_count,))
            GRF = math.TransformVectorIntoMovingCoors(GRF, ELab)
            arrayRightGRF[0][_batch_slice] = np.broadcast_to(GRF[..., 0] / float(self.valueBodyMass), (_batch_count,))
            arrayRightGRF[1][_batch_slice] = np.broadcast_to(Sign * GRF[..., 1] / float(self.valueBodyMass), (_batch_count,))
            arrayRightGRF[2][_batch_slice] = np.broadcast_to(GRF[..., 2] / float(self.valueBodyMass), (_batch_count,))
            arrayRightGRM[0][_batch_slice] = (
                np.broadcast_to(np.asarray(arrayCOPx)[FP_FrameNumber] -
                np.asarray(arrayPelvisOrigin[0])[_batch_slice], (_batch_count,))
            )
            arrayRightGRM[1][_batch_slice] = (
                np.broadcast_to(np.asarray(arrayCOPy)[FP_FrameNumber] -
                np.asarray(arrayPelvisOrigin[1])[_batch_slice], (_batch_count,))
            )
            arrayRightGRM[2][_batch_slice] = np.broadcast_to(Sign * GRT[..., 2] / float(self.valueBodyMass), (_batch_count,))
            COP_Pelvis = (
                math.FrameVector(_batch_count, np.asarray(arrayRightGRM[0])[_batch_slice],
                np.asarray(arrayRightGRM[1])[_batch_slice], np.asarray(arrayRightGRM[2])[_batch_slice])
            )
            COP_Pelvis = math.TransformVectorIntoMovingCoors(COP_Pelvis, ELab)
            arrayRightGRM[0][_batch_slice] = np.broadcast_to(100 * Direction * COP_Pelvis[..., 0] / self.valueRightLegLength, (_batch_count,))
            arrayRightGRM[1][_batch_slice] = (
                np.broadcast_to(100 * Sign * Direction * COP_Pelvis[..., 1] / self.valueRightLegLength,
                (_batch_count,))
            )
            arrayRightMPSum[0][_batch_slice] = (
                np.broadcast_to(np.asarray(arrayRightHipMoment[0])[_batch_slice] +
                np.asarray(arrayRightKneeMoment[0])[_batch_slice] +
                np.asarray(arrayRightAnkleMoment[0])[_batch_slice], (_batch_count,))
            )
            arrayRightMPSum[1][_batch_slice] = (
                np.broadcast_to(np.asarray(arrayRightHipPower[0])[_batch_slice] +
                np.asarray(arrayRightKneePower[0])[_batch_slice] +
                np.asarray(arrayRightAnklePower[0])[_batch_slice], (_batch_count,))
            )
            arrayRightMPSum[2][_batch_slice] = (
                np.broadcast_to(np.asarray(arrayRightHipPowerTotal[2])[_batch_slice] +
                np.asarray(arrayRightKneePowerTotal[2])[_batch_slice] +
                np.asarray(arrayRightAnklePowerTotal[2])[_batch_slice], (_batch_count,))
            )
            AnkleCOP = COP - RightAnkleCenterLab
            AnkleCOP[..., 2] = 0
            AnkleCOP_Foot = math.TransformVectorIntoMovingCoors(AnkleCOP, RightEFootAnat)
            FL = np.linalg.norm(RightToeMarker - RightAnkleCenterLab, axis=-1)
            AnkleCOP_Foot_Normalized = 100 * AnkleCOP_Foot / FL[..., None]
            arrayRightFootCoP[0][_batch_slice] = np.broadcast_to(AnkleCOP_Foot_Normalized[..., 0], (_batch_count,))
            arrayRightFootCoP[1][_batch_slice] = np.broadcast_to(-AnkleCOP_Foot_Normalized[..., 1], (_batch_count,))
            arrayRightFootCoP[2][_batch_slice] = np.broadcast_to(0, (_batch_count,))

        # =============================================================================
        #         Write Kinetics Outputs to C3D File
        # =============================================================================
        XYZNames = ["X", "Y", "Z"]
        ForcesTypes = ["Force", "Force", "Force"]
        MomentsTypes = ["Torque", "Torque", "Torque"]
        MomentsNormalizedTypes = [
            "TorqueNormalized",
            "TorqueNormalized",
            "TorqueNormalized",
        ]
        PowersNormalizedTypes = [
            "PowerNormalized",
            "PowerNormalized",
            "PowerNormalized",
        ]
        ForceNormalizedTypes = ["ForceNormalized", "ForceNormalized", "ForceNormalized"]

        # Left Moments and Power
        if not LeftForcePlate_DeviceID == "0":
            if not "LHipMoment" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LHipMoment", "Moments", XYZNames, MomentsNormalizedTypes
                )
            if not "LKneeMoment" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LKneeMoment", "Moments", XYZNames, MomentsNormalizedTypes
                )
            if not "LAnkleMoment" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LAnkleMoment", "Moments", XYZNames, MomentsNormalizedTypes
                )
            if not "LHipPower" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LHipPower", "Powers", XYZNames, PowersNormalizedTypes
                )
            if not "LKneePower" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LKneePower", "Powers", XYZNames, PowersNormalizedTypes
                )
            if not "LAnklePower" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LAnklePower", "Powers", XYZNames, PowersNormalizedTypes
                )
            if not "LHipPowerComponents" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LHipPowerComponents", "Powers", XYZNames, PowersNormalizedTypes
                )
            if not "LKneePowerComponents" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LKneePowerComponents", "Powers", XYZNames, PowersNormalizedTypes
                )
            if not "LAnklePowerComponents" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LAnklePowerComponents", "Powers", XYZNames, PowersNormalizedTypes
                )
            # Add JRFs
            if not "LAnkleForce" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LAnkleForce", "Forces", XYZNames, ForceNormalizedTypes
                )
            if not "LKneeForce" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LKneeForce", "Forces", XYZNames, ForceNormalizedTypes
                )
            if not "LHipForce" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LHipForce", "Forces", XYZNames, ForceNormalizedTypes
                )
            # Add GRFs and GRMs
            if not "LGroundReactionForce" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LGroundReactionForce", "Forces", XYZNames, ForceNormalizedTypes
                )
            if not "LGroundReactionMoment" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LGroundReactionMoment", "Moments", XYZNames, MomentsNormalizedTypes
                )
            if not "LMomentPowerSum" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LMomentPowerSum", "Moments", XYZNames, MomentsNormalizedTypes
                )
            # Add COP
            if not "LFootCoP" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "LFootCoP", "Angles", XYZNames, AnglesTypes
                )

        # Right Moments and Power
        if not RightForcePlate_DeviceID == "0":
            if not "RHipMoment" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RHipMoment", "Moments", XYZNames, MomentsNormalizedTypes
                )
            if not "RKneeMoment" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RKneeMoment", "Moments", XYZNames, MomentsNormalizedTypes
                )
            if not "RAnkleMoment" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RAnkleMoment", "Moments", XYZNames, MomentsNormalizedTypes
                )
            if not "RHipPower" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RHipPower", "Powers", XYZNames, PowersNormalizedTypes
                )
            if not "RKneePower" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RKneePower", "Powers", XYZNames, PowersNormalizedTypes
                )
            if not "RAnklePower" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RAnklePower", "Powers", XYZNames, PowersNormalizedTypes
                )
            if not "RHipPowerComponents" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RHipPowerComponents", "Powers", XYZNames, PowersNormalizedTypes
                )
            if not "RKneePowerComponents" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RKneePowerComponents", "Powers", XYZNames, PowersNormalizedTypes
                )
            if not "RAnklePowerComponents" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RAnklePowerComponents", "Powers", XYZNames, PowersNormalizedTypes
                )

            # Add JRFs
            if not "RAnkleForce" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RAnkleForce", "Forces", XYZNames, ForceNormalizedTypes
                )
            if not "RKneeForce" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RKneeForce", "Forces", XYZNames, ForceNormalizedTypes
                )
            if not "RHipForce" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RHipForce", "Forces", XYZNames, ForceNormalizedTypes
                )
            # Add GRFs and GRMs
            if not "RGroundReactionForce" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RGroundReactionForce", "Forces", XYZNames, ForceNormalizedTypes
                )
            if not "RGroundReactionMoment" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RGroundReactionMoment", "Moments", XYZNames, MomentsNormalizedTypes
                )
            if not "RMomentPowerSum" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RMomentPowerSum", "Moments", XYZNames, MomentsNormalizedTypes
                )
            # Add COP
            if not "RFootCoP" in ModelOutputs:
                self.Models.CreateModelOutput(
                    "RFootCoP", "Angles", XYZNames, AnglesTypes
                )

        # Rearrange all arrays before writing to C3D
        ReArranged_arrayLeftHipMoment = reArrangeArray(arrayLeftHipMoment)
        ReArranged_arrayLeftKneeMoment = reArrangeArray(arrayLeftKneeMoment)
        ReArranged_arrayLeftAnkleMoment = reArrangeArray(arrayLeftAnkleMoment)
        ReArranged_arrayLeftHipPower = reArrangeArray(arrayLeftHipPower)
        ReArranged_arrayLeftKneePower = reArrangeArray(arrayLeftKneePower)
        ReArranged_arrayLeftAnklePower = reArrangeArray(arrayLeftAnklePower)
        ReArranged_arrayLeftHipPowerTotal = reArrangeArray(arrayLeftHipPowerTotal)
        ReArranged_arrayLeftKneePowerTotal = reArrangeArray(arrayLeftKneePowerTotal)
        ReArranged_arrayLeftAnklePowerTotal = reArrangeArray(arrayLeftAnklePowerTotal)

        ReArranged_arrayRightHipMoment = reArrangeArray(arrayRightHipMoment)
        ReArranged_arrayRightKneeMoment = reArrangeArray(arrayRightKneeMoment)
        ReArranged_arrayRightAnkleMoment = reArrangeArray(arrayRightAnkleMoment)
        ReArranged_arrayRightHipPower = reArrangeArray(arrayRightHipPower)
        ReArranged_arrayRightKneePower = reArrangeArray(arrayRightKneePower)
        ReArranged_arrayRightAnklePower = reArrangeArray(arrayRightAnklePower)
        ReArranged_arrayRightHipPowerTotal = reArrangeArray(arrayRightHipPowerTotal)
        ReArranged_arrayRightKneePowerTotal = reArrangeArray(arrayRightKneePowerTotal)
        ReArranged_arrayRightAnklePowerTotal = reArrangeArray(arrayRightAnklePowerTotal)

        # Write Arrays to C3D Files
        # Left
        if not LeftForcePlate_DeviceID == "0":
            self.Models.SetModelOutput(
                "LHipMoment",
                ReArranged_arrayLeftHipMoment,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LKneeMoment",
                ReArranged_arrayLeftKneeMoment,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LAnkleMoment",
                ReArranged_arrayLeftAnkleMoment,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LHipPower",
                ReArranged_arrayLeftHipPowerTotal,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LKneePower",
                ReArranged_arrayLeftKneePowerTotal,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LAnklePower",
                ReArranged_arrayLeftAnklePowerTotal,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LHipPowerComponents",
                ReArranged_arrayLeftHipPower,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LKneePowerComponents",
                ReArranged_arrayLeftKneePower,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LAnklePowerComponents",
                ReArranged_arrayLeftAnklePower,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            # Add JRFs to output (not re-arranged)
            self.Models.SetModelOutput(
                "LAnkleForce",
                arrayLeftAnkleJRF,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LKneeForce",
                arrayLeftKneeJRF,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LHipForce",
                arrayLeftHipJRF,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            # Add GRFs and GRMs to output (not re-arranged)
            self.Models.SetModelOutput(
                "LGroundReactionForce",
                arrayLeftGRF,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LGroundReactionMoment",
                arrayLeftGRM,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            # Add Moment and Power Sums and Foot COP
            self.Models.SetModelOutput(
                "LMomentPowerSum",
                arrayLeftMPSum,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "LFootCoP",
                arrayLeftFootCoP,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )

        if not RightForcePlate_DeviceID == "0":
            self.Models.SetModelOutput(
                "RHipMoment",
                ReArranged_arrayRightHipMoment,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RKneeMoment",
                ReArranged_arrayRightKneeMoment,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RAnkleMoment",
                ReArranged_arrayRightAnkleMoment,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RHipPower",
                ReArranged_arrayRightHipPowerTotal,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RKneePower",
                ReArranged_arrayRightKneePowerTotal,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RAnklePower",
                ReArranged_arrayRightAnklePowerTotal,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RHipPowerComponents",
                ReArranged_arrayRightHipPower,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RKneePowerComponents",
                ReArranged_arrayRightKneePower,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RAnklePowerComponents",
                ReArranged_arrayRightAnklePower,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            # Add JRFs to output (not re-arranged)
            self.Models.SetModelOutput(
                "RAnkleForce",
                arrayRightAnkleJRF,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RKneeForce",
                arrayRightKneeJRF,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RHipForce",
                arrayRightHipJRF,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            # Add GRFs and GRMs to output (not re-arranged)
            self.Models.SetModelOutput(
                "RGroundReactionForce",
                arrayRightGRF,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RGroundReactionMoment",
                arrayRightGRM,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            # Add Moment and Power Sums and Foot CoP
            self.Models.SetModelOutput(
                "RMomentPowerSum",
                arrayRightMPSum,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
            self.Models.SetModelOutput(
                "RFootCoP",
                arrayRightFootCoP,
                exists,
                fields["First Frame"],
                fields["Last Frame"],
            )
        #self.Models.saveAsJson("test.json")
        print("[DynamicMain] FOR LOOP FINISHED! Exiting __init__...", flush=True)

    def getModel(self):
        return self.Models


# Calls the main Function
if __name__ == "__main__":
    try:
        print("[DynamicMain] Starting Dynamic_Main()...", flush=True)
        from time import perf_counter
        _dynamic_started = perf_counter()
        model = Dynamic_Main()
        _dynamic_seconds = perf_counter() - _dynamic_started
        print("[DynamicMain] Dynamic_Main() completed! Starting CreateGCD_Main...", flush=True)
        _gcd_started = perf_counter()
        CreateGCD_Main(model.getModel(), sessionPath, filename, fields, TestingCondition)
        _gcd_seconds = perf_counter() - _gcd_started
        artifact = _write_manifest.publish(fields, StaticDataFileName, VersionNumber,
            Path(fields["Path"]) / "GCD" / (Path(filename).stem + ".GCD"),
            timings={"dynamic_s": _dynamic_seconds, "gcd_s": _gcd_seconds})
        print("[WRITE_MANIFEST] " + str(artifact), flush=True)
        print("[DynamicMain] CreateGCD_Main completed successfully!", flush=True)
    except BaseException as e:
        import traceback
        print(f"[DynamicMain] CAUGHT EXCEPTION: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)

