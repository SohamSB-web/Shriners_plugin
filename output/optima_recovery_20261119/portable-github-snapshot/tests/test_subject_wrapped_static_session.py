import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.static_analysis_page import StaticAnalysisPage


def test_static_page_accepts_qtm_subject_wrapped_session(tmp_path):
    app = QApplication.instance() or QApplication([])
    session = tmp_path / "session.xml"
    session.write_text(
        '<Subject Type="Participant"><Fields><Name /></Fields>'
        '<Session Type="Session"><Fields><Name>Volunteer</Name></Fields>'
        '<Measurement Type="Static" Filename="Static 1.qtm"><Fields /></Measurement>'
        '</Session></Subject>', encoding="utf-8"
    )
    page = StaticAnalysisPage()
    try:
        page.set_session(str(session))
        assert page._session_path == str(session)
        assert page._filename == "Static 1.qtm"
        assert page._first_name.text() == "Volunteer"
    finally:
        page.close()


def test_foot_model_imports_only_recorded_angles_and_keeps_saved_choices(tmp_path):
    app = QApplication.instance() or QApplication([])
    session = tmp_path / "session.xml"
    session.write_text(
        '<Subject Type="Participant"><Session Type="Session"><Fields>'
        '<Name>Volunteer</Name><LeftVarValAngle>4.25</LeftVarValAngle>'
        '<RightVarValAngle>-3.5</RightVarValAngle>'
        '</Fields><Measurement Type="Static" Filename="Static 1.qtm"><Fields /></Measurement>'
        '</Session></Subject>', encoding="utf-8",
    )
    page = StaticAnalysisPage()
    try:
        page.set_session(str(session))
        assert page._left_foot_check.isChecked() and page._right_foot_check.isChecked()
        assert page._foot_inputs["left_hindfoot_varus"].text() == "4.25"
        assert page._foot_inputs["right_hindfoot_varus"].text() == "-3.5"
        assert page._foot_inputs["left_calcaneal_pitch"].text() == ""

        page.clear_session()
        (tmp_path / "Static_BF_Volunteer.py").write_text(
            "self.valueLeftFootModelCheck = '0'\nself.valueLeftHindfootVarus = '2.75'\n", encoding="utf-8"
        )
        page.set_session(str(session))
        assert not page._left_foot_check.isChecked()
        assert page._right_foot_check.isChecked()
        assert page._foot_inputs["left_hindfoot_varus"].text() == "2.75"
    finally:
        page.close()
