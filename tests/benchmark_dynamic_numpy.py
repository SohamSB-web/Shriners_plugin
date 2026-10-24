"""Numerical-core benchmark using synthetic data and frozen original formulas.

Run with the same Python/NumPy as processing: python tests/benchmark_dynamic_numpy.py
This excludes extraction, QTM, GCD and the application's remaining scalar frame loops.
"""
from pathlib import Path
import json
import os
import platform
import statistics
import sys
import time
import tracemalloc

if sys.platform == 'win32':
    library = Path(sys.prefix) / 'Library/bin'
    if library.is_dir():
        os.environ['PATH'] = str(library) + os.pathsep + os.environ.get('PATH', '')
        dll_directory = os.add_dll_directory(str(library))

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Gait-lab-Vicon-to-QTM'))
sys.path.insert(0, str(Path(__file__).parent / 'fixtures'))
import Py3_MathModules as math
import Py3_GaitModules as gait
import legacy_dynamic_math as original
import legacy_dynamic_gait as original_gait


def measure(function):
    function()
    times = []
    for _ in range(7):
        start = time.perf_counter()
        function()
        times.append(time.perf_counter() - start)
    tracemalloc.start()
    function()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {'median_s': statistics.median(times), 'samples_s': times, 'peak_traced_bytes': peak}


def main():
    rng = np.random.default_rng(1234)
    frames = 1000
    data = rng.normal(size=(3, frames))
    points = rng.normal(size=(3, frames, 3))
    matrices = np.linalg.qr(rng.normal(size=(frames, 3, 3)))[0]
    jobs = {
        'seven_point_cubic_derivatives': (
            lambda: original.Differentiate(data, 1, frames, frames, 1/120),
            lambda: math.Differentiate(data, 1, frames, frames, 1/120)),
        'cubic_smoothing': (
            lambda: original.Smooth1DArray(data[0], 1, frames, 4, 7),
            lambda: math.Smooth1DArray(data[0], 1, frames, 4, 7)),
        'pelvis_coordinate_systems': (
            lambda: [original_gait.TechCS_Pelvis_Newington(*points[:, i]) for i in range(frames)],
            lambda: gait.TechCS_Pelvis_Newington(*points)),
        'YXZ_angles': (
            lambda: [original.EulerAngles_YXZ(m, np.eye(3)) for m in matrices],
            lambda: math.EulerAngles_YXZ(matrices, np.eye(3))),
    }
    result = {'python':sys.version, 'numpy':np.__version__, 'platform':platform.platform(),
              'processor':platform.processor(), 'frames':frames, 'kernels':{}}
    for name, (baseline, optimized) in jobs.items():
        before, after = measure(baseline), measure(optimized)
        result['kernels'][name] = {'original':before, 'optimized':after,
                                  'speedup':before['median_s']/after['median_s']}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
