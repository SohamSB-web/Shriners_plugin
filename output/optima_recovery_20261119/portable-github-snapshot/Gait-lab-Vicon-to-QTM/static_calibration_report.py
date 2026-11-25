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

"""Original static PDF layout, rendered without a file dialog."""
import os
from pathlib import Path
import numpy as np
import Py3_MathModules as math
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import reportlab.lib.colors as reportlabColors


def save_calibration_report(state):
    if 'LeftASISMarker' in state: LeftASISMarker = state['LeftASISMarker']
    if 'LeftLateralAnkleMarker' in state: LeftLateralAnkleMarker = state['LeftLateralAnkleMarker']
    if 'LeftLateralKADMarker' in state: LeftLateralKADMarker = state['LeftLateralKADMarker']
    if 'LeftLateralKneeMarker' in state: LeftLateralKneeMarker = state['LeftLateralKneeMarker']
    if 'LeftLowerKADMarker' in state: LeftLowerKADMarker = state['LeftLowerKADMarker']
    if 'LeftMedialAnkleMarker' in state: LeftMedialAnkleMarker = state['LeftMedialAnkleMarker']
    if 'LeftMedialKneeMarker' in state: LeftMedialKneeMarker = state['LeftMedialKneeMarker']
    if 'LeftUpperKADMarker' in state: LeftUpperKADMarker = state['LeftUpperKADMarker']
    if 'RightASISMarker' in state: RightASISMarker = state['RightASISMarker']
    if 'RightLateralAnkleMarker' in state: RightLateralAnkleMarker = state['RightLateralAnkleMarker']
    if 'RightLateralKADMarker' in state: RightLateralKADMarker = state['RightLateralKADMarker']
    if 'RightLateralKneeMarker' in state: RightLateralKneeMarker = state['RightLateralKneeMarker']
    if 'RightLowerKADMarker' in state: RightLowerKADMarker = state['RightLowerKADMarker']
    if 'RightMedialAnkleMarker' in state: RightMedialAnkleMarker = state['RightMedialAnkleMarker']
    if 'RightMedialKneeMarker' in state: RightMedialKneeMarker = state['RightMedialKneeMarker']
    if 'RightUpperKADMarker' in state: RightUpperKADMarker = state['RightUpperKADMarker']
    if 'TestingCondition' in state: TestingCondition = state['TestingCondition']
    if 'UserPreferencesFileName' in state: UserPreferencesFileName = state['UserPreferencesFileName']
    if 'destination' in state: destination = state['destination']
    if 'display_measurement_meters' in state: display_measurement_meters = state['display_measurement_meters']
    if 'fields' in state: fields = state['fields']
    if 'report' in state: report = state['report']
    if 'self' in state: self = state['self']
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
    StaticResultsFilename = destination

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
    if len(str.split(report['LeftTrunkObliquity'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 1 * LineSpacing,
            str.split(report['LeftTrunkObliquity'])[0],
        )
    if len(str.split(report['LeftTrunkTilt'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 2 * LineSpacing,
            str.split(report['LeftTrunkTilt'])[0],
        )
    if len(str.split(report['LeftTrunkRotation'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 3 * LineSpacing,
            str.split(report['LeftTrunkRotation'])[0],
        )
    if len(str.split(report['LeftPelvisObliquity'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 4 * LineSpacing,
            str.split(report['LeftPelvisObliquity'])[0],
        )
    if len(str.split(report['LeftPelvisTilt'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 5 * LineSpacing,
            str.split(report['LeftPelvisTilt'])[0],
        )
    if len(str.split(report['LeftPelvisRotation'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 6 * LineSpacing,
            str.split(report['LeftPelvisRotation'])[0],
        )
    if len(str.split(report['LeftHipAbAdduction'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 7 * LineSpacing,
            str.split(report['LeftHipAbAdduction'])[0],
        )
    if len(str.split(report['LeftHipFlexExtension'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 8 * LineSpacing,
            str.split(report['LeftHipFlexExtension'])[0],
        )
    if len(str.split(report['LeftHipIntExtRotation'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 9 * LineSpacing,
            str.split(report['LeftHipIntExtRotation'])[0],
        )
    if len(str.split(report['LeftKneeVarusValgus'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 10 * LineSpacing,
            str.split(report['LeftKneeVarusValgus'])[0],
        )
    if len(str.split(report['LeftKneeFlexExtension'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 11 * LineSpacing,
            str.split(report['LeftKneeFlexExtension'])[0],
        )
    if len(str.split(report['LeftKneeIntExtRotation'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 12 * LineSpacing,
            str.split(report['LeftKneeIntExtRotation'])[0],
        )
    if len(str.split(report['LeftKneeProgression'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 13 * LineSpacing,
            str.split(report['LeftKneeProgression'])[0],
        )
    if len(str.split(report['LeftAnklePlantarDorsiflexion'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 14 * LineSpacing,
            str.split(report['LeftAnklePlantarDorsiflexion'])[0],
        )
    if len(str.split(report['LeftAnkleIntExtRotation'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 15 * LineSpacing,
            str.split(report['LeftAnkleIntExtRotation'])[0],
        )
    if len(str.split(report['LeftFootProgression'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 16 * LineSpacing,
            str.split(report['LeftFootProgression'])[0],
        )
    # Static Posture- Left Direction
    if len(str.split(report['LeftTrunkObliquity'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 1 * LineSpacing,
            "  " + str.split(report['LeftTrunkObliquity'])[1],
        )
    if len(str.split(report['LeftTrunkTilt'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 2 * LineSpacing,
            "  " + str.split(report['LeftTrunkTilt'])[1],
        )
    if len(str.split(report['LeftTrunkRotation'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 3 * LineSpacing,
            "  " + str.split(report['LeftTrunkRotation'])[1],
        )
    if len(str.split(report['LeftPelvisObliquity'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 4 * LineSpacing,
            "  " + str.split(report['LeftPelvisObliquity'])[1],
        )
    if len(str.split(report['LeftPelvisTilt'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 5 * LineSpacing,
            "  " + str.split(report['LeftPelvisTilt'])[1],
        )
    if len(str.split(report['LeftPelvisRotation'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 6 * LineSpacing,
            "  " + str.split(report['LeftPelvisRotation'])[1],
        )
    if len(str.split(report['LeftHipAbAdduction'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 7 * LineSpacing,
            "  " + str.split(report['LeftHipAbAdduction'])[1],
        )
    if len(str.split(report['LeftHipFlexExtension'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 8 * LineSpacing,
            "  " + str.split(report['LeftHipFlexExtension'])[1],
        )
    if len(str.split(report['LeftHipIntExtRotation'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 9 * LineSpacing,
            "  " + str.split(report['LeftHipIntExtRotation'])[1],
        )
    if len(str.split(report['LeftKneeVarusValgus'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 10 * LineSpacing,
            "  " + str.split(report['LeftKneeVarusValgus'])[1],
        )
    if len(str.split(report['LeftKneeFlexExtension'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 11 * LineSpacing,
            "  " + str.split(report['LeftKneeFlexExtension'])[1],
        )
    if len(str.split(report['LeftKneeIntExtRotation'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 12 * LineSpacing,
            "  " + str.split(report['LeftKneeIntExtRotation'])[1],
        )
    if len(str.split(report['LeftKneeProgression'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 13 * LineSpacing,
            "  " + str.split(report['LeftKneeProgression'])[1],
        )
    if len(str.split(report['LeftAnklePlantarDorsiflexion'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 14 * LineSpacing,
            "  " + str.split(report['LeftAnklePlantarDorsiflexion'])[1],
        )
    if len(str.split(report['LeftAnkleIntExtRotation'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 15 * LineSpacing,
            "  " + str.split(report['LeftAnkleIntExtRotation'])[1],
        )
    if len(str.split(report['LeftFootProgression'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 16 * LineSpacing,
            "  " + str.split(report['LeftFootProgression'])[1],
        )

    # Static Posture- Right Values
    if len(str.split(report['RightTrunkObliquity'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 1 * LineSpacing,
            str.split(report['RightTrunkObliquity'])[0],
        )
    if len(str.split(report['RightTrunkTilt'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 2 * LineSpacing,
            str.split(report['RightTrunkTilt'])[0],
        )
    if len(str.split(report['RightTrunkRotation'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 3 * LineSpacing,
            str.split(report['RightTrunkRotation'])[0],
        )
    if len(str.split(report['RightPelvisObliquity'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 4 * LineSpacing,
            str.split(report['RightPelvisObliquity'])[0],
        )
    if len(str.split(report['RightPelvisTilt'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 5 * LineSpacing,
            str.split(report['RightPelvisTilt'])[0],
        )
    if len(str.split(report['RightPelvisRotation'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 6 * LineSpacing,
            str.split(report['RightPelvisRotation'])[0],
        )
    if len(str.split(report['RightHipAbAdduction'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 7 * LineSpacing,
            str.split(report['RightHipAbAdduction'])[0],
        )
    if len(str.split(report['RightHipFlexExtension'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 8 * LineSpacing,
            str.split(report['RightHipFlexExtension'])[0],
        )
    if len(str.split(report['RightHipIntExtRotation'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 9 * LineSpacing,
            str.split(report['RightHipIntExtRotation'])[0],
        )
    if len(str.split(report['RightKneeVarusValgus'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 10 * LineSpacing,
            str.split(report['RightKneeVarusValgus'])[0],
        )
    if len(str.split(report['RightKneeFlexExtension'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 11 * LineSpacing,
            str.split(report['RightKneeFlexExtension'])[0],
        )
    if len(str.split(report['RightKneeIntExtRotation'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 12 * LineSpacing,
            str.split(report['RightKneeIntExtRotation'])[0],
        )
    if len(str.split(report['RightKneeProgression'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 13 * LineSpacing,
            str.split(report['RightKneeProgression'])[0],
        )
    if len(str.split(report['RightAnklePlantarDorsiflexion'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 14 * LineSpacing,
            str.split(report['RightAnklePlantarDorsiflexion'])[0],
        )
    if len(str.split(report['RightAnkleIntExtRotation'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 15 * LineSpacing,
            str.split(report['RightAnkleIntExtRotation'])[0],
        )
    if len(str.split(report['RightFootProgression'])) > 0:
        StaticResultsPage.drawRightString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 16 * LineSpacing,
            str.split(report['RightFootProgression'])[0],
        )

    # Static Posture- Right Direction
    if len(str.split(report['RightTrunkObliquity'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 1 * LineSpacing,
            "  " + str.split(report['RightTrunkObliquity'])[1],
        )
    if len(str.split(report['RightTrunkTilt'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 2 * LineSpacing,
            "  " + str.split(report['RightTrunkTilt'])[1],
        )
    if len(str.split(report['RightTrunkRotation'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 3 * LineSpacing,
            "  " + str.split(report['RightTrunkRotation'])[1],
        )
    if len(str.split(report['RightPelvisObliquity'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 4 * LineSpacing,
            "  " + str.split(report['RightPelvisObliquity'])[1],
        )
    if len(str.split(report['RightPelvisTilt'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 5 * LineSpacing,
            "  " + str.split(report['RightPelvisTilt'])[1],
        )
    if len(str.split(report['RightPelvisRotation'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 6 * LineSpacing,
            "  " + str.split(report['RightPelvisRotation'])[1],
        )
    if len(str.split(report['RightHipAbAdduction'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 7 * LineSpacing,
            "  " + str.split(report['RightHipAbAdduction'])[1],
        )
    if len(str.split(report['RightHipFlexExtension'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 8 * LineSpacing,
            "  " + str.split(report['RightHipFlexExtension'])[1],
        )
    if len(str.split(report['RightHipIntExtRotation'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 9 * LineSpacing,
            "  " + str.split(report['RightHipIntExtRotation'])[1],
        )
    if len(str.split(report['RightKneeVarusValgus'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 10 * LineSpacing,
            "  " + str.split(report['RightKneeVarusValgus'])[1],
        )
    if len(str.split(report['RightKneeFlexExtension'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 11 * LineSpacing,
            "  " + str.split(report['RightKneeFlexExtension'])[1],
        )
    if len(str.split(report['RightKneeIntExtRotation'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 12 * LineSpacing,
            "  " + str.split(report['RightKneeIntExtRotation'])[1],
        )
    if len(str.split(report['RightKneeProgression'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 13 * LineSpacing,
            "  " + str.split(report['RightKneeProgression'])[1],
        )
    if len(str.split(report['RightAnklePlantarDorsiflexion'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 14 * LineSpacing,
            "  " + str.split(report['RightAnklePlantarDorsiflexion'])[1],
        )
    if len(str.split(report['RightAnkleIntExtRotation'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 15 * LineSpacing,
            "  " + str.split(report['RightAnkleIntExtRotation'])[1],
        )
    if len(str.split(report['RightFootProgression'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 16 * LineSpacing,
            "  " + str.split(report['RightFootProgression'])[1],
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
        str.split(report['LeftTibiaTorsion'])[0],
    )
    if len(str.split(report['LeftTibiaTorsion'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + LeftColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 0 * LineSpacing,
            "  " + str.split(report['LeftTibiaTorsion'])[1],
        )
    # Right
    StaticResultsPage.drawRightString(
        WidthMargin + RightColumnSpacing,
        PageHeight - HeightMargin - VerticalOffsetFromTitle - 0 * LineSpacing,
        str.split(report['RightTibiaTorsion'])[0],
    )
    if len(str.split(report['RightTibiaTorsion'])) > 1:
        StaticResultsPage.drawString(
            WidthMargin + RightColumnSpacing,
            PageHeight
            - HeightMargin
            - VerticalOffsetFromTitle
            - 0 * LineSpacing,
            "  " + str.split(report['RightTibiaTorsion'])[1],
        )

    # =============================================================================
    #           QA Report Number are recomputed here
    #           These are not available here due to being computed in QA Report class
    # =============================================================================
    if (
        (self.LeftASISMarkerName in fields) is True
        and (self.RightASISMarkerName in fields) is True
    ):
        valueASISdistMarkers = np.linalg.norm(LeftASISMarker - RightASISMarker)

    if (
        (self.LeftLateralKneeMarkerName in fields) is True
        and (self.LeftMedialKneeMarkerName in fields)
        is True
    ):
        valueLeftKneeWidthMarkers = (
            np.linalg.norm(LeftLateralKneeMarker - LeftMedialKneeMarker)
            - self.MarkerDiameter
        )

    if (
        (self.RightLateralKneeMarkerName in fields) is True
        and (self.RightMedialKneeMarkerName in fields)
        is True
    ):
        valueRightKneeWidthMarkers = (
            np.linalg.norm(RightLateralKneeMarker - RightMedialKneeMarker)
            - self.MarkerDiameter
        )

    if (
        (self.LeftLateralAnkleMarkerName in fields) is True
        and (self.LeftMedialAnkleMarkerName in fields)
        is True
    ):
        valueLeftAnkleWidthMarkers = (
            np.linalg.norm(LeftLateralAnkleMarker - LeftMedialAnkleMarker)
            - self.MarkerDiameter
        )

    if (
        (self.RightLateralAnkleMarkerName in fields)
        is True
        and (self.RightMedialAnkleMarkerName in fields)
        is True
    ):
        valueRightAnkleWidthMarkers = (
            np.linalg.norm(RightLateralAnkleMarker - RightMedialAnkleMarker)
            - self.MarkerDiameter
        )

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
        (self.RightLateralKADMarkerName in fields) is True
        and (self.RightUpperKADMarkerName in fields)
        is True
        and (self.RightLowerKADMarkerName in fields)
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
        if len(str.split(report['LeftHindfootPitch'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 1 * LineSpacing,
                str.split(report['LeftHindfootPitch'])[0],
            )
        if len(str.split(report['LeftHindfootProgression'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 2 * LineSpacing,
                str.split(report['LeftHindfootProgression'])[0],
            )
        if len(str.split(report['LeftHindfootInvEversion'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 3 * LineSpacing,
                str.split(report['LeftHindfootInvEversion'])[0],
            )
        if len(str.split(report['LeftAnkleComplexInvEversion'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 4 * LineSpacing,
                str.split(report['LeftAnkleComplexInvEversion'])[0],
            )
        if len(str.split(report['LeftForefootPitch'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 5 * LineSpacing,
                str.split(report['LeftForefootPitch'])[0],
            )
        if len(str.split(report['LeftForefootProgression'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 6 * LineSpacing,
                str.split(report['LeftForefootProgression'])[0],
            )
        if len(str.split(report['LeftMidfootAbAdduction'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 7 * LineSpacing,
                str.split(report['LeftMidfootAbAdduction'])[0],
            )
        if len(str.split(report['LeftHalluxProgression'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 8 * LineSpacing,
                str.split(report['LeftHalluxProgression'])[0],
            )

        # Static Posture- Left Direction
        if len(str.split(report['LeftHindfootPitch'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 1 * LineSpacing,
                "  " + str.split(report['LeftHindfootPitch'])[1],
            )
        if len(str.split(report['LeftHindfootProgression'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 2 * LineSpacing,
                "  " + str.split(report['LeftHindfootProgression'])[1],
            )
        if len(str.split(report['LeftHindfootInvEversion'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 3 * LineSpacing,
                "  " + str.split(report['LeftHindfootInvEversion'])[1],
            )
        if len(str.split(report['LeftAnkleComplexInvEversion'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 4 * LineSpacing,
                "  " + str.split(report['LeftAnkleComplexInvEversion'])[1],
            )
        if len(str.split(report['LeftForefootPitch'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 5 * LineSpacing,
                "  " + str.split(report['LeftForefootPitch'])[1],
            )
        if len(str.split(report['LeftForefootProgression'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 6 * LineSpacing,
                "  " + str.split(report['LeftForefootProgression'])[1],
            )
        if len(str.split(report['LeftMidfootAbAdduction'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 7 * LineSpacing,
                "  " + str.split(report['LeftMidfootAbAdduction'])[1],
            )
        if len(str.split(report['LeftHalluxProgression'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + LeftColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 8 * LineSpacing,
                "  " + str.split(report['LeftHalluxProgression'])[1],
            )

        # Static Posture- Right Values
        if len(str.split(report['RightHindfootPitch'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 1 * LineSpacing,
                str.split(report['RightHindfootPitch'])[0],
            )
        if len(str.split(report['RightHindfootProgression'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 2 * LineSpacing,
                str.split(report['RightHindfootProgression'])[0],
            )
        if len(str.split(report['RightHindfootInvEversion'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 3 * LineSpacing,
                str.split(report['RightHindfootInvEversion'])[0],
            )
        if len(str.split(report['RightAnkleComplexInvEversion'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 4 * LineSpacing,
                str.split(report['RightAnkleComplexInvEversion'])[0],
            )
        if len(str.split(report['RightForefootPitch'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 5 * LineSpacing,
                str.split(report['RightForefootPitch'])[0],
            )
        if len(str.split(report['RightForefootProgression'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 6 * LineSpacing,
                str.split(report['RightForefootProgression'])[0],
            )
        if len(str.split(report['RightMidfootAbAdduction'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 7 * LineSpacing,
                str.split(report['RightMidfootAbAdduction'])[0],
            )
        if len(str.split(report['RightHalluxProgression'])) > 0:
            StaticResultsPage.drawRightString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 8 * LineSpacing,
                str.split(report['RightHalluxProgression'])[0],
            )

        # Static Posture- Right Direction
        if len(str.split(report['RightHindfootPitch'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 1 * LineSpacing,
                "  " + str.split(report['RightHindfootPitch'])[1],
            )
        if len(str.split(report['RightHindfootProgression'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 2 * LineSpacing,
                "  " + str.split(report['RightHindfootProgression'])[1],
            )
        if len(str.split(report['RightHindfootInvEversion'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 3 * LineSpacing,
                "  " + str.split(report['RightHindfootInvEversion'])[1],
            )
        if len(str.split(report['RightAnkleComplexInvEversion'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 4 * LineSpacing,
                "  " + str.split(report['RightAnkleComplexInvEversion'])[1],
            )
        if len(str.split(report['RightForefootPitch'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 5 * LineSpacing,
                "  " + str.split(report['RightForefootPitch'])[1],
            )
        if len(str.split(report['RightForefootProgression'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 6 * LineSpacing,
                "  " + str.split(report['RightForefootProgression'])[1],
            )
        if len(str.split(report['RightMidfootAbAdduction'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 7 * LineSpacing,
                "  " + str.split(report['RightMidfootAbAdduction'])[1],
            )
        if len(str.split(report['RightHalluxProgression'])) > 1:
            StaticResultsPage.drawString(
                WidthMargin + RightColumnSpacing,
                PageHeight
                - HeightMargin
                - VerticalOffsetFromTitle
                - 8 * LineSpacing,
                "  " + str.split(report['RightHalluxProgression'])[1],
            )

        StaticResultsPage.showPage()  # Finishes the Current Page

    StaticResultsPage.save()
