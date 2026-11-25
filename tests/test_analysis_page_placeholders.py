"""Analysis page drops unused, untitled placeholders and reflows graphs without gaps.

Uses disposable synthetic GCD data only (never patient data or QTM).
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

from app.services.gcd_service import GCDService
from app.services.settings_service import SettingsService
from app.ui.pages.analysis_page import AnalysisPage

CATEGORIES = ["kinematics", "sagittal_kinetics", "coronal_kinetics", "emg",
              "foot_kinematics", "muscle_length", "muscle_velocity"]


def _settings(cat):
    return getattr(SettingsService(), f"get_{cat}_settings")()


def _expected_titles(cat, side):
    """Valid (titled or used) graph titles in their original order."""
    s = _settings(cat)
    names = s.left_names if side != "R" else s.right_names
    if cat == "emg":
        return [s.titles[i] if i < len(s.titles) else names[i] for i in range(min(len(names), 5))]
    out = []
    for idx in range(min(len(names), 15)):
        title = s.titles[idx] if idx < len(s.titles) else ""
        if names[idx] or title:
            out.append(title)
    return out


def _by_title(page, title):
    return next(c for c in page._plot_grid.get_all_canvases()
                if not c.isHidden() and c.axes.get_title() == title)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def page(app, tmp_path):
    names = set()
    for cat in ("kinematics", "sagittal_kinetics", "coronal_kinetics", "muscle_length", "muscle_velocity"):
        s = _settings(cat)
        names.update(n for n in s.left_names + s.right_names if n)
    names.discard("LeftKneeValgVarMoment")  # an expected graph with no data
    x = np.linspace(0, 2 * np.pi, 101)
    gcd_path = tmp_path / "Dynamic 1.GCD"
    gcd_path.write_text("".join(f"!{n}\n" + "\n".join(f"{np.sin(v):.4f}" for v in x) + "\n"
                                for n in sorted(names)))
    gcd = GCDService().read_gcd(str(gcd_path))
    widget = AnalysisPage()
    widget.resize(1200, 1300)
    widget.show()
    widget._trial_data = {"L1": gcd, "R1": gcd}
    app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()


def _render(page, app, cat, side):
    page._current_side = side
    page._on_category_changed(cat)
    app.processEvents()


@pytest.mark.parametrize("side", ["L", "R", "LR"])
@pytest.mark.parametrize("cat", CATEGORIES)
def test_graphs_reflow_without_gaps(page, app, cat, side):
    _render(page, app, cat, side)
    titles = _expected_titles(cat, side)
    grid = page._plot_grid
    for pos in range(15):
        canvas = grid.get_canvas(*divmod(pos, 3))
        assert canvas.isHidden() == (pos >= len(titles)), (cat, side, pos)
    if cat != "emg":  # EMG slots without data stay untitled (left as is)
        shown = [grid.get_canvas(*divmod(p, 3)).axes.get_title() for p in range(len(titles))]
        assert shown == titles


def test_real_curves_and_legit_empty_graph_kept(page, app):
    _render(page, app, "coronal_kinetics", "L")
    hip = _by_title(page, "Hip Moment")
    assert any(len(l.get_ydata()) == 101 for l in hip.axes.lines)
    knee = _by_title(page, "Knee Moment")  # expected graph, data missing: still shown
    assert not knee.isHidden()


def test_last_row_graph_keeps_width(page, app):
    _render(page, app, "muscle_length", "L")  # 10 graphs
    grid = page._plot_grid
    assert abs(grid.get_canvas(3, 0).width() - grid.get_canvas(0, 0).width()) <= 2


def test_switching_sections_leaves_no_stale_placeholders(page, app):
    for _ in range(2):
        for cat in CATEGORIES:
            _render(page, app, cat, "L")
            n = len(_expected_titles(cat, "L"))
            hidden = {p for p in range(15) if page._plot_grid.get_canvas(*divmod(p, 3)).isHidden()}
            assert hidden == set(range(n, 15)), cat
    _render(page, app, "kinematics", "L")
    assert not any(c.isHidden() for c in page._plot_grid.get_all_canvases())
