self.LeftEMGNames = ['LeftRawLRectFem','LeftRawLVastLat', 'LeftRawLMedHams', 'LeftRawLGasTroc', 'LeftRawLTibAnte']

self.RightEMGNames = ['RightRawRRectFem','RightRawRVastLat', 'RightRawRMedHams', 'RightRawRGasTroc', 'RightRawRTibAnte']

self.NormEMGEnvelopeNames = ['RectFemEnvelope','VastLatEnvelope', 'MedHamsEnvelope', 'GasTrocEnvelope', 'TibAnteEnvelope']

self.NormEMGOffsets = [0.06,0.08,0.2,0.12,0.3]

self.EMGTitles =    ['Rectus Femoris','Vastus Lateralis', 'Medial Hamstrings', 'Gastrocnemius', 'Tibialis Anterior']

self.EMGUpperLimit = [5,5,5,
                 5,5,5,
                 5,5,5,
                 5,5,5,
                 5,5,5]

self.EMGLowerLimit = [-5,-5,-5,
                 -5,-5,-5,
                 -5,-5,-5,
                 -5,-5,-5,
                 -5,-5,-5]

self.EMGYAxisTickLabels = [[-5,-2,0,2,5],[-5,-2,0,2,5],[-5,-2,0,2,5],
                      [-5,-2,0,2,5],[-5,-2,0,2,5],[-5,-2,0,2,5],
                      [-5,-2,0,2,5],[-5,-2,0,2,5],[-5,-2,0,2,5],
                      [-5,-2,0,2,5],[-5,-2,0,2,5],[-5,-2,0,2,5],
                      [-5,-2,0,2,5],[-5,-2,0,2,5],[-5,-2,0,2,5]]

## Based on Typical Data from SLC, GRN, SPO
self.EMGOnOffBarStart =  [[0,52,93,0],   # Rectus Femoris
                         [0,85,0,0],    # Vastus Lateralis
                         [0,85,0,0],    # MedialHamstrings
                         [5,0,0,0],    # Gastrocnemius
                         [0,57,0,0]]    # Tibialis Anterior

self.EMGOnOffBarEnd =    [[14,75,100,0], # Rectus Femoris
                         [23,100,0,0],  # Vastus Lateralis
                         [30,100,0,0],   # MedialHamstrings
                         [53,0,0,0],    # Gastrocnemius
                         [11,100,0,0]]  # Tibialis Anterior

#Reference- Gazendam 2007- Averaged EMG profiles in jogging and running at different speeds
self.RunEMGOnOffBarStart =  [[0,40,80,0],   # Rectus Femoris
                     [0,80,0,0],    # Vastus Lateralis
                     [6,70,0,0],    # MedialHamstrings
                     [0,86,0,0],    # Gastrocnemius
                     [27,0,0,0]]    # Tibialis Anterior

self.RunEMGOnOffBarEnd =    [[15,70,100,0], # Rectus Femoris
                     [15,100,0,0],  # Vastus Lateralis
                     [30,100,0,0],  # MedialHamstrings
                     [25,100,0,0],  # Gastrocnemius
                     [100,0,0,0]]   # Tibialis Anterior