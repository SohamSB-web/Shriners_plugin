self.LeftSagittalKineticsNames = ['LeftTrunkTilt','', '', 
                             'LeftPelvicTilt', '', '',
                             'LeftHipFlexExt', 'LeftKneeFlexExt', 'LeftDorsiPlanFlex',
                             'LeftHipFlexExtMoment', 'LeftKneeFlexExtMoment', 'LeftDorsiPlanFlexMoment',
                             'LeftHipFlexExtPower', 'LeftKneeFlexExtPower', 'LeftDorsiPlanFlexPower']

self.RightSagittalKineticsNames = ['RightTrunkTilt','', '', 
                              'RightPelvicTilt', '', '',
                              'RightHipFlexExt', 'RightKneeFlexExt', 'RightDorsiPlanFlex',
                              'RightHipFlexExtMoment', 'RightKneeFlexExtMoment', 'RightDorsiPlanFlexMoment',
                              'RightHipFlexExtPower', 'RightKneeFlexExtPower', 'RightDorsiPlanFlexPower']

self.SagittalKineticsTitles =    ['Trunk Tilt','', '', 
                             'Pelvic Tilt', '', '',
                             'Hip Flexion-Extension', 'Knee Flexion-Extension', 'Ankle Plantar-Dorsiflexion',
                             'Hip Moment', 'Knee Moment', 'Ankle Moment',
                             'Hip Power (Sagittal)', 'Knee Power (Sagittal)', 'Ankle Power (Sagittal)']

self.SagittalKineticsYLabels =   ['Ant-Post', '-', '-', 
                             'Ant-Post', '-', '-', 
                             'Flex-Ext', 'Flex-Ext', 'Dors-Plnt', 
                             'Ext-Flex', 'Ext-Flex', 'Ext-Flex', 
                             'Gen-Abs', 'Gen-Abs', 'Gen-Abs']

self.SagittalKineticsUpperLimit = [40,15,45,
                              40,15,45,
                              60,80,30,
                              2,2,2,
                              3,3,3]

self.SagittalKineticsLowerLimit = [-10,-15,-30,
                              -10,-15,-30,
                              -15,-20,-45,
                              -1,-1,-1,
                              -2,-2,-2]

self.SagittalKineticsYAxisTickLabels = [[-10,0,10,20,30,40],[],[],
                                   [-10,0,10,20,30,40],[],[],
                                   [-15,0,15,30,45,60],[-20,0,20,40,60,80],[-45,-30,-15,0,15,30],
                                   [-1,0,1,2],[-1,0,1,2],[-1,0,1,2],
                                   [-2,-1,0,1,2,3],[-2,-1,0,1,2,3],[-2,-1,0,1,2,3]]

self.SagittalKineticsYLabelOffsetsXTop = [-2,0,0,
                                     -2,0,0,
                                     -2,-2,-2,
                                     -2,-2,-2,
                                     -2,-2,-2]

self.SagittalKineticsYLabelOffsetsYTop = [33.5,0,0,
                                     33.5,0,0,
                                     50.0,67.0,20.0,
                                     1.5,1.5,1.5,
                                     2.5,2.5,2.5]

self.SagittalKineticsYLabelOffsetsXBottom = [-2,0,0,
                                        -2,0,0,
                                        -2,-2,-2,
                                        -2,-2,-2,
                                        -2,-2,-2]

self.SagittalKineticsYLabelOffsetsYBottom = [-7,0,0,
                                        -7,0,0,
                                        -10,-14,-40,
                                        -0.7,-0.7,-0.7,
                                        -1.7,-1.7,-1.7]


self.SagittalKineticsUnitLabels = ["Degrees","Degrees","Degrees","Nm/kg","Watts/kg"]