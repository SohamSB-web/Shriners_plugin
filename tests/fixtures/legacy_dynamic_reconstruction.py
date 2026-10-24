"""Frozen original reconstruction loops; GPL-3.0-or-later, Copyright (C) 2023 Anas Fodkar."""

PELVIS = r"""for FrameNumber in range(StartFrame, EndFrame):
                # Compute Pelvis Tech Coordinates
                if self.valuePelvicFixCheck == "1":
                    # Pelvis Technical coordinate system based on LILC, RILC, SACR
                    LeftIliacMarker = np.array(
                        [
                            LeftIliacMarkerX[FrameNumber],
                            LeftIliacMarkerY[FrameNumber],
                            LeftIliacMarkerZ[FrameNumber],
                        ]
                    )
                    RightIliacMarker = np.array(
                        [
                            RightIliacMarkerX[FrameNumber],
                            RightIliacMarkerY[FrameNumber],
                            RightIliacMarkerZ[FrameNumber],
                        ]
                    )
                    SacralMarker = np.array(
                        [
                            SacralMarkerX[FrameNumber],
                            SacralMarkerY[FrameNumber],
                            SacralMarkerZ[FrameNumber],
                        ]
                    )
                    [EPelvisTech, MidASISLab] = gait.TechCS_Pelvis_Newington(
                        LeftIliacMarker, RightIliacMarker, SacralMarker
                    )

                if self.valuePelvicFixCheck == "2":  # Pelvic Triad Option
                    # Pelvis Technical coordinate system based on LPSI, RPSI, SACT
                    LeftPSISMarker = np.array(
                        [
                            LeftPSISMarkerX[FrameNumber],
                            LeftPSISMarkerY[FrameNumber],
                            LeftPSISMarkerZ[FrameNumber],
                        ]
                    )
                    RightPSISMarker = np.array(
                        [
                            RightPSISMarkerX[FrameNumber],
                            RightPSISMarkerY[FrameNumber],
                            RightPSISMarkerZ[FrameNumber],
                        ]
                    )
                    SacralTriadMarker = np.array(
                        [
                            SacralTriadMarkerX[FrameNumber],
                            SacralTriadMarkerY[FrameNumber],
                            SacralTriadMarkerZ[FrameNumber],
                        ]
                    )
                    [EPelvisTech, MidASISLab] = gait.TechCS_Pelvis_Newington(
                        LeftPSISMarker, RightPSISMarker, SacralTriadMarker
                    )

                LeftASISMarkerLab = math.TransformPointIntoLabCoors(
                    self.valueLeftASISMarkerPelvis, EPelvisTech, MidASISLab
                )
                RightASISMarkerLab = math.TransformPointIntoLabCoors(
                    self.valueRightASISMarkerPelvis, EPelvisTech, MidASISLab
                )

                arrayLASISMarkerX[FrameNumber] = LeftASISMarkerLab[0]
                arrayLASISMarkerY[FrameNumber] = LeftASISMarkerLab[1]
                arrayLASISMarkerZ[FrameNumber] = LeftASISMarkerLab[2]
                arrayRASISMarkerX[FrameNumber] = RightASISMarkerLab[0]
                arrayRASISMarkerY[FrameNumber] = RightASISMarkerLab[1]
                arrayRASISMarkerZ[FrameNumber] = RightASISMarkerLab[2]"""

FOOT = r"""for FrameNumber in range(StartFrame, EndFrame):
            # Compute Technical Coordinate System: Left Foot Segments
            if self.valueLeftFootModelCheck == "1":
                # print FrameNumber
                # print LeftFirstMetarsalBaseMarkerX
                LeftFirstMetarsalBaseMarker = np.array(
                    [
                        LeftFirstMetarsalBaseMarkerX[FrameNumber],
                        LeftFirstMetarsalBaseMarkerY[FrameNumber],
                        LeftFirstMetarsalBaseMarkerZ[FrameNumber],
                    ]
                )
                LeftFirstMetarsalHeadMarker = np.array(
                    [
                        LeftFirstMetarsalHeadMarkerX[FrameNumber],
                        LeftFirstMetarsalHeadMarkerY[FrameNumber],
                        LeftFirstMetarsalHeadMarkerZ[FrameNumber],
                    ]
                )
                LeftFifthMetarsalHeadMarker = np.array(
                    [
                        LeftFifthMetarsalHeadMarkerX[FrameNumber],
                        LeftFifthMetarsalHeadMarkerY[FrameNumber],
                        LeftFifthMetarsalHeadMarkerZ[FrameNumber],
                    ]
                )
                LeftEForefootTech = gait.TechCS_Forefoot_mSHCG(
                    "Left",
                    LeftFirstMetarsalBaseMarker,
                    LeftFirstMetarsalHeadMarker,
                    LeftFifthMetarsalHeadMarker,
                )
                LeftMT23HMarkerLab = math.TransformPointIntoLabCoors(
                    self.valueLeft23MetatarsalHeadMarkerForefoot,
                    LeftEForefootTech,
                    LeftFirstMetarsalBaseMarker,
                )
                arrayLMT23HMarkerX[FrameNumber] = LeftMT23HMarkerLab[0]
                arrayLMT23HMarkerY[FrameNumber] = LeftMT23HMarkerLab[1]
                arrayLMT23HMarkerZ[FrameNumber] = LeftMT23HMarkerLab[2]

            # Compute Technical Coordinate System: Right Foot Segments
            if self.valueRightFootModelCheck == "1":
                RightFirstMetarsalBaseMarker = np.array(
                    [
                        RightFirstMetarsalBaseMarkerX[FrameNumber],
                        RightFirstMetarsalBaseMarkerY[FrameNumber],
                        RightFirstMetarsalBaseMarkerZ[FrameNumber],
                    ]
                )
                RightFirstMetarsalHeadMarker = np.array(
                    [
                        RightFirstMetarsalHeadMarkerX[FrameNumber],
                        RightFirstMetarsalHeadMarkerY[FrameNumber],
                        RightFirstMetarsalHeadMarkerZ[FrameNumber],
                    ]
                )
                RightFifthMetarsalHeadMarker = np.array(
                    [
                        RightFifthMetarsalHeadMarkerX[FrameNumber],
                        RightFifthMetarsalHeadMarkerY[FrameNumber],
                        RightFifthMetarsalHeadMarkerZ[FrameNumber],
                    ]
                )
                RightEForefootTech = gait.TechCS_Forefoot_mSHCG(
                    "Right",
                    RightFirstMetarsalBaseMarker,
                    RightFirstMetarsalHeadMarker,
                    RightFifthMetarsalHeadMarker,
                )
                RightMT23HMarkerLab = math.TransformPointIntoLabCoors(
                    self.valueRight23MetatarsalHeadMarkerForefoot,
                    RightEForefootTech,
                    RightFirstMetarsalBaseMarker,
                )
                arrayRMT23HMarkerX[FrameNumber] = RightMT23HMarkerLab[0]
                arrayRMT23HMarkerY[FrameNumber] = RightMT23HMarkerLab[1]
                arrayRMT23HMarkerZ[FrameNumber] = RightMT23HMarkerLab[2]"""
