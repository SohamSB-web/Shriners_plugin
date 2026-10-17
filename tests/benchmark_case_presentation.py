"""Reproducible synthetic 20-trial / 15-chart benchmark; no patient files used."""
import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
import numpy as np
from app.models.data_models import GCDData
from app.services.gcd_service import GCDService
from app.ui.charts.clinical_plots import ClinicalPlotCanvas
from app.ui.pages.case_presentation_page import CasePresentationPage


def populate(page):
    page._current_side = "LR"
    settings = page._get_page_settings()
    names = list(dict.fromkeys(settings.left_names + settings.right_names))
    names += [s + event for s in ("Left", "Right")
              for event in ("FootOff", "OppositeFootOff", "OppositeFootContact")]
    x = np.arange(101)
    for side in ("L", "R"):
        for i in range(1, 11):
            data = [list(np.sin(x / 20) * (i + 2)) if "Foot" not in name
                    else [60.0 if name.endswith("FootOff") else 15.0]
                    for name in names]
            page._trial_data[f"{side}{i}"] = GCDData(variable_names=names, variable_data=data)
    page._active_trial_filter = set(page._trial_data) | {"Mean", "Mean_L", "Mean_R"}


def benchmark(iterations=3):
    app = QApplication.instance() or QApplication([])
    page = CasePresentationPage()
    populate(page)
    page._refresh_plots(show_overlay=False)
    extraction = [0.0]
    preparation = [0.0]
    getter = GCDService.get_variable_array
    plotter = ClinicalPlotCanvas.plot_gait_data

    def timed_get(*args, **kwargs):
        start = time.perf_counter()
        try:
            return getter(*args, **kwargs)
        finally:
            extraction[0] += time.perf_counter() - start

    def timed_plot(*args, **kwargs):
        start = time.perf_counter()
        try:
            return plotter(*args, **kwargs)
        finally:
            preparation[0] += time.perf_counter() - start

    results = []
    with patch.object(GCDService, "get_variable_array", timed_get), \
         patch.object(ClinicalPlotCanvas, "plot_gait_data", timed_plot), \
         patch.object(ClinicalPlotCanvas, "draw_idle") as redraw:
        for i in range(iterations):
            extraction[0] = preparation[0] = 0.0
            redraw.reset_mock()
            start = time.perf_counter()
            if i % 2 == 0:
                page._active_trial_filter.discard("L1")
            else:
                page._active_trial_filter.add("L1")
            page._refresh_plots(show_overlay=False)
            refresh = time.perf_counter() - start
            start = time.perf_counter()
            for canvas in page._plot_grid.get_all_canvases():
                canvas.draw()  # Explicit raster timing, never used in interaction code.
            render = time.perf_counter() - start
            results.append(dict(data_extraction_ms=extraction[0] * 1000,
                                graph_preparation_ms=preparation[0] * 1000,
                                visibility_refresh_ms=refresh * 1000,
                                full_15_graph_render_ms=render * 1000,
                                redraw_requests=redraw.call_count))
    page.close()
    return {key: statistics.median(r[key] for r in results) for key in results[0]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = benchmark(args.iterations)
    print(json.dumps(result, indent=2))
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
