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
# This code is run for the cases when foot can not be plantgrade
# Second static trial is collected with subject sitting such that foot is flat on the ground.
# mSHCG foot segment transformations are computed in this program

Created on Thu Feb 01 11:09:51 2018
Last Update: 26 Aug, 2024

@author: psaraswat
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""
VersionNumber = 'Py3_v1.3'

import os.path
import sys
import datetime

import tkinter as tk     ## Python 3.x

#import tkFileDialog
from tkinter import filedialog,messagebox

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import reportlab.lib.colors as reportlabColors

import numpy as np

#import Vicon Nexus Subroutines
#from viconnexusapi import ViconNexus
vicon = None#ViconNexus.ViconNexus()
from Py3_varExtractor import extract_fields_by_filename
import gapi
from gapi import  run_tkinter_grpc_server,SetTrajectory

#import Common Vector/Matrix Operations Modules
import Py3_MathModules as math
import Py3_GaitModules as gait
from pathlib import Path
UserPreferencesFileName = Path(__file__).parent/'Py3_UserPreferences.py'

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--TestingCondition', '-t', default="BF", help='Testing condition parameter (default: BF)')
parser.add_argument('--batch', '-b', action='store_true', help='Enable batch processing mode')
args, unknown = parser.parse_known_args()

TestingCondition = args.TestingCondition
gapi.BATCH_MODE = args.batch

_proj_root = Path(__file__).resolve().parent.parent.parent.parent
_sess_xml = Path(__file__).resolve().parent.parent / "Data" / "test_002" / "2025-02-21_0003" / "session.xml"
if not _sess_xml.exists():
    _sess_xml = Path(__file__).resolve().parent.parent / "Data" / "Shriners_test_002" / "2025-02-21_0003" / "session.xml"

fields = extract_fields_by_filename(str(_sess_xml), "Static 1.qtm")

#print(vicon.GetSubjectNames())
SubjectName = fields["Name"]
FilePath, FileName = fields["Path"], fields["Filename"]
calib_dir = Path(FilePath) / "Calibration"
calib_dir.mkdir(parents=True, exist_ok=True)
_sitting_cand = calib_dir / ('SittingFootStatic_' + TestingCondition + '_' + SubjectName + '.py')
if _sitting_cand.exists():
    SittingFootStaticDataFileName = _sitting_cand
elif (Path(FilePath) / ('SittingFootStatic_' + TestingCondition + '_' + SubjectName + '.py')).exists():
    SittingFootStaticDataFileName = Path(FilePath) / ('SittingFootStatic_' + TestingCondition + '_' + SubjectName + '.py')
else:
    SittingFootStaticDataFileName = _sitting_cand

_calib_cand = calib_dir / ('Static_' + TestingCondition + '_' + SubjectName + '.py')
if _calib_cand.exists():
    StaticDataFileName = _calib_cand
elif (Path(FilePath) / ('Static_' + TestingCondition + '_' + SubjectName + '.py')).exists():
    StaticDataFileName = Path(FilePath) / ('Static_' + TestingCondition + '_' + SubjectName + '.py')
else:
    StaticDataFileName = _calib_cand

#Height and Width of App Display
AppHeight=360 
AppWidth=800 
#Default font for display
Large_Font= "Calibri 14 bold" #("Calibri", 20)
Small_Font_Bold = "Calibri 12 bold"
Small_Font= ("Calibri", 12)
Smaller_Font= ("Calibri", 10)
Bold_Small_Font="Calibri 14 bold"

#This is the main function and has references to all the forms
class Static_Main(tk.Tk):
    #This __init__ part of the code runs everytime
    def __init__(self):
        
        tk.Tk.__init__(self)
        # Specify title of Form
        tk.Tk.wm_title(self, "Foot Static")
        
        #Create a dictionary of frames/forms
        self.frames = {} 
        frames = (PatientInfo_Page, StaticSubjectCalibrationReport_Page)
        #Specify all the form names
        for F in frames:
            frame = F(self)
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[F] = frame
    
        #Initialize the first form
        self.frames[PatientInfo_Page].tkraise()
        self.frames[PatientInfo_Page].build_UI()
        
class PatientInfo_Page(tk.Frame):

    def __init__(self, parent):
        tk.Frame.__init__(self, parent, width=AppWidth, height=AppHeight)
        self.parent = parent
        self.grid()
         
    def build_UI(self):    
        # Crete a Canvas to draw section on forms
        SectionCanvas = tk.Canvas(self, width=AppWidth, height=AppHeight)
        SectionCanvas.pack()
        
        # Proceed button chnages the form display to QA Report and saves data
        ProceedButton = tk.Button(self, text="Save &" + '\n'+ "Proceed",font=Small_Font,  justify = 'center', command= lambda: [saveSubjectData(),self.parent.frames[StaticSubjectCalibrationReport_Page].tkraise(),self.parent.frames[StaticSubjectCalibrationReport_Page].build_UI()])
        ProceedButton.place(x=700,y=20,width=90,height=180)
        # Quite buton closes app
        QuitButton = tk.Button(self,text="Quit",font=Small_Font, command=lambda: quit())
        QuitButton.place(x=700,y=210,width=90,height=90) 

# =============================================================================
#       Patient Information widgets are created here 
# =============================================================================       
        
        
        StaticForwardDirectionLabel = tk.Label(self, text="Static Forward Direction", font=Small_Font) 
        StaticForwardDirectionLabel.place(x=50,y=10)
        
        StaticForwardDirectionOptions = ["+X","-X","+Y","-Y"]
        StaticForwardDirection = tk.StringVar(self)
        if os.path.exists(SittingFootStaticDataFileName):
            exec(open(SittingFootStaticDataFileName).read())
        else:
            exec(open(UserPreferencesFileName).read())
        StaticForwardDirection.set(self.StaticForwardDirection)
        StaticForwardDirectionDropDown = tk.OptionMenu(self, StaticForwardDirection, *StaticForwardDirectionOptions)
        StaticForwardDirectionDropDown.place(x=50,y=30,width=150,height=25)
        
        StaticFrameNumberLabel = tk.Label(self, text="Static Frame Number", font=Small_Font)
        StaticFrameNumberLabel.place(x=450,y=20)
        StaticFrameNumber = tk.Entry(self, justify='center')
        StaticFrameNumber.place(x=600,y=20,width=40,height=20)
       
        #Draw box for Foot Model
        SectionCanvas.create_rectangle(20, 100, 680, 300, outline='grey')
        
        FootModelTitle = tk.Label(self, text="Foot Model Parameters", font=Small_Font)
        FootModelTitle.place(x=75,y=90)
        
        self.LeftFootModelCheck=tk.IntVar()
        self.LeftFootModelCheck.set('0')
        LeftFootModelCheckButton = tk.Checkbutton(self, text='Left', variable=self.LeftFootModelCheck, font=Small_Font)
        LeftFootModelCheckButton.place(x=150,y=160)
        
        self.RightFootModelCheck=tk.IntVar()
        self.RightFootModelCheck.set('0')
        RightFootModelCheckButton = tk.Checkbutton(self, text='Right', variable=self.RightFootModelCheck, font=Small_Font)
        RightFootModelCheckButton.place(x=250,y=160)
        
        HindfootVarusUnitLabel = tk.Label(self, text='deg', font=Small_Font)
        HindfootVarusUnitLabel.place(x=50,y=185)
        HindfootVarusLabel = tk.Label(self, text='Hindfoot Varus/Valgus', font=Small_Font)
        HindfootVarusLabel.place(x=350,y=185)
        LeftHindfootVarus = tk.Entry(self,justify='center')
        LeftHindfootVarus.place(x=150,y=185,width=80,height=20)
        RightHindfootVarus = tk.Entry(self,justify='center')
        RightHindfootVarus.place(x=250,y=185,width=80,height=20)
        
        CalcanealPitchUnitLabel = tk.Label(self, text='deg', font=Small_Font)
        CalcanealPitchUnitLabel.place(x=50,y=210)
        CalcanealPitchLabel = tk.Label(self, text='Calcaneal Pitch', font=Small_Font)
        CalcanealPitchLabel.place(x=350,y=210)
        LeftCalcanealPitch = tk.Entry(self,justify='center')
        LeftCalcanealPitch.place(x=150,y=210,width=80,height=20)
        RightCalcanealPitch = tk.Entry(self,justify='center')
        RightCalcanealPitch.place(x=250,y=210,width=80,height=20)
        
        HindfootProgressionUnitLabel = tk.Label(self, text='deg', font=Small_Font)
        HindfootProgressionUnitLabel.place(x=50,y=235)
        HindfootProgressionLabel = tk.Label(self, text='Hindfoot Progression', font=Small_Font)
        HindfootProgressionLabel.place(x=350,y=235)
        LeftHindfootProgression = tk.Entry(self,justify='center')
        LeftHindfootProgression.place(x=150,y=235,width=80,height=20)
        RightHindfootProgression = tk.Entry(self,justify='center')
        RightHindfootProgression.place(x=250,y=235,width=80,height=20)
        
        FirstMetatarsalPitchUnitLabel = tk.Label(self, text='deg', font=Small_Font)
        FirstMetatarsalPitchUnitLabel.place(x=50,y=260)
        FirstMetatarsalPitchLabel = tk.Label(self, text='First Metatarsal Pitch', font=Small_Font)
        FirstMetatarsalPitchLabel.place(x=350,y=260)
        LeftFirstMetatarsalPitch = tk.Entry(self,justify='center')
        LeftFirstMetatarsalPitch.place(x=150,y=260,width=80,height=20)
        RightFirstMetatarsalPitch = tk.Entry(self,justify='center')
        RightFirstMetatarsalPitch.place(x=250,y=260,width=80,height=20)
        
        
# =========================================================================================
#       Read Parameters from Nexus or existing Static Parameters File and tabulate parameters    
# =========================================================================================
        SubjectName = fields["Name"]
        FilePath, FileName = fields["Path"],fields["Filename"]
        StartFrame, EndFrame = fields["First Frame"],fields["Last Frame"] 
        
        if os.path.exists(SittingFootStaticDataFileName):
            # Execute Static File to read stored parameters values
            exec(open(SittingFootStaticDataFileName).read())
            # Put in stored values onto display
            self.LeftFootModelCheck.set('1')#self.valueLeftFootModelCheck)
            self.RightFootModelCheck.set('1')#self.valueRightFootModelCheck)
            LeftHindfootVarus.insert(0,self.valueLeftHindfootVarus)
            RightHindfootVarus.insert(0,self.valueRightHindfootVarus)
            LeftCalcanealPitch.insert(0,self.valueLeftCalcanealPitch)
            RightCalcanealPitch.insert(0,self.valueRightCalcanealPitch) 
            try:
                LeftHindfootProgression.insert(0,self.valueLeftHindfootProgression)
            except:
                pass
            try:
                RightHindfootProgression.insert(0,self.valueRightHindfootProgression)
            except:
                pass
            LeftFirstMetatarsalPitch.insert(0,self.valueLeftFirstMetatarsalPitch)
            RightFirstMetatarsalPitch.insert(0,self.valueRightFirstMetatarsalPitch)
            try:# If Static Frame Option exists
                StaticFrameNumber.insert(0,self.valueStaticFrameNumber)
            except:# Default if Static Frame Number not found in Py file
                StaticFrameNumber.insert(0,StartFrame + 20) # Default to 20th frame.
            
        elif  os.path.exists(StaticDataFileName):
            exec(open(StaticDataFileName).read())
            StaticFrameNumber.insert(0,StartFrame + 20) # Default to 20th frame.
            # If Static parmaeters file doesn't exist, read parameters values from Nexus
            # Read Foot Model Parameters
            if self.valueLeftHindfootVarus:
                LeftHindfootVarus.insert(0,int(round(float(self.valueLeftHindfootVarus),0)))
                self.LeftFootModelCheck.set('1')
            if self.valueRightHindfootVarus:
                RightHindfootVarus.insert(0,int(round(float(self.valueRightHindfootVarus),0)))
                self.RightFootModelCheck.set('1')
            if self.valueLeftFirstMetatarsalPitch:
                LeftFirstMetatarsalPitch.insert(0,int(round(float(self.valueLeftFirstMetatarsalPitch),0)))
            if self.valueRightFirstMetatarsalPitch:
                RightFirstMetatarsalPitch.insert(0,int(round(float(self.valueRightFirstMetatarsalPitch),0)))
            if self.valueLeftCalcanealPitch:
                LeftCalcanealPitch.insert(0,int(round(float(self.valueLeftCalcanealPitch),0)))
            if self.valueRightCalcanealPitch:
                RightCalcanealPitch.insert(0,int(round(float(self.valueRightCalcanealPitch),0)))
        else:
            #Terminate with a message box Please run StaticMain first with Foot values
            messagebox.showerror("Error", "Please run StaticMain first with Foot values.")
            quit()


        # =============================================================================
        #       Function to save Subject parameters in SittingFootStatic_BF_MRN.py file. It gets executed with Proceed button.
        # =============================================================================
        def saveSubjectData():
            if os.path.exists(SittingFootStaticDataFileName):
                # Read Current File
                SittingFootStaticDataFile = open(SittingFootStaticDataFileName,'r')
                lines=SittingFootStaticDataFile.readlines()
                SittingFootStaticDataFile.close()
                
                # Open Static py File
                SittingFootStaticDataFile = open(SittingFootStaticDataFileName,'w+')
                # Restore all the settings except foot model parameters
                LeftHindfootProgressionExists = False # Not available in old Static files
                RighttHindfootProgressionExists = False # Not available in old Static files
                StaticFrameNumberExists = False # Not availabe in old static files
                for line in lines:
                    words=line.split()
                    if words[0] == 'self.valueStaticFrameNumber':
                        StaticFrameNumberExists = True
                        SittingFootStaticDataFile.write('self.valueStaticFrameNumber = ' + "'" + StaticFrameNumber.get() + "'" + '\n')
                        continue
                    if words[0] == 'self.StaticForwardDirection':
                        SittingFootStaticDataFile.write('self.StaticForwardDirection = ' + "'" + str(StaticForwardDirection.get()) + "'" + '\n')
                        continue
                    if words[0] == 'self.valueLeftFootModelCheck':
                        SittingFootStaticDataFile.write('self.valueLeftFootModelCheck = ' + "'" + str(self.LeftFootModelCheck.get()) + "'" + '\n')
                        continue
                    if words[0] == 'self.valueLeftHindfootVarus':
                        SittingFootStaticDataFile.write('self.valueLeftHindfootVarus = ' + "'" + LeftHindfootVarus.get() + "'" + '\n')
                        continue
                    if words[0] == 'self.valueLeftCalcanealPitch':
                        SittingFootStaticDataFile.write('self.valueLeftCalcanealPitch = ' + "'" + LeftCalcanealPitch.get() + "'" + '\n')
                        continue
                    if words[0] == 'self.valueLeftHindfootProgression':
                        LeftHindfootProgressionExists = True
                        SittingFootStaticDataFile.write('self.valueLeftHindfootProgression = ' + "'" + LeftHindfootProgression.get() + "'" + '\n')
                        continue
                    if words[0] == 'self.valueLeftFirstMetatarsalPitch':
                        SittingFootStaticDataFile.write('self.valueLeftFirstMetatarsalPitch = ' + "'" + LeftFirstMetatarsalPitch.get() + "'" + '\n')
                        continue
                    if words[0] == 'self.valueRightFootModelCheck':
                        SittingFootStaticDataFile.write('self.valueRightFootModelCheck = ' + "'" + str(self.RightFootModelCheck.get()) + "'" + '\n')
                        continue
                    if words[0] == 'self.valueRightHindfootVarus':
                        SittingFootStaticDataFile.write('self.valueRightHindfootVarus = ' + "'" + RightHindfootVarus.get() + "'" + '\n')
                        continue
                    if words[0] == 'self.valueRightCalcanealPitch':
                        SittingFootStaticDataFile.write('self.valueRightCalcanealPitch = ' + "'" + RightCalcanealPitch.get() + "'" + '\n')
                        continue
                    if words[0] == 'self.valueRightHindfootProgression':
                        RighttHindfootProgressionExists = True
                        SittingFootStaticDataFile.write('self.valueRightHindfootProgression = ' + "'" + RightHindfootProgression.get() + "'" + '\n')
                        continue
                    if words[0] == 'self.valueRightFirstMetatarsalPitch':
                        SittingFootStaticDataFile.write('self.valueRightFirstMetatarsalPitch = ' + "'" + RightFirstMetatarsalPitch.get() + "'" + '\n')
                        continue
                    SittingFootStaticDataFile.write(line)
                if StaticFrameNumberExists is False:
                    SittingFootStaticDataFile.write('self.valueStaticFrameNumber = ' + "'" + StaticFrameNumber.get() + "'" + '\n')
                if LeftHindfootProgressionExists is False:
                    SittingFootStaticDataFile.write('self.valueLeftHindfootProgression = ' + "'" + LeftHindfootProgression.get() + "'" + '\n')
                if RighttHindfootProgressionExists is False:
                    SittingFootStaticDataFile.write('self.valueRightHindfootProgression = ' + "'" + RightHindfootProgression.get() + "'" + '\n')
                    
                SittingFootStaticDataFile.close()
            else:
                # Open Static py file
                SittingFootStaticDataFile = open(SittingFootStaticDataFileName,'w+')
                # Copy User Preferences 
                UserPreferencesFile = open(UserPreferencesFileName,'r')
                lines=UserPreferencesFile.readlines()
                UserPreferencesFile.close()
                for line in lines:
                    words=line.split()
                    SittingFootStaticDataFile.write(line)
                # Write Subject Data into Static Anthropometric File
                SittingFootStaticDataFile.write('self.valueStaticFrameNumber = ' + "'" + str(StaticFrameNumber.get()) + "'" + '\n')
                SittingFootStaticDataFile.write('self.valueSittingFootStaticFile = ' + "'" + FileName + "'" + '\n')
                SittingFootStaticDataFile.write('self.valueLeftFootModelCheck = ' + "'" + str(self.LeftFootModelCheck.get()) + "'" + '\n')
                SittingFootStaticDataFile.write('self.valueRightFootModelCheck = ' + "'" + str(self.RightFootModelCheck.get()) + "'" + '\n')
                SittingFootStaticDataFile.write('self.valueLeftHindfootVarus = ' + "'" + LeftHindfootVarus.get() + "'" + '\n')
                SittingFootStaticDataFile.write('self.valueLeftCalcanealPitch = ' + "'" + LeftCalcanealPitch.get() + "'" + '\n')
                SittingFootStaticDataFile.write('self.valueLeftHindfootProgression = ' + "'" + LeftHindfootProgression.get() + "'" + '\n')
                SittingFootStaticDataFile.write('self.valueLeftFirstMetatarsalPitch = ' + "'" + LeftFirstMetatarsalPitch.get() + "'" + '\n')
                SittingFootStaticDataFile.write('self.valueRightHindfootVarus = ' + "'" + RightHindfootVarus.get() + "'" + '\n')
                SittingFootStaticDataFile.write('self.valueRightCalcanealPitch = ' + "'" + RightCalcanealPitch.get() + "'" + '\n')
                SittingFootStaticDataFile.write('self.valueRightHindfootProgression = ' + "'" + RightHindfootProgression.get() + "'" + '\n')
                SittingFootStaticDataFile.write('self.valueRightFirstMetatarsalPitch = ' + "'" + RightFirstMetatarsalPitch.get() + "'" + '\n')
                SittingFootStaticDataFile.close() 
 
       
        
class StaticSubjectCalibrationReport_Page(tk.Frame):

    def __init__(self, parent):
        tk.Frame.__init__(self,parent, width=AppWidth, height=AppHeight)
        self.parent = parent
        self.grid()
        
    def build_UI(self):     
        # Crete a Canvas to draw section on forms
        SectionCanvas = tk.Canvas(self, width=AppWidth, height=AppHeight)
        SectionCanvas.pack()
        # Saves Static Results in Pdf file
        SavePdfButton = tk.Button(self, text="Save PDF",font=Small_Font, command=lambda: [saveTransformationMatrices(),savePdf(),self.parent.frames[StaticSubjectCalibrationReport_Page].build_UI()]) 
        SavePdfButton.place(x=700,y=20,width=90,height=180)
        # Back button chnages the form display to Patient Information Page
        BackButton = tk.Button(self, text="Back",font=Small_Font, command=lambda: [self.parent.frames[PatientInfo_Page].tkraise(),self.parent.frames[PatientInfo_Page].build_UI(),ErrorMessagesLabel.place_forget(),ErrorMessagesText.place_forget()])
        BackButton.place(x=700,y=210,width=90,height=40)
        #Quit button cloese app
        QuitButton = tk.Button(self,text="Quit",font=Small_Font, command=lambda: [saveTransformationMatrices(),quit()])
        QuitButton.place(x=700,y=260,width=90,height=40)
       
# =============================================================================
#       Patient Information widgets are created here
# =============================================================================
        SubjectName = fields["Name"]
        FilePath, FileName = fields["Path"],fields["Filename"]
               
        #Create Error Label but place them only if error occurs
        ErrorMessagesLabel = tk.Label(self,text='Warnings', font=Bold_Small_Font)
        ErrorMessagesText = tk.Text(self)
        ErrorMessagesLabel['fg']='red'
        ErrorMessagesText['fg']='red'
        #ErrorMessagesLabel.place(x=50,y=100, width=130,height=85)
        #ErrorMessagesText.place(x=195,y=95,width=490,height=85)
        
        #Create File Save Error Label but place them only if error occurs
        SaveErrorMessagesLabel = tk.Label(self,text='Warning', font=Small_Font, anchor = 'w')
        SaveErrorMessagesLabel['fg']='red'
        
# =============================================================================
#       Posture Information Form  widgets are created here
# =============================================================================
        SectionCanvas.create_rectangle(20, 20, 680, 300)
        
        StandingPostureLabel = tk.Label(self, text="Sitting Foot Posture (degrees)", font=Large_Font)
        StandingPostureLabel.place(x=50,y=30)
        
        LeftLabel = tk.Label(self, text='Left', font=Bold_Small_Font)
        LeftLabel.place(x=425,y=40)
        
        RightLabel = tk.Label(self, text='Right', font=Bold_Small_Font)
        RightLabel.place(x=575,y=40)
        
        # Foot Posture
        SectionCanvas.create_rectangle(40, 80, 660, 280, outline = 'grey')
        FootSegmentsLabel = tk.Label(self, text='Foot Segments', font=Small_Font, anchor='w')
        FootSegmentsLabel.place(x=50,y=65)
        
        HindfootPitchLabel = tk.Label(self, text='Hindfoot Pitch', font=Small_Font, anchor='e') 
        HindfootPitchLabel.place(x=100,y=98,width=290)
        LeftHindfootPitch = tk.Entry(self,justify='center')
        LeftHindfootPitch.place(x=400,y=100,height=20,width=100)
        RightHindfootPitch = tk.Entry(self,justify='center')
        RightHindfootPitch.place(x=550,y=100,height=20,width=100)
        
        HindfootProgressionLabel = tk.Label(self, text='Hindfoot Progression', font=Small_Font, anchor='e') 
        HindfootProgressionLabel.place(x=100,y=123,width=290)
        LeftHindfootProgression = tk.Entry(self,justify='center')
        LeftHindfootProgression.place(x=400,y=125,height=20,width=100)
        RightHindfootProgression = tk.Entry(self,justify='center')
        RightHindfootProgression.place(x=550,y=125,height=20,width=100)
        
        HindfootInvEversionLabel = tk.Label(self, text='Hindfoot Varus/Valgus', font=Small_Font, anchor='e') 
        HindfootInvEversionLabel.place(x=100,y=148,width=290)
        LeftHindfootInvEversion = tk.Entry(self,justify='center')
        LeftHindfootInvEversion.place(x=400,y=150,height=20,width=100)
        RightHindfootInvEversion = tk.Entry(self,justify='center')
        RightHindfootInvEversion.place(x=550,y=150,height=20,width=100)
        
        ForefootPitchLabel = tk.Label(self, text='Forefoot Pitch', font=Small_Font, anchor='e') 
        ForefootPitchLabel.place(x=100,y=173,width=290)
        LeftForefootPitch = tk.Entry(self,justify='center')
        LeftForefootPitch.place(x=400,y=175,height=20,width=100)
        RightForefootPitch = tk.Entry(self,justify='center')
        RightForefootPitch.place(x=550,y=175,height=20,width=100)
        
        ForefootProgressionLabel = tk.Label(self, text='Forefoot Progression', font=Small_Font, anchor='e') 
        ForefootProgressionLabel.place(x=100,y=198,width=290)
        LeftForefootProgression = tk.Entry(self,justify='center')
        LeftForefootProgression.place(x=400,y=200,height=20,width=100)
        RightForefootProgression = tk.Entry(self,justify='center')
        RightForefootProgression.place(x=550,y=200,height=20,width=100)
        
        MidfootAbAdductionLabel = tk.Label(self, text='Midfoot Complex Ab/Adduction', font=Small_Font, anchor='e') 
        MidfootAbAdductionLabel.place(x=100,y=223,width=290)
        LeftMidfootAbAdduction = tk.Entry(self,justify='center')
        LeftMidfootAbAdduction.place(x=400,y=225,height=20,width=100)
        RightMidfootAbAdduction = tk.Entry(self,justify='center')
        RightMidfootAbAdduction.place(x=550,y=225,height=20,width=100)
        
        HalluxProgressionLabel = tk.Label(self, text='MTP1 Varus/Valgus', font=Small_Font, anchor='e') 
        HalluxProgressionLabel.place(x=100,y=248,width=290)
        LeftHalluxProgression = tk.Entry(self,justify='center')
        LeftHalluxProgression.place(x=400,y=250,height=20,width=100)
        RightHalluxProgression = tk.Entry(self,justify='center')
        RightHalluxProgression.place(x=550,y=250,height=20,width=100)
        
# =============================================================================     
        
# =============================================================================
#       Posture Measures are computed from Marker data  
# =============================================================================
        
        # Extract Clinical Values
        exec(open(SittingFootStaticDataFileName).read())
        
        # =============================================================================
        #         Read Marker data from Start Frame (First Frame) for Static Check
        #         Dispplay Warning if marker not found
        # =============================================================================
        def HasTrajectory( subjectName, markerName):
            return markerName in fields
        # Function to extract markerdata into an array and check if data exists
        def MarkerCheck(Subject, MarkerName, FirstFrame):
            # Check if marker exists at all
            if HasTrajectory(Subject,MarkerName) is True:
                MarkerData = np.array((fields[MarkerName]["X"][FirstFrame], fields[MarkerName]["Y"][FirstFrame], fields[MarkerName]["Z"][FirstFrame]))
                # Check if marker is labeled at the first frame
                if MarkerData[0] == 0 or MarkerData[1] == 0 or MarkerData[2] == 0:
                    ErrorMessagesLabel.place(x=50,y=310, width=130,height=20)
                    ErrorMessagesText.place(x=195,y=295,width=490,height=85)
                    ErrorMessage = 'Marker ' + MarkerName + ' is not labeled at frame ' + str(FirstFrame) + '\n'
                    ErrorMessagesText.insert(tk.END,ErrorMessage)
            else:
                MarkerData = np.array([0,0,0])
                # Dont show error for Trunk Markers
                ExcludedForErrorMarkerNames = [self.C7MarkerName, self.LeftClavicleMarkerName, self.RightClavicleMarkerName]
                if not MarkerName in ExcludedForErrorMarkerNames: 
                    ErrorMessagesLabel.place(x=50,y=310, width=130,height=20)
                    ErrorMessagesText.place(x=195,y=310,width=490,height=40)
                    ErrorMessage = 'Marker ' + MarkerName + ' is not Found ' + '\n'
                    ErrorMessagesText.insert(tk.END,ErrorMessage)
            return MarkerData    
        
        # Read Left Foot Markers
        if self.valueLeftFootModelCheck == '1':
            LeftLateralCalcaneusMarker = MarkerCheck(SubjectName,self.LeftLateralCalcaneusMarkerName, int(self.valueStaticFrameNumber))
            LeftMedialCalcaneusMarker = MarkerCheck(SubjectName,self.LeftMedialCalcaneusMarkerName, int(self.valueStaticFrameNumber))
            LeftPosteriorCalcaneusMarker = MarkerCheck(SubjectName,self.LeftPosteriorCalcaneusMarkerName, int(self.valueStaticFrameNumber))
            LeftFirstMetarsalBaseMarker = MarkerCheck(SubjectName,self.LeftFirstMetarsalBaseMarkerName, int(self.valueStaticFrameNumber))
            LeftFirstMetarsalHeadMarker = MarkerCheck(SubjectName,self.LeftFirstMetarsalHeadMarkerName, int(self.valueStaticFrameNumber))
            LeftFifthMetarsalHeadMarker = MarkerCheck(SubjectName,self.LeftFifthMetarsalHeadMarkerName, int(self.valueStaticFrameNumber))
            LeftHalluxMarker = MarkerCheck(SubjectName,self.LeftHalluxMarkerName, int(self.valueStaticFrameNumber))
            Left23MetatarsalBaseMarker = MarkerCheck(SubjectName,self.Left23MetatarsalBaseMarkerName, int(self.valueStaticFrameNumber))
            Left23MetatarsalHeadMarker = MarkerCheck(SubjectName,self.Left23MetatarsalHeadMarkerName, int(self.valueStaticFrameNumber))
            LeftFirstMetatarsalMedialBaseMarker = MarkerCheck(SubjectName,self.LeftFirstMetatarsalMedialBaseMarkerName, int(self.valueStaticFrameNumber))
            LeftFirstMetatarsalMedialHeadMarker = MarkerCheck(SubjectName,self.LeftFirstMetatarsalMedialHeadMarkerName, int(self.valueStaticFrameNumber))
            LeftCalcanealPeronealTrochleaMarker = MarkerCheck(SubjectName,self.LeftCalcanealPeronealTrochleaMarkerName, int(self.valueStaticFrameNumber))
            LeftFirstMetatarsoPhalangealJointMarker = MarkerCheck(SubjectName,self.LeftFirstMetatarsoPhalangealJointMarkerName, int(self.valueStaticFrameNumber))

 
        
        # Read Right Foot Markers
        if self.valueRightFootModelCheck == '1':
            RightLateralCalcaneusMarker = MarkerCheck(SubjectName,self.RightLateralCalcaneusMarkerName, int(self.valueStaticFrameNumber))
            RightMedialCalcaneusMarker = MarkerCheck(SubjectName,self.RightMedialCalcaneusMarkerName, int(self.valueStaticFrameNumber))
            RightPosteriorCalcaneusMarker = MarkerCheck(SubjectName,self.RightPosteriorCalcaneusMarkerName, int(self.valueStaticFrameNumber))
            RightFirstMetarsalBaseMarker = MarkerCheck(SubjectName,self.RightFirstMetarsalBaseMarkerName, int(self.valueStaticFrameNumber))
            RightFirstMetarsalHeadMarker = MarkerCheck(SubjectName,self.RightFirstMetarsalHeadMarkerName, int(self.valueStaticFrameNumber))
            RightFifthMetarsalHeadMarker = MarkerCheck(SubjectName,self.RightFifthMetarsalHeadMarkerName, int(self.valueStaticFrameNumber))
            RightHalluxMarker = MarkerCheck(SubjectName,self.RightHalluxMarkerName, int(self.valueStaticFrameNumber))
            Right23MetatarsalBaseMarker = MarkerCheck(SubjectName,self.Right23MetatarsalBaseMarkerName, int(self.valueStaticFrameNumber))
            Right23MetatarsalHeadMarker = MarkerCheck(SubjectName,self.Right23MetatarsalHeadMarkerName, int(self.valueStaticFrameNumber))
            RightFirstMetatarsalMedialBaseMarker = MarkerCheck(SubjectName,self.RightFirstMetatarsalMedialBaseMarkerName, int(self.valueStaticFrameNumber))
            RightFirstMetatarsalMedialHeadMarker = MarkerCheck(SubjectName,self.RightFirstMetatarsalMedialHeadMarkerName, int(self.valueStaticFrameNumber))
            RightCalcanealPeronealTrochleaMarker = MarkerCheck(SubjectName,self.RightCalcanealPeronealTrochleaMarkerName, int(self.valueStaticFrameNumber))
            RightFirstMetatarsoPhalangealJointMarker = MarkerCheck(SubjectName,self.RightFirstMetatarsoPhalangealJointMarkerName, int(self.valueStaticFrameNumber))
        # =============================================================================

        #Read orientation of the Standing patient relative to laboratory coordinate system
        #print(self.StaticForwardDirection)        
        if self.StaticForwardDirection == '+X':
            RotationMatrix = np.array([[ 1.,  0.,  0.], [ 0.,  1.,  0.],[ 0.,  0.,  1.]])
        if self.StaticForwardDirection == '-X':
            RotationMatrix = np.array([[-1.,  0.,  0.], [ 0., -1.,  0.],[ 0.,  0.,  1.]])
        if self.StaticForwardDirection == '+Y':
            RotationMatrix = np.array([[ 0.,  1.,  0.], [-1.,  0.,  0.],[ 0.,  0.,  1.]])
        if self.StaticForwardDirection == '-Y':
            RotationMatrix = np.array([[ 0., -1.,  0.], [ 1.,  0.,  0.],[ 0.,  0.,  1.]])
    
        #Transform marker data if necessary based on direction that the patient is facing
        if self.valueLeftFootModelCheck == '1':
            LeftLateralCalcaneusMarker = RotationMatrix.dot(LeftLateralCalcaneusMarker)
            LeftMedialCalcaneusMarker = RotationMatrix.dot(LeftMedialCalcaneusMarker)
            LeftPosteriorCalcaneusMarker = RotationMatrix.dot(LeftPosteriorCalcaneusMarker)
            LeftFirstMetarsalBaseMarker = RotationMatrix.dot(LeftFirstMetarsalBaseMarker)
            LeftFirstMetarsalHeadMarker = RotationMatrix.dot(LeftFirstMetarsalHeadMarker)
            LeftFifthMetarsalHeadMarker = RotationMatrix.dot(LeftFifthMetarsalHeadMarker)
            LeftHalluxMarker = RotationMatrix.dot(LeftHalluxMarker)
            Left23MetatarsalBaseMarker = RotationMatrix.dot(Left23MetatarsalBaseMarker)
            Left23MetatarsalHeadMarker = RotationMatrix.dot(Left23MetatarsalHeadMarker)
            LeftFirstMetatarsalMedialBaseMarker = RotationMatrix.dot(LeftFirstMetatarsalMedialBaseMarker)
            LeftFirstMetatarsalMedialHeadMarker = RotationMatrix.dot(LeftFirstMetatarsalMedialHeadMarker)
            LeftCalcanealPeronealTrochleaMarker = RotationMatrix.dot(LeftCalcanealPeronealTrochleaMarker)
            LeftFirstMetatarsoPhalangealJointMarker = RotationMatrix.dot(LeftFirstMetatarsoPhalangealJointMarker)

        if self.valueRightFootModelCheck == '1':
            RightLateralCalcaneusMarker = RotationMatrix.dot(RightLateralCalcaneusMarker)
            RightMedialCalcaneusMarker = RotationMatrix.dot(RightMedialCalcaneusMarker)
            RightPosteriorCalcaneusMarker = RotationMatrix.dot(RightPosteriorCalcaneusMarker)
            RightFirstMetarsalBaseMarker = RotationMatrix.dot(RightFirstMetarsalBaseMarker)
            RightFirstMetarsalHeadMarker = RotationMatrix.dot(RightFirstMetarsalHeadMarker)
            RightFifthMetarsalHeadMarker = RotationMatrix.dot(RightFifthMetarsalHeadMarker)
            RightHalluxMarker = RotationMatrix.dot(RightHalluxMarker)
            Right23MetatarsalBaseMarker = RotationMatrix.dot(Right23MetatarsalBaseMarker)
            Right23MetatarsalHeadMarker = RotationMatrix.dot(Right23MetatarsalHeadMarker)
            RightFirstMetatarsalMedialBaseMarker = RotationMatrix.dot(RightFirstMetatarsalMedialBaseMarker)
            RightFirstMetatarsalMedialHeadMarker = RotationMatrix.dot(RightFirstMetatarsalMedialHeadMarker)
            RightCalcanealPeronealTrochleaMarker = RotationMatrix.dot(RightCalcanealPeronealTrochleaMarker)
            RightFirstMetatarsoPhalangealJointMarker = RotationMatrix.dot(RightFirstMetatarsoPhalangealJointMarker)
        
        
        # Compute Technical Coordinate System: Left Foot Segments
        if self.valueLeftFootModelCheck == '1':
            LeftEHindfootTech = gait.TechCS_Hindfoot_mSHCG('Left', LeftLateralCalcaneusMarker, LeftMedialCalcaneusMarker, LeftPosteriorCalcaneusMarker)
            LeftEForefootTech = gait.TechCS_Forefoot_mSHCG('Left', LeftFirstMetarsalBaseMarker, LeftFirstMetarsalHeadMarker, LeftFifthMetarsalHeadMarker)
            LeftEHalluxTech = gait.TechCS_Hallux_mSHCG('Left', LeftHalluxMarker, LeftFirstMetatarsoPhalangealJointMarker, Left23MetatarsalHeadMarker)
            #print(LeftEHindfootTech)
            #print(LeftEForefootTech)
            #print(LeftEHalluxTech)
        
        # Compute Technical Coordinate System: Right Foot Segments
        if self.valueRightFootModelCheck == '1':
            RightEHindfootTech = gait.TechCS_Hindfoot_mSHCG('Right', RightLateralCalcaneusMarker, RightMedialCalcaneusMarker, RightPosteriorCalcaneusMarker)
            RightEForefootTech = gait.TechCS_Forefoot_mSHCG('Right', RightFirstMetarsalBaseMarker, RightFirstMetarsalHeadMarker, RightFifthMetarsalHeadMarker)
            RightEHalluxTech = gait.TechCS_Hallux_mSHCG('Right', RightHalluxMarker, RightFirstMetatarsoPhalangealJointMarker, Right23MetatarsalHeadMarker)
            #print(RightEHindfootTech)
            #print(RightEForefootTech)
            #print(RightEHalluxTech)
            

        # Compute Anatomical Coordinate System: Left Foot Segments
        if self.valueLeftFootModelCheck == '1':
            LeftEHindfootAnat = gait.AnatCS_Hindfoot_mSHCG('Left', LeftLateralCalcaneusMarker, LeftMedialCalcaneusMarker, LeftPosteriorCalcaneusMarker, 
                                                           LeftCalcanealPeronealTrochleaMarker, self.valueLeftHindfootVarus, self.valueLeftCalcanealPitch,self.valueLeftHindfootProgression,self.HindfootValgusIsNegative)
            LeftEForefootAnat = gait.AnatCS_Forefoot_mSHCG('Left', Left23MetatarsalBaseMarker, Left23MetatarsalHeadMarker, LeftFirstMetatarsalMedialBaseMarker,
                                                           LeftFirstMetatarsalMedialHeadMarker, self.valueLeftFirstMetatarsalPitch)
            LeftEHalluxAnat = LeftEHalluxTech
            #print(LeftEHindfootAnat)
            #print(LeftEForefootAnat)
            #print(LeftEHalluxAnat)
        
        # Compute Anatomical Coordinate System: Right Foot Segments
        if self.valueRightFootModelCheck == '1':
            RightEHindfootAnat = gait.AnatCS_Hindfoot_mSHCG('Right', RightLateralCalcaneusMarker, RightMedialCalcaneusMarker, RightPosteriorCalcaneusMarker, 
                                                           RightCalcanealPeronealTrochleaMarker, self.valueRightHindfootVarus, self.valueRightCalcanealPitch,self.valueRightHindfootProgression,self.HindfootValgusIsNegative)
            RightEForefootAnat = gait.AnatCS_Forefoot_mSHCG('Right', Right23MetatarsalBaseMarker, Right23MetatarsalHeadMarker, RightFirstMetatarsalMedialBaseMarker,
                                                           RightFirstMetatarsalMedialHeadMarker, self.valueRightFirstMetatarsalPitch)
            RightEHalluxAnat = RightEHalluxTech
            #print(RightEHindfootAnat)
            #print(RightEForefootAnat)
            #print(RightEHalluxAnat)
            
        #Compute Attitude of Anatomical Coordinate Systems Relative to their respective Technical Coordinate System
        if self.valueLeftFootModelCheck == '1':
            LeftEHindfootAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(LeftEHindfootAnat, LeftEHindfootTech)
            LeftEForefootAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(LeftEForefootAnat, LeftEForefootTech)
            LeftEHalluxAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(LeftEHalluxAnat, LeftEHalluxTech)
            Left23MetatarsalHeadMarkerForefoot = math.TransformPointIntoMovingCoors(Left23MetatarsalHeadMarker, LeftEForefootTech, LeftFirstMetarsalBaseMarker)
            LeftFirstMetatarsoPhalangealJointMarkerForefoot = math.TransformPointIntoMovingCoors(LeftFirstMetatarsoPhalangealJointMarker, LeftEForefootTech, LeftFirstMetarsalBaseMarker)
              
        if self.valueRightFootModelCheck == '1':
            RightEHindfootAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(RightEHindfootAnat, RightEHindfootTech)
            RightEForefootAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(RightEForefootAnat, RightEForefootTech)
            RightEHalluxAnatRelTech = math.TransformAnatCoorSysIntoTechCoors(RightEHalluxAnat, RightEHalluxTech)
            Right23MetatarsalHeadMarkerForefoot = math.TransformPointIntoMovingCoors(Right23MetatarsalHeadMarker, RightEForefootTech, RightFirstMetarsalBaseMarker)
            RightFirstMetatarsoPhalangealJointMarkerForefoot = math.TransformPointIntoMovingCoors(RightFirstMetatarsoPhalangealJointMarker, RightEForefootTech, RightFirstMetarsalBaseMarker)
            
        #print(ETrunkAnatRelTech)
        #print(EPelvisAnatRelTech)
        #print(LeftEThighAnatRelTech)
        #print(LeftEShankProximalAnatRelTech)
        #print(LeftEShankDistalAnatRelTech)
        #print(LeftEFootAnatRelTech)
        #print(RightEThighAnatRelTech)
        #print(RightEShankProximalAnatRelTech)
        #print(RightEShankDistalAnatRelTech)
        #print(RightEFootAnatRelTech)
        
        
        
        #initialize the global or lab coordinate system
        ELab = np.eye(3)
        
        #Compute Left Foot kinematics
        if self.valueLeftFootModelCheck == '1':
            LeftHindfootAnglesRad = math.EulerAngles_ZYX(LeftEHindfootAnat,ELab)
            LeftForefootAnglesRad = math.EulerAngles_ZYX(LeftEForefootAnat,ELab)
            LeftHalluxAnglesRad   = math.EulerAngles_YXZ(LeftEHalluxAnat,ELab)
            LeftToesAnglesRad = math.EulerAngles_YXZ(LeftEHalluxAnat,LeftEForefootAnat)
            #print LeftHindfootAnglesRad
            #print LeftForefootAnglesRad
            #print LeftHalluxAnglesRad
            #print LeftAnkleComplexAnglesRad
            #print LeftMidfootAnglesRad
            #print LeftToesAnglesRad
        #Compute Right Foot kinematics
        if self.valueRightFootModelCheck == '1':
            RightHindfootAnglesRad = math.EulerAngles_ZYX(RightEHindfootAnat,ELab)
            RightForefootAnglesRad = math.EulerAngles_ZYX(RightEForefootAnat,ELab)
            RightHalluxAnglesRad   = math.EulerAngles_YXZ(RightEHalluxAnat,ELab)
            RightToesAnglesRad = math.EulerAngles_YXZ(RightEHalluxAnat,RightEForefootAnat)
            #print RightHindfootAnglesRad
            #print RightForefootAnglesRad
            #print RightHalluxAnglesRad
            #print RightAnkleComplexAnglesRad
            #print RightMidfootAnglesRad
            #print RightToesAnglesRad   
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
        
        #Convert units of angles from radians to degrees & set sign based on side and plotting convention
        Sign = -1 # For Left Side
        
        T1, T1[0,0], T1[1,1], T1[2,2] = np.eye(3), -Sign, +1, Sign
        T2, T2[0,0], T2[1,1], T2[2,2] = np.eye(3),  Sign, -1, Sign
        T3, T3[0,0], T3[1,1], T3[2,2] = np.eye(3),  Sign, +1, Sign
        
        if self.valueLeftFootModelCheck == '1':
            LeftHindfootAnglesDeg = T1.dot(LeftHindfootAnglesRad) * 180 / np.pi 
            LeftForefootAnglesDeg = T1.dot(LeftForefootAnglesRad) * 180 / np.pi 
            LeftHalluxAnglesDeg   = T1.dot(LeftHalluxAnglesRad) * 180 / np.pi 
            LeftToesAnglesDeg = T2.dot(LeftToesAnglesRad) * 180 / np.pi 
        #print(LeftTrunkAnglesDeg)
        #print(LeftPelvisAnglesDeg)
        #print(LeftThighAnglesDeg)
        #print(LeftShankAnglesDeg)
        #print(LeftFootAnglesDeg)
        #print(LeftHipAnglesDeg)
        #print(LeftKneeAnglesDeg)
        #print(LeftAnkleAnglesDeg)
        
        Sign = 1 #For Right Side
        
        T1, T1[0,0], T1[1,1], T1[2,2] = np.eye(3), -Sign, +1, Sign
        T2, T2[0,0], T2[1,1], T2[2,2] = np.eye(3),  Sign, -1, Sign
        T3, T3[0,0], T3[1,1], T3[2,2] = np.eye(3),  Sign, +1, Sign
        

        if self.valueRightFootModelCheck == '1':
            RightHindfootAnglesDeg = T1.dot(RightHindfootAnglesRad) * 180 / np.pi 
            RightForefootAnglesDeg = T1.dot(RightForefootAnglesRad) * 180 / np.pi 
            RightHalluxAnglesDeg   = T1.dot(RightHalluxAnglesRad) * 180 / np.pi 
            RightToesAnglesDeg = T2.dot(RightToesAnglesRad) * 180 / np.pi
        #print(RightTrunkAnglesDeg)
        #print(RightPelvisAnglesDeg)
        #print(RightThighAnglesDeg)
        #print(RightShankAnglesDeg)
        #print(RightFootAnglesDeg)
        #print(RightHipAnglesDeg)
        #print(RightKneeAnglesDeg)
        #print(RightAnkleAnglesDeg)
        
        
        
        
# =============================================================================
#       Fille in Posture Display Measurements
# =============================================================================
        # Left

        if self.valueLeftFootModelCheck == '1':
            if round(LeftHindfootAnglesDeg[0], 0) > 0:
                LeftHindfootInvEversion.insert(0, str(int(abs(round(LeftHindfootAnglesDeg[0], 0)))) +  " Val")
            if round(LeftHindfootAnglesDeg[0], 0) < 0:
                LeftHindfootInvEversion.insert(0, str(int(abs(round(LeftHindfootAnglesDeg[0], 0)))) +  " Var")
            if round(LeftHindfootAnglesDeg[0], 0) == 0:
                LeftHindfootInvEversion.insert(0, str(int(abs(round(LeftHindfootAnglesDeg[0], 0)))) +  "")
            if round(LeftHindfootAnglesDeg[1], 0) > 0:
                LeftHindfootPitch.insert(0, str(int(abs(round(LeftHindfootAnglesDeg[1], 0)))) +  " Down")
            if round(LeftHindfootAnglesDeg[1], 0) < 0:
                LeftHindfootPitch.insert(0, str(int(abs(round(LeftHindfootAnglesDeg[1], 0)))) +  " Up")
            if round(LeftHindfootAnglesDeg[1], 0) == 0:
                LeftHindfootPitch.insert(0, str(int(abs(round(LeftHindfootAnglesDeg[1], 0)))) +  "")
            if round(LeftHindfootAnglesDeg[2], 0) > 0:
                LeftHindfootProgression.insert(0, str(int(abs(round(LeftHindfootAnglesDeg[2], 0)))) +  " Int")
            if round(LeftHindfootAnglesDeg[2], 0) < 0:
                LeftHindfootProgression.insert(0, str(int(abs(round(LeftHindfootAnglesDeg[2], 0)))) +  " Ext")
            if round(LeftHindfootAnglesDeg[2], 0) == 0:
                LeftHindfootProgression.insert(0, str(int(abs(round(LeftHindfootAnglesDeg[2], 0)))) +  "")
            
#            if round(LeftForefootAnglesDeg[0], 0) > 0:
#                LeftForefootInvEversion.insert(0, str(int(abs(round(LeftForefootAnglesDeg[0], 0)))) +  " Inv")
#            if round(LeftForefootAnglesDeg[0], 0) < 0:
#                LeftForefootInvEversion.insert(0, str(int(abs(round(LeftForefootAnglesDeg[0], 0)))) +  " Ev")
#            if round(LeftForefootAnglesDeg[0], 0) == 0:
#                LeftForefootInvEversion.insert(0, str(int(abs(round(LeftForefootAnglesDeg[0], 0)))) +  "")
            if round(LeftForefootAnglesDeg[1], 0) > 0:
                LeftForefootPitch.insert(0, str(int(abs(round(LeftForefootAnglesDeg[1], 0)))) +  " Down")
            if round(LeftForefootAnglesDeg[1], 0) < 0:
                LeftForefootPitch.insert(0, str(int(abs(round(LeftForefootAnglesDeg[1], 0)))) +  " Up")
            if round(LeftForefootAnglesDeg[1], 0) == 0:
                LeftForefootPitch.insert(0, str(int(abs(round(LeftForefootAnglesDeg[1], 0)))) +  "")
            if round(LeftForefootAnglesDeg[2], 0) > 0:
                LeftForefootProgression.insert(0, str(int(abs(round(LeftForefootAnglesDeg[2], 0)))) +  " Int")
            if round(LeftForefootAnglesDeg[2], 0) < 0:
                LeftForefootProgression.insert(0, str(int(abs(round(LeftForefootAnglesDeg[2], 0)))) +  " Ext")
            if round(LeftForefootAnglesDeg[2], 0) == 0:
                LeftForefootProgression.insert(0, str(int(abs(round(LeftForefootAnglesDeg[2], 0)))) +  "")
            
            if round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0) > 0:
                LeftMidfootAbAdduction.insert(0, str(int(abs(round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0)))) +  " Add")
            if round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0) < 0:
                LeftMidfootAbAdduction.insert(0, str(int(abs(round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0)))) +  " Abd")
            if round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0) == 0:
                LeftMidfootAbAdduction.insert(0, str(int(abs(round(LeftForefootAnglesDeg[2] - LeftHindfootAnglesDeg[2], 0)))) +  "")
                
            if round(LeftHalluxAnglesDeg[2], 0) > 0:
                LeftHalluxProgression.insert(0, str(int(abs(round(LeftToesAnglesDeg[2], 0)))) +  " Var")
            if round(LeftHalluxAnglesDeg[2], 0) < 0:
                LeftHalluxProgression.insert(0, str(int(abs(round(LeftToesAnglesDeg[2], 0)))) +  " Val")
            if round(LeftHalluxAnglesDeg[2], 0) == 0:
                LeftHalluxProgression.insert(0, str(int(abs(round(LeftToesAnglesDeg[2], 0)))) +  "")
            
        #Right
        if self.valueRightFootModelCheck == '1':
            if round(RightHindfootAnglesDeg[0], 0) > 0:
                RightHindfootInvEversion.insert(0, str(int(abs(round(RightHindfootAnglesDeg[0], 0)))) +  " Val")
            if round(RightHindfootAnglesDeg[0], 0) < 0:
                RightHindfootInvEversion.insert(0, str(int(abs(round(RightHindfootAnglesDeg[0], 0)))) +  " Var")
            if round(RightHindfootAnglesDeg[0], 0) == 0:
                RightHindfootInvEversion.insert(0, str(int(abs(round(RightHindfootAnglesDeg[0], 0)))) +  "")
            if round(RightHindfootAnglesDeg[1], 0) > 0:
                RightHindfootPitch.insert(0, str(int(abs(round(RightHindfootAnglesDeg[1], 0)))) +  " Down")
            if round(RightHindfootAnglesDeg[1], 0) < 0:
                RightHindfootPitch.insert(0, str(int(abs(round(RightHindfootAnglesDeg[1], 0)))) +  " Up")
            if round(RightHindfootAnglesDeg[1], 0) == 0:
                RightHindfootPitch.insert(0, str(int(abs(round(RightHindfootAnglesDeg[1], 0)))) +  "")
            if round(RightHindfootAnglesDeg[2], 0) > 0:
                RightHindfootProgression.insert(0, str(int(abs(round(RightHindfootAnglesDeg[2], 0)))) +  " Int")
            if round(RightHindfootAnglesDeg[2], 0) < 0:
                RightHindfootProgression.insert(0, str(int(abs(round(RightHindfootAnglesDeg[2], 0)))) +  " Ext")
            if round(RightHindfootAnglesDeg[2], 0) == 0:
                RightHindfootProgression.insert(0, str(int(abs(round(RightHindfootAnglesDeg[2], 0)))) +  "")
            
#            if round(RightForefootAnglesDeg[0], 0) > 0:
#                RightForefootInvEversion.insert(0, str(int(abs(round(RightForefootAnglesDeg[0], 0)))) +  " Inv")
#            if round(RightForefootAnglesDeg[0], 0) < 0:
#                RightForefootInvEversion.insert(0, str(int(abs(round(RightForefootAnglesDeg[0], 0)))) +  " Ev")
#            if round(RightForefootAnglesDeg[0], 0) == 0:
#                RightForefootInvEversion.insert(0, str(int(abs(round(RightForefootAnglesDeg[0], 0)))) +  "")
            if round(RightForefootAnglesDeg[1], 0) > 0:
                RightForefootPitch.insert(0, str(int(abs(round(RightForefootAnglesDeg[1], 0)))) +  " Down")
            if round(RightForefootAnglesDeg[1], 0) < 0:
                RightForefootPitch.insert(0, str(int(abs(round(RightForefootAnglesDeg[1], 0)))) +  " Up")
            if round(RightForefootAnglesDeg[1], 0) == 0:
                RightForefootPitch.insert(0, str(int(abs(round(RightForefootAnglesDeg[1], 0)))) +  "")
            if round(RightForefootAnglesDeg[2], 0) > 0:
                RightForefootProgression.insert(0, str(int(abs(round(RightForefootAnglesDeg[2], 0)))) +  " Int")
            if round(RightForefootAnglesDeg[2], 0) < 0:
                RightForefootProgression.insert(0, str(int(abs(round(RightForefootAnglesDeg[2], 0)))) +  " Ext")
            if round(RightForefootAnglesDeg[2], 0) == 0:
                RightForefootProgression.insert(0, str(int(abs(round(RightForefootAnglesDeg[2], 0)))) +  "")
            
            if round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0) > 0:
                RightMidfootAbAdduction.insert(0, str(int(abs(round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0)))) +  " Add")
            if round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0) < 0:
                RightMidfootAbAdduction.insert(0, str(int(abs(round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0)))) +  " Abd")
            if round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0) == 0:
                RightMidfootAbAdduction.insert(0, str(int(abs(round(RightForefootAnglesDeg[2] - RightHindfootAnglesDeg[2], 0)))) +  "")
                
            if round(RightHalluxAnglesDeg[2], 0) > 0:
                RightHalluxProgression.insert(0, str(int(abs(round(RightToesAnglesDeg[2], 0)))) +  " Var")
            if round(RightHalluxAnglesDeg[2], 0) < 0:
                RightHalluxProgression.insert(0, str(int(abs(round(RightToesAnglesDeg[2], 0)))) +  " Val")
            if round(RightHalluxAnglesDeg[2], 0) == 0:
                RightHalluxProgression.insert(0, str(int(abs(round(RightToesAnglesDeg[2], 0)))) +  "")
                
# =============================================================================
#       Function to save Transformation matrics in Static_BF_MRN.py file. It gets executed with 'Save Pdf' and 'Save Results' Button.
# =============================================================================
        def saveTransformationMatrices():
            # Read Current File
            SittingFootStaticDataFile = open(SittingFootStaticDataFileName,'r')
            lines=SittingFootStaticDataFile.readlines()
            SittingFootStaticDataFile.close()
            
            # Write Subject Data into Static Anthropometric File
            SittingFootStaticDataFile = open(SittingFootStaticDataFileName,'w+')
            # Overwrite Foot Transformation matrices 
            LeftEHindfootAnatRelTech_Flag = 0
            LeftEForefootAnatRelTech_Flag = 0
            LeftEHalluxAnatRelTech_Flag = 0
            Left23MetatarsalHeadMarkerForefoot_Flag = 0
            LeftFirstMetatarsoPhalangealJointMarkerForefoot_Flag = 0
            RightEHindfootAnatRelTech_Flag = 0
            RightEForefootAnatRelTech_Flag = 0
            RightEHalluxAnatRelTech_Flag = 0
            Right23MetatarsalHeadMarkerForefoot_Flag = 0
            RightFirstMetatarsoPhalangealJointMarkerForefoot_Flag = 0

            # =============================================================================
            #    If Foot segment transformation exist in Static py then overwrite them
            # =============================================================================            
            for line in lines:
                words=line.split()
                if words[0] == 'self.valueLeftEHindfootAnatRelTech':
                    SittingFootStaticDataFile.write('self.valueLeftEHindfootAnatRelTech = np.array([[' + str(LeftEHindfootAnatRelTech[0,0]) + "," + str(LeftEHindfootAnatRelTech[0,1]) + ","  + str(LeftEHindfootAnatRelTech[0,2])  + "],[" +
                                                                      str(LeftEHindfootAnatRelTech[1,0]) + "," + str(LeftEHindfootAnatRelTech[1,1]) + ","  + str(LeftEHindfootAnatRelTech[1,2]) + "],[" +
                                                                      str(LeftEHindfootAnatRelTech[2,0]) + "," + str(LeftEHindfootAnatRelTech[2,1]) + ","  + str(LeftEHindfootAnatRelTech[2,2]) + "]])" + '\n')
                    LeftEHindfootAnatRelTech_Flag = 1
                    continue
                if words[0] == 'self.valueLeftEForefootAnatRelTech':
                    SittingFootStaticDataFile.write('self.valueLeftEForefootAnatRelTech = np.array([[' + str(LeftEForefootAnatRelTech[0,0]) + "," + str(LeftEForefootAnatRelTech[0,1]) + ","  + str(LeftEForefootAnatRelTech[0,2])  + "],[" +
                                                                      str(LeftEForefootAnatRelTech[1,0]) + "," + str(LeftEForefootAnatRelTech[1,1]) + ","  + str(LeftEForefootAnatRelTech[1,2]) + "],[" +
                                                                      str(LeftEForefootAnatRelTech[2,0]) + "," + str(LeftEForefootAnatRelTech[2,1]) + ","  + str(LeftEForefootAnatRelTech[2,2]) + "]])" + '\n')
                    LeftEForefootAnatRelTech_Flag = 1
                    continue                
                if words[0] == 'self.valueLeftEHalluxAnatRelTech':
                    SittingFootStaticDataFile.write('self.valueLeftEHalluxAnatRelTech = np.array([[' + str(LeftEHalluxAnatRelTech[0,0]) + "," + str(LeftEHalluxAnatRelTech[0,1]) + ","  + str(LeftEHalluxAnatRelTech[0,2])  + "],[" +
                                                                      str(LeftEHalluxAnatRelTech[1,0]) + "," + str(LeftEHalluxAnatRelTech[1,1]) + ","  + str(LeftEHalluxAnatRelTech[1,2]) + "],[" +
                                                                      str(LeftEHalluxAnatRelTech[2,0]) + "," + str(LeftEHalluxAnatRelTech[2,1]) + ","  + str(LeftEHalluxAnatRelTech[2,2]) + "]])" + '\n')
                    LeftEHalluxAnatRelTech_Flag = 1
                    continue                        
                if words[0] == 'self.valueLeft23MetatarsalHeadMarkerForefoot':
                    SittingFootStaticDataFile.write('self.valueLeft23MetatarsalHeadMarkerForefoot = np.array([' + str(Left23MetatarsalHeadMarkerForefoot[0]) + "," + str(Left23MetatarsalHeadMarkerForefoot[1]) + "," + str(Left23MetatarsalHeadMarkerForefoot[2]) + "])" +'\n')
                    Left23MetatarsalHeadMarkerForefoot_Flag = 1
                    continue                    
                if words[0] == 'self.valueLeftFirstMetatarsoPhalangealJointMarkerForefoot':
                     SittingFootStaticDataFile.write('self.valueLeftFirstMetatarsoPhalangealJointMarkerForefoot = np.array([' + str(LeftFirstMetatarsoPhalangealJointMarkerForefoot[0]) + "," + str(LeftFirstMetatarsoPhalangealJointMarkerForefoot[1]) + "," + str(LeftFirstMetatarsoPhalangealJointMarkerForefoot[2]) + "])" +'\n')
                     LeftFirstMetatarsoPhalangealJointMarkerForefoot_Flag = 1
                     continue
            
                if words[0] == 'self.valueRightEHindfootAnatRelTech':
                    SittingFootStaticDataFile.write('self.valueRightEHindfootAnatRelTech = np.array([[' + str(RightEHindfootAnatRelTech[0,0]) + "," + str(RightEHindfootAnatRelTech[0,1]) + ","  + str(RightEHindfootAnatRelTech[0,2])  + "],[" +
                                                                      str(RightEHindfootAnatRelTech[1,0]) + "," + str(RightEHindfootAnatRelTech[1,1]) + ","  + str(RightEHindfootAnatRelTech[1,2]) + "],[" +
                                                                      str(RightEHindfootAnatRelTech[2,0]) + "," + str(RightEHindfootAnatRelTech[2,1]) + ","  + str(RightEHindfootAnatRelTech[2,2]) + "]])" + '\n')
                    RightEHindfootAnatRelTech_Flag = 1
                    continue                
                if words[0] == 'self.valueRightEForefootAnatRelTech':
                    SittingFootStaticDataFile.write('self.valueRightEForefootAnatRelTech = np.array([[' + str(RightEForefootAnatRelTech[0,0]) + "," + str(RightEForefootAnatRelTech[0,1]) + ","  + str(RightEForefootAnatRelTech[0,2])  + "],[" +
                                                                      str(RightEForefootAnatRelTech[1,0]) + "," + str(RightEForefootAnatRelTech[1,1]) + ","  + str(RightEForefootAnatRelTech[1,2]) + "],[" +
                                                                      str(RightEForefootAnatRelTech[2,0]) + "," + str(RightEForefootAnatRelTech[2,1]) + ","  + str(RightEForefootAnatRelTech[2,2]) + "]])" + '\n')
                    RightEForefootAnatRelTech_Flag = 1
                    continue                
                if words[0] == 'self.valueRightEHalluxAnatRelTech':
                    SittingFootStaticDataFile.write('self.valueRightEHalluxAnatRelTech = np.array([[' + str(RightEHalluxAnatRelTech[0,0]) + "," + str(RightEHalluxAnatRelTech[0,1]) + ","  + str(RightEHalluxAnatRelTech[0,2])  + "],[" +
                                                                      str(RightEHalluxAnatRelTech[1,0]) + "," + str(RightEHalluxAnatRelTech[1,1]) + ","  + str(RightEHalluxAnatRelTech[1,2]) + "],[" +
                                                                      str(RightEHalluxAnatRelTech[2,0]) + "," + str(RightEHalluxAnatRelTech[2,1]) + ","  + str(RightEHalluxAnatRelTech[2,2]) + "]])" + '\n')
                    RightEHalluxAnatRelTech_Flag = 1
                    continue                       
                if words[0] == 'self.valueRight23MetatarsalHeadMarkerForefoot':
                    SittingFootStaticDataFile.write('self.valueRight23MetatarsalHeadMarkerForefoot = np.array([' + str(Right23MetatarsalHeadMarkerForefoot[0]) + "," + str(Right23MetatarsalHeadMarkerForefoot[1]) + "," + str(Right23MetatarsalHeadMarkerForefoot[2]) + "])" +'\n')
                    Right23MetatarsalHeadMarkerForefoot_Flag = 1
                    continue                    
                if words[0] == 'self.valueRightFirstMetatarsoPhalangealJointMarkerForefoot':
                     SittingFootStaticDataFile.write('self.valueRightFirstMetatarsoPhalangealJointMarkerForefoot = np.array([' + str(RightFirstMetatarsoPhalangealJointMarkerForefoot[0]) + "," + str(RightFirstMetatarsoPhalangealJointMarkerForefoot[1]) + "," + str(RightFirstMetatarsoPhalangealJointMarkerForefoot[2]) + "])" +'\n')
                     RightFirstMetatarsoPhalangealJointMarkerForefoot_Flag = 1
                     continue
                
                
                SittingFootStaticDataFile.write(line)
                
            
            
            # =============================================================================
            #    If Foot segment transformation don't exist in Static py then write them
            # =============================================================================
            
            if LeftEHindfootAnatRelTech_Flag == 0:
                SittingFootStaticDataFile.write('self.valueLeftEHindfootAnatRelTech = np.array([[' + str(LeftEHindfootAnatRelTech[0,0]) + "," + str(LeftEHindfootAnatRelTech[0,1]) + ","  + str(LeftEHindfootAnatRelTech[0,2])  + "],[" +
                                                                  str(LeftEHindfootAnatRelTech[1,0]) + "," + str(LeftEHindfootAnatRelTech[1,1]) + ","  + str(LeftEHindfootAnatRelTech[1,2]) + "],[" +
                                                                  str(LeftEHindfootAnatRelTech[2,0]) + "," + str(LeftEHindfootAnatRelTech[2,1]) + ","  + str(LeftEHindfootAnatRelTech[2,2]) + "]])" + '\n')
            if LeftEForefootAnatRelTech_Flag == 0:
                SittingFootStaticDataFile.write('self.valueLeftEForefootAnatRelTech = np.array([[' + str(LeftEForefootAnatRelTech[0,0]) + "," + str(LeftEForefootAnatRelTech[0,1]) + ","  + str(LeftEForefootAnatRelTech[0,2])  + "],[" +
                                                                  str(LeftEForefootAnatRelTech[1,0]) + "," + str(LeftEForefootAnatRelTech[1,1]) + ","  + str(LeftEForefootAnatRelTech[1,2]) + "],[" +
                                                                  str(LeftEForefootAnatRelTech[2,0]) + "," + str(LeftEForefootAnatRelTech[2,1]) + ","  + str(LeftEForefootAnatRelTech[2,2]) + "]])" + '\n')       
            if LeftEHalluxAnatRelTech_Flag == 0:
                SittingFootStaticDataFile.write('self.valueLeftEHalluxAnatRelTech = np.array([[' + str(LeftEHalluxAnatRelTech[0,0]) + "," + str(LeftEHalluxAnatRelTech[0,1]) + ","  + str(LeftEHalluxAnatRelTech[0,2])  + "],[" +
                                                                  str(LeftEHalluxAnatRelTech[1,0]) + "," + str(LeftEHalluxAnatRelTech[1,1]) + ","  + str(LeftEHalluxAnatRelTech[1,2]) + "],[" +
                                                                  str(LeftEHalluxAnatRelTech[2,0]) + "," + str(LeftEHalluxAnatRelTech[2,1]) + ","  + str(LeftEHalluxAnatRelTech[2,2]) + "]])" + '\n')                       
            if Left23MetatarsalHeadMarkerForefoot_Flag == 0:
                SittingFootStaticDataFile.write('self.valueLeft23MetatarsalHeadMarkerForefoot = np.array([' + str(Left23MetatarsalHeadMarkerForefoot[0]) + "," + str(Left23MetatarsalHeadMarkerForefoot[1]) + "," + str(Left23MetatarsalHeadMarkerForefoot[2]) + "])" +'\n')           
            if LeftFirstMetatarsoPhalangealJointMarkerForefoot_Flag == 0:
                 SittingFootStaticDataFile.write('self.valueLeftFirstMetatarsoPhalangealJointMarkerForefoot = np.array([' + str(LeftFirstMetatarsoPhalangealJointMarkerForefoot[0]) + "," + str(LeftFirstMetatarsoPhalangealJointMarkerForefoot[1]) + "," + str(LeftFirstMetatarsoPhalangealJointMarkerForefoot[2]) + "])" +'\n')
        
            if RightEHindfootAnatRelTech_Flag == 0:
                SittingFootStaticDataFile.write('self.valueRightEHindfootAnatRelTech = np.array([[' + str(RightEHindfootAnatRelTech[0,0]) + "," + str(RightEHindfootAnatRelTech[0,1]) + ","  + str(RightEHindfootAnatRelTech[0,2])  + "],[" +
                                                                  str(RightEHindfootAnatRelTech[1,0]) + "," + str(RightEHindfootAnatRelTech[1,1]) + ","  + str(RightEHindfootAnatRelTech[1,2]) + "],[" +
                                                                  str(RightEHindfootAnatRelTech[2,0]) + "," + str(RightEHindfootAnatRelTech[2,1]) + ","  + str(RightEHindfootAnatRelTech[2,2]) + "]])" + '\n')
            if RightEForefootAnatRelTech_Flag == 0:
                SittingFootStaticDataFile.write('self.valueRightEForefootAnatRelTech = np.array([[' + str(RightEForefootAnatRelTech[0,0]) + "," + str(RightEForefootAnatRelTech[0,1]) + ","  + str(RightEForefootAnatRelTech[0,2])  + "],[" +
                                                                  str(RightEForefootAnatRelTech[1,0]) + "," + str(RightEForefootAnatRelTech[1,1]) + ","  + str(RightEForefootAnatRelTech[1,2]) + "],[" +
                                                                  str(RightEForefootAnatRelTech[2,0]) + "," + str(RightEForefootAnatRelTech[2,1]) + ","  + str(RightEForefootAnatRelTech[2,2]) + "]])" + '\n')       
            if RightEHalluxAnatRelTech_Flag == 0:
                SittingFootStaticDataFile.write('self.valueRightEHalluxAnatRelTech = np.array([[' + str(RightEHalluxAnatRelTech[0,0]) + "," + str(RightEHalluxAnatRelTech[0,1]) + ","  + str(RightEHalluxAnatRelTech[0,2])  + "],[" +
                                                                  str(RightEHalluxAnatRelTech[1,0]) + "," + str(RightEHalluxAnatRelTech[1,1]) + ","  + str(RightEHalluxAnatRelTech[1,2]) + "],[" +
                                                                  str(RightEHalluxAnatRelTech[2,0]) + "," + str(RightEHalluxAnatRelTech[2,1]) + ","  + str(RightEHalluxAnatRelTech[2,2]) + "]])" + '\n')                       
            if Right23MetatarsalHeadMarkerForefoot_Flag == 0:
                SittingFootStaticDataFile.write('self.valueRight23MetatarsalHeadMarkerForefoot = np.array([' + str(Right23MetatarsalHeadMarkerForefoot[0]) + "," + str(Right23MetatarsalHeadMarkerForefoot[1]) + "," + str(Right23MetatarsalHeadMarkerForefoot[2]) + "])" +'\n')           
            if RightFirstMetatarsoPhalangealJointMarkerForefoot_Flag == 0:
                 SittingFootStaticDataFile.write('self.valueRightFirstMetatarsoPhalangealJointMarkerForefoot = np.array([' + str(RightFirstMetatarsoPhalangealJointMarkerForefoot[0]) + "," + str(RightFirstMetatarsoPhalangealJointMarkerForefoot[1]) + "," + str(RightFirstMetatarsoPhalangealJointMarkerForefoot[2]) + "])" +'\n')

            
            #print('FileUpdate- Tmatrix')
            SittingFootStaticDataFile.close()
            

        def savePdf():
            # Collect information to construct Pdf File Name
            SubjectName = fields["Name"]
            FilePath, FileName = fields["Path"],fields["Filename"]
            self.valuePatientNumber = SubjectName
            SystemFileName = FileName + '.x1d'
            self.valueStaticFile = FileName
            self.valueTrialModifier = 'Barefoot'
            #now = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(FilePath,SystemFileName)))
            now =datetime.datetime.now()
            DateOptions = ["01","02","03","04","05","06","07","08","09","10",
                       "11","12","13","14","15","16","17","18","19","20",
                       "21","22","23","24","25","26","27","28","29","30","31"]
            MonthOptions = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            YearOptions = ["1981","1982","1983","1984","1985","1986","1987","1988","1989","1990",
                       "1991","1992","1993","1994","1995","1996","1997","1998","1999","2000",
                       "2001","2002","2003","2004","2005","2006","2007","2008","2009","2010",
                       "2011","2012","2013","2014","2015","2016","2017","2018","2019","2020",
                       "2021","2022","2023","2024","2025","2026","2027","2028","2029","2030"]
            self.valueDataCollectionDate_Day = DateOptions[int(now.day)-1] # File Creation Date
            self.valueDataCollectionDate_Month = MonthOptions[int(now.month)-1] # File Creation Date
            self.valueDataCollectionDate_Year = YearOptions[int(now.year)-1981] # File Creation Date
            #############################################################################################
            
            # Confirm the File Name and Path for Static Results pdf
            FilePath, FileName = fields["Path"],fields["Filename"]
            InitialPath = FilePath
            
            InitialFileName = 'Static ' + TestingCondition + ' Foot ' + self.valuePatientNumber[:7] + ' ' + self.valueDataCollectionDate_Year + self.valueDataCollectionDate_Month + self.valueDataCollectionDate_Day + '.pdf'
            StaticResultsFilename = filedialog.asksaveasfilename(initialdir = InitialPath,initialfile = InitialFileName, title = "Select Static Results File Location",filetypes = (("pdf files","*.pdf"),("all files","*.*")))
            
            #Prepare Results Page pdf
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
            StaticResultsPage.rect(WidthMargin,HeightMargin + DrawRegionHeight,DrawRegionWidth,-30,stroke = 0, fill = 1)
            StaticResultsPage.setFont("Times-Bold", 12)
            StaticResultsPage.setFillGray(0.0)
            StaticResultsPage.drawCentredString(PageWidth/2,PageHeight - HeightMargin - 12,"Shriners Hospital for Children- Greenville, SC")
            StaticResultsPage.drawCentredString(PageWidth/2,PageHeight - HeightMargin - 25,"Motion Analysis Center")
            StaticResultsPage.drawCentredString(PageWidth/2,PageHeight - HeightMargin - 50,"-Static Report-")
            
            # Static Settings
            StaticResultsPage.setFont("Times-Roman", 11)
            VerticalOffsetFromTitle = 70
            LineSpacing = 15
            ColumnSpacing = 120
            StaticResultsPage.drawString(WidthMargin, PageHeight - HeightMargin - VerticalOffsetFromTitle ,"Static File:")
            StaticResultsPage.drawString(WidthMargin + ColumnSpacing, PageHeight - HeightMargin - VerticalOffsetFromTitle , self.valueStaticFile + '.c3d')
                        
            StaticResultsPage.drawString(WidthMargin, PageHeight - HeightMargin -VerticalOffsetFromTitle - 1 * LineSpacing ,"Data Collection Date:")
            StaticResultsPage.drawString(WidthMargin + ColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 1 * LineSpacing , self.valueDataCollectionDate_Day + '-' + self.valueDataCollectionDate_Month + '-' + self.valueDataCollectionDate_Year)
            
            StaticResultsPage.drawString(WidthMargin, PageHeight - HeightMargin -VerticalOffsetFromTitle - 2 * LineSpacing ,"Foot Static File:")
            StaticResultsPage.drawString(WidthMargin + ColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 2 * LineSpacing , FileName + '.c3d')

            
            StaticResultsPage.drawString(WidthMargin, PageHeight - HeightMargin -VerticalOffsetFromTitle - 3 * LineSpacing ,"Foot Model:")
            StaticResultsPage.drawString(WidthMargin + ColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 3 * LineSpacing ,'mSHCG')
            StaticResultsPage.drawString(WidthMargin + 2 * ColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 3 * LineSpacing ,'DataFrameUsed: ' + str(self.valueStaticFrameNumber))
            #StaticResultsPage.drawString(WidthMargin + 3 * ColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 3 * LineSpacing ,'Plantigrade: ' + PlantigradeText)
            
            StaticResultsPage.drawString(WidthMargin, PageHeight - HeightMargin -VerticalOffsetFromTitle - 4 * LineSpacing ,"TestingCondition:") 
            StaticResultsPage.drawString(WidthMargin + ColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 4 * LineSpacing , self.valueTrialModifier)
            #StaticResultsPage.drawString(WidthMargin + 2 * ColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 4 * LineSpacing , "AssistiveDevice: " + self.valueAssistiveDevice)
            

            # Add Foot Static Posture if Foot Model was used
            # Page Title
            StaticResultsPage.setFillColor(reportlabColors.lightgrey)
            StaticResultsPage.rect(WidthMargin,HeightMargin + DrawRegionHeight,DrawRegionWidth,-30,stroke = 0, fill = 1)
            StaticResultsPage.setFont("Times-Bold", 12)
            StaticResultsPage.setFillGray(0.0)
            StaticResultsPage.drawCentredString(PageWidth/2,PageHeight - HeightMargin - 12,"Shriners Hospital for Children- Greenville, SC")
            StaticResultsPage.drawCentredString(PageWidth/2,PageHeight - HeightMargin - 25,"Motion Analysis Center")
            StaticResultsPage.drawCentredString(PageWidth/2,PageHeight - HeightMargin - 50,"-Static Report-")
            
            # Static Posture- Labels
            StaticResultsPage.setFont("Times-Bold", 12)
            StaticResultsPage.setStrokeGray(0.75)
            VerticalOffsetFromTitle = 160
            LabelColumnSpacing = 150
            LeftColumnSpacing = 200
            RightColumnSpacing = 300
            StaticResultsPage.drawString(WidthMargin, PageHeight - HeightMargin -VerticalOffsetFromTitle, "Foot Posture (degrees)")
            StaticResultsPage.drawString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle, "Left")
            StaticResultsPage.drawString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle, "Right")
            StaticResultsPage.rect(WidthMargin -5 , PageHeight - HeightMargin -VerticalOffsetFromTitle + 15, DrawRegionWidth + 5, -(8*LineSpacing + 5),stroke = 1, fill = 0)
            
            StaticResultsPage.setFont("Times-Roman", 11)
            StaticResultsPage.drawRightString(WidthMargin + LabelColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 1 * LineSpacing ,"Hindfoot Pitch")
            StaticResultsPage.drawRightString(WidthMargin + LabelColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 2 * LineSpacing ,"Hindfoot Progression")
            StaticResultsPage.drawRightString(WidthMargin + LabelColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 3 * LineSpacing ,"Hindfoot Varus/Valgus")
            StaticResultsPage.drawRightString(WidthMargin + LabelColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 4 * LineSpacing ,"Forefoot Pitch")
            StaticResultsPage.drawRightString(WidthMargin + LabelColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 5 * LineSpacing ,"Forefoot Progression")
            #StaticResultsPage.drawRightString(WidthMargin + LabelColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 6 * LineSpacing ,"Forefoot Inv/Eversion")
            StaticResultsPage.drawRightString(WidthMargin + LabelColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 7 * LineSpacing ,"Hallux Progression")

        
            # Static Posture- Left Values
            if len(str.split(LeftHindfootPitch.get())) > 0:
                StaticResultsPage.drawRightString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 1 * LineSpacing ,str.split(LeftHindfootPitch.get())[0])
            if len(str.split(LeftHindfootProgression.get())) > 0:
                StaticResultsPage.drawRightString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 2 * LineSpacing ,str.split(LeftHindfootProgression.get())[0])
            if len(str.split(LeftHindfootInvEversion.get())) > 0:
                StaticResultsPage.drawRightString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 3 * LineSpacing ,str.split(LeftHindfootInvEversion.get())[0])
            if len(str.split(LeftForefootPitch.get())) > 0:
                StaticResultsPage.drawRightString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 4 * LineSpacing ,str.split(LeftForefootPitch.get())[0])
            if len(str.split(LeftForefootProgression.get())) > 0:
                StaticResultsPage.drawRightString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 5 * LineSpacing ,str.split(LeftForefootProgression.get())[0])
            #if len(str.split(LeftForefootInvEversion.get())) > 0:
            #    StaticResultsPage.drawRightString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 6 * LineSpacing ,str.split(LeftForefootInvEversion.get())[0])
            if len(str.split(LeftHalluxProgression.get())) > 0:
                StaticResultsPage.drawRightString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 7 * LineSpacing ,str.split(LeftHalluxProgression.get())[0])


            # Static Posture- Left Direction
            if len(str.split(LeftHindfootPitch.get())) > 1:
                StaticResultsPage.drawString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 1 * LineSpacing , '  ' + str.split(LeftHindfootPitch.get())[1])
            if len(str.split(LeftHindfootProgression.get())) > 1:
                StaticResultsPage.drawString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 2 * LineSpacing , '  ' + str.split(LeftHindfootProgression.get())[1])
            if len(str.split(LeftHindfootInvEversion.get())) > 1:
                StaticResultsPage.drawString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 3 * LineSpacing , '  ' + str.split(LeftHindfootInvEversion.get())[1])
            if len(str.split(LeftForefootPitch.get())) > 1:
                StaticResultsPage.drawString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 4 * LineSpacing , '  ' + str.split(LeftForefootPitch.get())[1])
            if len(str.split(LeftForefootProgression.get())) > 1:
                StaticResultsPage.drawString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 5 * LineSpacing , '  ' + str.split(LeftForefootProgression.get())[1])
            #if len(str.split(LeftForefootInvEversion.get())) > 1:
            #    StaticResultsPage.drawString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 6 * LineSpacing , '  ' + str.split(LeftForefootInvEversion.get())[1])
            if len(str.split(LeftHalluxProgression.get())) > 1:
                StaticResultsPage.drawString(WidthMargin + LeftColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 7 * LineSpacing , '  ' + str.split(LeftHalluxProgression.get())[1])
            
            
            # Static Posture- Right Values
            if len(str.split(RightHindfootPitch.get())) > 0:
                StaticResultsPage.drawRightString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 1 * LineSpacing ,str.split(RightHindfootPitch.get())[0])
            if len(str.split(RightHindfootProgression.get())) > 0:
                StaticResultsPage.drawRightString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 2 * LineSpacing ,str.split(RightHindfootProgression.get())[0])
            if len(str.split(RightHindfootInvEversion.get())) > 0:
                StaticResultsPage.drawRightString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 3 * LineSpacing ,str.split(RightHindfootInvEversion.get())[0])
            if len(str.split(RightForefootPitch.get())) > 0:
                StaticResultsPage.drawRightString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 4 * LineSpacing ,str.split(RightForefootPitch.get())[0])
            if len(str.split(RightForefootProgression.get())) > 0:
                StaticResultsPage.drawRightString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 5 * LineSpacing ,str.split(RightForefootProgression.get())[0])
            #if len(str.split(RightForefootInvEversion.get())) > 0:
            #    StaticResultsPage.drawRightString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 6 * LineSpacing ,str.split(RightForefootInvEversion.get())[0])
            if len(str.split(RightHalluxProgression.get())) > 0:
                StaticResultsPage.drawRightString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 7 * LineSpacing ,str.split(RightHalluxProgression.get())[0])


            # Static Posture- Right Direction
            if len(str.split(RightHindfootPitch.get())) > 1:
                StaticResultsPage.drawString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 1 * LineSpacing , '  ' + str.split(RightHindfootPitch.get())[1])
            if len(str.split(RightHindfootProgression.get())) > 1:
                StaticResultsPage.drawString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 2 * LineSpacing , '  ' + str.split(RightHindfootProgression.get())[1])
            if len(str.split(RightHindfootInvEversion.get())) > 1:
                StaticResultsPage.drawString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 3 * LineSpacing , '  ' + str.split(RightHindfootInvEversion.get())[1])
            if len(str.split(RightForefootPitch.get())) > 1:
                StaticResultsPage.drawString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 4 * LineSpacing , '  ' + str.split(RightForefootPitch.get())[1])
            if len(str.split(RightForefootProgression.get())) > 1:
                StaticResultsPage.drawString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 5 * LineSpacing , '  ' + str.split(RightForefootProgression.get())[1])
            #if len(str.split(RightForefootInvEversion.get())) > 1:
            #    StaticResultsPage.drawString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 6 * LineSpacing , '  ' + str.split(RightForefootInvEversion.get())[1])
            if len(str.split(RightHalluxProgression.get())) > 1:
                StaticResultsPage.drawString(WidthMargin + RightColumnSpacing, PageHeight - HeightMargin -VerticalOffsetFromTitle - 7 * LineSpacing , '  ' + str.split(RightHalluxProgression.get())[1])

            
            StaticResultsPage.showPage() # Finishes the Current Page
            
            try:
                StaticResultsPage.save()
                SaveErrorMessagesLabel.place(x=50,y=320, width=650,height=15)
                SaveErrorMessagesLabel['text'] = 'Static Results file saved'
                SaveErrorMessagesLabel['fg']='seagreen'
            except:
                SaveErrorMessagesLabel.place(x=50,y=320, width=650,height=15)
                SaveErrorMessagesLabel['text'] = 'Warning: Results file could not be saved. Close the Pdf file and try again.'
                

                    
#Calls the main Function
app = Static_Main()
#Centers the App on Monitor
ScreenWidth = app.winfo_screenwidth()
ScreenHeight = app.winfo_screenheight()
x=(ScreenWidth/2) - (AppWidth/2)
y=0 #Put the App at Top of Monitor
app.geometry('%dx%d+%d+%d' % (AppWidth, AppHeight, x, y))

app.mainloop()
