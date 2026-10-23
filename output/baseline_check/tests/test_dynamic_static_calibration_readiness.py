"""Dynamic calibration detection in disposable sessions; no QTM/clinical jobs."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QMessageBox

from app.models.data_models import ProcessingStatus
from app.ui.pages.dynamic_analysis_page import DynamicAnalysisPage
from test_local_calibration_workflow import app, sessions, window, choose
from test_calibration_subfolder_validation import directory_link


VALID = '# Transformation Matrices\nself.valueEPelvisAnatRelTech = [[1,0,0],[0,1,0],[0,0,1]]\n'


def readiness(xml):
    return DynamicAnalysisPage._is_static_calibration_ready(SimpleNamespace(_session_path=str(xml)))


@pytest.mark.parametrize('subfolder', ['', 'Calibration'], ids=['session-root', 'calibration-subfolder'])
def test_valid_calibration_in_supported_locations(sessions, subfolder):
    folder = sessions[1].parent / subfolder
    folder.mkdir(exist_ok=True)
    (folder / 'Static_BF_B.py').write_text(VALID)
    assert readiness(sessions[1]) == (True, '')
    assert readiness(sessions[1].parent / '..' / sessions[1].parent.name / 'session.xml') == (True, '')


@pytest.mark.parametrize('content', ['', "self.valueBodyMass = '72'\n", '# Transformation Matrices\n',
                                     'self.valueEPelvisAnatRelTech = []\n'])
def test_incomplete_calibration_is_rejected(sessions, content):
    folder = sessions[1].parent / 'Calibration'
    folder.mkdir()
    (folder / 'Static_BF_B.py').write_text(content)
    ready, reason = readiness(sessions[1])
    assert not ready and 'transformation matrices are missing' in reason


def test_arbitrary_python_file_is_not_a_calibration(sessions):
    (sessions[1].parent / 'other.py').write_text(VALID)
    ready, reason = readiness(sessions[1])
    assert not ready and 'No Static calibration file' in reason


@pytest.mark.parametrize('foreign_session', ['patient-a', 'another-b-session'])
def test_other_sessions_are_not_searched(sessions, foreign_session):
    folder = (sessions[0].parent if foreign_session == 'patient-a' else sessions[1].parent.parent / 'another-session') / 'Calibration'
    folder.mkdir(parents=True)
    (folder / 'Static_BF_Other.py').write_text(VALID)
    assert not readiness(sessions[1])[0]


def test_linked_calibration_folder_cannot_use_another_patient(sessions):
    foreign = sessions[0].parent / 'Calibration'
    foreign.mkdir()
    (foreign / 'Static_BF_A.py').write_text(VALID)
    directory_link(sessions[1].parent / 'Calibration', foreign)
    assert not readiness(sessions[1])[0]


def test_linked_root_calibration_cannot_use_another_patient(sessions):
    foreign = sessions[0].parent / 'Static_BF_A.py'
    foreign.write_text(VALID)
    link = sessions[1].parent / foreign.name
    try:
        link.symlink_to(foreign)
    except OSError as error:
        pytest.skip(f'File symlink unavailable: {error}')
    assert not readiness(sessions[1])[0]


def test_valid_candidate_still_works_when_another_is_incomplete(sessions):
    folder = sessions[1].parent / 'Calibration'
    folder.mkdir()
    (folder / 'Static_BF_valid.py').write_text(VALID)
    (sessions[1].parent / 'Static_BF_incomplete.py').write_text('self.valueBodyMass = 72\n')
    assert readiness(sessions[1]) == (True, '')


def test_patient_switch_requires_current_calibration_and_allows_processing(window, sessions, monkeypatch):
    folder_a = sessions[0].parent / 'Calibration'
    folder_a.mkdir()
    (folder_a / 'Static_BF_A.py').write_text(VALID)
    choose(window, sessions[0])
    window._on_static_to_dynamic(str(sessions[0]), 'Static 3.qtm')
    dynamic = window._dynamic_page
    assert dynamic._is_static_calibration_ready() == (True, '')
    choose(window, sessions[1])
    assert dynamic._session_path == ''
    window._on_static_to_dynamic(str(sessions[1]), 'Static 3.qtm')
    assert Path(dynamic._session_path) == sessions[1]
    assert not dynamic._is_static_calibration_ready()[0]
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args[1:]))
    starts = []
    monkeypatch.setattr(dynamic, '_process_next_in_queue', lambda: starts.append(list(dynamic._processing_queue)))
    dynamic._opt_auto_events.setChecked(False)
    dynamic._on_process_clicked()
    assert warnings[0][0] == 'Static Calibration Required'
    assert 'No Static calibration file' in warnings[0][1]
    assert not starts
    folder_b = sessions[1].parent / 'Calibration'
    folder_b.mkdir()
    (folder_b / 'Static_BF_B.py').write_text(VALID)
    dynamic._on_process_clicked()
    assert len(warnings) == 1
    assert starts == [[('dynamic', 'Dynamic 1.qtm')]]


@pytest.mark.parametrize('location,completed,success', [('', True, True), ('GCD', True, True),
                                                       (None, True, False), ('', False, False)],
                         ids=['root-success', 'gcd-subfolder-success', 'missing-gcd', 'failed-status'])
def test_trial_completion_checks_gcd_and_schedules_next(window, sessions, monkeypatch, location, completed, success):
    dynamic = window._dynamic_page
    dynamic.load_session(str(sessions[1]))
    root_gcd = sessions[1].parent / 'Dynamic 1.GCD'
    if location == 'GCD':
        folder = sessions[1].parent / 'GCD'
        folder.mkdir()
        root_gcd.rename(folder / root_gcd.name)
    elif location is None:
        root_gcd.unlink()  # Disposable fixture only.
    dynamic._current_processing_file = 'Dynamic 1.qtm'
    dynamic._current_task_type = 'dynamic'
    scheduled = []
    monkeypatch.setattr(dynamic, '_schedule', lambda delay, callback: scheduled.append((delay, callback)))
    finished_slot = dynamic._processing_slots[2][1]
    finished_slot(ProcessingStatus(step='complete' if completed else 'error', completed=completed))
    assert dynamic._trial_rows['Dynamic 1.qtm']._status == ('COMPLETE' if success else 'ERROR')
    assert dynamic._processed_success_count == int(success)
    assert dynamic._processed_error_count == int(not success)
    assert dynamic._failed_trials == ([] if success else ['Dynamic 1.qtm'])
    assert scheduled == [(400, dynamic._process_next_in_queue)]
