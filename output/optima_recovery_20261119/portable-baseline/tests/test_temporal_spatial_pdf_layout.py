"""PDF layout regressions use synthetic gait data and disposable output files."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pytest
from matplotlib.backends.backend_pdf import PdfPages
from app.models.data_models import GCDData
from app.services.pdf_report_service import CasePresentationPdfService as Service

METRICS = [
    ('Walking Speed', 'm/s', 'Speed', 1.2, '1.10 - 1.30'),
    ('Cadence', 'steps/min', 'Cadence', 120.0, '110 - 130'),
    ('Stride Length', 'm', 'StrideLength', 1.25, '1.10 - 1.35'),
    ('Step Length', 'm', 'StepLength', 0.60, '0.55 - 0.68'),
    ('Stride Time', 's', 'StrideTime', 1.05, '0.95 - 1.10'),
    ('Step Time', 's', 'StepTime', 0.52, '0.48 - 0.55'),
    ('Stance Phase', '%', 'Stance', 60.0, '58.0 - 62.0'),
    ('Single Support', '%', 'SingleSupport', 40.0, '38.0 - 42.0'),
    ('Double Support', '%', 'DoubleSupport', 20.0, '18.0 - 22.0'),
    ('Toe-Off Timing', '%', 'FootOff', 60.0, '58.0 - 62.0'),
]
INFO = {'hospital': "Shriners Children's Hospital - Motion Analysis Center", 'mrn': 'SYNTHETIC-TEST',
        'session_date': '2026-10-19', 'condition': 'Barefoot', 'export_time': 'October 19, 2026 12:00'}
CASES = [('one_trial', 1, 0, False), ('five_left', 5, 0, False), ('ten_left', 10, 0, False),
         ('twenty_trials', 10, 10, False), ('unequal_limbs', 3, 7, False), ('missing_scalars', 4, 3, True)]


def make_trials(left, right, missing=False, large=False):
    trials = {}
    for side, count in [('L', left), ('R', right)]:
        limb = 'Left' if side == 'L' else 'Right'
        for number in range(1, count + 1):
            names = ['LeftTrunkTilt', 'RightTrunkTilt']
            values = [np.sin(np.linspace(0, 2 * np.pi, 101)).tolist()] * 2
            for _, _, name, value, _ in METRICS:
                if missing and ((name == 'Speed' and number % 2) or name == 'StepTime'):
                    continue
                names.append(limb + name)
                if large:
                    value += 1_234_567_890.0
                values.append([value + (number - 1) * 0.01])
            trials[side + str(number)] = GCDData(variable_names=names, variable_data=values)
    return trials


def summary_figures(trials):
    figures = []
    Service._create_temporal_spatial_page(SimpleNamespace(savefig=figures.append), trials, INFO)
    return figures


def table_rows(figure):
    table = list(figure.axes[0].tables)[0]
    cells = table.get_celld()
    rows = max(row for row, _ in cells) + 1
    columns = max(column for _, column in cells) + 1
    return [[cells[row, column].get_text().get_text() for column in range(columns)] for row in range(rows)]


@pytest.mark.parametrize('name,left,right,missing', CASES)
def test_limb_tables_preserve_all_trials_metrics_means_and_norms(name, left, right, missing):
    trials = make_trials(left, right, missing)
    figures = summary_figures(trials)
    assert len(figures) == bool(left) + bool(right)
    for figure, side, count in zip(figures, ['L', 'R'] if left and right else ['L' if left else 'R'],
                                   [left, right] if left and right else [left or right]):
        rows = table_rows(figure)
        assert rows[0] == ['Parameter', 'Unit'] + [side + str(i) for i in range(1, count + 1)] + [side + ' Mean', 'Norm TD']
        assert len(rows) == 11
        for row, (label, unit, var, _, norm) in zip(rows[1:], METRICS):
            assert row[:2] == [label, unit]
            values = []
            for index in range(1, count + 1):
                source = trials[side + str(index)].get_variable(('Left' if side == 'L' else 'Right') + var)
                expected = '--' if source is None else f'{source[0]:.2f}'
                assert row[index + 1] == expected
                if source is not None:
                    values.append(source[0])
            assert row[-2] == (f'{np.mean(values):.2f}' if values else '--')
            assert row[-1] == norm
        renderer = figure.canvas.get_renderer()
        table = list(figure.axes[0].tables)[0]
        for (_, column), cell in table.get_celld().items():
            text, bounds = cell.get_text().get_window_extent(renderer), cell.get_window_extent(renderer)
            assert cell.get_text().get_fontsize() >= 9
            assert text.x0 >= bounds.x0 + cell.PAD * bounds.width - 1
            assert text.x1 <= bounds.x1 - cell.PAD * bounds.width + 1
            assert text.y0 >= bounds.y0 + cell.PAD * bounds.height - 1
            assert text.y1 <= bounds.y1 - cell.PAD * bounds.height + 1
            assert cell.get_text().get_ha() == ('left' if column == 0 else 'center')
            assert bounds.x0 >= figure.bbox.width * 0.05 - 1
            assert bounds.x1 <= figure.bbox.width * 0.95 + 1
        # Interpretation and signatures are in disjoint horizontal regions below the table.
        notes = figure.axes[1].texts
        signatures = [text for text in notes if text.get_position()[0] == 0.64]
        bullets = [text for text in notes if text.get_text().startswith('•')]
        boundary = figure.axes[1].transAxes.transform((0.62, 0))[0]
        assert all(text.get_window_extent(renderer).x1 < boundary for text in bullets)
        assert all(text.get_window_extent(renderer).x0 > boundary for text in signatures)


def test_wider_values_paginate_without_recomputing_the_limb_mean():
    figures = summary_figures(make_trials(10, 0, large=True))
    assert len(figures) > 1
    seen = []
    means = []
    for figure in figures:
        rows = table_rows(figure)
        assert len(rows) == 11
        seen.extend(rows[0][2:-2])
        means.append(rows[1][-2])
    assert seen == [f'L{i}' for i in range(1, 11)]
    assert means == [f'{1_234_567_890.0 + 1.2 + 0.045:.2f}'] * len(figures)


def test_empty_or_invalid_limb_does_not_create_a_blank_summary():
    assert summary_figures({}) == []
    assert summary_figures({'L1': None, 'R1': GCDData()}) == []
    figures = summary_figures(dict(make_trials(0, 1), L1=None))
    assert len(figures) == 1
    assert table_rows(figures[0])[0][2] == 'R1'


def test_full_report_keeps_four_graph_pages_and_adds_only_selected_limb_summaries(tmp_path):
    from pypdf import PdfReader
    for name, left, right, missing in CASES:
        path = tmp_path / (name + '.pdf')
        trials = make_trials(left, right, missing)
        Service.generate_report(tmp_path, path, trials_data=trials, patient_info=INFO, selected_trials=set(trials))
        pages = PdfReader(path).pages
        assert len(pages) == 4 + bool(left) + bool(right)
        assert 'LOWER LIMB KINEMATICS' in pages[0].extract_text()
        assert 'FOOT KINEMATICS' in pages[3].extract_text()
        summary_text = '\n'.join(page.extract_text() for page in pages[4:])
        assert all(metric[0] in summary_text for metric in METRICS)
        assert all(key in summary_text.split() for key in trials)
        for page in pages[4:]:
            text = page.extract_text()
            assert 'CONFIDENTIAL MEDICAL RECORD' in text
            assert 'SYNTHETIC-TEST' in text
            assert 'CLINICAL INTERPRETATION' in text
