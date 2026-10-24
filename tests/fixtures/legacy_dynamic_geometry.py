"""Frozen pre-batching formulas; GPL-3.0-or-later, Copyright (C) 2023 Anas Fodkar."""
import numpy as np
from legacy_dynamic_math import *
import legacy_dynamic_math as math
from types import SimpleNamespace

def MassCenter(ProximalPoint, DistalPoint, DistalPercentage):

    LongAxisVector = ProximalPoint - DistalPoint
    SegmentLength = np.linalg.norm(LongAxisVector)
    LongAxisUnitVector = LongAxisVector / np.linalg.norm(LongAxisVector)

    COM = DistalPoint + DistalPercentage * SegmentLength * LongAxisUnitVector

    return COM

def RadiusOfGyration(ProximalPoint, DistalPoint, Percentage1, Percentage2, Percentage3):

    LongAxisVector = ProximalPoint - DistalPoint
    SegmentLength = np.linalg.norm(LongAxisVector)

    RadGyr = np.array([0.,0.,0.])
    RadGyr[0] = Percentage1 * SegmentLength
    RadGyr[1] = Percentage2 * SegmentLength
    RadGyr[2] = Percentage3 * SegmentLength

    return RadGyr

def ComputeMuscleLength(Side,MusclePoints,MuscleSegments,EPelvisAnatDelp,PelvisOrigin,EThighAnat,ThighOrigin,EShankAnat,ShankOrigin,EPatellaAnat,PatellaOrigin,ECalcaneusAnat,CalcaneusOrigin):
    MuscleLength = 0
    MusclePointsLab = []
    for i in range(len(MusclePoints)-1):
        if Side == 'Left':
            MusclePoint1 = MusclePoints[i]
            MusclePoint2 = MusclePoints[i+1]
        if Side == 'Right':
            MusclePoint1 = [MusclePoints[i][0],-MusclePoints[i][1],MusclePoints[i][2]]
            MusclePoint2 = [MusclePoints[i+1][0],-MusclePoints[i+1][1],MusclePoints[i+1][2]]

        # First Point
        if MuscleSegments[i] == 'Pelvis':
            Point1 = TransformPointIntoLabCoors(MusclePoint1,EPelvisAnatDelp,PelvisOrigin)
        if MuscleSegments[i] == 'Thigh':
            Point1 = TransformPointIntoLabCoors(MusclePoint1,EThighAnat,ThighOrigin)
        if MuscleSegments[i] == 'Shank':
            Point1 = TransformPointIntoLabCoors(MusclePoint1,EShankAnat,ShankOrigin)
        if MuscleSegments[i] == 'Patella':
            Point1 = TransformPointIntoLabCoors(MusclePoint1,EPatellaAnat,PatellaOrigin)
        if MuscleSegments[i] == 'Calcaneus':
            Point1 = TransformPointIntoLabCoors(MusclePoint1,ECalcaneusAnat,CalcaneusOrigin)
        # Second Point
        if MuscleSegments[i+1] == 'Pelvis':
            Point2 = TransformPointIntoLabCoors(MusclePoint2,EPelvisAnatDelp,PelvisOrigin)
        if MuscleSegments[i+1] == 'Thigh':
            Point2 = TransformPointIntoLabCoors(MusclePoint2,EThighAnat,ThighOrigin)
        if MuscleSegments[i+1] == 'Shank':
            Point2 = TransformPointIntoLabCoors(MusclePoint2,EShankAnat,ShankOrigin)
        if MuscleSegments[i+1] == 'Patella':
            Point2 = TransformPointIntoLabCoors(MusclePoint2,EPatellaAnat,PatellaOrigin)
        if MuscleSegments[i+1] == 'Calcaneus':
            Point2 = TransformPointIntoLabCoors(MusclePoint2,ECalcaneusAnat,CalcaneusOrigin)

        # Add Points to the List
        if i == 0:
            MusclePointsLab.append(Point1)
            MusclePointsLab.append(Point2)
        else:
            MusclePointsLab.append(Point2)

        # Compute Distance
        MuscleLength = MuscleLength + np.linalg.norm(Point2-Point1)

    return [MuscleLength,MusclePointsLab]

def RotateCSaroundXaxis(InputCS,Angle):
    OutputCS = np.eye(3)
    epx = np.array([InputCS[0][0],InputCS[1][0],InputCS[2][0]])
    epy = np.array([InputCS[0][1],InputCS[1][1],InputCS[2][1]])
    epz = np.array([InputCS[0][2],InputCS[1][2],InputCS[2][2]])

    # Rotate CS around Y axis by Angle
    ex = epx
    ey = epy * np.cos(-Angle*np.pi/180) + epz *-np.sin(-Angle*np.pi/180)
    ez = epy * np.sin(-Angle*np.pi/180) + epz * np.cos(-Angle*np.pi/180)

    OutputCS = np.column_stack((ex,ey,ez))

    return OutputCS

def RotateCSaroundYaxis(InputCS,Angle):
    OutputCS = np.eye(3)
    epx = np.array([InputCS[0][0],InputCS[1][0],InputCS[2][0]])
    epy = np.array([InputCS[0][1],InputCS[1][1],InputCS[2][1]])
    epz = np.array([InputCS[0][2],InputCS[1][2],InputCS[2][2]])

    # Rotate CS around Y axis by Angle
    ex = epx * np.cos(-Angle*np.pi/180) + epz * np.sin(-Angle*np.pi/180)
    ey = epy
    ez = epx *-np.sin(-Angle*np.pi/180) + epz * np.cos(-Angle*np.pi/180)

    OutputCS = np.column_stack((ex,ey,ez))

    return OutputCS

def RotateCSaroundZaxis(InputCS,Angle):
    OutputCS = np.eye(3)
    epx = np.array([InputCS[0][0],InputCS[1][0],InputCS[2][0]])
    epy = np.array([InputCS[0][1],InputCS[1][1],InputCS[2][1]])
    epz = np.array([InputCS[0][2],InputCS[1][2],InputCS[2][2]])

    # Rotate CS around Y axis by Angle
    ex = epx * np.cos(-Angle*np.pi/180) + epy *-np.sin(-Angle*np.pi/180)
    ey = epx * np.sin(-Angle*np.pi/180) + epy * np.cos(-Angle*np.pi/180)
    ez = epz

    OutputCS = np.column_stack((ex,ey,ez))

    return OutputCS

def TechCS_Trunk_Newington(C7, LCLV, RCLV, LASIS, RASIS, SACR):

    # Intialize Matrix and array
    # If . is not placed after zero, values will be truncated to integers
    ETrunkTech =  np.matrix([[0. for m in range(3)] for n in range(3)])
    PelvicCenterLab = np.array([0.,0.,0.])
    ShouldersCenterLab = np.array([0.,0.,0.])

    # Determine Pelvic Coordinate System
    epy = math.ComputeUnitVecFromPts(RASIS, LASIS)
    ed3 = math.ComputeUnitVecFromPts(RASIS, SACR)
    epz = np.cross(epy,ed3)
    epz = epz/np.linalg.norm(epz)
    epx = np.cross(epy,epz)

    #Determine Center of the Pelvic Cluster
    d3 = np.linalg.norm(SACR - RASIS)
    beta = np.arccos(np.dot(ed3,epy))
    d2 = d3 * np.sin(beta)

    PelvicCenterLab = (RASIS + LASIS)/2 - 0.5 * d2 * epx

    # Compute Shoulder Coordinate System
    esy = math.ComputeUnitVecFromPts(RCLV, LCLV)
    ed3 = math.ComputeUnitVecFromPts(RCLV, C7)
    esz = np.cross(esy,ed3)
    esz = esz/np.linalg.norm(esz)
    esx = np.cross(esy,esz)

    # Determine Center of Shoulder Cluster
    d3 = np.linalg.norm(C7 - RCLV)
    beta = np.arccos(np.dot(ed3,esy))
    d2 = d3 * np.sin(beta)

    ShouldersCenterLab = (RCLV + LCLV)/2 - 0.5 * d2 * esx

    # Compute Trunk Coordinate System
    etz = ShouldersCenterLab - PelvicCenterLab

    etz = etz/np.linalg.norm(etz)
    etx = np.cross(esy,etz)
    etx = etx/np.linalg.norm(etx)
    ety = np.cross(etz,etx)

    ETrunkTech = np.column_stack((etx,ety,etz))

    return([ETrunkTech, PelvicCenterLab, ShouldersCenterLab])

def AnatCS_Pelvis_Delp(LASIS, RASIS, SACR, PelvicTiltOffset):
    MidASISLab = (LASIS + RASIS) /2

    ey = math.ComputeUnitVecFromPts(RASIS, LASIS)
    ed3 = math.ComputeUnitVecFromPts(SACR,  MidASISLab)
    ez = np.cross(ed3,ey)
    ez = ez/np.linalg.norm(ez)
    ex = np.cross(ey,ez)

    EPelvisAnat = np.column_stack((ex,ey,ez))

    # Rotate CS around Y axis by PelviTiltOffset
    EPelvisAnat = math.RotateCSaroundYaxis(EPelvisAnat,PelvicTiltOffset)

    return([EPelvisAnat, MidASISLab])

def JointCenterModel_Hip_Newington(Side, MarkerDiameter, ASISdist, ASIStoGTdist, LeftLegLength, RightLegLength, RASIS, LASIS, EPelvisTech, MidASISLab):

    #Constants in degrees
    ThetaConst = 28.42
    PelvisTiltConst = 18.0

    # Convert to radians
    ThetaConstRadians = ThetaConst * np.pi /180
    PelvisTiltConstRadians = PelvisTiltConst * np.pi /180

    LongerLegLength = max(LeftLegLength, RightLegLength)
    #estimate ASIStoGTDist based on regression relationship if necessary
    if ASIStoGTdist == 0:
            ASIStoGTdist = 0.12876 * float(LongerLegLength) - 48.56

    C = float(LongerLegLength) * 0.115 - 15.33

    #define hip center relative to a neutral (flat) pelvis
    HipInPelvisCoorsTemp = np.array([0.,0.,0.])
    HipInPelvisCoorsTemp[0] = -(float(ASIStoGTdist) + float(MarkerDiameter)/2)
    if Side == 'Right':
        HipInPelvisCoorsTemp[1] = C * np.sin(ThetaConstRadians) - (float(ASISdist)/2)
    if Side == 'Left':
        HipInPelvisCoorsTemp[1] = -C * np.sin(ThetaConstRadians) + (float(ASISdist)/2)
    HipInPelvisCoorsTemp[2] = -C * np.cos(ThetaConstRadians)

    #rotate to account for mean pelvic tilt of study group
    HipCenterPelvis = np.array([0.,0.,0.])
    HipCenterPelvis[0] = np.cos(PelvisTiltConstRadians) * HipInPelvisCoorsTemp[0] - np.sin(PelvisTiltConstRadians) * HipInPelvisCoorsTemp[2]
    HipCenterPelvis[1] = HipInPelvisCoorsTemp[1]
    HipCenterPelvis[2] = np.sin(PelvisTiltConstRadians) * HipInPelvisCoorsTemp[0] + np.cos(PelvisTiltConstRadians) * HipInPelvisCoorsTemp[2]

    #compute hip location relative to lab origin and expressed relative to lab coordinate system
    HipCenterLab = math.TransformPointIntoLabCoors(HipCenterPelvis, EPelvisTech, MidASISLab)

    return([HipCenterPelvis, HipCenterLab])

def JointCenterModel_Hip_Harrington(Side, ASISdist, RASIS, LASIS, SACR, EPelvisTech, MidASISLab):

    #PelvicWidth = np.linalg.norm(LASIS-RASIS)
    PelvicWidth = ASISdist
    PelvicDepth = np.linalg.norm((LASIS+RASIS)/2 - SACR)

    #define hip center relative to a pelvis coordinate syste (Origin at MidASIS)
    HipCenterPelvis = np.array([0.,0.,0.])

    # Single Linear Regression Equations
    HipCenterPelvis[0] = -0.24 * PelvicDepth - 9.9
    if Side == 'Right':
        HipCenterPelvis[1] =  -0.33*PelvicWidth - 7.3
    if Side == 'Left':
        HipCenterPelvis[1] =  +0.33*PelvicWidth + 7.3
    HipCenterPelvis[2] = -0.30*PelvicWidth -10.9

    # Two Variable Regression Equations
#    HipCenterPelvis[0] = -0.24 * PelvicDepth - 9.9
#    if Side == 'Right':
#        HipCenterPelvis[1] =  -0.28*PelvicDepth - 0.16*PelvicWidth - 7.9
#    if Side == 'Left':
#        HipCenterPelvis[1] =  +0.28*PelvicDepth + 0.16*PelvicWidth + 7.9
#    HipCenterPelvis[2] = -0.16*PelvicWidth - 0.04*LongerLegLength - 7.1


    #compute hip location relative to lab origin and expressed relative to lab coordinate system
    HipCenterLab = math.TransformPointIntoLabCoors(HipCenterPelvis, EPelvisTech, MidASISLab)

    return([HipCenterPelvis, HipCenterLab])

def JointCenterModel_Hip_Harrington2(Side, ASISdist, LeftLegLength, RightLegLength, RASIS, LASIS, SACR, EPelvisTech, MidASISLab):

    #PelvicWidth = np.linalg.norm(LASIS-RASIS)
    PelvicWidth = ASISdist
    PelvicDepth = np.linalg.norm((LASIS+RASIS)/2 - SACR)
    LongerLegLength = max(LeftLegLength, RightLegLength)

    #define hip center relative to a pelvis coordinate syste (Origin at MidASIS)
    HipCenterPelvis = np.array([0.,0.,0.])

    # Single Linear Regression Equations
#    HipCenterPelvis[0] = -0.24 * PelvicDepth - 9.9
#    if Side == 'Right':
#        HipCenterPelvis[1] =  -0.33*PelvicWidth - 7.3
#    if Side == 'Left':
#        HipCenterPelvis[1] =  +0.33*PelvicWidth + 7.3
#    HipCenterPelvis[2] = -0.30*PelvicWidth -10.9

    # Two Variable Regression Equations
    HipCenterPelvis[0] = -0.24 * PelvicDepth - 9.9
    if Side == 'Right':
        HipCenterPelvis[1] =  -0.28*PelvicDepth - 0.16*PelvicWidth - 7.9
    if Side == 'Left':
        HipCenterPelvis[1] =  +0.28*PelvicDepth + 0.16*PelvicWidth + 7.9
    HipCenterPelvis[2] = -0.16*PelvicWidth - 0.04*LongerLegLength - 7.1


    #compute hip location relative to lab origin and expressed relative to lab coordinate system
    HipCenterLab = math.TransformPointIntoLabCoors(HipCenterPelvis, EPelvisTech, MidASISLab)

    return([HipCenterPelvis, HipCenterLab])


math = SimpleNamespace(**vars(math))
math.RotateCSaroundYaxis = RotateCSaroundYaxis
