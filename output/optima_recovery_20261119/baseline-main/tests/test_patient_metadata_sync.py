"""Patient controls and selected-session safety use real Qt and a disposable HTTP PAF."""
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox

from test_anthropometric_sync import app, paf, page, edit, idle, wait_for, VALUES
from app.services.anthropometric_sync_service import validate_patient_field


def patient_edit(page, name, text, commit=True):
    page._set_sync_value(name, text)
    if name in {"Name", "ID"}:
        page._patient_widgets[name].textEdited.emit(text)
        if commit:
            page._patient_widgets[name].editingFinished.emit()
    elif commit:
        widget = page._sex if name == "Sex" else page._dob_day
        widget.activated.emit(widget.currentIndex())
    else:
        page._on_anthro_edited(name)
    if commit:
        page._on_save_clicked()


@pytest.mark.parametrize("name,value", [("Name", "Claudia Rivera"), ("ID", "00098"),
                                       ("DOB", "1920-02-29"), ("Sex", "Male")])
def test_external_patient_edit_refreshes_correct_control_without_put(app, paf, page, name, value):
    before = {n: page._sync_value(n) for n in page._sync_fields}
    paf.nodes["session-a"]["Fields"][name] = value
    page._on_fetch_clicked()
    idle(app, page)
    assert page._sync_value(name) == value
    assert all(page._sync_value(n) == before[n] for n in page._sync_fields - {name})
    assert paf.puts == []


def test_patient_typing_and_choices_sync_automatically(app, paf, page):
    widget = page._first_name
    widget.setFocus()
    widget.selectAll()
    QTest.keyClicks(widget, "Uncommitted name")
    widget.editingFinished.emit()
    page._sex.setCurrentText("Male")
    page._sex.activated.emit(page._sex.currentIndex())
    page._dob_year.setCurrentText("2001")
    page._dob_year.activated.emit(page._dob_year.currentIndex())
    idle(app, page)
    assert any("/api/v1/paf/instance/session-a" in put for put in paf.puts)
    page._on_save_clicked()
    idle(app, page)
    assert page._config_status.text() == "Parameters saved successfully."
    assert "Uncommitted name" in Path(page._loaded_py_path).read_text()


@pytest.mark.parametrize("name,value", [("Name", ""), ("Name", "a\nb"),
                                       ("DOB", "2099-01-01"), ("DOB", "2001-02-29"),
                                       ("Sex", "unsupported")])
def test_patient_validation_rejects_invalid_input(name, value):
    with pytest.raises(ValueError):
        validate_patient_field(name, value)


def test_fetch_unsaved_confirmation_cancel_and_accept_are_read_only(app, paf, page, monkeypatch):
    patient_edit(page, "Name", "Retained draft", commit=False)
    edit(page, "BodyMass", "72", commit=False)
    paf.nodes["session-a"]["Fields"].update(Name="Current QTM name", BodyMass=73)
    questions = []
    def answer(*args):
        questions.append(args)
        return QMessageBox.No
    monkeypatch.setattr(QMessageBox, "question", answer)
    count = len(paf.gets)
    page._on_fetch_clicked()
    idle(app, page)
    assert len(questions) == 1 and "replace your unsaved changes" in questions[0][2]
    assert len(paf.gets) == count
    assert page._first_name.text() == "Retained draft" and page._body_mass.text() == "72"
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Yes)
    page._on_fetch_clicked()
    idle(app, page)
    assert page._first_name.text() == "Current QTM name" and float(page._body_mass.text()) == 73
    assert not page._anthro_dirty and paf.puts == []


def test_explicit_fetch_follows_open_session_without_cross_session_writes(app, paf, page, monkeypatch):
    patient_edit(page, "Name", "Old session draft", commit=False)
    (paf.other.parent / "Static 3.qtm").touch()
    paf.nodes["session-b"]["Fields"].update(Name="Other patient", ID="456")
    paf.active_file = str(paf.other.parent / "Dynamic 1.qtm")
    page._on_save_clicked()
    idle(app, page)
    assert all("session-b" not in put for put in paf.puts) and page._config_status.text() == "Parameters saved successfully."
    assert page._first_name.text() == "Old session draft"
    paf.puts.clear()
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Yes)
    page._on_fetch_clicked()
    idle(app, page)
    assert Path(page._session_path) == paf.other and page._filename == "Static 3.qtm"
    assert page._first_name.text() == "Other patient" and page._patient_number.text() == "456"
    assert not page._anthro_dirty and paf.puts == []
    page.set_session(str(paf.session), "Static 1.qtm")
    assert page._first_name.text() == "Old session draft" and not page._anthro_dirty


def test_xml_measurement_snapshot_does_not_override_patient_session_fields(app, paf, page):
    paf.fail = True
    xml = '<Session><Fields><Name>Session name</Name><BodyMass>71</BodyMass><Height>210</Height></Fields>'
    xml += '<Measurement Filename="Static 1.qtm"><Fields><Name>Stale measurement</Name><BodyMass>49.9</BodyMass></Fields></Measurement></Session>'
    paf.session.write_text(xml, encoding="utf8")
    page._auto_fetch_static_data()
    assert page._first_name.text() == "Session name"
    assert float(page._body_mass.text()) == 71
    assert float(page._height.text()) == 210  # No guessed mm-to-m conversion.
    idle(app, page)


def test_external_invalid_date_does_not_erase_gui_and_recovers_on_valid_poll(app, paf, page):
    original = page._sync_value("DOB")
    paf.nodes["session-a"]["Fields"]["DOB"] = "2001-02-29"
    page._on_fetch_clicked()
    idle(app, page)
    assert page._sync_value("DOB") == original
    assert "Invalid QTM metadata" in page._sync_details_text()
    paf.nodes["session-a"]["Fields"]["DOB"] = "2004-02-29"
    page._on_fetch_clicked()
    idle(app, page)
    assert page._sync_value("DOB") == "2004-02-29"
    assert "DOB" not in page._sync_details['failed_parameters']
    assert paf.puts == []


def test_edits_during_fetch_remain_dirty_and_are_not_written(app, paf, page):
    paf.delay = .1
    paf.nodes["session-a"]["Fields"]["Name"] = "External patient"
    page._on_fetch_clicked()
    patient_edit(page, "Name", "New draft during Fetch", commit=False)
    idle(app, page)
    assert page._first_name.text() == "New draft during Fetch"
    assert "Name" in page._anthro_dirty and paf.puts == []


def test_metadata_error_wraps_without_hiding_patient_controls(app, paf, page):
    page.resize(1280, 900)
    app.processEvents()
    previous_overflow = page.horizontalScrollBar().maximum()
    page._anthro_status("QTM synchronization unavailable: " + "C:/long-session-path/" * 25, error=True)
    app.processEvents()
    assert page.horizontalScrollBar().maximum() <= previous_overflow
    assert page._metadata_status.text() == page._config_status.text()


def test_fetch_detects_unsaved_programmatic_value_changes(app, paf, page, monkeypatch):
    page._body_mass.setText("72")
    questions = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a: questions.append(a) or QMessageBox.No)
    page._on_fetch_clicked()
    assert len(questions) == 1 and paf.puts == []
    assert page._body_mass.text() == "72"


def test_fetch_without_gui_session_uses_open_qtm_measurement(app, paf, page):
    paf.active_file = str(paf.other.parent / "Static 1.qtm")
    page._anthro_context = None
    page._manual_baseline = {}
    page._on_fetch_clicked()
    idle(app, page)
    assert Path(page._session_path) == paf.other
    assert page._anthro_connected and not page._anthro_dirty and paf.puts == []


@pytest.mark.parametrize("control", ["_last_name", "_trial_activity", "_left_sole", "_left_foot_check"])
def test_local_calibration_edit_confirms_before_fetch_session_switch(app, paf, page, monkeypatch, control):
    widget = getattr(page, control)
    if hasattr(widget, "textEdited"):
        widget.setText("Local draft")
        widget.textEdited.emit("Local draft")
    elif hasattr(widget, "activated"):
        widget.setCurrentIndex(1)
        widget.activated.emit(1)
    else:
        widget.click()
    assert page._manual_local_dirty
    paf.active_file = str(paf.other.parent / "Static 1.qtm")
    questions = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a: questions.append(a) or QMessageBox.No)
    count = len(paf.gets)
    page._on_fetch_clicked()
    idle(app, page)
    assert len(questions) == 1 and len(paf.gets) == count
    assert Path(page._session_path) == paf.session and paf.puts == []
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Yes)
    page._on_fetch_clicked()
    idle(app, page)
    assert Path(page._session_path) == paf.other and not page._manual_local_dirty
    assert paf.puts == []

@pytest.mark.parametrize('same_guid', [False, True])
def test_fetch_rejects_multiple_records_for_same_full_path(app, paf, page, same_guid):
    import copy
    duplicate = copy.deepcopy(paf.nodes['session-a'])
    duplicate['ID'] = 'session-a' if same_guid else 'another-guid'
    duplicate['Fields'].update(Name='Wrong patient', BodyMass=110)
    paf.nodes['ambiguous-branch'] = {'ID': 'ambiguous-branch', 'Fields': {'Class': 'RawFolder'}, 'Children': [duplicate]}
    before = {name: page._sync_value(name) for name in page._sync_fields}
    page._on_fetch_clicked()
    idle(app, page)
    assert {name: page._sync_value(name) for name in page._sync_fields} == before
    assert paf.puts == []
    assert page._sync_details['error_type'] == 'ambiguous_read_source'
    assert len(page._sync_details['conflicting_sessions']) == 2
    assert page._config_status.text() == 'Parameters not fetched — QTM read source is ambiguous.'
    patient_edit(page, 'Name', 'Retained draft')
    idle(app, page)
    assert page._first_name.text() == 'Retained draft'


def test_guid_expansion_cannot_replace_parent_with_different_path(app, paf, page, monkeypatch, tmp_path):
    import copy
    request = page._anthro_sync.client._request
    tree = {'Children': [{'ID': 'parent-guid', 'Fields': {'Class': 'RawFolder', 'Path': str(tmp_path / 'original')},
                          'ChildIDs': ['session-a']}]}
    wrong = {'ID': 'parent-guid', 'Fields': {'Class': 'RawFolder', 'Path': str(tmp_path / 'copy')},
             'Children': [copy.deepcopy(paf.nodes['session-a'])]}
    def expand(*args, **kwargs):
        if not args and kwargs.get('query') == '?depth=3':
            return tree
        if args == ('parent-guid',):
            return wrong
        return request(*args, **kwargs)
    monkeypatch.setattr(page._anthro_sync.client, '_request', expand)
    original = page._first_name.text()
    page._on_fetch_clicked()
    idle(app, page)
    assert page._first_name.text() == original and paf.puts == []
    assert page._sync_details['error_type'] == 'ambiguous_read_source'


