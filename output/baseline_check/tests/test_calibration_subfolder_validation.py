"""Real local saves and ownership boundaries in disposable session folders."""
import os
from pathlib import Path
import subprocess

import pytest
from PySide6.QtTest import QTest

from app.models.data_models import ProcessingStatus
from app.ui.pages.static_analysis_page import StaticAnalysisPage
from test_local_calibration_workflow import app, sessions, local_page, config


@pytest.mark.parametrize('subfolder', ['', 'Calibration'], ids=['session-root', 'calibration-subfolder'])
def test_b_save_after_processing_persists_and_reloads(local_page, sessions, app, monkeypatch, subfolder):
    local_page._on_save_clicked()
    saved_a = Path(local_page._loaded_py_path)
    saved_a_bytes = saved_a.read_bytes()
    xml_bytes = [xml.read_bytes() for xml in sessions]
    destination = sessions[1].parent / subfolder
    destination.mkdir(exist_ok=True)
    local_page.set_session(str(sessions[1]))
    runs = []
    monkeypatch.setattr(local_page._service, 'process_static', lambda *args, **kw: runs.append(args))
    local_page._on_run_clicked()
    assert runs and Path(runs[0][0]) == sessions[1]
    local_page._on_finished(ProcessingStatus(step='complete', completed=True))
    QTest.qWait(350)
    assert local_page._stack.currentWidget() is local_page._completion_widget
    saved_b = Path(local_page._loaded_py_path)
    assert saved_b.parent == destination
    local_page._body_mass.setText('72.125')
    local_page._on_save_clicked()
    assert local_page._config_status.text() == 'Parameters saved successfully.'
    assert config(saved_b).valueBodyMass == '72.125'
    assert config(saved_b).valuePatientNumber == 'B'
    assert config(saved_b).valueMeasurementUnits == 'm'
    fresh = StaticAnalysisPage()
    try:
        fresh.set_session(str(sessions[1]))
        assert Path(fresh._loaded_py_path) == saved_b
        assert fresh._body_mass.text() == '72.125' and fresh._patient_number.text() == 'B'
        fresh._on_save_clicked()
        assert fresh._config_status.text() == 'Parameters saved successfully.'
    finally:
        fresh.close()
    assert saved_a.read_bytes() == saved_a_bytes
    assert [xml.read_bytes() for xml in sessions] == xml_bytes


def test_condition_change_can_reuse_current_session_calibration(local_page, sessions):
    destination = sessions[1].parent / 'Calibration'
    destination.mkdir()
    local_page.set_session(str(sessions[1]))
    local_page._on_save_clicked()
    original = Path(local_page._loaded_py_path)
    tail = '# Transformation Matrices\nself.preserved_matrix = [[1, 0], [0, 1]]\n'
    original.write_text(original.read_text() + tail)
    local_page._trial_modifier.addItem('Alternate')
    local_page._trial_modifier.setCurrentText('Alternate')
    local_page._on_save_clicked()
    assert local_page._config_status.text() == 'Parameters saved successfully.'
    assert Path(local_page._loaded_py_path) != original
    assert Path(local_page._loaded_py_path).read_text().endswith(tail)


@pytest.mark.parametrize('source', ['other-patient', 'other-session', 'arbitrary-child', 'prefix-sibling', 'traversal'])
def test_foreign_calibration_source_is_rejected(local_page, sessions, source):
    session = sessions[1].parent
    folders = {
        'other-patient': sessions[0].parent / 'Calibration',
        'other-session': session.parent / 'another-session' / 'Calibration',
        'arbitrary-child': session / 'NotCalibration',
        'prefix-sibling': session.with_name(session.name + '-other') / 'Calibration',
        'traversal': session / '..' / 'another-session' / 'Calibration',
    }
    foreign = folders[source] / 'Static_BF_Same name.py'
    foreign.parent.mkdir(parents=True, exist_ok=True)
    foreign.write_text("self.valueBodyMass = '99'\n")
    before = foreign.read_bytes()
    local_page.set_session(str(sessions[1]))
    local_page._loaded_py_path = str(foreign)
    local_page._on_save_clicked()
    assert 'Loaded calibration belongs to a different session.' in local_page._config_status.text()
    assert foreign.read_bytes() == before
    assert not list(session.glob('Static_*.py'))


def directory_link(link, target):
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        if os.name != 'nt':
            raise
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
    assert link.resolve() == target.resolve()


@pytest.mark.parametrize('destination_link', [False, True], ids=['linked-source', 'linked-calibration-destination'])
@pytest.mark.parametrize('existing_target', [False, True], ids=['new-file', 'existing-file'])
def test_directory_link_cannot_escape_session(local_page, sessions, destination_link, existing_target):
    local_page.set_session(str(sessions[1]))
    foreign_dir = sessions[0].parent / 'Calibration'
    foreign_dir.mkdir()
    foreign = foreign_dir / 'Static_BF_Same name.py'
    (foreign_dir / 'sentinel.txt').write_bytes(b'unchanged')
    if existing_target:
        foreign.write_text("self.valueBodyMass = '99'\n")
    before = {path.name: path.read_bytes() for path in foreign_dir.iterdir()}
    link = sessions[1].parent / ('Calibration' if destination_link else 'Alias')
    directory_link(link, foreign_dir)
    if not destination_link:
        local_page._loaded_py_path = str(link / foreign.name)
    local_page._on_save_clicked()
    expected = 'calibration destination is outside this session.' if destination_link else 'Loaded calibration belongs to a different session.'
    assert expected in local_page._config_status.text()
    assert {path.name: path.read_bytes() for path in foreign_dir.iterdir()} == before
    assert not list(sessions[1].parent.glob('Static_*.py'))


@pytest.mark.parametrize('field', ['Sex', 'DOB'])
def test_existing_patient_metadata_validation_remains(local_page, sessions, field):
    (sessions[1].parent / 'Calibration').mkdir()
    local_page.set_session(str(sessions[1]))
    if field == 'Sex':
        local_page._sex.addItem('Invalid')
        local_page._sex.setCurrentText('Invalid')
    else:
        local_page._dob_month.setCurrentIndex(-1)
    local_page._on_save_clicked()
    assert 'Parameters not saved' in local_page._config_status.text()
    assert field in local_page._config_status.text()
    assert not list((sessions[1].parent / 'Calibration').glob('Static_*.py'))
