"""Isolated regression probe. Only writes to the caller's disposable session copy."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

parser = argparse.ArgumentParser()
parser.add_argument('mode', choices=['legacy', 'legacy-normalized', 'engine'])
parser.add_argument('session')
parser.add_argument('filename')
parser.add_argument('result')
parser.add_argument('--condition', default='BF')
args = parser.parse_args()
if not (Path(args.session).resolve().parent / '.static-refactor-disposable').is_file():
    raise RuntimeError('Regression probe requires a marked disposable session copy; never pass clinical originals')
root = Path(__file__).resolve().parents[1]
backend = root / 'Gait-lab-Vicon-to-QTM'
sys.path.insert(0, str(backend))
sys.path.insert(0, str(root))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
started = perf_counter()
import numpy as np
commands = []


def sender(command, payload):
    if command in ('SetTrajectory', 'CreateModelMarker'):
        commands.append((command, json.loads(payload)))
    return 'recorded by offline regression probe'


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return value.name
    raise TypeError(type(value).__name__)


marker_error = None
if args.mode.startswith('legacy'):
    # Exact committed baseline, not the other agent's changing working files.
    source = subprocess.check_output(['git', 'show', 'origin/main:Gait-lab-Vicon-to-QTM/Py3_StaticMain.py'], cwd=root).decode('utf8')
    if args.mode == 'legacy-normalized':
        start = source.index('        def saveResultsinC3D():')
        prefix, body = source[:start], source[start:]
        body = body.replace('exec(open(StaticDataFileName).read())',
                            'exec(open(StaticDataFileName).read())\n            normalize_processing_measurements(self)', 1)
        source = prefix + body
    import Py3_varExtractor as extractor
    old_extract = extractor.extract_fields_by_filename
    load_timings = {}
    def timed_extract(*a,**kw):
        start = perf_counter()
        result = old_extract(*a,**kw)
        load_timings['c3d_and_force_loading'] = perf_counter()-start
        return result
    extractor.extract_fields_by_filename = timed_extract
    import gapi
    gapi.grpc_send_command = sender
    gapi.GetForcePlate = lambda: {}
    scope = {'__file__': str(backend / 'Py3_StaticMain.py'), '__name__': 'static_baseline'}
    sys.argv = ['Py3_StaticMain.py', '-s', args.session, '-f', args.filename, '-t', args.condition, '--headless']
    exec(compile(source.split('# Calls the main Function')[0], 'static_baseline', 'exec'), scope)
    imports = perf_counter() - started
    app = scope['Static_Main'](headless=True)
    app.hide()
    captured = {}
    def profiler(frame, event, arg):
        if event == 'return' and frame.f_code.co_name == 'build_UI' and 'LeftHipCenterPelvis' in frame.f_locals:
            captured.update(frame.f_locals)
    sys.setprofile(profiler)
    page = app.frames[scope['PatientInfo_Page']]
    clinical_started = perf_counter()
    page.build_UI()
    clinical = perf_counter() - clinical_started
    qa_started = perf_counter()
    app.frames[scope['QAreport_Page']].build_UI()
    qa = perf_counter() - qa_started
    calc_started = perf_counter()
    page = app.frames[scope['StaticSubjectCalibrationReport_Page']]
    page.build_UI()
    calc = perf_counter() - calc_started
    sys.setprofile(None)
    save_started = perf_counter()
    page.saveTransformationMatrices()
    save = perf_counter() - save_started
    marker_started = perf_counter()
    try:
        page.saveResultsinC3D()
    except Exception as error:
        marker_error = f'{type(error).__name__}: {error}'
    marker = perf_counter() - marker_started
    saved = scope['StaticDataFileName']
    owner = page
    timings = dict(load_timings, startup_and_loading=imports, clinical_ui=clinical, qa=qa, calculation=calc,
               saving=save, markers=marker, total=perf_counter() - started)
    app.close()
else:
    from static_calibration_engine import run_static_calibration
    imports = perf_counter() - started
    result = run_static_calibration(args.session, args.filename, args.condition)
    commands = result.modeled_commands
    captured = result.values
    saved = result.calibration_path
    owner = result.values['self']
    timings = dict(result.timings, startup_and_loading=imports, process_total=perf_counter() - started)
    assert result.success

values = {}
for key, value in captured.items():
    if key in ('self', 'state', 'fields', 'report', 'warnings'):
        continue
    if isinstance(value, (np.ndarray, int, float, str, bool, list, tuple)):
        try:
            json.dumps(value, default=plain)
        except TypeError:
            continue
        values[key] = value
data = {'values': values, 'commands': commands, 'timings': timings, 'marker_error': marker_error,
        'saved': Path(saved).read_text(encoding='utf8')}
Path(args.result).write_text(json.dumps(data, default=plain), encoding='utf8')
print('PROBE_RESULT', args.result)
