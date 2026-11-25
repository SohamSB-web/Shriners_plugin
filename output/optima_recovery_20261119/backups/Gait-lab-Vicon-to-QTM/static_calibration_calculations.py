# <One of the file associated with the Program to compute lower extremity Shrine Gait Model kinematics and kinetics>
# Copyright (C) 2023  <Anas Fodkar>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Static calibration equations extracted unchanged from Py3_StaticMain at e6b06a1.

Each stage takes one per-run state dictionary and returns its calculated values.
There are no widgets, event loops, or live QTM calls in these stages.
"""
import os
import datetime
from pathlib import Path
import numpy as np
from numpy import array, nan
import Py3_MathModules as math
import Py3_GaitModules as gait
from static_calibration_parameters import normalize_processing_measurements, write_setting, qtm_measurement_to_meters, persisted_measurement_to_meters
MILLIMETERS_PER_METER = 1000.0


def validate_static_markers(state):
    if 'DefaultTestingCondition' in state: DefaultTestingCondition = state['DefaultTestingCondition']
    if 'FilePath' in state: FilePath = state['FilePath']
    if 'SetTrajectory' in state: SetTrajectory = state['SetTrajectory']
    if 'SittingFootStaticDataFileName' in state: SittingFootStaticDataFileName = state['SittingFootStaticDataFileName']
    if 'StaticDataFileName' in state: StaticDataFileName = state['StaticDataFileName']
    if 'SubjectName' in state: SubjectName = state['SubjectName']
    if 'fields' in state: fields = state['fields']
    if 'report' in state: report = state['report']
    if 'self' in state: self = state['self']
    if 'warnings' in state: warnings = state['warnings']
    exec(open(StaticDataFileName).read())
    normalize_processing_measurements(self)
    # Extract Nexus first frame
    StartFrame, EndFrame = fields["First Frame"], fields["Last Frame"]

    # =============================================================================
    #         Read Marker data from Start Frame (First Frame) for Static Check
    #         Dispplay Warning if marker not found
    # =============================================================================

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
                ErrorMessage = (
                    "Marker "
                    + MarkerName
                    + " is not labeled at frame "
                    + str(FirstFrame)
                    + "\n"
                )
                warnings.append(str(ErrorMessage).strip())
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
                ErrorMessage = "Marker " + MarkerName + " is not Found " + "\n"
                warnings.append(str(ErrorMessage).strip())
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
            ErrorMessage = "Marker " + MarkerName + " is not Found " + "\n"
            warnings.append(str(ErrorMessage).strip())
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
            selected = [line for line in Path(DefaultStaticDataFileName).read_text().splitlines(True)
                        if line.split() and line.split()[0] in (
                            'self.valueLeftASISMarkerPelvis', 'self.valueRightASISMarkerPelvis')]
            exec(''.join(selected))
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
            ErrorMessage = (
                "Markers on the Left KAD do not appear to be properly labeled"
                + "\n"
            )
            warnings.append(str(ErrorMessage).strip())
        if RightLowerKADMarker[2] > RightUpperKADMarker[2]:
            ErrorMessage = (
                "Markers on the Right KAD do not appear to be properly labeled"
                + "\n"
            )
            warnings.append(str(ErrorMessage).strip())
        # =============================================================================

    report['ASISdistClinical'] = f'{self.valueASISdist / MILLIMETERS_PER_METER:.3f}'
    #print(SubjectName, self.LeftASISMarkerName)
    if (
        (self.LeftASISMarkerName in fields) is True
        and (self.RightASISMarkerName in fields) is True
    ):
        valueASISdistMarkers = np.linalg.norm(LeftASISMarker - RightASISMarker)

        print(
            f"ASIS clinical:{self.valueASISdist} ASIS Markers:{valueASISdistMarkers}"
        )
        report['ASISdistMarkers'] = f'{valueASISdistMarkers / MILLIMETERS_PER_METER:.3f}'
        report['ASISdistDiff'] = str(f'{abs(valueASISdistMarkers - self.valueASISdist) / MILLIMETERS_PER_METER:.3f}')

    report['LeftKneeWidthClinical'] = f'{self.valueLeftKneeWidth / MILLIMETERS_PER_METER:.3f}'
    if self.valueKneeAlignmentCheck == "1":
        valueLeftKneeWidthMarkers = (
            np.linalg.norm(LeftLateralKneeMarker - LeftMedialKneeMarker)
            - self.MarkerDiameter
        )
        print(
            f"Left Knee Width clinical:{self.valueLeftKneeWidth} Left Knee Width Markers:{valueLeftKneeWidthMarkers}"
        )
        report['LeftKneeWidthMarkers'] = f'{valueLeftKneeWidthMarkers / MILLIMETERS_PER_METER:.3f}'
        report['LeftKneeWidthDiff'] = str(f'{abs(valueLeftKneeWidthMarkers - self.valueLeftKneeWidth) / MILLIMETERS_PER_METER:.3f}')

    report['RightKneeWidthClinical'] = f'{self.valueRightKneeWidth / MILLIMETERS_PER_METER:.3f}'
    if self.valueKneeAlignmentCheck == "1":
        valueRightKneeWidthMarkers = (
            np.linalg.norm(RightLateralKneeMarker - RightMedialKneeMarker)
            - self.MarkerDiameter
        )
        print(
            f"Right Knee Width clinical:{self.valueRightKneeWidth} Right Knee Width Markers:{valueRightKneeWidthMarkers}"
        )
        report['RightKneeWidthMarkers'] = f'{valueRightKneeWidthMarkers / MILLIMETERS_PER_METER:.3f}'
        report['RightKneeWidthDiff'] = str(f'{abs(valueRightKneeWidthMarkers - self.valueRightKneeWidth) / MILLIMETERS_PER_METER:.3f}')

    report['LeftAnkleWidthClinical'] = f'{self.valueLeftAnkleWidth / MILLIMETERS_PER_METER:.3f}'
    if (
        (self.LeftLateralAnkleMarkerName in fields) is True
        and (self.LeftMedialAnkleMarkerName in fields) is True
    ):
        valueLeftAnkleWidthMarkers = (
            np.linalg.norm(LeftLateralAnkleMarker - LeftMedialAnkleMarker)
            - self.MarkerDiameter
        )
        print(
            f"Left Ankle Width clinical:{self.valueLeftAnkleWidth} Left Ankle Width Markers:{valueLeftAnkleWidthMarkers}"
        )
        report['LeftAnkleWidthMarkers'] = f'{valueLeftAnkleWidthMarkers / MILLIMETERS_PER_METER:.3f}'
        report['LeftAnkleWidthDiff'] = str(f'{abs(valueLeftAnkleWidthMarkers - self.valueLeftAnkleWidth) / MILLIMETERS_PER_METER:.3f}')

    report['RightAnkleWidthClinical'] = f'{self.valueRightAnkleWidth / MILLIMETERS_PER_METER:.3f}'
    if (
        (self.RightLateralAnkleMarkerName in fields) is True
        and (self.RightMedialAnkleMarkerName in fields) is True
    ):
        valueRightAnkleWidthMarkers = (
            np.linalg.norm(RightLateralAnkleMarker - RightMedialAnkleMarker)
            - self.MarkerDiameter
        )
        print(
            f"Right Ankle Width clinical:{self.valueRightAnkleWidth} Right Ankle Width Markers:{valueRightAnkleWidthMarkers}"
        )
        report['RightAnkleWidthMarkers'] = f'{valueRightAnkleWidthMarkers / MILLIMETERS_PER_METER:.3f}'
        report['RightAnkleWidthDiff'] = str(f'{abs(valueRightAnkleWidthMarkers - self.valueRightAnkleWidth) / MILLIMETERS_PER_METER:.3f}')

    if (
        (self.LeftLateralKADMarkerName in fields) is True
        and (self.LeftUpperKADMarkerName in fields) is True
        and (self.LeftLowerKADMarkerName in fields) is True
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
        report['LeftUpperLateral'] = int(round(valueLeftUpperLateral))
        report['LeftUpperLower'] = int(round(valueLeftUpperLower))
        report['LeftLateralLower'] = int(round(valueLeftLateralLower))
        report['LeftDistRange'] = str(int(round(max(valueLeftUpperLateral, valueLeftUpperLower, valueLeftLateralLower) - min(valueLeftUpperLateral, valueLeftUpperLower, valueLeftLateralLower))))
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
        report['LeftUpperLateralLower'] = int(round(valueLeftUpperLateralLower))
        report['LeftLateralUpperLower'] = int(round(valueLeftLateralUpperLower))
        report['LeftUpperLowerLateral'] = int(round(valueLeftUpperLowerLateral))
        report['LeftAngleRange'] = str(int(round(max(valueLeftUpperLateralLower, valueLeftLateralUpperLower, valueLeftUpperLowerLateral) - min(valueLeftUpperLateralLower, valueLeftLateralUpperLower, valueLeftUpperLowerLateral))))

    if (
        (self.RightLateralKADMarkerName in fields) is True
        and (self.RightUpperKADMarkerName in fields) is True
        and (self.RightLowerKADMarkerName in fields) is True
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
        report['RightUpperLateral'] = int(round(valueRightUpperLateral))
        report['RightUpperLower'] = int(round(valueRightUpperLower))
        report['RightLateralLower'] = int(round(valueRightLateralLower))
        report['RightDistRange'] = str(int(round(max(valueRightUpperLateral, valueRightUpperLower, valueRightLateralLower) - min(valueRightUpperLateral, valueRightUpperLower, valueRightLateralLower))))
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
        report['RightUpperLateralLower'] = int(round(valueRightUpperLateralLower))
        report['RightLateralUpperLower'] = int(round(valueRightLateralUpperLower))
        report['RightUpperLowerLateral'] = int(round(valueRightUpperLowerLateral))
        report['RightAngleRange'] = str(int(round(max(valueRightUpperLateralLower, valueRightLateralUpperLower, valueRightUpperLowerLateral) - min(valueRightUpperLateralLower, valueRightLateralUpperLower, valueRightUpperLowerLateral))))

    # Make Calculated Fields Uneditable

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

    return {name: value for name, value in locals().items() if name != "state" and not callable(value)}


def load_calibration_markers(state):
    if 'SittingFootStaticDataFileName' in state: SittingFootStaticDataFileName = state['SittingFootStaticDataFileName']
    if 'StaticDataFileName' in state: StaticDataFileName = state['StaticDataFileName']
    if 'SubjectName' in state: SubjectName = state['SubjectName']
    if 'fields' in state: fields = state['fields']
    if 'self' in state: self = state['self']
    if 'warnings' in state: warnings = state['warnings']
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

    # Function to extract markerdata into an array and check if data exists
    def MarkerCheck(Subject, MarkerName, FirstFrame):
        # Check if marker exists at all
        if (MarkerName in fields) is True:
            MarkerData = np.array(
                (
                    fields[MarkerName]["X"][FirstFrame],
                    fields[MarkerName]["Y"][FirstFrame],
                    fields[MarkerName]["Z"][FirstFrame],
                )
            )
            # Check if marker is labeled at the first frame
            if MarkerData[0] == 0 or MarkerData[1] == 0 or MarkerData[2] == 0:
                ErrorMessage = (
                    "Marker "
                    + MarkerName
                    + " is not labeled at frame "
                    + str(FirstFrame)
                    + "\n"
                )
                warnings.append(str(ErrorMessage).strip())
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
                ErrorMessage = "Marker " + MarkerName + " is not Found " + "\n"
                warnings.append(str(ErrorMessage).strip())
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

    return {name: value for name, value in locals().items() if name != "state" and not callable(value)}


def compute_joint_centers_and_technical_systems(state):
    if 'EPelvisTech' in state: EPelvisTech = state['EPelvisTech']
    if 'LeftASISMarker' in state: LeftASISMarker = state['LeftASISMarker']
    if 'LeftFifthMetarsalHeadMarker' in state: LeftFifthMetarsalHeadMarker = state['LeftFifthMetarsalHeadMarker']
    if 'LeftFirstMetarsalBaseMarker' in state: LeftFirstMetarsalBaseMarker = state['LeftFirstMetarsalBaseMarker']
    if 'LeftFirstMetarsalHeadMarker' in state: LeftFirstMetarsalHeadMarker = state['LeftFirstMetarsalHeadMarker']
    if 'LeftHalluxMarker' in state: LeftHalluxMarker = state['LeftHalluxMarker']
    if 'LeftHeelMarker' in state: LeftHeelMarker = state['LeftHeelMarker']
    if 'LeftLateralAnkleMarker' in state: LeftLateralAnkleMarker = state['LeftLateralAnkleMarker']
    if 'LeftLateralCalcaneusMarker' in state: LeftLateralCalcaneusMarker = state['LeftLateralCalcaneusMarker']
    if 'LeftLateralKADMarker' in state: LeftLateralKADMarker = state['LeftLateralKADMarker']
    if 'LeftLateralKneeMarker' in state: LeftLateralKneeMarker = state['LeftLateralKneeMarker']
    if 'LeftLowerKADMarker' in state: LeftLowerKADMarker = state['LeftLowerKADMarker']
    if 'LeftMedialAnkleMarker' in state: LeftMedialAnkleMarker = state['LeftMedialAnkleMarker']
    if 'LeftMedialCalcaneusMarker' in state: LeftMedialCalcaneusMarker = state['LeftMedialCalcaneusMarker']
    if 'LeftMedialKneeMarker' in state: LeftMedialKneeMarker = state['LeftMedialKneeMarker']
    if 'LeftPosteriorCalcaneusMarker' in state: LeftPosteriorCalcaneusMarker = state['LeftPosteriorCalcaneusMarker']
    if 'LeftThighMarker' in state: LeftThighMarker = state['LeftThighMarker']
    if 'LeftTibialMarker' in state: LeftTibialMarker = state['LeftTibialMarker']
    if 'LeftToeMarker' in state: LeftToeMarker = state['LeftToeMarker']
    if 'LeftUpperKADMarker' in state: LeftUpperKADMarker = state['LeftUpperKADMarker']
    if 'MarkerCheck' in state: MarkerCheck = state['MarkerCheck']
    if 'MidASISLab' in state: MidASISLab = state['MidASISLab']
    if 'RightASISMarker' in state: RightASISMarker = state['RightASISMarker']
    if 'RightFifthMetarsalHeadMarker' in state: RightFifthMetarsalHeadMarker = state['RightFifthMetarsalHeadMarker']
    if 'RightFirstMetarsalBaseMarker' in state: RightFirstMetarsalBaseMarker = state['RightFirstMetarsalBaseMarker']
    if 'RightFirstMetarsalHeadMarker' in state: RightFirstMetarsalHeadMarker = state['RightFirstMetarsalHeadMarker']
    if 'RightHalluxMarker' in state: RightHalluxMarker = state['RightHalluxMarker']
    if 'RightHeelMarker' in state: RightHeelMarker = state['RightHeelMarker']
    if 'RightLateralAnkleMarker' in state: RightLateralAnkleMarker = state['RightLateralAnkleMarker']
    if 'RightLateralCalcaneusMarker' in state: RightLateralCalcaneusMarker = state['RightLateralCalcaneusMarker']
    if 'RightLateralKADMarker' in state: RightLateralKADMarker = state['RightLateralKADMarker']
    if 'RightLateralKneeMarker' in state: RightLateralKneeMarker = state['RightLateralKneeMarker']
    if 'RightLowerKADMarker' in state: RightLowerKADMarker = state['RightLowerKADMarker']
    if 'RightMedialAnkleMarker' in state: RightMedialAnkleMarker = state['RightMedialAnkleMarker']
    if 'RightMedialCalcaneusMarker' in state: RightMedialCalcaneusMarker = state['RightMedialCalcaneusMarker']
    if 'RightMedialKneeMarker' in state: RightMedialKneeMarker = state['RightMedialKneeMarker']
    if 'RightPosteriorCalcaneusMarker' in state: RightPosteriorCalcaneusMarker = state['RightPosteriorCalcaneusMarker']
    if 'RightThighMarker' in state: RightThighMarker = state['RightThighMarker']
    if 'RightTibialMarker' in state: RightTibialMarker = state['RightTibialMarker']
    if 'RightToeMarker' in state: RightToeMarker = state['RightToeMarker']
    if 'RightUpperKADMarker' in state: RightUpperKADMarker = state['RightUpperKADMarker']
    if 'RotationMatrix' in state: RotationMatrix = state['RotationMatrix']
    if 'SacralMarker' in state: SacralMarker = state['SacralMarker']
    if 'SittingFootStaticDataFileName' in state: SittingFootStaticDataFileName = state['SittingFootStaticDataFileName']
    if 'StaticDataFileName' in state: StaticDataFileName = state['StaticDataFileName']
    if 'SubjectName' in state: SubjectName = state['SubjectName']
    if 'fields' in state: fields = state['fields']
    if 'self' in state: self = state['self']
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
        (self.LeftTibialMarkerName in fields) is True
        and (self.LeftTibialUpperMarkerName in fields) is True
        and (self.LeftTibialLowerMarkerName in fields) is True
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
        (self.RightTibialMarkerName in fields) is True
        and (self.RightTibialUpperMarkerName in fields) is True
        and (self.RightTibialLowerMarkerName in fields) is True
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

    return {name: value for name, value in locals().items() if name != "state" and not callable(value)}


def compute_anatomical_systems_and_foot(state):
    if 'EPelvisTech' in state: EPelvisTech = state['EPelvisTech']
    if 'ETrunkTech' in state: ETrunkTech = state['ETrunkTech']
    if 'Left23MetatarsalBaseMarker' in state: Left23MetatarsalBaseMarker = state['Left23MetatarsalBaseMarker']
    if 'Left23MetatarsalHeadMarker' in state: Left23MetatarsalHeadMarker = state['Left23MetatarsalHeadMarker']
    if 'LeftAnkleCenterLab' in state: LeftAnkleCenterLab = state['LeftAnkleCenterLab']
    if 'LeftCalcanealPeronealTrochleaMarker' in state: LeftCalcanealPeronealTrochleaMarker = state['LeftCalcanealPeronealTrochleaMarker']
    if 'LeftEForefootTech' in state: LeftEForefootTech = state['LeftEForefootTech']
    if 'LeftEHalluxTech' in state: LeftEHalluxTech = state['LeftEHalluxTech']
    if 'LeftEHindfootTech' in state: LeftEHindfootTech = state['LeftEHindfootTech']
    if 'LeftFirstMetatarsalMedialBaseMarker' in state: LeftFirstMetatarsalMedialBaseMarker = state['LeftFirstMetatarsalMedialBaseMarker']
    if 'LeftFirstMetatarsalMedialHeadMarker' in state: LeftFirstMetatarsalMedialHeadMarker = state['LeftFirstMetatarsalMedialHeadMarker']
    if 'LeftHipCenterLab' in state: LeftHipCenterLab = state['LeftHipCenterLab']
    if 'LeftKneeCenterLab' in state: LeftKneeCenterLab = state['LeftKneeCenterLab']
    if 'LeftLateralAnkleMarker' in state: LeftLateralAnkleMarker = state['LeftLateralAnkleMarker']
    if 'LeftLateralCalcaneusMarker' in state: LeftLateralCalcaneusMarker = state['LeftLateralCalcaneusMarker']
    if 'LeftMedialCalcaneusMarker' in state: LeftMedialCalcaneusMarker = state['LeftMedialCalcaneusMarker']
    if 'LeftPosteriorCalcaneusMarker' in state: LeftPosteriorCalcaneusMarker = state['LeftPosteriorCalcaneusMarker']
    if 'LeftToeMarker' in state: LeftToeMarker = state['LeftToeMarker']
    if 'LeftVirtualHeelMarkerLab' in state: LeftVirtualHeelMarkerLab = state['LeftVirtualHeelMarkerLab']
    if 'LeftVirtualKneeMarkerLab' in state: LeftVirtualKneeMarkerLab = state['LeftVirtualKneeMarkerLab']
    if 'Right23MetatarsalBaseMarker' in state: Right23MetatarsalBaseMarker = state['Right23MetatarsalBaseMarker']
    if 'Right23MetatarsalHeadMarker' in state: Right23MetatarsalHeadMarker = state['Right23MetatarsalHeadMarker']
    if 'RightAnkleCenterLab' in state: RightAnkleCenterLab = state['RightAnkleCenterLab']
    if 'RightCalcanealPeronealTrochleaMarker' in state: RightCalcanealPeronealTrochleaMarker = state['RightCalcanealPeronealTrochleaMarker']
    if 'RightEForefootTech' in state: RightEForefootTech = state['RightEForefootTech']
    if 'RightEHalluxTech' in state: RightEHalluxTech = state['RightEHalluxTech']
    if 'RightEHindfootTech' in state: RightEHindfootTech = state['RightEHindfootTech']
    if 'RightFirstMetatarsalMedialBaseMarker' in state: RightFirstMetatarsalMedialBaseMarker = state['RightFirstMetatarsalMedialBaseMarker']
    if 'RightFirstMetatarsalMedialHeadMarker' in state: RightFirstMetatarsalMedialHeadMarker = state['RightFirstMetatarsalMedialHeadMarker']
    if 'RightHipCenterLab' in state: RightHipCenterLab = state['RightHipCenterLab']
    if 'RightKneeCenterLab' in state: RightKneeCenterLab = state['RightKneeCenterLab']
    if 'RightLateralAnkleMarker' in state: RightLateralAnkleMarker = state['RightLateralAnkleMarker']
    if 'RightLateralCalcaneusMarker' in state: RightLateralCalcaneusMarker = state['RightLateralCalcaneusMarker']
    if 'RightMedialCalcaneusMarker' in state: RightMedialCalcaneusMarker = state['RightMedialCalcaneusMarker']
    if 'RightPosteriorCalcaneusMarker' in state: RightPosteriorCalcaneusMarker = state['RightPosteriorCalcaneusMarker']
    if 'RightToeMarker' in state: RightToeMarker = state['RightToeMarker']
    if 'RightVirtualHeelMarkerLab' in state: RightVirtualHeelMarkerLab = state['RightVirtualHeelMarkerLab']
    if 'RightVirtualKneeMarkerLab' in state: RightVirtualKneeMarkerLab = state['RightVirtualKneeMarkerLab']
    if 'SittingFootStaticDataFileName' in state: SittingFootStaticDataFileName = state['SittingFootStaticDataFileName']
    if 'StaticDataFileName' in state: StaticDataFileName = state['StaticDataFileName']
    if 'self' in state: self = state['self']
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

    return {name: value for name, value in locals().items() if name != "state" and not callable(value)}


def compute_transforms_and_posture(state):
    if 'EPelvisAnat' in state: EPelvisAnat = state['EPelvisAnat']
    if 'EPelvisTech' in state: EPelvisTech = state['EPelvisTech']
    if 'ETrunkAnat' in state: ETrunkAnat = state['ETrunkAnat']
    if 'ETrunkTech' in state: ETrunkTech = state['ETrunkTech']
    if 'Left23MetatarsalHeadMarker' in state: Left23MetatarsalHeadMarker = state['Left23MetatarsalHeadMarker']
    if 'LeftAnkleCenterLab' in state: LeftAnkleCenterLab = state['LeftAnkleCenterLab']
    if 'LeftEFootAnat' in state: LeftEFootAnat = state['LeftEFootAnat']
    if 'LeftEFootAnat2' in state: LeftEFootAnat2 = state['LeftEFootAnat2']
    if 'LeftEFootTech' in state: LeftEFootTech = state['LeftEFootTech']
    if 'LeftEForefootAnat' in state: LeftEForefootAnat = state['LeftEForefootAnat']
    if 'LeftEForefootTech' in state: LeftEForefootTech = state['LeftEForefootTech']
    if 'LeftEHalluxAnat' in state: LeftEHalluxAnat = state['LeftEHalluxAnat']
    if 'LeftEHalluxTech' in state: LeftEHalluxTech = state['LeftEHalluxTech']
    if 'LeftEHindfootAnat' in state: LeftEHindfootAnat = state['LeftEHindfootAnat']
    if 'LeftEHindfootTech' in state: LeftEHindfootTech = state['LeftEHindfootTech']
    if 'LeftEShankDistalAnat' in state: LeftEShankDistalAnat = state['LeftEShankDistalAnat']
    if 'LeftEShankProximalAnat' in state: LeftEShankProximalAnat = state['LeftEShankProximalAnat']
    if 'LeftEShankTech' in state: LeftEShankTech = state['LeftEShankTech']
    if 'LeftEThighAnat' in state: LeftEThighAnat = state['LeftEThighAnat']
    if 'LeftEThighTech' in state: LeftEThighTech = state['LeftEThighTech']
    if 'LeftFirstMetarsalBaseMarker' in state: LeftFirstMetarsalBaseMarker = state['LeftFirstMetarsalBaseMarker']
    if 'LeftFirstMetatarsoPhalangealJointMarker' in state: LeftFirstMetatarsoPhalangealJointMarker = state['LeftFirstMetatarsoPhalangealJointMarker']
    if 'LeftKneeCenterLab' in state: LeftKneeCenterLab = state['LeftKneeCenterLab']
    if 'LeftLateralAnkleMarker' in state: LeftLateralAnkleMarker = state['LeftLateralAnkleMarker']
    if 'LeftMedialAnkleMarker' in state: LeftMedialAnkleMarker = state['LeftMedialAnkleMarker']
    if 'Right23MetatarsalHeadMarker' in state: Right23MetatarsalHeadMarker = state['Right23MetatarsalHeadMarker']
    if 'RightAnkleCenterLab' in state: RightAnkleCenterLab = state['RightAnkleCenterLab']
    if 'RightEFootAnat' in state: RightEFootAnat = state['RightEFootAnat']
    if 'RightEFootAnat2' in state: RightEFootAnat2 = state['RightEFootAnat2']
    if 'RightEFootTech' in state: RightEFootTech = state['RightEFootTech']
    if 'RightEForefootAnat' in state: RightEForefootAnat = state['RightEForefootAnat']
    if 'RightEForefootTech' in state: RightEForefootTech = state['RightEForefootTech']
    if 'RightEHalluxAnat' in state: RightEHalluxAnat = state['RightEHalluxAnat']
    if 'RightEHalluxTech' in state: RightEHalluxTech = state['RightEHalluxTech']
    if 'RightEHindfootAnat' in state: RightEHindfootAnat = state['RightEHindfootAnat']
    if 'RightEHindfootTech' in state: RightEHindfootTech = state['RightEHindfootTech']
    if 'RightEShankDistalAnat' in state: RightEShankDistalAnat = state['RightEShankDistalAnat']
    if 'RightEShankProximalAnat' in state: RightEShankProximalAnat = state['RightEShankProximalAnat']
    if 'RightEShankTech' in state: RightEShankTech = state['RightEShankTech']
    if 'RightEThighAnat' in state: RightEThighAnat = state['RightEThighAnat']
    if 'RightEThighTech' in state: RightEThighTech = state['RightEThighTech']
    if 'RightFirstMetarsalBaseMarker' in state: RightFirstMetarsalBaseMarker = state['RightFirstMetarsalBaseMarker']
    if 'RightFirstMetatarsoPhalangealJointMarker' in state: RightFirstMetatarsoPhalangealJointMarker = state['RightFirstMetatarsoPhalangealJointMarker']
    if 'RightKneeCenterLab' in state: RightKneeCenterLab = state['RightKneeCenterLab']
    if 'RightLateralAnkleMarker' in state: RightLateralAnkleMarker = state['RightLateralAnkleMarker']
    if 'RightMedialAnkleMarker' in state: RightMedialAnkleMarker = state['RightMedialAnkleMarker']
    if 'self' in state: self = state['self']
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

    return {name: value for name, value in locals().items() if name != "state" and not callable(value)}


def format_calibration_report(state):
    if 'LeftAnkleAnglesDeg' in state: LeftAnkleAnglesDeg = state['LeftAnkleAnglesDeg']
    if 'LeftAnkleComplexAnglesDeg' in state: LeftAnkleComplexAnglesDeg = state['LeftAnkleComplexAnglesDeg']
    if 'LeftFootAnglesDeg' in state: LeftFootAnglesDeg = state['LeftFootAnglesDeg']
    if 'LeftForefootAnglesDeg' in state: LeftForefootAnglesDeg = state['LeftForefootAnglesDeg']
    if 'LeftHalluxAnglesDeg' in state: LeftHalluxAnglesDeg = state['LeftHalluxAnglesDeg']
    if 'LeftHindfootAnglesDeg' in state: LeftHindfootAnglesDeg = state['LeftHindfootAnglesDeg']
    if 'LeftHipAnglesDeg' in state: LeftHipAnglesDeg = state['LeftHipAnglesDeg']
    if 'LeftKneeAnglesDeg' in state: LeftKneeAnglesDeg = state['LeftKneeAnglesDeg']
    if 'LeftPelvisAnglesDeg' in state: LeftPelvisAnglesDeg = state['LeftPelvisAnglesDeg']
    if 'LeftThighAnglesDeg' in state: LeftThighAnglesDeg = state['LeftThighAnglesDeg']
    if 'LeftTibialTorsion' in state: LeftTibialTorsion = state['LeftTibialTorsion']
    if 'LeftToesAnglesDeg' in state: LeftToesAnglesDeg = state['LeftToesAnglesDeg']
    if 'LeftTrunkAnglesDeg' in state: LeftTrunkAnglesDeg = state['LeftTrunkAnglesDeg']
    if 'RightAnkleAnglesDeg' in state: RightAnkleAnglesDeg = state['RightAnkleAnglesDeg']
    if 'RightAnkleComplexAnglesDeg' in state: RightAnkleComplexAnglesDeg = state['RightAnkleComplexAnglesDeg']
    if 'RightFootAnglesDeg' in state: RightFootAnglesDeg = state['RightFootAnglesDeg']
    if 'RightForefootAnglesDeg' in state: RightForefootAnglesDeg = state['RightForefootAnglesDeg']
    if 'RightHalluxAnglesDeg' in state: RightHalluxAnglesDeg = state['RightHalluxAnglesDeg']
    if 'RightHindfootAnglesDeg' in state: RightHindfootAnglesDeg = state['RightHindfootAnglesDeg']
    if 'RightHipAnglesDeg' in state: RightHipAnglesDeg = state['RightHipAnglesDeg']
    if 'RightKneeAnglesDeg' in state: RightKneeAnglesDeg = state['RightKneeAnglesDeg']
    if 'RightPelvisAnglesDeg' in state: RightPelvisAnglesDeg = state['RightPelvisAnglesDeg']
    if 'RightThighAnglesDeg' in state: RightThighAnglesDeg = state['RightThighAnglesDeg']
    if 'RightTibialTorsion' in state: RightTibialTorsion = state['RightTibialTorsion']
    if 'RightToesAnglesDeg' in state: RightToesAnglesDeg = state['RightToesAnglesDeg']
    if 'RightTrunkAnglesDeg' in state: RightTrunkAnglesDeg = state['RightTrunkAnglesDeg']
    if 'TrunkFlag' in state: TrunkFlag = state['TrunkFlag']
    if 'report' in state: report = state['report']
    if 'self' in state: self = state['self']
    if TrunkFlag == 1:
        if round(LeftTrunkAnglesDeg[0], 0) > 0:
            report['LeftTrunkObliquity'] = str(str(int(abs(round(LeftTrunkAnglesDeg[0], 0)))) + ' Up')
        if round(LeftTrunkAnglesDeg[0], 0) < 0:
            report['LeftTrunkObliquity'] = str(str(int(abs(round(LeftTrunkAnglesDeg[0], 0)))) + ' Down')
        if round(LeftTrunkAnglesDeg[0], 0) == 0:
            report['LeftTrunkObliquity'] = str(str(int(abs(round(LeftTrunkAnglesDeg[0], 0)))) + '')
        if round(LeftTrunkAnglesDeg[1], 0) > 0:
            report['LeftTrunkTilt'] = str(str(int(abs(round(LeftTrunkAnglesDeg[1], 0)))) + ' Forw')
        if round(LeftTrunkAnglesDeg[1], 0) < 0:
            report['LeftTrunkTilt'] = str(str(int(abs(round(LeftTrunkAnglesDeg[1], 0)))) + ' Back')
        if round(LeftTrunkAnglesDeg[1], 0) == 0:
            report['LeftTrunkTilt'] = str(str(int(abs(round(LeftTrunkAnglesDeg[1], 0)))) + '')
        if round(LeftTrunkAnglesDeg[2], 0) > 0:
            report['LeftTrunkRotation'] = str(str(int(abs(round(LeftTrunkAnglesDeg[2], 0)))) + ' Int')
        if round(LeftTrunkAnglesDeg[2], 0) < 0:
            report['LeftTrunkRotation'] = str(str(int(abs(round(LeftTrunkAnglesDeg[2], 0)))) + ' Ext')
        if round(LeftTrunkAnglesDeg[2], 0) == 0:
            report['LeftTrunkRotation'] = str(str(int(abs(round(LeftTrunkAnglesDeg[2], 0)))) + '')

    if round(LeftPelvisAnglesDeg[0], 0) > 0:
        report['LeftPelvisObliquity'] = str(str(int(abs(round(LeftPelvisAnglesDeg[0], 0)))) + ' Up')
    if round(LeftPelvisAnglesDeg[0], 0) < 0:
        report['LeftPelvisObliquity'] = str(str(int(abs(round(LeftPelvisAnglesDeg[0], 0)))) + ' Down')
    if round(LeftPelvisAnglesDeg[0], 0) == 0:
        report['LeftPelvisObliquity'] = str(str(int(abs(round(LeftPelvisAnglesDeg[0], 0)))) + '')
    if round(LeftPelvisAnglesDeg[1], 0) > 0:
        report['LeftPelvisTilt'] = str(str(int(abs(round(LeftPelvisAnglesDeg[1], 0)))) + ' Ant')
    if round(LeftPelvisAnglesDeg[1], 0) < 0:
        report['LeftPelvisTilt'] = str(str(int(abs(round(LeftPelvisAnglesDeg[1], 0)))) + ' Post')
    if round(LeftPelvisAnglesDeg[1], 0) == 0:
        report['LeftPelvisTilt'] = str(str(int(abs(round(LeftPelvisAnglesDeg[1], 0)))) + '')
    if round(LeftPelvisAnglesDeg[2], 0) > 0:
        report['LeftPelvisRotation'] = str(str(int(abs(round(LeftPelvisAnglesDeg[2], 0)))) + ' Int')
    if round(LeftPelvisAnglesDeg[2], 0) < 0:
        report['LeftPelvisRotation'] = str(str(int(abs(round(LeftPelvisAnglesDeg[2], 0)))) + ' Ext')
    if round(LeftPelvisAnglesDeg[2], 0) == 0:
        report['LeftPelvisRotation'] = str(str(int(abs(round(LeftPelvisAnglesDeg[2], 0)))) + '')

    if round(LeftHipAnglesDeg[0], 0) > 0:
        report['LeftHipAbAdduction'] = str(str(int(abs(round(LeftHipAnglesDeg[0], 0)))) + ' Add')
    if round(LeftHipAnglesDeg[0], 0) < 0:
        report['LeftHipAbAdduction'] = str(str(int(abs(round(LeftHipAnglesDeg[0], 0)))) + ' Abd')
    if round(LeftHipAnglesDeg[0], 0) == 0:
        report['LeftHipAbAdduction'] = str(str(int(abs(round(LeftHipAnglesDeg[0], 0)))) + '')
    if round(LeftHipAnglesDeg[1], 0) > 0:
        report['LeftHipFlexExtension'] = str(str(int(abs(round(LeftHipAnglesDeg[1], 0)))) + ' Flex')
    if round(LeftHipAnglesDeg[1], 0) < 0:
        report['LeftHipFlexExtension'] = str(str(int(abs(round(LeftHipAnglesDeg[1], 0)))) + ' Ext')
    if round(LeftHipAnglesDeg[1], 0) == 0:
        report['LeftHipFlexExtension'] = str(str(int(abs(round(LeftHipAnglesDeg[1], 0)))) + '')
    if round(LeftHipAnglesDeg[2], 0) > 0:
        report['LeftHipIntExtRotation'] = str(str(int(abs(round(LeftHipAnglesDeg[2], 0)))) + ' Int')
    if round(LeftHipAnglesDeg[2], 0) < 0:
        report['LeftHipIntExtRotation'] = str(str(int(abs(round(LeftHipAnglesDeg[2], 0)))) + ' Ext')
    if round(LeftHipAnglesDeg[2], 0) == 0:
        report['LeftHipIntExtRotation'] = str(str(int(abs(round(LeftHipAnglesDeg[2], 0)))) + '')

    if round(LeftKneeAnglesDeg[0], 0) > 0:
        report['LeftKneeVarusValgus'] = str(str(int(abs(round(LeftKneeAnglesDeg[0], 0)))) + ' Var')
    if round(LeftKneeAnglesDeg[0], 0) < 0:
        report['LeftKneeVarusValgus'] = str(str(int(abs(round(LeftKneeAnglesDeg[0], 0)))) + ' Val')
    if round(LeftKneeAnglesDeg[0], 0) == 0:
        report['LeftKneeVarusValgus'] = str(str(int(abs(round(LeftKneeAnglesDeg[0], 0)))) + '')
    if round(LeftKneeAnglesDeg[1], 0) > 0:
        report['LeftKneeFlexExtension'] = str(str(int(abs(round(LeftKneeAnglesDeg[1], 0)))) + ' Flex')
    if round(LeftKneeAnglesDeg[1], 0) < 0:
        report['LeftKneeFlexExtension'] = str(str(int(abs(round(LeftKneeAnglesDeg[1], 0)))) + ' Ext')
    if round(LeftKneeAnglesDeg[1], 0) == 0:
        report['LeftKneeFlexExtension'] = str(str(int(abs(round(LeftKneeAnglesDeg[1], 0)))) + '')
    if round(LeftKneeAnglesDeg[2], 0) > 0:
        report['LeftKneeIntExtRotation'] = str(str(int(abs(round(LeftKneeAnglesDeg[2], 0)))) + ' Int')
    if round(LeftKneeAnglesDeg[2], 0) < 0:
        report['LeftKneeIntExtRotation'] = str(str(int(abs(round(LeftKneeAnglesDeg[2], 0)))) + ' Ext')
    if round(LeftKneeAnglesDeg[2], 0) == 0:
        report['LeftKneeIntExtRotation'] = str(str(int(abs(round(LeftKneeAnglesDeg[2], 0)))) + '')

    if round(LeftThighAnglesDeg[2], 0) > 0:
        report['LeftKneeProgression'] = str(str(int(abs(round(LeftThighAnglesDeg[2], 0)))) + ' Int')
    if round(LeftThighAnglesDeg[2], 0) < 0:
        report['LeftKneeProgression'] = str(str(int(abs(round(LeftThighAnglesDeg[2], 0)))) + ' Ext')
    if round(LeftThighAnglesDeg[2], 0) == 0:
        report['LeftKneeProgression'] = str(str(int(abs(round(LeftThighAnglesDeg[2], 0)))) + '')

    if round(LeftAnkleAnglesDeg[1], 0) > 0:
        report['LeftAnklePlantarDorsiflexion'] = str(str(int(abs(round(LeftAnkleAnglesDeg[1], 0)))) + ' Dorsi')
    if round(LeftAnkleAnglesDeg[1], 0) < 0:
        report['LeftAnklePlantarDorsiflexion'] = str(str(int(abs(round(LeftAnkleAnglesDeg[1], 0)))) + ' Plant')
    if round(LeftAnkleAnglesDeg[1], 0) == 0:
        report['LeftAnklePlantarDorsiflexion'] = str(str(int(abs(round(LeftAnkleAnglesDeg[1], 0)))) + '')
    if round(LeftAnkleAnglesDeg[2], 0) > 0:
        report['LeftAnkleIntExtRotation'] = str(str(int(abs(round(LeftAnkleAnglesDeg[2], 0)))) + ' Int')
    if round(LeftAnkleAnglesDeg[2], 0) < 0:
        report['LeftAnkleIntExtRotation'] = str(str(int(abs(round(LeftAnkleAnglesDeg[2], 0)))) + ' Ext')
    if round(LeftAnkleAnglesDeg[2], 0) == 0:
        report['LeftAnkleIntExtRotation'] = str(str(int(abs(round(LeftAnkleAnglesDeg[2], 0)))) + '')

    if round(LeftFootAnglesDeg[2], 0) > 0:
        report['LeftFootProgression'] = str(str(int(abs(round(LeftFootAnglesDeg[2], 0)))) + ' Int')
    if round(LeftFootAnglesDeg[2], 0) < 0:
        report['LeftFootProgression'] = str(str(int(abs(round(LeftFootAnglesDeg[2], 0)))) + ' Ext')
    if round(LeftFootAnglesDeg[2], 0) == 0:
        report['LeftFootProgression'] = str(str(int(abs(round(LeftFootAnglesDeg[2], 0)))) + '')

    if round(LeftTibialTorsion, 0) > 0:
        report['LeftTibiaTorsion'] = str(str(int(abs(round(LeftTibialTorsion, 0)))) + ' Ext')
    if round(LeftTibialTorsion, 0) < 0:
        report['LeftTibiaTorsion'] = str(str(int(abs(round(LeftTibialTorsion, 0)))) + ' Int')
    if round(LeftTibialTorsion, 0) == 0:
        report['LeftTibiaTorsion'] = str(str(int(abs(round(LeftTibialTorsion, 0)))) + '')

    if self.valueLeftFootModelCheck == "1":
        if round(LeftHindfootAnglesDeg[0], 0) > 0:
            report['LeftHindfootInvEversion'] = str(str(int(abs(round(LeftHindfootAnglesDeg[0], 0)))) + ' Val')
        if round(LeftHindfootAnglesDeg[0], 0) < 0:
            report['LeftHindfootInvEversion'] = str(str(int(abs(round(LeftHindfootAnglesDeg[0], 0)))) + ' Var')
        if round(LeftHindfootAnglesDeg[0], 0) == 0:
            report['LeftHindfootInvEversion'] = str(str(int(abs(round(LeftHindfootAnglesDeg[0], 0)))) + '')
        if round(LeftHindfootAnglesDeg[1], 0) > 0:
            report['LeftHindfootPitch'] = str(str(int(abs(round(LeftHindfootAnglesDeg[1], 0)))) + ' Down')
        if round(LeftHindfootAnglesDeg[1], 0) < 0:
            report['LeftHindfootPitch'] = str(str(int(abs(round(LeftHindfootAnglesDeg[1], 0)))) + ' Up')
        if round(LeftHindfootAnglesDeg[1], 0) == 0:
            report['LeftHindfootPitch'] = str(str(int(abs(round(LeftHindfootAnglesDeg[1], 0)))) + '')
        if round(LeftHindfootAnglesDeg[2], 0) > 0:
            report['LeftHindfootProgression'] = str(str(int(abs(round(LeftHindfootAnglesDeg[2], 0)))) + ' Int')
        if round(LeftHindfootAnglesDeg[2], 0) < 0:
            report['LeftHindfootProgression'] = str(str(int(abs(round(LeftHindfootAnglesDeg[2], 0)))) + ' Ext')
        if round(LeftHindfootAnglesDeg[2], 0) == 0:
            report['LeftHindfootProgression'] = str(str(int(abs(round(LeftHindfootAnglesDeg[2], 0)))) + '')

        if round(LeftAnkleComplexAnglesDeg[0], 0) > 0:
            report['LeftAnkleComplexInvEversion'] = str(str(int(abs(round(LeftAnkleComplexAnglesDeg[0], 0)))) + ' Var')
        if round(LeftAnkleComplexAnglesDeg[0], 0) < 0:
            report['LeftAnkleComplexInvEversion'] = str(str(int(abs(round(LeftAnkleComplexAnglesDeg[0], 0)))) + ' Val')
        if round(LeftAnkleComplexAnglesDeg[0], 0) == 0:
            report['LeftAnkleComplexInvEversion'] = str(str(int(abs(round(LeftAnkleComplexAnglesDeg[0], 0)))) + '')

        #            if round(LeftForefootAnglesDeg[0], 0) > 0:
        #                LeftForefootInvEversion.insert(0, str(int(abs(round(LeftForefootAnglesDeg[0], 0)))) +  " Inv")
        #            if round(LeftForefootAnglesDeg[0], 0) < 0:
        #                LeftForefootInvEversion.insert(0, str(int(abs(round(LeftForefootAnglesDeg[0], 0)))) +  " Ev")
        #            if round(LeftForefootAnglesDeg[0], 0) == 0:
        #                LeftForefootInvEversion.insert(0, str(int(abs(round(LeftForefootAnglesDeg[0], 0)))) +  "")
        if round(LeftForefootAnglesDeg[1], 0) > 0:
            report['LeftForefootPitch'] = str(str(int(abs(round(LeftForefootAnglesDeg[1], 0)))) + ' Down')
        if round(LeftForefootAnglesDeg[1], 0) < 0:
            report['LeftForefootPitch'] = str(str(int(abs(round(LeftForefootAnglesDeg[1], 0)))) + ' Up')
        if round(LeftForefootAnglesDeg[1], 0) == 0:
            report['LeftForefootPitch'] = str(str(int(abs(round(LeftForefootAnglesDeg[1], 0)))) + '')
        if round(LeftForefootAnglesDeg[2], 0) > 0:
            report['LeftForefootProgression'] = str(str(int(abs(round(LeftForefootAnglesDeg[2], 0)))) + ' Int')
        if round(LeftForefootAnglesDeg[2], 0) < 0:
            report['LeftForefootProgression'] = str(str(int(abs(round(LeftForefootAnglesDeg[2], 0)))) + ' Ext')
        if round(LeftForefootAnglesDeg[2], 0) == 0:
            report['LeftForefootProgression'] = str(str(int(abs(round(LeftForefootAnglesDeg[2], 0)))) + '')

        if round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0) > 0:
            report['LeftMidfootAbAdduction'] = str(str(int(abs(round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0)))) + ' Add')
        if round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0) < 0:
            report['LeftMidfootAbAdduction'] = str(str(int(abs(round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0)))) + ' Abd')
        if round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0) == 0:
            report['LeftMidfootAbAdduction'] = str(str(int(abs(round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0)))) + '')

        if round(LeftHalluxAnglesDeg[2], 0) > 0:
            report['LeftHalluxProgression'] = str(str(int(abs(round(LeftToesAnglesDeg[2], 0)))) + ' Var')
        if round(LeftHalluxAnglesDeg[2], 0) < 0:
            report['LeftHalluxProgression'] = str(str(int(abs(round(LeftToesAnglesDeg[2], 0)))) + ' Val')
        if round(LeftHalluxAnglesDeg[2], 0) == 0:
            report['LeftHalluxProgression'] = str(str(int(abs(round(LeftToesAnglesDeg[2], 0)))) + '')

    # Right
    if TrunkFlag == 1:
        if round(RightTrunkAnglesDeg[0], 0) > 0:
            report['RightTrunkObliquity'] = str(str(int(abs(round(RightTrunkAnglesDeg[0], 0)))) + ' Up')
        if round(RightTrunkAnglesDeg[0], 0) < 0:
            report['RightTrunkObliquity'] = str(str(int(abs(round(RightTrunkAnglesDeg[0], 0)))) + ' Down')
        if round(RightTrunkAnglesDeg[0], 0) == 0:
            report['RightTrunkObliquity'] = str(str(int(abs(round(RightTrunkAnglesDeg[0], 0)))) + '')
        if round(RightTrunkAnglesDeg[1], 0) > 0:
            report['RightTrunkTilt'] = str(str(int(abs(round(RightTrunkAnglesDeg[1], 0)))) + ' Forw')
        if round(RightTrunkAnglesDeg[1], 0) < 0:
            report['RightTrunkTilt'] = str(str(int(abs(round(RightTrunkAnglesDeg[1], 0)))) + ' Back')
        if round(RightTrunkAnglesDeg[1], 0) == 0:
            report['RightTrunkTilt'] = str(str(int(abs(round(RightTrunkAnglesDeg[1], 0)))) + '')
        if round(RightTrunkAnglesDeg[2], 0) > 0:
            report['RightTrunkRotation'] = str(str(int(abs(round(RightTrunkAnglesDeg[2], 0)))) + ' Int')
        if round(RightTrunkAnglesDeg[2], 0) < 0:
            report['RightTrunkRotation'] = str(str(int(abs(round(RightTrunkAnglesDeg[2], 0)))) + ' Ext')
        if round(RightTrunkAnglesDeg[2], 0) == 0:
            report['RightTrunkRotation'] = str(str(int(abs(round(RightTrunkAnglesDeg[2], 0)))) + '')

    if round(RightPelvisAnglesDeg[0], 0) > 0:
        report['RightPelvisObliquity'] = str(str(int(abs(round(RightPelvisAnglesDeg[0], 0)))) + ' Up')
    if round(RightPelvisAnglesDeg[0], 0) < 0:
        report['RightPelvisObliquity'] = str(str(int(abs(round(RightPelvisAnglesDeg[0], 0)))) + ' Down')
    if round(RightPelvisAnglesDeg[0], 0) == 0:
        report['RightPelvisObliquity'] = str(str(int(abs(round(RightPelvisAnglesDeg[0], 0)))) + '')
    if round(RightPelvisAnglesDeg[1], 0) > 0:
        report['RightPelvisTilt'] = str(str(int(abs(round(RightPelvisAnglesDeg[1], 0)))) + ' Ant')
    if round(RightPelvisAnglesDeg[1], 0) < 0:
        report['RightPelvisTilt'] = str(str(int(abs(round(RightPelvisAnglesDeg[1], 0)))) + ' Post')
    if round(RightPelvisAnglesDeg[1], 0) == 0:
        report['RightPelvisTilt'] = str(str(int(abs(round(RightPelvisAnglesDeg[1], 0)))) + '')
    if round(RightPelvisAnglesDeg[2], 0) > 0:
        report['RightPelvisRotation'] = str(str(int(abs(round(RightPelvisAnglesDeg[2], 0)))) + ' Int')
    if round(RightPelvisAnglesDeg[2], 0) < 0:
        report['RightPelvisRotation'] = str(str(int(abs(round(RightPelvisAnglesDeg[2], 0)))) + ' Ext')
    if round(RightPelvisAnglesDeg[2], 0) == 0:
        report['RightPelvisRotation'] = str(str(int(abs(round(RightPelvisAnglesDeg[2], 0)))) + '')

    if round(RightHipAnglesDeg[0], 0) > 0:
        report['RightHipAbAdduction'] = str(str(int(abs(round(RightHipAnglesDeg[0], 0)))) + ' Add')
    if round(RightHipAnglesDeg[0], 0) < 0:
        report['RightHipAbAdduction'] = str(str(int(abs(round(RightHipAnglesDeg[0], 0)))) + ' Abd')
    if round(RightHipAnglesDeg[0], 0) == 0:
        report['RightHipAbAdduction'] = str(str(int(abs(round(RightHipAnglesDeg[0], 0)))) + '')
    if round(RightHipAnglesDeg[1], 0) > 0:
        report['RightHipFlexExtension'] = str(str(int(abs(round(RightHipAnglesDeg[1], 0)))) + ' Flex')
    if round(RightHipAnglesDeg[1], 0) < 0:
        report['RightHipFlexExtension'] = str(str(int(abs(round(RightHipAnglesDeg[1], 0)))) + ' Ext')
    if round(RightHipAnglesDeg[1], 0) == 0:
        report['RightHipFlexExtension'] = str(str(int(abs(round(RightHipAnglesDeg[1], 0)))) + '')
    if round(RightHipAnglesDeg[2], 0) > 0:
        report['RightHipIntExtRotation'] = str(str(int(abs(round(RightHipAnglesDeg[2], 0)))) + ' Int')
    if round(RightHipAnglesDeg[2], 0) < 0:
        report['RightHipIntExtRotation'] = str(str(int(abs(round(RightHipAnglesDeg[2], 0)))) + ' Ext')
    if round(RightHipAnglesDeg[2], 0) == 0:
        report['RightHipIntExtRotation'] = str(str(int(abs(round(RightHipAnglesDeg[2], 0)))) + '')

    if round(RightKneeAnglesDeg[0], 0) > 0:
        report['RightKneeVarusValgus'] = str(str(int(abs(round(RightKneeAnglesDeg[0], 0)))) + ' Var')
    if round(RightKneeAnglesDeg[0], 0) < 0:
        report['RightKneeVarusValgus'] = str(str(int(abs(round(RightKneeAnglesDeg[0], 0)))) + ' Val')
    if round(RightKneeAnglesDeg[0], 0) == 0:
        report['RightKneeVarusValgus'] = str(str(int(abs(round(RightKneeAnglesDeg[0], 0)))) + '')
    if round(RightKneeAnglesDeg[1], 0) > 0:
        report['RightKneeFlexExtension'] = str(str(int(abs(round(RightKneeAnglesDeg[1], 0)))) + ' Flex')
    if round(RightKneeAnglesDeg[1], 0) < 0:
        report['RightKneeFlexExtension'] = str(str(int(abs(round(RightKneeAnglesDeg[1], 0)))) + ' Ext')
    if round(RightKneeAnglesDeg[1], 0) == 0:
        report['RightKneeFlexExtension'] = str(str(int(abs(round(RightKneeAnglesDeg[1], 0)))) + '')
    if round(RightKneeAnglesDeg[2], 0) > 0:
        report['RightKneeIntExtRotation'] = str(str(int(abs(round(RightKneeAnglesDeg[2], 0)))) + ' Int')
    if round(RightKneeAnglesDeg[2], 0) < 0:
        report['RightKneeIntExtRotation'] = str(str(int(abs(round(RightKneeAnglesDeg[2], 0)))) + ' Ext')
    if round(RightKneeAnglesDeg[2], 0) == 0:
        report['RightKneeIntExtRotation'] = str(str(int(abs(round(RightKneeAnglesDeg[2], 0)))) + '')

    if round(RightThighAnglesDeg[2], 0) > 0:
        report['RightKneeProgression'] = str(str(int(abs(round(RightThighAnglesDeg[2], 0)))) + ' Int')
    if round(RightThighAnglesDeg[2], 0) < 0:
        report['RightKneeProgression'] = str(str(int(abs(round(RightThighAnglesDeg[2], 0)))) + ' Ext')
    if round(RightThighAnglesDeg[2], 0) == 0:
        report['RightKneeProgression'] = str(str(int(abs(round(RightThighAnglesDeg[2], 0)))) + '')

    if round(RightAnkleAnglesDeg[1], 0) > 0:
        report['RightAnklePlantarDorsiflexion'] = str(str(int(abs(round(RightAnkleAnglesDeg[1], 0)))) + ' Dorsi')
    if round(RightAnkleAnglesDeg[1], 0) < 0:
        report['RightAnklePlantarDorsiflexion'] = str(str(int(abs(round(RightAnkleAnglesDeg[1], 0)))) + ' Plant')
    if round(RightAnkleAnglesDeg[1], 0) == 0:
        report['RightAnklePlantarDorsiflexion'] = str(str(int(abs(round(RightAnkleAnglesDeg[1], 0)))) + '')
    if round(RightAnkleAnglesDeg[2], 0) > 0:
        report['RightAnkleIntExtRotation'] = str(str(int(abs(round(RightAnkleAnglesDeg[2], 0)))) + ' Int')
    if round(RightAnkleAnglesDeg[2], 0) < 0:
        report['RightAnkleIntExtRotation'] = str(str(int(abs(round(RightAnkleAnglesDeg[2], 0)))) + ' Ext')
    if round(RightAnkleAnglesDeg[2], 0) == 0:
        report['RightAnkleIntExtRotation'] = str(str(int(abs(round(RightAnkleAnglesDeg[2], 0)))) + '')

    if round(RightFootAnglesDeg[2], 0) > 0:
        report['RightFootProgression'] = str(str(int(abs(round(RightFootAnglesDeg[2], 0)))) + ' Int')
    if round(RightFootAnglesDeg[2], 0) < 0:
        report['RightFootProgression'] = str(str(int(abs(round(RightFootAnglesDeg[2], 0)))) + ' Ext')
    if round(RightFootAnglesDeg[2], 0) == 0:
        report['RightFootProgression'] = str(str(int(abs(round(RightFootAnglesDeg[2], 0)))) + '')

    if round(RightTibialTorsion, 0) > 0:
        report['RightTibiaTorsion'] = str(str(int(abs(round(RightTibialTorsion, 0)))) + ' Ext')
    if round(RightTibialTorsion, 0) < 0:
        report['RightTibiaTorsion'] = str(str(int(abs(round(RightTibialTorsion, 0)))) + ' Int')
    if round(RightTibialTorsion, 0) == 0:
        report['RightTibiaTorsion'] = str(str(int(abs(round(RightTibialTorsion, 0)))) + '')

    if self.valueRightFootModelCheck == "1":
        if round(RightHindfootAnglesDeg[0], 0) > 0:
            report['RightHindfootInvEversion'] = str(str(int(abs(round(RightHindfootAnglesDeg[0], 0)))) + ' Val')
        if round(RightHindfootAnglesDeg[0], 0) < 0:
            report['RightHindfootInvEversion'] = str(str(int(abs(round(RightHindfootAnglesDeg[0], 0)))) + ' Var')
        if round(RightHindfootAnglesDeg[0], 0) == 0:
            report['RightHindfootInvEversion'] = str(str(int(abs(round(RightHindfootAnglesDeg[0], 0)))) + '')
        if round(RightHindfootAnglesDeg[1], 0) > 0:
            report['RightHindfootPitch'] = str(str(int(abs(round(RightHindfootAnglesDeg[1], 0)))) + ' Down')
        if round(RightHindfootAnglesDeg[1], 0) < 0:
            report['RightHindfootPitch'] = str(str(int(abs(round(RightHindfootAnglesDeg[1], 0)))) + ' Up')
        if round(RightHindfootAnglesDeg[1], 0) == 0:
            report['RightHindfootPitch'] = str(str(int(abs(round(RightHindfootAnglesDeg[1], 0)))) + '')
        if round(RightHindfootAnglesDeg[2], 0) > 0:
            report['RightHindfootProgression'] = str(str(int(abs(round(RightHindfootAnglesDeg[2], 0)))) + ' Int')
        if round(RightHindfootAnglesDeg[2], 0) < 0:
            report['RightHindfootProgression'] = str(str(int(abs(round(RightHindfootAnglesDeg[2], 0)))) + ' Ext')
        if round(RightHindfootAnglesDeg[2], 0) == 0:
            report['RightHindfootProgression'] = str(str(int(abs(round(RightHindfootAnglesDeg[2], 0)))) + '')

        if round(RightAnkleComplexAnglesDeg[0], 0) > 0:
            report['RightAnkleComplexInvEversion'] = str(str(int(abs(round(RightAnkleComplexAnglesDeg[0], 0)))) + ' Var')
        if round(RightAnkleComplexAnglesDeg[0], 0) < 0:
            report['RightAnkleComplexInvEversion'] = str(str(int(abs(round(RightAnkleComplexAnglesDeg[0], 0)))) + ' Val')
        if round(RightAnkleComplexAnglesDeg[0], 0) == 0:
            report['RightAnkleComplexInvEversion'] = str(str(int(abs(round(RightAnkleComplexAnglesDeg[0], 0)))) + '')

        #            if round(RightForefootAnglesDeg[0], 0) > 0:
        #                RightForefootInvEversion.insert(0, str(int(abs(round(RightForefootAnglesDeg[0], 0)))) +  " Inv")
        #            if round(RightForefootAnglesDeg[0], 0) < 0:
        #                RightForefootInvEversion.insert(0, str(int(abs(round(RightForefootAnglesDeg[0], 0)))) +  " Ev")
        #            if round(RightForefootAnglesDeg[0], 0) == 0:
        #                RightForefootInvEversion.insert(0, str(int(abs(round(RightForefootAnglesDeg[0], 0)))) +  "")
        if round(RightForefootAnglesDeg[1], 0) > 0:
            report['RightForefootPitch'] = str(str(int(abs(round(RightForefootAnglesDeg[1], 0)))) + ' Down')
        if round(RightForefootAnglesDeg[1], 0) < 0:
            report['RightForefootPitch'] = str(str(int(abs(round(RightForefootAnglesDeg[1], 0)))) + ' Up')
        if round(RightForefootAnglesDeg[1], 0) == 0:
            report['RightForefootPitch'] = str(str(int(abs(round(RightForefootAnglesDeg[1], 0)))) + '')
        if round(RightForefootAnglesDeg[2], 0) > 0:
            report['RightForefootProgression'] = str(str(int(abs(round(RightForefootAnglesDeg[2], 0)))) + ' Int')
        if round(RightForefootAnglesDeg[2], 0) < 0:
            report['RightForefootProgression'] = str(str(int(abs(round(RightForefootAnglesDeg[2], 0)))) + ' Ext')
        if round(RightForefootAnglesDeg[2], 0) == 0:
            report['RightForefootProgression'] = str(str(int(abs(round(RightForefootAnglesDeg[2], 0)))) + '')

        if round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0) > 0:
            report['RightMidfootAbAdduction'] = str(str(int(abs(round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0)))) + ' Add')
        if round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0) < 0:
            report['RightMidfootAbAdduction'] = str(str(int(abs(round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0)))) + ' Abd')
        if round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0) == 0:
            report['RightMidfootAbAdduction'] = str(str(int(abs(round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0)))) + '')

        if round(RightHalluxAnglesDeg[2], 0) > 0:
            report['RightHalluxProgression'] = str(str(int(abs(round(RightToesAnglesDeg[2], 0)))) + ' Var')
        if round(RightHalluxAnglesDeg[2], 0) < 0:
            report['RightHalluxProgression'] = str(str(int(abs(round(RightToesAnglesDeg[2], 0)))) + ' Val')
        if round(RightHalluxAnglesDeg[2], 0) == 0:
            report['RightHalluxProgression'] = str(str(int(abs(round(RightToesAnglesDeg[2], 0)))) + '')

    return {name: value for name, value in locals().items() if name != "state" and not callable(value)}


def save_transformation_matrices(state):
    if 'EPelvisAnatRelTech' in state: EPelvisAnatRelTech = state['EPelvisAnatRelTech']
    if 'ETrunkAnatRelTech' in state: ETrunkAnatRelTech = state['ETrunkAnatRelTech']
    if 'Left23MetatarsalHeadMarkerForefoot' in state: Left23MetatarsalHeadMarkerForefoot = state['Left23MetatarsalHeadMarkerForefoot']
    if 'LeftAnkleCenterShank' in state: LeftAnkleCenterShank = state['LeftAnkleCenterShank']
    if 'LeftEFootAnat2RelTech' in state: LeftEFootAnat2RelTech = state['LeftEFootAnat2RelTech']
    if 'LeftEFootAnatRelTech' in state: LeftEFootAnatRelTech = state['LeftEFootAnatRelTech']
    if 'LeftEForefootAnatRelTech' in state: LeftEForefootAnatRelTech = state['LeftEForefootAnatRelTech']
    if 'LeftEHalluxAnatRelTech' in state: LeftEHalluxAnatRelTech = state['LeftEHalluxAnatRelTech']
    if 'LeftEHindfootAnatRelTech' in state: LeftEHindfootAnatRelTech = state['LeftEHindfootAnatRelTech']
    if 'LeftEShankDistalAnatRelTech' in state: LeftEShankDistalAnatRelTech = state['LeftEShankDistalAnatRelTech']
    if 'LeftEShankProximalAnatRelTech' in state: LeftEShankProximalAnatRelTech = state['LeftEShankProximalAnatRelTech']
    if 'LeftEThighAnatRelTech' in state: LeftEThighAnatRelTech = state['LeftEThighAnatRelTech']
    if 'LeftFirstMetatarsoPhalangealJointMarkerForefoot' in state: LeftFirstMetatarsoPhalangealJointMarkerForefoot = state['LeftFirstMetatarsoPhalangealJointMarkerForefoot']
    if 'LeftHipCenterPelvis' in state: LeftHipCenterPelvis = state['LeftHipCenterPelvis']
    if 'LeftKneeCenterThigh' in state: LeftKneeCenterThigh = state['LeftKneeCenterThigh']
    if 'LeftTibialTorsion' in state: LeftTibialTorsion = state['LeftTibialTorsion']
    if 'Right23MetatarsalHeadMarkerForefoot' in state: Right23MetatarsalHeadMarkerForefoot = state['Right23MetatarsalHeadMarkerForefoot']
    if 'RightAnkleCenterShank' in state: RightAnkleCenterShank = state['RightAnkleCenterShank']
    if 'RightEFootAnat2RelTech' in state: RightEFootAnat2RelTech = state['RightEFootAnat2RelTech']
    if 'RightEFootAnatRelTech' in state: RightEFootAnatRelTech = state['RightEFootAnatRelTech']
    if 'RightEForefootAnatRelTech' in state: RightEForefootAnatRelTech = state['RightEForefootAnatRelTech']
    if 'RightEHalluxAnatRelTech' in state: RightEHalluxAnatRelTech = state['RightEHalluxAnatRelTech']
    if 'RightEHindfootAnatRelTech' in state: RightEHindfootAnatRelTech = state['RightEHindfootAnatRelTech']
    if 'RightEShankDistalAnatRelTech' in state: RightEShankDistalAnatRelTech = state['RightEShankDistalAnatRelTech']
    if 'RightEShankProximalAnatRelTech' in state: RightEShankProximalAnatRelTech = state['RightEShankProximalAnatRelTech']
    if 'RightEThighAnatRelTech' in state: RightEThighAnatRelTech = state['RightEThighAnatRelTech']
    if 'RightFirstMetatarsoPhalangealJointMarkerForefoot' in state: RightFirstMetatarsoPhalangealJointMarkerForefoot = state['RightFirstMetatarsoPhalangealJointMarkerForefoot']
    if 'RightHipCenterPelvis' in state: RightHipCenterPelvis = state['RightHipCenterPelvis']
    if 'RightKneeCenterThigh' in state: RightKneeCenterThigh = state['RightKneeCenterThigh']
    if 'RightTibialTorsion' in state: RightTibialTorsion = state['RightTibialTorsion']
    if 'StaticDataFileName' in state: StaticDataFileName = state['StaticDataFileName']
    if 'self' in state: self = state['self']
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

    return {name: value for name, value in locals().items() if name != "state" and not callable(value)}


def generate_modeled_markers(state):
    if 'CreateModeledMarker' in state: CreateModeledMarker = state['CreateModeledMarker']
    if 'EndFrame' in state: EndFrame = state['EndFrame']
    if 'SetTrajectory' in state: SetTrajectory = state['SetTrajectory']
    if 'StartFrame' in state: StartFrame = state['StartFrame']
    if 'StaticDataFileName' in state: StaticDataFileName = state['StaticDataFileName']
    if 'SubjectName' in state: SubjectName = state['SubjectName']
    if 'fields' in state: fields = state['fields']
    if 'self' in state: self = state['self']
    # Function to extract markerdata into an array and check if data exists
    def MarkerArrayCheck(Subject, MarkerName):
        # Check if marker exists at all
        if (MarkerName in fields) is True:
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
    normalize_processing_measurements(self)
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
        (self.LeftTibialMarkerName in fields) is True
        and (self.LeftTibialUpperMarkerName in fields)
        is True
        and (self.LeftTibialLowerMarkerName in fields)
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
        (self.RightTibialMarkerName in fields) is True
        and (self.RightTibialUpperMarkerName in fields)
        is True
        and (self.RightTibialLowerMarkerName in fields)
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

    return {name: value for name, value in locals().items() if name != "state" and not callable(value)}
