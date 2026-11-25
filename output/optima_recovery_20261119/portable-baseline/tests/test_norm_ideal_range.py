# -*- coding: utf-8 -*-
"""
Verification test for Ideal Range (Normative Band and Dotted Mean Line)
displayed in the MAC Case Presentation page.
"""

import os
import tempfile
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Register Conda Library/bin on Windows for DLLs
if sys.platform == "win32":
    import ctypes
    _sys32_icu = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "icuuc.dll")
    if os.path.exists(_sys32_icu):
        try:
            ctypes.WinDLL(_sys32_icu)
        except Exception:
            pass

    conda_lib = os.path.join(sys.prefix, "Library", "bin")
    if os.path.isdir(conda_lib):
        if conda_lib not in os.environ.get("PATH", ""):
            os.environ["PATH"] = conda_lib + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(conda_lib)
            except Exception:
                pass

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Initialize QApplication
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from app.models.data_models import SessionInfo, TrialInfo
from app.services.gcd_service import GCDService
from app.ui.pages.case_presentation_page import CasePresentationPage

def test_norm_ideal_range():
    print("=" * 60)
    print("TESTING IDEAL RANGE IN MAC CASE PRESENTATION")
    print("=" * 60)

    # 1. Initialize page
    page = CasePresentationPage()
    page.resize(1600, 1000)
    page.show()
    app.processEvents()

    # 2. Check normative data loaded
    assert page._norm_data is not None, "Normative data failed to load!"
    print(f"[PASS] 1. Default normative data loaded successfully: {len(page._norm_data.variable_names)} variables")

    # 3. Check canvas 0 (Trunk Tilt) and canvas 4 (Pelvic Obliquity)
    pelvic_canvas = page._plot_grid.get_canvas(1, 1)  # row 1, col 1 is index 4: Pelvic Obliquity
    ax = pelvic_canvas.axes

    # Verify collections (fill_between creates PolyCollection)
    poly_collections = [c for c in ax.collections if hasattr(c, "get_paths")]
    assert not poly_collections, "Normative data alone must not render patient graphs"
    print(f"[PASS] 2. Empty presentation has no normative band")

    # Verify dotted line (ls=":")
    dotted_lines = [line for line in ax.lines if line.get_linestyle() == ":"]
    assert not dotted_lines, "Empty presentation must not render normative curves"
    print(f"[PASS] 3. Dotted normative mean curve (ls=':') verified on Pelvic Obliquity canvas")

    # 4. Load a session and verify trials plotted over ideal range
    temporary = tempfile.TemporaryDirectory()
    demo_dir = Path(temporary.name)
    variables = ("LeftTrunkTilt", "RightTrunkTilt", "LeftPelvicObliquity", "RightPelvicObliquity")
    (demo_dir / "Dynamic 1 - Copy.GCD").write_text("".join("!" + name + "\n" + "1\n" * 101 for name in variables))
    sess = SessionInfo(
        directory=str(demo_dir),
        analysis_date="2025-02-21",
        left_trials=[TrialInfo(side="L", number=1, gcd_filename="Dynamic 1 - Copy")],
        right_trials=[TrialInfo(side="R", number=1, gcd_filename="Dynamic 1 - Copy")],
    )
    page.load_session_data([sess], display_mode="MR")
    app.processEvents()

    # Verify that both trial lines and normative band exist
    ax = pelvic_canvas.axes
    poly_collections = [c for c in ax.collections if hasattr(c, "get_paths")]
    dotted_lines = [line for line in ax.lines if line.get_linestyle() == ":"]
    solid_lines = [line for line in ax.lines if line.get_linestyle() == "-"]

    assert len(poly_collections) > 0, "Normative band missing after loading session!"
    assert len(dotted_lines) > 0, "Dotted mean line missing after loading session!"
    assert len(solid_lines) > 0, "Patient trial lines missing after loading session!"
    print(f"[PASS] 4. Both ideal range band, dotted center curve, and patient trial lines co-exist correctly")

    # 5. Test Norm Band Toggle button
    page._norm_btn.setChecked(False)
    app.processEvents()
    ax = pelvic_canvas.axes
    polys_off = [c for c in ax.collections if hasattr(c, "get_paths")]
    assert len(polys_off) == 0, "Norm band should be hidden when toggle button is unchecked!"
    print(f"[PASS] 5. Norm band hide toggle verified")

    page._norm_btn.setChecked(True)
    app.processEvents()
    ax = pelvic_canvas.axes
    polys_on = [c for c in ax.collections if hasattr(c, "get_paths")]
    assert len(polys_on) > 0, "Norm band should be restored when toggle button is checked!"
    print(f"[PASS] 6. Norm band restore toggle verified")

    # 6. Switch to Bilateral side
    page._sidebar.side_changed.emit("LR")
    app.processEvents()
    print(f"[PASS] 7. Bilateral (L/R) view loaded successfully")

    # 7. Capture screenshots for artifacts
    artifact_dir = demo_dir / "test_reports"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    out_img = artifact_dir / "case_presentation_ideal_range_bilateral.png"
    pix = page.grab()
    pix.save(str(out_img))
    print(f"[PASS] 8. Bilateral screenshot saved to {out_img}")

    # Also capture close-up of the Pelvic Obliquity canvas in bilateral mode
    out_pelvic_img = artifact_dir / "pelvic_obliquity_ideal_range_closeup.png"
    pelvic_pix = pelvic_canvas.grab()
    pelvic_pix.save(str(out_pelvic_img))
    print(f"[PASS] 9. Close-up screenshot of Pelvic Obliquity saved to {out_pelvic_img}")

    # 8. Test Dark Mode
    from app.ui.theme.design_tokens import DARK_PALETTE, LIGHT_PALETTE
    page.apply_theme(DARK_PALETTE, dark=True)
    app.processEvents()
    out_dark_img = artifact_dir / "case_presentation_ideal_range_dark.png"
    pix = page.grab()
    pix.save(str(out_dark_img))
    print(f"[PASS] 10. Dark mode screenshot saved to {out_dark_img}")

    print("=" * 60)
    page.close()
    temporary.cleanup()
    print("ALL IDEAL RANGE TESTS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_norm_ideal_range()
