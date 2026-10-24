# Validated incremental Dynamic NumPy optimization

2026-10-23.

This changes three production files. It batches the measured polynomial-window bottlenecks and independent reconstruction; it does **not** replace the complete biomechanical model. Original scalar reference formulas are frozen in tests/fixtures with source SHA256 provenance.

## Changes and retained loops

- `Gait-lab-Vicon-to-QTM/Py3_MathModules.py`: Differentiate and Smooth1DArray solve the original cubic least-squares design with multiple right-hand sides. Seven-point neighborhoods, cubic degree, original evaluation points, finite-window skips, inactive zeros and list return interfaces are preserved. AngVelAcc_Euler_YXZ evaluates the original expressions over the selected interval. ComputeUnitVecFromPts calculates one norm and supports batches; scalar precision/zero/NaN behavior is tested. Existing vector, point, calibration and YXZ/ZXY/ZYX helpers accept batched matrices while preserving scalar formulas.
- `Gait-lab-Vicon-to-QTM/Py3_GaitModules.py`: pelvis, thigh, technical shank, proximal/distal anatomical shank, standard foot, hindfoot, forefoot and hallux coordinate constructors use last-axis norms/cross products and stack axes as columns. No regression coefficients, left/right signs or clinical angle definitions changed.
- `Gait-lab-Vicon-to-QTM/Py3_DynamicMain.py`: batched Pelfix ASIS reconstruction and virtual metatarsal reconstruction remove the two independent frame loops (original lines 241–309 and 399–476). Progress now includes first/last and every 50 frames. The main kinematics/muscle loop and both inverse-dynamics loops remain. Small boundary loops over at most three samples in differentiation and half a smoothing window remain; the per-window fits and angular-derivative frame loop are removed.
- Unmodified: Py3_CreateGCD.py, Py3_varExtractor.py, Py3_Utils.py, gapi.py, processing_service.py, clinical files, source ZIPs and dependency manifests. No commit or push.

## Numerical regression

75 tests pass on the processing runtime (Python 3.9.25 / NumPy 1.26.4). Tests cover original-vs-batch coordinate systems for both sides; zero/NaN/collinear inputs; original Euler sequences including singular matrices; static matrix broadcasting and np.matrix compatibility; first/last/partial/short derivative windows; NaN/Inf windows; odd/even/reduced smoothing widths; angular derivatives; scalar float32/float64 precision; Pelfix iliac/posterior-triad options; all four foot-enable combinations; empty/partial intervals and progress throttling.

Tolerances are in the original function units: coordinate/Euler/calibration comparisons atol=rtol=1e-12 (reconstruction atol=1e-10); derivative velocity atol=2e-9, acceleration atol=2e-7 with rtol=2e-12; smoothing atol=1e-9, rtol=1e-12. Derivative tolerances account for cancellation in differentiated fits, not clinical rescaling. NaN/Inf masks must match exactly. Inactive samples and skipped windows stay zero.

Real-data validation used disposable copies of two C3D trials with their existing XML, calibration and sidecar events. Every model and modeled-marker numeric array was compared, including joint-center markers, angles, muscle lengths/velocities, forces, moments, reactions and powers. There are 298 arrays in the dual-plate diagnostic run; the single-/no-plate configurations have their own output sets. All comparisons pass at atol=1e-8, rtol=2e-11, with identical nonfinite masks. The largest absolute stored-output difference across final configurations was 8.73e-11. Generated GCD lines match numerically after excluding only creation timestamp and disposable source paths; no numerical curve differences were found.

Configurations: no plate, right FP0, left FP0 on the second trial, and FP0 assigned to both sides as a computational branch diagnostic. Assigning the same physical plate to both sides is not a claim of physiologically valid clinical plate assignment.

## Paired offline benchmark

Three sequential, alternating original/optimized process pairs used identical copies, hardware, Python/NumPy, trial and settings. No competing benchmark process was running. The trial has 1,027 stored frames; the existing active interval and all calibration choices are unchanged. Medians below are not profiled timings. Total includes module import/C3D extraction, Dynamic calculation, GCD and capture overhead; it excludes interpreter launch, UI and live QTM latency.

| Measurement (seconds) | Original median | Optimized median | Original / optimized |
|---|---:|---:|---:|
| dynamic_s | 3.382233 | 1.019849 | 3.32× |
| total_s | 4.976012 | 2.598387 | 1.92× |
| import_and_extraction_s | 1.410449 | 1.444932 | 0.98× |
| gcd_s | 0.029795 | 0.033093 | 0.90× |

Peak process working set (Windows GetProcessMemoryInfo): 189.60 MiB original, 189.67 MiB optimized. This small difference is process noise, not evidence of a memory reduction.

### Stage measurements

One additional sequential pair used identical AST-inserted timers. These explain the distribution and are not the uninstrumented medians above. Kinetics includes its own smoothing/differentiation and output preparation; coordinate and angle stages retain scalar main-loop work.

| Stage | Original seconds | Optimized seconds |
|---|---:|---:|
| C3D extraction | 0.189589 | 0.182745 |
| marker_preprocessing | 0.014369 | 0.015274 |
| coordinate_systems_and_joint_centers | 0.147335 | 0.156861 |
| joint_angles_and_signs | 0.043387 | 0.049096 |
| muscles_COM_and_storage | 0.328869 | 0.435533 |
| output_and_muscle_derivatives | 0.370169 | 0.028949 |
| kinetics_including_smoothing_and_derivatives | 2.307268 | 0.328138 |
| GCD generation | 0.030534 | 0.037527 |
| Live QTM communication | Not measured; calls suppressed | Not measured; calls suppressed |

The same 1 force-plate getter, 13 modeled-marker creations and 13 trajectory writes were recorded in original/optimized dual-plate runs. The offline recorder does not serialize or send them, so these timings cannot predict network/bridge latency.

### Numerical kernels (1,000 synthetic frames)

Seven repeats after warm-up; median time. Batched CS/Euler kernel results demonstrate helper performance, not full-main-loop speedups: those calculations still run per frame in the main processor.

| Kernel | Original seconds | Batched seconds | Speedup | Peak traced bytes, original / batched |
|---|---:|---:|---:|---:|
| seven_point_cubic_derivatives | 0.148067 | 0.000932 | 158.9× | 201640 / 669175 |
| cubic_smoothing | 0.041720 | 0.000306 | 136.5× | 36648 / 227595 |
| pelvis_coordinate_systems | 0.045211 | 0.000140 | 322.5× | 419180 / 217272 |
| YXZ_angles | 0.006097 | 0.000172 | 35.4× | 150560 / 121404 |

Hardware/runtime: Windows-10-10.0.26200-SP0; Intel64 Family 6 Model 151 Stepping 5, GenuineIntel; Python 3.9.25; NumPy 1.26.4.

## Remaining bottlenecks and correctness limits

- The main kinematics/muscle loop, muscle attachment/wrapping logic and both inverse-dynamics loops remain. Coordinate/Euler helpers support batches, but complete batched orchestration is not enabled without broader real calibration coverage. Repeated coordinate reconstruction inside kinetics and Python attachment calculations remain opportunities.
- All available real calibration files examined have the multi-segment foot flags disabled. Foot geometry, transformations and enable branches have synthetic regression coverage; complete real-data LHFGA/RHFGA, LFFGA/RFFGA, LHXGA/RHXGA, LANKA/RANKA, LMDFA/RMDFA and LHLXA/RHLXA equivalence with sitting-foot, Pelfix, AFO and tibial-triad options remains unverified. Their existing model paths/output names are retained.
- The original marker fallback can produce zeros with Exists=False, while some modeled outputs later use an all-true exists list. This pre-existing validity-provenance issue is documented in the audit and is not silently repaired by a speed refactor. Numerical equality to the original does not establish clinical validity. No nan_to_num, arcsin clipping or new identity-matrix fallback was introduced.
- Startup/import and unchanged C3D extraction now occupy a substantial fraction of the offline run. GCD has no measured speedup. Live QTM/GUI performance, all force-plate hardware/analog-rate configurations and full sitting-foot/AFO clinical datasets were not tested.

## Reproduce / evidence

- `tests/test_dynamic_numpy.py`, `tests/fixtures/legacy_dynamic_math.py`, `legacy_dynamic_gait.py`, `legacy_dynamic_reconstruction.py`: frozen formula comparisons; no patient data in fixtures.
- `python -m pytest tests/test_dynamic_numpy.py -q` and `python tests/benchmark_dynamic_numpy.py`. On the Windows Conda processing environment, launch with its Library/bin on PATH; disable unrelated pytest auto-plugins if they load conflicting LAPACK DLLs. The verified run used PYTEST_DISABLE_PLUGIN_AUTOLOAD=1.
- `docs/dynamic_numpy_audit.md` and `docs/dynamic_numpy_loop_inventory.md`: reviewed audit/plan plus complete original loop/call inventory.
- Full private validation artifacts: `C:\Users\ADMIN\Desktop\C\codex\output\dynamic_vectorization_2026-10-23`. Includes untouched baseline source, run_trial.py, benchmark_suite.py, compare.py, original/optimized logs, arrays, disposable GCD files, profile, per-array comparison JSON, benchmark_results.json, core_benchmark.json and input hashes.
- SHA256 integrity: all 271 monitored original clinical/configuration files unchanged across the suite; logs and live SQLite bookkeeping were excluded. The runner only writes to external disposable copies. Existing unrelated working-tree changes were preserved.

This is a measured, validated incremental optimization. Complete clinical equivalence across every supported model option and a fully batched end-to-end processor are not claimed.
