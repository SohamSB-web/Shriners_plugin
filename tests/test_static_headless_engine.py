"""Focused static refactor checks; all clinical runs use disposable copies."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'Gait-lab-Vicon-to-QTM'
sys.path.insert(0, str(BACKEND))
import static_calibration_engine as engine
import static_calibration_calculations as calculations
import static_trial


@pytest.fixture
def clinical_copy(tmp_path):
    source = os.environ.get('STATIC_REFERENCE_SESSION')
    if not source:
        pytest.skip('Set STATIC_REFERENCE_SESSION to a representative session; original files remain read-only')
    source = Path(source)
    trial = os.environ.get('STATIC_REFERENCE_FILENAME', 'Static 3.qtm')
    folder = tmp_path / 'session'
    folder.mkdir()
    (folder / '.static-refactor-disposable').touch()
    for path in source.iterdir():
        if path.name in ('session.xml', trial.split('.')[0] + '.c3d') or path.name.startswith(('Static_', 'SittingFootStatic_')) and path.suffix == '.py':
            shutil.copy2(path, folder / path.name)
    if (source / 'Calibration').is_dir():
        shutil.copytree(source / 'Calibration', folder / 'Calibration')
    return folder, trial


def hashes(folder):
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file() and p.suffix in ('.c3d', '.xml', '.qtm')}


def run_probe(mode, folder, trial, output):
    proc = subprocess.run([sys.executable, '-B', str(ROOT / 'tests/static_calibration_probe.py'),
                           mode, str(folder / 'session.xml'), trial, str(output)],
                          capture_output=True, text=True, timeout=90, cwd=ROOT,
                          env=dict(os.environ, QT_QPA_PLATFORM='offscreen'))
    assert proc.returncode == 0, proc.stdout[-1200:] + proc.stderr[-2000:]
    return json.loads(output.read_text(encoding='utf8'))


def calibration_parameters(text):
    result = SimpleNamespace()
    exec(text, {'self': result, 'np': np, 'array': np.array, 'nan': np.nan})
    return vars(result)


def test_no_gui_dependency_even_during_engine_import():
    code = """
import builtins,sys
real = builtins.__import__
def guarded(name,*a,**kw):
    if name.startswith(('PySide6','tkinter','pyside6_compat')):
        raise AssertionError('GUI import: '+name)
    return real(name,*a,**kw)
builtins.__import__=guarded
sys.path.insert(0,sys.argv[1])
import static_calibration_engine
"""
    proc = subprocess.run([sys.executable, '-B', '-c', code, str(BACKEND)], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr


def test_static_loader_rejects_ambiguous_measurement_and_path_escape(tmp_path):
    xml = tmp_path/'session.xml'
    xml.write_text('<Session><Measurement Filename="Static.qtm"/><Measurement Filename="Static.qtm"/></Session>')
    with pytest.raises(ValueError, match='found 2'):
        static_trial.load_static_trial(xml, 'Static.qtm')
    with pytest.raises(ValueError, match='within the selected session'):
        static_trial.load_static_trial(xml, '../Static.qtm')


def test_saved_matrix_validation_checks_dimensions_and_finite_values(tmp_path):
    path = tmp_path/'Static_BF_Test.py'
    path.write_text('self.valueLeftEThighAnatRelTech = np.ones((2, 3))\n')
    with pytest.raises(ValueError, match='Invalid calibration matrix'):
        engine._validate_calibration(path)
    path.write_text('self.valueLeftEThighAnatRelTech = np.full((3, 3), np.nan)\n')
    with pytest.raises(ValueError, match='Invalid calibration matrix'):
        engine._validate_calibration(path)


def test_original_math_calls_preserved_including_optional_foot_branches():
    source = subprocess.check_output(['git', 'show', 'e6b06a1:Gait-lab-Vicon-to-QTM/Py3_StaticMain.py'], cwd=ROOT).decode('utf8')
    tree = ast.parse(source)
    intervals = [(1314, 2480), (2739, 4099), (5480, 6416)]
    def calls(tree, intervals=None):
        selected = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id in ('math', 'gait'):
                if intervals is None or any(start <= node.lineno <= end for start, end in intervals):
                    selected.append(ast.dump(node, include_attributes=False))
        return sorted(selected)
    assert calls(tree, intervals) == calls(ast.parse(Path(calculations.__file__).read_text(encoding='utf8')))


def test_static_loader_matches_original_point_and_metadata_values(clinical_copy, monkeypatch):
    folder, trial = clinical_copy
    import Py3_varExtractor as legacy
    monkeypatch.setattr(legacy, 'ProcessForceplateData', lambda reader: {})
    expected = legacy.extract_fields_by_filename(str(folder / 'session.xml'), trial, True)
    actual = static_trial.load_static_trial(folder / 'session.xml', trial)
    assert actual.keys() == expected.keys() - {'FP'}
    for key in actual:
        if isinstance(actual[key], dict):
            for axis in actual[key]:
                np.testing.assert_array_equal(actual[key][axis], expected[key][axis])
        else:
            assert actual[key] == expected[key]


def test_clinical_equivalence_and_modeled_marker_payloads(clinical_copy, tmp_path):
    folder, trial = clinical_copy
    before = hashes(folder)
    legacy_folder = tmp_path / 'legacy'
    normalized_folder = tmp_path / 'legacy-normalized'
    shutil.copytree(folder, legacy_folder)
    shutil.copytree(folder, normalized_folder)
    legacy = run_probe('legacy', legacy_folder, trial, tmp_path / 'legacy.json')
    reference = run_probe('legacy-normalized', normalized_folder, trial, tmp_path / 'reference.json')
    actual = run_probe('engine', folder, trial, tmp_path / 'engine.json')
    compared = 0
    for key, value in legacy['values'].items():
        if key not in actual['values']:
            continue
        try:
            array = np.asarray(value, dtype=float)
        except (TypeError, ValueError):
            continue
        np.testing.assert_allclose(actual['values'][key], array, rtol=1e-12, atol=1e-10, equal_nan=True, err_msg=key)
        compared += 1
    assert compared >= 100
    expected = calibration_parameters(legacy['saved'])
    observed = calibration_parameters(actual['saved'])
    assert expected.keys() == observed.keys()
    for key, value in expected.items():
        if isinstance(value, np.ndarray):
            np.testing.assert_allclose(observed[key], value, rtol=1e-12, atol=1e-10, err_msg=key)
        else:
            assert observed[key] == value, key
    assert reference['marker_error'] is None
    assert len(reference['commands']) == len(actual['commands']) > 0
    for expected_command, actual_command in zip(reference['commands'], actual['commands']):
        assert actual_command[0] == expected_command[0]
        assert actual_command[1].keys() == expected_command[1].keys()
        for key, value in expected_command[1].items():
            if isinstance(value, list):
                np.testing.assert_allclose(actual_command[1][key], value, rtol=1e-12, atol=1e-10, equal_nan=True)
            else:
                assert actual_command[1][key] == value
    assert hashes(folder) == before


def test_qtm_failure_is_partial_success_and_pdf_remains_headless(clinical_copy, tmp_path):
    folder, trial = clinical_copy
    before = hashes(folder)
    result = engine.run_static_calibration(folder / 'session.xml', trial, qtm_sender=lambda *args: None,
                                         report_path=tmp_path / 'report.pdf')
    assert not result.success and result.qtm_errors[0]['remaining_commands'] > 0
    assert result.calibration_path.exists()
    assert (tmp_path / 'report.pdf').read_bytes().startswith(b'%PDF')
    assert hashes(folder) == before
    assert result.values['self'].__class__ is SimpleNamespace


def test_legacy_root_calibration_stays_compatible(clinical_copy):
    folder, trial = clinical_copy
    modern = next((folder/'Calibration').glob('Static_BF_*.py'))
    legacy = folder/modern.name
    shutil.copy2(modern, legacy)
    modern.unlink()  # Only this test's disposable copy.
    result = engine.run_static_calibration(folder/'session.xml', trial, qtm_sender=lambda *a: 'acknowledged')
    assert result.success and result.calibration_path == legacy
    assert not modern.exists()
    loaded = calibration_parameters(legacy.read_text(encoding='utf8'))
    assert loaded['valueLeftEThighAnatRelTech'].shape == (3, 3)


@pytest.mark.parametrize('stage', ['compute_joint_centers_and_technical_systems', 'generate_modeled_markers'])
def test_failed_calculation_does_not_replace_existing_calibration(clinical_copy, monkeypatch, stage):
    folder, trial = clinical_copy
    before = {p: p.read_bytes() for p in folder.rglob('Static_*.py')}
    def fail(state):
        raise RuntimeError('deliberate isolated computation failure')
    monkeypatch.setattr(calculations, stage, fail)
    with pytest.raises(RuntimeError, match='deliberate'):
        engine.run_static_calibration(folder / 'session.xml', trial, qtm_sender=lambda *a: pytest.fail('No writes before computation succeeds'))
    assert {p: p.read_bytes() for p in folder.rglob('Static_*.py')} == before
    assert not [p for p in folder.rglob('.static-*') if p.is_dir()]


@pytest.mark.parametrize('value', ['', 'abc', 'nan', '-1'])
def test_invalid_clinical_values_are_not_defaulted_or_saved(monkeypatch, value):
    inputs = {name: '1' for name in ('BodyMass', 'Height', 'ASISdist', 'LeftLegLength', 'RightLegLength',
              'LeftKneeWidth', 'RightKneeWidth', 'LeftAnkleWidth', 'RightAnkleWidth', 'LeftASIStoGTdist', 'RightASIStoGTdist')}
    inputs['BodyMass'] = value
    monkeypatch.setattr(engine, 'populate_clinical_inputs', lambda state: inputs)
    monkeypatch.setattr(engine, 'save_clinical_inputs', lambda state: pytest.fail('Invalid parameters must not be saved'))
    with pytest.raises(ValueError, match='clinical parameter'):
        engine.load_clinical_parameters({})


def test_missing_required_markers_fail_without_overwriting_calibration(clinical_copy, monkeypatch):
    folder, trial = clinical_copy
    original_loader = engine.load_static_trial
    def missing(*args):
        data = original_loader(*args)
        return {key: value for key, value in data.items() if not isinstance(value, dict)}
    monkeypatch.setattr(engine, 'load_static_trial', missing)
    before = {p: p.read_bytes() for p in folder.rglob('Static_*.py')}
    with pytest.raises((ValueError, UnboundLocalError, ZeroDivisionError)):
        engine.run_static_calibration(folder / 'session.xml', trial, qtm_sender=lambda *a: pytest.fail('No QTM writes'))
    assert {p: p.read_bytes() for p in folder.rglob('Static_*.py')} == before


def test_missing_optional_trunk_markers_keep_the_existing_fallback(clinical_copy, tmp_path, monkeypatch):
    folder, trial = clinical_copy
    loader = engine.load_static_trial
    def without_trunk(*args):
        data = loader(*args)
        for name in ('C7', 'Left_Clavicle', 'Right_Clavicle'):
            data.pop(name, None)
        return data
    monkeypatch.setattr(engine, 'load_static_trial', without_trunk)
    result = engine.run_static_calibration(folder/'session.xml', trial, qtm_sender=lambda *a:'acknowledged',
                                         report_path=tmp_path/'optional-markers.pdf')
    assert result.success and result.values['TrunkFlag'] == 0
    assert result.values['report']['LeftTrunkTilt'] == ''


def test_command_payload_builders_and_partial_acknowledgements():
    commands = []
    api = engine._command_collectors(commands)
    api['CreateModeledMarker']('TEST')
    api['SetTrajectory']('TEST', [1, 2], [3, 4], [5, 6], [True, False], 0, 2, 19)
    assert commands[1][1] == {'name': 'TEST', 'X': [1., 2.], 'Y': [3., 4.], 'Z': [5., 6.],
                              'exists': [True, False], 'source_start': 19}
    replies = iter(['acknowledged', None])
    errors = engine.write_qtm_outputs(commands, lambda *a: next(replies))
    assert errors[0]['index'] == 1 and errors[0]['remaining_commands'] == 1
    assert not engine.write_qtm_outputs(commands, lambda *a: 'acknowledged')


@pytest.mark.parametrize('side', ['Left', 'Right'])
def test_optional_foot_angles_remain_empty_for_marker_derived_calculations(monkeypatch, tmp_path, side):
    inputs = {name: '1' for name in ('BodyMass', 'Height', 'ASISdist', 'LeftLegLength', 'RightLegLength',
              'LeftKneeWidth', 'RightKneeWidth', 'LeftAnkleWidth', 'RightAnkleWidth', 'LeftASIStoGTdist', 'RightASIStoGTdist')}
    inputs.update({'StaticFrameNumber': '20', 'self.LeftFootModelCheck': int(side == 'Left'),
                   'self.RightFootModelCheck': int(side == 'Right'), side+'HindfootVarus': '0',
                   side+'CalcanealPitch': '', side+'HindfootProgression': '', side+'FirstMetatarsalPitch': ''})
    monkeypatch.setattr(engine, 'populate_clinical_inputs', lambda state: inputs)
    monkeypatch.setattr(engine, 'save_clinical_inputs', lambda state: None)
    state = {'self': SimpleNamespace(), 'fields': {'First Frame': 0, 'Last Frame': 100},
             'SittingFootStaticDataFileName': tmp_path/'missing.py', 'StaticDataFileName': tmp_path/'new.py'}
    assert engine.load_clinical_parameters(state)[side+'FirstMetatarsalPitch'] == ''


@pytest.mark.parametrize('success, expected', [(True, 0), (False, 2)])
def test_cli_returns_complete_or_partial_status(monkeypatch, success, expected):
    spec = importlib.util.spec_from_file_location('static_entry', BACKEND / 'Py3_StaticMain.py')
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    monkeypatch.setattr(engine, 'run_static_calibration', lambda *a, **kw: SimpleNamespace(success=success))
    assert entry.main(['--headless', '-s', 'session.xml', '-f', 'Static.qtm', '-t', 'BF']) == expected


def test_existing_processing_service_keeps_ui_responsive(clinical_copy, tmp_path, monkeypatch):
    """Run the actual service/subprocess interface with acknowledgements isolated from QTM."""
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication
    from app.services import processing_service
    app = QApplication.instance() or QApplication([])
    wrapper = tmp_path / 'Py3_StaticMain.py'
    wrapper.write_text(f'''import sys,runpy,builtins
real_import=builtins.__import__
def guarded(name,*a,**kw):
    if name.startswith(('PySide6','tkinter','pyside6_compat')):
        raise AssertionError('GUI import in backend: '+name)
    return real_import(name,*a,**kw)
builtins.__import__=guarded
sys.path.insert(0,{str(BACKEND)!r})
import static_calibration_engine as engine
original=engine.run_static_calibration
def offline(*a,**kw):
    return original(*a,**dict(kw,qtm_sender=lambda *a:'offline regression acknowledgement'))
engine.run_static_calibration=offline
runpy.run_path({str(BACKEND/'Py3_StaticMain.py')!r},run_name='__main__')
''', encoding='utf8')
    monkeypatch.setattr(processing_service, '_GAIT_DIR', tmp_path)
    monkeypatch.setattr(processing_service, '_resolve_python_launcher', lambda env: [sys.executable])
    service = processing_service.GaitProcessingService()
    results, logs, ticks = [], [], []
    service.processing_finished.connect(results.append)
    service.processing_log.connect(logs.append)
    loop = QEventLoop()
    heartbeat = QTimer()
    heartbeat.setInterval(20)
    def tick():
        ticks.append(1)
        if results and service._thread is None:
            loop.quit()
    heartbeat.timeout.connect(tick)
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    heartbeat.start()
    timeout.start(20000)
    folder, trial = clinical_copy
    service.process_static(str(folder/'session.xml'), trial, 'BF')
    loop.exec()
    heartbeat.stop()
    timeout.stop()
    if not results:
        service.cancel()
    assert results and results[0].completed, logs[-20:]
    assert len(ticks) >= 3
    assert all(any(f'[STAGE {stage}]' in line for line in logs) for stage in range(1,8))
