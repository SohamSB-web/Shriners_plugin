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
# Vector/Matrix operations modules

Created on Mon Feb 12 15:49:17 2018
Last Update: 26 Aug, 2024

@author: psaraswat
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

VersionNumber = 'Py3_v1.3'

import numpy as np
import math

def FrameVector(framecount, x, y, z):
    """Stack scalar or per-frame components into writable (frames, 3) vectors."""
    return np.broadcast_to(np.stack(np.broadcast_arrays(x, y, z), axis=-1),
                           (framecount, 3)).copy()

def ComputeUnitVecFromPts(Tail, Tip):
    difference = Tip - Tail
    if difference.ndim == 1:
        length = np.linalg.norm(difference)
        return np.zeros(3) if length == 0 or np.isnan(length) else difference / length
    length = np.linalg.norm(difference, axis=-1, keepdims=True)
    return np.divide(difference, length, out=np.zeros_like(difference, dtype=float),
                     where=(length != 0) & ~np.isnan(length))

def Compute3DAngle(Point1, Point2, Point3):
    UnitVector1 = ComputeUnitVecFromPts(Point2, Point1)
    UnitVector2 = ComputeUnitVecFromPts(Point2, Point3)
    
    Angle = np.arccos(np.dot(UnitVector1, UnitVector2))
    return Angle

def TransformVectorIntoLabCoors(Vector, TransformationMatrix):
    if np.ndim(TransformationMatrix) > 2 or np.ndim(Vector) > 1:
        return np.matmul(np.asarray(TransformationMatrix), np.asarray(Vector)[..., None])[..., 0]
    TransformedVector = np.array([0.,0.,0.])
    for i in range(3):
        TransformedVector[i] = Vector[0]*TransformationMatrix[i,0] + Vector[1]*TransformationMatrix[i,1] + Vector[2]*TransformationMatrix[i,2]
    
    return TransformedVector

def TransformPointIntoLabCoors(Point, TransformationMatrix, CoordinateSystemOrigin):
    TransformedVector = TransformVectorIntoLabCoors(Point, TransformationMatrix)
    TransformedPoint = TransformedVector + CoordinateSystemOrigin    

    return TransformedPoint

def TransformVectorIntoMovingCoors(Vector, TransformationMatrix):
    if np.ndim(TransformationMatrix) > 2 or np.ndim(Vector) > 1:
        return np.matmul(np.swapaxes(np.asarray(TransformationMatrix), -1, -2), np.asarray(Vector)[..., None])[..., 0]
    TransformedVector = np.array([0.,0.,0.])
    for i in range(3):
        TransformedVector[i] = Vector[0]*TransformationMatrix[0,i] + Vector[1]*TransformationMatrix[1,i] + Vector[2]*TransformationMatrix[2,i]
        
    return TransformedVector


def TransformPointIntoMovingCoors(Point, TransformationMatrix, Origin):
    
    TranslatedPoint = Point - Origin
    TransformedPoint = TransformVectorIntoMovingCoors(TranslatedPoint, TransformationMatrix)
    
    return TransformedPoint

def TransformAnatCoorSysIntoTechCoors(EAnt, ETech):
    if np.ndim(EAnt) > 2 or np.ndim(ETech) > 2:
        return np.matmul(np.swapaxes(np.asarray(ETech), -1, -2), np.asarray(EAnt))
    # ea- Vectors to be Transformed
    eax = EAnt[:,0]
    eay = EAnt[:,1]
    eaz = EAnt[:,2]
    
    # et- Transformed Vectors
    etx = TransformVectorIntoMovingCoors(eax,ETech)
    ety = TransformVectorIntoMovingCoors(eay,ETech)
    etz = TransformVectorIntoMovingCoors(eaz,ETech)
    
    EAnatRelTech = np.column_stack((etx,ety,etz))
        
    return EAnatRelTech

def TransformAnatCoorSysFromTechCoors(EAnatRelTech, ETech):
    if np.ndim(EAnatRelTech) > 2 or np.ndim(ETech) > 2:
        return np.matmul(np.asarray(ETech), np.asarray(EAnatRelTech))
    # ea- Vectors to be Transformed
    eax = EAnatRelTech[:,0]
    eay = EAnatRelTech[:,1]
    eaz = EAnatRelTech[:,2]
    
    # et- Transformed Vectors
    etx = TransformVectorIntoLabCoors(eax,ETech)
    ety = TransformVectorIntoLabCoors(eay,ETech)
    etz = TransformVectorIntoLabCoors(eaz,ETech)
    
    EAnat = np.column_stack((etx,ety,etz))
        
    return EAnat

def EulerAngles_YXZ(EMoving, ERef):
    if np.ndim(EMoving) > 2 or np.ndim(ERef) > 2:
        relative = np.matmul(np.swapaxes(ERef, -1, -2), EMoving)
        return np.stack((np.arcsin(-relative[..., 1, 2]),
                         np.arctan2(relative[..., 0, 2], relative[..., 2, 2]),
                         np.arctan2(relative[..., 1, 0], relative[..., 1, 1])), axis=-1)
    
    # em- Vectors of Moving Coordinate System
    emx = EMoving[:,0]
    emy = EMoving[:,1]
    emz = EMoving[:,2]
    
    # er- Vectors of Reference Coordinate System
    erx = ERef[:,0]
    ery = ERef[:,1]
    erz = ERef[:,2]
    
    # Initialize Compute Angles in radians 
    AnglesRad = np.array([0.,0.,0.])
    
    # Obiliquity or Ab/Adduction
    AnglesRad[0] = np.arcsin(-np.dot(emz,ery))    
    # Tilt or Flexion/Extension
    #AnglesRad[1] = np.arcsin(np.dot(emz,erx)) / np.cos(AnglesRad[0])
    AnglesRad[1] = np.arctan2(np.dot(emz,erx),np.dot(emz,erz))
    # Int/Ext Rotation
    #AnglesRad[2] = np.arcsin(np.dot(emx,ery)) / np.cos(AnglesRad[0])
    AnglesRad[2] = np.arctan2(np.dot(emx,ery),np.dot(emy,ery))
    
    return AnglesRad

def EulerAngles_ZXY(EMoving, ERef):
    if np.ndim(EMoving) > 2 or np.ndim(ERef) > 2:
        relative = np.matmul(np.swapaxes(ERef, -1, -2), EMoving)
        return np.stack((np.arcsin(relative[..., 2, 1]),
                         np.arctan2(-relative[..., 2, 0], relative[..., 2, 2]),
                         np.arctan2(-relative[..., 0, 1], relative[..., 1, 1])), axis=-1)
    
    # ROWS: em- Vectors of Moving Coordinate System
    emx = EMoving[:,0]
    emy = EMoving[:,1]
    emz = EMoving[:,2]
    
    # COLS: er- Vectors of Reference Coordinate System
    erx = ERef[:,0]
    ery = ERef[:,1]
    erz = ERef[:,2]
    
    # Initialize Compute Angles in radians 
    AnglesRad = np.array([0.,0.,0.])
    
    #alpha = ArcSin(t(2, 3))
    #beta = Atan2(-t(1, 3), t(3, 3))
    #gamma = Atan2(-t(2, 1), t(2, 2))

    # Obiliquity or Ab/Adduction
    AnglesRad[0] = np.arcsin(np.dot(emy,erz))
    # Tilt or Flexion/Extension
    AnglesRad[1] = np.arctan2(-np.dot(emx,erz),np.dot(emz,erz))
    # Int/Ext Rotation
    AnglesRad[2] = np.arctan2(-np.dot(emy,erx),np.dot(emy,ery))
    
    return AnglesRad
	
def EulerAngles_ZYX(EMoving, ERef):
    if np.ndim(EMoving) > 2 or np.ndim(ERef) > 2:
        relative = np.matmul(np.swapaxes(ERef, -1, -2), EMoving)
        return np.stack((np.arctan2(relative[..., 2, 1], relative[..., 2, 2]),
                         np.arcsin(-relative[..., 2, 0]),
                         np.arctan2(relative[..., 1, 0], relative[..., 0, 0])), axis=-1)
    
    # ROWS: em- Vectors of Moving Coordinate System
    emx = EMoving[:,0]
    emy = EMoving[:,1]
    emz = EMoving[:,2]
    
    # COLS: er- Vectors of Reference Coordinate System
    erx = ERef[:,0]
    ery = ERef[:,1]
    erz = ERef[:,2]
    
    # Initialize Compute Angles in radians 
    AnglesRad = np.array([0.,0.,0.])
    
    #alpha = Atan2(t(2, 3), t(3, 3))
    #beta = ArcSin(-t(1, 3))
    #gamma = Atan2(t(1, 2), t(1, 1))

    # Obiliquity or Ab/Adduction
    AnglesRad[0] = np.arctan2(np.dot(emy,erz),np.dot(emz,erz))
    # Tilt or Flexion/Extension
    AnglesRad[1] = np.arcsin(-np.dot(emx,erz))
    # Int/Ext Rotation
    AnglesRad[2] = np.arctan2(np.dot(emx,ery),np.dot(emx,erx))
    
    return AnglesRad

def AngVelAcc_Euler_YXZ(Angles, Velocity, Acceleration, FirstFrame, LastFrame, framecount):
    Angles, Velocity, Acceleration = map(np.asarray, (Angles, Velocity, Acceleration))
    AngVel = np.zeros((3, framecount))
    AngAcc = np.zeros((3, framecount))
    active = slice(FirstFrame - 1, LastFrame)
    AngVel[0][active] =  Velocity[0][active] * np.cos(Angles[1][active]) + \
                                      Velocity[2][active] * np.cos(Angles[0][active]) * np.sin(Angles[1][active])
    AngVel[1][active] =  Velocity[1][active] + \
                                     -Velocity[2][active] * np.sin(Angles[0][active])
    AngVel[2][active] = -Velocity[0][active] * np.sin(Angles[1][active]) + \
                                      Velocity[2][active] * np.cos(Angles[0][active]) * np.cos(Angles[1][active])
    AngAcc[0][active] =  Acceleration[0][active] * np.cos(Angles[1][active]) +\
                                     -Velocity[0][active] * Velocity[1][active] * np.sin(Angles[1][active]) +\
                                      Acceleration[2][active] * np.cos(Angles[0][active]) * np.sin(Angles[1][active]) +\
                                     -Velocity[2][active] * Velocity[0][active] * np.sin(Angles[0][active]) * np.sin(Angles[1][active]) +\
                                      Velocity[2][active] * Velocity[1][active] * np.cos(Angles[0][active]) * np.cos(Angles[1][active])
    AngAcc[1][active] =  Acceleration[1][active] + \
                                     -Acceleration[2][active] * np.sin(Angles[0][active])  + \
                                     -Velocity[2][active] * Velocity[0][active] * np.cos(Angles[0][active])
    AngAcc[2][active] = -Acceleration[0][active] * np.sin(Angles[1][active]) + \
                                     -Velocity[0][active] * Velocity[1][active] * np.cos(Angles[1][active]) + \
                                      Acceleration[2][active] * np.cos(Angles[0][active]) * np.cos(Angles[1][active]) + \
                                     -Velocity[2][active] * Velocity[0][active] * np.sin(Angles[0][active]) * np.cos(Angles[1][active]) + \
                                     -Velocity[2][active] * Velocity[1][active] * np.cos(Angles[0][active]) * np.sin(Angles[1][active])
    return [AngVel.tolist(), AngAcc.tolist()]

def MassCenter(ProximalPoint, DistalPoint, DistalPercentage):

    if np.ndim(ProximalPoint) > 1 or np.ndim(DistalPoint) > 1:
        LongAxisVector = ProximalPoint - DistalPoint
        SegmentLength = np.linalg.norm(LongAxisVector, axis=-1, keepdims=True)
        LongAxisUnitVector = LongAxisVector / SegmentLength
        return DistalPoint + DistalPercentage * SegmentLength * LongAxisUnitVector

    
    LongAxisVector = ProximalPoint - DistalPoint
    SegmentLength = np.linalg.norm(LongAxisVector)
    LongAxisUnitVector = LongAxisVector / np.linalg.norm(LongAxisVector)
    
    COM = DistalPoint + DistalPercentage * SegmentLength * LongAxisUnitVector
    
    return COM

def RadiusOfGyration(ProximalPoint, DistalPoint, Percentage1, Percentage2, Percentage3):

    if np.ndim(ProximalPoint) > 1 or np.ndim(DistalPoint) > 1:
        length = np.linalg.norm(ProximalPoint - DistalPoint, axis=-1)
        return np.stack((Percentage1 * length, Percentage2 * length, Percentage3 * length), axis=-1)


    LongAxisVector = ProximalPoint - DistalPoint
    SegmentLength = np.linalg.norm(LongAxisVector)
    
    RadGyr = np.array([0.,0.,0.])
    RadGyr[0] = Percentage1 * SegmentLength
    RadGyr[1] = Percentage2 * SegmentLength
    RadGyr[2] = Percentage3 * SegmentLength
    
    return RadGyr
def fill_gaps_polynomial(data, degree=3):
    """
    Interpolates NaN values in a trajectory array using a polynomial fit.

    Args:
        data (np.ndarray): The input array with shape (n_frames, n_dims).
                           Can be 1D or 2D.
        degree (int): The degree of the polynomial to fit.

    Returns:
        np.ndarray: The array with NaN values filled.
    """
    # Ensure data is at least 2D for consistent processing
    is_1d = data.ndim == 1
    if is_1d:
        data = data[:, np.newaxis]

    filled_data = data.copy()
    n_frames, n_dims = filled_data.shape
    frame_indices = np.arange(n_frames)

    for i in range(n_dims):
        y = filled_data[:, i]
        valid_mask = ~np.isnan(y)
        
        # Check if there's enough data to fit the polynomial
        if np.sum(valid_mask) <= degree:
            print(f"Warning: Not enough data points to fit a polynomial of degree {degree} for dimension {i}. Skipping.")
            continue

        # Get the known data points for fitting
        x_known = frame_indices[valid_mask]
        y_known = y[valid_mask]

        # Fit the polynomial to the known points
        # The result is an array of coefficients (from highest power to lowest)
        coeffs = np.polyfit(x_known, y_known, degree)

        # Create a callable polynomial function from the coefficients
        p = np.poly1d(coeffs)

        # Apply the function to all frame indices to get the full trajectory
        filled_data[:, i] = p(frame_indices)

    return filled_data.squeeze() if is_1d else filled_data

def Differentiate(YData, FirstFrame, LastFrame, framecount, DeltaTime):
    """Original seven-point cubic fit, solved for all finite windows together."""
    first = np.zeros((3, framecount))
    second = np.zeros((3, framecount))
    if LastFrame - FirstFrame + 1 < 7:
        return [first.tolist(), second.tolist()]
    windows = np.lib.stride_tricks.sliding_window_view(np.asarray(YData), 7, axis=-1)
    windows = windows[:, FirstFrame - 1:LastFrame - 6]
    valid = np.all(np.isfinite(windows), axis=-1)
    if not valid.any():
        return [first.tolist(), second.tolist()]
    x = np.arange(7) * DeltaTime
    try:
        coefficients = np.polyfit(x, windows[valid].T, 3)
    except np.linalg.LinAlgError:
        return [first.tolist(), second.tolist()]
    d1 = coefficients[:-1] * np.array([3, 2, 1])[:, None]
    d2 = d1[:-1] * np.array([2, 1])[:, None]
    axes, centers = np.nonzero(valid)
    first[axes, centers + FirstFrame + 2] = np.polyval(d1, 3 * DeltaTime)
    second[axes, centers + FirstFrame + 2] = np.polyval(d2, 3 * DeltaTime)
    # Edge values come only from the same first/last valid boundary window as before.
    for position, offsets in ((0, (0, 1, 2)), (windows.shape[1] - 1, (4, 5, 6))):
        selected = centers == position
        for offset in offsets:
            indices = position + FirstFrame - 1 + offset
            first[axes[selected], indices] = np.polyval(d1[:, selected], offset * DeltaTime)
            second[axes[selected], indices] = np.polyval(d2[:, selected], offset * DeltaTime)
    return [first.tolist(), second.tolist()]

def Smooth1DArray(DataArray, StartFrame, EndFrame, Order, WindowWidth):
    """Keep the legacy cubic degree, finite-window rule and boundary evaluation."""
    result = np.zeros(len(DataArray))
    WindowWidth = min(WindowWidth, EndFrame - StartFrame + 1)
    half = int(WindowWidth / 2)
    if EndFrame - StartFrame + 1 <= 2 * half:
        return result.tolist()
    windows = np.lib.stride_tricks.sliding_window_view(np.asarray(DataArray), WindowWidth)
    windows = windows[StartFrame - 1:EndFrame - 2 * half]
    valid = np.all(np.isfinite(windows), axis=-1)
    if not valid.any():
        return result.tolist()
    try:
        coefficients = np.polyfit(np.arange(WindowWidth), windows[valid].T, 3)
    except np.linalg.LinAlgError:
        return result.tolist()
    positions = np.flatnonzero(valid)
    result[positions + StartFrame - 1 + half] = np.polyval(coefficients, half)
    for position, offsets in ((0, range(half)),
                              (len(windows) - 1, range(half + 1, 2 * half + 1))):
        if not valid[position]:
            continue
        selected = np.flatnonzero(positions == position)[0]
        for offset in offsets:
            result[position + StartFrame - 1 + offset] = np.polyval(coefficients[:, selected], offset)
    return result.tolist()

def Smooth3DArray(Data3DArray,StartFrame,EndFrame,Order,WindowWidth):
    
    Data3DArraySmoothed = [[0. for m in range(len(Data3DArray[0]))] for n in range(3)]
    Data1DArrayX = [0. for m in range(len(Data3DArray[0]))]
    Data1DArrayY = [0. for m in range(len(Data3DArray[0]))]
    Data1DArrayZ = [0. for m in range(len(Data3DArray[0]))]
    
    # Create 3 1D Arrays
    for i in range(len(Data3DArray[0])):
        Data1DArrayX[i] = Data3DArray[0][i]
        Data1DArrayY[i] = Data3DArray[1][i]
        Data1DArrayZ[i] = Data3DArray[2][i]
    Data1DArrayXSmoothed = Smooth1DArray(Data1DArrayX, StartFrame, EndFrame, Order, WindowWidth)
    Data1DArrayYSmoothed = Smooth1DArray(Data1DArrayY, StartFrame, EndFrame, Order, WindowWidth)
    Data1DArrayZSmoothed = Smooth1DArray(Data1DArrayZ, StartFrame, EndFrame, Order, WindowWidth)
    
    for i in range(len(Data3DArray[0])):
        Data3DArraySmoothed[0][i] = Data1DArrayXSmoothed[i]
        Data3DArraySmoothed[1][i] = Data1DArrayYSmoothed[i]
        Data3DArraySmoothed[2][i] = Data1DArrayZSmoothed[i]
    
    return Data3DArraySmoothed

def Trim3DList(List,StartFrame,EndFrame):
    trimmedList = [[0. for m in range(EndFrame-StartFrame+1)] for n in range(len(List))]
    for i in range(len(List)):
        for j in range(StartFrame-1,EndFrame):
            trimmedList[i][j-StartFrame+1] = List[i][j]        
    return trimmedList

def ComputeMuscleLength(Side,MusclePoints,MuscleSegments,EPelvisAnatDelp,PelvisOrigin,EThighAnat,ThighOrigin,EShankAnat,ShankOrigin,EPatellaAnat,PatellaOrigin,ECalcaneusAnat,CalcaneusOrigin, active_points=None):

    if np.ndim(EPelvisAnatDelp) > 2 or np.ndim(PelvisOrigin) > 1:
        frames = {"Pelvis": (EPelvisAnatDelp, PelvisOrigin),
                  "Thigh": (EThighAnat, ThighOrigin), "Shank": (EShankAnat, ShankOrigin),
                  "Patella": (EPatellaAnat, PatellaOrigin), "Calcaneus": (ECalcaneusAnat, CalcaneusOrigin)}
        local = np.asarray(MusclePoints) * ([1, -1, 1] if Side == "Right" else [1, 1, 1])
        points = np.stack([TransformPointIntoLabCoors(point, *frames[segment])
                           for point, segment in zip(local, MuscleSegments)], axis=-2)
        length = np.zeros(points.shape[:-2])
        previous = points[..., 0, :]
        for index in range(1, len(MusclePoints)):
            distance = np.linalg.norm(points[..., index, :] - previous, axis=-1)
            if active_points is None:
                length = length + distance
                previous = points[..., index, :]
            else:
                include = active_points[..., index]
                length = length + np.where(include, distance, 0)
                previous = np.where(include[..., None], points[..., index, :], previous)
        return [length, points]

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

    if np.ndim(InputCS) > 2 or np.ndim(Angle) > 0:
        InputCS = np.asarray(InputCS)
        epx, epy, epz = InputCS[..., :, 0], InputCS[..., :, 1], InputCS[..., :, 2]
        c = np.cos(-np.asarray(Angle) * np.pi / 180)[..., None]
        s = np.sin(-np.asarray(Angle) * np.pi / 180)[..., None]
        return np.stack(np.broadcast_arrays(epx, epy * c + epz * -s, epy * s + epz * c), axis=-1)

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

    if np.ndim(InputCS) > 2 or np.ndim(Angle) > 0:
        InputCS = np.asarray(InputCS)
        epx, epy, epz = InputCS[..., :, 0], InputCS[..., :, 1], InputCS[..., :, 2]
        c = np.cos(-np.asarray(Angle) * np.pi / 180)[..., None]
        s = np.sin(-np.asarray(Angle) * np.pi / 180)[..., None]
        return np.stack(np.broadcast_arrays(epx * c + epz * s, epy, epx * -s + epz * c), axis=-1)

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

    if np.ndim(InputCS) > 2 or np.ndim(Angle) > 0:
        InputCS = np.asarray(InputCS)
        epx, epy, epz = InputCS[..., :, 0], InputCS[..., :, 1], InputCS[..., :, 2]
        c = np.cos(-np.asarray(Angle) * np.pi / 180)[..., None]
        s = np.sin(-np.asarray(Angle) * np.pi / 180)[..., None]
        return np.stack(np.broadcast_arrays(epx * c + epy * -s, epx * s + epy * c, epz), axis=-1)

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
