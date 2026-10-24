"""Frozen original formulas for regression only; do not optimize this fixture.
Py3_MathModules.py SHA256 42a09ddf22a7ffc4be564bbe252bb7b26f9e5e4d885fc550eb7d6ba0afee5f57
Original GPL-3.0-or-later source; Copyright (C) 2023 Anas Fodkar.
"""
import numpy as np
import math


def ComputeUnitVecFromPts(Tail, Tip):
    if np.linalg.norm(Tip-Tail) == 0.0 or math.isnan(np.linalg.norm(Tip-Tail)) is True:
        #print('Error: Attempt to divide by zero in determination of unit vector.')
        UnitVector = np.array([0.,0.,0.])
    else:
        UnitVector = (Tip-Tail)/np.linalg.norm(Tip-Tail)
    return UnitVector

def TransformVectorIntoLabCoors(Vector, TransformationMatrix):
    TransformedVector = np.array([0.,0.,0.])
    for i in range(3):
        TransformedVector[i] = Vector[0]*TransformationMatrix[i,0] + Vector[1]*TransformationMatrix[i,1] + Vector[2]*TransformationMatrix[i,2]

    return TransformedVector

def TransformPointIntoLabCoors(Point, TransformationMatrix, CoordinateSystemOrigin):
    TransformedVector = TransformVectorIntoLabCoors(Point, TransformationMatrix)
    TransformedPoint = TransformedVector + CoordinateSystemOrigin

    return TransformedPoint

def TransformVectorIntoMovingCoors(Vector, TransformationMatrix):
    TransformedVector = np.array([0.,0.,0.])
    for i in range(3):
        TransformedVector[i] = Vector[0]*TransformationMatrix[0,i] + Vector[1]*TransformationMatrix[1,i] + Vector[2]*TransformationMatrix[2,i]

    return TransformedVector

def TransformPointIntoMovingCoors(Point, TransformationMatrix, Origin):

    TranslatedPoint = Point - Origin
    TransformedPoint = TransformVectorIntoMovingCoors(TranslatedPoint, TransformationMatrix)

    return TransformedPoint

def TransformAnatCoorSysIntoTechCoors(EAnt, ETech):
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
    AngVel = [[0. for m in range(framecount)] for n in range(3)]
    AngAcc = [[0. for m in range(framecount)] for n in range(3)]

    for FrameNumber in range(FirstFrame-1, LastFrame):
        AngVel[0][FrameNumber] =  Velocity[0][FrameNumber] * np.cos(Angles[1][FrameNumber]) + \
                                  Velocity[2][FrameNumber] * np.cos(Angles[0][FrameNumber]) * np.sin(Angles[1][FrameNumber])

        AngVel[1][FrameNumber] =  Velocity[1][FrameNumber] + \
                                 -Velocity[2][FrameNumber] * np.sin(Angles[0][FrameNumber])

        AngVel[2][FrameNumber] = -Velocity[0][FrameNumber] * np.sin(Angles[1][FrameNumber]) + \
                                  Velocity[2][FrameNumber] * np.cos(Angles[0][FrameNumber]) * np.cos(Angles[1][FrameNumber])

        AngAcc[0][FrameNumber] =  Acceleration[0][FrameNumber] * np.cos(Angles[1][FrameNumber]) +\
                                 -Velocity[0][FrameNumber] * Velocity[1][FrameNumber] * np.sin(Angles[1][FrameNumber]) +\
                                  Acceleration[2][FrameNumber] * np.cos(Angles[0][FrameNumber]) * np.sin(Angles[1][FrameNumber]) +\
                                 -Velocity[2][FrameNumber] * Velocity[0][FrameNumber] * np.sin(Angles[0][FrameNumber]) * np.sin(Angles[1][FrameNumber]) +\
                                  Velocity[2][FrameNumber] * Velocity[1][FrameNumber] * np.cos(Angles[0][FrameNumber]) * np.cos(Angles[1][FrameNumber])

        AngAcc[1][FrameNumber] =  Acceleration[1][FrameNumber] + \
                                 -Acceleration[2][FrameNumber] * np.sin(Angles[0][FrameNumber])  + \
                                 -Velocity[2][FrameNumber] * Velocity[0][FrameNumber] * np.cos(Angles[0][FrameNumber])

        AngAcc[2][FrameNumber] = -Acceleration[0][FrameNumber] * np.sin(Angles[1][FrameNumber]) + \
                                 -Velocity[0][FrameNumber] * Velocity[1][FrameNumber] * np.cos(Angles[1][FrameNumber]) + \
                                  Acceleration[2][FrameNumber] * np.cos(Angles[0][FrameNumber]) * np.cos(Angles[1][FrameNumber]) + \
                                 -Velocity[2][FrameNumber] * Velocity[0][FrameNumber] * np.sin(Angles[0][FrameNumber]) * np.cos(Angles[1][FrameNumber]) + \
                                 -Velocity[2][FrameNumber] * Velocity[1][FrameNumber] * np.cos(Angles[0][FrameNumber]) * np.sin(Angles[1][FrameNumber])

    return ([AngVel, AngAcc])

def Differentiate(YData, FirstFrame, LastFrame, framecount, DeltaTime):
    # Inputs is vector-based data set.
    # Converts into three single dimensional arrays for differentiation
    # Returns the first and second derivative arrays into vector-based variables
    FirstDerivativeData = [[0. for m in range(framecount)] for n in range(3)]
    SecondDerivativeData = [[0. for m in range(framecount)] for n in range(3)]

    for i in range(3):
        for FrameNumber in range(FirstFrame -1 + 3 , LastFrame - 3):
            # Fit Quadratic polynomial in 7 point window
            x = [0, 1*DeltaTime, 2*DeltaTime, 3*DeltaTime, 4*DeltaTime, 5*DeltaTime, 6*DeltaTime]
            y = [ YData[i][FrameNumber-3],YData[i][FrameNumber-2], YData[i][FrameNumber-1], YData[i][FrameNumber], YData[i][FrameNumber+1], YData[i][FrameNumber+2], YData[i][FrameNumber+3] ]
            if not np.all(np.isfinite(y)):
                continue

            # Fit fourth order polynomial to the 7 point data window
            try:
                coeffs = np.polyfit(x, y, 3)
            except np.linalg.LinAlgError:
                continue
            ffit_Polynomial = np.poly1d(coeffs)
            FirstDeriv_Polynomial = ffit_Polynomial.deriv()
            SecondDeriv_Polynomial = FirstDeriv_Polynomial.deriv()

            # Compute values at midpoint of 7-point window
            FirstDerivativeData[i][FrameNumber] = FirstDeriv_Polynomial(3*DeltaTime)
            SecondDerivativeData[i][FrameNumber] = SecondDeriv_Polynomial(3*DeltaTime)

            # Account for Beginning and End Points
            if FrameNumber == FirstFrame -1 + 3:
                FirstDerivativeData[i][FrameNumber-3] = FirstDeriv_Polynomial(0*DeltaTime)
                SecondDerivativeData[i][FrameNumber-3] = SecondDeriv_Polynomial(0*DeltaTime)
                FirstDerivativeData[i][FrameNumber-2] = FirstDeriv_Polynomial(1*DeltaTime)
                SecondDerivativeData[i][FrameNumber-2] = SecondDeriv_Polynomial(1*DeltaTime)
                FirstDerivativeData[i][FrameNumber-1] = FirstDeriv_Polynomial(2*DeltaTime)
                SecondDerivativeData[i][FrameNumber-1] = SecondDeriv_Polynomial(2*DeltaTime)
                #print(x)
                #print(y)
                #print(FirstDeriv_Polynomial(3*DeltaTime))
                #print(SecondDerivativeData[i][FrameNumber])


            if FrameNumber == LastFrame - 3 - 1:
                FirstDerivativeData[i][FrameNumber+1] = FirstDeriv_Polynomial(4*DeltaTime)
                SecondDerivativeData[i][FrameNumber+1] = SecondDeriv_Polynomial(4*DeltaTime)
                FirstDerivativeData[i][FrameNumber+2] = FirstDeriv_Polynomial(5*DeltaTime)
                SecondDerivativeData[i][FrameNumber+2] = SecondDeriv_Polynomial(5*DeltaTime)
                FirstDerivativeData[i][FrameNumber+3] = FirstDeriv_Polynomial(6*DeltaTime)
                SecondDerivativeData[i][FrameNumber+3] = SecondDeriv_Polynomial(6*DeltaTime)


    return ([FirstDerivativeData, SecondDerivativeData])

def Smooth1DArray(DataArray,StartFrame,EndFrame,Order,WindowWidth):
    #print DataArray
    DataArraySmoothed = [0. for m in range(len(DataArray))]
    # If WindowWidth is larger than data array size
    if EndFrame - StartFrame + 1 < WindowWidth:
        WindowWidth = EndFrame - StartFrame + 1

    # Fit fourth order polynomial to WindowWidth Data
    XWindow = [0. for m in range(WindowWidth)]
    YWindow = [0. for m in range(WindowWidth)]
    for FrameNumber in range(StartFrame - 1 + int(WindowWidth/2), EndFrame - int(WindowWidth/2)):
        for i in range(WindowWidth):
            XWindow[i] = i
            YWindow[i] = DataArray[FrameNumber - int(WindowWidth/2) + i]
        if not np.all(np.isfinite(YWindow)):
            continue
        try:
            coeffs = np.polyfit(XWindow, YWindow, 3)
        except np.linalg.LinAlgError:
            continue
        ffit_polynomial = np.poly1d(coeffs)
        DataArraySmoothed[FrameNumber] = ffit_polynomial(int(WindowWidth/2))

        # For Beginning of Data Array
        if FrameNumber == StartFrame - 1 + int(WindowWidth/2):
            #print FrameNumber
            #print XWindow
            #print YWindow
            for j in range(int(WindowWidth/2)):
                #print(int(WindowWidth/2) - j - 1, FrameNumber - j - 1)
                DataArraySmoothed[FrameNumber - j - 1] = ffit_polynomial(int(WindowWidth/2) - j - 1)

        # For End of Data Array
        if FrameNumber == EndFrame - int(WindowWidth/2) - 1:
            #print FrameNumber
            for j in range(int(WindowWidth/2)):
                #print(int(WindowWidth/2) + j + 1, FrameNumber + j + 1)
                DataArraySmoothed[FrameNumber + j + 1] = ffit_polynomial(int(WindowWidth/2) + j + 1)

    return DataArraySmoothed
