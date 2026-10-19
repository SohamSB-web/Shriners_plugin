"""Presentation navigation and empty states use disposable GCD sessions, never QTM."""
import os
import sys
from pathlib import Path
from unittest.mock import Mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot
import pytest
from PySide6.QtCore import Signal, QTimer, QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QWidget
from app.models.data_models import AppSettings, SessionInfo, TrialInfo
from app.ui.pages.case_presentation_page import CasePresentationPage, NO_PRESENTATION_SELECTION, NO_PROCESSED_TRIALS
from app.ui.main_window import MainWindow


class QuietQTM(QWidget):
    connection_changed = Signal(bool)


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def close_test_widgets(app):
    yield
    for widget in app.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


@pytest.fixture
def window(app, monkeypatch):
    monkeypatch.setattr('app.ui.main_window.QTMMonitorPage', QuietQTM)
    widget = MainWindow(AppSettings(patients_data_location=''))
    yield widget
    widget._dynamic_page.clear_session()
    widget._static_page.close()
    widget.close()
    widget.deleteLater()
    app.processEvents()


def gcd_file(folder, name='Dynamic 1.GCD', value=1):
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / name
    text = ''.join('!' + variable + '\n' + '\n'.join([str(value)] * 101) + '\n'
                   for variable in ('LeftTrunkTilt', 'RightTrunkTilt', 'LeftPelvicObliquity', 'RightPelvicObliquity'))
    target.write_text(text)
    return target


def select(window, folder):
    window._patients.mrn_input.setText('TEST')
    window._patients._selected_mrn = 'TEST'
    window._patients.session_rows[0].set_directory(str(folder))
    # SessionRow establishes the owning patient when a directory is explicitly chosen.
    return window._patients.session_rows[0]


@pytest.mark.parametrize('global_patient', [False, True])
def test_no_presentation_selection_redirects_without_overlay(window, app, global_patient, monkeypatch):
    if global_patient:
        window._on_patient_selected('GLOBAL_ONLY')
    overlay = Mock()
    monkeypatch.setattr(window._presentation_page._loading_overlay, 'show_loading', overlay)
    window._navigate_to('case_presentation')
    app.processEvents()
    assert window._pages.currentWidget() is window._patients
    assert window._patients._presentation_notice.text() == NO_PRESENTATION_SELECTION
    assert window._status_label.text() == NO_PRESENTATION_SELECTION
    overlay.assert_not_called()


def test_patient_confirmed_but_no_session_cannot_open(window, app):
    window._patients.mrn_input.setText('TEST')
    window._patients._selected_mrn = 'TEST'
    window._on_proceed_from_patients()
    app.processEvents()
    assert window._pages.currentWidget() is window._patients
    assert window._patients._presentation_notice.text() == NO_PRESENTATION_SELECTION


@pytest.mark.parametrize('content', ['missing', 'empty', 'corrupt', 'normative', 'unselected'])
def test_session_without_displayable_processed_trials(window, app, tmp_path, monkeypatch, content):
    session = tmp_path / 'Patient' / 'Session'
    session.mkdir(parents=True)
    if content == 'normative':
        gcd_file(session, 'TD_Run_Ave.GCD')
    elif content == 'unselected':
        gcd_file(session)
    elif content != 'missing':
        (session / 'Dynamic 1.GCD').write_text('' if content == 'empty' else '!LeftTrunkTilt\ninvalid\n')
    row = select(window, session)
    if content == 'unselected':
        row.clear_dynamic_trials()
    before = window._patients.get_all_sessions()[0].directory
    show = Mock()
    monkeypatch.setattr(window._presentation_page._loading_overlay, 'show_loading', show)
    window._on_open_single_session_presentation(0)
    app.processEvents()
    assert window._pages.currentWidget() is window._patients
    assert window._patients._presentation_notice.text() == NO_PROCESSED_TRIALS
    assert window._patients.get_all_sessions()[0].directory == before
    assert window._presentation_page._trial_data == {}
    show.assert_not_called()
    # A repeated sidebar click must retain the correct no-processed-data reason.
    window._navigate_to('case_presentation')
    app.processEvents()
    assert window._patients._presentation_notice.text() == NO_PROCESSED_TRIALS


def test_valid_load_renders_selected_slots_and_filters_do_not_redirect(window, app, tmp_path):
    session = tmp_path / 'Patient' / 'Session'
    first = gcd_file(session)
    second = gcd_file(session, 'Dynamic 10.GCD', value=10)
    row = select(window, session)
    row.clear_dynamic_trials()
    row.left_combos[9].setCurrentText(second.stem)
    row.right_combos[0].setCurrentText(first.stem)
    window._on_open_single_session_presentation(0)
    page = window._presentation_page
    assert window._pages.currentWidget() is page
    assert set(page._trial_data) == {'L10', 'R1'}
    app.processEvents()
    assert page._plot_grid.get_canvas(0, 0)._last_plot_kwargs['curve_ids'] == ['L10', 'R1']
    for key in list(page._active_trial_filter):
        page._pill_buttons[key].setChecked(False)
        page._on_filter_toggled(key, False)
    app.processEvents()
    assert not page._active_trial_filter
    assert window._pages.currentWidget() is page
    assert page._trial_data
    page._on_side_changed('L')
    page._on_side_changed('R')
    page._on_side_changed('LR')
    page._on_filter_toggled('Mean', True)
    page._on_norm_toggled(False)
    page._on_norm_toggled(True)
    app.processEvents()
    assert window._pages.currentWidget() is page


def test_patient_or_session_switch_clears_curves_and_pending_refresh(window, app, tmp_path):
    session = tmp_path / 'PatientA' / 'Session'
    gcd_file(session)
    select(window, session)
    window._on_open_single_session_presentation(0)
    page = window._presentation_page
    assert page._trial_data
    page._schedule_plot_refresh()
    empty = tmp_path / 'PatientB' / 'Session'
    empty.mkdir(parents=True)
    window._patients.load_patient_by_path('PatientB', str(empty.parent))
    app.processEvents()
    assert page._trial_data == {} and page._session_path == ''
    assert page._session_date == page._study_type == ''
    assert not page._plot_refresh_timer.isActive()
    assert all(not canvas.axes.lines for canvas in page._plot_grid.get_all_canvases())
    window._on_open_single_session_presentation(0)
    app.processEvents()
    assert window._pages.currentWidget() is window._patients
    assert window._patients._presentation_notice.text() == NO_PROCESSED_TRIALS


def test_constructor_and_empty_refresh_never_render(app, monkeypatch):
    render = Mock()
    monkeypatch.setattr('app.ui.pages.case_presentation_page.MultiPlotGrid.plot_at', render)
    page = CasePresentationPage()
    show = Mock()
    monkeypatch.setattr(page._loading_overlay, 'show_loading', show)
    page._refresh_plots()
    render.assert_not_called()
    show.assert_not_called()
    page.close()


def test_session_switcher_preserves_selected_trials_and_rejects_invalid_session(app, tmp_path):
    page = CasePresentationPage()
    a = gcd_file(tmp_path / 'A')
    b = gcd_file(tmp_path / 'B', value=2)
    sessions = [SessionInfo(directory=str(path.parent), analysis_date=path.parent.name,
                            left_trials=[TrialInfo(gcd_filename=path.name)]) for path in (a, b)]
    try:
        assert page.load_session_data(sessions)
        page._session_combo.setCurrentIndex(1)
        assert set(page._trial_data) == {'L1'}
        assert Path(page._trial_data['L1'].file_path) == b
        assert page._session_date == 'B'
        assert not page.load_session_data([])
        assert page._trial_data == {} and page._sessions == []
    finally:
        page.close()


def test_context_change_during_overlay_invalidates_old_render(window, app, tmp_path, monkeypatch):
    session = tmp_path / 'Patient' / 'Session'
    gcd_file(session)
    select(window, session)
    page = window._presentation_page
    original = page._loading_overlay.show_loading

    def switch_context(*args, **kwargs):
        QTimer.singleShot(0, lambda: window._on_patient_selected('Different Patient'))
        original(*args, **kwargs)

    monkeypatch.setattr(page._loading_overlay, 'show_loading', switch_context)
    window._on_open_single_session_presentation(0)
    app.processEvents()
    assert page._trial_data == {}
    assert all(not canvas.axes.lines for canvas in page._plot_grid.get_all_canvases())
    app.processEvents()
    assert window._pages.currentWidget() is not page


def test_rejected_navigation_is_coalesced_and_does_not_loop(window, app, monkeypatch):
    navigate = Mock(wraps=window._navigate_to)
    monkeypatch.setattr(window, '_navigate_to', navigate)
    window._navigate_to('case_presentation')
    window._navigate_to('case_presentation')
    app.processEvents()
    app.processEvents()
    assert [call.args[0] for call in navigate.call_args_list].count('patients') == 1
    assert not window._presentation_redirect_pending


def test_pdf_export_keeps_the_actual_selected_trials(app, tmp_path, monkeypatch):
    page = CasePresentationPage()
    path = gcd_file(tmp_path / 'Session')
    session = SessionInfo(directory=str(path.parent), left_trials=[TrialInfo(gcd_filename=path.name)])
    assert page.load_session_data([session])
    from PySide6.QtWidgets import QFileDialog, QMessageBox
    target = str(tmp_path / 'report.pdf')
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a: (target, 'PDF'))
    monkeypatch.setattr(QMessageBox, 'exec', lambda self: 0)
    report = Mock(return_value=target)
    monkeypatch.setattr('app.ui.pages.case_presentation_page.CasePresentationPdfService.generate_report', report)
    page._on_export_pdf_clicked()
    assert report.call_args.kwargs['selected_trials'] == {'L1'}
    assert set(report.call_args.kwargs['trials_data']) == {'L1'}
    page.close()


def test_last_chart_failure_always_unblocks_interface(app, tmp_path, monkeypatch):
    page = CasePresentationPage()
    path = gcd_file(tmp_path / 'Session')
    session = SessionInfo(directory=str(path.parent), left_trials=[TrialInfo(gcd_filename=path.name)])
    original = page._plot_grid.plot_at

    def fail_last(row, col, **kwargs):
        if (row, col) == (4, 2):
            raise ValueError('last chart failed')
        original(row, col, **kwargs)

    monkeypatch.setattr(page._plot_grid, 'plot_at', fail_last)
    page.show()
    page.load_session_data([session])
    app.processEvents()
    assert not page._loading_overlay.isVisible()
    assert not page._is_rendering
    assert 'last chart failed' in page._meta_badge.text()
    # Further filter changes still work after the failure.
    monkeypatch.setattr(page._plot_grid, 'plot_at', original)
    page._on_filter_toggled('L1', False)
    app.processEvents()
    assert not page._loading_overlay.isVisible()
    page.close()


def test_nested_refreshes_are_coalesced_instead_of_rendered_recursively(app, tmp_path, monkeypatch):
    page = CasePresentationPage()
    path = gcd_file(tmp_path / 'Session')
    session = SessionInfo(directory=str(path.parent), left_trials=[TrialInfo(gcd_filename=path.name)])
    show = page._loading_overlay.show_loading
    original = page._render_plots
    calls = []

    def nested(*args, **kwargs):
        page._on_filter_toggled('L1', False)
        page._refresh_plots()
        page._refresh_plots()
        show(*args, **kwargs)

    def render(overlay):
        calls.append(overlay)
        original(overlay)

    monkeypatch.setattr(page._loading_overlay, 'show_loading', nested)
    monkeypatch.setattr(page, '_render_plots', render)
    page.show()
    page.load_session_data([session])
    app.processEvents()
    app.processEvents()
    assert calls == [True, False]
    assert not page._loading_overlay.isVisible()
    assert not page._is_rendering and not page._plot_refresh_pending
    page.close()


def test_hidden_page_load_does_not_reveal_a_stuck_overlay_on_navigation(app, tmp_path):
    page = CasePresentationPage()
    path = gcd_file(tmp_path / 'Session')
    session = SessionInfo(directory=str(path.parent), left_trials=[TrialInfo(gcd_filename=path.name)])
    assert page.isHidden()
    assert page.load_session_data([session])
    assert page._loading_overlay.isHidden()  # isVisible() alone misses the hidden-parent bug.
    page.show()
    app.processEvents()
    assert page._loading_overlay.isHidden()
    assert page._plot_grid.get_canvas(0, 0)._last_plot_kwargs['curve_ids'] == ['L1']
    page.close()


def test_view_mac_case_navigates_before_rendering(window, app, tmp_path, monkeypatch):
    path = gcd_file(tmp_path / 'Patient' / 'Session')
    select(window, path.parent)
    render = Mock()
    monkeypatch.setattr(window._presentation_page, '_render_plots', render)
    window._on_open_single_session_presentation(0)
    assert window._pages.currentWidget() is window._presentation_page
    render.assert_not_called()
    app.processEvents()
    render.assert_called_once_with(True)
