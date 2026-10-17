"""Unit tests for automatic QTM synchronization and session.xml update."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from PySide6.QtCore import QThreadPool
from PySide6.QtTest import QTest

from app.services.anthropometric_sync_service import (
    ANTHROPOMETRIC_FIELDS,
    QtmAnthropometricClient,
    get_session_xml_path,
    update_session_xml,
)
from app.ui.pages.static_analysis_page import StaticAnalysisPage
from test_anthropometric_sync import app, paf, page, idle, VALUES


def test_get_session_xml_path_resolves_all_variants(tmp_path):
    session_dir = tmp_path / "session_folder"
    session_dir.mkdir(parents=True, exist_ok=True)
    xml_file = session_dir / "session.xml"
    xml_file.write_text("<Session/>", encoding="utf-8")
    trial_file = session_dir / "Static 1.qtm"
    trial_file.touch()

    assert get_session_xml_path(xml_file) == xml_file
    assert get_session_xml_path(session_dir) == xml_file
    assert get_session_xml_path(trial_file) == xml_file
    assert get_session_xml_path(None) is None


def test_update_session_xml_utf16_and_formatting(tmp_path):
    folder = tmp_path / "utf16_session"
    folder.mkdir()
    xml_path = folder / "session.xml"
    initial_xml = """<?xml version="1.0"?>
<Session Type="Session">
    <Fields>
        <ID>123</ID>
        <Name>Claudia</Name>
        <BodyMass>100.000000000</BodyMass>
    </Fields>
</Session>"""
    xml_path.write_bytes(initial_xml.encode("utf-16"))

    success = update_session_xml(xml_path, {
        "BodyMass": 75.0,
        "Height": 0.600000024,
        "InterAsisDistance": 7.5,
        "ID": "123",
        "Sex": "Female",
        "DOB": "2006-09-14",
    })
    assert success is True

    raw = xml_path.read_bytes()
    assert raw.startswith((b"\xff\xfe", b"\xfe\xff")), "Should preserve UTF-16 BOM"

    tree = ET.parse(xml_path)
    fields = tree.getroot().find("Fields")
    assert fields.findtext("BodyMass") == "75.000000000"
    assert fields.findtext("Height") == "0.600000024"
    assert fields.findtext("InterAsisDistance") == "7.500000000"
    assert fields.findtext("ID") == "123"
    assert fields.findtext("Sex") == "Female"
    assert fields.findtext("DOB") == "2006-09-14"


def test_editing_anthropometrics_in_gui_updates_xml_and_qtm(app, paf, page):
    page._body_mass.setText("75.0")
    page._body_mass.editingFinished.emit()

    QThreadPool.globalInstance().waitForDone(2000)
    idle(app, page)

    # Verify session.xml was updated
    tree = ET.parse(page._session_path)
    bm_in_xml = tree.getroot().find("Fields").findtext("BodyMass")
    assert float(bm_in_xml) == 75.0

    # Verify QTM mock endpoint received PUT
    assert any("/api/v1/paf/instance/session-a" in put for put in paf.puts)
    assert paf.nodes["session-a"]["Fields"]["BodyMass"] == 75.0


def test_saving_parameters_updates_py_xml_and_qtm(app, paf, page):
    paf.puts.clear()
    page._height.setText("1.65")
    page._patient_number.setText("pat-999")
    page._on_save_clicked()

    QThreadPool.globalInstance().waitForDone(2000)
    idle(app, page)

    # 1. Local calibration saved
    assert Path(page._loaded_py_path).is_file()

    # 2. session.xml updated
    tree = ET.parse(page._session_path)
    f = tree.getroot().find("Fields")
    assert float(f.findtext("Height")) == 1.65
    assert f.findtext("ID") == "pat-999"

    # 3. QTM updated
    assert any("/api/v1/paf/instance/session-a" in put for put in paf.puts)
    assert paf.nodes["session-a"]["Fields"]["Height"] == 1.65
    assert paf.nodes["session-a"]["Fields"]["ID"] == "pat-999"
