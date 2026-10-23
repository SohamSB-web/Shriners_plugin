# Headless static calibration refactor

Date: 2026-10-23. Baseline: `e6b06a1` (`main`). Branch: `refactor/static-headless`.
Isolated checkout: `C:\Users\ADMIN\Music\Shriners_static_headless`.

The original working directory contains another agent's changes to the math
modules. None were copied, reset, stashed, edited or overwritten. No commits,
merges, cherry-picks or pushes were performed. The desktop worktree tool could
not resolve the project from this chat's working directory; the worktree was
created with native Git instead. It is a normal Git worktree.

## Before and after

Before: PySide6 page → processing service → `Py3_StaticMain.py --headless` →
legacy Qt/Tk compatibility application → patient-page construction (twice) →
QA-page construction → calibration-report-page construction → nested save
closures → QTM commands. The hidden backend still required QApplication,
widgets and event processing. A modeled-marker exception was printed as a
notice and the original command exited successfully.

After: existing PySide6 page → unchanged processing service → thin CLI →
static C3D loader → plain clinical inputs → marker QA → marker/coordinate
calculations → calibration serialization → modeled-marker generation → atomic
calibration publication → existing acknowledged QTM commands. There is no
legacy application, UI page, Qt/Tk import or event loop in the backend path.
The existing user-facing application layout and input fields are unchanged.

The CLI keeps `--sessionPath/-s`, `--filename/-f`,
`--TestingCondition/-t`, and `--headless`. The session argument is the XML
**file**, not a directory. The available recording used for validation is
`Static 3.qtm`; the example `Static 1.qtm` was not assumed to exist.
An optional `--reportPath` accepts a PDF destination without opening a dialog.
Invoking the script without `--headless` also uses the headless engine; the
existing Shriners application is the sole static-analysis interface.

## Audit and dependency map

Original line numbers below refer to `e6b06a1`.

| Original method/block | Calculation or side effect | New responsibility |
| --- | --- | --- |
| Module initialization, 133–159 | XML measurement lookup, C3D extraction; calibration/sitting-file lookup | `static_trial.load_static_trial()` and engine path resolution |
| `PatientInfo_Page.build_UI()`, 269–1007 | Widgets; defaults; persisted/preferences/sitting/BF loading; field/unit precedence | `populate_clinical_inputs()` returns plain values; no controls |
| Nested `saveSubjectData()`, 824–1007 | Serialize preferences and patient settings; preserve matrix/Pelfix tail | `save_clinical_inputs()` initializes new calibration files only |
| `QAreport_Page.build_UI()`, 1314–2480 | Normalize clinical lengths; marker QA; Pelfix reconstruction; missing heel/toe reconstruction; clinical/marker comparisons; KAD checks; Pelfix serialization | `validate_static_markers()` returns stage data and structured warnings; writes only the per-run staging file |
| `StaticSubjectCalibrationReport_Page.build_UI()`, 2739–3245 | Load marker vectors, trunk availability, triad handling and static-forward rotation | `load_calibration_markers()` |
| Same method, 3250–3632 | Hip-model and shank options; joint centers; segment technical systems | `compute_joint_centers_and_technical_systems()` |
| Same method, 3638–3778 | Anatomical systems, hindfoot/forefoot/hallux; sitting-file transforms | `compute_anatomical_systems_and_foot()` |
| Same method, 3784–4099 | Anatomical-to-technical matrices; posture/sign conventions; tibial torsion | `compute_transforms_and_posture()` |
| Same method, 4107–4815 | Format posture values/directions into UI entries | `format_calibration_report()` returns display strings for reporting |
| Nested `saveTransformationMatrices()`, 4884–5478 | Serialize existing parameter/matrix names | `save_transformation_matrices()` writes the staging calibration |
| Nested `saveResultsinC3D()`, 5480–6416 | Per-frame joint centers, virtual markers, CreateModelMarker/SetTrajectory calls | `generate_modeled_markers()` buffers the original API payloads; transport runs afterward |
| Nested `savePdf()`, 6426–8550 | File chooser plus existing multipage ReportLab layout | `save_calibration_report()` accepts an explicit path; layout retained |

All window/layout/label/entry/menu/button/scrollbar construction, the legacy
`Static_Main`, the three page classes, their `build_UI()` methods,
`QApplication.processEvents()`, and the backend GUI/gRPC-server main loop were
removed from the processing path. There is no replacement backend GUI.

The old implicit module inputs were `fields`, `SubjectName`, `FilePath`,
`FileName`, testing condition/default, calibration/sitting/preferences paths,
and imported math/gAPI functions. Clinical values were `self.value*` attributes;
other preferences were also stored on widget instances. Nested save closures
captured calculated vectors/matrices, frame bounds and UI controls. These are
now explicit entries in a dictionary owned by one `run_static_calibration()`
invocation. `self` inside extracted equations is a SimpleNamespace of data,
never a widget. Stages accept that dictionary and return calculated values.
There is no shared mutable session state. Warning and report strings use
separate collections; empty report strings reproduce empty display entries,
not clinical defaults. The PDF renderer imports ReportLab only when requested.

## Math, parameters and persistence

The original equations, evaluation order within each calculation block,
marker tests, axis/sign conventions, frame offsets, unit heuristics, KAD,
triad/Pelfix choices, foot/sitting transformations and calibration names were
retained. An AST regression compares **all gait/math function calls**, including
optional branches, with the original calculation blocks. This is structural
evidence, not a substitute for clinical recordings exercising those branches.

Existing reviewed calibration parameters and their serialized types are
preserved. The original headless implementation never actually invoked its
`saveSubjectData()` closure; the refactor likewise does not rewrite existing
clinical settings from the patient-page population logic. New files use the
extracted existing serializer, with type/finite/frame validation first. Missing
or invalid required inputs raise errors; optional Calcaneal Pitch, Hindfoot
Progression and First Metatarsal Pitch remain empty where the original
formulas derive them from markers. Sitting transforms retain precedence.

One existing defect was confirmed experimentally: `saveResultsinC3D()` reloaded
length strings from disk without the normalization used by the calibration
stage. The baseline raised `TypeError: can't multiply sequence by non-int of
type 'float'` in the Harrington2 calculation. The extracted modeled-marker
stage normalizes immediately after that reload. No formula changed. Regression
results distinguish the exact baseline from a baseline with only this missing
normalization call supplied; only the latter can produce complete reference
modeled-marker trajectories for the available files.

Generated output remains `Calibration/Static_<condition>_<C3D subject>.py`,
with the original existing root-level fallback retained. Names, units, vectors,
3×3 transformation matrices and Python assignment serialization are unchanged.
Both left/right hindfoot, forefoot and hallux `value*AnatRelTech` assignments
were retained. Output is staged in a unique directory next to its destination,
parsed and checked for finite 3×3 matrices, then replaced atomically only after
calculation and marker generation succeed. A failure retains the prior file.
Calibration redirects outside the session are rejected. The Pelfix branch reads
its selected assignment lines directly rather than using the shared system
temporary file `Pelfix.py`.

No original C3D, QTM, session XML, data.qpr, Settings, or patient files were
modified. The function formerly named `saveResultsinC3D()` actually issued QTM
commands; the new backend also does not rewrite patient C3Ds.

## QTM and completion

Payload construction reuses the **unchanged** `gapi.SetTrajectory()` and
`CreateModeledMarker()` function bodies with a per-run collector. Payloads retain
the exact trajectory coordinates, validity flags and `source_start` offset.
QA reconstructions and final modeled-marker commands retain their relative
command order. Publication precedes live output, so a computation failure sends
no commands. QTM commands then execute serially through the existing
`grpc_send_command()` mechanism, which checks the bridge acknowledgement.
No new QTM methods, synchronization services or native file writes were added.

CLI statuses: **0** = calculation and all QTM acknowledgements succeeded;
**1** = input/calculation/persistence/report error; **2** = calibration saved but
QTM output failed or was unavailable. The first failed QTM command and number
remaining are reported. The application already displays nonzero exits as an
error; its existing error display includes the concise final partial-status
line. No success is fabricated for an unavailable bridge.

This retains the existing bridge's active-measurement targeting semantics.
Native target ownership, actual trajectory read-back and persistence in a live
QTM project were **not verified**. No bridge changes or measurement auto-opening
were introduced. Operators still need the intended static measurement open in
QTM when running the existing output pathway.

## Verification

Environment: Windows, Conda `python-example`, Python 3.9, 12 logical CPUs.
All numerical runs used disposable copies. Regression probes refuse sessions
without a disposable-copy marker. Native commands were intercepted and
acknowledged offline; no clinical project was used as a write target.

- Two available `Static 3.c3d` session copies were compared with committed source.
  For the first, **127 common numeric results** matched at `rtol=1e-12`,
  `atol=1e-10`; all saved parameter values/types and transformation matrices
  matched. The second session's equivalence test also passed.
- All **16 modeled-marker commands**, including complete trajectory arrays,
  validity flags and offsets, matched the normalized reference.
- Static-only extraction matched every original point, metadata and frame value;
  only unused `FP` was omitted. Neither original point scaling nor offsets changed.
- Guarded imports reject Qt/Tk; the real service-launched backend completed with
  that guard active. The GUI timer continued ticking and stages 1–7 arrived.
- Verified missing required markers, missing optional trunk markers, invalid/
  empty/nonfinite/negative numeric inputs, empty optional foot angles, failed
  calculations/marker generation, repeated parameter loading, existing root
  calibration compatibility, PDF generation and partial QTM acknowledgement.
- Original C3D/XML/QTM hashes were unchanged in the isolated tests. The benchmark
  also checked hashes of all original files it copied.
- Final focused selection: **26 passed, 48 deselected** (10.10 seconds),
  including the guarded probes and additional loader/matrix checks. The four
  adapted legacy helper cases also passed independently.
- Broader combined run: **43 passed, 28 failed**. Failures are in older GUI
  local-only Save/selection expectations, not backend equation comparisons.
  Representative failure was reproduced on a separate untouched `git archive
  HEAD` copy: expected `Parameters saved successfully.`, received the baseline's
  `Saved locally; updating QTM…`. Those unrelated assertions and GUI functions
  were not changed. A clean full-suite result is not claimed.

The available recordings have foot models disabled, M/L knee markers and no
Pelfix. No saved sitting-foot calibrations were available. Numerically equivalent
enabled left/right/bilateral foot, KAD, Pelfix 1/2, shod/AFO, tibial-triad and
sitting-foot workflows therefore remain **unverified with representative clinical
datasets**. Their source branches and math calls were preserved. Optional angle
and marker fallback behavior has focused coverage; this is not clinical clearance
for all configurations. PDF file generation was checked, not a visual layout audit.

## Performance

Detailed repeated measurements: [static_headless_benchmark.json](static_headless_benchmark.json).
Medians of three separate child processes per mode, same actual trial copies,
offline QTM acknowledgements. This machine was also used by another workstream;
these are local observations, not universal performance guarantees.

| Measurement (seconds) | Original | Original + marker normalization | Headless engine |
| --- | ---: | ---: | ---: |
| Entire child-process wall time | 1.835 | 1.893 | 1.020 |
| Startup/import/initial loading* | 1.566 | 1.595 | 0.677 |
| C3D/metadata loading | 0.0307 | 0.0293 | 0.0251 |
| Clinical population | 0.0107 | 0.0087 | 0.0105 |
| Marker QA | 0.0057 | 0.0052 | 0.0011 |
| Calibration marker preparation | included in report build | included | 0.0018 |
| Joint centers + technical systems | included in report build | included | 0.00048 |
| Anatomical systems + foot | included in report build | included | 0.00048 |
| Transformations + posture | included in report build | included | 0.00034 |
| Whole old calibration report build | 0.0160 | 0.0149 | no UI build |
| Matrix serialization | 0.00087 | 0.00094 | 0.00087 |
| Modeled-marker generation | failed | 0.0511 | 0.0433 |
| Offline command serialization/acknowledgement | included | included | 0.0017 |

*The old startup measure includes initial C3D extraction and reading baseline
source. The probe imports NumPy before the engine import timer. It is not a pure
interpreter-startup comparison. Whole child-process wall time includes startup,
probe serialization and shutdown, and is the directly comparable end-to-end
measurement. The complete normalized reference versus engine was about **1.86×**
faster (46% less wall time) for this trial. Live gRPC latency was not benchmarked.
All 32 legacy serializer parameter/matrix names were also compared structurally and preserved.
No gait equations were vectorized. The largest difference is avoiding GUI and
dynamic utility imports; force-plate extraction is skipped because the entire
static source contains no consumer of `fields['FP']`.

## Commands and changed files

Isolation: `git status --short`, `git branch --show-current`, `git worktree list`,
`git worktree add -b refactor/static-headless C:/Users/ADMIN/Music/Shriners_static_headless main`.
Audit/baseline: `rg`, Python `ast`/`symtable`, `git show e6b06a1:...`, and
`git archive HEAD` into a disposable baseline directory. Verification:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
$env:STATIC_REFERENCE_SESSION = '<read-only original session directory>'
conda run --no-capture-output -n python-example python -B -m pytest `
  tests/test_static_headless_engine.py tests/test_local_calibration_workflow.py `
  -k 'headless or original_math or static_loader or clinical_equivalence or qtm_failure_is_partial or failed_calculation or invalid_clinical or missing_required or command_payload or cli_returns or optional_foot or processing_service_keeps or legacy_root' `
  -q -p no:cacheprovider --disable-warnings
conda run --no-capture-output -n python-example python -B tests/benchmark_static_headless.py `
  --session '<read-only original session directory>' --filename 'Static 3.qtm' `
  --output docs/static_headless_benchmark.json --repeats 3
git diff --check
```

Changed files:

1. `Gait-lab-Vicon-to-QTM/Py3_StaticMain.py`: thin CLI, progress and exit status.
2. `Gait-lab-Vicon-to-QTM/static_trial.py`: static-only loader.
3. `Gait-lab-Vicon-to-QTM/static_calibration_parameters.py`: plain clinical inputs and existing serialization.
4. `Gait-lab-Vicon-to-QTM/static_calibration_calculations.py`: extracted original QA/math/output functions.
5. `Gait-lab-Vicon-to-QTM/static_calibration_engine.py`: per-run orchestration, timings, staging and QTM acknowledgement handling.
6. `Gait-lab-Vicon-to-QTM/static_calibration_report.py`: original PDF layout without controls/dialogs.
7. `tests/test_static_headless_engine.py`: headless, numerical, persistence, command and service integration checks.
8. `tests/test_local_calibration_workflow.py`: adapt only the three legacy test functions (four current cases) that depended on removed page/helper definitions.
9. `tests/static_calibration_probe.py`: guarded disposable-copy baseline/engine comparison.
10. `tests/benchmark_static_headless.py`: repeated isolated benchmark.
11. `docs/static_headless_benchmark.json`: measured timings, no clinical arrays or patient values.
12. `docs/static_headless_refactor.md`: this audit and validation record.

`output/` also contains disposable baseline code, copied trial inputs and raw
comparison logs generated during validation. Automatic approval review blocked
cleanup of that folder without a specific reason; it remains untracked in this
isolated worktree. It is not an implementation deliverable and must not be
included in a later clinical-data-free source commit.

## Integration restrictions

`processing_service.py`, `static_analysis_page.py`, all listed shared dynamic/
math/extraction/gapi files, QTM templates, and QTM bridge copies are unchanged.
Separate legacy `Py3_SittingFootStaticMain.py` and QTM's template static script
still contain their old UI code; neither is imported by this application backend.
Existing saved sitting-foot outputs remain supported as inputs, subject to the
unverified-dataset restriction above.

The dynamic agent may change shared math function implementations or signatures.
This branch tested committed versions only. Re-run the numerical comparisons
against the eventual combined source before clinical rollout. The static refactor
has **not** been merged into the original application's checkout or deployed.
