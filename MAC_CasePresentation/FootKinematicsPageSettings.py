self.LeftFootAngleNames = ['LeftHindFootTilt','LeftHindFootObliquity','LeftForeFootTilt',
                    'LeftDorsiPlanFlex', '', 'LeftFootProgression',  
                    'LeftAnkleComplexDorsiPlanFlex','LeftAnkleComplexValgVar','LeftAnkleComplexRotation', 
                    'LeftMidFootDorsiPlanFlex','LeftMidFootSupPron','LeftMidFootAbAdduct',
                    'LeftHalDorsiPlanFlex', 'LeftSupination', 'LeftHalValgVar']

self.RightFootAngleNames = ['RightHindFootTilt','RightHindFootObliquity','RightForeFootTilt',
                    'RightDorsiPlanFlex', '', 'RightFootProgression',  
                    'RightAnkleComplexDorsiPlanFlex','RightAnkleComplexValgVar','RightAnkleComplexRotation', 
                    'RightMidFootDorsiPlanFlex','RightMidFootSupPron','RightMidFootAbAdduct',
                    'RightHalDorsiPlanFlex', 'RightSupination', 'RightHalValgVar']

self.FootAngleTitles =    ['Hindfoot Tilt','Hindfoot Obliquity','Forefoot Tilt',
                      'Ankle Plantar-Dorsiflexion', '', 'Foot Progression',
                      'AnkleComplex Plnt-Dorsiflexion','AnkleComplex Varus/Valgus', 'AnkleComplex Rotation', 
                      'MidfootComplex Flex-Extension','MidfootComplex Inv/Eversion', 'MidfootComplex Ab/Adduction',
                      '1st MTP Flexion-Extension', 'Supination Index', '1st MTP Varus-Valgus']

self.FootAnglesYLabels =   ['Dors-Plnt','Var-Val','Dors-Plnt', 
                  'Dors-Plnt', '-', 'Int-Ext',
                  'Dors-Plnt', 'Var-Val', 'Int-Ext', 
                  'Dors-Plnt', 'Inv-Ev', 'Add-Abd', 
                  'Dors-Plnt', 'Sup-Pro', 'Var-Val']

self.FootAngleUpperLimit = [90,30,60,
                   30,45,45,
                   45,30,45,
                   15,30,45,
                   90,30,45]

self.FootAngleLowerLimit = [-90,-30,-180,
                       -45,-30,-45,
                       -30,-30,-45,
                       -60,-30,-45,
                       -30,-30,-45]
                   
self.FootYAxisTickLabels = [[-90,-60,-30,0,30,60,90],[-30,-15,0,15,30],[-180,-120,-60,0,60],
                       [-45,-30,-15,0,15,30],[-30,-15,0,15,30,45],[-45,-30,-15,0,15,30,45],
                       [-30,-15,0,15,30,45],[-30,-15,0,15,30],[-45,-30,-15,0,15,30,45],
                       [-60,-45,-30,-15,0,15],[-30,-15,0,15,30],[-45,-30,-15,0,15,30,45],
                       [-30,0,30,60,90],[-30,-15,0,15,30],[-45,-30,-15,0,15,30,45]]

self.FootYLabelOffsetsXTop = [-2,-3,-3,
                     -2,-3,-3,
                     -2,-3,-3,
                     -2,-3,-3,
                     -2,-2,-3]

self.FootYLabelOffsetsYTop = [70.0,22.5,30.0,
                         20.0,35.0,34.5,
                         35.0,22.5,34.5,
                         04.5,22.5,34.5,
                         72.5,22.5,34.5]

self.FootYLabelOffsetsXBottom = [-2,-3,-3,
                        -2,-3,-3,
                        -2,-3.0,-3,
                        -2,-3.0,-3,
                        -2,-3.0,-3]

self.FootYLabelOffsetsYBottom = [-80,-25.0,-160,
                            -40.5,-25.0,-40.5,
                            -25.5,-25.5,-40.5,
                            -55.0,-25.5,-40.5,
                            -17.5,-25.5,-40.5]

self.FootAnglesUnitLabels = ["Degrees","Degrees","Degrees","Degrees","Degrees"]