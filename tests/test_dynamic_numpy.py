"""Compare optimized numerical functions with frozen, unmodified model formulas."""
from pathlib import Path
import sys
import ast
import copy
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Gait-lab-Vicon-to-QTM'))
sys.path.insert(0, str(Path(__file__).parent / 'fixtures'))
import Py3_MathModules as math
import Py3_GaitModules as gait
import legacy_dynamic_math as original
import legacy_dynamic_gait as original_gait
from legacy_dynamic_reconstruction import PELVIS, FOOT


def assert_same(actual, expected, atol=1e-12, rtol=1e-12):
    actual, expected = np.asarray(actual), np.asarray(expected)
    np.testing.assert_array_equal(np.isnan(actual), np.isnan(expected))
    np.testing.assert_array_equal(np.isinf(actual), np.isinf(expected))
    np.testing.assert_allclose(actual, expected, atol=atol, rtol=rtol, equal_nan=True)


@pytest.mark.parametrize('frames,start,end,dt', [(121, 1, 121, .01), (121, 8, 110, 1/120),
                                               (6, 1, 6, .01), (7, 1, 7, .005)])
@pytest.mark.parametrize('kind', ['smooth', 'noise', 'constant', 'missing'])
def test_derivatives_preserve_cubic_windows_and_edges(frames, start, end, dt, kind):
    rng = np.random.default_rng(381)
    t = np.arange(frames) * dt
    data = np.array([np.sin(t), 4*t**3-2*t**2+t, 2*np.cos(t)]) * 1000
    if kind == 'noise':
        data += rng.normal(size=data.shape)
    elif kind == 'constant':
        data[:] = 733.3
    elif kind == 'missing':
        data[0, :4] = np.nan
        data[1, frames//2] = np.inf
        data[2, -4:] = np.nan
    expected = original.Differentiate(data, start, end, frames, dt)
    actual = math.Differentiate(data.tolist(), start, end, frames, dt)
    assert isinstance(actual[0], list) and isinstance(actual[0][0], list)
    assert_same(actual[0], expected[0], atol=2e-9, rtol=2e-12)
    assert_same(actual[1], expected[1], atol=2e-7, rtol=2e-12)


@pytest.mark.parametrize('width', [1, 3, 4, 5, 7, 8, 201])
@pytest.mark.parametrize('start,end', [(1, 121), (5, 115)])
def test_smoothing_preserves_actual_degree_edges_and_invalid_windows(width, start, end):
    data = np.random.default_rng(712).normal(size=121) * 1000
    data[17] = np.nan
    data[-1] = np.inf
    with np.errstate(all='ignore'):
        expected = original.Smooth1DArray(data, start, end, 4, width)
        actual = math.Smooth1DArray(data.tolist(), start, end, 4, width)
    assert_same(actual, expected, atol=1e-9)


@pytest.mark.parametrize('name', ['EulerAngles_YXZ','EulerAngles_ZXY','EulerAngles_ZYX'])
def test_euler_scalar_and_batched_match_original_including_singularities(name):
    rng = np.random.default_rng(16)
    moving = np.linalg.qr(rng.normal(size=(30, 3, 3)))[0]
    reference = np.linalg.qr(rng.normal(size=(30, 3, 3)))[0]
    moving[:4] = [np.eye(3), np.zeros((3, 3)), np.full((3, 3), np.nan),
                  np.array([[0., 0., 1.], [0., 1., 0.], [-1., 0., 0.]])]
    reference[:4] = np.eye(3)
    expected = np.array([getattr(original, name)(m, r) for m, r in zip(moving, reference)])
    assert_same(getattr(math, name)(moving, reference), expected)
    for m, r, e in zip(moving, reference, expected):
        assert_same(getattr(math, name)(m, r), e)


@pytest.mark.parametrize('side', ['Left', 'Right'])
@pytest.mark.parametrize('name', ['TechCS_Pelvis_Newington','TechCS_Thigh_Newington',
    'TechCS_Shank_Newington','TechCS_Foot_Newington','AnatCS_Shank_Proximal_Newington',
    'AnatCS_Shank_Distal_VCM','TechCS_Hindfoot_mSHCG','TechCS_Forefoot_mSHCG','TechCS_Hallux_mSHCG'])
def test_segment_frames_match_original_for_each_side_and_degeneracies(side, name):
    points = np.random.default_rng(41).normal(size=(3, 23, 3)) * 500
    points[:, 0] = 0
    points[:, 1] = np.nan
    points[:, 2] = [[0., 0., 0.], [1., 0., 0.], [2., 0., 0.]]
    args = [] if name == 'TechCS_Pelvis_Newington' else [side]
    with np.errstate(all='ignore'):
        expected = [getattr(original_gait, name)(*args, *points[:, frame]) for frame in range(23)]
        actual = getattr(gait, name)(*args, *points)
    if name == 'TechCS_Pelvis_Newington':
        assert_same(actual[0], [e[0] for e in expected])
        assert_same(actual[1], [e[1] for e in expected])
    else:
        assert_same(actual, expected)


def test_calibration_transforms_keep_column_convention_and_broadcasting():
    rng = np.random.default_rng(52)
    matrices = np.linalg.qr(rng.normal(size=(24, 3, 3)))[0]
    calibration = np.linalg.qr(rng.normal(size=(3, 3)))[0]
    points, origins = rng.normal(size=(2, 24, 3))
    for name in ['TransformVectorIntoLabCoors', 'TransformVectorIntoMovingCoors']:
        expected = [getattr(original, name)(p, m) for p, m in zip(points, matrices)]
        assert_same(getattr(math, name)(points, matrices), expected)
    expected = [original.TransformPointIntoLabCoors(p, m, o) for p,m,o in zip(points,matrices,origins)]
    assert_same(math.TransformPointIntoLabCoors(points, matrices, origins), expected)
    assert_same(math.TransformAnatCoorSysFromTechCoors(calibration, matrices),
                [original.TransformAnatCoorSysFromTechCoors(calibration, m) for m in matrices])
    # Legacy np.matrix inputs must still yield the original ndarray shape.
    assert_same(math.TransformVectorIntoLabCoors([1., 2., 3.], np.matrix(calibration)),
                original.TransformVectorIntoLabCoors([1., 2., 3.], np.matrix(calibration)))


def test_angular_velocity_and_acceleration_preserve_frame_interval():
    data = np.random.default_rng(78).normal(size=(3, 3, 39))
    data[0, 0, 10] = np.nan
    assert_same(math.AngVelAcc_Euler_YXZ(*data, 3, 36, 39),
                original.AngVelAcc_Euler_YXZ(*data, 3, 36, 39))


def test_unit_vectors_preserve_zero_and_nan_behavior():
    points = np.array([[0.,0.,0.], [np.nan,1.,2.], [3.,4.,0.]])
    assert_same(math.ComputeUnitVecFromPts(np.zeros_like(points), points),
                [original.ComputeUnitVecFromPts(np.zeros(3), p) for p in points])


@pytest.mark.parametrize('dtype', [np.float32, np.float64])
def test_scalar_unit_vectors_retain_original_precision(dtype):
    point = np.array([3., 4., 7.], dtype=dtype)
    expected = original.ComputeUnitVecFromPts(np.zeros(3, dtype=dtype), point)
    actual = math.ComputeUnitVecFromPts(np.zeros(3, dtype=dtype), point)
    assert actual.dtype == expected.dtype
    np.testing.assert_array_equal(actual, expected)


def test_production_stages_do_not_hide_frame_loops():
    source = (ROOT/'Gait-lab-Vicon-to-QTM/Py3_DynamicMain.py').read_text(encoding='utf8')
    assert not [n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.For)
                and isinstance(n.target,ast.Name) and n.target.id=='FrameNumber']
    assert 'Batched kinematics' in source
    assert 'np.vectorize' not in source and 'np.frompyfunc' not in source


@pytest.mark.parametrize('kind,flags', [('pelvis', ('1',)), ('pelvis', ('2',)),
    ('foot', ('0','0')), ('foot', ('1','0')), ('foot', ('0','1')), ('foot', ('1','1'))])
@pytest.mark.parametrize('start,end', [(0, 31), (3, 27), (5, 5)])
def test_reconstruction_branches_match_original_without_qtm(kind, flags, start, end):
    legacy = PELVIS if kind == 'pelvis' else FOOT
    rng = np.random.default_rng(77)
    config = SimpleNamespace(valuePelvicFixCheck=flags[0], valueLeftFootModelCheck=flags[0],
                             valueRightFootModelCheck=flags[-1])
    for side in ('Left','Right'):
        setattr(config, 'value'+side+'ASISMarkerPelvis', rng.normal(size=3))
        setattr(config, 'value'+side+'23MetatarsalHeadMarkerForefoot', rng.normal(size=3))
    context = {'self':config, 'StartFrame':start, 'EndFrame':end, 'framecount':31}
    for node in ast.walk(ast.parse(legacy)):
        if isinstance(node, ast.Name) and node.id.endswith(('X','Y','Z')):
            if node.id.startswith('array'):
                context[node.id] = [0.] * 31
            else:
                context[node.id] = rng.normal(size=31).tolist()
    source = (ROOT/'Gait-lab-Vicon-to-QTM/Py3_DynamicMain.py').read_text(encoding='utf8')
    constructor = next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name=='__init__')
    if kind == 'pelvis':
        branch = next(n for n in constructor.body if isinstance(n,ast.If) and ast.unparse(n.test)=='not self.valuePelvicFixCheck == \'0\'')
        statements = branch.body
        first = next(i for i,n in enumerate(statements) if isinstance(n,ast.Assign) and ast.unparse(n.targets[0])=='active')
        last = next(i for i,n in enumerate(statements[first:],first) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='SetTrajectory')
    else:
        statements = constructor.body
        # The independent metatarsal reconstruction is the active-slice block at top level.
        first = next(i for i,n in enumerate(statements) if isinstance(n,ast.Assign) and ast.unparse(n.targets[0])=='active')
        last = first + 3
    expected = {**copy.deepcopy(context), 'np':np, 'gait':original_gait, 'math':original}
    actual = {**copy.deepcopy(context), 'np':np, 'gait':gait, 'math':math}
    with np.errstate(all='ignore'):
        exec(legacy, expected)
        exec(compile(ast.Module(body=statements[first:last], type_ignores=[]),'<batched reconstruction>','exec'),actual)
    prefixes = ('arrayLASISMarker','arrayRASISMarker') if kind=='pelvis' else ('arrayLMT23HMarker','arrayRMT23HMarker')
    for prefix in prefixes:
        for axis in 'XYZ':
            key = prefix + axis
            if key in expected:
                assert_same(actual[key], expected[key], atol=1e-10)
