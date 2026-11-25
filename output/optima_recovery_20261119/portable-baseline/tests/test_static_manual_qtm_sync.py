"""Explicit Static Analysis operations only; disposable files and a fake QTM client."""
import copy
import os
import sys
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
from app.ui.pages.static_analysis_page import StaticAnalysisPage
from app.services.anthropometric_sync_service import ANTHROPOMETRIC_FIELDS


def wait(app, predicate):
    deadline = time.monotonic() + 5
    while not predicate():
        app.processEvents()
        QTest.qWait(5)
        assert time.monotonic() < deadline, "Manual operation did not finish"
    app.processEvents()


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def manual(app, tmp_path):
    fields = {name: 1.0 for name in ANTHROPOMETRIC_FIELDS}
    fields.update(BodyMass=71.0, Name="Patient", ID="A", Sex="Female", DOB="2000-01-01")
    paths = []
    for patient in ("A", "B"):
        folder = tmp_path / patient / "Session"
        folder.mkdir(parents=True)
        xml = folder / "session.xml"
        root = ET.Element("Session")
        for owner in (root, ET.SubElement(root, "Measurement", Filename="Static 1.qtm"),
                      ET.SubElement(root, "Measurement", Filename="Dynamic 1.qtm")):
            node = ET.SubElement(owner, "Fields")
            for name, value in {**fields, "ID": patient}.items():
                ET.SubElement(node, name).text = str(value)
        ET.ElementTree(root).write(xml, encoding="utf-8", xml_declaration=True)
        (folder / "data.qpr").write_bytes(b"opaque native data")
        (folder / "Static 1.qtm").write_bytes(b"opaque native recording")
        paths.append(xml)

    class Client:
        active_measurement = str(paths[0].parent / "Dynamic 1.qtm")
        active = paths[0].parent
        reads = []
        writes = []
        active_reads = 0
        gate = threading.Event()
        fail_write = False
        reject_write = False
        fail_read = False
        block = False

        def active_session_dir(self):
            self.active_reads += 1
            return self.active

        def read(self, context):
            self.reads.append(str(context))
            if self.block:
                assert self.gate.wait(5)
            if self.fail_read:
                raise OSError("QTM disconnected")
            return {"context": os.path.normcase(str(Path(context).resolve())),
                    "fields": copy.deepcopy(fields), "errors": {}, "resolution": {}}

        def write(self, context, values):
            self.writes.append((str(context), dict(values)))
            if self.block:
                assert self.gate.wait(5)
            if self.fail_write:
                raise OSError("QTM disconnected")
            return not self.reject_write

    client = Client()
    page = StaticAnalysisPage()
    page._anthro_sync.client = client
    page.set_session(str(paths[0]))
    page.show()
    app.processEvents()
    state = SimpleNamespace(page=page, client=client, paths=paths, fields=fields)
    try:
        yield state
    finally:
        client.gate.set()
        wait(app, lambda: page._anthro_sync.operation is None and not page._manual_busy)
        page.close()
        page.deleteLater()
        app.processEvents()


def idle(app, state):
    wait(app, lambda: state.page._anthro_sync.operation is None and not state.page._manual_busy)


def test_open_wait_30_seconds_never_syncs_or_rewrites(manual, app):
    page, client = manual.page, manual.client
    original = manual.paths[0].read_bytes()
    original_value = page._body_mass.text()
    QTest.qWait(30_000)
    assert client.reads == client.writes == [] and client.active_reads == 0
    assert manual.paths[0].read_bytes() == original
    assert page._body_mass.text() == original_value
    assert not hasattr(page, "_auto_sync_timer") and not hasattr(page, "_external_sync_timer")


def test_edits_cursor_focus_and_show_hide_are_local_only(manual, app):
    page, client = manual.page, manual.client
    original = manual.paths[0].read_bytes()
    page._sync_feedback("Previous error", {"message": "Keep Details"}, error=True)
    page._body_mass.setFocus()
    page._body_mass.selectAll()
    QTest.keyClicks(page._body_mass, "72")
    page._body_mass.setCursorPosition(1)
    page._body_mass.editingFinished.emit()
    page._sex.setCurrentText("Male")
    page._sex.activated.emit(page._sex.currentIndex())
    page._dob_day.activated.emit(page._dob_day.currentIndex())
    page._first_name.textEdited.emit(page._first_name.text())
    page._patient_number.editingFinished.emit()
    page.hide()
    page.show()
    QTest.qWait(1600)
    assert client.reads == client.writes == [] and client.active_reads == 0
    assert manual.paths[0].read_bytes() == original
    assert page._body_mass.text() == "72" and page._body_mass.cursorPosition() == 1
    assert {"BodyMass", "Sex", "DOB", "Name"} <= page._anthro_dirty
    assert page._sync_details == {"message": "Keep Details"}
    assert not page._sync_details_btn.isHidden()


def test_external_file_change_does_not_reload_fields(manual):
    page = manual.page
    page._body_mass.setText("72")
    page._on_anthro_edited("BodyMass")
    tree = ET.parse(manual.paths[0])
    tree.find("Fields/BodyMass").text = "99"
    tree.write(manual.paths[0])
    changed = manual.paths[0].read_bytes()
    QTest.qWait(1600)
    assert page._body_mass.text() == "72" and manual.paths[0].read_bytes() == changed
    assert manual.client.reads == manual.client.writes == []


def test_fetch_once_preserves_selected_session_and_never_saves(manual, app):
    page, client = manual.page, manual.client
    client.active = manual.paths[1].parent
    original = manual.paths[0].read_bytes()
    page._fetch_btn.click()
    idle(app, manual)
    QTest.qWait(1500)
    assert client.reads == [os.path.normcase(str(manual.paths[0].parent))]
    assert client.writes == [] and manual.paths[0].read_bytes() == original
    assert page._session_path == str(manual.paths[0])
    assert "another session open" in page._config_status.text()


def test_fetch_confirms_unsaved_changes_and_keeps_new_edits(manual, app, monkeypatch):
    page, client = manual.page, manual.client
    page._body_mass.setText("72")
    page._on_anthro_edited("BodyMass")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.No)
    page._fetch_btn.click()
    assert client.reads == []
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
    client.block = True
    page._fetch_btn.click()
    wait(app, lambda: bool(client.reads))
    page._body_mass.setText("73")
    page._on_anthro_edited("BodyMass")
    client.gate.set()
    idle(app, manual)
    assert len(client.reads) == 1 and client.writes == []
    assert page._body_mass.text() == "73" and "New edits retained" in page._config_status.text()


def test_save_once_waits_for_result_and_preserves_native_files(manual, app):
    page, client = manual.page, manual.client
    original_b = manual.paths[1].read_bytes()
    native = {p: p.read_bytes() for p in manual.paths[0].parent.iterdir() if p.suffix in (".qtm", ".qpr")}
    client.block = True
    page._body_mass.setText("72")
    page._save_btn.click()
    wait(app, lambda: bool(client.writes))
    assert "updating QTM" in page._config_status.text()
    assert not page._save_btn.isEnabled() and not page._fetch_btn.isEnabled()
    page._on_save_clicked()
    page._on_fetch_clicked()
    assert len(client.writes) == 1 and client.reads == []
    assert Path(page._loaded_py_path).is_file()
    root = ET.parse(manual.paths[0]).getroot()
    assert all(float(node.findtext("BodyMass")) == 72 for node in root.iter("Fields"))
    client.gate.set()
    idle(app, manual)
    QTest.qWait(1500)
    assert page._config_status.text() == "Parameters saved locally and to QTM."
    assert len(client.writes) == 1 and client.reads == []
    assert manual.paths[1].read_bytes() == original_b
    assert all(p.read_bytes() == content for p, content in native.items())
    assert page._sync_details["qtm_saved"] and not page._sync_details_btn.isHidden()


@pytest.mark.parametrize("raises", [True, False])
def test_failed_qtm_write_keeps_local_save_and_does_not_retry(manual, app, raises):
    page, client = manual.page, manual.client
    client.fail_write = raises
    client.reject_write = not raises
    page._body_mass.setText("72")
    page._save_btn.click()
    idle(app, manual)
    details = dict(page._sync_details)
    QTest.qWait(1600)
    assert len(client.writes) == 1 and client.reads == []
    assert float(ET.parse(manual.paths[0]).findtext("Fields/BodyMass")) == 72
    assert Path(page._loaded_py_path).is_file()
    assert page._config_status.text() == "Saved locally; QTM update failed"
    assert page._sync_details == details and not page._sync_details_btn.isHidden()


def test_failed_fetch_reports_once_without_retry(manual, app):
    page, client = manual.page, manual.client
    client.fail_read = True
    original = manual.paths[0].read_bytes()
    before = page._body_mass.text()
    page._fetch_btn.click()
    idle(app, manual)
    details = dict(page._sync_details)
    QTest.qWait(1600)
    assert len(client.reads) == 1 and client.writes == []
    assert page._body_mass.text() == before and manual.paths[0].read_bytes() == original
    assert "not fetched" in page._config_status.text() and page._sync_details == details


@pytest.mark.parametrize("kind", ["fetch", "save"])
def test_session_switch_discards_old_result(manual, app, kind):
    page, client = manual.page, manual.client
    client.block = True
    (page._fetch_btn if kind == "fetch" else page._save_btn).click()
    wait(app, lambda: bool(client.reads or client.writes))
    page.set_session(str(manual.paths[1]))
    page._body_mass.setText("88")
    before = page._config_status.text()
    client.gate.set()
    idle(app, manual)
    assert page._session_path == str(manual.paths[1]) and page._body_mass.text() == "88"
    assert page._config_status.text() == before
    assert not page._sync_details and page._save_btn.isEnabled()
    assert len(client.reads) + len(client.writes) == 1


def test_xml_failure_prevents_qtm_write(manual, monkeypatch):
    monkeypatch.setattr("app.ui.pages.static_analysis_page.update_session_xml", lambda *args: False)
    manual.page._save_btn.click()
    assert manual.client.writes == []
    assert "session XML update failed" in manual.page._config_status.text()
    assert Path(manual.page._loaded_py_path).is_file()


def test_invalid_input_never_writes_and_run_still_processes_locally(manual, monkeypatch):
    page = manual.page
    page._body_mass.setText("nan")
    page._save_btn.click()
    assert "Parameters not saved" in page._config_status.text()
    assert manual.client.writes == [] and not page._loaded_py_path
    page._body_mass.setText("72")
    calls = []
    monkeypatch.setattr(page._service, "process_static", lambda *args, **kwargs: calls.append((args, kwargs)))
    page._run_btn.click()
    assert len(calls) == 1 and page._stack.currentWidget() is page._processing_widget
    assert Path(page._loaded_py_path).is_file() and manual.client.writes == manual.client.reads == []
