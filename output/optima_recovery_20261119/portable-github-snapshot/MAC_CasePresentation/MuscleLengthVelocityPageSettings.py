self.LeftMuscleLengthVelocityNames = ['LeftTrunkTilt','','',
                        'LeftPelvicTilt','LeftIlioPsoasLength','LeftRectFemLength',
                        'LeftHipFlexExt','LeftMedHamstringLength','LeftLatHamstringLength',
                        'LeftKneeFlexExt','LeftMedHamstringVelocity','LeftLatHamstringVelocity',
                        'LeftDorsiPlanFlex', 'LeftGastrocLength','LeftSoleusLength']

self.RightMuscleLengthVelocityNames = ['RightTrunkTilt','','',
                        'RightPelvicTilt','RightIlioPsoasLength','RightRectFemLength',
                        'RightHipFlexExt','RightMedHamstringLength','RightLatHamstringLength',
                        'RightKneeFlexExt','RightMedHamstringVelocity','RightLatHamstringVelocity',
                        'RightDorsiPlanFlex', 'RightGastrocLength','RightSoleusLength']

self.MuscleLengthVelocityTitles =    ['Trunk Tilt','', '', 
                  'Pelvic Tilt', 'IlioPsoas Length (Normalized)', 'Rectus Femoris Length (Norm.)',
                  'Hip Flexion-Extension', 'Med Hamstrings Length (Norm.)','Lat Hamstrings Length (Norm.)',
                  'Knee Flexion-Extension', 'Med Hamstrings Velocity (Norm.)','Lat Hamstrings Velocity (Norm.)',
                  'Ankle Plantar-Dorsiflexion', 'Gastrocnemius Length (Norm.)','Soleus Length (Normalized)',]

self.MuscleLengthVelocityYLabels =   ['Ant-Post', '-', '-', 
                  'Ant-Post', '-', '-', 
                  'Flex-Ext', '-', '-', 
                  'Flex-Ext', '-', '-', 
                  'Dors-Plnt', '-', '-']

self.MuscleLengthVelocityUpperLimit = [ 40,1.2,1.2,
                           40,1.1,1.15,
                           60,1.1,1.1,
                           80,2,2,
                           30,1.1,1.1,]

self.MuscleLengthVelocityLowerLimit = [-10,0.8,0.8,
                          -10,0.9,0.9,
                          -15,0.9,0.9,
                          -20,-2,-2,
                          -45,0.9,0.9]
                   
self.MuscleLengthVelocityYAxisTickLabels = [[-10,0,10,20,30,40],[0.8,0.9,1.0,1.1,1.2],[0.8,0.9,1.0,1.1,1.2],
                               [-10,0,10,20,30,40],[0.9,0.95,1.0,1.05,1.1],[0.9,0.95,1.0,1.05,1.1,1.15],
                               [-15,0,15,30,45,60],[0.9,0.95,1.0,1.05,1.1],[0.9,0.95,1.0,1.05,1.1],
                               [-20,0,20,40,60,80], [-2,-1,0,1,2], [-2,-1,0,1,2],
                               [-45,-30,-15,0,15,30],[0.9,0.95,1.0,1.05,1.1],[0.9,0.95,1.0,1.05,1.1]]

self.MuscleLengthVelocityYLabelOffsetsXTop = [-2,-2,-2,
                                 -2,-2,-2,
                                 -2,-2,-2,
                                 -2,-2,-2,
                                 -2,-2,-2]

self.MuscleLengthVelocityYLabelOffsetsYTop = [33.5,1.14,1.14,
                                 33.5,1.30,1.14,
                                 50.0,1.14,1.14,
                                 67.0,1.4,1.4,
                                 20.0,1.14,1.14,]

self.MuscleLengthVelocityYLabelOffsetsXBottom = [-2,-2,-2,
                                     -2,-2,-2,
                                     -2,-2,-2,
                                     -2,-2,-2,
                                     -2,-2,-2]

self.MuscleLengthVelocityYLabelOffsetsYBottom = [-7,0.84,0.84,
                                    -7,0.86,0.84,
                                    -10,0.84,0.84,
                                    -14,-1.6,-1.6,
                                    -40.5,0.84,0.84,]          

self.MuscleLengthVelocityUnitLabels = ["Degrees","Degrees","Degrees","Degrees","Degrees"]