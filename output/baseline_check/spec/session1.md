# Session 1 — QTM trajectories, event coordinates, and case presentation

## 1. Session overview

Date: 2026-10-08. Project: Shriners_Plugin. This record covers the original implementation and the frame-offset follow-up supplied while the session was still active.

Objectives were to correct selected-range trajectory length failures, make modeled-marker creation repeatable, synchronize event positions across detection/QTM/C3D/JSON/UI, and improve the existing Qt MAC Case Presentation without changing clinical calculations or design.

At inspection, `spec/session1.md` did not exist. There was no earlier document to read or append to. This document was created after implementation and verification; the initial implementation history is retained below, followed by the requested follow-up section. The final frame specification supersedes the initial, incorrect zero-based event-frame assumption.

Final status: code implemented; 64 focused automated tests passed; repeated real detector/C3D processing passed; a live event at displayed QTM frame 295 was written and retrieved; QTM's event editor and marker status confirmed the displayed frame. Selected-range trajectory cases were validated using the real handler functions with mocked native writes. Clinical plot rasters were compared against the starting implementation. No commit or push was made.

The checkout already contained many modifications and untracked files. An external start-of-session snapshot recorded 678 file hashes, source/document copies, and Git status. Session changes below are measured against that snapshot, rather than treating all changes against Git HEAD as this session's work.

### Initial implementation history

1. Both QTM adapters received measured-range trajectory mapping, count validation, and marker reuse. Client origins were propagated through modern and template static processing.
2. An initial shared event helper treated QTM scripting indices as displayed event frames. The initial tests used that same incorrect assumption. This was a real error in the investigation, not evidence of a correct physical mapping. The intermediate helper used `frame/frequency`, server retrieval omitted the displayed-frame origin, and metadata used `qtm_absolute_zero_based`.
3. The UI's redundant display increment was removed. That removal remains correct once the model carries actual displayed QTM frames.
4. Plot objects, arrays, and means were reused, duplicate redraws removed, and rapid filter refreshes coalesced. Those optimizations were retained unchanged during the frame follow-up.
5. The initial combined run eventually passed 53 tests after resolving a queued Matplotlib callback accessing a deleted Qt canvas. Separate scroll/session-navigation tests passed. These intermediate passes did not establish the correct event coordinate system.
6. The follow-up supplied the 296/295 and reversed 294/295 observations. Actual QTM APIs, native UI, detector output, and marker coordinates were then inspected. The final mapping and tests below replace the incorrect event assumptions.

## 2. Root cause analysis

### Trajectory sample count

`setTrajectory()` in both `Py3_staticmain.py` adapters sent the entire XYZ sequence to `get_selected_range()`. The selected span could be only 120 samples while the supplied trajectory contained 1,027. A user's current selection is not the source array's origin or length.

The destination now comes from the inclusive measured range or an explicit validated target range. Array position is mapped using a source sample origin. A short payload without origin information fails clearly instead of being guessed, padded, resampled, or truncated.

### Duplicate markers

`createMarker()` called `add_trajectory()` without resolving an existing label. It now returns the existing ID, creates only absent labels, and rechecks after an add failure to handle a competing creation. If no existing marker can explain that failure, the actual error is raised.

### Event synchronization

Three different coordinates had been conflated: array indices, zero-based QTM scripting sample indices, and one-based displayed QTM marker frames. The original auto path used `max(offset, 1)` as a base; that happened to work for uncropped arrays but was wrong for some cropped origins. The original UI added another display increment. Writers disagreed: the baseline auto client subtracted `qtm_base`, whereas application save/send paths used `frame/frequency`. Subtracting a crop origin from an already absolute frame also moved events to the wrong original-measurement time.

The intermediate fix removed the UI increment but incorrectly made event-frame values zero-based, including server reads. Native verification confirmed sample index 354 is displayed as frame 355 at 2.95 s and 120 Hz. Therefore event model frames must use the displayed origin; QTM trajectory ranges must continue using scripting sample indices.

### MAC Case Presentation

`_refresh_plots()` cleared every plot, and `plot_gait_data()` rebuilt axes, references, trial curves, toe-off markers, legends, limits, and layout. `plot_at()` also requested a redraw after the canvas had requested one. Trial arrays and bilateral means were repeatedly prepared. These main-thread preparation costs dominated checkbox interactions.

The legacy Tk application was also inspected: repeated GCD reading and synchronous plotting remain potential costs there. It was not rewritten; the measured optimization is for the existing Qt page.

## 3. Files modified

Paths are relative to the repository. No existing source file or directory was renamed, moved, or deleted.

| File | Change | Reason |
|---|---|---|
| `Gait-lab-Vicon-to-QTM/QTM_GRPC/tools/Py3_staticmain.py` | Trajectory payload handling, measured/source/target validation, marker reuse, shared event conversions and diagnostics | Correct embedded QTM adapter |
| `QTM-GRPC/tools/Py3_staticmain.py` | Same trajectory and event fixes in the second deployed adapter | Keep both entry points consistent |
| `Gait-lab-Vicon-to-QTM/gapi.py` | Serialize source origin/existence; single and bulk event timestamps use the shared displayed-frame boundary; include frame metadata | Preserve physical positions across gRPC |
| `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Templates/gapi.py` | Preserve template's half-open source slice and send its true sample origin | Legacy trajectory compatibility |
| `Gait-lab-Vicon-to-QTM/Py3_StaticMain.py` | Pass C3D initial sample offset to SetTrajectory | Map static arrays to their measurement samples |
| `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Templates/Py3_StaticMain.py` | Pass the same origin to the template client | Match legacy processing |
| `Gait-lab-Vicon-to-QTM/Py3_varExtractor.py` | Combine C3D minutes/seconds; convert absolute event time to the gait consumer's relative one-based convention; correct window boundaries and sidecar fallback | Preserve the sample selected by existing gait calculations |
| `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Templates/Py3_varExtractor.py` | Combine minute/second timestamps, retain relative one-based consumer frames, recognize canonical event labels | Read events saved by current app in legacy processing |
| `Gait-lab-Vicon-to-QTM/auto_event_trigger.py` | Convert detector index using the actual displayed recording origin; serialize convention/origin; use shared timestamp conversion for C3D and QTM; opt-in trace | Correct auto event lifecycle |
| `app/services/frame_coordinates.py` (new) | Pure Python coordinate helpers, provenance migration, opt-in event trace | One explicit event boundary |
| `app/services/event_service.py` | Consistent load/save/C3D/send/fetch/sync coordinates, exact timestamps, migration metadata | Correct manual and retrieved event paths |
| `app/ui/dialogs/event_details_dialog.py` | Show absolute displayed frames directly; correct relative indices, times, and first/last input bounds; resolve C3D origin | Remove duplicate UI adjustment |
| `app/services/gcd_service.py` | Bounded, content-validated immutable NumPy array cache and shared normalized X axis | Avoid repeated array conversion |
| `app/ui/charts/clinical_plots.py` | Reuse artists/references, hide inactive curves, conditionally update layout/legend/limits, remove duplicate draw, guard deleted Qt canvas callback | Reduce graph preparation while preserving output |
| `app/ui/pages/case_presentation_page.py` | Avoid clearing used cells; stable curve identities; bounded bilateral mean cache; zero-delay single-shot refresh coalescing | Keep all 15 canvases and render final filter state |
| `tests/benchmark_case_presentation.py` (new) | Reproducible 20-trial/15-graph perf_counter benchmark | Measure preparation, refresh, raster, and redraws |
| `tests/test_session1_regressions.py` (new) | Focused trajectory, physical frame, C3D/JSON/UI/gRPC, migration, repeated labeling, and artist/cache tests | Protect corrected behavior |
| `tests/test_bilateral_mean_separation.py` | Check visible artists when testing bilateral means | Persistent hidden artists are retained intentionally |
| `tests/test_10_trials_support.py` | Count visible trial curves | Verify user-visible trials with reused artists |
| `Gait-lab-Vicon-to-QTM/test_auto_event_zero_events.py` | Update stub signature and trial identity; intercept gRPC for standalone fixtures | Keep synthetic pipelines isolated from live QTM |
| `test_reports/case_presentation_ideal_range_bilateral.png` (generated) | Existing norm-range test screenshot | Test artifact; not a source or design change |
| `test_reports/case_presentation_ideal_range_dark.png` (generated) | Existing dark norm-range test screenshot | Test artifact |
| `test_reports/pelvic_obliquity_ideal_range_closeup.png` (generated) | Existing norm-range detail screenshot | Test artifact |
| `spec/session1.md` (new) | This implementation, verification, and follow-up record | Mandatory technical documentation |

`app.py`, event detection algorithms, thresholds, signal processing, GCD clinical formulas, and legacy MAC source were inspected and not changed by this session. Some already differ from Git HEAD; those existing changes were preserved.

### Runtime file audit

The initial hash audit found 41 changed non-source files during the session (44 at the final snapshot while the application/QTM remained active): QTM project settings/messages, measurement files and derived outputs from the concurrently observed 20-file QTM batch, event JSON/logs, and session metadata. They are not included as authored code changes. Earlier broad GUI checks instantiated real application settings and may have persisted runtime data. In particular, the `Data/test_002/2025-02-21_0003/auto_event_Dynamic 1_results.json` demo sidecar and `Data/2023-11-17/CGM - Full body_Barefoot/session.xml` changed during the first phase. The snapshot contains their initial hashes, not their original bytes; exact restoration of those runtime files cannot be claimed. They were not guessed at or reverted over concurrent user work. Subsequent detector and C3D checks used temporary copies; the live diagnostic event was removed and the eight original events were compared exactly at cleanup.

Counts are snapshot observations and can change during concurrent processing or synchronization. The complete observed runtime path inventory is retained in the external `shriners-session1-baseline/audit.json`. Runtime outputs are outside the source diff and are a limitation of this session's broad GUI tests, not evidence that all patient files remained byte-identical.

## 4. Detailed implementation changes

### QTM adapters and clients

Both `QtmCommandServicer.SendCommandToQtm()` implementations pass optional `exists`, `source_start`, and `target_range` to `setTrajectory()`. Marker creation acknowledgement includes its resolved ID. `setTrajectory(name, X, Y, Z, exists=None, source_start=None, target_range=None)` validates source lengths, measured bounds, target ordering/integer bounds, and coverage before calling native `set_samples()`.

For a requested inclusive target, mapping is:

```python
first = target_start - source_start
last = target_end - source_start + 1
samples = source[first:last]
assert len(samples) == target_end - target_start + 1
```

Metadata-free full arrays remain supported when their count exactly matches the measured count. A shorter metadata-free payload is ambiguous and rejected. Finite valid positions preserve XYZ and residual zero; missing/invalid coordinates or `exists=False` become native `None` gaps. No clinical trajectory computation was changed.

The modern client preserves its existing full-array payload; its `start/end` arguments remain the processing window, and `offset` identifies full-array element zero. The legacy template continues slicing `[start:end]`, with `source_start=offset+start`. Existing dynamic calls already supplied an offset; static callers now do so too.

`createMarker()` uses `find_trajectory()` before adding, handles ID zero as valid by checking `is not None`, and propagates real creation failures.

`getEvents()` now obtains displayed frames via `time_to_frame()`, derives a scripting index only for measured-range validation and fractional event offset, and returns `recording_start_frame` plus `frame_convention`. The former native range check permitted an extra frame; validation now uses the actual inclusive measured indices.

Both QTM scripts find the repository root through their parent paths before importing the pure Python event helper. The application package must remain present beside the plugin's QTM directories. No Qt import is required by that helper. Protobuf definitions and command names were unchanged; older servers ignore the additional event JSON fields.

### Event helper and application service

`sample_index_to_frame()` and `frame_to_sample_index()` define the calibrated native/display boundary. `recording_start_frame()` respects explicit origin metadata, otherwise derives it from the ezc3d sample origin. `index_to_frame()`/`frame_to_index()` map recording-relative indices with that actual start. `frame_to_time()` validates frequency and uses the original measurement clock. `time_to_frame()` performs the inverse using nearest-sample rounding.

`normalize_saved_events()` converts only identifiable previous conventions: the intermediate zero-based metadata is migrated at the native/display boundary; older auto files with a recorded relative index are reconstructed from that index and actual recording start. Unversioned manual frames and original displayed QTM snapshots retain their frame values. New convention metadata prevents repeated conversion. Save normalizes relative indices and timestamps from the selected absolute frame.

`event_service.load_trial_events()` tags its normalized in-memory metadata. `save_trial_events()` saves the displayed frame, crop-relative index, precise time, origin, and convention, and invokes the existing C3D writer. `send_events_to_qtm()` serializes that time, adds optional frame/convention diagnostics, and retains existing trial matching and ClearEvents/SetEvents flow. `fetch_events_from_qtm()` prefers physical native time over a conflicting frame field; it supports raw events, legacy FrameNo/EventOffset dictionaries, and event lists. Legacy offsets are fractions of a sample, not additional display frames. `sync_qtm_events_to_session()` uses the same time helper when resolving real C3D frequency.

Both C3D writers fill `EVENT:TIMES` with minutes and seconds without rounding to four decimals. Consumers combine both rows before mapping into existing relative one-based gait slicing conventions. Thus events over one minute and cropped arrays address the intended sample without changing gait formulas.

### Detector and UI

`process_trial()` retains the real detector call and all thresholds, filters, ordering, and count validation. It converts each returned relative index once, stores `recording_start_frame`, and passes the resulting displayed frame to the client. C3D and JSON describe the same physical sample.

`EventDetailsDialog.__init__()` resolves C3D origin/frequency where available, normalizes its working copy, and uses `_qtm_base` as the displayed first frame. Table rows, previews, manual addition/editing, and notifications display the model frame directly. Fetch updates the same origin and input bounds. `_on_save_and_update_qtm()` uses the existing service path. Nudge buttons still change frames by the user's requested amount; those are editing operations, not coordinate adjustments. No layout or design was changed.

`trace_event()` is inactive unless `SHRINERS_FRAME_TRACE=1`. Detector, client, service read/send, server read/write, and dialog initialization log an identifier formed from label and absolute physical sample. Diagnostic labels normalized by the service may change their text; clinical labels such as `LSTRIKE:294` remain consistent.

### Plot changes

`ClinicalPlotCanvas.clear_plot()` resets artist, scene, layout, and last-input state. `plot_gait_data()` keeps scene references when title/directions/norm data/theme/toe reference are unchanged. Trial identities locate existing line/marker groups; active curves receive new data/styles and inactive groups are hidden. Reference bands, limits, ticks, legends, and direction labels retain their previous rules and appearance. `_last_plot_kwargs` contains the active presentation for detail/export reuse.

Layout is recalculated when relevant scene, limits, ticks, legend, or figure size changes. Y-range calculation is cached only for identical inputs. One canvas redraw is scheduled after a complete update; `MultiPlotGrid.plot_at()` no longer duplicates it. `_draw_idle()` checks `shiboken6.isValid(self)` because Qt can delete a child canvas while a Matplotlib callback is queued.

`CasePresentationPage._refresh_plots()` clears only unused cells and cancels a pending coalesced refresh when an explicit synchronous refresh is requested. `_schedule_plot_refresh()` restarts one single-shot zero-delay QTimer; a burst renders its final state on the GUI thread. `_mean_curve()` retains the latest fingerprint per plot/side (at most 30 entries), invalidating on membership or content changes. Stable trial/Mean_L/Mean_R keys keep their artist groups separate.

`GCDService.get_variable_array()` and the SD getter cache read-only arrays per GCD object and variable, compare source content, and invalidate on mutation. Cache size is bounded at 256 entries. The normalized 101-point X axis is shared and read-only. No worker thread was added: after optimization preparation was sufficiently small that an additional thread was not justified. Qt and Matplotlib updates remain on the GUI thread.

## 5. Frame numbering specifications

| Coordinate | Meaning | Live example |
|---|---|---|
| Array index `i` | Zero-based index within extracted points | 294 |
| Relative event index | Same recording-relative sample coordinate used by detection | 294 |
| Absolute scripting sample `s` | Zero-based QTM native sample index | 294 |
| Recording start `F0` | Actual displayed QTM frame of array index zero | 1 |
| Absolute displayed QTM frame `f` | One-based marker timeline coordinate | 295 |
| Event time `t` | Seconds on original measurement clock | 2.45 |
| UI/model/saved frame | The absolute displayed QTM frame; no extra UI adjustment | 295 |

```python
s = initial_frame_offset + i
F0 = sample_index_to_frame(initial_frame_offset)
f = index_to_frame(i, F0)
i = frame_to_index(f, F0)
t = frame_to_time(f, frequency)  # native sample index / frequency
f = time_to_frame(t, frequency)
```

`QTM_TIMELINE_FIRST_FRAME=1` is the verified native/display origin, not a global correction applied after an absolute frame is computed. Trajectory ranges are always native indices and never receive this displayed-frame conversion.

At 120 Hz, sample 294 is displayed frame 295 at `294/120 = 2.45 s`. For an array beginning at native sample 200, displayed recording start is 201; event array index 94 is still absolute frame 295 at 2.45 s. For displayed start 100, native origin is 99 and frame 295 is relative index 195. Cropping changes the array origin, not the original-measurement timestamp of an absolute event.

The C3D legacy gait consumer uses a separate relative one-based frame: `round(t*frequency)-initial_frame_offset+1`, because existing code slices `[Strike1-1:Strike2]`. That conversion remains at the consumer boundary and does not modify a QTM/UI absolute frame.

## 6. QTM trajectory specifications

- Full measured range is independent of the current selected range. Inclusive count is `end-start+1`.
- Full-source writes map array origin to the measured/source span, not the user's selection.
- Explicit selected writes slice by absolute source origin, e.g. full source 0..1026 and target 100..219 produce exactly 120 samples from indices 100..219.
- Cropped source 100..103 maps four samples to native 100..103.
- Missing origin on a short legacy array, differing XYZ/existence lengths, reversed/outside target ranges, or uncovered samples fail before native writes.
- Diagnostics include label, ID, source count, target count, and target start/end.
- Existing marker IDs are reused, including repeated calls; absent labels are added once; true errors propagate.
- Missing samples remain native gaps (`None`), preserving QTM gap semantics.

These match the documented [timeline range API](https://qualisys.github.io/qtm-scripting/latest/qtm.gui.timeline.html), [3D sample API](https://qualisys.github.io/qtm-scripting/latest/qtm.data.series._3d.html), and [trajectory object API](https://qualisys.github.io/qtm-scripting/latest/qtm.data.object.trajectory.html).

## 7. Graph performance architecture

Before: checkbox → clear 15 axes → fetch/convert arrays → recalculate means → rebuild references/curves/markers/legends → tight_layout → duplicate redraw requests.

After: checkbox burst → one queued refresh → reuse cached arrays and unchanged means → update/hide persistent curve groups → update limits/layout only when required → one redraw request per used canvas.

Artist cache identity includes trial and mean side; scene invalidation includes titles, direction labels, normalization references, theme, and reference toe position. Content fingerprints prevent stale means/arrays. Unused graphs clear when data/category changes. Layout change, resize, detail, and export continue to use existing canvases and presentation parameters. Most Representative/Average calculations and colors/styles were not changed.

Remaining costs: rasterizing 15 complete canvases still takes about 312 ms in the synthetic benchmark. This work remains on the GUI thread. Persistent curves retain a small number of hidden groups, rather than repeatedly deleting/recreating them. Legacy Tk redraw/GCD costs were investigated but remain outside this optimization.

## 8. Tools and dependencies

PowerShell; `rg`/`rg --files`; Git status/diff/diff --check; Python AST, compile/import checks, hashlib and difflib snapshot auditing; `time.perf_counter()` and median benchmark timing; pytest/unittest.mock; NumPy; SciPy-backed existing detection; ezc3d; gRPC/protobuf; PySide6 QApplication/QTimer; Matplotlib artist setters, LineCollection segments, buffer_rgba, tight_layout, and draw_idle; shiboken6 isValid.

Runtime used: Python 3.10 in the existing `python-example` environment, PySide6 6.10.3, Matplotlib 3.9.4, NumPy 1.26.4. The system Python lacked Qt, so it was not used for validation. pytest was installed into the existing test environment. Repository dependency declarations were unchanged; no production dependency was added.

Research used official Qualisys scripting documentation and an Exa search through the installed agent-reach workflow. Computer Use used the bundled `@oai/sky` native Windows API. Local QTM REST requests used the documented port 7979 API; application commands used gRPC port 50052. No clinical data was sent to an external service. No extra worker or service was created.

## 9. Tests executed

Environment for commands below: activate the existing Python 3.10 environment; set `QT_QPA_PLATFORM=offscreen`; on Windows include the environment's `Library/bin` on PATH; run from repository root.

```powershell
python -X utf8 -m pytest tests/test_session1_regressions.py tests/test_dynamic_plot_scaling.py tests/test_bilateral_mean_separation.py tests/test_10_trials_support.py tests/test_norm_ideal_range.py tests/test_qtm_auto_event_sync.py tests/test_case_presentation_smooth_scroll.py tests/test_particular_session_mac_case.py -q --disable-warnings
```

Result: **64 passed, 14 warnings, 31.38 s, exit 0**. After adding the second real auto-label pass assertion, the focused file was rerun: **46 passed, 14 warnings, 8.16 s, exit 0**. Other source code was unchanged between these runs. Warnings did not fail validation; they included existing Matplotlib/Qt warnings, and do not imply a full UI typography/export audit.

| Test/group | Expected behavior | Actual status |
|---|---|---|
| `test_full_trajectory_ignores_short_selection` (both servers) | 1,027 samples target 0..1026 despite selection 100..219 | Pass |
| `test_selected_range_maps_source_without_resampling` (both) | Exactly 120 samples with source positions 100 and 219 at ends | Pass |
| `test_partial_source_and_missing_samples` (both) | Explicit crop origin and native missing gaps | Pass |
| `test_bad_ranges_never_write` (both, four ranges) | Reversed, negative, outside, and uncovered ranges reject before write | Pass |
| `test_mismatched_lengths_and_ambiguous_legacy_payload` (both) | Unequal arrays/unknown short origin reject with diagnostics | Pass |
| `test_marker_creation_idempotent_and_real_errors_propagate` (both) | Existing/new/repeated markers reuse IDs; true error survives | Pass |
| `test_event_conversion_save_load_and_ui` (four origins/rates) | Physical frame 295, first/last frame, manual input, three save/load cycles | Pass |
| `test_old_auto_sidecar_migrates_once` | Known auto provenance retains the physical event | Pass |
| `test_qtm_read_write_roundtrip` (both) | First frame 1, target 295, last 1027 map from native timestamps | Pass with native event API mocked |
| `test_grpc_client_payloads_preserve_absolute_frame` | Single/bulk event time and trajectory origin preserved | Pass |
| `test_event_service_grpc_serialization_and_retrieval` (three formats) | Raw time, legacy dictionary, and list read/write return 295 | Pass with transport mocked |
| `test_real_c3d_roundtrip` (origins 0, 200, 7200) | Real C3D minute/second timestamps address original physical samples | Pass |
| `test_auto_detection_end_to_end_with_mock_qtm` (origins 0, 200) | Real detector, JSON, C3D, client serialization, and repeat processing preserve eight positions | Pass; only live transport/force-plate provider mocked |
| `test_both_reported_mismatches_are_physical_sample_errors` (four rates) | Reject both 296 and 294 for physical sample 294/displayed frame 295 | Pass |
| `test_legacy_data_provenance_and_no_cumulative_offset` (five formats) | Old auto, intermediate zero-based, original QTM, and manual data migrate once | Pass |
| `test_canvas_reuses_artists_and_matches_values` | Same line IDs, no unchanged tight_layout, correct visibility and updated arrays | Pass |
| `test_page_means_cache_invalidation_and_trial_changes` | Bilateral means, source mutation, membership changes, canvas identity | Pass |
| `test_checkbox_burst_coalesces` | Three filter operations produce one final refresh | Pass |
| Dynamic scaling, bilateral separation, ten-trial support, normative ideal ranges | Existing clinical display behavior | Pass |
| QTM automatic sync service/page tests | Existing label/signature/sync behavior | Pass with transport fixtures |
| Scroll and particular-session navigation | Existing interaction and session switching | Pass; broad MainWindow runtime side effects noted above |

Additional command:

```powershell
python -X utf8 Gait-lab-Vicon-to-QTM/test_auto_event_zero_events.py
```

Result: **ALL PASS**, exit 0. Missing EVENT group, zero, one, and multiple existing events extract successfully; three real synthetic processing pipelines each produce eight events. These run in a temporary directory and intercept QTM commands.

Syntax checks compiled all **20 changed Python files**. Import checks passed for `app.main`, the frame/event/GCD services, clinical plots, event dialog, case presentation page, `gapi`, `auto_event_trigger`, and `Py3_varExtractor`. Both QTM handlers were loaded from AST to avoid starting their embedded server/menu during offline testing. Their updated event-read functions were also exercised against actual native QTM REST data.

`git diff --check` returned exit 0; it printed pre-existing CRLF normalization warnings. Introduced source-line auditing found no absolute user-specific paths. No circular helper imports were introduced: the shared helper uses only Python standard-library modules.

Visual comparison against the saved baseline canvas used real Matplotlib rasters for initial curves, hidden trial, and changed curve/y-range. All three had **zero differing pixel channels**. Existing normative-range tests generated the three screenshots listed above; one full-page screenshot includes the existing loading overlay/missing UI glyphs in the headless runtime and is not claimed as a successful full-window visual acceptance check.

Skipped: a blanket `pytest tests` run. `test_multi_trial_isolation.py` can overwrite a real C3D and send events to a matching live trial; `test_manual_event_editing.py` also includes paths that can write live events. Remaining broad screenshot/end-to-end scripts were not run indiscriminately. Focused replacements use temporary data. Clinical export workflows, every marker/trial in live QTM, and live cropped recordings at several frequencies were not exhaustively tested.

## 10. Performance comparison

Measured with the same synthetic 20-trial, 15-graph workload, three warmed alternating L1 visibility toggles, offscreen Qt, same interpreter/machine. Values are median milliseconds; extraction and graph preparation are components of refresh, not independent totals. A subsequent explicit synchronous draw of all canvases measures raster work, separately from interaction preparation.

| Metric | Before | After | Interpretation |
|---|---:|---:|---|
| Data extraction | 1.0375 | 0.5962 | Reused arrays |
| Graph preparation | 972.3748 | 33.9041 | About 28.7x faster |
| Single trial visibility refresh | 1127.0376 | 36.9365 | About 30.5x faster; 96.7% reduction |
| Full 15-graph raster | 317.0303 | 312.1236 | Little change; raster remains a cost |
| Redraw requests per refresh | 45 | 15 | One per used canvas |

Reproduce current measurement:

```powershell
python -X utf8 tests/benchmark_case_presentation.py --iterations 3 --output benchmark-after.json
```

Before values were measured using the same harness on the starting source copies in the external snapshot. Before/after JSON results are retained there. These are measured synthetic interactions, not a claim of patient-specific performance or total first-load latency.

## 11. Errors resolved

- 1,027-source/120-selected-range trajectory failure: validated target mapping now matches counts; regression coverage in both adapters.
- Duplicate modeled-marker creation: existing IDs reused; repeated calls tested.
- Mixed event-frame display/write/read conventions: actual native sample/display mapping verified; frame 295 write, native read, application dialog, and QTM editor agree at the intended sample.
- Cropped event time, double UI increment, rounded timestamps, and dropped C3D minutes: shared boundaries and real C3D/save/load tests.
- Heavy full graph rebuild/duplicate redraws: persistent artists and measured refresh reduction.
- Native crash in queued `FigureCanvasQTAgg._draw_idle` after Qt child deletion: validity guard; previously crashing combined test sequence exits successfully.

No remaining mismatch was observed for the verified live frame-295 event. Exhaustive QTM trajectory/crop coverage and full clinical export validation remain unperformed. Runtime file side effects of earlier broad GUI tests are explicitly recorded; exact byte restoration of those files was not verified.

## 12. Compatibility and risks

QTM semantics were checked against current official scripting docs and the running installation. Event objects store seconds and optional color, not a native frame input; see the [event API](https://qualisys.github.io/qtm-scripting/latest/qtm.data.object.event.html). The existing embedded server runs Python 3.10.9 according to its terminal. The precise installed QTM product version was not established; older versions must provide the documented measured-range and trajectory APIs.

Old exact full-range XYZ-only payloads remain supported. Ambiguous partial legacy payloads must provide an origin; rejecting them is intentional protection against writing samples to the wrong place. New helper imports require the application package in the plugin checkout.

New sidecars explicitly use `qtm_timeline_one_based`. Identifiable intermediate zero-based results migrate once on read; original auto relative indices are retained. Unversioned manual files do not prove their original coordinate system, so displayed frame values are preserved rather than guessed. Migration occurs in memory until the user saves; there was no bulk patient-data rewrite.

The native frame origin was verified on the current measurement; live cropped/rebased QTM measurements were not switched into the active, dirty user recording. Original-clock event semantics and ezc3d sample origins are covered by synthetic cropped C3D tests and the official timeline specification, but unusual imports that reset the clock require separate live calibration.

Qt/Matplotlib updates stay on the GUI thread. Mean/array caches invalidate by content and are bounded; arrays returned by the cache are read-only. Unknown callers that mutate those returned arrays would need to copy them. Existing application rendering uses them as inputs. No detection/preprocessing/clinical formula changes were made in the follow-up.

The original live measurement had unsaved changes. It was not closed or saved over during verification. A temporary event was added through real gRPC, shown in the editor, then removed individually. Script-added events did not enter QTM's Undo history; cleanup used the event editor rather than clearing all events. The original eight events were checked for exact equality at that point. Later read-only observations after script reload showed the same eight physical samples with precise sample-aligned timestamps, consistent with concurrent application synchronization.

## 13. Final verification checklist

- [x] Both trajectory adapters validate count, range, coverage, and gaps.
- [x] Marker creation is repeatable and true failures propagate.
- [x] Detector output traced to a real signal sample; native and C3D XYZ matched.
- [x] QTM event writer/reader and actual native editor verified at displayed frame 295.
- [x] Frame 1, displayed start 100, cropped origins, last frame, manual events, multiple frequencies, save/reload, migration, and repeated detection covered offline.
- [x] UI displays the absolute model frame directly.
- [x] Existing chart values/styles retained; focused raster equivalence and behavior tests passed.
- [x] Performance benchmark measured before and after.
- [x] Focused syntax/import/diff checks completed.
- [x] Pre-existing source changes preserved; no source moves/deletions, user-specific source paths, dependency-file edits, or push.
- [x] Complete authored file list and follow-up history recorded.
- [ ] Every trajectory/marker and cropped measurement tested live.
- [ ] Full patient/export UI visually accepted in the native app.
- [ ] Runtime measurement/settings files proven byte-identical to the session start; concurrent processing and earlier GUI side effects prevent that claim.

## 14. Future recommendations

Optional work: benchmark patient datasets and cold-load/export costs; separately optimize legacy Tk GCD/rendering; add fully isolated settings/session fixtures before running broad MainWindow tests; validate live cropped/rebased files in disposable measurements; verify native fonts/export layouts; improve trial identity matching beyond a same-named filename across different session directories. These are distinct from the completed coordinate and rendering changes.

## Session 1 Follow-up — Frame Offset Root Cause and Correction

### 1. Reported mismatches and why the previous fix failed

The original task reported QTM 295/application 296. The follow-up reported the other observed path as server/QTM 296/application 295, then server/QTM 294/application 295 after the earlier changes. These are retained as user observations, rather than silently rewritten as one identical observation.

Removing a UI increment was necessary, but it did not establish whether a server FrameNo was a scripting index or a displayed frame. The intermediate zero-based helper and server output used the former. Tests round-tripped that same wrong convention and therefore passed without validating the native display or physical sample. It also introduced faulty migration of original QTM snapshots. The correction retains the valid UI removal and replaces the event boundaries and provenance migration.

At the baseline, `gapi.SetEvent()` subtracted `max(offset,1)`: correct for default displayed frames, wrong for an already absolute cropped frame. `event_service` send/save instead used `f/frequency`, placing displayed frame 295 at native sample 295 (visible frame 296). The intermediate server `getEvents()` returned `round(t*frequency)` (294 for the correct 2.45 s event), which is a native sample index, not displayed frame 294. Actual QTM's native editor confirmed the distinction.

### 2. Exact boundaries corrected

| Location | Previous/intermediate behavior | Final behavior |
|---|---|---|
| `auto_event_trigger.process_trial` | `max(offset,1)`, then intermediate `offset` as displayed origin | `sample_index_to_frame(offset)` gives actual array-zero displayed frame; add relative detector index once |
| `gapi.SetEvent/SetEvents` | Baseline subtracts crop/base; intermediate divides displayed/model value directly by rate | `frame_to_time()` converts displayed absolute frame to original-clock time |
| Both QTM `getEvents` | Intermediate returns scripting indices as FrameNo; baseline validation also allowed an extra frame | Shared native-time-to-display conversion; validate inverse native index against measured range |
| `event_service` load/save/send/fetch/sync/C3D | Mixed relative/absolute origins and rounded times | Shared displayed-frame/original-clock mapping, explicit origin/convention, time-authoritative retrieval |
| `EventDetailsDialog` init/add/edit/fetch/time/table | Original duplicate display increment; intermediate zero-based recording bounds | Display frame unchanged; actual recording start for relative index/bounds |
| `frame_coordinates.normalize_saved_events` | Intermediate decremented original QTM snapshots | Migrate only known zero-based format; derive older auto positions from relative index; preserve original displayed QTM/manual frames |
| Modern extractor sidecar fallback | Intermediate subtracts native sample origin from displayed frame | Subtract actual displayed array-zero frame; legacy relative consumer conversion remains deliberate |

Unchanged increments/decrements found in the audit: gait consumer `[Strike1-1:Strike2]` and its relative one-based input boundary; inclusive sample lengths/end bounds; peak/window indexing inside detection; UI nudge buttons; generic trajectory neighboring-sample/gap-fill loops; Vicon API inclusive ranges. These have different purposes and were not globally adjusted.

### 3. Before/after snippets

Incorrect intermediate event convention:

```python
qtm_base = initial_frame_offset
frame = relative_index + qtm_base
time = frame / frequency
retrieved_frame = round(time * frequency)
# UI now showed frame without an increment, but native QTM showed sample+1.
```

Final boundary:

```python
recording_start = sample_index_to_frame(initial_frame_offset)
frame = index_to_frame(relative_index, recording_start)
time = frame_to_time(frame, frequency)
retrieved_frame = time_to_frame(native_event["time"], frequency)
# UI displays retrieved_frame directly.
```

The only native/display origin lives in the named helper. No conversion is applied again after a value is an absolute displayed frame. The pure helper functions and their purpose are documented in sections 4 and 5.

### 4. Actual runtime event trace

The real detector ran on a temporary copy of the active `Dynamic 1.c3d` and session XML. It selected its canonical eight-event sequence, beginning with `LSTRIKE` at relative sample 294. Detector parameters/algorithms were unchanged. QTM reads remained live; clinical source C3D writes were confined to the temporary copy.

| Stage | Identifier/value actually observed |
|---|---|
| Raw recording | 1,027 point samples; 120 Hz; ezc3d first sample origin 0 |
| Detector | `LSTRIKE:294`, returned relative index 294 |
| Relative/absolute sample | Relative 294, native absolute sample 294 |
| Actual recording start | Displayed frame 1 |
| Computed absolute frame | 295 |
| Captured real auto client payload | `{label: LSTRIKE, frame: 295, time: 2.45, frame_convention: qtm_timeline_one_based, trial_name: Dynamic 1}` |
| Native existing event | `LSTRIKE` at 2.45 s |
| Live gRPC diagnostic write | `LSTRIKE_FRAME_CHECK`, frame 295, time 2.45 s; ACK success |
| Native API readback | Diagnostic event time 2.45 s, color 255 |
| Actual QTM event editor | Diagnostic event **frame 295**, time **2.450 s** |
| Real application event dialog | Table frame **295**; physical sample trace 294 |
| QTM cursor API | `get_current_frame=294`, `get_current_time=2.45` |
| Actual QTM marker status | **Marker frame 295 of 1027 (120 Hz)**, time **2.45 s** |
| Updated live gRPC server after reload | First LSTRIKE FrameNo/raw frame **295**, convention metadata `qtm_timeline_one_based` |

Physical signal check: native `Left_Heel` trajectory ID 319, sample 294, XYZ `[1048.1501457060738, 211.78479072879537, -1.4016104055752654]`; C3D XYZ `[1048.150146484375, 211.7847900390625, -1.4016103744506836]`. All coordinates matched within 0.001. This independently ties the detector sample to the same native sample, rather than only making two displayed numbers match.

Representative trace:

```text
[FRAME TRACE] Event=LSTRIKE:294 stage=detector recording_start_frame=1
sample_index=294 relative_index=294 frequency=120.0 QTM_frame=295
time=2.45 details={'detector_output': 294}
[FRAME TRACE] Event=LSTRIKE:294 stage=grpc_send ... QTM_frame=295 time=2.45
[FRAME TRACE] Event=LSTRIKE:294 stage=application_read ... QTM_frame=295 time=2.45
[FRAME TRACE] Event=LSTRIKE:294 stage=UI_display ... QTM_frame=295 time=2.45
```

The diagnostic label was separate from the clinical label so it could be removed individually. The eight original label/time/color objects matched exactly immediately after cleanup. The original cursor was restored to scripting index 354. No live trajectory write was performed during this follow-up.

### 5. Tools, commands, test results, and external verification

Investigation used snapshot/HEAD diffs, `rg` searches across application, engine, templates, and both adapters; official QTM timeline/event/3D/file documentation; native window screenshots/accessibility; local REST and real gRPC; real detector/ezc3d/Qt tests. Relevant native API calls included `get_measured_range`, `get_frequency`, `get_current_frame/time`, `find_trajectory`, `get_sample`, `get_events`, and `get_path/is_dirty`. GUI commands opened the event editor and reloaded scripts. The temporary event was removed through the editor. The user then stopped Computer Use with physical Escape; no further native UI automation was used. A subsequent read-only gRPC query confirmed the reloaded server's corrected frame values.

After reload, the first query briefly returned an empty dictionary while scripts initialized. A later read-only query returned all eight events, frames `[295,310,357,373,420,434,480,494]`, frequency 120, native origin 0, displayed start 1, and the final convention metadata. This is a live result, not a mocked handler result. Separately, both updated getEvents source functions were loaded into a REST-backed harness and returned the same displayed frames from actual QTM objects.

Regression requirements are mapped in section 9. Both mismatch directions are explicitly reproduced: time `295/frequency` gives displayed frame 296, and time `293/frequency` gives frame 294; only `294/frequency` places the tested physical sample at displayed frame 295. Different rates 100, 120, 240, and 59.94 are covered. Both uncropped and cropped real detector pipelines were run twice with identical event positions. Conversion functions themselves were not mocked.

All final focused results, performance values, syntax/import checks, skipped cases, and outstanding limits appear in sections 9–13. Live verification covered a full recording at 120 Hz; cropped origins and other rates are real offline C3D/Qt tests, not live measurements. Full trajectory writes remain handler tests and observed concurrent QTM processing diagnostics, not an agent-run live write certification.

### 6. Complete follow-up file scope and final diff

Follow-up event corrections touched `app/services/frame_coordinates.py`, `app/services/event_service.py`, `app/ui/dialogs/event_details_dialog.py`, `Gait-lab-Vicon-to-QTM/auto_event_trigger.py`, `Gait-lab-Vicon-to-QTM/gapi.py`, `Gait-lab-Vicon-to-QTM/Py3_varExtractor.py`, both QTM `Py3_staticmain.py` adapters, `tests/test_session1_regressions.py`, and this document. Adapter changes during the follow-up were limited to event imports, writes/reads, metadata, and trace; trajectory logic and MAC optimization logic were retained.

The entire session's authored source/test diff against the captured start state is **20 Python files, 1,083 inserted lines and 265 removed lines**, plus this new documentation and three generated test screenshots. This differs from the larger Git HEAD diff, which includes pre-existing work. No source deletions/moves were introduced; no absolute user-specific source paths were added; dependency files were unchanged; no commit or push was made. Complete paths are in section 3. External snapshot artifacts include `session-diff.patch`, `changes.json`, `audit.json`, before/after benchmark JSON, pipeline logs, `live-frame-trace.json`, `live-roundtrip.json`, and `live-grpc-read-after-reload.json`.


## Session 1 Follow-up 2 — MAC Scale Persistence and Anthropometric Synchronization

Verified on 2026-10-08. Scope: the two requested follow-up issues and the static Run regression reported while testing them. No event detection, frame conversion, trajectory-length, duplicate-marker, or previous graph-performance implementation was revised. Existing repository changes were captured before work and preserved.

### 1. Initial behavior and confirmed causes

The expanded Matplotlib dialog previously owned its own limits. Applying a range changed that temporary figure, while closing it, toggling trials, or refreshing the grid reconstructed limits from defaults. Neither the main canvas nor stable graph identity retained the selection.

Anthropometric values previously came primarily from local Python/XML files. QTM discovery ran synchronously, could fall back to a matching folder basename, and Save PUT the whole form into both Session and a cached parent, including RawFolder. Success meant either PUT succeeded, without verifying accepted values. No periodic pull or editing-finished synchronization existed. This permitted stale form values, incorrect parent writes, rounded displays, and no visible updates after external edits.

The first synchronization implementation introduced two Run blockers: PAF entry bounds were checked against every existing value, and a read-only background operation was treated as a pending write. The user reported that Run opened neither analysis nor the loading view. These gates were corrected before final verification: input bounds apply to edited values; existing finite calibration values and zero sentinels retain the earlier workflow. Run waits for actual unsent edits/writes, while an unrelated read poll cannot stop the processing transition. The existing clinical engine was unchanged.

### 2. Exact source scope, classes and functions

The complete authored file inventory and snapshot diff statistics are listed in section 18. Changes reach:

- `ClinicalPlotCanvas`: `plot_gait_data`, `_apply_scale_state`, `set_scale_limits`, double-click dialog launch, and shared graph state initialization.
- `ClinicalPlotDetailDialog`: source canvas binding, axes callbacks, `_publish_scale`, Apply/Expand/Auto Fit/Reset handling, and callback cleanup. Existing Auto Fit calculations were moved into `_full_graph_limits` without changing their clinical values.
- `MultiPlotGrid`: shared scale-state storage.
- `CasePresentationPage._refresh_plots`: one added stable `graph_id` argument.
- `QtmAnthropometricClient`, `_SyncOperation`, `AnthropometricSyncService`: real PAF REST transport, discovery, partial writes, validation, cancellation, and verified read-back.
- `StaticAnalysisPage`: context preparation, edited-field tracking, commit/read callbacks, timer/lifecycle cleanup, asynchronous initial QTM fetch, Save/Run integration, and signal-blocked path updates in `set_session`.
- Two focused test modules. No dependency or configuration files were changed.

### 3. Graph storage, sharing, and before/after behavior

The grid owns an in-memory dictionary indexed by `(normalized absolute session path, category, side, variable name)`. Canvases and their expanded dialogs reference that same dictionary. Each graph stores X/Y modes (`manual`, `auto`, `reset`), selected limits, Y ticks, and full-data-fit choice. The standalone canvas fallback uses its title/direction labels.

Manual limits are applied after Matplotlib ticks, which can otherwise expand axes. Dialog callbacks publish toolbar changes with a reentrancy guard. Apply/Expand adjust existing axes and relative annotations; no data curves are rebuilt and no 15-panel refresh is scheduled. Only the source and expanded canvas draw. An old dialog checks canvas validity and graph identity before updating a reused cell. Reopening, trial/norm toggles, and theme reconstruction retain the same graph's limits. A different session or variable gets its own state. Auto Fit restores full-data automatic behavior; Reset restores existing clinical defaults/dynamic headroom. In-memory persistence does not extend across application restarts.

### 4. Actual QTM interface and all field mappings

The existing application and installed QTM documentation identify PAF REST as the field interface: GET `/api/v1/paf/instance`, GET an instance with `depth=-1`, GET `typeInfo=true`, and PUT a dictionary of changed fields. This implementation uses that interface; it does not invent gRPC parameter endpoints. Instance type information exposes Float32 and ReadOnly. Discovery uses the full normalized Session `Path` and Class, skips measurement subtrees, and limits work to 256 nodes and a four-second discovery deadline. Steady polling reads the cached Session rather than recrawling the project.

Mappings, units, and inclusive input bounds come directly from this model's `Settings.paf`:

| QTM field | GUI control | Units | Input bounds |
|---|---|---|---|
| BodyMass | Body Mass | kg | 0–250 |
| Height | Height | m | 0.5–2.5 |
| InterAsisDistance | ASIS-to-ASIS | m | 0.1–0.4 |
| LeftLegLength / RightLegLength | Left / Right Leg Length | m | 0.6–1.2 |
| LeftKneeWidth / RightKneeWidth | Left / Right Knee Width | m | 0.06–0.15 |
| LeftAnkleWidth / RightAnkleWidth | Left / Right Ankle Width | m | 0.05–0.12 |
| LeftAsisTrocanterDistance / RightAsisTrocanterDistance | Left / Right ASIS-to-GT | m | 0–0.3 |

`Trocanter` is the real PAF spelling. No unit conversion was introduced. Bounds comparisons account for Float32 boundaries such as 1.200000047. Nine significant display digits preserve every Float32 value, replacing the old two/three-decimal truncation. Empty/non-numeric/non-finite/overflow/newly out-of-range edits cannot be written. Existing finite values outside entry bounds are displayed faithfully and do not prevent an otherwise unchanged static calibration from starting.

### 5. GUI-to-QTM flow

`textEdited` marks only the edited field and advances its revision. `editingFinished` validates and queues that field. A background QRunnable reads current QTM state, checks the expected context token, checks actual field ownership/ReadOnly, skips equivalent Float32 values, and PUTs only changed keys. The Session owns fields it exposes; a genuine Subject is used only when it exposes a field absent from Session. RawFolder is never written. Explicit Save retains the prior ID/Name/DOB save behavior, with only actual metadata differences sent.

A subsequent GET must confirm the accepted field value and the same context before success is shown. HTTP 200 with an ignored value is an error. Save writes the existing local static parameter file/session XML only after validation. Save & Run waits when new writes are outstanding and starts only after their successful confirmation. A clean configuration can start while polling or when the PAF synchronization endpoint is unavailable; this does not assert that the underlying calibration engine can run without QTM.

### 6. QTM-to-GUI flow and notification discovery

Initial local Python/XML loading remains available; an asynchronous QTM read then fills idle anthropometric controls for the selected session. The earlier synchronous tree crawl was removed. Programmatic changes use `QSignalBlocker` and compare the existing value before setting text.

The bundled gRPC bridge/proto exposes frame/capture/event information, not an anthropometric field-change event. Installed `RESTful_QTM_API.pdf`, PAF documentation, and official QTM GUI scripting callbacks were inspected; no suitable field subscription was found. A two-second Qt timer therefore pulls values while the configuration view is visible. All network requests run off the UI thread with one-second HTTP deadlines. Hide, close, processing-view transitions, and context changes stop polling/cancel operations without waiting for network completion. References inspected: https://github.com/qualisys/paf-documentation and https://qualisys.github.io/qtm-scripting/latest/qtm.gui.html . No undocumented callback was registered.

### 7. Loop prevention and concurrent edits

Only user editing signals create writes; incoming text changes cannot feed back into PUT. Float32 equivalence prevents formatting differences from causing repeated writes. One operation runs at a time; the pending dictionary retains the latest committed value. A response acknowledges a field only if its captured revision and submitted value still match the widget. Incoming QTM values never replace dirty typing. A later uncommitted revision remains visible; a later committed revision runs after the current operation.

Context generations discard responses from an old selection. Session/trial drafts are retained separately. Context tokens include the normalized folder and Session/Subject GUIDs; replacing an instance before a write requires review and recommit. Switching session does not replay the previous session's edits.

### 8. Errors, reconnects, and cleanup

Transport failure, missing fields, read-only fields, incorrect context, ignored writes, and invalid incoming non-finite values produce visible status instead of false success. Dirty text is retained. Disconnects clear automatic write queues and block unsent edits; reconnect reads current values, and the user must review and commit retained edits again. A failed edit cannot automatically start static processing. Worker cancellation is checked before PUT; already transmitted requests cannot be recalled. Closing returns immediately and does not block on the HTTP worker. No silent clinical value correction occurs.

### 9. Tools, dependencies, and verification command

Used `rg`, PowerShell, Git diff checks, Python AST/hash comparison, urllib HTTP, real PySide6 widgets/QTest, Matplotlib, pytest, a disposable `ThreadingHTTPServer`, and pypdf to read installed QTM documentation. Ponytail and Graphify skills were applied; no graph-generation pipeline was run because the task explicitly limits changes. Agent Reach was used to inspect official Qualisys documents. No packages were installed.

Runtime: `C:\Users\ADMIN\anaconda3\envs\python-example\python.exe` (Python 3.10), PySide6 6.10.3, Matplotlib 3.9.4, NumPy 1.26.4. Offscreen tests set `QT_QPA_PLATFORM=offscreen` and prepend the conda `Library\bin` to PATH. Final command from the repository:

```powershell
python -X utf8 -m pytest tests/test_mac_scale_persistence.py tests/test_anthropometric_sync.py tests/test_session1_regressions.py tests/test_dynamic_plot_scaling.py tests/test_bilateral_mean_separation.py tests/test_10_trials_support.py -q --disable-warnings --maxfail=3
```

### 10. Tests created and actual results

`test_mac_scale_persistence.py` contains eight tests: main/expanded shared X/Y limits, close/refresh/reopen/theme retention, norm/trial checkboxes, stable identities/cell reuse, Auto Fit/Reset, real double-click opening, retained artist identity/limited draw scope, and relative annotations.

`test_anthropometric_sync.py` contains 50 tests/cases using actual HTTP and Qt controls: every one of the 11 GUI fields outbound independently and every field inbound; exact single-field payloads; repeated-poll no-write behavior; genuine keyboard typing; invalid values; Float32 boundary/precision/schema checks; timeout responsiveness; HTTP PUT failure; ignored PUT; ReadOnly; Subject fallback; rapid revisions; full-path/context replacement/drafts; hidden/close lifecycle; Save only edited fields; Run waits for successful writes and rejects failed edits; invalid Save cannot rewrite local files; real Run button opens the loading view and calls the processing service in connected/initial-poll/unavailable cases; newly out-of-range Run edits remain rejected.

Final focused run: **115 passed, 14 warnings, 48.93 seconds, exit code 0**. Earlier pre-Run-correction suite: 111 passed. The initial new Run test attempt had 46 passes and two assertion failures caused solely by comparing Windows slash formatting; the real loading transition and processing-service call had already succeeded. The assertions were corrected to compare Path objects and the full suite passed. Earlier development failures were repaired; no failed verification is represented as a pass.

Six authored Python files passed syntax compilation. Final imports cover `app.main`, `StaticAnalysisPage`, `ClinicalPlotDetailDialog`, and the synchronization client. One initial verification command used the nonexistent shorthand `DetailDialog`; its import failed, then the correct existing class name was checked. Scoped `git diff --check` passed; Git reports pre-existing CRLF normalization notices. Whole-repository clinical/manual-event tests that can modify patient data were not run.

### 11. Actual live QTM verification

QTM 2026.2 build 17495 and Python Example PAF 1.1.3 were running. The live test selected the canonical Session folder that the PAF API actually reports. All 11 initial field reads matched their correct real Qt controls at Float32 precision. Real GUI `textEdited`/`editingFinished` changed BodyMass from 75 to 75.125; live PUT and read-back confirmed 75.125 and the GUI reported confirmation. An independent REST PUT to 75.25 was detected by the real two-second GUI timer in **2.016 seconds**. Repeated polling produced no queued edits. The harness restored BodyMass to 75 in `finally`; all 11 queried parameters plus ID/Name/DOB matched their initial values exactly after cleanup. Other clinical values were not adjusted.

Live evidence is stored outside the repository at `C:\Users\ADMIN\Desktop\C\codex\shriners-followup2-baseline\live-anthropometric-roundtrip.json` and `live-roundtrip.py`. The canonical tested folder is `C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\Data\Claudia_123-20260928T142041Z-1-001\Claudia_123\2026-10-01_2`.

### 12. Live gaps and remaining limitations

Native QTM Edit Fields dialog changes were not automated because Computer Use had previously been stopped by the user. Live reverse synchronization was tested through the actual PAF field API plus the real Qt timer. Every field was tested bidirectionally against a disposable PAF server; only BodyMass was deliberately changed in live QTM. The new Run tests validate the button, loading view, and real processing-service invocation boundary; they do not claim a fresh successful clinical-engine calibration on patient data.

An imported alias folder currently references a Session GUID whose API `Path` remains its original canonical folder. Full-path matching deliberately refuses that alias rather than guessing by basename or writing a different subject. Live synchronization for such an alias requires selecting the authoritative canonical folder or fixing the project's alias/path mapping in QTM. This unresolved project-data condition is exposed as synchronization unavailable; an unchanged local static configuration can still start. The schema is specific to the existing PAF model, and arbitrary QTM navigation does not silently change the GUI's selected session. Graph limits persist for the lifetime of the current page/application only. Existing QTM fields outside the PAF entry bounds were observed and preserved; this work does not certify those measurements as clinically correct.

The running Shriners Python process does not hot-reload source changes. Close/reopen the application to use the corrected Run behavior.

### 13. Previous fixes and scope audit

All unrelated source hashes match the captured follow-up baseline, including the event/frame helpers, detector, both static adapters, gait engine/template files, trajectory/marker handling, and processing service. AST checks confirm `_mean_curve`, `_schedule_plot_refresh`, `_on_filter_toggled`, `calculate_dynamic_y_limits`, and `_draw_idle` remain identical. The existing retained-artist update loop was preserved. No commit or push was made. No file deletions or moves were introduced.

### 18. Final diff, complete changed-file inventory, and runtime files

The six authored Python source/test files total **1,254 inserted and 250 removed lines** relative to the captured start-of-follow-up snapshot. This document is the seventh authored file. Git HEAD already contained substantial changes from earlier work, so its larger diff is not attributed to this follow-up. Complete source/test diff files, baseline hashes, final test log, full Git status, and `final-audit.json` are kept in `C:\Users\ADMIN\Desktop\C\codex\shriners-followup2-baseline`.

Author-created live PAF writes rewrote the canonical Session `data.qpr`. Values were restored and verified, but binary byte identity was not restored or claimed. Separately, during the session, QTM's message log records a 21-file batch at 20:20:41–20:20:42 that saved Static 3 and exported Static 3 plus Dynamic 1–20 C3Ds in the imported alias folder. No agent tool launched that batch. Those concurrent runtime files were not reverted or edited to conceal the changes. The full snapshot-delta inventory follows, including runtime changes, so it is not mistaken for source edits.


| Authored file (absolute path) | Added | Removed |
|---|---:|---:|
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\app\ui\charts\clinical_plots.py` | 146 | 94 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\app\ui\pages\case_presentation_page.py` | 1 | 0 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\app\ui\pages\static_analysis_page.py` | 240 | 156 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\app\services\anthropometric_sync_service.py` | 233 | 0 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\tests\test_mac_scale_persistence.py` | 184 | 0 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\tests\test_anthropometric_sync.py` | 450 | 0 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\spec\session1.md` | Append-only documentation | 0 |

Complete additional runtime snapshot delta (paths relative to repository root):

- modified: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/session.xml`
- modified: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Static 3.qtm`
- modified: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/Claudia_123-20260928T142041Z-1-001/Claudia_123/2026-10-01_2/data.qpr`
- modified: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Messages/Messages 2026-10-08.log`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 1.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 10.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 11.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 12.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 13.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 14.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 15.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 16.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 17.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 18.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 19.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 2.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 20.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 3.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 4.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 5.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 6.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 7.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 8.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Dynamic 9.c3d`
- new: `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/Static 3.c3d`

No runtime deletion was observed. These files are included for disclosure and are not described as authored source changes.

### 19. Final verification status

Shared graph-scale persistence, all 11 parameter mappings, transport/read-back behavior, concurrent editing, lifecycle cancellation, static Run startup, focused regressions, syntax/imports, and preservation of earlier source fixes passed the checks described above. Native-dialog and full clinical-engine certification remain the explicit gaps in section 12. Documentation history is preserved byte-for-byte as the original prefix.


## Session 1 Follow-up 3 — Patient Metadata and Anthropometric Synchronization

2026-10-08. Scope: patient and anthropometric metadata only. The application implementation is tested; **full live two-way acceptance remains BLOCKED for the currently open imported session**, because its GUID is duplicated in the QTM project. The supported write endpoint resolves that GUID to another folder. No GUID repair, folder move, metadata mutation, or native measurement switching was performed during this follow-up.

### 1. Why the previous implementation failed

The earlier implementation hooked only the 11 anthropometric QLineEdits. Name, patient number and DOB were read from local static Python/XML files, had no editing handlers, and were never applied on incoming polls. The transport retained ID/Name/DOB for explicit Save, but Save could push those stale local values instead of the live patient record. Sex was omitted altogether. The previous notes explicitly limited live testing to a canonical folder and BodyMass; they did not establish working synchronization for the imported folder shown by the user.

The live project has **two distinct Session nodes with GUID `{17698CAD-BDA1-11F1-891E-2C58B910BA1C}`**. Tree reads show separate full paths and separate values. At investigation, the open trial's imported session reported BodyMass **71 kg** and Height **0.209999993 m**, while the direct GUID endpoint reported the other session's BodyMass **100 kg** and Height **0.600000024 m**. The earlier description of this as a path alias was incomplete: it is a duplicated identifier, with distinct metadata in each copy. A basename match or blind GUID PUT would target the wrong copy.

Additionally, the GUI's "QTM Connected" label was raised when the application's local gRPC listener started. It did not establish remote connectivity, PAF availability, or patient-field read/write capability.

### 2. Actual APIs and their capabilities

Installed `C:\Program Files\Qualisys\Qualisys Track Manager\REST\RESTful_QTM_API.pdf` documents GET/PUT `/api/v1/paf/instance/{ID}`, GET `depth` for embedded child/parent containers, and `typeInfo=true` for TypeName, ReadOnly and Enum Content. PUT changes only the addressed container's Fields dictionary; container ID, ChildIDs and ParentIDs are immutable. No supported operation for replacing an existing Session GUID or addressing a duplicated GUID by full path was found. `/api/v1/project` exposes OpenProject and ProjectDirectory as status, not editable patient metadata. Live `/api/v1/paf` lists only `instance`.

The installed PAF schema is `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Settings.paf`, Python Example 1.1.3. Real type information reports ID/Name as UnicodeString, DOB as Date, Sex as Enum with Female/Male/Other, and all 11 dimensions/mass fields as Float32. These fields report ReadOnly=false at the uniquely addressed Session endpoint. Actual availability/ReadOnly is checked before writing; unsupported or ignored writes are errors, never assumed successes.

The [official qtm.file API](https://qualisys.github.io/qtm-scripting/latest/qtm.file.html) supports the currently open measurement's `get_path`, also via POST `/api/scripting/qtm/file/get_path/`. This is used to follow its Session folder. The [documented selection API](https://qualisys.github.io/qtm-scripting/latest/qtm.gui.selection.html) selects trajectories/bones; it does not expose project-tree patient selection. No suitable patient-field change notification was found in the installed REST documentation or official scripting modules. A controlled two-second poll is therefore retained.

### 3. Patient/session mapping

| GUI representation | Actual destination | Representation | Two-way status |
|---|---|---|---|
| First Name | Session/connected Subject `Name` | Unicode string, preserved intact | Supported when the target can be uniquely addressed |
| Last Name | None in installed PAF schema | Local `valueLastName` | UNSUPPORTED; local-only tooltip, no split/join or invented field |
| Patient Number | `ID` | String; leading zeros preserved | Supported with the same target restriction |
| Sex | `Sex` | Female, Male, Other | Supported; added control in the existing unused patient-grid position |
| Date of Birth day/month/year | `DOB` | One ISO `YYYY-MM-DD` Date | Supported with the same target restriction |

`Name` is mapped to the existing First Name control as the earlier application did. A full name already stored in QTM remains whole in that control; no assumption is made about where to split it. No GUI last name is appended to QTM Name. A genuine Subject is used only for a field not exposed by its Session. A Raw folder is never treated as a patient or written.

### 4. Anthropometric mapping and units

| QTM field | GUI field | Units | Input bounds |
|---|---|---|---|
| BodyMass | Body Mass | kg | 0–250 |
| Height | Height | m | 0.5–2.5 |
| InterAsisDistance | ASIS-to-ASIS | m | 0.1–0.4 |
| LeftLegLength / RightLegLength | Left / Right Leg Length | m | 0.6–1.2 |
| LeftKneeWidth / RightKneeWidth | Left / Right Knee Width | m | 0.06–0.15 |
| LeftAnkleWidth / RightAnkleWidth | Left / Right Ankle Width | m | 0.05–0.12 |
| LeftAsisTrocanterDistance / RightAsisTrocanterDistance | Left / Right ASIS-to-GT | m | 0–0.3 |

All 11 remain supported by the same shared field flow. `Trocanter` is the real installed spelling. No conversion is needed between PAF and GUI units. Float32 equality and nine-digit rendering remain intact. The old magnitude-based millimetre guess in local fallback display was removed; a height of 210 in a source that this interface treats as metres is not silently divided by 1,000. Suspicious finite live values are displayed unchanged and flagged in status/tooltips; new out-of-range edits are rejected. Existing finite calibration values/zero sentinels retain the previously fixed static Run behavior.

### 5. Other details and unsupported/read-only fields

Trial Activity is a local clinical activity selection, not equivalent to QTM's per-measurement `Measurement type` (Static/Dynamic). Trial Modifier, Assistive Device, Static Forward Direction, Static Frame Number, and foot-model/configuration fields lack equivalent shared fields in this PAF and remain local. Tooltips identify the local configuration controls. Capture date is loaded from readonly Creation date/local configuration, not PUT back as a patient attribute. Session ID, Operator, Comments and project status do not have corresponding editable patient controls here and are not written. No unrelated metadata is included in a patient PUT.

The immutable Session **GUID** is distinct from editable patient `ID` and from the clinical `Session ID` field. Changing those ordinary fields cannot repair the duplicated internal GUID. Native project-tree selection without opening a measurement is not exposed by the investigated scripting API; select the GUI session path when no QTM measurement is open, or open the desired QTM measurement. This limitation is not claimed as a passing selection test.

### 6. XML, measurement metadata, local configuration and live state

Initial local loading uses Static_*.py, then Session-level Fields in session.xml, with C3D PROCESSING fallback for supported local values. XML remains an exported snapshot, not an interface to QTM's in-memory record. The old merge of Measurement Fields into patient/session XML data was removed: a stale static measurement's mass/name must not replace the Session patient values. The separate binary-QTM/C3D metadata service supplies trial/frame/comment information, not the patient synchronization target.

Once a live read completes, each clean mapped control takes its value from the selected live PAF Session/Subject. Local Save remains a local calibration operation. XML changes are restricted to Session Fields and the exactly selected static measurement snapshot, instead of copying into every unrelated measurement. Patient strings are serialized to Static_*.py with Python repr so names with apostrophes remain valid; the generated file's patient-name component is sanitized without changing the actual patient name. No session.xml write is represented as live QTM confirmation.

### 7. Correct target resolution and polling

The worker reads QTM's open measurement path before a poll/write. If it belongs to another Session, the page loads that folder's session.xml and chooses an available static trial (QTM preferred over C3D), retaining old uncommitted drafts. Missing session.xml blocks writes and explains the selection requirement. Polling remains visible/config-view-only, on background QRunnable work, with bounded HTTP deadlines and cached discovery.

Discovery now inspects embedded child containers from their actual parent branches. It matches full normalized Session Path and Class, without discarding distinct branches just because their GUIDs are equal. The direct write endpoint is then checked against that path. If it addresses another copy, reads continue from the correct parent branch but `writable=false` blocks PUT and a visible patient-card status explains the duplicate-GUID condition. Normal uniquely addressed Sessions retain the cached direct read. The selected Session folder, rather than trial filename, identifies patient drafts, because these are Session fields.

### 8. GUI writes and incoming updates

Name/ID now use textEdited and editingFinished; Sex/DOB use user activated signals. DOB's three controls produce one validated date and one field update. Dirty fields, revisions, pending latest values and confirmations are shared with anthropometric fields. Explicit Save commits only dirty mapped fields; stale ID/Name/DOB are no longer inferred from the entire form and pushed automatically.

The worker validates input, verifies context, checks field ownership/ReadOnly/Enum, and submits only changed keys. It rechecks the open Session before PUT. Read-back must match the intended string/date/enum or Float32 value and context. HTTP errors, ReadOnly, absent fields, invalid incoming dates and HTTP-200 ignored writes remain visible errors. The GUI applies confirmed clean values with blocked signals and never starts a second PUT from an incoming update.

### 9. Conflict, reconnect and status behavior

Dirty text and invalid/uncommitted dates are protected against incoming polls. A response clears a draft only if the submitted revision/value still matches. Rapid commits keep the latest pending value; subsequent uncommitted typing is retained. Selecting another Session cancels old work, saves drafts under the old folder, and does not replay them into the new patient. Context-generation/GUID changes prevent a queued old write from reaching a new target.

Disconnects stop automatic write replay, retain drafts and reconcile current clean values on reconnect; retained drafts require review/recommit. Hide/close/processing transitions stop polling and cancel work without a network wait. Partial or unconfirmed updates leave their fields dirty and report an error; no overall success or pending static Run is claimed. The installed API provides no atomic multi-owner transaction or compare-and-swap; a change after the final target check can still race, and a transmitted request cannot be recalled. Read-back detects the observable result.

The generic gRPC badge now says **Bridge Listening**, reflecting what starting the local listener proves. Static Analysis has separate actual patient-metadata status next to patient controls and the existing Save/Run status. Long errors wrap without widening the page. Read-only duplicate Session data never appears as a successful write connection.

### 10. Source files, classes and functions changed

The exact authored inventory/diff table is appended below. `QtmAnthropometricClient` gains active_session_dir, branch-aware read resolution, patient validation, duplicate-target blocking and write/read-back guards. `validate_patient_field` and `same_field_value` handle typed patient values. `_SyncOperation.run` carries the actual open Session into the result. Existing public service/class names were retained to avoid changing callers.

`StaticAnalysisPage` changes patient-card construction, `_auto_fetch_static_data`, `_build_updated_static_py`, `_update_session_xml`, `_init_anthropometric_sync`, `_prepare_anthro_context`, commit/request/result callbacks, `_sync_to_qtm`, `_save_static_parameters`, and shared `_sync_value`/`_set_sync_value`/choice/status helpers. MainWindow header and QTMMonitorPage each have one connection-label change. One existing HTTP fixture was made faithful to embedded tree responses and open-file REST queries; one patient-specific test module was added.

### 11. gRPC review

No gRPC command, proto, client/server implementation, frame/event callback or trajectory operation was changed or introduced. The proto's QtmFields contains frames, capture_frequency, first_frame and last_frame. The server dispatch exposes measurement/event/trajectory/project-directory commands, not editable patient properties. Starting that listener is not evidence that patient APIs exist. Metadata uses the installed PAF REST operations directly.

### 12. Validation and tests

Patient validation preserves Unicode/ID leading zeros, rejects control characters and empty Name, validates real calendar dates including leap years, rejects future DOB, and checks Sex against the supported enum. Incoming years outside the old combo's 1930–2035 range can be displayed without truncation. All programmatic updates block signals; invalid incoming dates do not erase the GUI and recover on a later valid read.

The new patient test module contains 33 cases: each of four patient fields in both directions with exact single-field PUTs; user typing protection; invalid date/sex/name; each patient field ReadOnly; reconnect/no replay; real open-session switching and old drafts; queued writes blocked for a newly selected patient; duplicated GUIDs with different values/paths; measurement-vs-session XML sources; apostrophe-safe local Save and unrelated measurement protection; suspicious-unit values; invalid incoming date recovery; rapid revisions; ignored PUT/HTTP failure/missing field; unexported selected Session; and long status layout. The previous 50 anthropometric cases still verify all 11 fields both ways with real HTTP and Qt controls.

Final command, with the python-example conda interpreter, `QT_QPA_PLATFORM=offscreen` and conda Library/bin on PATH:

```powershell
python -X utf8 -m pytest tests/test_patient_metadata_sync.py tests/test_anthropometric_sync.py tests/test_mac_scale_persistence.py tests/test_session1_regressions.py tests/test_dynamic_plot_scaling.py tests/test_bilateral_mean_separation.py tests/test_10_trials_support.py -q --disable-warnings --maxfail=2
```

Final result: **148 passed, 14 warnings, 65.05 seconds, exit code 0**. Development checks first passed 50 existing cases, then 77 metadata cases. An initial session-draft return test exposed trial-specific draft identity; using the Session folder corrected that defect. A layout test initially assumed a zero-width overflow in an unthemed offscreen fixture; that fixture already had 171 pixels of overflow from missing system fonts. The test now verifies that metadata errors introduce no additional overflow. The themed live panel with registered fonts independently measured zero overflow. Those failed attempts are not described as passes.

Six authored Python files passed compilation/import checks including app.main, StaticAnalysisPage and QtmAnthropometricClient. Scoped Git diff checks passed (existing CRLF normalization notice only). No dependency was installed. Tools: rg, PowerShell, Git, urllib, pytest, PySide6/QTest, hash/AST inspection, installed REST documentation, and Agent Reach/Jina plus official Qualisys web pages. Ponytail/Graphify were applied; no unrelated graph generation was performed.

### 13. Live QTM verification — exact status

Real QTM 2026.2 build 17495, Python Example PAF 1.1.3, and the actual API were queried. The current measurement was imported-folder Dynamic 1.qtm and had `is_dirty=true`. It was neither saved nor switched. Real type info confirms the field names, storage types, writable flags and Sex enum.

**PASS, actual QTM-to-GUI reads:** all 15 controls first read the selected imported Session. They were then deliberately assigned stale local values without marking user edits; the real two-second Qt timer replaced every value with live QTM data in about two seconds. Thus this test is more than initially matching strings. It does not claim an external native-dialog edit was performed. Live values included Claudia, ID 123, Female, DOB 2006-09-14, BodyMass 71, and Height 0.209999993 m.

**PASS, actual wrong-target protection:** a Name diagnostic draft was committed through the real Qt editing signals. No write was sent because the direct endpoint addressed the other copy. The draft stayed visible/dirty. Both copies' queried Fields, the open filename and its unsaved state remained exactly unchanged after the harness. GUI-to-QTM write/read-back for these 15 fields passed against the disposable PAF server, not live QTM.

**BLOCKED, live GUI-to-QTM writes to the selected copy:** the duplicate GUID prevents safe addressing. Native QTM Edit Fields changes, selected project-tree row switching and live two-way field-change certification are not passed. No temporary write was sent to the other patient's copy to disguise this gap. No native Computer Use was resumed after the earlier user stop.

Evidence and screenshots are outside the repository at `C:\Users\ADMIN\Desktop\C\codex\shriners-followup3-baseline`: live-tree.json, session/type snapshots, live-file-state-before.json, live-patient-sync.py/json, live-patient-panel.png, final-tests.txt, baseline hashes, source diffs and audit.json. The screenshot verifies the existing two-column design, added Sex/status, correct selected values and no horizontal scroll with the real theme/fonts.

### 14. Remaining blockers and limitations

To complete live two-way synchronization for the imported copy, QTM must give it a unique internal Session GUID or remove the conflicting project instance so that the GUID endpoint returns the same selected folder. The ordinary patient number or Session ID field is not that GUID. The REST API documents GUID/relationships as immutable; this task did not guess an unsupported repair command or modify the binary project databases. Patient folders and unsaved measurements were preserved. Full acceptance therefore remains blocked on this QTM project-data repair.

No separate Last Name destination exists in this schema. Local clinical fields remain local. Project-tree selection without an open measurement cannot be followed through the investigated APIs; explicit GUI path selection remains the fallback. Polling is every two seconds only while the configuration view is visible, and the existing application process must be reopened to load changed Python code. Suspicious pre-existing measurements are flagged, not automatically corrected. No clinical-engine calibration was launched as part of this metadata task.

### 15. Prior fixes and complete file scope

Snapshot hashes prove chart scaling/performance, frame helpers, event services/detection, trajectory adapters, gait engine, processing service and protobuf definitions are unchanged. No event/frame or graph implementation was revisited. No file was deleted/moved; no Git commit or push was made. The previous documentation is preserved byte-for-byte as the appended section's prefix.

During this task, unrelated runtime changes were observed at 20:45:40–20:45:46: canonical Dynamic 1.c3d and auto_event_Dynamic 1.log changed, and QTM's message log records "Auto events: wrote 8 events". No metadata task tool launched auto-event processing; the regression detector runs use temporary C3Ds and mocked QTM writes. These runtime changes are disclosed in the full snapshot inventory, were not reverted, and are not attributed to the authored metadata source diff. The live metadata harness itself was non-mutating, as verified against both records and the open-file state.

### 16. Final Git/snapshot diff summary

The authored table below compares the captured beginning of this follow-up with the final source, separately from the large pre-existing Git HEAD diff. Source changes are limited to the four metadata/status files; test changes are the existing HTTP fixture and one new metadata test file. This append-only document is the seventh authored file. Additional runtime snapshot changes are listed separately.


| Authored file (absolute path) | Added | Removed |
|---|---:|---:|
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\app\services\anthropometric_sync_service.py` | 100 | 15 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\app\ui\pages\static_analysis_page.py` | 144 | 42 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\app\ui\pages\qtm_page.py` | 1 | 1 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\app\ui\main_window.py` | 1 | 1 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\tests\test_anthropometric_sync.py` | 9 | 2 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\tests\test_patient_metadata_sync.py` | 284 | 0 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\spec\session1.md` | Append-only notes | 0 |

Six source/test files total **539 added and 61 removed lines**, plus this documentation append.

Additional runtime files changed relative to the follow-up baseline (not authored source changes):

- modified: `C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\Data\Claudia_123-20260928T142041Z-1-001\Claudia_123\2026-10-01_2\auto_event_Dynamic 1.log`
- modified: `C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\Data\Claudia_123-20260928T142041Z-1-001\Claudia_123\2026-10-01_2\Dynamic 1.c3d`
- modified: `C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\Messages\Messages 2026-10-08.log`

Live two-way acceptance for the current imported Session remains **BLOCKED**, not passed. The application can read the correct copy and refuses wrong-copy writes; a unique QTM Session GUID is the remaining prerequisite.


## Session 1 Follow-up 5 — Manual Calibration Parameter Synchronization

Project: `C:\Users\ADMIN\Downloads\Shriners_Plugin`.

### Confirmed causes and scope

The existing “Edit Calibration / Re-run” action returns to `StaticAnalysisPage`'s configuration view; there is no separate calibration modal to replace. Its text `editingFinished` handlers, Sex/DOB selection handlers, pending-write queue, and two-second metadata timer made synchronization automatic. Save previously wrote local files first and displayed a green local-save message while the QTM operation was still pending. These behaviors conflicted with explicit manual Save/Fetch and could obscure a live write failure.

Only the existing calibration form, its PAF REST synchronization service, its two synchronization test files, and this append changed. Patient and anthropometric controls retain their layout, theme, field names, and validation. The footer now contains **Save Parameters**, **Fetch QTM**, and the existing **Save & Run Static Analysis**. No standalone page, plugin dependency, protocol method, folder restructuring, Git commit, or push was introduced.

The bridge, gRPC schema/server, `qtm_metadata_service`, and page callers were inspected. The installed `QtmFields` message carries frame count/frequency/first/last frame; it does not provide patient metadata. The metadata service reads trial/session files for trial metadata. Manual parameter synchronization reuses the working QTM PAF REST interface instead of inventing a gRPC patient command. Unrelated bridge status, capture/measurement callbacks, processing, graphs, trajectories, frame coordinates, labeling, events, and QTM tree expansion remain unchanged.

### Exact files, classes, and functions

- `C:\Users\ADMIN\Downloads\Shriners_Plugin\app\ui\pages\static_analysis_page.py`: `StaticAnalysisPage._create_config_view`, `_auto_fetch_static_data`, `_init_anthropometric_sync`, `_on_patient_choice`, `_prepare_anthro_context`, `_on_anthro_edited`, `_anthro_status`, `_on_anthro_sync_finished`, `_on_anthro_view_changed`, `hideEvent`, `closeEvent`, `_save_static_parameters`, `_on_save_clicked`, `_on_run_clicked`; new `_has_unsaved_sync_edits`, `_on_local_calibration_edited`, `_on_fetch_clicked`, `_start_manual_sync`. Removed the automatic `_commit_anthro_parameter`, `_request_anthro_sync`, `_sync_to_qtm`, show-time refresh, timer, pending queue, and run-after-sync machinery. `_sync_value` and `_set_sync_value` are reused for all mappings and blocked Qt signals.
- `C:\Users\ADMIN\Downloads\Shriners_Plugin\app\services\anthropometric_sync_service.py`: `QtmAnthropometricClient.__init__`, new `_project`, `active_session_dir`, `read`, `synchronize`, and `_SyncOperation.run`. `AnthropometricSyncService.request/cancel` and its background QRunnable/QThreadPool transport remain the operation mechanism.
- `C:\Users\ADMIN\Downloads\Shriners_Plugin\tests\test_anthropometric_sync.py`: disposable real HTTP PAF/project fixtures, real Qt button actions, existing anthropometric/validation/processing regressions adapted to explicit synchronization, plus multi-field, partial update, project/target collision, and manual workflow checks.
- `C:\Users\ADMIN\Downloads\Shriners_Plugin\tests\test_patient_metadata_sync.py`: all four metadata mappings, confirmation accept/cancel, dirty revisions, selected-session safety, duplicates on either copy, local configuration confirmation, and live/local separation checks.
- `C:\Users\ADMIN\Downloads\Shriners_Plugin\spec\session1.md`: this append only. Previous 91639 bytes preserved; SHA-256 of the previous document is `567f9298c90edacf821a4bac14b816d8a7c58bc78c4612f2b823d676ae1a4223`.

### Save Parameters

The button collects all 15 supported controls. GUI validation rejects invalid names, dates, sex values, non-finite/overflowing numeric values, and new values outside the model bounds before any HTTP write. Unchanged preexisting finite numeric values outside input bounds remain usable and are flagged; they are not silently converted or rewritten. Numeric comparisons use Float32 equivalence and nine-digit round-trip display values, avoiding repeated writes caused by representation differences.

The worker reads the active QTM measurement path and active project. Save never redirects an old form into another QTM session: a different active measurement directory blocks Save and requires Fetch/review. Full normalized session directory, project name/directory, Session instance ID, and genuine Subject owner ID form the context token. If an existing token changes, repeated Save clicks stay blocked until Fetch establishes the reviewed target. A first Save without a prior Fetch can establish a fresh target only when the GUI session directory matches the live context and the target is uniquely addressable.

The client compares the complete GUI snapshot with freshly read live fields and groups only changed supported values by their actual owners. Session fields take precedence; a genuine Subject is used only for fields absent from the Session. RawFolder is never treated as a patient owner. Before each owner PUT, it rediscovers the session copies, checks context/owners/active measurement again, checks actual writable field metadata and Sex content, and checks cancellation. Unavailable/read-only fields are reported individually while other writable fields can succeed.

After PUT responses, live fields are read again from the intended session and compared with the submitted values and context. The UI reports **Verified** and **Failed** fields for partial results, retains failed/new drafts, and claims all parameters verified only when every requested field is confirmed. HTTP success with an ignored value does not count as persistence. A read-back/connection failure cannot produce a blanket saved message. Repeated unchanged Save on a unique target performs reads but sends no PUT.

**Local files are separate:** Save Parameters performs live QTM synchronization, not a success claim based on `session.xml` or a generated Python file. Last Name and other calibration fields have no shared PAF destination and are identified as local-only in existing tooltips plus the Save tooltip/status. **Save & Run Static Analysis** retains local `Static_*.py`/`session.xml` saving and processing, with no hidden manual-metadata REST commit or QTM confirmation gate. Fetch and Save do not rewrite local clinical files. Root session fields and selected measurement snapshots remain distinct in the existing local saver.

### Fetch QTM and dirty state

Fetch calls `read` directly with an empty update set; it never calls the write path or PUT. It follows the session directory of QTM's open measurement, otherwise the explicit GUI directory. With no GUI session, an open QTM measurement can supply the context. Existing static-trial selection/local fallback are reused when moving the form to another session; a new context without `session.xml` is reported clearly rather than used as a local calibration target.

Before fetching, a default-No Qt confirmation asks: “Fetching QTM parameters will replace your unsaved changes. Continue?” Cancel performs no HTTP operation and retains the form. Accept replaces supported fields only on a successful read. Failed/missing incoming fields remain visible as errors, rather than erasing valid GUI values.

Text/choice editing marks the 15 shared fields dirty without requesting reads or writes. A baseline also detects supported values changed programmatically. Local-only text, combo, checkbox, and radio edits are tracked to require confirmation before a Fetch switches/reloads sessions. Same-session Fetch leaves these local controls intact; local saving clears their local dirty flag. Drafts for shared fields remain associated with the full session directory when changing sessions.

`QSignalBlocker` prevents incoming field updates from causing edit callbacks. Revision and submitted-value checks retain newer edits made while a request is in flight. A generation check discards old results after a GUI context change. Buttons disable during a request; there is no automatic retry, queued replay, or polling on show/local reload. Hide/close/processing transitions cancel pending work without blocking Qt. Unrelated QTM status/measurement services remain intact.

### Supported field mappings, units, and validation

| GUI control | Live PAF field | Unit / allowed new values |
|---|---|---|
| First Name | `Name` | Full unsplit nonempty patient name; no control characters |
| Patient Number | `ID` | String; leading zeros retained; no control characters |
| Date of Birth day/month/year | `DOB` | ISO date `YYYY-MM-DD`, real date, not future |
| Sex | `Sex` | Female / Male / Other, checked against live enum content before writing |
| Body Mass | `BodyMass` | kg, 0–250 |
| Height | `Height` | m, 0.5–2.5 |
| ASIS distance | `InterAsisDistance` | m, 0.1–0.4 |
| Left / Right leg length | `LeftLegLength` / `RightLegLength` | m, 0.6–1.2 |
| Left / Right knee width | `LeftKneeWidth` / `RightKneeWidth` | m, 0.06–0.15 |
| Left / Right ankle width | `LeftAnkleWidth` / `RightAnkleWidth` | m, 0.05–0.12 |
| Left / Right ASIS–trochanter distance | `LeftAsisTrocanterDistance` / `RightAsisTrocanterDistance` | m, 0–0.3; real PAF spelling retained |

Both sides are explicitly mapped; none are swapped. GUI and the bundled Shriners PAF schema already use kg and metres, so no magnitude-based conversion is required or guessed. Bounds remain tied to the actual bundled `Settings.paf`, with Float32 endpoints checked by tests. Real QTM type metadata exposes Float32/read-only/content information, not a unit property; other PAF models with different units are outside this model's supported mapping.

### Real QTM commands and collision safeguards

Existing API requests at `http://localhost:7979`:

- `GET /api/v1/project`: active project name/directory, checked around reads and included in the target token.
- `POST /api/scripting/qtm/file/get_path/` with `[]`: read-only scripting command identifying the open measurement. Its parent supplies the active session context.
- `GET /api/v1/paf/instance?depth=3`, bounded ancestor `GET /api/v1/paf/instance/{id}?depth=2` when needed: embedded session discovery across the current project.
- `GET /api/v1/paf/instance/{id}?depth=-1`: directly addressed Session data/parents and read-back.
- `GET /api/v1/paf/instance/{owner-id}?typeInfo=true`: field availability/read-only/enum content.
- `PUT /api/v1/paf/instance/{owner-id}` with changed-field JSON only: Save, never Fetch.

Read discovery no longer stops after the first matching session or trusts a cached GUID. It checks all discovered copies, comparing full normalized paths and the direct endpoint. If a Session GUID occurs under different paths, **both copies are blocked for writes**, including the canonical/directly addressable copy. Duplicate Subject owners are also blocked. A collision introduced immediately before PUT is caught by the second discovery. Discovery is bounded to 256 visited edges and a four-second discovery budget, with one-second HTTP request deadlines; incomplete discovery fails instead of assuming uniqueness.

The earlier 71 kg versus 100 kg incident was evidence of distinct copies sharing `{17698CAD-BDA1-11F1-891E-2C58B910BA1C}`; those historic values are not used to identify the target. The collision still exists in the live project. Both full conflicting paths appear in error text and tooltips:

```text
QTM has duplicate Session GUIDs or an ambiguous owner. Writes blocked. Ambiguous paths: C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\Data\2026-10-01_2-20261004T101228Z-1-001\2026-10-01_2\ | C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\Data\Claudia_123-20260928T142041Z-1-001\Claudia_123\2026-10-01_2\
```

### Verification commands and actual results

Runtime: `C:\Users\ADMIN\anaconda3\envs\python-example\python.exe` (Python 3.10), with `QT_QPA_PLATFORM=offscreen` and the environment's `Library\bin` on PATH. Disposable HTTP integration tests use real Qt controls and real HTTP requests; successful PUT/read-back tests do not mutate the installed live QTM project.

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PATH='C:\Users\ADMIN\anaconda3\envs\python-example\Library\bin;'+$env:PATH
& 'C:\Users\ADMIN\anaconda3\envs\python-example\python.exe' -X utf8 -m pytest tests/test_anthropometric_sync.py tests/test_patient_metadata_sync.py tests/test_mac_scale_persistence.py tests/test_session1_regressions.py tests/test_dynamic_plot_scaling.py tests/test_bilateral_mean_separation.py tests/test_10_trials_support.py -q --tb=short
```

Final result: **165 passed, 14 warnings in 92.02s (0:01:32)**. The warnings are existing Matplotlib/Pyparsing deprecations. Earlier manual regression iteration: 161 passed; focused rerun after local-only dirty-state tracking: 40 passed. Development failures caused by obsolete automatic-poll assertions, a Float32 payload representation assertion, and a test changing field ownership without Fetch were corrected; no failing tests were skipped.

| Scenario | Actual result and environment |
|---|---|
| GUI BodyMass 72 and finish editing | Mock: QTM stays 75 with zero PUT/GET polling after >2 seconds; live: actual 71 stays 71 |
| Save BodyMass 72 | Mock: correct session receives only BodyMass, read-back 72, dirty state cleared; live: correctly BLOCKED by duplicate GUID |
| External QTM BodyMass 73 | Mock: GUI stays 72 until explicit Fetch; no background requests |
| Fetch | Mock: correct GUI field becomes 73, no additional PUT; live: all 15 real mapped fields fetched |
| Multiple edited fields | Mock: all 15 fields sent under correct names, verified with Float32/string comparison |
| Fetch with unsaved edits | Real Qt button/confirmation call tested with deterministic Yes/No answers; cancel does no HTTP, accept reads without PUT; local text/combo/checkbox cases also checked |
| Duplicate GUID | Mock and live: aliases and canonical targets blocked, conflicting paths reported, no wrong-copy write |
| Offline Save / Fetch | Mock: clear failure, GUI draft retained, Qt timer remains responsive during HTTP timeout |
| Repeated Save unchanged | Mock unique target: verified, no additional PUT |
| QTM session/project switch | Mock: old-form Save blocked, repeated project-change Save blocked until Fetch, no cross-session writes |
| GUI session switch during request | Mock: cancelled old request, stale result ignored, old-session draft retained |
| Partial failure | Mock: same-owner read-only/ignored field and separate-owner HTTP failure distinguish Verified/Failed; failed draft retained |
| Read-only/missing/invalid fields | Mock: explicit field errors, no blanket success; invalid incoming DOB/numeric values cannot erase valid controls |
| New typing during Save / Fetch | Mock: newer revision retained dirty, no queued automatic replay |
| Static Run | Mock processing service: valid local saves still start loading/processing without manual metadata PUT; new invalid values still rejected |
| Previous frame/event/trajectory/graph behavior | Existing focused regression modules passed; implementation files unchanged |

### Live verification and limitations

Live harness: `C:\Users\ADMIN\Desktop\C\codex\shriners-followup5-baseline\live-manual-sync.py`; report `live-manual-sync.json`; screenshots `manual-patient-panel.png` and `manual-action-row.png` in the same external evidence directory. The harness uses the actual installed QTM REST API and actual offscreen Qt Fetch/Save buttons, with confirmation responses substituted for deterministic testing. It does not automate the native QTM UI.

Installed QTM: 2026.2 build 17495; PAF package Python Example 1.1.3. Open measurement when checked:

```text
C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\Data\Claudia_123-20260928T142041Z-1-001\Claudia_123\2026-10-01_2\Static 3.qtm
```

All 15 fields matched actual live values after Fetch, including BodyMass 71 kg and Height 0.6000000238418579 m. Editing BodyMass to 72 and finishing editing produced no network sync. Save displayed the collision and both paths and emitted **zero live PUT requests**. Fetch cancel preserved that draft; accepted Fetch restored the real 71 kg. Selected and directly addressed copy fields, open measurement, and QTM unsaved state were identical before/after. Themed screenshots were inspected: both buttons are visible in the existing footer and horizontal scrollbar maximum is zero; full long errors also have tooltips.

**A successful live GUI→QTM write is NOT verified for this project:** the duplicate GUID must be resolved in QTM to establish a unique write target. No GUID reassignment, folder repair, trial saving/closing, or bypass was attempted. Mock transport tests verify the successful unique-target path and partial failures; they are not presented as a live write pass.

The installed scripting API exposes the open measurement path, not the highlighted project-tree row. Fetch therefore uses the open measurement's session; when none is open (or the older get_path method is absent), it uses the explicit GUI session. This is stated in the Fetch tooltip. Pure tree-row selection and native patient-dialog editing were not verified. The bundled PAF field mapping is the supported unit schema. No atomic multi-owner transaction or compare-and-swap is offered by this API: guards run before each PUT, but an already-sent request cannot be recalled. Partial/uncertain outcomes remain errors and require review/read-back; there is no silent rollback/retry.

### Complete diff summary and preservation

The project started with a dirty working tree. Git HEAD's aggregate diff includes earlier/user work and cannot attribute this follow-up by itself. A 704-file baseline and copies of all edited files were captured before implementation outside the project at `C:\Users\ADMIN\Desktop\C\codex\shriners-followup5-baseline`. Complete follow-up unified patch: `complete-task.diff`; per-file patches and `audit.json` in the same directory.

This follow-up's source/test deltas relative to that baseline:

| Full file | Added lines | Removed lines |
|---|---:|---:|
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\app\services\anthropometric_sync_service.py` | 91 | 69 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\app\ui\pages\static_analysis_page.py` | 130 | 163 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\tests\test_anthropometric_sync.py` | 209 | 73 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\tests\test_patient_metadata_sync.py` | 146 | 76 |
| `C:\Users\ADMIN\Downloads\Shriners_Plugin\spec\session1.md` | This append | 0 |

All 219 other `.py`/`.proto`/`.paf` sources matched baseline hashes. The full manifest before this documentation append found exactly these four modified source/test files, no new/deleted project files, and no changed clinical/runtime data files. Earlier documentation remains an exact byte prefix. No prior frame/trajectory/chart/clinical engine files were edited or reverted.

For completeness, the entire tracked Git diff summary below includes preexisting changes; it is **not** the follow-up-only delta. Git reports 73 tracked diff entries and 99 total status entries. Full raw snapshots are `git-numstat-after.txt` and `git-status-after.txt` in the external evidence directory.

| Repository-relative file | Git added | Git removed |
|---|---:|---:|
| `Gait-lab-Vicon-to-QTM/Py3_ComputeGDI.py` | 0 | 1 |
| `Gait-lab-Vicon-to-QTM/Py3_CreateGCD-Run.py` | 7 | 1 |
| `Gait-lab-Vicon-to-QTM/Py3_DynamicMain.py` | 2 | 4 |
| `Gait-lab-Vicon-to-QTM/Py3_GaitModules.py` | 127 | 95 |
| `Gait-lab-Vicon-to-QTM/Py3_SittingFootStaticMain.py` | 6 | 1 |
| `Gait-lab-Vicon-to-QTM/Py3_StaticMain.py` | 34 | 7 |
| `Gait-lab-Vicon-to-QTM/Py3_WriteHeelToeMarkers.py` | 7 | 1 |
| `Gait-lab-Vicon-to-QTM/Py3_varExtractor.py` | 79 | 28 |
| `Gait-lab-Vicon-to-QTM/QTM_GRPC/gapi.py` | 0 | 5 |
| `Gait-lab-Vicon-to-QTM/QTM_GRPC/tools/Py3_staticmain.py` | 213 | 34 |
| `Gait-lab-Vicon-to-QTM/auto_event_trigger.py` | 191 | 57 |
| `Gait-lab-Vicon-to-QTM/gapi.py` | 53 | 25 |
| `Gait-lab-Vicon-to-QTM/test_auto_event_zero_events.py` | 4 | 1 |
| `MAC_CasePresentation/DisplaySettingsLocation/0001111.py` | 6 | 1 |
| `MAC_CasePresentation/DisplaySettingsLocation/01.py` | 9 | 2 |
| `MAC_CasePresentation/DisplaySettingsLocation/02.py` | 8 | 1 |
| `MAC_CasePresentation/DisplaySettingsLocation/06.py` | 8 | 1 |
| `MAC_CasePresentation/DisplaySettingsLocation/11.py` | 8 | 1 |
| `MAC_CasePresentation/DisplaySettingsLocation/1234.py` | 8 | 1 |
| `MAC_CasePresentation/DisplaySettingsLocation/12345.py` | 8 | 1 |
| `MAC_CasePresentation/DisplaySettingsLocation/123456.py` | 8 | 1 |
| `MAC_CasePresentation/DisplaySettingsLocation/45454.py` | 6 | 1 |
| `MAC_CasePresentation/DisplaySettingsLocation/8.py` | 6 | 1 |
| `MAC_CasePresentation/FilePathSettings.py` | 17 | 12 |
| `MAC_CasePresentation/MAC_CasePresentation.py` | 20 | 10 |
| `QTM-GRPC/gapi.py` | 2 | 1 |
| `QTM-GRPC/startup_tools.py` | 15 | 10 |
| `QTM-GRPC/tools/Py3_staticmain.py` | 206 | 34 |
| `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Templates/Py3_ComputeGDI.py` | 0 | 1 |
| `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Templates/Py3_CreateGCD-Run.py` | 6 | 1 |
| `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Templates/Py3_DynamicMain.py` | 2 | 4 |
| `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Templates/Py3_SittingFootStaticMain.py` | 6 | 1 |
| `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Templates/Py3_StaticMain.py` | 22 | 8 |
| `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Templates/Py3_WriteHeelToeMarkers.py` | 6 | 1 |
| `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Templates/Py3_varExtractor.py` | 13 | 7 |
| `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Templates/gapi.py` | 22 | 9 |
| `Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Templates/test_c3d_events.py` | 6 | 1 |
| `app/models/data_models.py` | 13 | 3 |
| `app/services/event_service.py` | 701 | 2 |
| `app/services/gcd_service.py` | 31 | 16 |
| `app/services/pdf_report_service.py` | 60 | 19 |
| `app/services/processing_service.py` | 7 | 2 |
| `app/services/settings_service.py` | 161 | 13 |
| `app/ui/charts/clinical_plots.py` | 877 | 92 |
| `app/ui/dialogs/event_details_dialog.py` | 1036 | 140 |
| `app/ui/main_window.py` | 72 | 12 |
| `app/ui/pages/analysis_page.py` | 4 | 4 |
| `app/ui/pages/case_presentation_page.py` | 965 | 124 |
| `app/ui/pages/dynamic_analysis_page.py` | 393 | 15 |
| `app/ui/pages/patients_page.py` | 135 | 22 |
| `app/ui/pages/qtm_page.py` | 212 | 6 |
| `app/ui/pages/settings_page.py` | 27 | 3 |
| `app/ui/pages/static_analysis_page.py` | 339 | 186 |
| `app/ui/theme/design_tokens.py` | 40 | 20 |
| `app/ui/theme/theme_manager.py` | 66 | 0 |
| `app/ui/widgets/components.py` | 237 | 17 |
| `app/ui/widgets/smooth_scroll.py` | 1 | 1 |
| `app/ui/widgets/trial_row.py` | 21 | 0 |
| `scripts/capture_new_theme_screenshots.py` | 0 | 101 |
| `tests/capture_auto_event_screenshots.py` | 2 | 2 |
| `tests/capture_dark_and_light_theme.py` | 2 | 2 |
| `tests/capture_fp_screenshot.py` | 2 | 2 |
| `tests/capture_screenshots.py` | 2 | 2 |
| `tests/capture_ui_screenshots.py` | 2 | 2 |
| `tests/test_all_components.py` | 1 | 1 |
| `tests/test_auto_event_gui.py` | 9 | 10 |
| `tests/test_mac_case_presentation_guide.py` | 1 | 1 |
| `tests/test_new_workflow.py` | 1 | 1 |
| `tests/test_norm_ideal_range.py` | 2 | 2 |
| `tests/test_patients_data_location.py` | 8 | 8 |
| `tests/test_processing_ui.py` | 6 | 8 |
| `tests/test_smooth_scroll.py` | 1 | 1 |
| `tests/test_theme_toggle.py` | 27 | 32 |

Complete untracked status entries (already present at task start, including this service/tests/spec and earlier work):

- `app/services/anthropometric_sync_service.py`
- `app/services/frame_coordinates.py`
- `pyrightconfig.json`
- `resources/icons/chevron_down_teal.svg`
- `resources/icons/chevron_down_teal_dark.svg`
- `resources/icons/plus.svg`
- `spec/`
- `tests/benchmark_case_presentation.py`
- `tests/capture_manual_event_dialog.py`
- `tests/test_10_trials_support.py`
- `tests/test_anthropometric_sync.py`
- `tests/test_bilateral_mean_separation.py`
- `tests/test_case_presentation_smooth_scroll.py`
- `tests/test_collapsible_file_paths.py`
- `tests/test_dynamic_plot_scaling.py`
- `tests/test_loading_overlay.py`
- `tests/test_mac_scale_persistence.py`
- `tests/test_manual_event_editing.py`
- `tests/test_multi_trial_isolation.py`
- `tests/test_particular_session_mac_case.py`
- `tests/test_patient_metadata_sync.py`
- `tests/test_qtm_auto_event_sync.py`
- `tests/test_qtm_grpc_settings_sync.py`
- `tests/test_session1_regressions.py`
- `tests/test_titlebar_theme.py`
- `typings/`

The requested manual workflow is implemented and tested. The installed project's unique-target prerequisite for a successful live write remains unresolved and is explicitly blocked.


## Session 1 Follow-up 6 — Manual Parameter Synchronization and Session Resolution

Date: 2026-10-09. Scope: Save Parameters / Fetch QTM, their session and owner resolution,
and compact feedback. Existing folders, static processing, graphs, trajectories, events,
and frame-offset implementations were not changed. Nothing was staged, committed, or pushed.

### Confirmed root cause and identity investigation

The installed QTM project really contains two distinct Session records with the same
internal container GUID `{17698CAD-BDA1-11F1-891E-2C58B910BA1C}`. Full normalized paths
identify separate embedded records for reading, but they do not supply separate REST write identities.
The direct GUID GET consistently resolves to the canonical copy. Allowing the imported
copy to write through that same endpoint would address the canonical copy instead.
The previous collision block was therefore justified; this follow-up preserves it.

Live inspection used QTM 2026.2 build 17495 and PAF Python Example 1.1.3. Selected project:
`Shriners_Gait_Model_PAF_v1.0`; project directory:
`C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\`.
The open measurement during inspection was:
`Data\Claudia_123-20260928T142041Z-1-001\Claudia_123\2026-10-01_2\Static 3.qtm`
(relative to that project). Its unsaved/dirty state was true and was left unchanged.

Conflicting Session folders relative to that project:

| Record | Folder | Live BodyMass (kg) | Live Height (m, unchanged units) |
| --- | --- | --- | --- |
| Canonical | `Data\Claudia_123-20260928T142041Z-1-001\Claudia_123\2026-10-01_2` | 71 | 0.6000000238418579 |
| Imported | `Data\2026-10-01_2-20261004T101228Z-1-001\2026-10-01_2` | 71 | 0.20999999344348907 |

Both expose Name `Claudia`, patient number `123`, DOB `2006-09-14`, Sex `Female`,
and Session ID `2`. Their anthropometric values differ (currently Height); historical
71-versus-100 mass examples are not the current live values. The Subject-looking ancestor
folders have class `Raw folder`, not `Subject`, so this live case has no genuine Subject
field owner. A patient's editable `Fields.ID` is different from the container's immutable `ID`.
Likewise, the editable Session ID label is not an internal session GUID.

Both `session.xml` files have root attributes `Type="Session"` and
`Filename="2026-10-01_2"`, with root patient/anthropometric Fields and `Session_ID=2`.
Neither root supplies an internal container GUID. Local XML and the GUI measurement/path
are evidence of the intended session, not alternative PAF write addresses. Measurement-level
export snapshots do not override root patient/session Fields.

A second application defect was that Save submitted all 15 form values, then compared them
against live QTM values. A field untouched by the user could consequently overwrite a value
changed externally after Fetch. Save now submits only values changed from the GUI baseline.
Old technical errors also expanded the form with multiple paths. They are now in Details.

### Confirmed QTM API behavior and supported resolution

Read the installed `C:\Program Files\Qualisys\Qualisys Track Manager\REST\RESTful_QTM_API.pdf`,
revision 1.4 (2018-11-07), including the PUT example on page 11 and immutable-container table
on pages 14–15. Rendered page 11 and inspected its real example visually. This installed
reference documents modifying Fields through `PUT /api/v1/paf/instance/<internal-container-GUID>`
with a JSON body of parameter entries. The client percent-encodes that GUID in the URL.
`typeInfo=true` reports capabilities; `depth` expands reads. Root PUT supplies no documented
path-based session selector. Container ID, ParentIDs and ChildIDs are immutable metadata;
patient `Fields.ID` may be edited without changing the container GUID.

Read-only live queries confirmed `/api/v1` lists `paf`, `project`, `version`, and
`/api/v1/paf` lists `instance`. Traversing the project tree exposes both Session copies;
GET of their common GUID exposes the canonical Session. The installed reference and
available API provide no verified path, GUI selection, or parent/child composite write
identity that distinguishes these copies. No guessed PUT, deletion, import, container
creation, measurement save/close, or GUID edit was attempted.

Official reference cross-checks:

- [QTM scripting modules](https://qualisys.github.io/qtm-scripting/latest/modules.html): no supported session-field writer that supplies another PAF identity.
- [qtm.file](https://qualisys.github.io/qtm-scripting/latest/qtm.file.html): `get_path` supplies the open measurement. It does not expose project-tree session selection.
- [qtm.gui.selection](https://qualisys.github.io/qtm-scripting/latest/qtm.gui.selection.html): trajectory/bone selection is not a patient/session write selector.
- [PAF Project view](https://docs.qualisys.com/qtm/content/applications/paf_project_view.htm): QTM provides supported project/session management and properties editing. This page does not document an automatic duplicate-GUID repair recipe.

The actual duplicate-GUID data identity issue remains unresolved. Repair/reconcile the copied
sessions through QTM's supported project/session management with Qualisys support as necessary,
then Fetch and review the intended session. Renaming a folder, changing patient number or
Session ID, selecting a GUI row, or bypassing the collision check is not a supported GUID repair.
No automatic repair is implemented or claimed. Successful live writes remain blocked.

### Session resolution and safety behavior

- GUI context is the absolute resolved, Windows-normalized session directory; its XML and
  selected measurement are captured as diagnostic evidence when the user starts the operation.
- Fetch uses the directory of QTM's open measurement when available; otherwise it uses the
  selected GUI directory. Save never redirects the form to another open session.
- Read checks the current project before/after traversal. It matches the complete normalized
  Session path, requires exactly one matching tree record, and retains every embedded edge.
  Previously a visited-key deduplication could hide two records sharing GUID/path/parent.
  Same-path records now remain ambiguous even if their GUIDs are identical.
- Branches requiring expansion by GUID must return the same GUID, class, and normalized path.
  Otherwise no source is selected and the GUI values are retained. Discovery remains bounded
  at 256 edges / four seconds, with one-second HTTP timeouts.
- A unique embedded Session can be read even when GUID writes are blocked or its direct
  endpoint cannot be verified. The GUID-addressed record replaces the embedded source only
  when it is uniquely proven to be the same Session. Reads never substitute the other copy.
- Genuine Subject ancestry supplies fallback fields. If only GUID-returned Parent data is
  available, Subject fields require a unique catalogued owner and matching direct GUID endpoint
  (class/path/GUID). A duplicated Subject GUID blocks writes. Embedded ancestry can still
  prove a read source; ambiguous fallback Subject values are not silently used.
- Writes require one Session occurrence for the internal GUID, a matching direct endpoint,
  and uniquely addressable genuine Subject ownership where applicable. Every actual owner
  and corresponding GUID PUT URL is exposed in Details.
- The project/path/Session/Subject token must still match the reviewed GUI context. Switching
  project or target requires Fetch/review; repeatedly clicking Save does not acknowledge it.
- Capabilities are checked per changed field. Immediately after capability lookup, before each
  owner PUT, the client re-resolves target/owners/project, checks open measurement context and
  cancellation. Collision or context change during typeInfo therefore blocks the PUT.
- Read-back re-resolves the intended session and verifies each submitted value with Float32
  equality for numeric fields and preserved text/date values for patient metadata. Fields are
  confirmed separately; failed/ignored/read-only writes retain drafts. There is no rollback to
  another patient and no automatic replay. Late worker results from another GUI generation are
  discarded. An interrupted operation is not reported as successful.

### Save Parameters and Fetch QTM changes

Save compares all supported controls to their load/Fetch/confirmed baseline, sends only actual
changes, validates only those edits, and leaves externally changed untouched QTM fields alone.
The four patient fields remain Name, ID, DOB, Sex; the eleven anthropometric fields retain their
existing kg/m units and exact left/right mappings. Supported QTM values outside current input
bounds can still be fetched without guessed conversion; new out-of-bounds edits are rejected.

No-change Save makes no HTTP request, shows `No parameter changes to save.`, and does not invent
new confirmation. Local-only calibration drafts remain local and dirty. Draft baselines now
survive session switches and local reloads so restored edits still submit when saved.
Save confirmation updates only submitted controls. Untouched externally changed values appear
on the next explicit Fetch rather than being overwritten or silently replaced during Save.

Fetch remains independent and read-only: it performs GETs plus the scripting `get_path` query,
never parameter PUTs. Confirmation is required before replacing unsaved shared/programmatic or
local calibration edits. Cancel performs no request. Ambiguous reads warn and keep the GUI
values; uniquely matched copies fetch successfully even when their shared GUID prevents writes.
Edits typed during an operation remain drafts for the next explicit user action.

Save & Run Static Analysis and its local configuration/processing behavior were not modified.
No background polling, editing-finished writes, implicit parameter PUT, or graph changes were added.

### Compact feedback and Details

The form now shows concise results such as:

- `Parameters not saved — QTM session identity is ambiguous.`
- `Parameters fetched. Saving requires a unique QTM session.`
- `Parameters confirmed in QTM.`
- `Some parameters could not be saved.`

The Details button opens a read-only, scrollable/copyable dialog containing the error type,
attempted operation, requested GUI identity/XML metadata, active measurement, current project,
Session/Subject identifiers and normalized paths, conflicting records, GUID write targets and
parameter owners, submitted/failed/confirmed or fetched fields, warnings and recommended resolution.
Only compact text appears in both form status labels/tooltips; full conflicting paths are not
printed inline. New edits or session selection clear stale operation details.

### Every modified file and functions changed

Exactly these five project files were modified relative to the follow-up 6 baseline:

1. `app/services/anthropometric_sync_service.py`: added `GUID_RESOLUTION`, `session_identity`,
   `QtmSessionResolutionError.__init__`; changed `QtmAnthropometricClient.read` (including nested
   `discover`), `QtmAnthropometricClient.synchronize`, `_SyncOperation.run`.
2. `app/ui/pages/static_analysis_page.py`: changed `_create_config_view`, `_auto_fetch_static_data`,
   `_init_anthropometric_sync`, `_prepare_anthro_context`, `_anthro_status`, `_start_manual_sync`,
   `_on_anthro_sync_finished`, `_on_save_clicked`; added `_sync_feedback`, `_sync_details_text`,
   `_show_sync_details`, `_gui_session_identity`. Added standard-library JSON and Qt dialog imports.
3. `tests/test_anthropometric_sync.py`: realistic Subject paths in owner fixtures, assertions moved
   to structured Details where appropriate, separate Save/Fetch failure wording, disposable server
   connection-abort handling. Existing field/transport/local-processing tests retained.
4. `tests/test_patient_metadata_sync.py`: compact-message/Details assertions; added tests for same-path
   ambiguity with same/different GUIDs, external untouched changes, no-op Save, restored drafts,
   real Details dialog, unavailable GUID endpoint with independent tree read, incorrect branch
   expansion, duplicate Subject ownership with/without embedded ancestry, a different direct GUID returning the same path, and target changes
   during typeInfo (duplicate session, measurement switch, project switch).
5. `spec/session1.md`: appended this section; previous content preserved byte-for-byte.

No dependency was installed. Existing dirty/untracked files from earlier sessions were preserved.
External baseline copies, documentation extracts, command logs, screenshots and harnesses are under
`C:\Users\ADMIN\Desktop\C\codex\shriners-followup6-baseline`, outside the project.

### Tools, commands, executed tests, and actual results

Tools: PowerShell, rg, Git status/diff, Python pathlib/hashlib/difflib/json/XML parsing,
urllib read-only live QTM requests, real PySide6/QTest controls and dialogs, pytest,
pypdf, installed Poppler pdftoppm, image viewing; Agent Reach/Jina curl plus official
Qualisys documentation. Ponytail, Graphify, PDF and Agent Reach skill instructions were read.
No graphify graph existed and no unrelated graph pipeline or native computer automation was run.

The Python runtime for app/test/harness checks was
`C:\Users\ADMIN\anaconda3\envs\python-example\python.exe` with `QT_QPA_PLATFORM=offscreen`
and its `Library\bin` prepended to PATH. The bundled Python runtime read the installed PDF;
`pdftoppm.exe -f 11 -l 11 -png -singlefile` rendered the documented PUT example.
Relevant executed commands (external scripts/logs contain exact request bodies and results):

```powershell
rg --files -g AGENTS.md
rg -n 'Subject|_config_status.text|_metadata_status.text|Verified|Failed' tests/test_anthropometric_sync.py tests/test_patient_metadata_sync.py
git status --short
git diff --check -- app/ui/pages/static_analysis_page.py
python -m py_compile app/services/anthropometric_sync_service.py app/ui/pages/static_analysis_page.py tests/test_anthropometric_sync.py tests/test_patient_metadata_sync.py
python -X utf8 -m pytest tests/test_anthropometric_sync.py tests/test_patient_metadata_sync.py -q
python -X utf8 -m pytest tests/test_anthropometric_sync.py tests/test_patient_metadata_sync.py tests/test_mac_scale_persistence.py tests/test_session1_regressions.py tests/test_dynamic_plot_scaling.py tests/test_bilateral_mean_separation.py tests/test_10_trials_support.py -q
```

Also executed external `capture.py`, `inspect-qtm.py`, `edit-ui.py`, `edit-tests.py`,
`prepare-live.py`/`fix-live.py`, `live-manual-sync.py` (rerun after final diagnostics changes), `audit.py`, `prepare-notes.py`, and `append-notes.py`.
The read-only live paths were `/api/v1`, `/api/v1/paf`, `/api/v1/project`, `/api/v1/version`,
`/api/v1/paf/instance?depth=3`, GUID instance GETs with depth/typeInfo, and scripting
`qtm/file/get_path` / `qtm/file/is_dirty` with empty argument arrays. No native QTM dialogs
were opened, and the existing unsaved measurement was not saved or closed.

Initial focused run: **97 passed, 3 failed in 72.78s**. All three were obsolete presentation
assertions (Save wording used for Fetch and raw Windows paths searched in JSON-escaped Details).
Updated assertions inspected the proper operation and structured conflicting records.
Expanded workflow run: **110 passed in 81.72s**. One external live-harness preparation attempt
had a syntax error caused by a repeated text replacement; it failed before making any QTM request,
was fixed, and the actual live harness passed. Final regression result: **178 passed, 14 existing Matplotlib/pyparsing deprecation warnings in 100.21s**.
After adding normalized paths, parent GUIDs and actual parameter-owner URLs to Details, only those final diagnostics/guard cases were rerun. Final targeted diagnostics/guard result: **10 passed, 104 deselected in 6.30s**; includes an additional same-path/different-direct-GUID safety case and assertions for actual Subject/Session parameter owner write targets on the final code.

| Requested validation | Actual result |
| --- | --- |
| Save unique session | Disposable real HTTP endpoint receives only edited supported fields; read-back confirmed; unrelated patient unchanged. |
| Save duplicate Session GUID | Both canonical and copied folders blocked, zero PUT; edited values retained. |
| Fetch unique source | All 15 patient/anthropometric controls populated, exact units/bilateral mappings preserved, zero PUT. |
| Fetch ambiguous source | Same-path records with same/different GUIDs and ambiguous Subject/branch sources warn, retain GUI, zero PUT. |
| Save no changes | Repeated no-op Save produces no HTTP call or fabricated success; local drafts remain dirty. |
| Disconnected QTM | Timeout/HTTP failure leaves drafts and Qt responsiveness; manual retry recovers. |
| Repeated Save/Fetch | Explicit retries only; no background traffic; one verified Save followed by no-op Save makes no extra PUT. |
| Session switching | Full-path context, token/generation guards, draft baselines and Fetch confirmation prevent wrong-session writes. |
| Partial failures | Read-only/ignored fields and separate Subject/session HTTP failures identify confirmed/failed fields independently and retain failed drafts. |
| Successful read-back | Numeric Float32 and four patient metadata values verified against the intended unique session in the disposable endpoint. |
| Target change during typeInfo | Duplicate session, open measurement switch and project switch each produce zero PUT. |
| Real Details action | QTest opens the actual dialog; identity, GUID targets, XML, failures and resolution are readable; form has no inline conflicting paths. |

Live real-QTM/real-Qt harness: **passed**. Selected canonical source fetched all 15 fields despite
write ambiguity; Save displayed the exact compact collision message with both records in Details;
zero live PUTs. Dirty Fetch cancel retained the draft without HTTP; accepted Fetch restored QTM
values with no write. The complete live tree (all copies' fields), direct GUID record, open
measurement and unsaved state matched before/after. The real themed footer and Details screenshots
were visually inspected; at 1280×900 the horizontal scrollbar maximum was zero.

Scoped Git whitespace and Python compilation checks passed. Final hash/file audit: **only the five listed project files changed; all other 699 baseline files stayed identical**. Previous documentation prefix preserved.
The broader graph/frame/event-related modules were run only as regressions and their sources were
not edited. Logs: `focused-tests.txt`, `final-tests.txt`, `targeted-tests.txt`, `live-manual-sync.json`;
evidence: `live-identity-before.json`, `live-tree.json`, `rest-api.txt`, `rest-put-page11.png`,
`manual-action-row.png`, `sync-details-dialog.png`, and per-file follow-up diffs.

### Remaining limitations

The real project's duplicated GUID is still an unresolved QTM data identity issue. No successful
live write is claimed: safe unique-session writes and persistence were verified against the
controlled disposable QTM API fixture, while actual QTM writes remained blocked. No undocumented
GUID repair or alternative write address was assumed. GUI project-tree selection cannot be queried
through the documented scripting selection API; Fetch follows the open measurement or explicit GUI
folder. Session discovery has conservative bounds and rejects unverifiable branch expansion.

The REST API provides no documented atomic compare-and-set or transactional multi-owner write.
Guards run immediately before each PUT and verify read-back, but cannot atomically exclude an
external QTM change in the gap between validation and PUT; partial writes across owners are
reported rather than automatically rolled back. File.is_dirty stayed true, so a disk flush across
QTM restart was not tested or forced. Native QTM Properties-dialog interaction and interactive
production static processing were not executed in this follow-up. Existing out-of-range QTM
values are displayed with warnings; their units are never guessed or repaired automatically.


## Session 1 Follow-up 7 — GUI-to-QTM Parameter Write Resolution

Date: 2026-10-09. Investigated only GUI-to-QTM Save Parameters. Fetch QTM and the entire GUI
source are byte-for-byte unchanged from the follow-up 7 baseline. No graph, frame, event,
trajectory, theme, directory-structure, clinical calculation, unit or settings changes.
No offline metadata substitute, automatic GUID repair, staging, commit or GitHub push.

### Confirmed failure point and before/after flow

The requested gRPC stage is not part of this button's actual pipeline. Save connects to
QTM's PAF REST field API through `QtmAnthropometricClient`; there is no gRPC request from
this handler. `QTM-GRPC/qtm_data_transfer.proto` defines a generic command bridge used by
other features, not an independently addressable patient/session metadata writer.
`app/services/qtm_metadata_service.py` extracts trial metadata; it is not this Save writer.
These files were inspected and left unchanged.

Actual flow:

1. `StaticAnalysisPage._on_save_clicked` collects supported values changed from the GUI baseline.
2. Numeric, finite-value, bounds/unit, patient/date and enum validation run on those edits.
3. `_start_manual_sync` captures GUI context/revisions and starts the existing worker.
4. `_SyncOperation.run` checks the open QTM measurement against the intended GUI session.
5. `QtmAnthropometricClient.synchronize` calls `read` to resolve the project, Session, owners,
   normalized paths and GUID endpoint.
6. **The present failure is the `if not snapshot["writable"]` branch in synchronize.**
   It returns the collision snapshot before field capability lookup, PUT or write verification.
7. The existing GUI completion handler displays `Parameters not saved — QTM session identity is ambiguous.`

Before this follow-up, the block was already safe but its Details did not identify the exact
pipeline stage. After this follow-up, blocked Save adds `failure_stage=session_identity_resolution`,
`write_attempted=false`, `verification_status=not_started` to the existing Details data. Fetch's
read snapshot and implementation are unchanged. No success message was added to bypass the block.

For a unique target, the existing write flow is already functional: inspect field capabilities,
revalidate owners/project/measurement immediately before PUT, submit only changed supported
fields to the appropriate owner GUID, re-read the intended session and verify each submitted
value. Only confirmed fields are acknowledged; failed or unverified drafts remain in the GUI.
The new tests explicitly check server state and Fetch after Save, not merely a status label.

### Current live identities and confirmed root cause

Inspected QTM 2026.2 build 17495, PAF Python Example 1.1.3. The open project is
`Shriners_Gait_Model_PAF_v1.0`, rooted at:
`C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\`.
There are exactly two Session records; both have internal container GUID
`{17698CAD-BDA1-11F1-891E-2C58B910BA1C}`.

Absolute canonical Session path:
`C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\Data\Claudia_123-20260928T142041Z-1-001\Claudia_123\2026-10-01_2\`.

Absolute imported Session path:
`C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\Data\2026-10-01_2-20261004T101228Z-1-001\2026-10-01_2\`.

Both are in that same project and report Name `Claudia`, patient number `123`, DOB
`2006-09-14`, Sex `Female`, Session ID `2`. Their ancestor folders are `Raw folder`,
not genuine Subject containers. These editable patient/session labels do not replace the
immutable internal container GUID. Root session.xml metadata supplies no internal GUID.

Only the canonical copy has a currently open measurement:
`C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\Data\Claudia_123-20260928T142041Z-1-001\Claudia_123\2026-10-01_2\Static 3.qtm`.
Its dirty state is true. The imported folder also contains Static 3.qtm, but it is not the open
measurement. No file was opened, closed or saved to change that context during this task.
Both tree records report 20 Dynamic measurements and one Static measurement.

Current live anthropometric values (unchanged model units, no conversion):

| Parameter | Unit | Canonical | Imported |
| --- | --- | --- | --- |
| BodyMass | kg | 88 | 71 |
| Height | m | 0.6000000238418579 | 0.20999999344348907 |
| InterAsisDistance | m | 7.5 | 7.5 |
| LeftLegLength | m | 1.2000000476837158 | 1.2000000476837158 |
| RightLegLength | m | 0.20000000298023224 | 0.20000000298023224 |
| LeftKneeWidth | m | 0.20000000298023224 | 0.20000000298023224 |
| RightKneeWidth | m | 2.0999999046325684 | 2.0999999046325684 |
| LeftAnkleWidth | m | 0.5 | 0.5 |
| RightAnkleWidth | m | 6.5 | 6.5 |
| LeftAsisTrocanterDistance | m | 0.6000000238418579 | 0.6000000238418579 |
| RightAsisTrocanterDistance | m | 8.100000381469727 | 8.100000381469727 |

The canonical mass was already 88 at this follow-up's first read, before any changes by Codex.
It was not changed by this task. Follow-up 6's values are historical and preserved in its notes.
Existing out-of-range values were not converted, repaired or used to choose a write destination.

The identical GUID's 16-byte little-endian representation was found at byte offset 16536 in
each 24576-byte `data.qpr`. Their hashes differ because their metadata differ; the identity bytes
are duplicated. Read-only checks confirm this is persistent QTM container identity data, not
only a GUI naming or cache problem. No binary bytes were edited. The exact historical copying
operation was not observed, so it is not claimed as independently established.

### QTM identity and APIs

Fetch matches a unique embedded tree record by complete normalized session path. This supplies
separate read sources even with a duplicated GUID. The GUID-addressed GET for either copy returns
the canonical path. Thus a GUID PUT while intending the imported copy would address a different
session; selecting by patient name, mass or folder cannot safely fix the endpoint.

The installed `REST\RESTful_QTM_API.pdf`, revision 1.4, documents the specific-container PUT
on page 11 and immutable internal ID/ParentIDs/ChildIDs in the container-format section. Writes
accept an internal owner GUID at `/api/v1/paf/instance/<GUID>`, percent-encoded in the URL, with
a JSON body of field/value entries. There is no documented project/session/measurement path
selector for this PUT. The current project already scopes the tree; both copies are in that scope.
The generic gRPC command bridge does not supply another verified PAF session write identity.
No guessed path-based PUT or undocumented gRPC metadata command was attempted.

Read-only live endpoints used: `/api/v1`, `/api/v1/paf`, `/api/v1/project`, `/api/v1/version`,
root PAF instance GET with `depth=3`, GUID instance GET with `depth=-1`, and scripting
`qtm/file/get_path` / `qtm/file/is_dirty` with empty argument arrays. The Save code's actual
writer remains `PUT /api/v1/paf/instance/<owner-guid>`; `typeInfo=true` supplies capabilities.
The collision prevented any live PUT and any live Save capability lookup/write read-back.

Qualisys's current [PAF development documentation](https://github.com/qualisys/paf-documentation#yaml)
confirms non-measurement item data are stored in data.qpr; measurement metadata are inside .qtm;
session.xml is an exported snapshot. Editing session.xml is therefore not an active metadata
write. No supported offline QPR update API was established, so none was implemented or represented
as a live Save. The local calibration Save & Run behavior was not touched.

### Supported rebuilding procedure and repair limits

No documented in-place duplicate-GUID repair command was found in the installed API/help or
current official PAF/scripting documentation. A confirmed in-place repair preserving the existing
folders must come from Qualisys support; this task does not invent a menu command or binary edit.
The required repair outcome is a separately addressable QTM container identity for each intended
session/field owner, with tree and direct GUID GET agreeing before Save is allowed.

The following reconstruction uses documented QTM operations. It is a manual recovery route,
not an in-place repair or an end-to-end live-tested migration. It was not executed in the clinical
project because it would create new patient/session data and the open measurement is unsaved:

1. Preserve both original sessions and pending unsaved measurement work. Have the operator decide
   which clinical recordings/metadata belong to the intended session; this cannot be inferred from
   matching names or the differing BodyMass/Height values.
2. Open **View → Project view**. Use **Add → Participant** for a fresh genuine Subject if needed
   (both existing Subject-looking parents are Raw folder). Under that Participant, use
   **Add → Session** to create a fresh Session using this project's configured types.
   These type names come from the inspected Settings.paf; QTM creates fresh containers.
   Do not duplicate the old session folder or its data.qpr into the new one.
3. Import the chosen recordings individually using PAF **Import file** on Static/Dynamic file
   slots, where offered. The installed REST reference also documents the supported equivalent:
   `POST /api/v1/paf/instance/<new-unique-session-guid>/import_file`, body
   `{"FileName": "<chosen-recording.qtm>", "Type": "Static"}` (or `Dynamic`). This is a
   reconstruction command, not a Save bypass. Nothing here was POSTed by this task.
4. Review patient and anthropometric metadata in QTM's **Details** for the genuine Participant
   and Session. Enter only operator-confirmed values in the established units. Do not copy old
   container identity data. Resolve invalid legacy values with the clinician/Qualisys rather
   than guessing conversions. Imported measurement metadata do not establish Session identity.
5. Check the new Subject and Session GUIDs are each unique in the project tree and direct GUID
   GETs resolve their exact normalized paths. A new distinct folder alone is insufficient.
   If an imported recording reintroduces ambiguity, stop and obtain Qualisys assistance.
6. Before selecting the rebuilt session in Shriners, obtain its normal PAF session export.
   In this Settings.paf, **Shriner Static** declares `Export session: Yes`, which generates
   session.xml as part of that normal QTM operation. This can also start processing; it was
   not run automatically. Qualisys can advise a supported export/recovery workflow if processing
   or retaining the original folder layout makes reconstruction inappropriate.
7. Open the intended rebuilt measurement in QTM, select its exported session in Shriners and
   Fetch/review. Perform a single valid Save, inspect QTM, Fetch again and verify the intended
   value and all other sessions. Do not declare the repair complete until this succeeds.

Sources: [PAF Project view / Add and Details](https://docs.qualisys.com/qtm/content/applications/paf_project_view.htm),
[official PAF recording import instructions](https://docs.qualisys.com/baseball/Content/PAF%20Baseball/Capture%20Step%2007%20-%20Collect%20data%20Baseball.htm),
the installed REST creation/import contract (new-container POST returns a unique identifier),
and [PAF Export session](https://github.com/qualisys/paf-documentation#external-program).
Creation/import are supported building blocks; resolution of these existing clinical copies by
this reconstruction has not been verified. Renaming, changing patient number/Session ID or direct
binary GUID editing is not an established repair. No originals were removed or modified to force Save.

### Exact modified files, functions and safety checks

- `app/services/anthropometric_sync_service.py`: only
  `QtmAnthropometricClient.synchronize`, two added lines identifying the collision failure stage,
  false write-attempt flag and unstarted verification in the existing Details. No guards removed;
  `read`, `_request`, active-session resolution and worker/Fetch dispatch are unchanged.
- `tests/test_anthropometric_sync.py`: added
  `test_body_mass_71_to_72_save_fetch_persists_only_in_intended_session`,
  `test_duplicate_guid_save_stops_at_resolution_before_write_capabilities` (canonical/imported),
  `test_write_with_failed_readback_retains_draft_and_never_claims_success`.
- `spec/session1.md`: appended this section. Previous content preserved byte-for-byte.

Existing safety checks retained: input validation, only-edited supported fields, GUID collision and
owner/path/project checks, pre-PUT revalidation after typeInfo, cancellation/generation guards,
Float32-aware read-back, per-field failure handling and draft retention. Added diagnostic evidence
is Save-only; it cannot weaken targeting or produce a new write. The external live harness refuses
any unexpected PUT before sending it to QTM.

### Tools, commands, executed tests and actual results

Tools: PowerShell, rg, Git status/diff, apply_patch; Python pathlib/json/urllib/XML/hashlib/uuid/AST/
difflib and py_compile; real PySide6/QTest widgets; pytest; installed REST/help references;
Agent Reach web/GitHub routing through curl/Jina and gh API; official Qualisys web search/read.
No dependency installation, native computer automation, graph generation or GitHub write occurred.
App tests used `C:\Users\ADMIN\anaconda3\envs\python-example\python.exe`,
`QT_QPA_PLATFORM=offscreen`, and that environment's Library\bin prepended to PATH.

Relevant commands and external scripts:

```powershell
rg --files -g AGENTS.md -g '*qtm*' -g '*sync*'
rg -n 'Save Parameters|_on_save_clicked|_start_manual_sync|qtm_metadata|Metadata' app/services app/ui/pages/static_analysis_page.py
rg -n -i '\bguid\b|unique.*ident|import file|data.qpr' 'C:\Program Files\Qualisys\Qualisys Track Manager\Help\content' -g '*.htm'
gh api repos/qualisys/paf-documentation/contents/README.md -H 'Accept: application/vnd.github.raw+json'
curl.exe -s --max-time 35 'https://r.jina.ai/https://docs.qualisys.com/qtm/content/applications/paf_project_view.htm'
python -X utf8 -m pytest tests/test_anthropometric_sync.py tests/test_patient_metadata_sync.py -q
python -X utf8 -m pytest tests/test_anthropometric_sync.py -q -k 'body_mass_71_to_72 or duplicate_guid_save_stops or write_with_failed_readback'
python -m py_compile app/services/anthropometric_sync_service.py tests/test_anthropometric_sync.py
git status --short
git diff --check -- app/services/anthropometric_sync_service.py tests/test_anthropometric_sync.py spec/session1.md
```

Executed external capture.py, inspect-qtm.py, summary-identity.py, inspect-qpr.py,
prepare-live.py, live-manual-sync.py, audit.py and append-notes.py. Evidence/logs are outside
the project in `C:\Users\ADMIN\Desktop\C\codex\shriners-followup7-baseline`.
One read-only QPR probe initially failed on misspelled encoding `utf16le`; corrected to
`utf-16-le` and the probe succeeded. An expected nonexistent Scripting folder search and an
unavailable guessed documentation URL were replaced by the installed Help and actual official
PAF documentation. No failures were concealed as successful API operations.

Workflow regression: **117 passed in 85.47s** (both metadata test modules, including the first
three new cases). Added final failed-read-back test and reran the four focused persistence/failure
cases: **4 passed, 60 deselected in 2.72s**. Python compilation passed. Test results:

| Requested scenario | Verified result |
| --- | --- |
| Unique session, 71 → 72 → Save → Fetch | Controlled real HTTP API stores 72 at intended session-a; Fetch returns 72. Another session with identical name/mass stays unchanged. One-field PUT only. |
| Persistent-file substitution prohibited | session.xml and opaque data.qpr bytes stay unchanged during GUI Save in the controlled test. |
| Duplicate GUIDs | Canonical and imported reads retain their individual values; Save stops before typeInfo/PUT; both server records and XML bytes unchanged. |
| Similar patient names | Identically named distinct sessions are targeted by context/unique internal identity, never name/value. |
| Invalid numeric input | Existing NaN/infinite, nonnumeric, bounds and precision tests pass; invalid edits retained without writes. |
| Disconnected QTM | Existing timeout/HTTP failure tests pass; edits retained and Qt responsive. |
| Unchanged/repeated Save | No additional writes, no fabricated new confirmation, local drafts retained. |
| Failed read-back | Ignored PUT tests pass. New test makes PUT persist 72 then fails the verification GET: no success, dirty draft retained, other session unchanged; explicit Fetch recovers 72 with no extra PUT. |
| Read-only/partial failure | Existing per-field/per-owner tests pass and retain failed drafts. |
| Fetch preservation | Existing Fetch tests pass; all GUI source and client read/dispatch functions unchanged. |

Actual QTM/real Qt harness: **passed**. Fetch retrieved all 15 live fields; editing mass to 72
then pressing Save stopped at session_identity_resolution with write_attempted=false and
verification_status=not_started. Zero live PUTs. The complete live tree, direct GUID field values,
both copies, open measurement path and dirty state matched before/after. Accepted Fetch restored
the current canonical mass of 88, with no write. The existing Details dialog opened successfully.

### Live verification status, restrictions and final diff

A successful **live** 71 → 72 Save is **not verified and remains blocked**. The open project has
no uniquely identifiable session: its only two Sessions share a GUID. Tests against the controlled
endpoint validate implementation behavior but are not represented as live QTM persistence.
No clinical test session was created, no project was switched while its measurement was unsaved,
and no copied GUID was changed. Native QTM property editing/reconstruction and durable persistence
across a QTM restart were not tested. The REST API still offers no documented atomic multi-owner
transaction/compare-and-set; the previously documented concurrency limits remain.

Follow-up 7 diff relative to the captured baseline (separate from the pre-existing dirty tree):

| File | Added lines | Removed lines |
| --- | ---: | ---: |
| `app/services/anthropometric_sync_service.py` | 2 | 0 |
| `tests/test_anthropometric_sync.py` | 91 | 0 |
| `spec/session1.md` | 268 | 0 |

Only these three files changed. The GUI/Fetch, all protected source/settings/data files and all
other baseline files match their original hashes. Captured 705 baseline files; 702 were unchanged, with no project files added, removed or moved. Previous session1.md content
was preserved. The service/tests/spec were already untracked in this repository; ordinary Git diff
alone does not display their earlier history, so baseline-relative diffs and hashes are also saved
as evidence. Nothing was staged, committed, pushed, or automatically repaired.

The live Save failure is an unresolved QTM data identity prerequisite, not a missing GUI/gRPC
metadata write. The existing unique-target writer is verified by transport/control tests; the
collision remains blocked until a supported QTM recovery yields and verifies unique identities.


## Session 1 Follow-up 8 — Native QTM gRPC and Metadata Write Investigation

### Scope and outcome

Investigated only whether the working Dynamic Analysis gRPC bridge can safely support GUI-to-QTM
Save Parameters despite duplicate PAF session GUIDs. No supported native patient/session metadata
writer was found in the running QTM API or either embedded bridge implementation. No production
change was made: adding a transport fallback would not create a distinct PAF write identity.
Save remains blocked for the duplicated sessions. Fetch QTM, Dynamic Analysis, frame/event/trajectory
behavior, graphs, units, theme and directory structure are unchanged. No GUID repair or file-write
substitute was attempted. This is an unresolved QTM data identity issue, not a verified fix.

### Working Dynamic Analysis communication and target verification

Inspected these files and functions (none modified):

| File | Relevant functions / behavior |
| --- | --- |
| `app/ui/pages/dynamic_analysis_page.py` | `_on_push_trial_events_to_qtm`, `_process_next_in_queue`: event send and processing dispatch. |
| `app/services/processing_service.py` | `ProcessingWorker.run`, `GaitProcessingService.process_dynamic`, `_run_script`: QThread/subprocess launches `Py3_DynamicMain.py` with GUI session XML, trial and condition. |
| `app/services/event_service.py` | `get_qtm_active_file`, `send_events_to_qtm`, `fetch_events_from_qtm`: title check, protobuf requests, event transport. |
| `Gait-lab-Vicon-to-QTM/Py3_DynamicMain.py` | Imports gapi and calls `SetTrajectory` for calculated measurement trajectories. |
| `Gait-lab-Vicon-to-QTM/gapi.py` | `grpc_send_command`, `SetEvent`, `SetEvents`, `SetTrajectory`, `GetProjDirectory`: socket check then `SendCommandToQtm` on localhost:50052. |
| `Gait-lab-Vicon-to-QTM/QTM_GRPC/tools/Py3_staticmain.py` | `QtmCommandServicer.SendCommandToQtm`, `get_current_open_trial_name`, `getEvents`, `GetProjDirectory`, `setTrajectory`: native measurement API dispatch. |
| `QTM-GRPC/tools/Py3_staticmain.py` | Same command inventory in the configured bridge directory; checked separately from the requested legacy copy. |
| `QTM-GRPC/qtm_data_transfer.proto` | Generic `CommandToQtm(command_name, command_args_json)` / `Ack(success, message)` transport, not an arbitrary native scripting executor. |
| `app/services/settings_service.py`, `MAC_CasePresentation/FilePathSettings.py` | Configured `QtmGrpcLocation` resolves the project-relative primary `QTM-GRPC` directory. Loading settings for this investigation did not synchronize/rewrite gapi. |

Event push flow: GUI sidecar events -> `send_events_to_qtm` -> optional `ClearEvents`, then
`SetEvents` -> embedded `SendCommandToQtm` -> `qtm.data.object.event.add_event({label,time})`.
gapi supplies the same generic request for individual/bulk events and trajectories. The server
uses QTM's currently open measurement; no patient/Session GUID is passed to the event API.
The GUI explains that event persistence requires the operator to save the measurement in QTM.

The event target guard is a trial basename derived from visible QTM window titles. Both sides
allow basename equality or substring matching, and a missing active title does not establish a
verified full-path identity. This guard cannot distinguish copies of `Static 3.qtm` in different
patient/session folders. `GetActiveMeasurement` returns that title/name, not a PAF instance ID or
normalized full path. `GetProjDirectory` returns only the project directory. This limitation was
recorded, not changed; Dynamic Analysis was not refactored to support Static Analysis.

### Exact APIs and installed capability evidence

Queried the running QTM's documented read-only introspection API:
`qtm.utilities.documentation.get_package_documentation()` via
`POST /api/scripting/qtm/utilities/documentation/get_package_documentation/` with JSON empty string.
Saved its complete return outside the project as `installed-native-api.json`.
The installed version is QTM **2026.2, build 17495**, PAF **Python Example 1.1.3**.
The complete runtime catalog contains **45 modules / 776 methods**. Inspection of module paths,
method names, descriptions, parameters and return types found no patient, anthropometric, PAF,
BodyMass, session, subject or metadata API. No native metadata setter was guessed or invoked.

Relevant supported APIs:

| API | Actual scope / identifier |
| --- | --- |
| `qtm.data.object.event.add_event(event)` | Open measurement event; label/time/optional color; no session/subject identity argument. |
| `qtm.data.object.event.get_events()` / `clear_events()` | Measurement event access. Clear was inspected only; never called live here. |
| `qtm.data.object.trajectory.*`, `qtm.data.series._3d.set_samples(...)` | Measurement trajectories and samples, not PAF patient/session fields. |
| `qtm.file.get_path()` | Full path of an open measurement; read context only. |
| `qtm.file.is_dirty()` | Measurement unsaved state; requires an open measurement. |
| `qtm.settings.directory.get_project_directory()` | Project directory only. |
| `qtm.utilities.documentation.get_package_documentation()` | Complete installed scripting method definitions; read-only introspection. |
| `PUT /api/v1/paf/instance/<internal-owner-GUID>` | Actual supported patient/anthropometric field writer used by Save; JSON body consists of changed field entries. |
| `GET /api/v1/paf/instance?depth=3` | Embedded project tree preserves both conflicting session records for contextual reads. |
| `GET /api/v1/paf/instance/<GUID>?depth=-1` / `?typeInfo=true` | Direct GUID record / supported writable-field capabilities. |

Both bridge sources register exactly: PrintMessage, GetActiveMeasurement, GetFrameCount,
SetTrajectory, GetForcePlate, CreateModelMarker, GetEvents, ClearEvents, SetEvent, SetEvents,
GetMeasurementRange, GetProjDirectory, ResetTimeline and SetMeasuredRange. Neither exposes
patient/anthropometric getters or setters. Unknown command names are rejected with success=false.
The presence of a generic JSON RPC message does not imply an unavailable QTM API exists.
Wrapping the GUID-based REST PUT in gRPC would preserve the same ambiguity.

Sources: [official scripting modules](https://qualisys.github.io/qtm-scripting/latest/modules.html),
[event API](https://qualisys.github.io/qtm-scripting/latest/qtm.data.object.event.html),
[measurement file API](https://qualisys.github.io/qtm-scripting/latest/qtm.file.html),
[installed documentation introspection contract](https://qualisys.github.io/qtm-scripting/latest/qtm.utilities.documentation.html),
and the installed `C:\Program Files\Qualisys\Qualisys Track Manager\REST\RESTful_QTM_API.pdf`
(the earlier extracted REST reference was inspected again). The installed runtime catalog provides
stronger version-specific evidence than assuming that an online module list matches this machine.
No supported path/current-measurement selector for PAF field PUT was established.

### Live identities and exact Save failure point

Open project: `Shriners_Gait_Model_PAF_v1.0`.
Absolute project directory:
`C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\`.

Both records still have internal GUID **{17698CAD-BDA1-11F1-891E-2C58B910BA1C}**:

1. `C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\Data\Claudia_123-20260928T142041Z-1-001\Claudia_123\2026-10-01_2\`
2. `C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\Data\2026-10-01_2-20261004T101228Z-1-001\2026-10-01_2\`

Each tree record has Name=Claudia, patient ID=123, DOB=2006-09-14, Sex=Female,
Session ID=2 and 20 Dynamic / 1 Static measurements. Their ancestors are Raw folders, not
genuine Subject records. Fresh live values differ from older follow-up observations:

| Field | First copy | Second copy |
| --- | ---: | ---: |
| BodyMass (kg) | 100 | 71 |
| Height (m) | 0.6000000238418579 | 0.20999999344348907 |

Other anthropometric values remain individually recorded in `live-identity-before.json`.
No values were inferred from patient name or magnitude. The first copy's exported session.xml
still has BodyMass=71, demonstrating that XML is a snapshot rather than current live metadata.
Both XML roots declare Type=Session and Filename=2026-10-01_2; neither root supplies an
alternative API write identity. Direct GET of the shared GUID returns the first copy for both
requests. Therefore a valid full path can select an embedded read record, but cannot uniquely
address both copies through the supported write endpoint. Selecting a project/trial cannot alter
the endpoint's GUID addressing contract.

Existing Save pipeline remains:
`_on_save_clicked` -> changed-field/type/unit validation -> `_start_manual_sync` ->
`_SyncOperation.run` -> `QtmAnthropometricClient.synchronize` -> `read` target resolution ->
capability/owner checks -> guarded changed-only PUT -> read-back verification.
With these copies, `read` returns writable=false and `synchronize` stops at
**session_identity_resolution**, before typeInfo or PUT. Details report write_attempted=false
and verification_status=not_started. The unchanged GUI error is compact:
“Parameters not saved — QTM session identity is ambiguous.” Full evidence remains in Details.

`app/services/qtm_metadata_service.py` extracts trial/file/comments metadata; it is not a patient
metadata writer. The actual Save writer is `app/services/anthropometric_sync_service.py`.
This distinction explains why successful dynamic data communication is not a safe Save route.

### Commands, tests and actual results

Used PowerShell, `rg`/`rg --files`, `Get-Content`/`Select-Object`, read-only Python AST parsing,
urllib HTTP GET/documented scripting introspection, protobuf gRPC getter calls, pytest,
SHA256/difflib baseline comparison, and `git status --short`. Official sources were read through
web browsing and Agent Reach's Jina/curl route. Main commands:

```powershell
curl.exe -s --max-time 30 'https://r.jina.ai/https://qualisys.github.io/qtm-scripting/latest/modules.html' -o '<external-evidence>\qtm-modules.txt'
curl.exe -s --max-time 8 -H 'Content-Type: application/json' -d '""' http://localhost:7979/api/scripting/qtm/utilities/documentation/get_package_documentation/ -o '<external-evidence>\installed-native-api.json'
$env:QT_QPA_PLATFORM='offscreen'
$env:PATH='C:\Users\ADMIN\anaconda3\envs\python-example\Library\bin;'+$env:PATH
& 'C:\Users\ADMIN\anaconda3\envs\python-example\python.exe' -m pytest tests/test_anthropometric_sync.py tests/test_patient_metadata_sync.py -q --disable-warnings
& 'C:\Users\ADMIN\anaconda3\envs\python-example\python.exe' -m pytest '<external-evidence>\test_native_dispatch.py' -q
```

External evidence location: `C:\Users\ADMIN\Desktop\C\codex\shriners-native-metadata-baseline`.
Ran capture.py, inspect-qtm.py, probe-native.py, verify-live-collision.py, test_native_dispatch.py,
append-findings.py and audit-final.py there. Initial protobuf imports tried a nonexistent `proto` package and
then a tools directory; corrected to the actual primary QTM-GRPC root before the successful probe.
Initial get_path/is_dirty HTTP 400 responses were inspected: the server explicitly says
“method requires a measurement file”; both empty-array and empty-string argument forms behaved
identically. This was not treated as a JSON signature error or successful measurement read.

| Verification | Actual result |
| --- | --- |
| Existing focused GUI/HTTP metadata modules | **118 passed in 86.11s**. |
| Unique-target GUI Save 71 -> 72 -> Fetch | Controlled real HTTP/Qt test passed; unrelated identically named session unchanged; no session.xml/data.qpr substitution. Not live QTM persistence. |
| Duplicate GUIDs, similar names, invalid inputs, disconnected transport, unchanged/repeated Save, session switching, partial write failures, failed read-back | Existing focused tests passed; failure is retained as failure and drafts remain reviewable. |
| Existing Fetch behavior | Focused Fetch regression cases passed; no production Fetch change. |
| Offline native bridge/API checks | **7 passed in 0.11s**: six rejection cases across both real extracted dispatch methods, plus installed capability-catalog inspection. Hypothetical metadata command names were tested only offline, with zero native calls. |
| Live gRPC GetProjDirectory | success=true, correct open project directory. Confirms running bridge connectivity; does not identify a Session writer. |
| Live gRPC GetActiveMeasurement / GetEvents | Active measurement success=false with empty name; events success=true with `{}`. Neither proves event-write persistence. |
| Live scripting file context | No measurement open: get_path/is_dirty return HTTP 400 requiring a measurement; final documented `qtm.file.is_open()` returns false. No file was opened/saved/closed by this task. |
| Real Save resolver on both live copies | Both returned session_identity_resolution, write_attempted=false, verification_status=not_started; zero typeInfo requests, zero live PUTs. |
| Live read-back after blocked operation | Individual fields and complete embedded project tree unchanged. This verifies no mutation, not a successful save. |

### Changes, remaining restrictions and repair requirement

Only `spec/session1.md` was intentionally edited in this follow-up: this section was appended. **No source or
production/test function was modified.** External investigation harnesses are outside the project.
All source/settings/test files match their baseline SHA256 hashes. Of 705 baseline files, 703
remain byte-identical: this documentation append and the second session's opaque `data.qpr` differ.
The latter changed during the observation window; its origin is not established by this audit.
No investigation code writes that file, the live harness refuses PUT before transport, and the
before/after live metadata trees agree. It was neither edited nor restored by this task. Therefore
complete clinical-file byte stability is not claimed. No project files were added, removed or
moved, and all previous documentation bytes were preserved. Baseline-relative diff and Git status
are captured separately from the pre-existing dirty/untracked tree.
Nothing was staged, committed, pushed or automatically repaired.

A live successful metadata write/read-back is **not verified**. The live project offers no unique
Session GUID, and there was no open measurement during this investigation. No native write was
integrated because no supported setter/unique PAF targeting mechanism exists in the inspected
installed scripting contract. Future QTM versions or private vendor APIs were not assumed.

The required repair outcome is unique internal container IDs whose embedded tree records and
direct GUID GETs agree with the intended normalized paths. For an in-place repair preserving
existing clinical folders, obtain a supported procedure from **Qualisys support**; no documented
in-place GUID reset was found. Follow-up 7 records the documented recovery building blocks:
create a fresh Participant/Session through PAF Project view, import chosen recordings individually
without copying old data.qpr identities, review correct metadata, obtain the normal PAF session
export, and verify new owner GUID uniqueness before a single Save/Fetch/read-back check.
That reconstruction remains operator/vendor supervised and not end-to-end verified here.
Renaming folders, choosing the matching mass, selecting a project row, passing a trial basename,
or moving the same REST PUT through gRPC does not repair the collision. Writes must remain blocked
until QTM provides a verified distinct destination; no other patient's data may be changed to
make Save succeed.


## Session 1 Follow-up 9 — Local Calibration Saving and Patient Session Isolation

Date: 2026-10-09. This request cancels the earlier GUI-to-QTM parameter-writing requirement. Earlier entries are retained as history; their Save Parameters write flow is no longer the current implementation.

### Outcome and material limitation

Save Parameters now validates and atomically saves the application's existing session-local Static_<condition>_<export-subject>.py calibration file. It displays "Parameters saved successfully." after a committed local save. Fetch QTM remains a separate read-only operation with its unsaved-edit confirmation. Startup has no active patient/session, and actual patient/session changes invalidate both analysis pages and their old callbacks.

**A regression-test mistake changed clinical/runtime data during this follow-up. Recovery is unresolved.** An existing legacy test rewrote the canonical Dynamic 1.c3d, and other legacy tests sent event writes to the running QTM bridge. These effects are disclosed below. The implementation tests pass, but preservation of the affected recording/timeline cannot be claimed. The source changes did not modify the event writer, gRPC bridge, graph implementations, or clinical calculation modules.

### Removed QTM Save workflow

Before: edited widgets -> changed-field validation -> asynchronous QTM identity/owner resolution -> GUID collision protection -> capability lookup -> REST PUT -> write read-back/conflict feedback.

After: edited widgets -> local finite/type validation -> exact selected XML/session directory -> existing calibration template/update builder -> QSaveFile commit -> clear saved draft baseline -> local success confirmation.

Removed QtmAnthropometricClient.synchronize; payload/PUT support from _request; save-only writable-owner/capability tokens, collision/write-target guards, Float32-equivalence/quantization requirements, write read-back and conflict/retry bookkeeping; GUI Save dispatch into _start_manual_sync; QTM save-state fields/feedback and remembered per-session drafts; and _update_session_xml with its local-save calls. No GUIDs are repaired or edited. There is no offline write substitute to QTM-managed XML or data.qpr.

Read-source ambiguity protection remains for Fetch. QTM communication for events, trajectories, processing, and monitoring remains available.

### Local persistence, identity, and compatibility

- Reuses the existing Static_*.py self.attribute format and _build_updated_static_py. There is no new database or separate calibration format.
- The destination is under the normalized selected XML's directory. The export's original Fields/Name supplies the established processing filename; editing the displayed patient name/ID does not redirect saving into another patient's file. Invalid Windows filename characters retain the existing sanitizing convention.
- Existing model preferences and the transformation-matrix tail are preserved. Existing file syntax is checked before replacement. QSaveFile checks opening, complete byte write, and commit; failure retains the original file and draft and displays an error.
- The loaded source and destination must resolve inside the selected session. A symlink pointing to another session is rejected. An invalid manually typed XML path cannot save the previously loaded session.
- Local calibration takes precedence over exported XML/C3D fallback values when reopening that exact session. Numeric text is preserved rather than reformatted to two decimals or nine significant digits. Explicitly saved blank patient values/dates remain blank.
- New saves add valueMeasurementUnits = 'm' inside the existing format. Kilograms remain kilograms; left/right field mappings are retained. The marker makes metre-to-millimetre conversion explicit for headless static processing, including unusual finite lengths above 10 m.
- Headless static parameter loading prefers marked local calibration over stale export values. Local patient identity and dates are retained. Its setting writer preserves patient string quoting and Sex and stops rounding mass to two decimals.
- Legacy unmarked files retain the existing downstream unit heuristic/fallback. Existing calibration candidates are loaded only from the selected session, choosing the most recently modified valid Static_*.py file. Old calibration files are not migrated or deleted.
- Fetch populates widgets for review and does not update the local calibration file. Save is still required to persist fetched values locally.

### Validation rules

Removed application clinical minimum/maximum ranges for all eleven anthropometric fields and the former Float32 write-target range/quantization. No clamping or automatic clinical correction is applied.

Retained: required anthropometric fields must parse as finite Python float values. Malformed, blank, NaN, infinity, overflow, and nonzero decimal input that underflows to float zero are rejected. Metre values must also survive the established analysis model's multiplication by 1000 without becoming infinite; this is a numerical representation constraint, not a clinical plausibility range. Optional foot angles and sole thickness use the same finite/underflow validation when entered, with their own labels and degree/metre units.

Patient values retain string/control-character, supported Sex, and valid DOB checks. A partially selected DOB is rejected; a completely blank DOB can be saved. The existing static-frame contract requires a positive integer. No numeric parse failure is converted to zero. Supported float64 precision is retained for analysis; the GUI's entered numeric text is retained in local persistence. Arbitrary finite inputs are not a guarantee that a clinical analysis can run on physically impossible/degenerate measurements; formulas are unchanged.

### Static/Dynamic invalidation and session identity

MainWindow tracks a tuple of normalized absolute patient and session paths, using the explicit MRN only when no patient directory exists. Same-name patients in different folders therefore have different identities. PatientsPage emits context changes from explicit patient selection and session-row directory selection; population is batched so intermediate row signals cannot activate another context. Browsing another patient's session updates its patient identity/header.

An actual context change clears both pages and workflow completion markers. Static loads only the selected session's own XML/local calibration into an unprocessed form. Dynamic stays empty until the existing continuation loads that session's trials. No saved analysis files are deleted.

Static clear_session clears calibration/trial/source paths, patient/measurement inputs, completion summaries, progress/status, and draft baselines; disables patient controls/Save/Fetch/Run; cancels Fetch and invalidates processing. Dynamic clear_session removes old trial widgets, metadata, force-plate selections, queues/current trial, completion/status/events badges, watcher paths, and sync timer state. It does not fabricate three default trials when discovery is empty.

Processing-service generation checks reject old progress/log/completion/error signals. Page handlers capture their context generation. Static's delayed completion view and Dynamic's delayed polling/queue/error callbacks capture generation; old force-plate/event-dialog callbacks and watcher paths are rejected after switching. Thread cleanup is bound to the originating thread, allowing another processing job to start safely.

Fetch cancellation releases the old operation on context clearing. A stale Fetch completion is checked before it can release a newer operation or re-enable Save. Newer widget edits during a Fetch are retained through the existing revision/value checks.

Tab navigation and reselecting the same patient/session do not clear analysis. A -> B -> A restores A's saved local parameters and requires fresh analysis rather than carrying B's results.

### XML browsing and startup

Browse Data uses exactly "XML Files (*.xml)". set_session also validates the selected extension case-insensitively, parses the XML, and requires a Session root/type with Fields. Invalid selections show a helpful error. Valid selected XML filenames, including Calibration.XML, survive the MainWindow context handoff. Static trial discovery/parsing remains based on that XML and its session's local trials.

Removed Static's _load_default_session/_find_first_session_in_data_root and Dynamic's _load_default_session constructor activation. Loading a data-root setting only populates available choices. Patients & Sessions begins at its placeholder with empty MRN/session rows. Analysis starts with empty/disabled patient inputs and the message "Select a patient and session in Patients & Sessions to begin." QTM connection/reconnection updates connection indicators without selecting a patient.

### Modified files and functions

The table is generated from AST comparisons against the captured start-of-follow-up source, rather than against Git HEAD, which already contained extensive prior work. Nested helper names are included. New signals: StaticAnalysisPage.session_selected, SessionRow.directory_selected, and PatientsPage.analysis_context_selected.

| File | Changed / added / removed functions |
| --- | --- |
| app/services/anthropometric_sync_service.py | changed: AnthropometricSyncService.request, QtmAnthropometricClient._request, QtmAnthropometricClient.active_session_dir, QtmAnthropometricClient.read, QtmAnthropometricClient.read.discover, _SyncOperation.__init__, _SyncOperation.run, parameter_text, same_parameter_value, validate_parameter; removed: QtmAnthropometricClient.synchronize |
| app/services/processing_service.py | changed: GaitProcessingService.__init__, GaitProcessingService._on_error, GaitProcessingService._on_finished, GaitProcessingService._run_script; added: GaitProcessingService._emit_current, GaitProcessingService._release_thread, GaitProcessingService.invalidate; removed: GaitProcessingService._cleanup_thread |
| app/ui/main_window.py | changed: MainWindow.__init__, MainWindow._connect_signals; added: MainWindow._on_analysis_context_selected, MainWindow._on_calibration_session_selected |
| app/ui/pages/static_analysis_page.py | changed: StaticAnalysisPage.__init__, StaticAnalysisPage._auto_fetch_static_data, StaticAnalysisPage._auto_fetch_static_data.format_mass, StaticAnalysisPage._auto_fetch_static_data.format_meters, StaticAnalysisPage._auto_fetch_static_data.get_val, StaticAnalysisPage._browse_static_file, StaticAnalysisPage._create_config_view, StaticAnalysisPage._init_anthropometric_sync, StaticAnalysisPage._on_anthro_edited, StaticAnalysisPage._on_anthro_sync_finished, StaticAnalysisPage._on_fetch_clicked, StaticAnalysisPage._on_finished, StaticAnalysisPage._on_path_changed, StaticAnalysisPage._on_run_clicked, StaticAnalysisPage._on_save_clicked, StaticAnalysisPage._prepare_anthro_context, StaticAnalysisPage._save_static_parameters, StaticAnalysisPage._show_sync_details, StaticAnalysisPage._start_manual_sync, StaticAnalysisPage.set_data_root, StaticAnalysisPage.set_session; added: StaticAnalysisPage._bind_processing_context, StaticAnalysisPage._set_calibration_enabled, StaticAnalysisPage.clear_session; removed: StaticAnalysisPage._find_first_session_in_data_root, StaticAnalysisPage._load_default_session, StaticAnalysisPage._on_path_changed.find_static_candidate, StaticAnalysisPage._update_session_xml |
| app/ui/pages/dynamic_analysis_page.py | changed: DynamicAnalysisPage.__init__, DynamicAnalysisPage._init_ui, DynamicAnalysisPage._on_fs_directory_changed, DynamicAnalysisPage._on_fs_file_changed, DynamicAnalysisPage._on_open_force_plate_dialog, DynamicAnalysisPage._on_trial_error, DynamicAnalysisPage._on_trial_finished, DynamicAnalysisPage._on_view_trial_events, DynamicAnalysisPage.load_session; added: DynamicAnalysisPage._bind_processing_context, DynamicAnalysisPage._schedule, DynamicAnalysisPage.clear_session; removed: DynamicAnalysisPage._load_default_session |
| app/ui/pages/patients_page.py | changed: PatientsPage.__init__, PatientsPage._add_session_row, PatientsPage._on_select_patient, PatientsPage.load_patient_by_path, PatientsPage.load_session, SessionRow.set_directory; added: PatientsPage._on_session_directory_selected, SessionRow.clear_directory |
| Gait-lab-Vicon-to-QTM/Py3_StaticMain.py | changed: PatientInfo_Page.build_UI, PatientInfo_Page.build_UI.get_qtm_or_persisted, PatientInfo_Page.build_UI.saveSubjectData, normalize_processing_measurements |

Tests: updated tests/test_anthropometric_sync.py and tests/test_patient_metadata_sync.py to retire cancelled QTM-write cases and retain Fetch/unsaved-edit/read-source cases. Their HTTP PUT fixture now records/rejects unexpected writes. Added tests/test_local_calibration_workflow.py for local saving, precision, input errors, atomic failure, persistence, identity and lifecycle isolation. This append is the only documentation modification.

### Tools, dependencies, and commands

Used PowerShell, rg/rg --files, Git status/diff/diff --check, Python AST/compile, pathlib/hashlib/difflib/json, pytest, PySide6 real widgets/QSignalBlocker/QSaveFile/QThread/QTest, temporary directories, ezc3d, and NumPy already installed in python-example. No new package was installed. Ponytail and Graphify instructions were read; no code graph existed, and no graph generation/refactor was performed.

Python executable: C:\Users\ADMIN\anaconda3\envs\python-example\python.exe.
Test environment: QT_QPA_PLATFORM=offscreen; PATH prepended with that environment's Library\bin.

The final focused command, run from C:\Users\ADMIN\Downloads\Shriners_Plugin:

```powershell
& 'C:\Users\ADMIN\anaconda3\envs\python-example\python.exe' -m pytest tests/test_local_calibration_workflow.py tests/test_anthropometric_sync.py tests/test_patient_metadata_sync.py -q --disable-warnings
```

The final isolated regression command:

```powershell
& 'C:\Users\ADMIN\anaconda3\envs\python-example\python.exe' -m pytest tests/test_session1_regressions.py tests/test_mac_scale_persistence.py tests/test_qtm_auto_event_sync.py -q --disable-warnings
```

An earlier broader invocation additionally included tests/test_multi_trial_isolation.py and tests/test_manual_event_editing.py; this was unsafe, as described below. It must not be repeated against live clinical data/QTM without isolating both their filesystem targets and transport.

External evidence/work scripts and logs are in C:\Users\ADMIN\Desktop\C\codex\shriners-followup9-baseline. capture.py recorded a 705-file SHA256 manifest and copied source/docs/tests; it did **not** back up the clinical binary files. edit-service.py, edit-static.py, edit-dynamic.py, and update-existing-tests.py performed the scoped transformations. audit-followup9.py compiles the ten authored Python files, compares source/functions/hashes, emits baseline-relative diffs, and checks documentation prefix preservation. These external transformation scripts are one-time tools and should not be rerun on the already changed source.

### Tests and actual results

- Final focused suite: **91 passed, 14 warnings in 62.61s (0:01:02)**.
- Final isolated regression suite: **58 passed, 14 warnings in 11.99s**.

The focused coverage includes all eleven bilateral/anthropometric fields, exact reopen/restart text, edited name/ID/last name, blank identity/dates, stable local destination, another patient's files and QTM XML/QPR unchanged, preserved transformation tail, atomic commit failure, repeated saves, local saving with QTM offline/unusable IDs and no QTM requests, read-only Fetch after Save, unsaved-edit confirmation/new typing, no-open-measurement Fetch fallback, stale Fetch/worker/timer completion rejection, A -> B -> A/same-session/tab navigation, alternate XML filenames, non-XML/malformed XML/schema rejection, numerical integrity/explicit units, startup and reconnect state, and headless local metadata/measurement precedence without launching a clinical analysis.

Some development runs failed while old synchronization expectations were being replaced: the first Fetch-oriented run reported 35 passed/6 failed; an intermediate workflow run reported 81 passed/1 failed. Those expectations were corrected and the final focused run passed. The earlier broad run reported 146 passed/1 failed/14 warnings in 55.46 s. Its failure was test_direct_c3d_event_writing expecting the obsolete 2.45 s at frame 294, while unchanged one-based production conversion yielded approximately 2.4416667 s. No frame/event algorithm was changed to satisfy that assertion.

The next broad run excluding only the C3D module passed 144 tests/14 warnings in 55.63 s, but still included the unsafe manual "offline" RPC test. That passing run is **not** evidence of data preservation. A subsequent focused run passed 90 tests/14 warnings in 83.41 s; the final focused run below includes the additional headless patient/date test.

### Accidental legacy-test data writes and unresolved recovery

I inadvertently ran two existing event test modules against a running QTM environment:

1. tests/test_multi_trial_isolation.py::test_direct_c3d_event_writing targets the bundled canonical clinical session directly, rather than a temporary copy. It overwrote the EVENT group and reserialized the complete recording at:
   C:\Users\ADMIN\Downloads\Shriners_Plugin\Shriners_Gait_Model_PAF_v1.0\Shriners_Gait_Model_PAF_v1.0\Data\Claudia_123-20260928T142041Z-1-001\Claudia_123\2026-10-01_2\Dynamic 1.c3d.
   Its eight test events use frames 294, 309, 356, 372, 419, 433, 479, 493. The unchanged saved sidecar instead has frames 295, 310, 357, 373, 420, 434, 480, 494.
2. That module's test_cross_trial_qtm_protection overrides the active-title probe and sends a matching-trial event RPC. tests/test_manual_event_editing.py::test_event_service_operations calls send_events_to_qtm without a trial target under an assumed "offline" state. The actual bridge was reachable, so ClearEvents/SetEvents altered the open Dynamic 1 timeline. The second broad invocation repeated the manual RPC. QTM's message log shows event counts 1 and 4 at 01:50:40, then 4 at 01:59:44 on 2026-10-09.

Read-only native scripting calls qtm.file.get_path(), qtm.file.is_dirty(), and qtm.data.object.event.get_events() subsequently confirmed the canonical Dynamic 1.qtm was open, dirty=true, with four test events: RSTRIKE 1.9166666666666667 s, LOFF 2.033333333333333 s, LSTRIKE 2.441666666666667 s, ROFF 2.566666666666667 s. These POST scripting requests are getters, not parameter/event writes. Evidence: post-test-live-event-state.json.

The on-disk QTM measurement, session.xml, data.qpr files and all saved GCD results match their captured hashes. The application Save implementation issued no patient/anthropometric metadata writes. The affected C3D does **not** match its pre-test hash:

```text
Expected original SHA256:
0be86290b2b89a820fd8b0b24e5e17c111e486fc3ff7b87ce9f220f2e3325925
Observed overwritten SHA256:
ac2d70b1d7f0e8ab593b7d7fbd46a47c77773bde53ad5cb006e5843b41260992
```

Recovery attempts copied the overwritten recording outside the project, rebuilt candidate events from the unchanged sidecar, checked an older Shriners_Plugin ZIP and earlier temporary copies, and tried external-only metadata/time/label variants. None matched the original hash. Every recovery script requires an exact hash match before replacing the clinical recording; none passed that guard, and no guessed candidate was copied over it. The original clinical binary was not part of the source backup. The diagnostic QTM log was preserved.

Therefore, exact C3D restoration remains unresolved and requires a trusted pre-test recording copy. The live unsaved QTM timeline also remains altered; it must not be saved over the original measurement. Reloading the unchanged on-disk measurement without saving the test timeline can recover its persisted events, but no pre-test snapshot of other unsaved QTM edits exists, so that action was not automated. This incident violates the requested clinical-file preservation constraint; it is not presented as a successful recovery or concealed by passing tests. Both unsafe modules were excluded from the final isolated regression command.

### Remaining verification limits

- No end-to-end live static/dynamic clinical analysis was launched for these changes, and no clinical validation of unusual measurements was attempted. Worker races, GUI state, disk persistence, and existing graph/frame/event behavior were exercised in focused offline tests.
- The real running GUI process was not restarted automatically. Restart Shriners to load the changed Python code; the fresh-process persistence test explicitly selects its temporary session after starting empty.
- Fetch was exercised against real Qt widgets and local HTTP fixtures including offline/ambiguous-source/no-open-measurement responses. No new live patient parameter write was attempted or claimed.
- Legacy unmarked calibration files keep their prior downstream unit convention. Subject names invalid as Windows filenames remain constrained by the existing static-script filename contract; no QTM-managed names or metadata were rewritten.
- The unresolved recording/timeline recovery described above is a material data limitation. Final preservation checks cannot claim a clean clinical-data baseline.

### Final diff and preservation audit

The repository already had extensive modified/untracked source, tests, and documentation at the start. The following counts attribute only this follow-up against its captured baseline, including the new test file; they do not attribute all Git HEAD changes to this task.

| Source/test file | Added | Removed |
| --- | ---: | ---: |
| app/services/anthropometric_sync_service.py | 80 | 235 |
| app/services/processing_service.py | 26 | 17 |
| app/ui/main_window.py | 25 | 0 |
| app/ui/pages/static_analysis_page.py | 258 | 455 |
| app/ui/pages/dynamic_analysis_page.py | 79 | 38 |
| app/ui/pages/patients_page.py | 59 | 0 |
| Gait-lab-Vicon-to-QTM/Py3_StaticMain.py | 36 | 12 |
| tests/test_anthropometric_sync.py | 8 | 462 |
| tests/test_patient_metadata_sync.py | 7 | 328 |
| tests/test_local_calibration_workflow.py | 438 | 0 |
| Total source/tests | 1016 | 1547 |

No source/test files were moved or deleted, no folders reorganized, and no Git staging/commit/push was performed. Cancelled synchronization test cases were removed within their existing files. Prior documentation bytes are preserved as an exact prefix.

SHA256 checks confirm unchanged event_service.py, frame_coordinates.py, gcd_service.py, clinical_plots.py, case_presentation_page.py, auto_event_trigger.py, gapi.py, Py3_GaitModules.py, Py3_MathModules.py, and both embedded Py3_staticmain.py bridge implementations. Py3_StaticMain.py changes are restricted to local parameter precedence, explicit unit conversion, and setting serialization; clinical formulas are unchanged. Ten authored Python files compile, and scoped Git diff --check passes (Git also reports its existing CRLF normalization notices).

The full snapshot delta additionally includes the accidentally changed canonical Dynamic 1.c3d and the QTM Messages 2026-10-09.log runtime log. Those are separate from the authored source/test diff. All other clinical/session/result hashes match the pre-task manifest.

A final ad-hoc AST read initially omitted the source encoding and failed under Windows cp1252. Rerunning with explicit UTF-8 succeeded and confirmed both the obsolete QTM synchronize method and QTM-managed XML save updater are absent; this was a verification-command encoding error, not a failing application test.



## Session 1 Follow-up 10 — Static Patient Page Headless Mode Ownership Fix

Date: 2026-10-09. The reported Static Analysis failure was "AttributeError: 'PatientInfo_Page' object has no attribute '_headless'".

Confirmed cause: Static_Main.__init__(headless=...) sets self._headless on the application before constructing its pages. PatientInfo_Page.__init__ stores that application as self.parent and does not define a page-local _headless. Two checks added for local calibration precedence incorrectly read self._headless on the page. The first check runs during the application's initial build_UI, before the headless processing driver's try/except, causing immediate exit code 1.

Changed Gait-lab-Vicon-to-QTM/Py3_StaticMain.py at PatientInfo_Page.build_UI and its nested get_qtm_or_persisted: both checks now use self.parent._headless. This retains the actual requested execution mode, including True for Save & Run Static Analysis, rather than masking the exception with a False default. Production diff: two lines replaced. No clinical formulas, QTM APIs, frame/event/trajectory code, Fetch implementation, or patient/session selection logic changed.

Changed tests/test_local_calibration_workflow.py:

- Existing headless measurement and patient/date tests now put the flag on a parent application object instead of inventing a page-local attribute.
- Added test_real_static_patient_page_builds_with_mode_owned_by_application with four combinations: headless/interactive and saved local/no saved calibration.
- The test executes the actual Static_Main and PatientInfo_Page class definitions using real PySide6 compatibility widgets. QA/calibration report pages are inert substitutes. Only AST-selected definitions and parameter helpers are loaded; argparse, gapi, the script entry point, clinical processing, and native QTM RPCs are not run.
- It checks initial construction, repeat page building, local headless precision/precedence, existing interactive fallback behavior, actual parent ownership without a page-local flag, and unchanged temporary calibration/preferences bytes.

Commands/dependencies: PowerShell, rg, Git diff --check, Python AST/compile/hashlib/difflib, pytest and installed PySide6/pyside6_compat. Used C:\Users\ADMIN\anaconda3\envs\python-example\python.exe with QT_QPA_PLATFORM=offscreen and its Library\bin prepended to PATH.

Actual verification:

1. Ran the new four-case page test against captured pre-fix source through an external read-only pytest plugin: 4 failed, 50 deselected, 14 warnings in 2.14 s, all with the reported missing _headless AttributeError. The plugin substitutes source only inside the isolated test process; it does not replace production files.
2. An initial fixed-source selected run had 5 passed/1 failed: all pages constructed, but an assertion incorrectly expected XML mass in interactive mode when an existing local mass takes precedence. Corrected that test expectation, preserving production fallback behavior.
3. Final command: python -m pytest tests/test_local_calibration_workflow.py tests/test_anthropometric_sync.py tests/test_patient_metadata_sync.py -q --disable-warnings. Result: **95 passed, 14 warnings in 66.14 s**.
4. Changed Python source/test files compile. Scoped Git diff --check passed with Git's CRLF normalization notice. No unsafe legacy event tests were run, and no live QTM calibration was launched by this follow-up.

Source snapshots, baseline reproduction, final tests and diff evidence are in C:\Users\ADMIN\Desktop\C\codex\shriners-headless-fix-baseline. Prior documentation is preserved.

The snapshot audit also observed concurrent runtime changes outside the authored diff: canonical Claudia session Dynamic 1–5.GCD, Static 3.qtm, Static_BF_Claudia.py, and Messages 2026-10-09.log. The log records batch processing and measurement loads; a separately running app.py process was present. These tests use temporary session/calibration files and the agent issued no live QTM processing/write commands during this fix. The runtime files were not reverted or attributed to the two-line source patch. The canonical Dynamic 1.c3d matches this follow-up's starting hash; this does not establish recovery from the earlier follow-up's documented recording incident.

Remaining limit: complete live clinical calibration and its output persistence were not rerun or claimed. Cancel the failed processing view and retry Save & Run Static Analysis to launch the corrected script. No Git commit or push was made.



## Session 1 Follow-up 10 — session.xml Parameter Persistence

Date: 2026-10-09. Investigation outcome: **the required live QTM reload prerequisite failed. No application XML-saving workaround was implemented.** The repeated follow-up number is retained exactly as requested; the earlier headless-mode fix and all previous documentation are preserved.

### Confirmed QTM behavior and authoritative storage

Tested installed QTM **2026.2 build 17495**, using a disposable copy of the complete current project. Changed only the disposable session XML BodyMass text from 71 to 72. QTM continued to expose BodyMass **71**, including after opening/closing/reopening that session's measurement and after fully unloading/reloading the disposable project. The on-disk XML remained **72**, byte-for-byte unchanged through those operations. Thus neither a measurement reopen nor a full project reload imports the XML change into native PAF metadata on this installation.

Qualisys' official [PAF documentation](https://github.com/qualisys/paf-documentation/blob/main/README.md#types) states that non-measurement PAF item data reside in `data.qpr`, while measurement metadata reside inside `.qtm` files. Its [External program documentation](https://github.com/qualisys/paf-documentation/blob/main/README.md#external-program) describes `Export session` as producing `session.xml` for external processing. The project's own `Settings.paf`, `Analyses/Shriner Static`, enables `Export session: Yes`. This is an analysis export, not a verified native metadata import interface.

The live read-back is from QTM's PAF metadata API, which is also used by Fetch QTM. This was an actual installed-QTM project reload test, not a mocked server or a file-parser-only test. QTM's native patient form was not visually inspected, and a complete QTM application restart was not tested. No unsupported claim of visual confirmation or immediate live synchronization is made.

### Disposable test, identity checks and actual results

Evidence directory: `C:\Users\ADMIN\Desktop\C\codex\shriners-xml-persistence-investigation`.

- Captured a 706-file pre-task SHA256 manifest and full before-copies of the inspected source files and this document. Copied all 463 project files (498,220,470 bytes) into `disposable-project` outside the application repository and verified every copied file against its source before editing.
- Target: `disposable-project/Data/2026-10-01_2-20261004T101228Z-1-001/2026-10-01_2/session.xml`. Its root is `Session`, attributes `Type="Session"`, `Filename="2026-10-01_2"`; patient Name Claudia, ID 123, Session_ID 2. The disposable sibling under `Data/Claudia_123-20260928T142041Z-1-001/Claudia_123/2026-10-01_2` is the control session with native BodyMass 100.
- Both sessions retain internal native GUID `{17698CAD-BDA1-11F1-891E-2C58B910BA1C}`. No GUID or native metadata was edited to make the test succeed. Read-back enumerated the whole PAF tree and required one exact canonical target Path under the verified disposable project. No duplicated-GUID endpoint was used to select a write destination.
- The first read-only probe found the original Dynamic 1 measurement dirty. No close or discard command was issued against it. A later probe reported no measurement open, after the original project's log recorded an independent save/close at 16:37:12; testing proceeded only then.
- RT protocol version/QTMVersion probes succeeded. `TakeControl` returned `Wrong or missing password`; no password was guessed and no access setting was changed. The project was instead opened using its documented Windows file association, confirmed as `QTM.exe "<Settings.qtmproj>"`, with a hidden helper launch. Qualisys documents opening a project through [Settings.qtmproj](https://docs.qualisys.com/qtm/content/qtm_user_interface/qtm_startup.htm).
- First load of the edited disposable project: QTM session mass **71**, XML **72**, sibling native mass **100**. Both native Paths were verified to lie under the disposable project.
- Opened target copy `Dynamic 1.qtm` through the installed scripting file API, verified its exact path, read metadata, closed it, reopened the same file, verified again and closed. Both dirty checks were false before closing. Result stayed **QTM 71 / XML 72**.
- Fully unloaded the copy into an empty disposable control project, verified that project through REST, then reopened the edited copy. Result again **QTM 71 / XML 72**, with every edited XML byte unchanged. A clean measurement from the other disposable session was observed open on returning to the copy; it was inside the copy, verified clean, and closed before restoring the original project. The first strict no-open-file assertion therefore stopped that audit command; the follow-up captured the actual state and completed the checks with explicit copy-path and clean-file guards.
- Reopened the original project after the test. Original before/after PAF tree Fields were equal for every enumerated Path, including both original BodyMass values **100** and **71**. All original `session.xml` files and all Python source/test files match the pre-task hashes.

Recorded evidence: `live-state-before.json`, `rt-control-probe.json`, `after-project-launch.json`, `measurement-reopen-result.json`, `unloaded-project-state.json`, `full-project-reload-result.json`, `restored-project-state.json`, `native-fields-before-after.json`, the before/edited disposable XML, manifests and `focused-tests.txt`.

### XML schema, GUI mapping and units

The examined exports are UTF-16 little-endian with a BOM. The root's direct `Fields` contains merged patient/session values. Per-measurement Fields are separate historical/export snapshots, not interchangeable with the root fields. There are 21 Measurement elements in the tested export, with Type and Filename references. The root Type/Filename and Fields ID/Name/Session_ID are descriptive context; they do not replace native PAF GUID identity. No GUID was present in the tested root attributes; the collision is established by QTM's native tree.

| XML root Fields element | Existing GUI control | Meaning/unit |
|---|---|---|
| Name | `_first_name` | Patient name; no verified separate XML LastName field |
| ID | `_patient_number` | Patient identifier text |
| Sex | `_sex` | Existing schema enumeration |
| DOB | `_dob_day`, `_dob_month`, `_dob_year` | ISO date split into controls |
| BodyMass | `_body_mass` | kilograms |
| Height | `_height` | metres |
| InterAsisDistance | `_asis_dist` | metres |
| LeftLegLength / RightLegLength | `left_leg_length` / `right_leg_length` | metres, side retained |
| LeftKneeWidth / RightKneeWidth | `left_knee_width` / `right_knee_width` | metres, side retained |
| LeftAnkleWidth / RightAnkleWidth | `left_ankle_width` / `right_ankle_width` | metres, side retained |
| LeftAsisTrocanterDistance / RightAsisTrocanterDistance | `left_asis_gt` / `right_asis_gt` | metres; preserve schema spelling Trocanter |

`Settings.paf` declares these anthropometrics as Float fields, BodyMass as mass/kilograms and lengths in m. Its existing display decimals and Min/Max declarations were inspected, not modified or newly enforced in the GUI. No artificial clinical ranges were added. Other GUI settings (foot angles, sole thickness, alignment choices, frame number, trial settings, separate last name) have no verified equivalent root XML tags in this export; no tags were invented.

### Existing flow and inspected functions

No production functions were modified. Inspected:

- `app/ui/pages/static_analysis_page.py`: `set_session`, `_auto_fetch_static_data`, `_init_anthropometric_sync`, `_save_static_parameters`, `_on_save_clicked`, `_on_run_clicked`. The XML is resolved to the selected session, root Fields are parsed with ElementTree, and existing local Static_*.py calibration values currently take precedence over XML/C3D fallback values. The Save handler validates and persists the session-local Python calibration file atomically with QSaveFile, then reports that local save.
- `app/services/anthropometric_sync_service.py`: working read-only QTM snapshot/Fetch path. Kept unchanged.
- `Gait-lab-Vicon-to-QTM/Py3_varExtractor.py`: `extract_fields_by_filename` identifies a measurement from XML but currently merges the C3D extraction; the older XML Fields extraction block is commented out. This does not establish native QTM XML import.
- `Gait-lab-Vicon-to-QTM/Py3_StaticMain.py`: local static-settings load and headless patient-page precedence. The previously fixed parent-owned `_headless` checks remain unchanged.
- Project `Settings.paf`: schema, inheritance and analysis export declarations; read only.

Before and after flow is unchanged: GUI edit -> existing validation -> selected session-local Static_*.py atomic save -> optional static processing. Fetch QTM remains independent. There is **no new XML persistence implementation**, no new REST/gRPC parameter writer and no claim that a local save updated QTM.

### Probe serialization, backups and unimplemented safety features

The offline disposable probe saved full original XML bytes externally before editing. It decoded UTF-16, replaced exactly the first matching BodyMass 71 element with 72, encoded back to the same BOM/endianness, parsed it, and used a temporary file plus os.replace inside the disposable session. A reverse byte replacement reproduced the full original bytes exactly; restoring BodyMass in the parsed tree reproduced the complete original parsed structure. All unrelated nodes, 21 measurement entries, attributes, references, whitespace and numeric text were preserved in this probe. No precision conversion or general ElementTree serialization was used to write it.

This probe is not an application save service. Production XML backup/recovery, concurrency/version detection, read-only failures, selection-change rejection, duplicate-GUID XML-save handling and the proposed close-QTM warning were deliberately not implemented or claimed tested after the required reload prerequisite failed. The probe backup remains recoverable, and the changed disposable XML remains available for inspection. Original XML files were never replaced.

No close/reopen instruction would make this a working QTM metadata save on the tested installation. QTM did not overwrite this XML during the tested measurement/project reopen sequence. Analysis-triggered re-export was not executed; documentation and Settings.paf establish that export is an analysis operation, so future processing may regenerate XML from native metadata. No prediction about every possible QTM caching/overwrite circumstance is presented as a live test result.

### Tools, commands and focused verification

Tools: PowerShell, rg, Git status/diff, Python stdlib pathlib/shutil/hashlib/json/xml.etree.ElementTree/re/urllib/socket/struct/os, Windows registered file association, installed native QTM HTTP scripting and PAF GET APIs, pytest/PySide6 offscreen. Used `C:\Users\ADMIN\anaconda3\envs\python-example\python.exe`.

Web research used agent-reach's `mcporter call 'exa.web_search_exa(...)'` and `curl.exe -s https://r.jina.ai/<official-source>`, plus direct read of Qualisys' raw PAF README. Sources and RT protocol text were retained externally. The installed native API JSON was parsed selectively. An initial helper incorrectly expected module key `name` instead of `path`; corrected before API use. A PDF-read probe found no pymupdf installed; no package was installed and official online documentation was used.

QTM operations:

- GET `/api/v1/project`, GET `/api/v1/paf/instance?depth=3`.
- POST read-only scripting getters `/api/scripting/qtm/get_version/`, `qtm/file/is_open/`, `qtm/file/get_path/`, `qtm/file/is_dirty/` (empty argument arrays). get_path/is_dirty correctly returned HTTP 400 when no measurement existed; is_open was used as the prerequisite.
- POST scripting `qtm/file/open/` with the exact disposable measurement path and `qtm/file/close/` only after path/clean guards. These controlled disposable file opening, not parameter writes.
- TCP 22223 RT `Version 1.25`, `QTMVersion`, `TakeControl` (denied) and `ReleaseControl`. No RT metadata, event, capture, save or project-load command was issued.
- `Start-Process ... QTM.exe -ArgumentList '"<verified-project>/Settings.qtmproj"' -WindowStyle Hidden` for supported project open/unload/reload/restore.

Regression command: `python -m pytest tests/test_local_calibration_workflow.py tests/test_anthropometric_sync.py tests/test_patient_metadata_sync.py -q --disable-warnings`, with QT_QPA_PLATFORM=offscreen and the environment's Library/bin on PATH. **95 passed, 14 warnings in 64.76 seconds.** No unsafe legacy event tests or clinical analysis were run by this investigation.

Additional evidence assertions passed: exact UTF-16 BOM preservation; only the intended XML scalar bytes changed; all unrelated XML structure/measurement references preserved; QTM first-load and full-reload target Paths under disposable project; unchanged duplicate native GUID; intended native mass 71 and sibling 100; original PAF Fields equal before/after; original XML and source/test hashes unchanged. These are separate from the live negative reload result. GUI XML-saving reopen, invalid/read-only/conflict-save cases are not implemented/tested as a new feature because the prerequisite failed.

### Diff, runtime audit and remaining restriction

Authored repository diff for this request: **spec/session1.md append only; zero production/test code changes**. No files moved, directories reorganized, Git stage/commit/push or GUID repair. Scoped whitespace check and exact preservation of the prior documentation prefix were verified. The large pre-existing working-tree diff is not attributed to this investigation.

The snapshot audit also observed runtime file changes in the original project during this interval: Settings.qtmproj, both Claudia data.qpr files, dynamic C3D/QTM recordings and auto_event result/log files, and the QTM Messages log. Opening/unloading QTM can persist project state, and an independently running app.py process (PID 3528, started 16:18:14) remained present; the Messages log records an original Dynamic 2.qtm load at 16:43:06 and subsequent event-output timestamps were observed. No agent parameter/event/trajectory write or clinical processing request was issued. These runtime changes were recorded separately in the external audit, not reverted or falsely reported unchanged. Native patient/session Fields and original session XML are confirmed unchanged; source/tests are unchanged. No stronger attribution of every runtime binary change is possible from the captured evidence.

Final restriction: this requested XML-to-native-QTM mechanism is ineffective on the tested QTM version. Per the explicit stop condition, leave the current calibration saving and working Fetch behavior in place. Native metadata must be edited through a supported QTM workflow with a correctly resolved patient/session identity; a separate XML editor would only change an export and cannot honestly be presented as a successful QTM save. No live metadata-writing workaround or duplicate-GUID repair is included.


## Session 1 Follow-up - Stale Calibration Reference Reset Only

Date: 2026-10-10. Authoritative project: `C:\Users\ADMIN\Music\Shriners_Plugin`.

### Confirmed reset gap and limited change

`StaticAnalysisPage.clear_session()` already emptied the displayed XML, `_session_path`, `_filename`, `_subject_name`, `_loaded_py_path`, `_anthro_context`, baseline/dirty state, completion labels and progress. It already invalidated processing and metadata request generations. No extra loaded/completed boolean exists that needed resetting. However, a completed or attempted Fetch could leave `_manual_requested_identity` holding A's XML path and metadata, `_manual_inflight_values` holding A's patient values, and `_anthro_inflight_revisions` holding the old request's edit snapshot. A pending automatic edit timer was also left running. The regression reproduced these surviving caches after switching from A to B.

Only `app/ui/pages/static_analysis_page.py::StaticAnalysisPage.clear_session` changed in production: four added lines, zero removed:

```python
self._manual_requested_identity = {}
self._manual_inflight_values = {}
self._anthro_inflight_revisions = {}
self._auto_sync_timer.stop()
```

Fresh dictionaries clear page-owned caches without mutating a dictionary already captured by another operation's diagnostic record. The existing reset still clears calibration paths/UI and invalidates old results. The application's newly selected patient/session identity remains unchanged. Manual Browse remains the entry point for the new XML. No new signal, state manager, identity validation, calculation, GUID operation or persistence mechanism was added. Save Parameters and Fetch QTM implementations are unchanged. MainWindow, Patients, Case Presentation, Dynamic Analysis, processing services, XML persistence and QTM communication code are unchanged from this request's baseline.

Added `tests/test_static_calibration_reset.py::test_patient_reset_discards_calibration_request_caches` using existing disposable A/B fixtures and MainWindow. The test covers loading and simulated processing of A; caching A's actual request identity/values; switching to B; blank UI and empty calibration/cached references; preserved active B context; stopped edit timer; discarded old processing/Fetch callbacks; blocked Save before manual XML selection; Browse B; processing handoff/completion; actual local Save and read-back of B BodyMass 72; byte-preservation of A's saved calibration and both XMLs; same-session selection and tab changes preserving B.

### Separate ownership failure: reproduced, not changed

The stale caches do **not** cause `_save_static_parameters` to emit `Loaded calibration belongs to a different session.` That guard uses `existing.resolve().parent != session_dir`, where `session_dir` comes from the selected XML's parent. The loader explicitly accepts both the session root and its `Calibration` subdirectory, and the writer chooses `Calibration` when it exists. Thus a valid B calibration can be saved there on the first run when no file exists, but a subsequent Save rejects the existing B file because its parent is the subdirectory rather than the root. This reproduces the reported error with no surviving A file reference.

Exact conflicting values captured by the disposable diagnostic:

- GUI calibration XML (`_file_path_edit.text()`): `C:\Users\ADMIN\AppData\Local\Temp\pytest-of-ADMIN\pytest-433\test_correct_b_calibration_sub0\B\2026-10-01_2\session.xml`
- Page selected XML (`_session_path`): `C:\Users\ADMIN\AppData\Local\Temp\pytest-of-ADMIN\pytest-433\test_correct_b_calibration_sub0\B\2026-10-01_2\session.xml`
- Application active patient/session tuple (existing MainWindow selection): `["c:\\users\\admin\\appdata\\local\\temp\\pytest-of-admin\\pytest-433\\test_correct_b_calibration_sub0\\b", "c:\\users\\admin\\appdata\\local\\temp\\pytest-of-admin\\pytest-433\\test_correct_b_calibration_sub0\\b\\2026-10-01_2"]`
- Loaded calibration (`_loaded_py_path`, created by the first B Save & Run): `C:\Users\ADMIN\AppData\Local\Temp\pytest-of-ADMIN\pytest-433\test_correct_b_calibration_sub0\B\2026-10-01_2\Calibration\Static_BF_Same name.py`
- Ownership check left operand (`existing.resolve().parent`): `C:\Users\ADMIN\AppData\Local\Temp\pytest-of-ADMIN\pytest-433\test_correct_b_calibration_sub0\B\2026-10-01_2\Calibration`
- Ownership check right operand (`Path(_session_path).resolve().parent`): `C:\Users\ADMIN\AppData\Local\Temp\pytest-of-ADMIN\pytest-433\test_correct_b_calibration_sub0\B\2026-10-01_2`
- Cleared prior request identity (`_manual_requested_identity`): `{}`


These are path identifiers, not patient/session GUID comparisons. The valid B mismatch was independently reproduced after a full reset and first successful local save. Both A and B files remained byte-identical after the rejected subsequent save. A separate diagnostic injected a genuine A calibration path into B and confirmed the existing ownership check still rejects it without writing either session. Per the explicit scope restriction, the ownership predicate and all Save Parameters logic remain intact; this subdirectory case is an unresolved persistence restriction, not a successful save or a reason to bypass protection.

### Tools, commands and actual results

Used PowerShell, `rg`, `Get-Content`/`Get-ChildItem` (read-only source/data-path inspection), `apply_patch`, Python AST comparison, SHA-256 snapshots, `difflib` and pytest. Runtime: `C:\Users\ADMIN\anaconda3\envs\python-example\python.exe` (Python 3.9); `QT_QPA_PLATFORM=offscreen`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONIOENCODING=utf-8`, and the environment's `Library\bin` prefixed to PATH. Commands ran in the Music project. No original clinical scripts or QTM requests were executed.

1. Before production modification: `python -B -m pytest tests/test_static_calibration_reset.py -q -p no:cacheprovider --disable-warnings` -> **1 failed, 14 warnings, 3.55 s**. Failure showed A's XML identity and patient values still present in the three request caches after switching to B, while the selected XML and loaded `.py` references were already blank.
2. Initial reset patch plus three focused existing checks -> **4 passed, 14 warnings, 5.09 s**. Then changed dictionary clearing to replacement with fresh empty dictionaries to preserve already-captured diagnostic records.
3. Final verification command:

```powershell
& 'C:\Users\ADMIN\anaconda3\envs\python-example\python.exe' -B -m pytest tests/test_static_calibration_reset.py tests/test_local_calibration_workflow.py::test_local_save_preserves_xml_qpr_other_patient_and_transformation_tail tests/test_local_calibration_workflow.py::test_static_late_completion_timer_cannot_restore_old_results tests/test_local_calibration_workflow.py::test_fetch_result_from_previous_session_is_discarded tests/test_local_calibration_workflow.py::test_old_fetch_completion_does_not_release_new_request tests/test_local_calibration_workflow.py::test_fetch_remains_read_only_after_local_save 'C:\Users\ADMIN\AppData\Local\Temp\shriners-stale-calibration-zoq5tb1g\test_ownership_diagnostic.py' -q -p no:cacheprovider --disable-warnings
```

Result: **8 passed, 14 warnings, 17.40 s**: six workflow/reset/persistence regressions and two ownership diagnostics. The valid Calibration-subdirectory diagnostic passed by confirming the existing save rejection; it does not represent a repaired or successful save in that layout. Existing local persistence preserved XML, opaque QPR bytes, another patient's file and transformation-tail content. Fetch tests used disposable fixtures, not live QTM.

`git diff --check -- app/ui/pages/static_analysis_page.py tests/test_static_calibration_reset.py` passed. AST comparison confirms `clear_session` is the only changed Static Analysis function; Save/Fetch bodies are identical. MainWindow is byte-identical to this request's baseline. Snapshots and the diagnostic JSON are outside the repository at `C:\Users\ADMIN\AppData\Local\Temp\shriners-stale-calibration-zoq5tb1g`. Previous documentation is preserved byte-for-byte as the prefix of this file. No Git stage/commit/push, reset/revert, saved-result deletion or audit restoration was performed.

### Remaining limitations

Clinical computations and live QTM processing were not run. Processing start/completion were simulated while exercising real Qt widgets and actual local calibration saves in temporary sessions. This task changes only the existing reset; it does not add a Case Presentation selection signal or alter whichever existing callers trigger that reset. The valid `Calibration`-subdirectory ownership rejection remains as described above. Authored changes are four production lines, one focused regression test and this documentation append; pre-existing repository edits are not part of this task.


## Session 1 Follow-up — Calibration Subfolder Validation Fix

Date: 2026-10-10. Project: `C:\Users\ADMIN\Music\Shriners_Plugin`.

### Root cause and exact production change

The existing workflow selects a session XML and persists parameters in a session-local `Static_*.py` calibration. Both the loader and destination selection support the session root and its `Calibration` child directory. `_save_static_parameters()` nevertheless required the existing calibration's resolved parent to equal only the session root. Consequently the first save into an empty Calibration folder succeeded, but the next Save after processing rejected that same valid file.

Only `app/ui/pages/static_analysis_page.py::StaticAnalysisPage._save_static_parameters` changed in production: two replaced validation lines and one explanatory comment.

```diff
-        allowed_target_parents = {session_dir.resolve(), calib_dir.resolve()}
+        # Resolving Calibration here would let a directory link expand the allowed destinations.
+        allowed_target_parents = {session_dir, calib_dir}
...
-            if existing is not None and existing.resolve().parent != session_dir:
+            if existing is not None and existing.resolve().parent not in allowed_target_parents:
```

`session_dir` is already absolute and resolved from `Path(self._session_path).resolve().parent`; `calib_dir` is its exact `Calibration` child. Both the destination file and existing source file are resolved before comparing their parent Path objects with these two permitted locations. The permitted child itself is deliberately not resolved into a different folder: a symlink/junction must not expand the allowed destinations into another patient's or session's directory. No string-prefix or substring matching is used. Arbitrary children, siblings sharing the session-name prefix, another session of B, another patient's session, and links/traversal escaping these two parents remain rejected.

This corrects the existing `.py` calibration ownership comparison; it does not add a new XML file-selection or session-discovery workflow. The existing selected-XML agreement check, XML parser, numeric/patient-field validation, subject-name handling, parameter dictionary, transformation preservation, atomic QSaveFile serialization and save/reload mechanism remain unchanged. Patient fields remain editable under the existing metadata rules; no new immutable patient/GUID identity check was invented. Reset behavior, MainWindow selection logic, Fetch QTM, XML persistence, QTM communication and all other production functions are unchanged from this request's baseline.

### Focused tests and actual persistence

Added `tests/test_calibration_subfolder_validation.py` using existing disposable A/B XML fixtures and real StaticAnalysisPage controls/local persistence. Its 14 cases cover:

- Session-root and Calibration-subfolder saves: save A, load B, perform the existing Save & Run processing handoff, simulate completion, change B BodyMass to `72.125`, perform a second real Save Parameters, read the resulting `.py`, then instantiate a fresh StaticAnalysisPage and reload B's XML. The reloaded BodyMass is exactly `72.125`, patient ID is B and units remain m. A's saved calibration and both XMLs remain byte-identical. Saving again from the fresh page also succeeds.
- Reusing B's existing Calibration file when changing the condition: new destination creation succeeds and existing transformation-tail content survives.
- Five rejected source locations: another patient, another B session, an arbitrary subdirectory, a sibling sharing the session-name prefix, and an escaping `..` path. Foreign bytes remain unchanged and no B output is created.
- Four actual directory-symlink cases: foreign source and foreign Calibration destination, each with a nonexistent or existing target file. Both creation and replacement attempts are rejected with foreign directory contents unchanged. Inspection confirmed Windows reparse tag `0xa000000c` (symbolic links) for the exercised links; the test helper also supports a directory-junction fallback where Windows symlink privileges are unavailable.
- Invalid Sex and incomplete DOB still block saves in the Calibration layout through the existing patient metadata validators.

Also ran the existing A-to-B reset regression, XML/QPR/other-patient/transformation-tail preservation check, typed-XML mismatch check, and atomic-save-failure check. The reset regression confirms the old calibration selection is cleared, B remains the active context, stale callbacks cannot restore A and Browse still works. No reset code was changed by this task.

Before the production change, the valid Calibration-subfolder save/reload test and linked-destination guard test both failed (**2 failed, 14 warnings, 1.90 s**). The former reproduced the erroneous session mismatch; the latter showed the destination guard resolving the permitted child through the foreign link and reaching the later source rejection rather than rejecting the destination itself. The final tests additionally cover the missing-target link case, where no source file exists to provide that later rejection.

Final command, from the Music project:

```powershell
& 'C:\Users\ADMIN\anaconda3\envs\python-example\python.exe' -B -m pytest tests/test_calibration_subfolder_validation.py tests/test_static_calibration_reset.py tests/test_local_calibration_workflow.py::test_local_save_preserves_xml_qpr_other_patient_and_transformation_tail tests/test_local_calibration_workflow.py::test_invalid_typed_xml_path_cannot_save_previous_session tests/test_local_calibration_workflow.py::test_atomic_save_failure_preserves_original_and_dirty_draft -q -p no:cacheprovider --disable-warnings
```

Result: **18 passed, 14 warnings, 6.84 s**. Unlike the earlier negative diagnostic, the valid-subfolder checks now require successful file persistence and read-back through a fresh page. Processing calculations are stubbed, but QSaveFile writes, calibration serialization and reload are real and occur only in temporary sessions. No live QTM connection or clinical calculation was run.

Tools: PowerShell, `rg`, source reads, `apply_patch`, Python AST/difflib comparison, SHA-256 snapshot comparison, pytest, and `git diff --check`. Environment: Python 3.9 at the interpreter above, `QT_QPA_PLATFORM=offscreen`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONIOENCODING=utf-8`, environment `Library\bin` prefixed to PATH. Scoped whitespace checks passed; AST comparison identifies `_save_static_parameters` as the only changed production function, and an exact expected-text comparison confirms its only changes are the two validation lines and comment. The prior documentation prefix is preserved byte-for-byte. Evidence snapshot: `C:\Users\ADMIN\AppData\Local\Temp\shriners-calibration-ownership-7b5xa5aa`.

Authored files for this request: `app/ui/pages/static_analysis_page.py`, new `tests/test_calibration_subfolder_validation.py`, and this append to `spec/session1.md`. No source outside the ownership validation was modified; no saved clinical files were deleted, no folder structure was changed, and no Git stage/commit/push or reset/revert was performed. Live clinical/QTM verification remains outside these local tests.


Runtime snapshot note: the final filesystem audit additionally observed a regenerated Static Analysis bytecode cache and changes to seven original Dynamic C3D recordings plus their event logs/results during the interval. These are recorded separately in the external `runtime-changes.json`; no agent clinical/event processing command was run and all tests above used disposable sessions. QTM PID 20656 was already running; an independent `python.exe app.py` PID 23596 started at 22:39:12, after the 22:37:06 baseline snapshot. This audit cannot attribute every runtime write more precisely. These files were not reverted or deleted. Original session XMLs and unrelated source files remained unchanged in the captured comparison; the authored patch remains the validation source, focused test and documentation append.


## Session 1 Follow-up — Dynamic Analysis Static Calibration Detection

Date: 2026-10-10. Authoritative project: `C:\Users\ADMIN\Music\Shriners_Plugin`.

### Confirmed root cause and session-path trace

Current `DynamicAnalysisPage._is_static_calibration_ready()` used `session_dir.glob("Static_*.py")`, which searched only the root even though the existing workflow can save valid calibrations in `Calibration/`. Trial completion flags, existing GCD files and detected events do not establish static calibration readiness and must not bypass the prerequisite.

`MainWindow._on_static_to_dynamic` passes the selected session XML to `DynamicAnalysisPage.load_session`. `load_session` already stores the absolute resolved XML path in `_session_path`. The readiness check now explicitly obtains `Path(self._session_path).resolve().parent`, keeping the lookup anchored to that XML's session directory. No active patient/session resolution or selection code was changed.

### Exact change and preserved validation

Only production function changed: `app/ui/pages/dynamic_analysis_page.py::DynamicAnalysisPage._is_static_calibration_ready` (six added lines, two removed; net four):

```diff
-        session_dir = Path(os.path.dirname(self._session_path))
+        session_dir = Path(self._session_path).resolve().parent
...
-        static_files = list(session_dir.glob("Static_*.py"))
+        from app.services.session_organizer import find_static_calibration_files
+        static_files = [
+            sf for sf in find_static_calibration_files(session_dir)
+            if sf.resolve().parent in {session_dir, session_dir / "Calibration"}
+        ]
```

The existing `find_static_calibration_files` helper is reused without modification. It enumerates existing `Static_*.py` files in the root and Calibration folder. Because the helper itself follows directory links, the readiness check filters each resolved file's parent against the canonical session root and its exact Calibration child. A Calibration link or root-file link resolving into another patient/session cannot satisfy the prerequisite. There is no recursive patient search, copied file, cached prior calibration, string-prefix comparison or new session manager.

The existing transformation check is unchanged: readable content must contain both `valueEPelvisAnatRelTech` and `Transformation Matrices`. It continues checking other candidates when one is incomplete/unreadable. Arbitrary `.py` files are not candidates. The existing no-file and missing-transformation warnings, and `_on_process_clicked` prerequisite, remain intact. This task preserves that existing marker check; it does not introduce matrix parsing, numeric/shape validation or execute calibration source to determine readiness.

### Existing files with incomplete calibration data

A read-only scan of the current project's clinical Data tree found seven Static files: two contain both required markers; five do not. Four lack both `valueEPelvisAnatRelTech` and `Transformation Matrices`; one contains the pelvis-matrix marker but lacks `Transformation Matrices`. Their exact absolute filenames and per-file missing markers are recorded in `C:\Users\ADMIN\AppData\Local\Temp\shriners-dynamic-calibration-ui1zzwx4\read-only-calibration-markers.json`. These files were read as text only, never executed or modified. Merely fixing folder discovery cannot make incomplete configurations ready; the existing validation correctly continues to reject them. Files that already meet both markers can now be found in their Calibration folder.

### Focused tests and actual results

Added `tests/test_dynamic_static_calibration_readiness.py` with 13 cases using disposable sessions:

- Valid calibration in root and Calibration folder; equivalent normalized `..` alias paths remain anchored to the same session.
- Empty/parameter-only calibration, missing pelvis marker and missing Transformation Matrices marker are rejected.
- Arbitrary `.py` filename containing the marker text is rejected.
- Another patient's and another same-patient session's calibrations are not searched.
- Actual linked Calibration folder and linked root calibration resolving to A cannot make B ready (both tests ran; no symlink skips).
- A valid candidate remains usable when another candidate is incomplete.
- Existing patient switch/load workflow discards A's Dynamic state; B without calibration triggers the exact Static Calibration Required warning and does not start the queue. After B receives its own valid Calibration file, the existing processing action reaches a queue containing `('dynamic', 'Dynamic 1.qtm')`. Only the processing handoff is stubbed; no QTM/clinical command is run.

Before the fix, running the valid Calibration-subfolder case produced **1 failed, 14 warnings, 1.35 s**, reproducing the erroneous No Static calibration file message.

Final command, run from the Music project:

```powershell
& 'C:\Users\ADMIN\anaconda3\envs\python-example\python.exe' -B -m pytest tests/test_dynamic_static_calibration_readiness.py tests/test_session_subfolder_organization.py::test_dual_lookup_fallback tests/test_static_calibration_reset.py tests/test_calibration_subfolder_validation.py -q -p no:cacheprovider --disable-warnings
```

Result: **29 passed, 14 warnings, 11.14 s**. This includes the helper's existing dual-location lookup test, the A/B reset regression, and all 14 actual local calibration-save/ownership checks from the preceding task. Static save-and-fresh-page-reload remains successful and foreign-path protections remain functional. No existing tests were rewritten to weaken a prerequisite.

Tools: PowerShell, `rg`, source reads, `apply_patch`, Python AST/difflib comparison, SHA-256 snapshots, pytest, and `git diff --check`. Runtime: Python 3.9 at the interpreter above; `QT_QPA_PLATFORM=offscreen`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONIOENCODING=utf-8`, environment `Library\bin` prefixed to PATH. Scoped whitespace check passed. AST comparison confirms `_is_static_calibration_ready` is the only changed Dynamic Analysis function. Static Analysis source (including reset, Save and Fetch) and the session organizer are byte-identical to this request's baseline. Previous documentation is preserved byte-for-byte as this file's prefix. Evidence snapshot: `C:\Users\ADMIN\AppData\Local\Temp\shriners-dynamic-calibration-ui1zzwx4`.

Authored files: `app/ui/pages/dynamic_analysis_page.py`, new `tests/test_dynamic_static_calibration_readiness.py`, and this append to `spec/session1.md`. No patient-selection, GUID, XML-persistence, QTM, event/frame or graph code was changed. No Git stage/commit/push or reset/revert was performed. Live clinical calculations and QTM processing were not run; the processing handoff was simulated. The prerequisite still rejects configurations missing the original required markers.


## Session 1 Follow-up — Dynamic Completion GCD Lookup Import

Date: 2026-10-10. During verification of the readiness fix, the user reported a separate live traceback from `_bind_processing_context`'s finished-slot lambda into `_on_trial_finished`: `NameError: name 'find_gcd_file' is not defined`.

Confirmed cause: `find_gcd_file` was imported locally in `load_session` and `_process_next_in_queue`. Those local bindings are unavailable in `_on_trial_finished`, which invokes the helper in its dynamic-completion branch. All callers of the helper and completion callback were inspected before editing.

Exact production fix: one line added in `app/ui/pages/dynamic_analysis_page.py::DynamicAnalysisPage._on_trial_finished`, directly inside `else: # dynamic`, before deriving the trial stem:

```python
from app.services.session_organizer import find_gcd_file
```

The existing helper now runs in the callback's own scope. Its root/GCD-folder lookup, success prerequisite (completed status plus actual GCD existence), row status, success/error counters, failed-trial list, and 400 ms next-trial scheduling are unchanged. No event, frame, QTM, clinical computation or patient/session behavior was modified. Static Analysis/Save/Fetch and the session organizer remain byte-identical to the initial readiness-task baseline.

Added four cases to `tests/test_dynamic_static_calibration_readiness.py::test_trial_completion_checks_gcd_and_schedules_next`, invoking the actual generation-bound finished-slot lambda with real DynamicAnalysisPage trial rows: root GCD success, GCD-subfolder success, completed status with no GCD, and failed status despite a GCD. Each asserts row status, exact success/error counters, failed-trial list and scheduling of the next trial. Only temporary fixture files are moved/deleted for the missing/subfolder cases; no original clinical file is touched. Scheduling is captured to avoid starting clinical processing or QTM calls.

Before the import, the GCD-subfolder completion test reproduced the exact traceback: **1 failed, 14 warnings, 3.52 s**. After the one-line fix, the same full focused command listed in the preceding section passed **33 tests, 14 warnings, 39.19 s** (the original 29 checks plus four callback cases). These tests use real lookup/UI callbacks and disposable files; GCD generation and live QTM/clinical processing are not run.

Tools/commands: `rg` for every helper/callback use, source inspection with PowerShell, `apply_patch`, the preceding pytest command with the same offscreen/no-bytecode environment, AST comparison, `difflib`, SHA-256 snapshots and scoped `git diff --check`. Exact expected-text comparison confirms the callback fix is only the one import. Relative to the beginning of the readiness request, only `_is_static_calibration_ready` and `_on_trial_finished` changed in production. Scope remains the same three authored files: Dynamic Analysis source, its new focused test file, and this documentation append. All prior documentation is preserved. No Git push/stage/commit, reset/revert or application restart was performed; an already-running GUI must be restarted to import the edited source.


Runtime audit: the filesystem snapshot also observed unrelated runtime differences in the Dynamic Analysis bytecode cache, an original Dynamic GCD and the QTM Messages log. Exact paths are recorded in the external evidence `runtime-changes.json`. No original clinical processing or event/QTM write was issued by the agent; focused tests used disposable sessions and captured processing callbacks. These concurrent runtime files were left in place, not reverted or deleted. No stronger attribution of these writes is inferred from the snapshot.

## Session 1 Follow-up — QTM Remove All Events minimal fix (2026-10-14)

Root cause: the 1.2-second poll called sync_qtm_events_to_session(force=False), whose empty-timeline branch restored cached events. Removed that branch so successful empty reads use the same save_trial_events persistence path as partial deletions. Only the matched trial's JSON/event data is updated; unrelated trial files are preserved. No cached JSON file needs deletion.

Production changes: app/services/event_service.py — sync_qtm_events_to_session removes automatic restore; fetch_events_from_qtm rejects the bridge's ambiguous empty-object/error response and non-container payloads. Explicit raw_events: [] and list [] remain valid empty reads. Existing unsuccessful RPC/exception handling returns before synchronization persistence.

app/ui/pages/dynamic_analysis_page.py — _poll_qtm_events_sync, _on_single_trial_pull_from_qtm, and _on_sync_from_qtm_clicked refresh zero-event text and reset only an EVENTS LABELED row to READY. Completed processing status is retained. No timer, loading, processing, calibration, selection, frame conversion, or explicit writer code changed.

Tests: updated tests/test_qtm_auto_event_sync.py to replace the obsolete automatic-restore expectation. Added tests/test_qtm_remove_all_events.py. Executed with the existing python-example interpreter, QT_QPA_PLATFORM=offscreen, PYTHONDONTWRITEBYTECODE=1:

```text
python -B -m pytest -q -p no:cacheprovider tests/test_qtm_remove_all_events.py tests/test_qtm_auto_event_sync.py
17 passed, 14 existing dependency deprecation warnings, 1.54 seconds.
```

Executed checks: 8→7, 8→5, 1→0, 8→0; four repeated synchronization cycles; actual temporary JSON persistence/reload; other-trial byte preservation; failed reads preserve cached events; valid empty vs bridge-error payloads through mocked gRPC; actual Static and Dynamic page construction; GUI zero state followed by eight new simulated events; manual Push callback; actual explicit sender emits ClearEvents then SetEvents through mocked transport. No live endpoint was contacted by these tests.

NOT RUN: live Remove All Events on QTM, real auto-label detection/reprocessing, actual calibration execution, real manual event writes. Newly generated event ingestion was simulated; it is not proof of a real detector run. Protected detection scripts, processing services, startup scripts and explicit write implementation were not edited.

Reviewed the complete task delta against captured pre-edit source/test content. Only the two permitted production files changed, plus the two focused test files and this documentation append. Existing unrelated modifications were preserved. git diff --stat reports the whole pre-existing dirty tree (76 tracked files, 7498 insertions, 1658 deletions), not this task alone; git diff --check passed with exit 0. No Git commit/push or service restart. The running GUI needs a normal restart to import the updated Python source.

## Session 1 Follow-up — Event JSON fallback path fix (2026-10-15)

Confirmed against the current source: `Gait-lab-Vicon-to-QTM/Py3_varExtractor.py::extract_c3d` searched only beside the C3D when embedded events were absent. Existing auto-label sidecars are stored under the same session's `Events/` directory. Added exactly these two candidates at lines 95–96, before the existing root candidates:

```python
os.path.join(c3d_dir, "Events", f"auto_event_{c3d_stem}_results.json"),
os.path.join(c3d_dir, "Events", f"auto_event_{c3d_stem.lower()}_results.json"),
```

The fallback can now find the intended trial's existing sidecar. Embedded events retain priority; legacy root lookup, JSON parsing/error handling, event labels and all frame conversions remain unchanged. No processing, calibration, QTM, parameter-saving, or presentation code was modified. Exact byte comparison against a fresh external snapshot confirms the entire production delta is these two inserted lines, including preservation of existing line endings.

Focused tests use the actual extractor module with real temporary ezc3d fixtures outside the project. QTM-facing imports are replaced by fail-fast test doubles, and the force-plate helper (which calls live QTM) returns an empty dictionary. Existing event extraction/JSON/frame code executes unchanged. Before the patch, the `Events/` regression failed with empty events while legacy-root and embedded-event checks passed (1 failed, 2 passed). After the patch, all **15 tests passed in 0.489 seconds**, covering embedded precedence, `Events/` lookup for Dynamic 7 and Dynamic 20, lowercase stems, root compatibility, Events-before-root priority, missing JSON, malformed JSON, invalid frame input, another trial/session isolation, two strikes per limb, frame conversion equivalence with first-frame offsets 0 and 37 (relative and absolute JSON frames), and the unchanged static branch.

An isolated copy of the real Dynamic 7 C3D and its JSON was also tested through `extract_fields_by_filename()` using a synthetic temporary session XML: all eight events were retrieved, with two LSTRIKE and two RSTRIKE events and the existing one-based conversion. Original clinical files were read only. Test command: `C:\Users\ADMIN\anaconda3\envs\python-example\python.exe -B C:\Users\ADMIN\AppData\Local\Temp\shriners_event_lookup_fix_89auha5m\test_event_lookup.py`. The external folder retains the test harness, before snapshots, manifest, and exact source patch.

End-to-end Dynamic Processing/GCD generation was **NOT RUN**: the normal script can issue live QTM/model writes, so a copied C3D alone does not isolate it safely. Existing GCD files were not regenerated; recovery of their curves requires a separately controlled processing run. No dependency installation, application restart, clinical write, Git commit or push was performed.

Scope verification: this current project copy has no `.git` directory; `git status` and repository `git diff --check` were attempted and reported that it is not a Git repository (diff-check exit 129). `git diff --no-index --check` against the captured source snapshot emitted no whitespace errors (exit 1 indicates the intended content difference). The final snapshot comparison checked 425 source/data/document file hashes and size/modification metadata for 77 QTM measurements: only the permitted extractor and this documentation append differed. The pre-existing document content is preserved byte-for-byte; no scoped project files were added or removed. No other production file was changed, and no separate graph-selection improvements were made.


## Session 1 Follow-up — Parallel dynamic processing safety audit (2026-10-16)

Result: **implementation stopped at the mandatory safety gate**. No production change was made. The current dynamic command cannot be shown to process different trials independently because it combines per-trial C3D computation with reads and writes against a shared live QTM measurement. The request explicitly requires stopping when isolation would need changes to protected gait/QTM code.

Existing scheduling: `app/ui/pages/dynamic_analysis_page.py::_on_process_clicked` (1058-1101) builds an optional auto-label queue followed by dynamic trials; `_process_next_in_queue` (1139-1218) starts one job; `_on_trial_finished` (1229-1264) validates status plus GCD existence and schedules the next job after 400 ms. `app/services/processing_service.py::GaitProcessingService` owns one worker/thread, rejects overlap at 286-288, and launches the existing interpreter and arguments in `ProcessingWorker.run` (91-125). Cancellation and session invalidation remain unchanged. Single-trial processing and all GUI behavior are untouched.

Confirmed blockers, inspected read-only:

- `Gait-lab-Vicon-to-QTM/Py3_varExtractor.py:169` always invokes `ProcessForceplateData(reader)`. `Py3_Utils.py:563-565` calls `GetForcePlate()`; `gapi.py:188-189` sends an empty argument object to the fixed QTM endpoint at port 50052 (`:30,59-71`). The receiver `QTM-GRPC/tools/Py3_staticmain.py::GetForcePlateData` (311-336) reads the current measurement's force series. `Py3_Utils.py:583-605` can combine those live center-of-pressure arrays with another trial's C3D data without checking trial identity. Concurrent workers would share this input source.
- `Py3_DynamicMain.py:4194-4224` creates common modeled marker names such as LHJC/RHJC/LKJC/RKJC. `Py3_Utils.py::SimModlOutput.CreateModeledMarker/SetModelOutput` (93-108) sends marker/trajectory writes through `gapi.py:83-98,174-176`. Those requests include marker names and samples but no patient, session, or measurement target. The active receiver dispatches them at `QTM-GRPC/tools/Py3_staticmain.py:117-130`; `setTrajectory` (539-587) resolves the current measurement and writes via `qtm.data.series._3d.set_samples` at 587. `createMarker` (591-603) likewise operates on the active measurement. Two workers writing LKJC therefore have the same destination.
- No existing offline/no-QTM/per-process-endpoint option was found in the active command. The existing noninteractive flags only control dialogs or force-plate choices. Serializing individual RPCs does not establish which trial owns QTM's active measurement. Serializing the entire command is the existing sequential behavior. Computation and later GCD generation share an in-memory model in `Py3_DynamicMain.py:8104-8109`; there is no supported separate command to schedule just its CPU-only stage. Separating it or adding verified measurement targets would change protected components and requires a separately authorized task.

Other collision/resource findings: XML and C3D paths are derived from the requested session and filename (`Py3_varExtractor.py:254-307`). `Py3_CreateGCD.py:103-113` writes `GCD/<trial-stem>.GCD`, and may remove that same trial's legacy root GCD; distinct canonical stems generally have separate disk outputs, but this does not isolate QTM. The extractor truncates filenames at the first dot (`:292`), and case aliases could map to the same Windows output. Calibration files are shared read-only by the inspected callers (`Py3_DynamicMain.py:143`, `Py3_CreateGCD.py:93`). No active fixed intermediate/log-file writer was found in the inspected dynamic/helper path; the shared `test.json` save call is commented out at `Py3_DynamicMain.py:8096`. All children use the source directory as cwd (`processing_service.py:121`), which does not isolate the bridge.

Resource policy: read-only `os.cpu_count()` reported 12 logical CPUs, which would suggest six workers before affinity, pending-trial, and RAM caps. No parallel worker calculation or configuration was introduced after the safety gate failed. Peak per-process RAM and actual numerical-library thread counts were not measured; optional thread-pool metadata was unavailable and no dependency was installed. There is no evidence supporting a safe RAM-based worker count for this workload.

Executed checks: three isolated assertions against the actual AST-extracted `gapi.py` serialization functions, with `grpc_send_command` replaced by an in-memory capture, passed: (1) two different trajectory arrays for LKJC serialize the same destination name with no trial/session identifier; (2) CreateModelMarker contains only the marker name; (3) GetForcePlate sends an empty identity payload. These are serialization/safety checks, not clinical processing or concurrency tests. No live endpoint, Qt GUI, processing command, auto-labeler, clinical writer, or application restart was invoked.

NOT RUN: one/two/four-worker functional tests, cancellation/out-of-order scheduler tests, clinical or copied-trial processing, output-equivalence checks, sequential/parallel timing, CPU-utilization sampling, and peak-RAM measurement. There is no implemented scheduler to validate and no performance improvement is claimed. After a separately approved safe isolation mechanism exists, a reproducible benchmark should use a fixed disposable trial set and identical interpreter/arguments; record sequential then bounded-parallel wall time, aggregate CPU, parent/child peak RSS, active child count, failures, and numerical GCD equality (excluding creation timestamps). Do not run that benchmark against the current shared live-QTM path.

Tools: PowerShell source reads, `rg`, Python AST inspection/in-memory command capture, CPU query, and a filesystem hash/metadata snapshot. An independent read-only review confirmed the QTM targeting blocker. Git status was attempted; this project copy has no `.git` directory, so repository status/diff reporting is unavailable. Final scope verification uses the captured source/data hashes and an append-only comparison of this document. Only this documentation append is authorized/performed for the blocked implementation; production calculations, Static Analysis, QTM integration, processing orchestration, single-trial execution, and clinical files are preserved. No commit or push.
