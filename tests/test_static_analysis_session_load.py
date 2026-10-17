# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_static_page_populates_when_session_xml_selected(qapp):
    win = MainWindow()
    sample_xml = Path("Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/Claudia_123-20260928T142041Z-1-001/Claudia_123/2026-10-01_2/session.xml")
    if not sample_xml.exists():
        pytest.skip("Sample session.xml not found")

    # Select the session via StaticAnalysisPage (reproduces user action)
    win._static_page.set_session(str(sample_xml))

    # Assert fields are populated and not cleared by signal bounce
    assert win._static_page._first_name.text() == "Claudia"
    assert win._static_page._body_mass.text() == "150.0"
    assert win._static_page._height.text() == "0.600"
    assert win._static_page._anthro_inputs["right_leg_length"].text() == "1.400"
    assert win._static_page._anthro_inputs["left_leg_length"].text() == "1.200"

    # Also assert Update Measurements page was synchronized
    assert win._update_measurements_page._patient_name.text() == "Claudia"
    assert win._update_measurements_page._anthro_inputs["RightLegLength"].text() == "1.400"
