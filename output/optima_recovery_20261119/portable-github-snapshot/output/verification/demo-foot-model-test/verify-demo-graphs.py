import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PySide6.QtWidgets import QApplication
from app.services.gcd_service import GCDService
from app.ui.pages.case_presentation_page import CasePresentationPage

folder = Path(__file__).resolve().parent
app = QApplication([])
page = CasePresentationPage()
page.resize(1570, 1200)
page.show()
page.load_folder(str(folder))
app.processEvents()
assert set(page._trial_data) == {side+str(trial) for side in "LR" for trial in range(4,9)}
page._on_category_changed("foot_kinematics")
page._on_side_changed("LR")
page._render_plots(show_overlay=False)
app.processEvents()
settings = page._get_page_settings()
vars_ = list(zip(settings.left_names, settings.right_names))
canvases = page._plot_grid.get_all_canvases()
metrics = []
for (left, right), canvas in zip(vars_, canvases):
    if not left and not right:
        continue
    traces = canvas._last_plot_kwargs or {}
    curves = traces.get("curve_ids", [])
    assert curves, (left, right)
    values = traces["y_data"]
    assert len(values) == len(curves)
    entry = {"left_variable":left, "right_variable":right, "plotted_trial_curves":len(curves),
             "left_trials": sum(key.startswith("L") for key in curves),
             "right_trials": sum(key.startswith("R") for key in curves)}
    for key, data in zip(curves, values):
        arr = np.asarray(data)
        assert arr.size == 101 and np.isfinite(arr).all(), (left,right,key)
        assert np.ptp(arr) > 1e-5, (left,right,key,"flat")
        expected = GCDService.get_variable_array(page._trial_data[key], left if key.startswith("L") else right)
        np.testing.assert_array_equal(arr, expected)
    metrics.append(entry)
for canvas in canvases:
    canvas.draw()
page._plot_grid.grab().save(str(folder / "DEMO-foot-kinematics.png"))
trial_sha = json.loads((folder / "DEMO-inputs.json").read_text())["source_hashes"]
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest for p,digest in trial_sha.items())
report = {"demo_angles_degrees":{"left":4,"right":-3}, "clinical_source_hashes_verified":True,
          "gcd_trials":len(list((folder/"GCD").glob("*.GCD"))), "plotted_panels":len(metrics),
          "panels":metrics}
(folder / "DEMO-graph-verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))
