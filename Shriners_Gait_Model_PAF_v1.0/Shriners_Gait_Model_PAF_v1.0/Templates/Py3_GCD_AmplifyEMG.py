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
# Program that amplifies EMG with a constant factor such that maximum value of EMG signal is 4 across all channels.

Created on Tue Feb 20 11:38:05 2024
Last Update: 26 Aug, 2024

@author: psaraswat
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

VersionNumber = 'Py3_v1.3'

#import Vicon Nexus Subroutines
from viconnexusapi import ViconNexus
vicon = ViconNexus.ViconNexus()


# Function to read GCD Files
def ReadGCD(GCDFileName):
    GCD_VariableNames = []
    GCD_VariableData = []
    if not GCDFileName[-6:-4] == '--':
        GCDfile=open(GCDFileName,'r')
        lines=GCDfile.readlines()
        VariableNameIndex = -1
        Keywords = ['#','$','!']
        ReadTextParameterFlag = False
        for line in lines:
            # Read C3d and Static File Name
            if line[0] == '$':
                ReadTextParameterFlag = True
                GCD_VariableNames.append(line[1:-1])
                GCD_VariableData.append([])
                VariableNameIndex = VariableNameIndex + 1
            if not any(x == line[0] for x in Keywords):
                if ReadTextParameterFlag == True:
                    GCD_VariableData[VariableNameIndex].append(line[:-1])
                
            # Read Computed Parameters
            if line[0] == '!':
                ReadTextParameterFlag = False
                #GCD_VariableNames.append(line[1:-1])
                GCD_VariableNames.append(line.split(' ')[0][1:].rstrip())
                GCD_VariableName = line.split(' ')[0][1:].rstrip()
                GCD_VariableData.append([])
                VariableNameIndex = VariableNameIndex + 1
            if not any(x == line[0] for x in Keywords):
                if ReadTextParameterFlag == False:
                    if GCD_VariableName == 'LeftStrideLength' or GCD_VariableName == 'RightStrideLength' or GCD_VariableName == 'LeftStepLength' or GCD_VariableName == 'RightStepLength' or GCD_VariableName == 'LeftSpeed' or GCD_VariableName == 'RightSpeed':
                        GCD_VariableData[VariableNameIndex].append(float(line.split(' ')[0])/1000)
                    else:
                        if GCD_VariableName == 'LeftCadence' or GCD_VariableName == 'RightCadence':
                            GCD_VariableData[VariableNameIndex].append(2*60*float(line.split(' ')[0]))
                        else:
                            GCD_VariableData[VariableNameIndex].append(float(line.split(' ')[0]))
                            #GCD_VariableData[VariableNameIndex].append(float(line[:-1]))
            
    return [GCD_VariableNames,GCD_VariableData] 



FilePath, FileName = vicon.GetTrialName()
GCDFileName= FilePath + "\\" + FileName + '.GCD'
[GCD_VariableNames,GCD_VariableData] =  ReadGCD(GCDFileName)

EMGVariableKeyword = 'Raw'
ExcludedKeyword = 'Envelope'
Keywords = ['#','$','!']


PeakEMGSignalValue = 0
for GCD_VariableName in GCD_VariableNames:
    if EMGVariableKeyword in GCD_VariableName:
        if ExcludedKeyword not in GCD_VariableName:
            EMGVarIndex = GCD_VariableNames.index(GCD_VariableName)
            EMGVariableData = GCD_VariableData[EMGVarIndex]
            #print(GCD_VariableName,max(EMGVariableData),min(EMGVariableData))
            Peak_EMGVariableData = max(abs(max(EMGVariableData)),abs(min(EMGVariableData)))
            if Peak_EMGVariableData > PeakEMGSignalValue:
                PeakEMGSignalValue = Peak_EMGVariableData
            #print(GCD_VariableName,PeakEMGSignalValue)
#print(PeakEMGSignalValue)

# =============================================================================
# # Modify GCD FIle
# =============================================================================
GCDfile = open(GCDFileName, 'r')
lines = GCDfile.readlines()
lineIndex = 0
EMGDataFoundFlag = 0
for line in lines:
    if '!' in line[0] and EMGDataFoundFlag == 1:
        EMGDataFoundFlag = 0
    if EMGVariableKeyword in line:
        if ExcludedKeyword not in line:
            EMGDataFoundFlag = 1
    if EMGDataFoundFlag == 1:
        if not line[0] in Keywords:
            if not PeakEMGSignalValue == 0:
                lines[lineIndex] = str(float(line)*4.0/PeakEMGSignalValue) + '\n'
    lineIndex = lineIndex + 1

GCDfile.close()

GCDfile = open(GCDFileName, 'w')
GCDfile.writelines(lines)
GCDfile.close()
