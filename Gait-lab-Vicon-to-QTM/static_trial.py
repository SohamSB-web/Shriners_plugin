"""Static-only C3D extraction; retains the legacy point and PROCESSING contracts.

Static calibration never consumes FP. Avoid the dynamic extractor's force-plate
calculation, live COP request and GUI imports on this path.
"""
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from ezc3d import c3d


def load_static_trial(session_path, filename):
    xml = Path(session_path).resolve(strict=True)
    if Path(filename).name != filename:
        raise ValueError("Static filename must be a filename within the selected session")
    measurements = [m for m in ET.parse(xml).getroot().iter('Measurement')
                    if m.get('Filename') == filename]
    if len(measurements) != 1:
        raise ValueError(f"Expected one XML measurement for {filename!r}; found {len(measurements)}")
    # Retain the original extractor's stem convention for existing recordings.
    stem = filename.split('.')[0]
    trial_path = (xml.parent / (stem + '.c3d')).resolve(strict=True)
    if trial_path.parent != xml.parent:
        raise ValueError("Static C3D resolves outside the selected session")
    reader = c3d(str(trial_path), extract_forceplat_data=False)
    offset = reader['header']['points']['first_frame']
    frames = reader['parameters']['POINT']['FRAMES']['value'][0]
    fields = {'Type': measurements[0].get('Type'), 'Filename': stem,
              'Path': str(xml.parent), 'Name': 'Test', 'initial_frame_offset': offset,
              'Capture_Frequency': reader['parameters']['POINT']['RATE']['value'][0],
              'Frames': frames, 'Points': reader['parameters']['POINT']['LABELS']['value'],
              'Units': reader['parameters']['POINT']['UNITS']['value'][0],
              'First Frame': max(reader['header']['points']['first_frame'] - offset, 0),
              'Last Frame': min(reader['header']['points']['last_frame'] + 1 - offset, frames)}
    processing = reader['parameters'].get('PROCESSING', {})
    skip = {'Session ID', 'ID', 'BodyMass', 'Mass', 'Bodymass', 'Uncropped Measurement Frames',
            'Cropped Measurement Start Frame', 'Cropped Measurement End Frame'}
    lengths = {'Height', 'InterAsisDistance', 'LeftLegLength', 'RightLegLength',
               'LeftKneeWidth', 'RightKneeWidth', 'LeftAnkleWidth', 'RightAnkleWidth',
               'LeftAsisTrocanterDistance', 'RightAsisTrocanterDistance'}
    declared = 'Metrics' in processing
    metric = processing.get('Metrics', {}).get('value', ['mm'])[0]
    for key, item in processing.items():
        if 'value' not in item or len(item['value']) == 0:
            continue
        value = item['value'][0]
        numeric = isinstance(value, (int, float)) or isinstance(value, str) and value.isdigit()
        if key not in skip and numeric:
            if metric == 'm':
                value *= 1000
            elif metric == 'cm':
                value *= 10
            elif not declared and key in lengths and isinstance(value, (int, float, np.floating)) and 0 < abs(value) < 10:
                value *= 1000
        fields[key] = value
    fields['Bodymass'] = fields.get('BodyMass', fields.get('Bodymass', 0))
    for index, label in enumerate(fields['Points']):
        marker = {axis: reader['data']['points'][i][index] for i, axis in enumerate(('X', 'Y', 'Z'))}
        marker['Exists'] = [not (np.isnan(marker['X'][j]) or np.isnan(marker['Y'][j]) or np.isnan(marker['Z'][j]))
                            for j in range(len(marker['X']))]
        fields[label.strip()] = marker
    return fields
