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

"""Clinical input loading and legacy serialization, using plain values.

Extracted from the patient page at e6b06a1. Empty optional foot angles and the
reviewed local-unit precedence retain their original meanings.
"""
import os
import datetime
from pathlib import Path
import numpy as np
from numpy import array, nan

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



def populate_clinical_inputs(state):
    if 'DefaultTestingCondition' in state: DefaultTestingCondition = state['DefaultTestingCondition']
    if 'SittingFootStaticDataFileName' in state: SittingFootStaticDataFileName = state['SittingFootStaticDataFileName']
    if 'StaticDataFileName' in state: StaticDataFileName = state['StaticDataFileName']
    if 'TestingCondition' in state: TestingCondition = state['TestingCondition']
    if 'UserPreferencesFileName' in state: UserPreferencesFileName = state['UserPreferencesFileName']
    if 'fields' in state: fields = state['fields']
    if 'self' in state: self = state['self']
    inputs = {
        'FirstName': '',
        'LastName': '',
        'PatientNumber': '',
        'Date': '',
        'Month': '',
        'Year': '',
        'TrialActivity': '',
        'TrialModifier': '',
        'StaticForwardDirection': '',
        'AssistiveDevice': '',
        'StaticFrameNumber': '',
        'StaticFile': '',
        'DataCollectionDate': '',
        'DataCollectionMonth': '',
        'DataCollectionYear': '',
        'BodyMass': '',
        'Height': '',
        'ASISdist': '',
        'LeftLegLength': '',
        'RightLegLength': '',
        'LeftKneeWidth': '',
        'RightKneeWidth': '',
        'LeftAnkleWidth': '',
        'RightAnkleWidth': '',
        'LeftASIStoGTdist': '',
        'RightASIStoGTdist': '',
        'self.LeftFootModelCheck': 0,
        'self.RightFootModelCheck': 0,
        'LeftHindfootVarus': '',
        'RightHindfootVarus': '',
        'LeftCalcanealPitch': '',
        'RightCalcanealPitch': '',
        'LeftHindfootProgression': '',
        'RightHindfootProgression': '',
        'LeftFirstMetatarsalPitch': '',
        'RightFirstMetatarsalPitch': '',
        'self.LeftPlantigradeCheck': 1,
        'self.RightPlantigradeCheck': 1,
        'self.SubjectShodCheck': 0,
        'LeftSoleThickness': '',
        'RightSoleThickness': '',
        'self.KneeAlignmentCheck': 1,
        'self.PelvicFixCheck': 0,
    }
    dob = fields.get('DOB', '1990-01-01').split('-')
    DateOptions = [f'{i:02d}' for i in range(1, 32)]
    inputs['Date'] = str(dob[2] if len(dob) > 2 else DateOptions[0])
    MonthOptions = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    inputs['Month'] = str(MonthOptions[int(dob[1]) - 1] if len(dob) > 1 else MonthOptions[0])
    YearOptions = [str(y) for y in range(1981, 2031)]
    inputs['Year'] = str(dob[0] if len(dob) > 0 else YearOptions[0])
    TrialActivityOptions = ['Static', 'Walking - Fast', 'Walking - Heel-Toe', 'Running', 'Sprinting', 'Stair Ascent', 'Stair Descent', 'Sit-To-Stand', 'Other']
    inputs['TrialActivity'] = str(TrialActivityOptions[0])
    TrialModifierOptions = ['Barefoot', 'B AFO-PLS', 'L AFO-PLS', 'R AFO-PLS', 'B AFO-Solid', 'L AFO-Solid', 'R AFO-Solid', 'B AFO-FR', 'L AFO-FR', 'R AFO-FR', 'B AFO-Artic', 'L AFO-Artic', 'R AFO-Artic', 'L LIFT', 'R LIFT', 'B SMO', 'L SMO', 'R SMO', 'B UCBL', 'L UCBL', 'R UCBL', 'KAFO', 'HKAFO', 'RGO', 'Parawalker', 'Shoes Only', 'Other']
    inputs['TrialModifier'] = str(TrialModifierOptions[0])
    StaticForwardDirectionOptions = ['+X', '-X', '+Y', '-Y']
    if os.path.exists(StaticDataFileName):
        exec(open(StaticDataFileName).read())
    else:
        exec(open(UserPreferencesFileName).read())
    if not hasattr(self, 'StaticForwardDirection'):
        self.StaticForwardDirection = StaticForwardDirectionOptions[0]
    inputs['StaticForwardDirection'] = str(self.StaticForwardDirection)
    AssistiveDeviceOptions = ['None', 'Walker', 'Walker - Wheeled', 'Walker - Pickup', 'Crutches', 'Crutches - Axillary', 'Crutches - Loftstrand', 'Cane', 'Bobath Poles', 'Hand-Held', 'Other']
    inputs['AssistiveDevice'] = str(AssistiveDeviceOptions[0])
    now = datetime.datetime.now()
    inputs['DataCollectionDate'] = str(DateOptions[int(now.day) - 1])
    inputs['DataCollectionMonth'] = str(MonthOptions[int(now.month) - 1])
    DataCollectionYearOptions = [str(y) for y in range(1991, 2031)]
    inputs['DataCollectionYear'] = str(YearOptions[int(now.year) - 1981])
    SubjectName = fields['Name']
    ID = fields.get('ID', '')
    FilePath, FileName = (fields['Path'], fields['Filename'])
    StartFrame, EndFrame = (fields['First Frame'], fields['Last Frame'])
    if os.path.exists(StaticDataFileName):
        exec(open(StaticDataFileName).read())
        inputs['TrialActivity'] = str(getattr(self, 'valueTrialActivity', TrialActivityOptions[0]))
        inputs['TrialModifier'] = str(getattr(self, 'valueTrialModifier', TrialModifierOptions[0]))
        inputs['AssistiveDevice'] = str(getattr(self, 'valueAssistiveDevice', AssistiveDeviceOptions[0]))
        inputs['self.LeftFootModelCheck'] = int(getattr(self, 'valueLeftFootModelCheck', 0))
        inputs['self.RightFootModelCheck'] = int(getattr(self, 'valueRightFootModelCheck', 0))
        if hasattr(self, 'valueLeftHindfootVarus'):
            inputs['LeftHindfootVarus'] = str(self.valueLeftHindfootVarus) + inputs['LeftHindfootVarus']
        if hasattr(self, 'valueRightHindfootVarus'):
            inputs['RightHindfootVarus'] = str(self.valueRightHindfootVarus) + inputs['RightHindfootVarus']
        if hasattr(self, 'valueLeftHindfootProgression'):
            inputs['LeftHindfootProgression'] = str(self.valueLeftHindfootProgression) + inputs['LeftHindfootProgression']
        if hasattr(self, 'valueRightHindfootProgression'):
            inputs['RightHindfootProgression'] = str(self.valueRightHindfootProgression) + inputs['RightHindfootProgression']
        if hasattr(self, 'valueLeftFirstMetatarsalPitch'):
            inputs['LeftFirstMetatarsalPitch'] = str(self.valueLeftFirstMetatarsalPitch) + inputs['LeftFirstMetatarsalPitch']
        if hasattr(self, 'valueRightFirstMetatarsalPitch'):
            inputs['RightFirstMetatarsalPitch'] = str(self.valueRightFirstMetatarsalPitch) + inputs['RightFirstMetatarsalPitch']
        if hasattr(self, 'valueLeftCalcanealPitch'):
            inputs['LeftCalcanealPitch'] = str(self.valueLeftCalcanealPitch) + inputs['LeftCalcanealPitch']
        if hasattr(self, 'valueRightCalcanealPitch'):
            inputs['RightCalcanealPitch'] = str(self.valueRightCalcanealPitch) + inputs['RightCalcanealPitch']
        inputs['self.LeftPlantigradeCheck'] = int(getattr(self, 'valueLeftPlantigradeCheck', 1))
        inputs['self.RightPlantigradeCheck'] = int(getattr(self, 'valueRightPlantigradeCheck', 1))
        if getattr(self, 'valueSujectShodCheck', '0') == '1':
            inputs['self.SubjectShodCheck'] = int(self.valueSujectShodCheck)
            inputs['LeftSoleThickness'] = str(getattr(self, 'valueLeftSoleThickness', '0')) + inputs['LeftSoleThickness']
            inputs['RightSoleThickness'] = str(getattr(self, 'valueRightSoleThickness', '0')) + inputs['RightSoleThickness']
        inputs['self.PelvicFixCheck'] = int(getattr(self, 'valuePelvicFixCheck', 0))
        try:
            inputs['self.KneeAlignmentCheck'] = int(self.valueKneeAlignmentCheck)
        except:
            inputs['self.KneeAlignmentCheck'] = int('0')
        try:
            inputs['StaticFrameNumber'] = str(self.valueStaticFrameNumber) + inputs['StaticFrameNumber']
        except:
            inputs['StaticFrameNumber'] = str(StartFrame + 20) + inputs['StaticFrameNumber']
    else:
        inputs['StaticFrameNumber'] = str(StartFrame + 20) + inputs['StaticFrameNumber']
        if 'LeftVarValAngle' in fields and fields['LeftVarValAngle'] is not None:
            inputs['LeftHindfootVarus'] = str(int(round(fields['LeftVarValAngle'], 0))) + inputs['LeftHindfootVarus']
            inputs['self.LeftFootModelCheck'] = int('1')
        if 'RightVarValAngle' in fields and fields['RightVarValAngle'] is not None:
            inputs['RightHindfootVarus'] = str(int(round(fields['RightVarValAngle'], 0))) + inputs['RightHindfootVarus']
            inputs['self.RightFootModelCheck'] = int('1')
        if 'Left1stRayPitch' in fields and fields['Left1stRayPitch'] is not None:
            inputs['LeftFirstMetatarsalPitch'] = str(int(fields['Left1stRayPitch'])) + inputs['LeftFirstMetatarsalPitch']
        if 'Right1stRayPitch' in fields and fields['Right1stRayPitch'] is not None:
            inputs['RightFirstMetatarsalPitch'] = str(int(fields['Right1stRayPitch'])) + inputs['RightFirstMetatarsalPitch']
        if 'LeftCalcanealPitch' in fields and fields['LeftCalcanealPitch'] is not None:
            inputs['LeftCalcanealPitch'] = str(int(fields['LeftCalcanealPitch'])) + inputs['LeftCalcanealPitch']
        if 'RightCalcanealPitch' in fields and fields['RightCalcanealPitch'] is not None:
            inputs['RightCalcanealPitch'] = str(int(fields['RightCalcanealPitch'])) + inputs['RightCalcanealPitch']
        if os.path.exists(SittingFootStaticDataFileName):
            exec(open(SittingFootStaticDataFileName).read())
            inputs['LeftCalcanealPitch'] = ''
            inputs['RightCalcanealPitch'] = ''
            inputs['LeftCalcanealPitch'] = str(self.valueLeftCalcanealPitch) + inputs['LeftCalcanealPitch']
            inputs['RightCalcanealPitch'] = str(self.valueRightCalcanealPitch) + inputs['RightCalcanealPitch']
            inputs['LeftHindfootVarus'] = ''
            inputs['RightHindfootVarus'] = ''
            inputs['LeftHindfootVarus'] = str(self.valueLeftHindfootVarus) + inputs['LeftHindfootVarus']
            inputs['RightHindfootVarus'] = str(self.valueRightHindfootVarus) + inputs['RightHindfootVarus']
            inputs['LeftHindfootProgression'] = ''
            inputs['RightHindfootProgression'] = ''
            try:
                inputs['LeftHindfootProgression'] = str(self.valueLeftHindfootProgression) + inputs['LeftHindfootProgression']
            except:
                pass
            try:
                inputs['RightHindfootProgression'] = str(self.valueRightHindfootProgression) + inputs['RightHindfootProgression']
            except:
                pass
    inputs['StaticFile'] = str(FileName) + inputs['StaticFile']
    local_saved = True and getattr(self, 'valueMeasurementUnits', '') == 'm'
    if local_saved and hasattr(self, 'valuePatientNumber'):
        inputs['PatientNumber'] = str(self.valuePatientNumber) + inputs['PatientNumber']
    elif ID:
        inputs['PatientNumber'] = str(ID) + inputs['PatientNumber']
    elif hasattr(self, 'valuePatientNumber') and self.valuePatientNumber:
        inputs['PatientNumber'] = str(self.valuePatientNumber) + inputs['PatientNumber']
    else:
        inputs['PatientNumber'] = str(SubjectName) + inputs['PatientNumber']
    if hasattr(self, 'valueFirstName') and (self.valueFirstName or local_saved):
        inputs['FirstName'] = str(self.valueFirstName) + inputs['FirstName']
    else:
        inputs['FirstName'] = str(SubjectName) + inputs['FirstName']
    if hasattr(self, 'valueLastName') and self.valueLastName:
        inputs['LastName'] = str(self.valueLastName) + inputs['LastName']
    creation_date = fields.get('Creation date') or fields.get('Creation_date')
    date_captured_set = False
    if creation_date:
        try:
            dt = datetime.datetime.strptime(str(creation_date).strip()[:10], '%Y-%m-%d')
            inputs['DataCollectionDate'] = str(DateOptions[dt.day - 1])
            inputs['DataCollectionMonth'] = str(MonthOptions[dt.month - 1])
            inputs['DataCollectionYear'] = str(str(dt.year))
            date_captured_set = True
        except Exception:
            pass
    if not date_captured_set:
        SystemFileName = FileName + '.c3d'
        try:
            now = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(FilePath, SystemFileName)))
            inputs['DataCollectionDate'] = str(DateOptions[int(now.day) - 1])
            inputs['DataCollectionMonth'] = str(MonthOptions[int(now.month) - 1])
            inputs['DataCollectionYear'] = str(YearOptions[int(now.year) - 1981])
            date_captured_set = True
        except Exception:
            pass
    if not date_captured_set and hasattr(self, 'valueDataCollectionDate_Day'):
        inputs['DataCollectionDate'] = str(self.valueDataCollectionDate_Day)
        inputs['DataCollectionMonth'] = str(self.valueDataCollectionDate_Month)
        inputs['DataCollectionYear'] = str(self.valueDataCollectionDate_Year)
    if local_saved:
        for variable, name in (('Date', 'valueDateOfBirth_Day'), ('Month', 'valueDateOfBirth_Month'), ('Year', 'valueDateOfBirth_Year'), ('DataCollectionDate', 'valueDataCollectionDate_Day'), ('DataCollectionMonth', 'valueDataCollectionDate_Month'), ('DataCollectionYear', 'valueDataCollectionDate_Year')):
            if hasattr(self, name):
                inputs[variable] = str(getattr(self, name))

    def get_qtm_or_persisted(field_key, persisted_attr, is_mass=False):
        if True and getattr(self, 'valueMeasurementUnits', '') == 'm' and hasattr(self, persisted_attr):
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
            if val is not None and str(val).strip() != '':
                try:
                    return round(float(val), 2) if is_mass else persisted_measurement_to_meters(val)
                except (ValueError, TypeError):
                    return val
        return ''
    body_mass_val = get_qtm_or_persisted('Bodymass', 'valueBodyMass', is_mass=True)
    if not body_mass_val:
        body_mass_val = get_qtm_or_persisted('BodyMass', 'valueBodyMass', is_mass=True)
    if body_mass_val != '':
        inputs['BodyMass'] = str(body_mass_val) + inputs['BodyMass']
    for widget, f_key, p_attr in [('Height', 'Height', 'valueHeight'), ('ASISdist', 'InterAsisDistance', 'valueASISdist'), ('LeftLegLength', 'LeftLegLength', 'valueLeftLegLength'), ('RightLegLength', 'RightLegLength', 'valueRightLegLength'), ('LeftKneeWidth', 'LeftKneeWidth', 'valueLeftKneeWidth'), ('RightKneeWidth', 'RightKneeWidth', 'valueRightKneeWidth'), ('LeftAnkleWidth', 'LeftAnkleWidth', 'valueLeftAnkleWidth'), ('RightAnkleWidth', 'RightAnkleWidth', 'valueRightAnkleWidth'), ('LeftASIStoGTdist', 'LeftAsisTrocanterDistance', 'valueLeftASIStoGTdist'), ('RightASIStoGTdist', 'RightAsisTrocanterDistance', 'valueRightASIStoGTdist')]:
        val = get_qtm_or_persisted(f_key, p_attr)
        if val != '':
            inputs[widget] = str(val) + inputs[widget]
    if TestingCondition != DefaultTestingCondition:
        _default_calib = os.path.join(FilePath, 'Calibration', 'Static_' + DefaultTestingCondition + '_' + SubjectName + '.py')
        if os.path.exists(_default_calib):
            DefaultStaticDataFileName = _default_calib
        else:
            DefaultStaticDataFileName = FilePath + 'Static_' + DefaultTestingCondition + '_' + SubjectName + '.py'
        if os.path.exists(DefaultStaticDataFileName):
            exec(open(DefaultStaticDataFileName).read())
            inputs['FirstName'] = ''
            inputs['LastName'] = ''
            inputs['PatientNumber'] = ''
            inputs['BodyMass'] = ''
            inputs['Height'] = ''
            inputs['ASISdist'] = ''
            inputs['LeftLegLength'] = ''
            inputs['RightLegLength'] = ''
            inputs['FirstName'] = str(self.valueFirstName) + inputs['FirstName']
            inputs['LastName'] = str(self.valueLastName) + inputs['LastName']
            inputs['PatientNumber'] = str(self.valuePatientNumber) + inputs['PatientNumber']
            inputs['DataCollectionDate'] = str(self.valueDataCollectionDate_Day)
            inputs['DataCollectionMonth'] = str(self.valueDataCollectionDate_Month)
            inputs['DataCollectionYear'] = str(self.valueDataCollectionDate_Year)
            inputs['BodyMass'] = str(self.valueBodyMass) + inputs['BodyMass']
            inputs['Height'] = str(persisted_measurement_to_meters(self.valueHeight)) + inputs['Height']
            inputs['ASISdist'] = str(persisted_measurement_to_meters(self.valueASISdist)) + inputs['ASISdist']
            inputs['LeftLegLength'] = str(persisted_measurement_to_meters(self.valueLeftLegLength)) + inputs['LeftLegLength']
            inputs['RightLegLength'] = str(persisted_measurement_to_meters(self.valueRightLegLength)) + inputs['RightLegLength']
    return inputs


def save_clinical_inputs(state):
    if 'StaticDataFileName' in state: StaticDataFileName = state['StaticDataFileName']
    if 'SubjectName' in state: SubjectName = state['SubjectName']
    if 'TestingCondition' in state: TestingCondition = state['TestingCondition']
    if 'UserPreferencesFileName' in state: UserPreferencesFileName = state['UserPreferencesFileName']
    if 'inputs' in state: inputs = state['inputs']
    if 'local_saved' in state: local_saved = state['local_saved']
    if 'self' in state: self = state['self']
    if os.path.exists(StaticDataFileName):
        StaticDataFile = open(StaticDataFileName, 'r')
        lines = StaticDataFile.readlines()
        StaticDataFile.close()
        StaticDataFile = open(StaticDataFileName, 'w+')
        UserPreferencesBlockEnds = 0
        for line in lines:
            words = line.split()
            if len(words) == 0:
                StaticDataFile.write(line)
                continue
            if words[0] == 'self.valueFirstName':
                UserPreferencesBlockEnds = 1
            if UserPreferencesBlockEnds == 0:
                if words[0] == 'self.StaticForwardDirection':
                    StaticDataFile.write('self.StaticForwardDirection = ' + "'" + inputs['StaticForwardDirection'] + "'\n")
                else:
                    StaticDataFile.write(line)
        write_setting(StaticDataFile, 'valueFirstName', inputs['FirstName'])
        write_setting(StaticDataFile, 'valueLastName', inputs['LastName'])
        write_setting(StaticDataFile, 'valuePatientNumber', inputs['PatientNumber'])
        if hasattr(self, 'valueSex'):
            write_setting(StaticDataFile, 'valueSex', self.valueSex)
        StaticDataFile.write('self.valueDateOfBirth_Day = ' + "'" + inputs['Date'] + "'" + '\n')
        StaticDataFile.write('self.valueDateOfBirth_Month = ' + "'" + inputs['Month'] + "'" + '\n')
        StaticDataFile.write('self.valueDateOfBirth_Year = ' + "'" + inputs['Year'] + "'" + '\n')
        StaticDataFile.write('self.valueTrialActivity = ' + "'" + inputs['TrialActivity'] + "'" + '\n')
        StaticDataFile.write('self.valueTrialModifier = ' + "'" + inputs['TrialModifier'] + "'" + '\n')
        StaticDataFile.write('self.valueAssistiveDevice = ' + "'" + inputs['AssistiveDevice'] + "'" + '\n')
        StaticDataFile.write('self.valueStaticFile = ' + "'" + inputs['StaticFile'] + "'" + '\n')
        StaticDataFile.write('self.valueAnthropometricFile = ' + "'" + 'Static_' + TestingCondition + '_' + SubjectName + "'" + '\n')
        StaticDataFile.write('self.valueDataCollectionDate_Day = ' + "'" + inputs['DataCollectionDate'] + "'" + '\n')
        StaticDataFile.write('self.valueDataCollectionDate_Month = ' + "'" + inputs['DataCollectionMonth'] + "'" + '\n')
        StaticDataFile.write('self.valueDataCollectionDate_Year = ' + "'" + inputs['DataCollectionYear'] + "'" + '\n')
        write_setting(StaticDataFile, 'valueBodyMass', inputs['BodyMass'] if local_saved else float(inputs['BodyMass']))
        if getattr(self, 'valueMeasurementUnits', '') == 'm':
            write_setting(StaticDataFile, 'valueMeasurementUnits', 'm')
        write_setting(StaticDataFile, 'valueHeight', inputs['Height'])
        write_setting(StaticDataFile, 'valueASISdist', inputs['ASISdist'])
        write_setting(StaticDataFile, 'valueLeftLegLength', inputs['LeftLegLength'])
        write_setting(StaticDataFile, 'valueRightLegLength', inputs['RightLegLength'])
        write_setting(StaticDataFile, 'valueLeftKneeWidth', inputs['LeftKneeWidth'])
        write_setting(StaticDataFile, 'valueRightKneeWidth', inputs['RightKneeWidth'])
        write_setting(StaticDataFile, 'valueLeftAnkleWidth', inputs['LeftAnkleWidth'])
        write_setting(StaticDataFile, 'valueRightAnkleWidth', inputs['RightAnkleWidth'])
        write_setting(StaticDataFile, 'valueLeftASIStoGTdist', inputs['LeftASIStoGTdist'])
        write_setting(StaticDataFile, 'valueRightASIStoGTdist', inputs['RightASIStoGTdist'])
        StaticDataFile.write('self.valueLeftFootModelCheck = ' + "'" + str(inputs['self.LeftFootModelCheck']) + "'" + '\n')
        StaticDataFile.write('self.valueRightFootModelCheck = ' + "'" + str(inputs['self.RightFootModelCheck']) + "'" + '\n')
        StaticDataFile.write('self.valueLeftHindfootVarus = ' + "'" + inputs['LeftHindfootVarus'] + "'" + '\n')
        StaticDataFile.write('self.valueLeftCalcanealPitch = ' + "'" + inputs['LeftCalcanealPitch'] + "'" + '\n')
        StaticDataFile.write('self.valueLeftHindfootProgression = ' + "'" + inputs['LeftHindfootProgression'] + "'" + '\n')
        StaticDataFile.write('self.valueLeftFirstMetatarsalPitch = ' + "'" + inputs['LeftFirstMetatarsalPitch'] + "'" + '\n')
        StaticDataFile.write('self.valueRightHindfootVarus = ' + "'" + inputs['RightHindfootVarus'] + "'" + '\n')
        StaticDataFile.write('self.valueRightCalcanealPitch = ' + "'" + inputs['RightCalcanealPitch'] + "'" + '\n')
        StaticDataFile.write('self.valueRightHindfootProgression = ' + "'" + inputs['RightHindfootProgression'] + "'" + '\n')
        StaticDataFile.write('self.valueRightFirstMetatarsalPitch = ' + "'" + inputs['RightFirstMetatarsalPitch'] + "'" + '\n')
        StaticDataFile.write('self.valueLeftPlantigradeCheck = ' + "'" + str(inputs['self.LeftPlantigradeCheck']) + "'" + '\n')
        StaticDataFile.write('self.valueRightPlantigradeCheck = ' + "'" + str(inputs['self.RightPlantigradeCheck']) + "'" + '\n')
        StaticDataFile.write('self.valueSujectShodCheck = ' + "'" + str(inputs['self.SubjectShodCheck']) + "'" + '\n')
        if str(inputs['self.SubjectShodCheck']) == '1':
            write_setting(StaticDataFile, 'valueLeftSoleThickness', inputs['LeftSoleThickness'])
            write_setting(StaticDataFile, 'valueRightSoleThickness', inputs['RightSoleThickness'])
        else:
            write_setting(StaticDataFile, 'valueLeftSoleThickness', '0')
            write_setting(StaticDataFile, 'valueRightSoleThickness', '0')
        StaticDataFile.write('self.valuePelvicFixCheck = ' + "'" + str(inputs['self.PelvicFixCheck']) + "'" + '\n')
        StaticDataFile.write('self.valueKneeAlignmentCheck = ' + "'" + str(inputs['self.KneeAlignmentCheck']) + "'" + '\n')
        StaticDataFile.write('self.valueStaticFrameNumber = ' + "'" + str(inputs['StaticFrameNumber']) + "'" + '\n')
        PatientInformationBlockEnds = 0
        for line in lines:
            words = line.split()
            if len(words) >= 2:
                if words[0] == '#' and words[1] == 'Pelfix':
                    PatientInformationBlockEnds = 1
                elif words[0] == '#' and words[1] == 'Transformation':
                    PatientInformationBlockEnds = 1
            if PatientInformationBlockEnds == 1:
                StaticDataFile.write(line)
        StaticDataFile.close()
    else:
        StaticDataFile = open(StaticDataFileName, 'w+')
        UserPreferencesFile = open(UserPreferencesFileName, 'r')
        lines = UserPreferencesFile.readlines()
        UserPreferencesFile.close()
        for line in lines:
            words = line.split()
            if len(words) == 0:
                StaticDataFile.write(line)
                continue
            if words[0] == 'self.StaticForwardDirection':
                StaticDataFile.write('self.StaticForwardDirection = ' + "'" + inputs['StaticForwardDirection'] + "'\n")
            else:
                StaticDataFile.write(line)
        write_setting(StaticDataFile, 'valueFirstName', inputs['FirstName'])
        write_setting(StaticDataFile, 'valueLastName', inputs['LastName'])
        write_setting(StaticDataFile, 'valuePatientNumber', inputs['PatientNumber'])
        if hasattr(self, 'valueSex'):
            write_setting(StaticDataFile, 'valueSex', self.valueSex)
        StaticDataFile.write('self.valueDateOfBirth_Day = ' + "'" + inputs['Date'] + "'" + '\n')
        StaticDataFile.write('self.valueDateOfBirth_Month = ' + "'" + inputs['Month'] + "'" + '\n')
        StaticDataFile.write('self.valueDateOfBirth_Year = ' + "'" + inputs['Year'] + "'" + '\n')
        StaticDataFile.write('self.valueTrialActivity = ' + "'" + inputs['TrialActivity'] + "'" + '\n')
        StaticDataFile.write('self.valueTrialModifier = ' + "'" + inputs['TrialModifier'] + "'" + '\n')
        StaticDataFile.write('self.valueAssistiveDevice = ' + "'" + inputs['AssistiveDevice'] + "'" + '\n')
        StaticDataFile.write('self.valueStaticFile = ' + "'" + inputs['StaticFile'] + "'" + '\n')
        StaticDataFile.write('self.valueAnthropometricFile = ' + "'" + 'Static_' + TestingCondition + '_' + SubjectName + "'" + '\n')
        StaticDataFile.write('self.valueDataCollectionDate_Day = ' + "'" + inputs['DataCollectionDate'] + "'" + '\n')
        StaticDataFile.write('self.valueDataCollectionDate_Month = ' + "'" + inputs['DataCollectionMonth'] + "'" + '\n')
        StaticDataFile.write('self.valueDataCollectionDate_Year = ' + "'" + inputs['DataCollectionYear'] + "'" + '\n')
        write_setting(StaticDataFile, 'valueBodyMass', inputs['BodyMass'] if local_saved else float(inputs['BodyMass']))
        if getattr(self, 'valueMeasurementUnits', '') == 'm':
            write_setting(StaticDataFile, 'valueMeasurementUnits', 'm')
        write_setting(StaticDataFile, 'valueHeight', inputs['Height'])
        write_setting(StaticDataFile, 'valueASISdist', inputs['ASISdist'])
        write_setting(StaticDataFile, 'valueLeftLegLength', inputs['LeftLegLength'])
        write_setting(StaticDataFile, 'valueRightLegLength', inputs['RightLegLength'])
        write_setting(StaticDataFile, 'valueLeftKneeWidth', inputs['LeftKneeWidth'])
        write_setting(StaticDataFile, 'valueRightKneeWidth', inputs['RightKneeWidth'])
        write_setting(StaticDataFile, 'valueLeftAnkleWidth', inputs['LeftAnkleWidth'])
        write_setting(StaticDataFile, 'valueRightAnkleWidth', inputs['RightAnkleWidth'])
        write_setting(StaticDataFile, 'valueLeftASIStoGTdist', inputs['LeftASIStoGTdist'])
        write_setting(StaticDataFile, 'valueRightASIStoGTdist', inputs['RightASIStoGTdist'])
        StaticDataFile.write('self.valueLeftFootModelCheck = ' + "'" + str(inputs['self.LeftFootModelCheck']) + "'" + '\n')
        StaticDataFile.write('self.valueRightFootModelCheck = ' + "'" + str(inputs['self.RightFootModelCheck']) + "'" + '\n')
        StaticDataFile.write('self.valueLeftHindfootVarus = ' + "'" + inputs['LeftHindfootVarus'] + "'" + '\n')
        StaticDataFile.write('self.valueLeftCalcanealPitch = ' + "'" + inputs['LeftCalcanealPitch'] + "'" + '\n')
        StaticDataFile.write('self.valueLeftHindfootProgression = ' + "'" + inputs['LeftHindfootProgression'] + "'" + '\n')
        StaticDataFile.write('self.valueLeftFirstMetatarsalPitch = ' + "'" + inputs['LeftFirstMetatarsalPitch'] + "'" + '\n')
        StaticDataFile.write('self.valueRightHindfootVarus = ' + "'" + inputs['RightHindfootVarus'] + "'" + '\n')
        StaticDataFile.write('self.valueRightCalcanealPitch = ' + "'" + inputs['RightCalcanealPitch'] + "'" + '\n')
        StaticDataFile.write('self.valueRightHindfootProgression = ' + "'" + inputs['RightHindfootProgression'] + "'" + '\n')
        StaticDataFile.write('self.valueRightFirstMetatarsalPitch = ' + "'" + inputs['RightFirstMetatarsalPitch'] + "'" + '\n')
        StaticDataFile.write('self.valueLeftPlantigradeCheck = ' + "'" + str(inputs['self.LeftPlantigradeCheck']) + "'" + '\n')
        StaticDataFile.write('self.valueRightPlantigradeCheck = ' + "'" + str(inputs['self.RightPlantigradeCheck']) + "'" + '\n')
        StaticDataFile.write('self.valueSujectShodCheck = ' + "'" + str(inputs['self.SubjectShodCheck']) + "'" + '\n')
        if str(inputs['self.SubjectShodCheck']) == '1':
            write_setting(StaticDataFile, 'valueLeftSoleThickness', inputs['LeftSoleThickness'])
            write_setting(StaticDataFile, 'valueRightSoleThickness', inputs['RightSoleThickness'])
        else:
            write_setting(StaticDataFile, 'valueLeftSoleThickness', '0')
            write_setting(StaticDataFile, 'valueRightSoleThickness', '0')
        StaticDataFile.write('self.valuePelvicFixCheck = ' + "'" + str(inputs['self.PelvicFixCheck']) + "'" + '\n')
        StaticDataFile.write('self.valueKneeAlignmentCheck = ' + "'" + str(inputs['self.KneeAlignmentCheck']) + "'" + '\n')
        StaticDataFile.write('self.valueStaticFrameNumber = ' + "'" + str(inputs['StaticFrameNumber']) + "'" + '\n')
        PatientInformationBlockEnds = 0
        for line in lines:
            words = line.split()
            if len(words) >= 2:
                if words[0] == '#' and words[1] == 'Pelfix':
                    PatientInformationBlockEnds = 1
                elif words[0] == '#' and words[1] == 'Transformation':
                    PatientInformationBlockEnds = 1
            if PatientInformationBlockEnds == 1:
                StaticDataFile.write(line)
        StaticDataFile.close()
    return {name: value for name, value in locals().items() if name != "state" and not callable(value)}
