"""Frozen original formulas for regression only; do not optimize this fixture.
Py3_GaitModules.py SHA256 52e1e3e7618c9adfdfa8e130300087239c725a4fd2d2f73689df16f6a5214246
Original GPL-3.0-or-later source; Copyright (C) 2023 Anas Fodkar.
"""
import numpy as np
from legacy_dynamic_math import *
import legacy_dynamic_math as math


def TechCS_Pelvis_Newington(LASIS, RASIS, SACR):

    epy = math.ComputeUnitVecFromPts(RASIS, LASIS)
    ed3 = math.ComputeUnitVecFromPts(RASIS, SACR)
    epz = np.cross(epy,ed3)
    epz = epz/np.linalg.norm(epz)
    epx = np.cross(epy,epz)

    EPelvisTech = np.column_stack((epx,epy,epz))
    MidASISLab = (LASIS + RASIS) /2

    return([EPelvisTech, MidASISLab])

def TechCS_Thigh_Newington(Side, HipCenter, ThighMarker, VirtualKneeMarker):

    ethz = math.ComputeUnitVecFromPts(VirtualKneeMarker, HipCenter)

    #Intermediate Vector from Knee to Thigh Marker
    R1 = math.ComputeUnitVecFromPts(VirtualKneeMarker, ThighMarker)

    if Side == 'Right':
        ethx = np.cross(ethz, R1)
        ethx = ethx /np.linalg.norm(ethx)
    if Side == 'Left':
        ethx = np.cross(R1, ethz)
        ethx = ethx /np.linalg.norm(ethx)

    ethy = np.cross(ethz, ethx)

    EThighTech = np.column_stack((ethx,ethy,ethz))

    return EThighTech

def TechCS_Shank_Newington(Side, KneeCenter, TibialMarker, LateralAnkle):

    esz = math.ComputeUnitVecFromPts(LateralAnkle, KneeCenter)
    R1 = math.ComputeUnitVecFromPts(LateralAnkle, TibialMarker)

    if Side == 'Right':
        esx = np.cross(esz, R1)
    if Side == 'Left':
        esx = np.cross(R1, esz)
    esx = esx /np.linalg.norm(esx)
    esy = np.cross(esz, esx)

    EShankTech = np.column_stack((esx,esy,esz))

    return EShankTech

def TechCS_Foot_Newington(Side, KneeCenterLab, AnkleCenterLab, ToeMarker):

    eztemp = math.ComputeUnitVecFromPts(AnkleCenterLab, KneeCenterLab)
    ex = math.ComputeUnitVecFromPts(AnkleCenterLab, ToeMarker)
    ey = np.cross(eztemp,ex)
    ey = ey/ np.linalg.norm(ey)
    ez = np.cross(ex,ey)
    ez = ez/ np.linalg.norm(ez)

    EFootTech = np.column_stack((ex,ey,ez))

    return EFootTech

def AnatCS_Shank_Proximal_Newington(Side, KneeCenterLab, VirtualKneeMarkerLab, AnkleCenterLab):

    ez = math.ComputeUnitVecFromPts(AnkleCenterLab,KneeCenterLab)
    R1 = math.ComputeUnitVecFromPts(KneeCenterLab, VirtualKneeMarkerLab)

    if Side == 'Left':
        ex = np.cross(R1, ez)
    if Side == 'Right':
        ex = np.cross(ez, R1)

    ex = ex/ np.linalg.norm(ex)
    ey = np.cross(ez,ex)

    EShankProximalAnat = np.column_stack((ex,ey,ez))

    return EShankProximalAnat

def AnatCS_Shank_Distal_VCM(Side, KneeCenterLab, AnkleCenterLab, LateralAnkleMarker):

    ez = math.ComputeUnitVecFromPts(AnkleCenterLab,KneeCenterLab)

    if Side == 'Left':
        R1 = math.ComputeUnitVecFromPts(AnkleCenterLab, LateralAnkleMarker)
    if Side == 'Right':
        R1 = math.ComputeUnitVecFromPts(LateralAnkleMarker, AnkleCenterLab)

    ex = np.cross(R1, ez)
    ex = ex/ np.linalg.norm(ex)
    ey = np.cross(ez,ex)

    EShankDistalAnat = np.column_stack((ex,ey,ez))

    return EShankDistalAnat

def TechCS_Hindfoot_mSHCG(Side, LateralCalcaneusMarker, MedialCalcaneusMarker, HeelMarker):

    CCAL = (LateralCalcaneusMarker + MedialCalcaneusMarker) /2
    ex = math.ComputeUnitVecFromPts(HeelMarker, CCAL)

    if Side == 'Left':
        R1 = math.ComputeUnitVecFromPts(MedialCalcaneusMarker, LateralCalcaneusMarker)
    if Side == 'Right':
        R1 = math.ComputeUnitVecFromPts(LateralCalcaneusMarker, MedialCalcaneusMarker)

    ez = np.cross(ex,R1)
    ez = ez/ np.linalg.norm(ez)
    ey = np.cross(ez,ex)

    EHindfootTech = np.column_stack((ex,ey,ez))

    return EHindfootTech

def TechCS_Forefoot_mSHCG(Side, MT1B, MT1H, MT5H):

    ex = math.ComputeUnitVecFromPts(MT1B, MT1H)

    if Side == 'Left':
        R1 = math.ComputeUnitVecFromPts(MT1H, MT5H)
    if Side == 'Right':
        R1 = math.ComputeUnitVecFromPts(MT5H, MT1H)

    ez = np.cross(ex,R1)
    ez = ez/ np.linalg.norm(ez)
    ey = np.cross(ez,ex)

    EForefootTech = np.column_stack((ex,ey,ez))
    return EForefootTech

def TechCS_Hallux_mSHCG(Side, HLX, MTP1, TOE):

    ex = math.ComputeUnitVecFromPts(MTP1, HLX)

    if Side == 'Left':
        R1 = math.ComputeUnitVecFromPts(MTP1, TOE)
    if Side =='Right':
        R1 = math.ComputeUnitVecFromPts(TOE, MTP1)

    ez = np.cross(ex,R1)
    ez = ez/ np.linalg.norm(ez)
    ey = np.cross(ez,ex)

    EHalluxTech = np.column_stack((ex,ey,ez))

    return EHalluxTech
