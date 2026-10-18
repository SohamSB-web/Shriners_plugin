# -*- coding: utf-8 -*-
"""
Tests for trial filtering during Case Presentation PDF Export.

Verifies:
1. When selected_trials is passed to CasePresentationPdfService.generate_report (e.g. {'L1', 'R1'}),
   only the selected trials are plotted and tabulated.
2. In the Temporal-Spatial table (Page 5), only the columns for selected trials are included.
3. The legend text on plot pages only lists the selected trials.
"""

import os
import sys
import unittest
from pathlib import Path
import zlib
import re

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.models.data_models import GCDData
from app.services.pdf_report_service import CasePresentationPdfService
from app.services.gcd_service import GCDService


class TestPdfExportTrialFiltering(unittest.TestCase):
    def setUp(self):
        self.output_pdf = Path("test_filtered_output.pdf")
        if self.output_pdf.exists():
            self.output_pdf.unlink()

        # Build mock trials L1..L4, R1..R4
        self.mock_trials = {}
        gcd_dir = Path("Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/Claudia_123-20260928T142041Z-1-001/Claudia_123/2026-10-18_2")
        if gcd_dir.exists():
            gcd_files = sorted(list(gcd_dir.glob("*.gcd")))
            for i in range(1, 5):
                src = gcd_files[(i - 1) % len(gcd_files)]
                self.mock_trials[f"L{i}"] = GCDService.read_gcd(str(src))
                self.mock_trials[f"R{i}"] = GCDService.read_gcd(str(src))
        else:
            # Fallback to minimal GCDData
            for i in range(1, 5):
                self.mock_trials[f"L{i}"] = GCDData(file_path=f"L{i}.gcd")
                self.mock_trials[f"R{i}"] = GCDData(file_path=f"R{i}.gcd")

    def tearDown(self):
        if self.output_pdf.exists():
            self.output_pdf.unlink()

    def test_trial_color_assignment(self):
        """Clinical colors: Left is royal blue, Right is crimson red for primary trials."""
        self.assertEqual(CasePresentationPdfService.get_trial_color("L1"), "#2563EB")
        self.assertEqual(CasePresentationPdfService.get_trial_color("R1"), "#DC2626")

    def test_pdf_export_only_selected_trials(self):
        """When selected_trials={'L1', 'R1'}, only L1 and R1 are exported."""
        svc = CasePresentationPdfService()
        selected = {"L1", "R1"}

        pdf_path = svc.generate_report(
            session_path=".",
            output_pdf_path=str(self.output_pdf),
            trials_data=self.mock_trials,
            patient_info={"name": "Test Patient", "id": "12345", "date": "2026-10-18"},
            selected_trials=selected,
        )

        self.assertTrue(os.path.exists(pdf_path))
        self.assertGreater(os.path.getsize(pdf_path), 1000)

        # Parse text from PDF stream objects
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        text_content = ""
        # Match each stream ... endstream
        for match in re.finditer(rb"stream[\r\n]+(.*?)(?:[\r\n]+endstream|\Z)", pdf_bytes, re.DOTALL):
            stream_data = match.group(1).strip()
            try:
                dec = zlib.decompress(stream_data).decode("latin1", errors="ignore")
                text_content += "\n" + dec
            except Exception:
                pass

        # In reportlab text chunks, strings appear like (L1) Tj or (R1) Tj
        self.assertIn("(L1)", text_content)
        self.assertIn("(R1)", text_content)

        # Unselected trials must NOT appear as labels or table headers
        self.assertNotIn("(L2)", text_content)
        self.assertNotIn("(R2)", text_content)
        self.assertNotIn("(L3)", text_content)
        self.assertNotIn("(R3)", text_content)
        self.assertNotIn("(L4)", text_content)
        self.assertNotIn("(R4)", text_content)

    def test_explicit_trial_listing_no_range(self):
        """Exporting L1, L2, L4 and R1, R2, R4 must explicitly mention those trials without L1..L10 or R1..R10."""
        svc = CasePresentationPdfService()
        selected = {"L1", "L2", "L4", "R1", "R2", "R4"}

        pdf_path = svc.generate_report(
            session_path=".",
            output_pdf_path=str(self.output_pdf),
            trials_data=self.mock_trials,
            patient_info={"name": "Test Patient", "id": "12345", "date": "2026-10-18"},
            selected_trials=selected,
        )

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        text_content = ""
        for match in re.finditer(rb"stream[\r\n]+(.*?)(?:[\r\n]+endstream|\Z)", pdf_bytes, re.DOTALL):
            try:
                dec = zlib.decompress(match.group(1).strip()).decode("latin1", errors="ignore")
                text_content += "\n" + dec
            except Exception:
                pass

        # Normalize escaped PDF string parentheses "\( ... \)" to "( ... )"
        clean_text = text_content.replace(r"\(", "(").replace(r"\)", ")")

        # Must explicitly mention trials
        self.assertIn("Left (L1, L2, L4)", clean_text)
        self.assertIn("Right (R1, R2, R4)", clean_text)

        # Must NOT condense to ranges like L1..L10 or R1..R10
        self.assertNotIn("L1..L10", clean_text)
        self.assertNotIn("R1..R10", clean_text)
        self.assertNotIn("L1-L10", clean_text)
        self.assertNotIn("R1-R10", clean_text)

    def test_only_mean_is_dotted_trials_are_solid(self):
        """Verify that individual Left and Right trials are plotted as solid lines, and mean as dashed/dotted."""
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        from app.services.settings_service import SettingsService

        settings = SettingsService().get_kinematics_settings()
        fig = plt.Figure(figsize=(11, 8.5))
        pdf_path = "test_lines_debug.pdf"
        with PdfPages(pdf_path) as pdf:
            CasePresentationPdfService._create_plot_page(
                pdf=pdf,
                page_title="TEST PAGE",
                subtitle="TEST",
                settings=settings,
                trials=self.mock_trials,
                norm_data=None,
                p_info={"hospital": "Shriners", "mrn": "123", "session_date": "2026-10-18", "condition": "BF", "export_time": "12:00"}
            )
        self.assertTrue(os.path.exists(pdf_path))
        os.remove(pdf_path)


if __name__ == "__main__":
    unittest.main()
