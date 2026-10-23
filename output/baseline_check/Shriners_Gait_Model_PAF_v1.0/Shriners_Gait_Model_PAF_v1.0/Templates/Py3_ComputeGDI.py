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
# Program to compute GDI and append as GCD variable

Created on Wed Apr  7 14:54:30 2021
Last Update: 26 Aug, 2024

@author: psaraswat
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

VersionNumber = 'Py3_v1.3'

import xlrd
import numpy as np
import sys
import os

# Import fields from DynamicMain (assume DynamicMain.py has already run and fields is available)
from Py3_DynamicMain import fields
from pathlib import Path
from Py3_varExtractor import extract_fields_by_filename

# Read GDI features and norms values from excel file
GDIFeaturesFileName = Path(__file__).parent/'mmc1-Shriners.xls'
GDIFeaturesFile = xlrd.open_workbook(GDIFeaturesFileName)
GDIFeaturesFile_sheet = GDIFeaturesFile.sheet_by_name('GDI Calculations')
GDIFeatures = [[0. for m in range(15)] for n in range(459)]
for rowIndex in range(459):
    for colIndex in range(15):
        GDIFeatures[rowIndex][colIndex] = GDIFeaturesFile_sheet.cell_value(rowIndex + 2, colIndex)

TDGDICoefficients = [0. for m in range(15)]
colIndex = 22
for rowIndex in range(15):
    TDGDICoefficients[rowIndex] = GDIFeaturesFile_sheet.cell_value(rowIndex + 2, colIndex)

GDIMeanSDFile_sheet = GDIFeaturesFile.sheet_by_name('control feature data')
TDGDI_Mean = GDIMeanSDFile_sheet.cell_value(1, 52)
TDGDI_SD = GDIMeanSDFile_sheet.cell_value(1, 53)

# Function to read GCD Files
def ReadGCD(GCDFileName):
    GCD_VariableNames = []
    GCD_VariableData = []
    if not GCDFileName.__str__()[-6:-4] == '--':
        with open(GCDFileName, 'r') as GCDfile:
            lines = GCDfile.readlines()
        VariableNameIndex = -1
        Keywords = ['#', '$', '!']
        ReadTextParameterFlag = False
        for line in lines:
            if line[0] == '$':
                ReadTextParameterFlag = True
                GCD_VariableNames.append(line[1:-1])
                GCD_VariableData.append([])
                VariableNameIndex += 1
            if not any(x == line[0] for x in Keywords):
                if ReadTextParameterFlag:
                    GCD_VariableData[VariableNameIndex].append(line[:-1])
            if line[0] == '!':
                ReadTextParameterFlag = False
                GCD_VariableNames.append(line.split(' ')[0][1:].rstrip())
                GCD_VariableName = line.split(' ')[0][1:].rstrip()
                GCD_VariableData.append([])
                VariableNameIndex += 1
            if not any(x == line[0] for x in Keywords):
                if not ReadTextParameterFlag:
                    if GCD_VariableName in ['LeftStrideLength', 'RightStrideLength', 'LeftStepLength', 'RightStepLength', 'LeftSpeed', 'RightSpeed']:
                        GCD_VariableData[VariableNameIndex].append(float(line.split(' ')[0]) / 1000)
                    elif GCD_VariableName in ['LeftCadence', 'RightCadence']:
                        GCD_VariableData[VariableNameIndex].append(2 * 60 * float(line.split(' ')[0]))
                    else:
                        GCD_VariableData[VariableNameIndex].append(float(line.split(' ')[0]))
    return [GCD_VariableNames, GCD_VariableData]

# Take GCD file input from user (file should be in the same directory as this script)
if len(sys.argv) > 1:
    GCDFileName = sys.argv[1]
else:
    # Default: use the GCD file from the current trial in fields
    FilePath, FileName = fields["Path"], fields["Filename"]
    GCDFileName = Path(FilePath) /(FileName + '.GCD')

[GCD_VariableNames, GCD_VariableData] = ReadGCD(GCDFileName)

# Generate single column of kinematics for GDI computation
GDIKinematricsVariableNames = [
    'PelvicTilt', 'PelvicObliquity', 'PelvicRotation',
    'HipFlexExt', 'HipAbAdduct', 'HipRotation',
    'KneeFlexExt',
    'DorsiPlanFlex', 'FootRotation'
]

# Left
if 'LeftDorsiPlanFlex' in GCD_VariableNames:
    LeftGCDKinematicsVector = []
    for GCDVariableName in GDIKinematricsVariableNames:
        GCDVarIndex = GCD_VariableNames.index('Left' + GCDVariableName)
        VariableData = GCD_VariableData[GCDVarIndex]
        GCD_101TimePoint = np.linspace(0, len(VariableData) - 1, len(VariableData))
        GCD_51TimePoints = np.linspace(0, len(VariableData) - 1, 51)
        VariabelData_51Points = np.interp(GCD_51TimePoints, GCD_101TimePoint, VariableData)
        for VariableDataIndex in range(len(VariabelData_51Points)):
            LeftGCDKinematicsVector.append(VariabelData_51Points[VariableDataIndex])
    LeftGDICoefficients = [0. for m in range(15)]
    for colIndex in range(15):
        for rowIndex in range(459):
            LeftGDICoefficients[colIndex] += LeftGCDKinematicsVector[rowIndex] * GDIFeatures[rowIndex][colIndex]
    LeftEuclideanDistance = 0
    for rowIndex in range(15):
        LeftEuclideanDistance += np.square(LeftGDICoefficients[rowIndex] - TDGDICoefficients[rowIndex])
    LeftGDI_Raw = np.log(np.sqrt(LeftEuclideanDistance))
    LeftGDI_z = (LeftGDI_Raw - TDGDI_Mean) / TDGDI_SD
    LeftGDI = int(round((100 - 10 * LeftGDI_z), 0))

# Right
if 'RightDorsiPlanFlex' in GCD_VariableNames:
    RightGCDKinematicsVector = []
    for GCDVariableName in GDIKinematricsVariableNames:
        GCDVarIndex = GCD_VariableNames.index('Right' + GCDVariableName)
        VariableData = GCD_VariableData[GCDVarIndex]
        GCD_101TimePoint = np.linspace(0, len(VariableData) - 1, len(VariableData))
        GCD_51TimePoints = np.linspace(0, len(VariableData) - 1, 51)
        VariabelData_51Points = np.interp(GCD_51TimePoints, GCD_101TimePoint, VariableData)
        for VariableDataIndex in range(len(VariabelData_51Points)):
            RightGCDKinematicsVector.append(VariabelData_51Points[VariableDataIndex])
    RightGDICoefficients = [0. for m in range(15)]
    for colIndex in range(15):
        for rowIndex in range(459):
            RightGDICoefficients[colIndex] += RightGCDKinematicsVector[rowIndex] * GDIFeatures[rowIndex][colIndex]
    RightEuclideanDistance = 0
    for rowIndex in range(15):
        RightEuclideanDistance += np.square(RightGDICoefficients[rowIndex] - TDGDICoefficients[rowIndex])
    RightGDI_Raw = np.log(np.sqrt(RightEuclideanDistance))
    RightGDI_z = (RightGDI_Raw - TDGDI_Mean) / TDGDI_SD
    RightGDI = int(round((100 - 10 * RightGDI_z), 0))

# Add to GCD File
with open(GCDFileName, 'a') as GCDfile:
    if 'LeftDorsiPlanFlex' in GCD_VariableNames:
        GCDfile.write('!LeftGDI\n')
        GCDfile.write(str(LeftGDI) + '\n')
    if 'RightDorsiPlanFlex' in GCD_VariableNames:
        GCDfile.write('!RightGDI\n')
        GCDfile.write(str(RightGDI) + '\n')
