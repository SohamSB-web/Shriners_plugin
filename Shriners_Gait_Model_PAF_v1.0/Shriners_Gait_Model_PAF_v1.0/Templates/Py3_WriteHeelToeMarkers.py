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
# =============================================================================
# Function to add HEE and TOE markers in walking trial with foot model
# It reads PCAL and MT23H markers and writes them into HEE and TOE markers
# It is required for Gait Events pipeline
# =============================================================================

Created on Wed Apr  7 14:54:30 2021
Last Update: 26 Aug, 2024

@author: psaraswat
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

VersionNumber = 'Py3_v1.3'


import numpy as np
import sys

# from viconnexusapi import ViconNexus
# vicon = ViconNexus.ViconNexus()

#import Common Vector/Matrix Operations Modules
import Py3_MathModules as math
import Py3_GaitModules as gait
from Py3_varExtractor import extract_fields_by_filename
from gapi import  run_tkinter_grpc_server,SetTrajectory,CreateModeledMarker,GetForcePlate

# Extract information from active trial
from pathlib import Path
_sess_xml = Path(__file__).resolve().parent.parent / "Data" / "test_002" / "2025-02-21_0003" / "session.xml"
if not _sess_xml.exists():
    _sess_xml = Path(__file__).resolve().parent.parent / "Data" / "Shriners_test_002" / "2025-02-21_0003" / "session.xml"

fields = extract_fields_by_filename(str(_sess_xml), "Static 1.qtm")

SubjectName = fields["Name"]
FilePath, FileName = fields["Path"]+"\\", fields["Filename"]
StartFrame, EndFrame = fields["First Frame"], fields["Last Frame"]

# First Argument is the command name, second argument is the testing condition
DefaultTestingCondition = 'BF'
TestingCondition = DefaultTestingCondition
if len(sys.argv) > 1:
    TestingCondition = sys.argv[1]
    
StaticDataFileName = FilePath + 'Static_' + TestingCondition + '_' + SubjectName + '.py'

class Main():
    def __init__(self):
        exec(open(StaticDataFileName).read())
        
        def HasTrajectory( subjectName, markerName):
            return markerName in fields 
        # Function to extract markerdata into an array and check if data exists
        def MarkerArrayCheck(Subject, MarkerName):
            # Check if marker exists at all
            if HasTrajectory(Subject,MarkerName) is True:
                MarkerDataX = fields[MarkerName]["X"]
                MarkerDataY = fields[MarkerName]["Y"]
                MarkerDataZ = fields[MarkerName]["Z"]
                MarkerDataExists = fields[MarkerName]["Exists"]
                
                # Smooth Marker Data
                Order = 3
                WindowWidth = 21 # Use Odd Number 
                MarkerDataX = math.Smooth1DArray(MarkerDataX,StartFrame,EndFrame,Order,WindowWidth)
                MarkerDataY = math.Smooth1DArray(MarkerDataY,StartFrame,EndFrame,Order,WindowWidth)
                MarkerDataZ = math.Smooth1DArray(MarkerDataZ,StartFrame,EndFrame,Order,WindowWidth)
            else:
                framecount = fields['Frames']
                MarkerDataX= [0 for m in range(framecount)] 
                MarkerDataY= [0 for m in range(framecount)] 
                MarkerDataZ= [0 for m in range(framecount)] 
                MarkerDataExists = [False]*framecount
            return MarkerDataX, MarkerDataY, MarkerDataZ, MarkerDataExists
        
        if self.valueLeftFootModelCheck == '1':
            LeftFirstMetarsalBaseMarkerX, LeftFirstMetarsalBaseMarkerY, LeftFirstMetarsalBaseMarkerZ, LeftFirstMetarsalBaseMarkerExists = MarkerArrayCheck(SubjectName, self.LeftFirstMetarsalBaseMarkerName)
            LeftFirstMetarsalHeadMarkerX, LeftFirstMetarsalHeadMarkerY, LeftFirstMetarsalHeadMarkerZ, LeftFirstMetarsalHeadMarkerExists = MarkerArrayCheck(SubjectName, self.LeftFirstMetarsalHeadMarkerName)
            LeftFifthMetarsalHeadMarkerX, LeftFifthMetarsalHeadMarkerY, LeftFifthMetarsalHeadMarkerZ, LeftFifthMetarsalHeadMarkerExists = MarkerArrayCheck(SubjectName, self.LeftFifthMetarsalHeadMarkerName)
        if self.valueRightFootModelCheck == '1':
            RightFirstMetarsalBaseMarkerX, RightFirstMetarsalBaseMarkerY, RightFirstMetarsalBaseMarkerZ, RightFirstMetarsalBaseMarkerExists = MarkerArrayCheck(SubjectName, self.RightFirstMetarsalBaseMarkerName)
            RightFirstMetarsalHeadMarkerX, RightFirstMetarsalHeadMarkerY, RightFirstMetarsalHeadMarkerZ, RightFirstMetarsalHeadMarkerExists = MarkerArrayCheck(SubjectName, self.RightFirstMetarsalHeadMarkerName)
            RightFifthMetarsalHeadMarkerX, RightFifthMetarsalHeadMarkerY, RightFifthMetarsalHeadMarkerZ, RightFifthMetarsalHeadMarkerExists = MarkerArrayCheck(SubjectName, self.RightFifthMetarsalHeadMarkerName)
        
        
        framecount = fields['Frames']
        arrayLMT23HMarkerX= [0 for m in range(framecount)] 
        arrayLMT23HMarkerY= [0 for m in range(framecount)] 
        arrayLMT23HMarkerZ= [0 for m in range(framecount)]
        arrayRMT23HMarkerX= [0 for m in range(framecount)] 
        arrayRMT23HMarkerY= [0 for m in range(framecount)] 
        arrayRMT23HMarkerZ= [0 for m in range(framecount)]  
        exists = [True]*framecount
        
        for FrameNumber in range(StartFrame-1,EndFrame):    
            # Compute Technical Coordinate System: Left Foot Segments
            if self.valueLeftFootModelCheck == '1':
                LeftFirstMetarsalBaseMarker = np.array([LeftFirstMetarsalBaseMarkerX[FrameNumber], LeftFirstMetarsalBaseMarkerY[FrameNumber], LeftFirstMetarsalBaseMarkerZ[FrameNumber]])
                LeftFirstMetarsalHeadMarker = np.array([LeftFirstMetarsalHeadMarkerX[FrameNumber], LeftFirstMetarsalHeadMarkerY[FrameNumber], LeftFirstMetarsalHeadMarkerZ[FrameNumber]])
                LeftFifthMetarsalHeadMarker = np.array([LeftFifthMetarsalHeadMarkerX[FrameNumber], LeftFifthMetarsalHeadMarkerY[FrameNumber], LeftFifthMetarsalHeadMarkerZ[FrameNumber]])
                LeftEForefootTech = gait.TechCS_Forefoot_mSHCG('Left', LeftFirstMetarsalBaseMarker, LeftFirstMetarsalHeadMarker, LeftFifthMetarsalHeadMarker)
                LeftMT23HMarkerLab = math.TransformPointIntoLabCoors(self.valueLeft23MetatarsalHeadMarkerForefoot,LeftEForefootTech, LeftFirstMetarsalBaseMarker)
                arrayLMT23HMarkerX[FrameNumber] = LeftMT23HMarkerLab[0]
                arrayLMT23HMarkerY[FrameNumber] = LeftMT23HMarkerLab[1]
                arrayLMT23HMarkerZ[FrameNumber] = LeftMT23HMarkerLab[2]
                
                
            # Compute Technical Coordinate System: Right Foot Segments
            if self.valueRightFootModelCheck == '1':
                RightFirstMetarsalBaseMarker = np.array([RightFirstMetarsalBaseMarkerX[FrameNumber], RightFirstMetarsalBaseMarkerY[FrameNumber], RightFirstMetarsalBaseMarkerZ[FrameNumber]])
                RightFirstMetarsalHeadMarker = np.array([RightFirstMetarsalHeadMarkerX[FrameNumber], RightFirstMetarsalHeadMarkerY[FrameNumber], RightFirstMetarsalHeadMarkerZ[FrameNumber]])
                RightFifthMetarsalHeadMarker = np.array([RightFifthMetarsalHeadMarkerX[FrameNumber], RightFifthMetarsalHeadMarkerY[FrameNumber], RightFifthMetarsalHeadMarkerZ[FrameNumber]])
                RightEForefootTech = gait.TechCS_Forefoot_mSHCG('Right', RightFirstMetarsalBaseMarker, RightFirstMetarsalHeadMarker, RightFifthMetarsalHeadMarker)
                RightMT23HMarkerLab = math.TransformPointIntoLabCoors(self.valueRight23MetatarsalHeadMarkerForefoot,RightEForefootTech, RightFirstMetarsalBaseMarker)
                arrayRMT23HMarkerX[FrameNumber] = RightMT23HMarkerLab[0]
                arrayRMT23HMarkerY[FrameNumber] = RightMT23HMarkerLab[1]
                arrayRMT23HMarkerZ[FrameNumber] = RightMT23HMarkerLab[2]
            

        if HasTrajectory(SubjectName, self.LeftFirstMetarsalBaseMarkerName) is True:
            if self.valueLeftFootModelCheck == '1':        
                SetTrajectory(SubjectName, self.LeftToeMarkerName, arrayLMT23HMarkerX, arrayLMT23HMarkerY, arrayLMT23HMarkerZ, exists )
                if HasTrajectory(SubjectName,self.LeftHeelMarkerName) is False:
                    LPCALx, LPCALy, LPCALz, LPCALexists = fields[self.LeftPosteriorCalcaneusMarkerName]["X"], fields[self.LeftPosteriorCalcaneusMarkerName]["Y"], fields[self.LeftPosteriorCalcaneusMarkerName]["Z"], fields[self.LeftPosteriorCalcaneusMarkerName]["Exists"]
                    SetTrajectory(SubjectName, self.LeftHeelMarkerName, LPCALx, LPCALy, LPCALz, exists )
        
        if HasTrajectory(SubjectName, self.RightFirstMetarsalBaseMarkerName) is True:
            if self.valueLeftFootModelCheck == '1':   
                SetTrajectory(SubjectName, self.RightToeMarkerName, arrayRMT23HMarkerX, arrayRMT23HMarkerY, arrayRMT23HMarkerZ, exists )
                if HasTrajectory(SubjectName,self.RightHeelMarkerName) is False:
                    RPCALx, RPCALy, RPCALz, RPCALexists = fields[self.RightPosteriorCalcaneusMarkerName]["X"], fields[self.RightPosteriorCalcaneusMarkerName]["Y"], fields[self.RightPosteriorCalcaneusMarkerName]["Z"], fields[self.RightPosteriorCalcaneusMarkerName]["Exists"]
                    SetTrajectory(SubjectName, self.RightHeelMarkerName, RPCALx, RPCALy, RPCALz, exists )
            
            
#Calls the main Function           
Main()