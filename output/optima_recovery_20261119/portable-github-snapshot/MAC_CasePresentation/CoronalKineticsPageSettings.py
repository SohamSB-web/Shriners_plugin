self.LeftCoronalKineticsNames = ['LeftTrunkObliquity','', '', 
                             'LeftPelvicObliquity', '', '',
                             'LeftHipAbAdduct', 'LeftKneeValgVar', '',
                             'LeftHipAbAdductMoment', 'LeftKneeValgVarMoment', 'LeftFootAbAdductMoment',
                             'LeftHipAbAdductPower', 'LeftKneeValgVarPower', '']

self.RightCoronalKineticsNames = ['RightTrunkObliquity','', '', 
                             'RightPelvicObliquity', '', '',
                             'RightHipAbAdduct', 'RightKneeValgVar', '',
                             'RightHipAbAdductMoment', 'RightKneeValgVarMoment', 'RightFootAbAdductMoment',
                             'RightHipAbAdductPower', 'RightKneeValgVarPower', '']

self.CoronalKineticsTitles =    ['Trunk Obliquity','', '', 
                             'Pelvic Obliquity', '', '',
                             'Hip Ab/Adduction', 'Knee Varus/Valgus', '',
                             'Hip Moment', 'Knee Moment', 'Ankle Moment',
                             'Hip Power (Coronal)', 'Knee Power (Coronal)', '']

self.CoronalKineticsYLabels =   ['Up-Down', '-', '-', 
                             'Up-Down', '-', '-', 
                             'Add-Abd', 'Var-Val', '-', 
                             'Abd-Add', 'Abd-Add', 'Abd-Add', 
                             'Gen-Abs', 'Gen-Abs', '-']

self.CoronalKineticsUpperLimit = [15,15,45,
                              15,15,45,
                              15,30,45,
                              2,2,2,
                              3,3,3]

self.CoronalKineticsLowerLimit = [-15,-15,-30,
                              -15,-15,-30,
                              -15,-30,-30,
                              -1,-1,-1,
                              -2,-2,-2]

self.CoronalKineticsYAxisTickLabels = [[-15,-10,-5,0,5,10,15],[],[],
                                   [-15,-10,-5,0,5,10,15],[],[],
                                   [-15,-10,-5,0,5,10,15],[-30,-20,-10,0,10,20,30],[],
                                   [-1,0,1,2],[-1,0,1,2],[-1,0,1,2],
                                   [-2,-1,0,1,2,3],[-2,-1,0,1,2,3],[]]

self.CoronalKineticsYLabelOffsetsXTop = [-3,0,0,
                                    -3,0,0,
                                    -3,-3,-3,
                                    -2,-2,-2,
                                    -2,-2,-2]

self.CoronalKineticsYLabelOffsetsYTop = [11.5,0,0,
                                    11.5,0,0,
                                    11.5,23.5,35.0,
                                    1.5,1.5,1.5,
                                    2.5,2.5,2.5]

self.CoronalKineticsYLabelOffsetsXBottom = [-0.5,0,0,
                                       -0.5,0,0,
                                       -3,-3,-3,
                                       -2,-2,-2,
                                       -2,-2,-2]

self.CoronalKineticsYLabelOffsetsYBottom = [-13.5,0,0,
                                       -13.5,0,0,
                                       -13.5,-27.5,-39.5,
                                       -0.7,-0.7,-0.7,
                                       -1.7,-1.7,-1.7]

self.CoronalKineticsUnitLabels = ["Degrees","Degrees","Degrees","Nm/kg","Watts/kg"]