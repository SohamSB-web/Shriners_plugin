# Static headless offline-processing correction

Date: 2026-10-24. Worktree: `C:\Users\ADMIN\Music\Shriners_static_headless`.
Branch: `refactor/static-headless`; starting HEAD: `9f70fe8`.
Reference fetched with `git fetch origin main`: `e6b06a1d25454e92c81ff6f4477f1036b9526f1f`.

## 1. Confirmed regression and reproduction

The numerical engine already read the selected C3D locally through ezc3d. It did
not need active QTM measurement data or force plates. The regression was after
calculation: `run_static_calibration()` unconditionally called `write_qtm_outputs()`
(pre-fix engine line 189). `CreateModelMarker` was the first of 16 buffered commands.
Without an available QTM measurement, `gapi.grpc_send_command()` returned `None`;
`write_qtm_outputs()` raised and caught `RuntimeError("QTM unavailable or command
rejected")` (pre-fix line 99), returning `qtm_errors`. `CalibrationResult.success`
(line 36) consequently became false, and CLI `main()` returned 2.

This happened **after valid transformation matrices had been saved**. Opening a
measurement allowed the native trajectory API to service uploads, making an
otherwise identical local calculation appear successful. The earlier QTM console
reported `qtm.data.object.trajectory.find_trajectory: method requires a measurement`.
It was not a missing C3D, missing patient input, force-plate dependency or hidden UI.

QTM was running during this investigation. The user explicitly requested that it
remain open. To reproduce safely, a test-only launcher changed gapi's destination
port to an unused localhost port (51827), then executed the unmodified pre-fix CLI
against a disposable session copy. The real transport performed its connection
preflight; no fake ACK was supplied and no clinical measurement was written.
The publisher attempted `CreateModelMarker`, but no gRPC request was transmitted
because the port preflight failed. C3D loading, clinical inputs, calculations,
matrix validation and local marker generation all completed; subprocess exit: 2.
No uncaught traceback existed for this particular failure: the writer caught its
own exception and converted it to `qtm_errors`. That absence is not a missing log.

Full command, cwd, interpreter, environment, stdout and stderr are retained in
`logs/static_offline_2026-10-24/before.json`, `before.stdout.log` and
`before.stderr.log`. These artifacts were initially generated under
`output/static_offline_2026-10-24` and subsequently moved, without deleting or
overwriting existing files, under ignored `logs/` to keep copied clinical data
out of Git. Invocation manifests retain their actual original execution paths.
Interpreter: `C:\Users\ADMIN\anaconda3\envs\python-example\python.exe` (Python 3.9).
The initial subprocess cwd was this worktree's `Gait-lab-Vicon-to-QTM` directory.
Relevant environment: `CONDA_DEFAULT_ENV=python-example`, `QT_QPA_PLATFORM=offscreen`,
`SHRINERS_NON_INTERACTIVE=1`, `SHRINERS_AUTO_SELECT_CYCLE=1`; full invocation is in JSON.

## 2. GitHub main comparison

Inspected all eight requested files using fetched Git objects and local source.
At the initial worktree HEAD, only `Py3_StaticMain.py` differed from main among
these eight files; the other seven were byte-identical Git versions.

| Reference source | Confirmed behavior |
| --- | --- |
| `Py3_StaticMain.py` | Reads the chosen XML measurement's sibling C3D; uses C3D subject metadata, persisted clinical parameters and model preferences; calculates through legacy page builders; saves matrices before attempting marker publishing. The headless tail catches marker-output errors and still finishes. |
| `Py3_varExtractor.py` | Loads points/PROCESSING data with ezc3d; the shared static/dynamic extractor also unnecessarily calls force-plate extraction for static work. |
| `Py3_Utils.py` | `ProcessForceplateData()` queries QTM COP but supports C3D force-plate fallback when QTM is unavailable. Static calibration equations do not consume its FP result. |
| `gapi.py` | Unreachable port or rejected native operation returns `None`; legacy trajectory/marker wrappers do not make it a fatal calibration error. |
| `Py3_GaitModules.py`, `Py3_MathModules.py` | Coordinate systems, joint centers, offsets and transformation calculations are shared mathematical functions. No formulas changed in this correction. |
| `processing_service.py` | Launches the local static entry point asynchronously with XML path, selected filename, condition and `--headless`; inherits the existing Conda runtime/DLL environment. No source changes needed. |
| `static_analysis_page.py` | Saves reviewed local parameters before launching the service. Previously Browse accepted only XML and chose a referenced static trial. Only Browse was extended here. |

The actual fetched main CLI was also run on a disposable copy, with the same real
transport disconnected by a test-only port override. It returned **0**, saved its
matrices, and printed `Notice: saveResultsinC3D: can't multiply sequence by non-int
of type 'float'`. Therefore main's successful offline exit is verified, but its
claim that C3D results were saved is not treated as proof of native marker output.
The previously documented string-unit bug in that optional output stage remains
visible in the reference. The headless refactor's existing normalization is retained.
Complete reference stdout/stderr and command are in `main.*` under the audit logs.

## 3. Production changes

| File | Functions / exact purpose |
| --- | --- |
| `Gait-lab-Vicon-to-QTM/static_calibration_engine.py` | `_command_collectors()` builds the unchanged marker/trajectory payloads locally without importing gapi/grpc. `run_static_calibration()` defaults to `publish_qtm=False`; only explicit publishing calls the retained `write_qtm_outputs()`. `_validate_calibration()` requires the complete standard matrices and enabled foot-model matrices, with finite 3x3 values. Validation now runs as a diagnostic stage before atomic replacement. `load_clinical_parameters()` also identifies absent required dictionary fields as validation errors. |
| `Gait-lab-Vicon-to-QTM/Py3_StaticMain.py` | `main()`, `_run()`, `_Tee`: default offline CLI; explicit `--publish-qtm` retains optional publishing; unique persistent stdout/stderr logs include invocation and complete Python tracebacks. Local input/numerical failures remain exit 1, explicit publishing failure remains separately reported exit 2. |
| `Gait-lab-Vicon-to-QTM/static_trial.py` | `load_static_trial()`: accepts the precise C3D filename or its existing XML measurement filename; validates unique static XML association, resolved session-local path, readable C3D, nonempty samples, capture rate and frame range. Uses `Path.stem`, preserving dots in filenames. If C3D subject Name is absent, uses the selected session XML Name instead of inventing `Test`; fails if both are absent. |
| `app/ui/pages/static_analysis_page.py` | `_browse_static_file()` accepts C3D as well as XML, matches the exact selected stem to one measurement in its sibling `session.xml`, and passes that chosen C3D filename through the existing workflow. Missing/ambiguous metadata is reported. |

Test changes: `tests/static_calibration_probe.py` compares fetched `origin/main`
and obtains the corrected engine's buffered commands without simulated publishing;
`tests/test_static_headless_engine.py` tests the production CLI, real page/service,
invalid inputs, complete artifacts, local subject fallback and optional publishing.

The numerical modules, parameter serializer, preferences, Dynamic code, shared
processing service, Save Parameters, Fetch QTM, QTM configuration and patient/session
navigation were not modified. No original recording, session XML or clinical
configuration was overwritten. All implementation edits are in this worktree.

## 4. Resulting execution contract

The existing PySide6 page saves reviewed clinical inputs, then the unchanged
service launches the refactored CLI. The engine reads the selected local C3D,
loads persisted measurements/model configuration, runs QA and the original
equations, validates the staged artifact, generates local modeled-marker payloads,
and atomically replaces the calibration. QTM transport is not imported on this
default path. No GUI, QApplication, force-plate extraction or native QTM query is
needed in the backend. No measurement has to be open in QTM.

The normal output remains
`<session>/Calibration/Static_<Condition>_<SubjectName>.py`; existing legitimate
root-level calibration files retain the established fallback. Sitting-foot lookup,
optional foot equations, unit conversions, variable names and matrix orientations
are unchanged. Missing required data does not result in a default calibration.

Publishing is separate and opt-in (`publish_qtm=True` / CLI `--publish-qtm`). The
existing acknowledged writer remains available; its target is the active QTM
measurement, so that explicit operation still requires the intended static trial
to be open. It was not exercised against a clinical recording during this task.
Logs are retained in ignored `logs/static/static-*.log`; the path is printed at
the start of every CLI run and is available through the service's existing log signal.

## 5. Executed verification

Focused command (PowerShell, from this worktree):

```powershell
$env:QT_QPA_PLATFORM='offscreen'
# STATIC_REFERENCE_SESSION points to the representative original session, read-only.
# The fixture copies its XML, C3D and calibration into a disposable temporary session.
& C:/Users/ADMIN/anaconda3/Scripts/conda.exe run --no-capture-output -n python-example python -B -m pytest tests/test_static_headless_engine.py -q -p no:cacheprovider --disable-warnings
```

Final result: **31 passed, 14 warnings, 14.46 seconds**. Complete output is in
`logs/static_offline_2026-10-24/pytest.log`. Also ran `git diff --check` successfully.
Read-only comparisons used `git diff origin/main -- <requested files>` and
`git show origin/main:<file>`; no merge, reset, branch switch, commit or push.

| Required scenario | Actual result and evidence |
| --- | --- |
| A: QTM completely closed | **Not executed**: user explicitly requested keeping QTM open. No claim of literal closed-process verification. |
| B: QTM open on another measurement | **Partial coverage**: read-only `GetActiveMeasurement` returned `Static 3.qtm` before and after. Production CLI processed a separate real-C3D copy named `Static.offline.c3d` with a corresponding disposable XML reference; exit 0. Only disposable filename/XML reference changed; coordinates were real recording data from the same acquisition, not an independent second acquisition. No upload occurred. |
| C: disconnected transport | Pre-fix and main reproduction used real connection refusal on an unused port, with no fake ACK. Corrected default path also passes a full real-C3D CLI run with imports of gapi, grpc, shared live extractor, Qt and Tk forbidden; no transport can be used. Literal closed-QTM test remains unperformed. |
| D: standalone CLI | Actual `Py3_StaticMain.py -s <copy>/session.xml -f "Static 3.c3d" -t BF --headless`, from a foreign cwd, returned 0 and saved validated calibration. No QTM or GUI shim in this production invocation. `after.*` contains exact command/output. |
| E: production PySide6 | Real page, Browse handler, clicked Run button, original service, real launcher and real subprocess reached the completion page. Only file-dialog selection was supplied by the test; no processing result, writer or ACK was mocked. A 20 ms Qt heartbeat continued. Separate real-service integration also passed. Qt ran offscreen; this was not a manual desktop interaction test. |
| F: numerical equivalence | Real C3D and persisted inputs: **127 numerical intermediate values**, max absolute difference **0**; **161 saved fields**, including **12 matrices**, matched reference at `rtol=1e-12`, `atol=1e-10`. All **16 buffered marker commands** matched the reference with its already documented output-only unit normalization. Numerical probes isolate native publishing with a recording sender; they are supplementary mathematical comparisons, not proof of live QTM writes. |
| G: invalid input | Missing/invalid real C3D, missing body mass, invalid frame, invalid output directory, ambiguous/escaping path, malformed matrices and absent markers were rejected without replacing existing calibration. A separate real-C3D copy with marker labels removed by ezc3d returned 1 with matrix-validation traceback; previous calibration bytes remained identical. Optional trunk-marker fallback and headless PDF rendering passed. Full failed-CLI traceback persistence also passed. |
| H: downstream Dynamic | Unmodified `Py3_DynamicMain.py` processed a copied real Dynamic 8 trial against the newly generated calibration: exit 0, GCD **124575 bytes**, **162 variables**, **115 arrays of 101 points**, parsed by the production GCD service. A test-only destination-port override kept Dynamic's existing QTM output attempts disconnected; no ACKs or clinical formulas were mocked. Dynamic emitted an existing divide warning; this is compatibility evidence, not clinical validation of every curve. |

Supplementary checks cover local payload formatting, partial QTM ACK failure,
atomic preservation after injected calculation failure, empty optional foot angles,
legacy root calibration fallback and GUI-free imports. Real recording copies remain
under ignored logs for review; original recordings were inputs only. The original
working repository was not edited. The fetched ref is shared Git metadata, as
explicitly authorized; it was never merged into either worktree.

## 6. Remaining limitations

The real-data configuration exercised BF, Harrington2, distal shank coordinates,
frame 20, medial/lateral knee markers, no Pelfix and no optional multi-segment foot.
Pelfix variants, KAD, tibial-triad, sitting-foot, orthotic conditions and enabled
hindfoot/forefoot/hallux calculations were not numerically exercised on representative
clinical recordings. Their existing equations are unchanged; AST comparison checks
that all legacy math/gait calls, including optional branches, are retained.

Direct C3D selection still requires its existing sibling session XML and unique
measurement association; no standalone patient identity is invented. Logs require
a writable worktree logs directory. Optional live marker publication, hardware,
literal QTM-closed operation and a manual visible-desktop run remain unverified.
The different-active-file check used a renamed copy of the same acquisition;
an independent second compatible static acquisition was not available for that check.
No clinical measurements or physiological defaults were introduced to make tests pass.
