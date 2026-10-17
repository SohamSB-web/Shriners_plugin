"""Local calibration persistence and patient isolation; no clinical project writes."""
import ast
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import subprocess
import time
from unittest.mock import Mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pytest
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget, QFileDialog, QMessageBox
from app.models.data_models import AppSettings, ProcessingStatus
from app.services import processing_service
from app.services.anthropometric_sync_service import QtmAnthropometricClient, validate_parameter
from app.ui.pages.static_analysis_page import StaticAnalysisPage
from app.ui.pages.dynamic_analysis_page import DynamicAnalysisPage
from test_anthropometric_sync import VALUES, app, paf, page, idle, wait_for

@pytest.fixture
def sessions(tmp_path):
    paths = []
    for patient in ['A', 'B']:
        folder = tmp_path / patient / '2026-10-01_2'
        folder.mkdir(parents=True)
        fields = {'Name': 'Same name', 'ID': patient, 'DOB': '2000-01-01', 'Sex': 'Female', **VALUES}
        xml = folder / 'session.xml'
        xml.write_text('<Session><Fields>' + ''.join(f'<{k}>{v}</{k}>' for k,v in fields.items()) +
                       '</Fields><Measurement Filename="Static 3.qtm"><Fields/></Measurement></Session>')
        (folder / 'Static 3.qtm').touch()
        (folder / 'Dynamic 1.qtm').touch()
        (folder / 'Dynamic 1.GCD').write_bytes(b'existing saved results ' + patient.encode())
        paths.append(xml)
    return paths

@pytest.fixture
def local_page(app, sessions, monkeypatch):
    widget = StaticAnalysisPage()
    widget.set_session(str(sessions[0]))
    monkeypatch.setattr('urllib.request.urlopen', lambda *a, **k: pytest.fail('Local save must not contact QTM'))
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()

def config(path):
    owner = SimpleNamespace()
    exec(Path(path).read_text(encoding='utf8'), {'self': owner})
    return owner

@pytest.mark.parametrize('name', list(VALUES))
def test_every_local_parameter_survives_reopen_without_qtm(local_page, sessions, name):
    local_page._anthro_widgets[name].setText('123.123456789012345')
    local_page._first_name.setText("O'Neil")
    local_page._last_name.setText('Last')
    local_page._patient_number.setText('edited-id')
    local_page._on_save_clicked()
    assert local_page._config_status.text() == 'Parameters saved successfully.'
    saved = Path(local_page._loaded_py_path)
    assert saved.parent == sessions[0].parent
    assert saved.name == 'Static_BF_Same name.py'  # Display name edits do not redirect the file identity.
    assert not list(sessions[1].parent.glob('Static_*.py'))
    fresh = StaticAnalysisPage()
    try:
        assert fresh._session_path == ''
        fresh.set_session(str(sessions[0]))
        assert fresh._anthro_widgets[name].text() == '123.123456789012345'
        assert fresh._first_name.text() == "O'Neil"
        assert fresh._last_name.text() == 'Last'
        assert fresh._patient_number.text() == 'edited-id'
    finally:
        fresh.close()

@pytest.mark.parametrize('value', ['-1', '0', '251', '.16', '12.34567890123456', '1e100', '1e-320'])
def test_unusual_representable_values_are_saved_exactly(local_page, value):
    local_page._height.setText(value)
    local_page._on_save_clicked()
    assert local_page._config_status.text() == 'Parameters saved successfully.'
    assert config(local_page._loaded_py_path).valueHeight == value
    xml = local_page._session_path
    local_page.clear_session()
    local_page.set_session(xml)
    assert local_page._height.text() == value

@pytest.mark.parametrize('value', ['', 'bad', 'nan', 'inf', '-inf', '1e309', '1e-999'])
def test_invalid_numeric_save_is_reported_without_zero_or_partial_file(local_page, value):
    local_page._height.setText(value)
    local_page._on_save_clicked()
    assert 'Parameters not saved' in local_page._config_status.text()
    assert local_page._height.text() == value
    assert local_page._loaded_py_path == ''
    assert not list(Path(local_page._session_path).parent.glob('Static_*.py'))

def test_atomic_save_failure_preserves_original_and_dirty_draft(local_page, monkeypatch):
    local_page._on_save_clicked()
    saved = Path(local_page._loaded_py_path)
    original = saved.read_bytes()
    local_page._body_mass.setText('72')
    local_page._body_mass.textEdited.emit('72')
    class FailedFile:
        def __init__(self, path): pass
        def open(self, mode): return True
        def write(self, data): return len(data)
        def commit(self): return False
        def errorString(self): return 'simulated disk failure'
    monkeypatch.setattr('app.ui.pages.static_analysis_page.QSaveFile', FailedFile)
    local_page._on_save_clicked()
    assert saved.read_bytes() == original
    assert 'simulated disk failure' in local_page._config_status.text()
    assert 'BodyMass' in local_page._anthro_dirty

def test_local_save_preserves_xml_qpr_other_patient_and_transformation_tail(local_page, sessions):
    folder = sessions[0].parent
    qpr = folder / 'data.qpr'
    qpr.write_bytes(b'opaque QTM data')
    source = folder / 'Static_BF_Same name.py'
    tail = '# Transformation Matrices\nself.valueEPelvisAnatRelTech = [[1,0,0],[0,1,0],[0,0,1]]\n'
    source.write_text("self.MarkerDiameter = 18\nself.valueFirstName = 'Same name'\n" + tail)
    local_page._loaded_py_path = str(source)
    before = {p:p.read_bytes() for p in [sessions[0], sessions[1], qpr, sessions[1].parent / 'Dynamic 1.GCD']}
    local_page._body_mass.setText('72.1234567890123')
    local_page._on_save_clicked()
    assert source.read_text().endswith(tail)
    assert config(source).valueBodyMass == '72.1234567890123'
    assert all(p.read_bytes() == data for p,data in before.items())
    local_page._on_save_clicked()
    assert local_page._config_status.text() == 'Parameters saved successfully.'

def test_local_calibration_persists_across_a_fresh_process(local_page):
    local_page._body_mass.setText('88.1234567890123')
    local_page._on_save_clicked()
    script = '''import json, sys
from PySide6.QtWidgets import QApplication
from app.ui.pages.static_analysis_page import StaticAnalysisPage
app=QApplication([])
page=StaticAnalysisPage()
assert page._session_path == "" and page._body_mass.text() == ""
page.set_session(sys.argv[1])
print(json.dumps({"mass": page._body_mass.text(), "path": page._session_path}))
page.close()
'''
    result = subprocess.run([sys.executable, '-c', script, local_page._session_path], cwd=ROOT,
                            env=dict(os.environ), text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['mass'] == '88.1234567890123'

def test_blank_patient_values_remain_blank_after_local_reopen(local_page):
    local_page._first_name.clear()
    local_page._patient_number.clear()
    local_page._sex.setCurrentIndex(-1)
    for widget in local_page._patient_widgets['DOB']:
        widget.setCurrentIndex(-1)
    local_page._on_save_clicked()
    assert local_page._config_status.text() == 'Parameters saved successfully.'
    xml = local_page._session_path
    local_page.clear_session()
    local_page.set_session(xml)
    assert local_page._first_name.text() == local_page._patient_number.text() == ''
    assert local_page._sex.currentIndex() == -1
    assert all(widget.currentIndex() == -1 for widget in local_page._patient_widgets['DOB'])

def test_invalid_typed_xml_path_cannot_save_previous_session(local_page):
    local_page._file_path_edit.setText(str(Path(local_page._session_path).with_suffix('.c3d')))
    local_page._on_save_clicked()
    assert 'Parameters not saved' in local_page._config_status.text()
    assert local_page._loaded_py_path == ''

def test_units_conversion_overflow_is_rejected_without_clinical_range():
    assert validate_parameter('BodyMass', '1e308') == 1e308
    with pytest.raises(ValueError, match='millimetres'):
        validate_parameter('Height', '1e308')

def test_old_fetch_completion_does_not_release_new_request(app, paf, page):
    old_generation = page._anthro_generation
    page.set_session(str(paf.other))
    operation = object()
    page._anthro_sync.operation = operation
    page._save_btn.setEnabled(False)
    page._on_anthro_sync_finished({'generation': old_generation, 'snapshot': None})
    assert page._anthro_sync.operation is operation
    assert not page._save_btn.isEnabled()
    page._anthro_sync.operation = None

def test_fetch_remains_read_only_after_local_save(app, paf, page):
    page._body_mass.setText('72')
    before = dict(paf.nodes['session-a']['Fields'])
    page._on_save_clicked()
    assert paf.nodes['session-a']['Fields'] == before and paf.puts == []
    assert config(page._loaded_py_path).valueBodyMass == '72'
    page._on_fetch_clicked()
    idle(app, page)
    assert float(page._body_mass.text()) == before['BodyMass']
    assert config(page._loaded_py_path).valueBodyMass == '72'
    assert paf.puts == []

def test_save_works_offline_and_with_duplicated_qtm_ids(app, paf, page):
    paf.fail = True
    paf.nodes['session-b']['ID'] = 'session-a'
    requests = len(paf.gets)
    page._height.setText('0.16')
    page._on_save_clicked()
    assert page._config_status.text() == 'Parameters saved successfully.'
    assert len(paf.gets) == requests and paf.puts == []

def test_fetch_selected_folder_when_qtm_has_no_open_measurement(app, paf, page):
    paf.active_error = True
    paf.nodes['session-a']['Fields']['BodyMass'] = 71
    page._on_fetch_clicked()
    idle(app, page)
    assert page._body_mass.text() == '71'
    assert page._config_status.text() == 'Parameters fetched.' and paf.puts == []

@pytest.mark.parametrize('extension, contents, accepted', [
    ('.xml', '<Session><Fields><Name>XML</Name></Fields></Session>', True),
    ('.XML', '<Container Type="Session"><Fields/></Container>', True),
    ('.qtm', '<Session><Fields/></Session>', False),
    ('.xml', '<Session>', False),
    ('.xml', '<Unrelated><Fields/></Unrelated>', False)])
def test_browse_accepts_only_valid_session_xml(app, tmp_path, monkeypatch, extension, contents, accepted):
    path = tmp_path / ('calibration' + extension)
    path.write_text(contents)
    widget = StaticAnalysisPage()
    args = []
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a: args.append(a) or (str(path), 'XML Files (*.xml)'))
    widget._browse_static_file()
    assert args[0][3] == 'XML Files (*.xml)'
    assert bool(widget._session_path) == accepted
    if not accepted:
        assert not widget._save_btn.isEnabled()
        assert 'XML' in widget._config_status.text()
    widget.close()

def test_static_late_completion_timer_cannot_restore_old_results(app, local_page, sessions):
    local_page._on_finished(ProcessingStatus(step='complete', completed=True))
    local_page.set_session(str(sessions[1]))
    QTest.qWait(350)
    assert local_page._stack.currentWidget() is local_page._config_widget
    assert local_page._comp_patient_lbl.text() == ''
    assert local_page._loaded_py_path == ''
    assert local_page._progress_bar.value() == 0

def test_fetch_result_from_previous_session_is_discarded(app, paf, page):
    paf.delay = .1
    page._on_fetch_clicked()
    page.set_session(str(paf.other))
    assert not page._anthro_connected
    idle(app, page)
    assert Path(page._session_path) == paf.other
    assert not page._anthro_connected
    assert page._first_name.text() == ''

class QuietQTMMonitor(QWidget):
    connection_changed = Signal(bool)

@pytest.fixture
def window(app, sessions, monkeypatch):
    import app.ui.main_window as main
    monkeypatch.setattr(main, 'QTMMonitorPage', QuietQTMMonitor)
    monkeypatch.setattr('app.ui.pages.dynamic_analysis_page.sync_qtm_events_to_session', lambda **kw: (False, '', None, [], None))
    widget = main.MainWindow(AppSettings(patients_data_location=str(sessions[0].parents[2])))
    yield widget
    widget._static_page.close()
    widget._dynamic_page.close()
    widget.close()
    widget.deleteLater()
    app.processEvents()

def choose(window, xml):
    patient = xml.parent.parent
    window._patients.load_patient_by_path(patient.name, str(patient))

def test_startup_reconnect_and_restart_do_not_activate_patient(window, sessions):
    assert window._active_analysis_context is None
    assert window._patients.patient_combo.currentIndex() == 0
    assert window._patients.get_mrn() == ''
    assert all(not s.directory for s in window._patients.get_all_sessions())
    assert window._static_page._session_path == window._dynamic_page._session_path == ''
    assert window._static_page._body_mass.text() == ''
    assert not window._static_page._save_btn.isEnabled()
    window._on_qtm_connection(True)
    assert window._active_analysis_context is None
    choose(window, sessions[0])
    assert Path(window._static_page._session_path) == sessions[0]
    assert window._dynamic_page._trial_rows == {}
    # Each page/window instance starts empty, even when local files exist.
    fresh = StaticAnalysisPage()
    fresh.set_data_root(str(sessions[0].parents[2]))
    assert fresh._session_path == '' and fresh._body_mass.text() == ''
    fresh.close()

def test_explicit_browse_preserves_selected_xml_and_clears_other_analysis(window, sessions):
    choose(window, sessions[0])
    window._dynamic_page._completion_label.setText('Results A')
    alternate = sessions[1].with_name('Calibration.XML')
    alternate.write_bytes(sessions[1].read_bytes())
    window._static_page.set_session(str(alternate))
    assert Path(window._static_page._session_path) == alternate
    assert window._static_page._patient_number.text() == 'B'
    assert window._dynamic_page._completion_label.text() == ''

def test_browsing_another_patients_session_updates_patient_identity(window, sessions):
    choose(window, sessions[0])
    window._patients.session_rows[0].set_directory(str(sessions[1].parent))
    assert window._patients._current_patient_dir == str(sessions[1].parent.parent)
    assert window._patients.get_mrn() == 'B'
    assert window._static_page._patient_number.text() == 'B'

def test_patient_and_session_switches_clear_both_pages_keep_disk_and_same_selection(window, sessions, app):
    choose(window, sessions[0])
    static, dynamic = window._static_page, window._dynamic_page
    static._on_save_clicked()
    saved = Path(static._loaded_py_path)
    before = saved.read_bytes()
    window._on_static_to_dynamic(str(sessions[0]), 'Static 3.qtm')
    dynamic._processing_queue = [('dynamic', 'Dynamic 1.qtm')]
    dynamic._completion_label.setText('Results A')
    static._comp_patient_lbl.setText('Results A')
    generation = dynamic._analysis_generation
    window._navigate_to('static_analysis')
    window._navigate_to('patients')
    assert dynamic._analysis_generation == generation and dynamic._completion_label.text() == 'Results A'
    choose(window, sessions[0])
    assert dynamic._analysis_generation == generation
    choose(window, sessions[1])
    assert static._patient_number.text() == 'B'
    assert static._comp_patient_lbl.text() == '' and static._loaded_py_path == ''
    assert dynamic._session_path == '' and dynamic._trial_rows == {}
    assert dynamic._processing_queue == [] and dynamic._force_plate_configs == {}
    assert dynamic._completion_label.text() == ''
    assert not dynamic._qtm_sync_timer.isActive()
    assert dynamic._fs_watcher.files() == dynamic._fs_watcher.directories() == []
    assert saved.read_bytes() == before
    assert (sessions[0].parent / 'Dynamic 1.GCD').read_bytes().endswith(b'A')
    choose(window, sessions[0])
    assert static._patient_number.text() == 'A'
    assert dynamic._trial_rows == {} and static._comp_patient_lbl.text() == ''
    # Different session of the same patient has a distinct full-path identity.
    second = sessions[0].parent.parent / '2026-10-02_2'
    second.mkdir()
    (second / 'session.xml').write_bytes(sessions[0].read_bytes())
    window._patients.session_rows[1].set_directory(str(second))
    assert Path(static._session_path) == second / 'session.xml'
    assert static._loaded_py_path == '' and dynamic._trial_rows == {}

def test_old_dynamic_timers_and_watcher_paths_cannot_repopulate_new_session(app, sessions, monkeypatch):
    widget = DynamicAnalysisPage()
    monkeypatch.setattr('app.ui.pages.dynamic_analysis_page.sync_qtm_events_to_session', lambda **kw: (False, '', None, [], None))
    widget.load_session(str(sessions[0]))
    old_slot = widget._processing_slots[2][1]
    calls = []
    widget._schedule(10, lambda: calls.append('old'))
    widget.clear_session()
    widget.load_session(str(sessions[1]))
    widget._processing_queue = [('dynamic', 'Dynamic 1.qtm')]
    old_slot(ProcessingStatus(step='complete', completed=True))
    widget._on_fs_directory_changed(str(sessions[0].parent))
    QTest.qWait(30)
    assert calls == [] and widget._processed_success_count == 0
    assert widget._processing_queue == [('dynamic', 'Dynamic 1.qtm')]
    widget.clear_session()
    widget.close()

def test_processing_service_discards_cancelled_worker_output_and_can_restart(app, monkeypatch):
    class Worker(QObject):
        progress = Signal(object)
        log_line = Signal(str)
        finished = Signal(object)
        error = Signal(str)
        def __init__(self, *a, **kw): super().__init__()
        def cancel(self): pass  # Simulate a completion racing with cancellation.
        def run(self):
            time.sleep(.02)
            self.progress.emit(ProcessingStatus(progress=75))
            self.finished.emit(ProcessingStatus(step='complete', completed=True))
    monkeypatch.setattr(processing_service, 'ProcessingWorker', Worker)
    service = processing_service.GaitProcessingService()
    events = []
    service.processing_finished.connect(events.append)
    service.processing_progress.connect(events.append)
    service.process_static('A/session.xml', 'Static.qtm')
    service.invalidate()
    wait_for(app, lambda: service._thread is None)
    assert events == []
    service.process_static('B/session.xml', 'Static.qtm')
    wait_for(app, lambda: service._thread is None)
    assert len(events) == 2

def test_headless_parameter_loading_uses_saved_local_values_and_explicit_units():
    source = ROOT / 'Gait-lab-Vicon-to-QTM/Py3_StaticMain.py'
    tree = ast.parse(source.read_text(encoding='utf8'))
    getter = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'get_qtm_or_persisted')
    normalize = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'normalize_processing_measurements')
    owner = SimpleNamespace(parent=SimpleNamespace(_headless=True), valueMeasurementUnits='m', valueHeight='12.34567890123456', valueBodyMass='72.1234567890123')
    names = ['valueASISdist', 'valueLeftLegLength', 'valueRightLegLength', 'valueLeftKneeWidth', 'valueRightKneeWidth',
             'valueLeftAnkleWidth', 'valueRightAnkleWidth', 'valueLeftASIStoGTdist', 'valueRightASIStoGTdist',
             'valueLeftSoleThickness', 'valueRightSoleThickness']
    for name in names: setattr(owner, name, '.00123456789')
    ns = {'self': owner, 'fields': {'Height': 0.21, 'BodyMass': 71}, 'MILLIMETERS_PER_METER': 1000}
    exec(compile(ast.Module(body=[getter, normalize], type_ignores=[]), str(source), 'exec'), ns)
    assert ns['get_qtm_or_persisted']('Height', 'valueHeight') == '12.34567890123456'
    assert ns['get_qtm_or_persisted']('BodyMass', 'valueBodyMass', True) == '72.1234567890123'
    ns['normalize_processing_measurements'](owner)
    assert owner.valueHeight == float('12.34567890123456') * 1000
    assert owner.valueLeftLegLength == float('.00123456789') * 1000

def test_headless_patient_loading_preserves_reviewed_local_identity_and_dates():
    import datetime
    source = ROOT / 'Gait-lab-Vicon-to-QTM/Py3_StaticMain.py'
    tree = ast.parse(source.read_text(encoding='utf8'))
    patient = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'PatientInfo_Page')
    build = next(n for n in patient.body if isinstance(n, ast.FunctionDef) and n.name == 'build_UI')
    start = next(i for i,n in enumerate(build.body) if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'local_saved' for t in n.targets))
    end = next(i for i,n in enumerate(build.body) if isinstance(n, ast.FunctionDef) and n.name == 'get_qtm_or_persisted')
    class Value:
        def __init__(self): self.value = 'XML value'
        def insert(self, index, value): self.value = value
        def set(self, value): self.value = value
    names = ['PatientNumber', 'FirstName', 'LastName', 'Date', 'Month', 'Year',
             'DataCollectionDate', 'DataCollectionMonth', 'DataCollectionYear']
    ns = {name: Value() for name in names}
    owner = SimpleNamespace(parent=SimpleNamespace(_headless=True), valueMeasurementUnits='m', valuePatientNumber='',
                            valueFirstName="O'Neil", valueLastName='Local last',
                            valueDateOfBirth_Day='09', valueDateOfBirth_Month='Sep', valueDateOfBirth_Year='2001',
                            valueDataCollectionDate_Day='10', valueDataCollectionDate_Month='Oct', valueDataCollectionDate_Year='2026')
    ns.update(self=owner, ID='XML-ID', SubjectName='XML patient', fields={'Creation date':'2024-01-01'},
              datetime=datetime, DateOptions=[f'{day:02d}' for day in range(1,32)],
              MonthOptions=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
    exec(compile(ast.Module(body=build.body[start:end],type_ignores=[]),str(source),'exec'),ns)
    assert ns['PatientNumber'].value == '' and ns['FirstName'].value == "O'Neil"
    assert [ns[name].value for name in ['Date','Month','Year']] == ['09','Sep','2001']
    assert [ns[name].value for name in ['DataCollectionDate','DataCollectionMonth','DataCollectionYear']] == ['10','Oct','2026']

@pytest.mark.parametrize('headless', [True, False])
@pytest.mark.parametrize('saved_local', [True, False])
def test_real_static_patient_page_builds_with_mode_owned_by_application(app, tmp_path, monkeypatch, headless, saved_local):
    """Construct real Qt pages without starting the script's QTM/clinical entry point."""
    import datetime
    from PySide6.QtWidgets import QStackedWidget, QLineEdit
    monkeypatch.syspath_prepend(str(ROOT / 'Gait-lab-Vicon-to-QTM'))
    from pyside6_compat import tk, ttk
    source = ROOT / 'Gait-lab-Vicon-to-QTM/Py3_StaticMain.py'
    tree = ast.parse(source.read_text(encoding='utf8'))
    names = {'Static_Main', 'PatientInfo_Page', 'qtm_measurement_to_meters',
             'persisted_measurement_to_meters', 'write_setting'}
    definitions = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names]
    calibration = tmp_path / 'Static_BF_Test.py'
    preferences = tmp_path / 'preferences.py'
    preferences.write_text("self.StaticForwardDirection = '+X'\n")
    if saved_local:
        calibration.write_text("self.StaticForwardDirection = '+X'\nself.valueMeasurementUnits = 'm'\n"
                               "self.valueHeight = '12.34567890123456'\nself.valueBodyMass = '72.1234567890123'\n")
    # Other report pages are inert: constructing PatientInfo must not process or write trials.
    class QA(tk.Frame): pass
    class Report(tk.Frame): pass
    ns = dict(tk=tk, ttk=ttk, QStackedWidget=QStackedWidget, datetime=datetime,
              fields={'Name':'Test', 'ID':'test-id', 'Path':str(tmp_path), 'Filename':'Static',
                      'First Frame':1, 'Last Frame':100, 'DOB':'2000-01-01',
                      'Creation date':'2026-01-01', 'Height':.21, 'BodyMass':71},
              StaticDataFileName=calibration, UserPreferencesFileName=preferences,
              SittingFootStaticDataFileName=tmp_path/'unused.py',
              TestingCondition='BF', DefaultTestingCondition='BF', MILLIMETERS_PER_METER=1000,
              QAreport_Page=QA, StaticSubjectCalibrationReport_Page=Report,
              Large_Font='Calibri 14', Small_Font='Calibri 12', Smaller_Font='Calibri 10', Bold_Small_Font='Calibri 12 bold')
    exec(compile(ast.Module(body=definitions,type_ignores=[]),str(source),'exec'),ns)
    before = {p.name:p.read_bytes() for p in tmp_path.iterdir()}
    root = ns['Static_Main'](headless=headless)
    try:
        page = root.frames[ns['PatientInfo_Page']]
        assert page.parent is root and root._headless is headless
        assert '_headless' not in page.__dict__
        entries = [entry.text() for entry in page.findChildren(QLineEdit)]
        assert ('12.34567890123456' if headless and saved_local else '0.21') in entries
        expected_mass = '72.1234567890123' if headless and saved_local else '72.12' if saved_local else '71.0'
        assert expected_mass in entries
        page.build_UI()  # Rebuilding must retain the controller mode too.
        assert {p.name:p.read_bytes() for p in tmp_path.iterdir()} == before
    finally:
        root.close()
        root.deleteLater()
        app.processEvents()
