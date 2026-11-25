"""Unused placeholders are dropped and graphs reflow without gaps; expected
graphs without data say so.

Uses disposable synthetic GCD sessions only (never patient data or QTM).
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot  # noqa: F401  (import before PySide6, as the other GUI tests do)
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from app.models.data_models import SessionInfo, TrialInfo
from app.services.settings_service import SettingsService
from app.ui.charts.plot_layout import (
    DATA_UNAVAILABLE_TEXT,
    availability_message,
    build_grid_plan,
)
from app.ui.pages.case_presentation_page import CasePresentationPage

CATEGORIES = ["kinematics", "sagittal_kinetics", "coronal_kinetics", "emg",
              "foot_kinematics", "muscle_length", "muscle_velocity"]

# Intentionally unused placeholder positions as (row, col), from *PageSettings.py.
EXPECTED_UNUSED = {
    "kinematics": set(),
    "sagittal_kinetics": {(0, 1), (0, 2), (1, 1), (1, 2)},
    "coronal_kinetics": {(0, 1), (0, 2), (1, 1), (1, 2), (2, 2), (4, 2)},
    "emg": {(1, 2)} | {(r, c) for r in (2, 3, 4) for c in range(3)},
    "foot_kinematics": {(1, 1)},
    "muscle_length": {(r, 2) for r in range(5)},
    "muscle_velocity": {(r, 2) for r in range(5)},
}


def _settings(cat):
    svc = SettingsService()
    return getattr(svc, f"get_{cat}_settings")()


def _expected_titles(cat):
    """Valid graph titles in their original order."""
    return [s.title for s in build_grid_plan(_settings(cat)).active_slots]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _write_gcd(path, variables):
    x = np.linspace(0, 2 * np.pi, 101)
    lines = []
    for i, name in enumerate(sorted(variables)):
        lines.append("!" + name)
        lines.extend(f"{10 * np.sin(x[j] + i):.4f}" for j in range(101))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path


def _full_body_vars(drop=()):
    """Every configured variable except EMG and foot-model channels (like a
    full-body session with no EMG), minus anything in ``drop``."""
    names = set()
    for cat in ("kinematics", "sagittal_kinetics", "coronal_kinetics",
                "muscle_length", "muscle_velocity"):
        s = _settings(cat)
        names.update(n for n in (s.left_names or []) + (s.right_names or []) if n)
    return names - set(drop)


@pytest.fixture
def page(app, tmp_path):
    session = tmp_path / "Patient" / "Session"
    _write_gcd(session / "Dynamic 1.GCD", _full_body_vars())
    # Right trial deliberately lacks the coronal knee moment.
    _write_gcd(session / "Dynamic 2.GCD", _full_body_vars(drop={"RightKneeValgVarMoment"}))
    info = SessionInfo(directory=str(session),
                       left_trials=[TrialInfo(gcd_filename="Dynamic 1.GCD")],
                       right_trials=[TrialInfo(gcd_filename="Dynamic 2.GCD")])
    widget = CasePresentationPage()
    widget.resize(1200, 1400)
    widget.show()
    assert widget.load_session_data([info])
    app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()


def _render(page, app, cat, side="LR"):
    page._current_side = side
    page._update_pill_visibility()
    page._on_category_changed(cat)
    app.processEvents()


def _status(canvas):
    artist = getattr(canvas, "_status_artist", None)
    if artist is None or artist.axes is not canvas.axes or not artist.get_visible():
        return None
    return artist.get_text()


def _by_title(page, title):
    return next(c for c in page._plot_grid.get_all_canvases()
                if not c.isHidden() and c.axes.get_title() == title)


def _visible_titles_row_major(page):
    grid = page._plot_grid
    return [grid.get_canvas(r, c).axes.get_title()
            for r in range(5) for c in range(3) if not grid.get_canvas(r, c).isHidden()]


# ── layout plan (pure) ────────────────────────────────────────────────────

@pytest.mark.parametrize("cat", CATEGORIES)
def test_plan_unused_positions_match_page_settings(cat):
    plan = build_grid_plan(_settings(cat))
    assert {(s.row, s.col) for s in plan.unused_slots} == EXPECTED_UNUSED[cat]
    assert all(s.title for s in plan.active_slots), "every graph has a title"


@pytest.mark.parametrize("cat", CATEGORIES)
def test_compacted_plan_fills_row_by_row_in_order(cat):
    plan = build_grid_plan(_settings(cat))
    compact = plan.compacted()
    assert [s.title for s in compact.slots] == [s.title for s in plan.active_slots]
    assert [s.index for s in compact.slots] == [s.index for s in plan.active_slots]
    assert [(s.row, s.col) for s in compact.slots] == [divmod(i, 3) for i in range(len(compact.slots))]
    assert not compact.unused_slots


def test_compacted_x_labels_on_bottom_graph_of_each_column():
    compact = build_grid_plan(_settings("muscle_length")).compacted()  # 10 graphs
    labelled = {(s.row, s.col) for s in compact.slots if compact.shows_x_labels(s)}
    assert labelled == {(3, 0), (2, 1), (2, 2)}


def test_availability_ignores_selection_and_reports_per_limb():
    plan = build_grid_plan(_settings("coronal_kinetics"))
    slot = next(s for s in plan.active_slots if s.title == "Knee Moment")
    has = lambda trial, var: var in trial
    trials = {"L1": {"LeftKneeValgVarMoment"}, "R1": set()}
    assert availability_message(slot, trials, ("L", "R"), has) == "Right data unavailable"
    assert availability_message(slot, trials, ("L",), has) is None
    assert availability_message(slot, trials, ("R",), has) == DATA_UNAVAILABLE_TEXT
    # A limb without any loaded trials is not "missing data".
    assert availability_message(slot, {"L1": set()}, ("L", "R"), has) == DATA_UNAVAILABLE_TEXT
    assert availability_message(slot, {}, ("L", "R"), has) is None


# ── on-screen grid ────────────────────────────────────────────────────────

@pytest.mark.parametrize("side", ["L", "R", "LR"])
@pytest.mark.parametrize("cat", CATEGORIES)
def test_graphs_reflow_without_gaps_in_original_order(page, app, cat, side):
    _render(page, app, cat, side)
    titles = _expected_titles(cat)
    n = len(titles)
    grid = page._plot_grid
    for r in range(5):
        for c in range(3):
            canvas = grid.get_canvas(r, c)
            pos = r * 3 + c
            assert canvas.isHidden() == (pos >= n), f"{cat} {side} ({r},{c})"
            if pos >= n:
                assert not [l for l in canvas.axes.lines if l.get_visible() and len(l.get_xdata())]
    assert _visible_titles_row_major(page) == titles


def test_last_row_does_not_stretch_and_heights_stay_consistent(page, app):
    grid = page._plot_grid
    _render(page, app, "kinematics")
    full_h = grid.get_canvas(0, 0).height()
    _render(page, app, "muscle_length")  # 10 graphs: rows 0-2 full, row 3 has one
    app.processEvents()
    first, last = grid.get_canvas(0, 0), grid.get_canvas(3, 0)
    assert grid.get_canvas(3, 1).sizePolicy().retainSizeWhenHidden()
    assert grid.get_canvas(3, 2).sizePolicy().retainSizeWhenHidden()
    assert abs(last.width() - first.width()) <= 2, "last-row graph must not stretch"
    assert not grid.get_canvas(4, 0).sizePolicy().retainSizeWhenHidden()  # empty row collapses
    _render(page, app, "emg")  # 5 graphs in 2 rows
    app.processEvents()
    assert abs(grid.get_canvas(0, 0).height() - full_h) <= max(4, 0.05 * full_h)


def test_missing_measurements_are_labelled_not_blank(page, app):
    _render(page, app, "emg")
    for r, c in [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1)]:
        assert _status(page._plot_grid.get_canvas(r, c)) == DATA_UNAVAILABLE_TEXT
    _render(page, app, "coronal_kinetics", "LR")
    knee_moment = _by_title(page, "Knee Moment")
    assert _status(knee_moment) == "Right data unavailable"
    assert any(l.get_visible() and len(l.get_ydata()) == 101 for l in knee_moment.axes.lines)
    _render(page, app, "coronal_kinetics", "L")
    assert _status(_by_title(page, "Knee Moment")) is None
    assert _status(_by_title(page, "Hip Moment")) is None


def test_deselected_trials_are_not_reported_as_missing(page, app):
    _render(page, app, "kinematics")
    page._clear_all_trials()
    app.processEvents()
    page._refresh_plots(show_overlay=False)
    assert all(_status(c) is None for c in page._plot_grid.get_all_canvases())


def test_repeated_section_switching_leaves_no_stale_widgets(page, app):
    for _ in range(3):
        for cat in CATEGORIES:
            _render(page, app, cat)
            n = len(_expected_titles(cat))
            for pos in range(n, 15):
                canvas = page._plot_grid.get_canvas(*divmod(pos, 3))
                assert canvas.isHidden()
                assert canvas._last_plot_kwargs is None
            assert _visible_titles_row_major(page) == _expected_titles(cat)
    _render(page, app, "kinematics")
    assert not any(c.isHidden() for c in page._plot_grid.get_all_canvases())
    assert page._plot_grid.get_canvas(0, 1).axes.get_title() == "Trunk Obliquity"


def test_mean_and_mr_curves_still_render(page, app):
    _render(page, app, "coronal_kinetics", "LR")
    page._active_trial_filter.update({"Mean_L", "Mean_R"})
    page._refresh_plots(show_overlay=False)
    hip = _by_title(page, "Hip Moment")
    styles = {l.get_linestyle() for l in hip.axes.lines if l.get_visible() and len(l.get_ydata()) == 101}
    assert "--" in styles and "-" in styles


# ── PDF export ────────────────────────────────────────────────────────────

class _CapturePdf:
    def __init__(self):
        self.figures = []

    def savefig(self, fig, **kwargs):
        self.figures.append(fig)


def _gcds(tmp_path):
    from app.services.gcd_service import GCDService
    svc = GCDService()
    left = svc.read_gcd(str(_write_gcd(tmp_path / "L.GCD", _full_body_vars())))
    right = svc.read_gcd(str(_write_gcd(tmp_path / "R.GCD", _full_body_vars(drop={"RightKneeValgVarMoment"}))))
    return {"L1": left, "R1": right}


@pytest.mark.parametrize("cat", ["kinematics", "sagittal_kinetics", "coronal_kinetics", "foot_kinematics"])
def test_pdf_page_reflows_without_gaps_and_flags_missing(tmp_path, cat):
    import matplotlib.pyplot as plt
    from app.services.pdf_report_service import CasePresentationPdfService as Pdf
    trials = _gcds(tmp_path)
    capture = _CapturePdf()
    p_info = {k: "-" for k in ("hospital", "mrn", "session_date", "condition", "export_time")}
    orig_close = plt.close
    plt.close = lambda *a, **k: None
    try:
        Pdf._create_plot_page(pdf=capture, page_title="T", subtitle="S", settings=_settings(cat),
                              trials=trials, norm_data=None, p_info=p_info)
    finally:
        plt.close = orig_close
    fig = capture.figures[0]
    titles = _expected_titles(cat)
    assert [ax.get_title() for ax in fig.axes] == titles
    # Axes fill the page row by row with the same size: no gaps, no stretching.
    boxes = [ax.get_position() for ax in fig.axes]
    xs = sorted({round(b.x0, 4) for b in boxes})
    ys = sorted({round(b.y0, 4) for b in boxes}, reverse=True)
    assert [(ys.index(round(b.y0, 4)), xs.index(round(b.x0, 4))) for b in boxes] == \
        [divmod(i, 3) for i in range(len(boxes))]
    assert len({(round(b.width, 4), round(b.height, 4)) for b in boxes}) == 1
    notes = {ax.get_title(): [t.get_text() for t in ax.texts] for ax in fig.axes}
    if cat == "coronal_kinetics":
        assert notes["Knee Moment"] == ["Right data unavailable"]
        assert notes["Hip Moment"] == []
    if cat == "foot_kinematics":
        assert notes["Hindfoot Tilt"] == [DATA_UNAVAILABLE_TEXT]
        assert notes["Ankle Plantar-Dorsiflexion"] == []


def test_pdf_report_end_to_end(tmp_path):
    from app.services.pdf_report_service import CasePresentationPdfService as Pdf
    out = tmp_path / "report.pdf"
    path = Pdf.generate_report(session_path=tmp_path, output_pdf_path=out,
                               trials_data=_gcds(tmp_path), selected_trials={"L1", "R1"})
    data = Path(path).read_bytes()
    assert data.startswith(b"%PDF") and data.count(b"/Type /Page\n") + data.count(b"/Type /Page ") >= 4
