"""Scale controls must change the graph, not just a temporary inspection canvas."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QCheckBox
from app.ui.charts.clinical_plots import ClinicalPlotCanvas, ClinicalPlotDetailDialog, MultiPlotGrid


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def plot(canvas, graph_id="hip", peak=30):
    canvas.plot_gait_data(
        graph_id=graph_id, x_data=[np.linspace(0, 100, 101)],
        y_data=[np.sin(np.linspace(0, np.pi, 101)) * peak], colors=["red"],
        y_min=-20, y_max=100, y_ticks=[-20, 0, 20, 40, 60, 80, 100], title="Hip",
    )


def test_expanded_range_persists_in_main_after_close_and_refresh(app):
    canvas = ClinicalPlotCanvas()
    plot(canvas)
    dialog = ClinicalPlotDetailDialog(canvas._last_plot_kwargs, source_canvas=canvas)
    dialog._spin_ymin.setValue(-40)
    dialog._spin_ymax.setValue(140)
    dialog._apply_custom_range()
    dialog.canvas.axes.set_xlim(10, 90)  # Same callback as toolbar zoom/pan.
    dialog.accept()
    assert canvas.axes.get_ylim() == (-40, 140)
    assert canvas.axes.get_xlim() == (10, 90)

    plot(canvas, peak=80)
    assert canvas.axes.get_ylim() == (-40, 140)
    assert canvas.axes.get_xlim() == (10, 90)


def test_reopening_theme_and_checkbox_keep_manual_scale(app):
    canvas = ClinicalPlotCanvas()
    plot(canvas)
    dialog = ClinicalPlotDetailDialog(canvas._last_plot_kwargs, source_canvas=canvas)
    dialog.canvas.axes.set_ylim(-40, 140)
    dialog.canvas.axes.set_xlim(15, 80)
    dialog.reject()
    checkbox = QCheckBox()
    checkbox.toggled.connect(lambda enabled: plot(canvas, peak=85 if enabled else 40))
    checkbox.setChecked(True)
    checkbox.setChecked(False)
    canvas.apply_theme(dark=True)
    plot(canvas)
    reopened = ClinicalPlotDetailDialog(canvas._last_plot_kwargs, source_canvas=canvas)
    for view in (canvas, reopened.canvas):
        assert view.axes.get_xlim() == (15, 80)
        assert view.axes.get_ylim() == (-40, 140)
    reopened.close()


def test_other_graphs_context_changes_and_position_changes_are_isolated(app):
    grid = MultiPlotGrid()
    a, b = grid.get_canvas(0, 0), grid.get_canvas(0, 1)
    plot(a, "session1/hip")
    plot(b, "session1/knee")
    dialog = ClinicalPlotDetailDialog(a._last_plot_kwargs, source_canvas=a)
    dialog.canvas.axes.set_ylim(-40, 140)
    b.set_scale_limits(ylim=(-10, 70))
    assert a.axes.get_ylim() == (-40, 140)
    plot(a, "session2/hip")
    dialog.canvas.axes.set_ylim(-50, 150)
    assert a.axes.get_ylim() == (-20, 100)  # Old popup cannot change a new context.
    dialog.close()
    plot(b, "session1/hip")  # Same graph in a different grid cell.
    assert b.axes.get_ylim() == (-50, 150)
    plot(b, "session1/knee")
    assert b.axes.get_ylim() == (-10, 70)


def test_auto_fit_and_explicit_reset_still_work(app):
    canvas = ClinicalPlotCanvas()
    plot(canvas, peak=130)
    dialog = ClinicalPlotDetailDialog(canvas._last_plot_kwargs, source_canvas=canvas)
    dialog.canvas.axes.set_xlim(20, 80)
    dialog.canvas.axes.set_ylim(-40, 200)
    dialog._autofit_range()
    assert canvas._scale_states["hip"]["y_mode"] == "auto"
    assert canvas.axes.get_ylim() == dialog.canvas.axes.get_ylim()
    assert canvas.axes.get_ylim()[1] > 130
    plot(canvas, peak=180)
    assert canvas.axes.get_ylim()[1] > 180
    dialog.close()
    reset_dialog = ClinicalPlotDetailDialog(canvas._last_plot_kwargs, source_canvas=canvas)
    reset_dialog._reset_range()
    assert canvas._scale_states["hip"]["y_mode"] == "reset"
    assert canvas.axes.get_xlim() == (0, 100)
    assert canvas.axes.get_ylim()[1] >= 180  # Existing dynamic default contains the peak.
    plot(canvas, peak=30)
    assert canvas.axes.get_ylim() == (-20, 100)
    reset_dialog.close()


def test_scale_edit_draws_only_source_and_detail_reuses_artists(app, monkeypatch):
    grid = MultiPlotGrid()
    for i, canvas in enumerate(grid.get_all_canvases()):
        plot(canvas, f"graph{i}")
    source = grid.get_canvas(0, 0)
    dialog = ClinicalPlotDetailDialog(source._last_plot_kwargs, source_canvas=source)
    curve = source._trial_artists["0"]["curve"]
    draws = []
    for canvas in grid.get_all_canvases():
        monkeypatch.setattr(canvas, "draw_idle", lambda c=canvas: draws.append(c))
    dialog._spin_ymin.setValue(-40)
    dialog._spin_ymax.setValue(140)
    dialog._apply_custom_range()
    assert draws == [source]
    plot(source, "graph0", peak=90)
    assert source._trial_artists["0"]["curve"] is curve
    assert source.axes.get_ylim() == (-40, 140)
    dialog.close()


def test_actual_double_click_wires_source_canvas(app, monkeypatch):
    source = ClinicalPlotCanvas()
    plot(source)

    def interact(dialog):
        dialog.canvas.axes.set_xlim(10, 90)
        dialog.canvas.axes.set_ylim(-40, 140)
        dialog.accept()
        return 1

    monkeypatch.setattr(ClinicalPlotDetailDialog, "exec", interact)
    event = QMouseEvent(QEvent.MouseButtonDblClick, QPointF(50, 50), QPointF(50, 50),
                        Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    source.mouseDoubleClickEvent(event)
    assert source.axes.get_xlim() == (10, 90)
    assert source.axes.get_ylim() == (-40, 140)


def test_mac_trial_and_norm_controls_preserve_scale(app, monkeypatch):
    from app.models.data_models import GCDData
    from app.ui.pages.case_presentation_page import CasePresentationPage

    monkeypatch.setattr(CasePresentationPage, "_load_default_norm", lambda self: None)
    page = CasePresentationPage()
    name = page._get_page_settings().left_names[0]
    page._trial_data = {"L1": GCDData(file_path="L1", variable_names=[name], variable_data=[[30] * 101]),
                        "L2": GCDData(file_path="L2", variable_names=[name], variable_data=[[40] * 101])}
    page._active_trial_filter = {"L1", "L2"}
    page._refresh_plots(show_overlay=False)
    source = page._plot_grid.get_canvas(0, 0)
    dialog = ClinicalPlotDetailDialog(source._last_plot_kwargs, source_canvas=source)
    dialog.canvas.axes.set_xlim(10, 90)
    dialog.canvas.axes.set_ylim(-40, 140)
    dialog.accept()
    page._pill_buttons["L1"].setChecked(False)
    app.processEvents()
    page._on_norm_toggled(False)
    app.processEvents()
    page._pill_buttons["L1"].setChecked(True)
    page._on_norm_toggled(True)
    app.processEvents()
    assert source.axes.get_xlim() == (10, 90)
    assert source.axes.get_ylim() == (-40, 140)
    page.close()


def test_manual_scale_moves_axis_relative_labels_and_events_without_new_artists(app):
    canvas = ClinicalPlotCanvas()
    canvas.plot_gait_data(
        graph_id="hip", x_data=[np.linspace(0, 100, 101)], y_data=[np.zeros(101)],
        colors=["red"], y_min=-20, y_max=100, y_label_top="Flexion", y_label_bottom="Extension",
        opposite_toe_offs=[15], opposite_foot_contacts=[45],
    )
    marker = canvas._trial_artists["0"]["opposite_contact"]
    canvas.set_scale_limits(ylim=(-40, 140))
    assert canvas._top_direction.get_position()[1] == 131
    assert canvas._bottom_direction.get_position()[1] == -31
    np.testing.assert_array_equal(marker.get_segments()[0], [[45, 131], [45, 140]])
    assert canvas._trial_artists["0"]["opposite_contact"] is marker
