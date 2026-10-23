"""Headless static orchestration; clinical equations live in calculations.

All state belongs to a single invocation. Original C3Ds and XML are read-only;
calibration publication is atomic and QTM output failures are reported separately.
"""
from time import perf_counter
_import_started = perf_counter()
from dataclasses import dataclass
from collections import defaultdict
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import FunctionType, SimpleNamespace

import numpy as np
import static_calibration_calculations as calculations
from static_calibration_parameters import populate_clinical_inputs, save_clinical_inputs
from static_trial import load_static_trial
_import_seconds = perf_counter() - _import_started


@dataclass
class CalibrationResult:
    calibration_path: Path
    parameters: dict
    values: dict
    warnings: list
    modeled_commands: list
    timings: dict
    qtm_errors: list

    @property
    def success(self):
        return not self.qtm_errors


def load_clinical_parameters(state):
    """Apply the original persisted/reviewed-parameter precedence and units."""
    inputs = populate_clinical_inputs(state)
    required = ('BodyMass', 'Height', 'ASISdist', 'LeftLegLength', 'RightLegLength',
                'LeftKneeWidth', 'RightKneeWidth', 'LeftAnkleWidth', 'RightAnkleWidth',
                'LeftASIStoGTdist', 'RightASIStoGTdist')
    for name in required:
        try:
            value = float(inputs[name])
        except (TypeError, ValueError) as error:
            raise ValueError(f"Missing or invalid clinical parameter: {name}") from error
        if not np.isfinite(value) or value < 0:
            raise ValueError(f"Invalid clinical parameter: {name}={inputs[name]!r}")
    try:
        frame = int(inputs['StaticFrameNumber'])
    except (ValueError, TypeError) as error:
        raise ValueError("Invalid static frame number") from error
    if not state['fields']['First Frame'] <= frame < state['fields']['Last Frame']:
        raise ValueError(f"Static frame {frame} is outside the captured range")
    for side in ('Left', 'Right'):
        if inputs[f'self.{side}FootModelCheck'] and not Path(state['SittingFootStaticDataFileName']).exists():
            for measure in ('HindfootVarus', 'CalcanealPitch', 'HindfootProgression', 'FirstMetatarsalPitch'):
                name = side + measure
                # Empty optional angles select the original marker-derived calculation.
                if measure != 'HindfootVarus' and inputs[name] == '':
                    continue
                try:
                    if not np.isfinite(float(inputs[name])):
                        raise ValueError(name)
                except (ValueError, TypeError) as error:
                    raise ValueError(f"Foot model requires a finite clinical parameter: {name}") from error
    state['inputs'] = inputs
    state['local_saved'] = getattr(state['self'], 'valueMeasurementUnits', '') == 'm'
    # The application already persists reviewed inputs. Preserve existing values
    # and types, as the original headless calculation did; initialize only new files.
    if not Path(state['StaticDataFileName']).exists():
        save_clinical_inputs(state)
    return inputs


def _command_collectors(commands):
    # Reuse the exact shared API payload builders without changing gapi globals.
    import gapi
    def collect(command, payload):
        commands.append((command, json.loads(payload)))
    namespace = dict(vars(gapi), grpc_send_command=collect)
    return {name: FunctionType(getattr(gapi, name).__code__, namespace, name,
                               getattr(gapi, name).__defaults__)
            for name in ('SetTrajectory', 'CreateModeledMarker')}


def write_qtm_outputs(commands, sender=None):
    """Use existing acknowledged gRPC commands; never claim an offline write."""
    if sender is None:
        from gapi import grpc_send_command
        sender = grpc_send_command
    for index, (command, payload) in enumerate(commands):
        try:
            response = sender(command, json.dumps(payload))
            if response is None:
                raise RuntimeError("QTM unavailable or command rejected")
        except Exception as error:
            return [{'command': command, 'index': index, 'message': str(error),
                     'remaining_commands': len(commands) - index}]
    return []


def _validate_calibration(path):
    owner = SimpleNamespace()
    exec(compile(path.read_text(encoding='utf8'), str(path), 'exec'), {'self': owner, 'np': np, 'array': np.array, 'nan': np.nan})
    matrices = [key for key in vars(owner) if key.endswith('AnatRelTech') or key.endswith('Anat2RelTech')]
    if not matrices:
        raise ValueError("Calibration has no transformation matrices")
    for name in matrices:
        value = np.asarray(getattr(owner, name))
        if value.shape != (3, 3) or not np.isfinite(value).all():
            raise ValueError(f"Invalid calibration matrix: {name}; check required marker data")
    return vars(owner)


def run_static_calibration(session_path, filename, testing_condition='BF', *, progress=print, qtm_sender=None, report_path=None):
    started = perf_counter()
    timings = {'engine_import': _import_seconds}
    commands = []
    warnings = []
    def stage(number, title, function, *args):
        progress(f'[STAGE {number}] {title}')
        began = perf_counter()
        try:
            return function(*args)
        except Exception as error:
            progress('[diagnostic] ' + json.dumps({'stage': title, 'error_type': type(error).__name__,
                                                  'message': str(error), 'warnings': list(dict.fromkeys(warnings))}))
            raise
        finally:
            timings[title] = perf_counter() - began
    fields = stage(1, 'C3D loading', load_static_trial, session_path, filename)
    subject = str(fields['Name'])
    for value, label in ((subject, 'subject name'), (testing_condition, 'testing condition')):
        if not value or any(char in value for char in ('/', '\\', '\x00')) or value in ('.', '..'):
            raise ValueError(f'Invalid {label} in calibration filename')
    session = Path(fields['Path'])
    calibration_dir = session / 'Calibration'
    calibration_dir.mkdir(exist_ok=True)
    if calibration_dir.resolve().parent != session:
        raise ValueError('Calibration directory resolves outside the selected session')
    name = f'Static_{testing_condition}_{subject}.py'
    destination = calibration_dir / name
    if not destination.exists() and (session / name).exists():
        destination = session / name
    if destination.is_symlink():
        raise ValueError('Calibration file must not redirect to another location')
    sitting_name = f'SittingFootStatic_{testing_condition}_{subject}.py'
    sitting = calibration_dir / sitting_name
    if not sitting.exists():
        sitting = session / sitting_name
    with tempfile.TemporaryDirectory(prefix='.static-', dir=destination.parent) as scratch:
        staging = Path(scratch) / name
        if destination.exists():
            shutil.copy2(destination, staging)
        state = {'self': SimpleNamespace(), 'fields': fields, 'SubjectName': subject,
                 'FilePath': str(session), 'FileName': fields['Filename'],
                 'StaticDataFileName': staging, 'SittingFootStaticDataFileName': sitting,
                 'TestingCondition': testing_condition, 'DefaultTestingCondition': 'BF',
                 'UserPreferencesFileName': Path(__file__).with_name('Py3_UserPreferences.py'),
                 'warnings': warnings, 'report': defaultdict(str)}
        state.update(_command_collectors(commands))
        stage(2, 'Clinical parameters', load_clinical_parameters, state)
        def calculate(function):
            state.update(function(state))
        stage(3, 'Marker QA', calculate, calculations.validate_static_markers)
        stage(4, 'Calibration markers', calculate, calculations.load_calibration_markers)
        stage(4, 'Joint centers and technical systems', calculate, calculations.compute_joint_centers_and_technical_systems)
        stage(4, 'Anatomical systems and foot', calculate, calculations.compute_anatomical_systems_and_foot)
        stage(4, 'Transformation matrices and posture', calculate, calculations.compute_transforms_and_posture)
        stage(5, 'Transformation saving', calculations.save_transformation_matrices, state)
        saved_parameters = _validate_calibration(staging)
        stage(6, 'Modeled marker generation', calculations.generate_modeled_markers, state)
        if report_path is not None:
            if Path(report_path).suffix.lower() != '.pdf':
                raise ValueError('Static report destination must have a .pdf extension')
            from static_calibration_report import save_calibration_report
            state.update(calculations.format_calibration_report(state))
            state['destination'] = str(report_path)
            from static_calibration_parameters import display_measurement_meters
            state['display_measurement_meters'] = display_measurement_meters
            stage(6, 'PDF rendering', save_calibration_report, state)
        os.replace(staging, destination)
    for warning in dict.fromkeys(warnings):
        progress('[warning] ' + warning)
    errors = stage(6, 'QTM communication', write_qtm_outputs, commands, qtm_sender)
    timings['total'] = perf_counter() - started
    state['StaticDataFileName'] = destination
    state.pop('SetTrajectory', None)
    state.pop('CreateModeledMarker', None)
    result = CalibrationResult(destination, saved_parameters, state, list(dict.fromkeys(warnings)), commands, timings, errors)
    if result.success:
        progress('[STAGE 7] Static calibration complete')
    progress('[timings] ' + json.dumps(timings, sort_keys=True))
    if errors:
        progress('[qtm_error] ' + json.dumps(errors))
        progress('[partial] Calibration saved; QTM modeled-marker output failed')
    return result
