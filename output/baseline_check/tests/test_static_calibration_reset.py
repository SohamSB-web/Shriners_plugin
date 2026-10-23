"""Calibration reset isolation using disposable sessions and no QTM calls."""
from pathlib import Path
import os

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog

from app.models.data_models import ProcessingStatus
from test_local_calibration_workflow import app, sessions, window, choose, config


def test_patient_reset_discards_calibration_request_caches(window, sessions, app, monkeypatch):
    static = window._static_page
    monkeypatch.setattr(static, '_sync_fields_to_xml_and_qtm', lambda *args: None)
    runs = []
    monkeypatch.setattr(static._service, 'process_static', lambda *args, **kw: runs.append(args))
    choose(window, sessions[0])
    static.set_session(str(sessions[0]))
    static._on_run_clicked()
    static._on_finished(ProcessingStatus(step='complete', completed=True))
    QTest.qWait(350)
    assert static._stack.currentWidget() is static._completion_widget
    saved_a = Path(static._loaded_py_path)
    saved_a_bytes = saved_a.read_bytes()
    xml_bytes = [xml.read_bytes() for xml in sessions]
    monkeypatch.setattr(static._anthro_sync, 'request', lambda *args: False)
    static._start_manual_sync()
    assert static._manual_requested_identity['session_xml'] == str(sessions[0])
    assert static._manual_inflight_values and static._anthro_inflight_revisions
    static._on_anthro_edited('BodyMass')
    assert static._auto_sync_timer.isActive()
    old_generation = static._anthro_generation
    old_finished = static._processing_slots[2][1]

    choose(window, sessions[1])
    assert window._active_analysis_context == (
        os.path.normcase(str(sessions[1].parent.parent.resolve())),
        os.path.normcase(str(sessions[1].parent.resolve())),
    )
    assert static._file_path_edit.text() == ''
    assert static._session_path == static._filename == static._loaded_py_path == static._subject_name == ''
    assert static._anthro_context is None
    assert static._manual_requested_identity == static._manual_inflight_values == static._anthro_inflight_revisions == {}
    assert not static._auto_sync_timer.isActive()
    assert not static._anthro_dirty and not static._manual_baseline and not static._manual_local_dirty
    assert not static._anthro_connected and static._anthro_sync.operation is None
    old_finished(ProcessingStatus(step='complete', completed=True))
    static._on_anthro_sync_finished({'generation': old_generation, 'snapshot': None})
    app.processEvents()
    assert static._stack.currentWidget() is static._config_widget
    assert static._comp_patient_lbl.text() == '' and static._progress_bar.value() == 0
    assert not static._save_btn.isEnabled() and static._browse_btn.isEnabled()
    static._on_save_clicked()
    assert static._config_status.text() == 'Select a valid calibration XML before saving.'
    assert not list(sessions[1].parent.glob('Static_*.py'))

    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: (str(sessions[1]), 'XML Files (*.xml)'))
    static._browse_btn.click()
    assert Path(static._file_path_edit.text()) == sessions[1]
    assert static._patient_number.text() == 'B'
    static._body_mass.setText('72')
    static._on_run_clicked()
    assert [Path(args[0]) for args in runs] == sessions
    static._on_finished(ProcessingStatus(step='complete', completed=True))
    QTest.qWait(350)
    assert static._stack.currentWidget() is static._completion_widget
    static._on_save_clicked()
    assert static._config_status.text() == 'Parameters saved successfully.'
    assert config(static._loaded_py_path).valueBodyMass == '72'
    assert Path(static._loaded_py_path).parent == sessions[1].parent
    assert saved_a.read_bytes() == saved_a_bytes
    assert [xml.read_bytes() for xml in sessions] == xml_bytes
    generation = static._analysis_generation
    choose(window, sessions[1])
    for page in ('patients', 'case_presentation', 'static_analysis'):
        window._navigate_to(page)
    assert static._analysis_generation == generation
    assert Path(static._session_path) == sessions[1]
