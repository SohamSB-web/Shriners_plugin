self.LeftMuscleVelocityNames = ['LeftIlioPsoasVelocity','LeftGluteusMaxVelocity','',
                                'LeftRectFemVelocity', 'LeftVastLatVelocity', '',  
                                'LeftMedHamstringVelocity','LeftLatHamstringVelocity','', 
                                'LeftGastrocVelocity','LeftSoleusVelocity','',
                                'LeftTibPostVelocity', 'LeftPeronealVelocity', '']
        
self.RightMuscleVelocityNames = ['RightIlioPsoasVelocity','RightGluteusMaxVelocity','',
                        'RightRectFemVelocity', 'RightVastLatVelocity', '',  
                        'RightMedHamstringVelocity','RightLatHamstringVelocity','', 
                        'RightGastrocVelocity','RightSoleusVelocity','',
                        'RightTibPostVelocity', 'RightPeronealVelocity', '']

self.MuscleVelocityTitles =    ['IlioPsoas Velocity','Gluteus Maximus Velocity','',
                        'Rectus Femoris Velocity', 'Vastus Lateralis Velocity', '',  
                        'Med Hamstrings Velocity','Lat Hamstrings Velocity','', 
                        'Gastrocnemius Velocity','Soleus Velocity','',
                        'Tibialis Post Velocity', 'Peroneal Velocity', '']

#        self.MuscleVelocityYLabels =   ['Fast-Slow','Fast-Slow','Fast-Slow', 
#                                  'Fast-Slow','Fast-Slow','Fast-Slow',
#                                  'Fast-Slow','Fast-Slow','Fast-Slow',  
#                                  'Fast-Slow','Fast-Slow','Fast-Slow', 
#                                  'Fast-Slow','Fast-Slow','Fast-Slow', ]

self.MuscleVelocityYLabels =  ['-','-','-', 
                          '-','-','-',
                          '-','-','-',  
                          '-','-','-', 
                          '-','-','-']

self.MuscleVelocityUpperLimit = [2,2,2,
                           2,4,2,
                           2,2,2,
                           2,2,2,
                           1,1,1]

self.MuscleVelocityLowerLimit = [-2,-2,-2,
                             -2,-4,-2,
                             -2,-2,-2,
                             -2,-2,-2,
                             -1,-1,-1]
                   
self.MuscleVelocityYAxisTickLabels = [[-2,-1,0,1,2],[-2,-1,0,1,2],[-2,-1,0,1,2],
                               [-2,-1,0,1,2],[-4,-2,0,2,4],[-2,-1,0,1,2],
                               [-2,-1,0,1,2],[-2,-1,0,1,2],[-2,-1,0,1,2],
                               [-2,-1,0,1,2],[-2,-1,0,1,2],[-2,-1,0,1,2],
                               [-1,-0.5,0,0.5,1],[-1,-0.5,0,0.5,1],[-1,-0.5,0,0.5,1]]

self.MuscleVelocityYLabelOffsetsXTop = [-2,-2,-2,
                                 -2,-2,-2,
                                 -2,-2,-2,
                                 -2,-2,-2,
                                 -2,-2,-2]

self.MuscleVelocityYLabelOffsetsYTop = [1.4,1.4,1.4,
                                 1.4,1.4,1.4,
                                 1.4,1.4,1.4,
                                 1.4,1.4,1.4,
                                 1.4,1.4,1.4,]

self.MuscleVelocityYLabelOffsetsXBottom = [-2,-2,-2,
                                 -2,-2,-2,
                                 -2,-2,-2,
                                 -2,-2,-2,
                                 -2,-2,-2]

self.MuscleVelocityYLabelOffsetsYBottom = [-1.6,-1.6,-1.6,
                                    -1.6,-1.6,-1.6,
                                    -1.6,-1.6,-1.6,
                                    -1.6,-1.6,-1.6,
                                    -1.6,-1.6,-1.6]  

self.MuscleVelocityUnitLabels = ["m/m","m/m","m/m","m/m","m/m"]