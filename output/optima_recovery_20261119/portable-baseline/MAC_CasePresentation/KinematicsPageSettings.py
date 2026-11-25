self.LeftAngleNames = ['LeftTrunkTilt','LeftTrunkObliquity', 'LeftTrunkRotation', 
                  'LeftPelvicTilt', 'LeftPelvicObliquity', 'LeftPelvicRotation',
                  'LeftHipFlexExt', 'LeftHipAbAdduct', 'LeftHipRotation',
                  'LeftKneeFlexExt', 'LeftKneeValgVar', 'LeftKneeRotation',
                  'LeftDorsiPlanFlex', 'LeftFootProgression', 'LeftFootRotation']

self.RightAngleNames = ['RightTrunkTilt','RightTrunkObliquity', 'RightTrunkRotation', 
                  'RightPelvicTilt', 'RightPelvicObliquity', 'RightPelvicRotation',
                  'RightHipFlexExt', 'RightHipAbAdduct', 'RightHipRotation',
                  'RightKneeFlexExt', 'RightKneeValgVar', 'RightKneeRotation',
                  'RightDorsiPlanFlex', 'RightFootProgression', 'RightFootRotation']

self.AngleTitles =    ['Trunk Tilt','Trunk Obliquity', 'Trunk Rotation', 
                  'Pelvic Tilt', 'Pelvic Obliquity', 'Pelvic Rotation',
                  'Hip Flexion-Extension', 'Hip Ab/Adduction', 'Hip Rotation',
                  'Knee Flexion-Extension', 'Knee Varus/Valgus', 'Knee Rotation',
                  'Ankle Plantar-Dorsiflexion', 'Foot Progression', 'Ankle Rotation']

self.AnglesYLabels =   ['Ant-Post', 'Up-Down', 'Int-Ext', 
                  'Ant-Post', 'Up-Down', 'Int-Ext', 
                  'Flex-Ext', 'Add-Abd', 'Int-Ext', 
                  'Flex-Ext', 'Var-Val', 'Int-Ext', 
                  'Dors-Plnt', 'Int-Ext', 'Int-Ext']

self.AngleUpperLimit = [40,15,45,
                   40,15,45,
                   60,15,45,
                   80,30,15,
                   30,45,45]

self.AngleLowerLimit = [-10,-15,-30,
                   -10,-15,-30,
                   -15,-15,-30,
                   -20,-30,-60,
                   -45,-45,-30]

self.YAxisTickLabels = [[-10,0,10,20,30,40],[-15,-10,-5,0,5,10,15],[-30,-15,0,15,30,45],
                   [-10,0,10,20,30,40],[-15,-10,-5,0,5,10,15],[-30,-15,0,15,30,45],
                   [-15,0,15,30,45,60],[-15,-10,-5,0,5,10,15],[-30,-15,0,15,30,45],
                   [-20,0,20,40,60,80],[-30,-20,-10,0,10,20,30],[-60,-45,-30,-15,0,15],
                   [-45,-30,-15,0,15,30],[-45,-30,-15,0,15,30,45],[-30,-15,0,15,30,45]]

self.YLabelOffsetsXTop = [-2,-3,-3,
                     -2,-3,-3,
                     -2,-3,-3,
                     -2,-3,-3,
                     -2,-3,-3]

self.YLabelOffsetsYTop = [33.5,11.5,35,
                     33.5,11.5,35,
                     50.0,11.5,35,
                     67.0,23.5,5,
                     20.0,35.0,35]

self.YLabelOffsetsXBottom = [-2,-0.5,-3,
                        -2,-0.5,-3,
                        -2,-3.0,-3,
                        -2,-3.0,-3,
                        -2,-3.0,-3]

self.YLabelOffsetsYBottom = [-7,-13.5,-25.0,
                        -7,-13.5,-25.0,
                        -10,-13.5,-25.0,
                        -14,-27.5,-55.0,
                        -40,-39.5,-25.0]

self.AnglesUnitLabels = ["Degrees","Degrees","Degrees","Degrees","Degrees"]