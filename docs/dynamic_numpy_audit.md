# Dynamic processing: original-source audit and optimization plan

2026-10-23. Source: C:\Users\ADMIN\Music\Shriners_plugin. Line numbers below refer to the untouched baseline_source snapshot. The exhaustive loop/call inventory is in loop_inventory.md and loop_inventory.json. All eight requested files were parsed in full. Clinical files and the original source ZIP remain untouched.

## All frame loops and dependencies

| Original file and lines | Purpose / called functions | Classification | Expected benefit and numerical risk |
|---|---|---|---|
| Py3_varExtractor.py:10–251,254–325 | ezc3d extraction, events, force plates and units; exact XML measurement lookup | I/O-bound / partly vectorizable | Preserve event precedence, frame offsets, coordinate units. Measure separately. |
| Py3_DynamicMain.py:127–140 | MarkerArrayCheck returns zero trajectories and Exists=False for missing markers | Requires further investigation | False masks must never be promoted to valid clinical data by a new batch path. |
| Py3_DynamicMain.py:241–309 | Pelfix ASIS reconstruction, TechCS_Pelvis_Newington and TransformPointIntoLabCoors; iliac or posterior triad | Fully vectorizable | Batch original marker axes and static transformation; preserve selected interval and unused zeros. |
| Py3_DynamicMain.py:399–476 | L/R virtual metatarsal head: TechCS_Forefoot_mSHCG and static local point | Fully vectorizable | Preserve separate limb flags, origins, axis order and signs. |
| Py3_DynamicMain.py:579–588 | Sacrum fallback midpoint of PSIS | Fully vectorizable | Preserve active interval and zeros outside it. |
| Py3_DynamicMain.py:815–819 | Determine whether medial ankle drops out anywhere in trial | Fully vectorizable reduction | Keep current whole-trial fallback, not a new per-frame decision. |
| Py3_DynamicMain.py:1333–4189 | Kinematics, muscles, COM and output storage; detailed breakdown below | Partially vectorizable | Scalar branches and list output bookkeeping require incremental validation. |
| Py3_DynamicMain.py:4483–4486 | reArrangeArray swaps flexion/abduction rows | Fully vectorizable | Preserve independent output lists and length. |
| Py3_DynamicMain.py:5545–6460,6760–7679 | Left/right inverse dynamics after derivatives and plate assignment | Partially vectorizable | Force/moment algebra is pointwise, but contact thresholds, sample-rate conversion and ankle→knee→hip chain need proof. |
| Py3_MathModules.py:190–220 | AngVelAcc_Euler_YXZ converts derivatives to angular velocity/acceleration | Fully vectorizable after differentiation | Preserve arithmetic, 1-based inclusive interval and inactive zeros. |
| Py3_MathModules.py:289–340 | Differentiate fits cubic to seven neighboring samples for each axis/frame | Vectorizable with time-window dependency | Solve same scaled design matrix for many RHS, never substitute np.gradient; preserve invalid-window skip and boundary evaluation. |
| Py3_MathModules.py:342–381 | Smooth1DArray cubic polynomial windows; Order is currently ignored | Partially vectorizable | Preserve actual degree and asymmetric boundary behavior. |
| Py3_MathModules.py:383–411 | Smooth3DArray copy loops and Trim3DList | Fully vectorizable copies | Preserve one-based bounds, return type and copy ownership. |
| Py3_MathModules.py:413–457 | ComputeMuscleLength transforms/mirrors attachment points, sums segment distances | Partially vectorizable | Small attachment loop can stay; frame batching must reproduce muscle wrapping thresholds. |
| Py3_GaitModules.py:198–245 | Spatial plate polygon membership per frame | Partially vectorizable | Polygon boundaries and missing-marker handling must match. |
| Py3_GaitModules.py:248–1489 | Event detection, adaptive threshold search, ordering, pairing and minimum detections | Sequential event logic | Retain event order and fallback decisions. |
| Py3_CreateGCD.py:153–304,366–378 | Event rounding, cycle/force/EMG extraction, interpolation and envelopes | Partially vectorizable / I/O-bound | Preserve indexing, signs, sample rates and normalization. |
| Py3_CreateGCD.py:423–541,796–917 | Side-specific gait-cycle and contralateral-event associations | Sequential / I/O-bound | Retain missing-event and cycle-selection logic. |
| Py3_Utils.py:563–644 | C3D force-plate conversion | Partially vectorizable / I/O-bound | Preserve offsets, orientation, analog rate and plate IDs. |
| gapi.py:59–98,174–180; Py3_Utils.py:87–111 | Socket check, channel, JSON and commands per trajectory | I/O-bound | SetTrajectory already sends a trajectory. No verified multi-command API: do not invent batching or retries. |
| app/services/processing_service.py:83–171,228–327 | Child process, pipes, progress parsing, cancellation | I/O-bound / sequential lifecycle | Keep parser-compatible Frame n/N messages; throttle producer, preserve diagnostics. |

The inventory includes every for/while and comprehension: DynamicMain 333, GaitModules 62, MathModules 33, CreateGCD 59, varExtractor 12, Utils 21, gapi 6, processing_service 2. Calls include nested branches and are not necessarily executed for every option. Its preliminary automatic classifications are superseded by this reviewed table.

## Numerical core

| DynamicMain original lines | Calculation | Vectorization opportunity | Invariants and risks |
|---|---|---|---|
| 1336–1691 | Dozens of new marker 3-vectors each frame | Batched (frames,3) preparation | Preserve current X/Y Direction handling, including existing exceptions; optional branches cannot access absent arrays. |
| 1692–1710 | Trunk technical/anatomical CS | Batched axes, further type investigation | Preserve deliberate ETrunkAnat=ETrunkTech overwrite and missing-trunk behavior. |
| 1711–1803 | Pelvis and three hip-center regressions | Batched norms/cross products/affine points | Harrington pelvic depth varies by frame; Newington local center is constant. No regression coefficient changes. |
| 1804–1905 | Thigh, shank, ankle centers, standard foot | Fully vectorizable within configured branch | Preserve triads, medial-ankle whole-trial fallback and left/right cross-product order. |
| 1906–2061 | Hindfoot, forefoot, hallux matrices and virtual heel | Fully vectorizable | Preserve sitting-foot, BF/AFO and optional foot flags; retain absent secondary-foot calibration fallback. |
| 2063–2214 | Segment, hip, knee, ankle and six multi-segment foot angle families | Batched original Euler expressions | Preserve YXZ/ZXY dot/arcsin/atan2 formulas, singularities, radian order, progression CS and Hallux Z==0 fallback. No SciPy substitution or arcsin clipping. |
| 2215–2318 | Degrees, L/R signs, radians for kinetics | Batched arithmetic/storage | Preserve clinical component order and every output name. |
| 2324–3600 | Knee/patella polynomials and Delp muscle paths | Partial: point transformations; wrapping decisions require proof | Muscle-specific angle thresholds choose attachments. Retain until equivalent across branches. |
| 3600–4189 | COM, joint/segment/marker output storage | Pointwise / partially vectorizable | Zero-length COM currently yields NaN; do not algebraically simplify it into a plausible point. |

Axes are columns: TransformAnatCoorSysFromTechCoors = ETech @ EAnatRelTech; reverse = ETech.T @ EAnat. Point = ETech @ local + origin. No active np.linalg.inv calls occur in the inspected core. An inverse is not interchangeable with a transpose for invalid/nonorthogonal axes.

Repeated allocations include many 3×frames list comprehensions and small matrices/vectors. Repeated normalization is present in ComputeUnitVecFromPts. JSON model export at DynamicMain:8096 is commented out; trajectory JSON is outside the main frame loop. Progress at :1334 logs every frame after 300, increasing pipe/UI work.

## Missing-marker correctness issue, separate from optimization

MarkerArrayCheck supplies Exists=False, but reconstruction/model output blocks use exists=[True]*framecount (for example :239 and :397). Zero-filled markers can therefore reach formulas that return finite angles. This is a pre-existing clinical-validity risk. Do not use nan_to_num, clipping, identity fallbacks or changed event selection to hide it. Preserve nonfinite masks in equivalence tests. A comprehensive output-validity policy is a separate correction and is not silently bundled here.

## Ordered plan and validation gates

1. Snapshot original source, fingerprint clinical inputs, copy an actual C3D/XML/calibration to an external disposable directory, suppress all QTM writes, capture every model/marker array and GCD. Profile separately from timed runs.
2. Compare original scalar functions before changes; extend only proven helpers to (...,3)/(...,3,3), preserving public names and scalar behavior. Test left/right, zero/NaN/degenerate/singular data and static matrices.
3. Batch independent reconstruction/marker operations using the existing helpers. Remove redundant same-frame work only when equivalent. Throttle progress to first/last and each 50 frames.
4. Batch seven-point cubic differentiation with the original scaled polynomial solve and edge evaluation. Compare real intermediate arrays, noise, constants, invalid windows, short trials and partial ranges. Retain old arithmetic if tight tolerances fail.
5. Benchmark numerical kernels and repeated identical offline full runs. Report extraction, preprocessing, coordinates, angles, kinetics, communication, GCD, total and peak memory separately where measured; explicitly mark unmeasured stages. Offline timings do not measure live QTM latency or the whole UI.
6. Keep unproven muscle wrapping, inverse dynamics, filters, event logic and GCD formatting unchanged. Expand only with original-versus-optimized comparisons; report residual bottlenecks and option coverage.

Expected benefits are hypotheses until measured. Original clinical files and source ZIPs must remain unchanged; no new dependencies, commits or pushes are needed.
