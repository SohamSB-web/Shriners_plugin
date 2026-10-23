# -*- coding: utf-8 -*-
"""Unit tests for UpdateMeasurementsPage and GUI tab integration."""

import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import pytest
from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.services.anthropometric_sync_service import update_session_xml
from app.ui.main_window import MainWindow
from app.ui.pages.update_measurements_page import UpdateMeasurementsPage
from test_anthropometric_sync import app, paf, idle, VALUES, f32


@pytest.fixture
def test_session(tmp_path):
    """Creates a sample patient session folder with session.xml and trials."""
    session_dir = tmp_path / "Claudia_123" / "2026-10-01_02"
    session_dir.mkdir(parents=True, exist_ok=True)
    xml_file = session_dir / "session.xml"

    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<Session Type="Session" Name="2026-10-01_02">
    <Fields>
        <Name>Claudia</Name>
        <ID>123</ID>
        <Sex>Female</Sex>
        <DOB>2006-09-14</DOB>
        <BodyMass>150.000000000</BodyMass>
        <Height>0.600000024</Height>
        <InterAsisDistance>0.220000000</InterAsisDistance>
        <LeftLegLength>0.700000000</LeftLegLength>
        <RightLegLength>0.710000000</RightLegLength>
        <LeftKneeWidth>0.090000000</LeftKneeWidth>
        <RightKneeWidth>0.090000000</RightKneeWidth>
        <LeftAnkleWidth>0.065000000</LeftAnkleWidth>
        <RightAnkleWidth>0.065000000</RightAnkleWidth>
        <LeftAsisTrocanterDistance>0.120000000</LeftAsisTrocanterDistance>
        <RightAsisTrocanterDistance>0.120000000</RightAsisTrocanterDistance>
    </Fields>
    <Measurement Type="Static" Name="Static 1">
        <Fields>
            <Name>Static 1</Name>
            <Filename>Static 1.qtm</Filename>
            <BodyMass>150.000000000</BodyMass>
            <Height>0.600000024</Height>
        </Fields>
    </Measurement>
    <Measurement Type="Dynamic" Name="Walking 1">
        <Fields>
            <Name>Walking 1</Name>
            <Filename>Walking 1.qtm</Filename>
            <BodyMass>150.000000000</BodyMass>
            <Height>0.600000024</Height>
        </Fields>
    </Measurement>
</Session>"""
    xml_file.write_text(xml_content, encoding="utf-8")
    (session_dir / "Static 1.qtm").touch()
    (session_dir / "Walking 1.qtm").touch()
    return session_dir


def test_update_measurements_tab_registered_in_main_window(app):
    """Verify that 'Update Mesurements' tab exists in MainWindow sidebar and pages."""
    win = MainWindow()
    assert "update_measurements" in win._page_map
    assert isinstance(win._page_map["update_measurements"], UpdateMeasurementsPage)

    # Verify sidebar nav item text and 2nd position
    nav_labels = [label for key, label, icon in win._sidebar.NAV_ITEMS]
    assert "Update Mesurements" in nav_labels
    assert win._sidebar.NAV_ITEMS[1][0] == "update_measurements"

    # Verify navigating to the tab works
    win._navigate_to("update_measurements")
    assert win._pages.currentWidget() is win._update_measurements_page
    assert win._sidebar._active_key == "update_measurements"


def test_update_measurements_page_population(app, test_session):
    """Verify that opening a session correctly populates all inputs, formats, and trials."""
    page = UpdateMeasurementsPage()
    assert page.set_session(test_session) is True

    # Patient info
    assert page._patient_name.text() == "Claudia"
    assert page._patient_id.text() == "123"
    assert page._sex.currentText() == "Female"
    assert page._dob_year.currentText() == "2006"
    assert page._dob_month.currentText() == "Sep"
    assert page._dob_day.currentText() == "14"

    # Measurements formatting (lengths: 3 decimals, mass: 1 decimal)
    assert page._body_mass.text() == "150.0"
    assert page._height.text() == "0.600"
    assert page._asis_dist.text() == "0.220"
    assert page._anthro_inputs["LeftLegLength"].text() == "0.700"
    assert page._anthro_inputs["RightLegLength"].text() == "0.710"

    # Trials table shows static and dynamic trials
    assert page._trials_table.rowCount() == 2
    trial_names = [page._trials_table.item(r, 0).text() for r in range(2)]
    assert "Static 1.qtm" in trial_names
    assert "Walking 1.qtm" in trial_names


def test_update_measurements_editing_propagates_to_all_trials_and_xml(app, test_session):
    """Verify that changing a measurement in GUI updates root session and all child trials in session.xml."""
    page = UpdateMeasurementsPage()
    page.set_session(test_session)

    # Edit BodyMass and Height
    page._body_mass.setText("145.5")
    page._body_mass.editingFinished.emit()

    page._height.setText("0.650")
    page._height.editingFinished.emit()

    QThreadPool.globalInstance().waitForDone(2000)
    app.processEvents()

    # Verify session.xml root fields
    tree = ET.parse(test_session / "session.xml")
    root = tree.getroot()
    root_fields = root.find("Fields")
    assert float(root_fields.findtext("BodyMass")) == 145.5
    assert float(root_fields.findtext("Height")) == 0.650

    # Verify all child <Measurement> blocks carry the updated values
    for m in root.findall("Measurement"):
        m_fields = m.find("Fields")
        assert float(m_fields.findtext("BodyMass")) == 145.5
        assert float(m_fields.findtext("Height")) == 0.650


def test_update_measurements_qtm_sync(app, paf):
    """Verify that edits push changes to QTM PAF REST API."""
    from app.services.anthropometric_sync_service import QtmAnthropometricClient
    session_xml = paf.session
    page = UpdateMeasurementsPage()
    page._anthro_sync.client = QtmAnthropometricClient(paf.url)
    page.set_session(session_xml)

    paf.puts.clear()
    page._body_mass.setText("82.5")
    page._body_mass.editingFinished.emit()

    QThreadPool.globalInstance().waitForDone(2000)
    idle(app, page)

    # Verify PUT request was received by mock QTM
    assert any("/api/v1/paf/instance/session-a" in put for put in paf.puts)
    assert paf.nodes["session-a"]["Fields"]["BodyMass"] == 82.5


def test_update_measurements_external_qtm_sync(app, test_session):
    """Verify that external changes in session.xml (from QTM) are automatically detected and reflected in GUI."""
    page = UpdateMeasurementsPage()
    page.set_session(test_session)
    assert page._height.text() == "0.600"

    # Simulate QTM writing a new measurement to session.xml
    time.sleep(0.05)
    update_session_xml(test_session / "session.xml", {
        "Height": 0.685,
        "BodyMass": 155.0,
    })

    # Poll external changes
    page._poll_external_sync()
    app.processEvents()

    # Verify GUI inputs are updated automatically
    assert page._height.text() == "0.685"
    assert page._body_mass.text() == "155.0"


def test_editing_backspace_preservation(app, test_session):
    """Verify that editing/backspacing does not get prematurely overwritten by auto-sync or polling."""
    page = UpdateMeasurementsPage()
    page.show()
    app.processEvents()
    page.set_session(test_session)
    leg = page._anthro_inputs["RightLegLength"]
    leg.setText("1.200")

    # Simulate user focusing and hitting backspace to edit: 1.200 -> 1.00
    leg.setFocus()
    app.processEvents()
    leg.setText("1.00")
    leg.textEdited.emit("1.00")

    # Trigger timer timeout while widget still has focus
    page._on_auto_sync_timer_timeout()
    app.processEvents()

    # The user's text MUST remain "1.00" and NOT be prematurely overwritten to "1.000"
    assert leg.text() == "1.00"

    # Now user types 3 to make it 1.300 and presses Enter (commits)
    leg.setText("1.300")
    leg.editingFinished.emit()
    app.processEvents()

    assert leg.text() == "1.300"
    tree = ET.parse(test_session / "session.xml")
    assert float(tree.getroot().find("Fields").findtext("RightLegLength")) == 1.300
    QThreadPool.globalInstance().waitForDone(2000)
    page.close()
