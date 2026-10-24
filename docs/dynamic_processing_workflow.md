# Dynamic processing and serialized QTM delivery

Validated offline on 24 October 2026 with Python 3.9, NumPy 1.26.4 and PySide6.
Original reference: GitHub main `e6b06a1d25454e92c81ff6f4477f1036b9526f1f`.

## Calculation and persistence

Parallel Dynamic Files selects concurrent **files**, including files from the same
patient. The ceiling comes from CPU count, optionally reduced by
`SHRINERS_MAX_PARALLEL_DYNAMIC_FILES`; four is not hardcoded. Independent QProcess
workers use one BLAS thread each. Cancellation terminates their subprocesses.

Dynamic processing records marker/trajectory requests locally, including optional
Pelfix, heel, toe and multisegment foot markers. It never contacts QTM. The existing
NumPy calculations, local reconstructed fields and GCD semantics are retained.
Completed GCDs are available to Case Presentation independently of QTM delivery.

Artifacts:

```
<session>/Processing/QTMWrites/<trial-id>/<run-id>/manifest.json
<session>/Processing/QTMWrites/<trial-id>/<run-id>/trajectories.npz
```

The manifest stores ordered operations, complete source/session/measurement
identities, source fingerprints, calibration/model version, frame windows and
offsets, NPZ/GCD checksums and timings. Publication is atomic. Reprocessing changes
`latest.json`, invalidating older artifacts. OS locks prevent two writers using
the same trial output. NPZ loading disables executable object serialization.

## Old and new write architecture

The old gRPC handler called native QTM trajectory APIs on ThreadPoolExecutor
workers. Serializing the external client with a QThread did not fix that native
execution context. The QThread writer and unsafe legacy compatibility path have
been removed.

The app now uses Qt timers, gRPC futures and QNetworkAccessManager. Receiver
threads only queue trajectory commands and return status. QTM's registered
`ShrinersDispatchTrajectory` command callback executes one pending operation when
invoked through the official REST `qtm.gui.send_command` endpoint. It verifies
that its thread matches the scripting thread where registration occurred before
calling any native trajectory API. An unexpected context fails closed.

Official references:

- https://qualisys.github.io/qtm-scripting/latest/ — REST interface, default port 7979.
- https://qualisys.github.io/qtm-scripting/latest/qtm.gui.html#send_command — command invocation, equivalent to clicking its button.
- https://qualisys.github.io/qtm-scripting/latest/qtm.gui.html#set_command_execute_function — registered execution callback.
- https://qualisys.github.io/qtm-scripting/latest/qtm.file.html — exact path, opening and saving.

For each operation the client waits for queue receipt, invokes the registered
command through REST, waits for the HTTP response, then reads the stored native
result through gRPC. It never submits another operation before acknowledgment.
An application QLockFile and bridge batch lease prevent overlapping clients.
Other legacy bridge requests are blocked during trajectory delivery; their
event/static behavior outside an active trajectory batch is retained.

Direct legacy SetTrajectory/CreateModelMarker RPC mutations are rejected. Both
the updated bridge and QTM REST interface must be available. There is no fallback
to worker-thread trajectory writes.

## Complete queue and destination checks

```python
write_queue = [trial_1_operations, ..., trial_N_operations]  # 1 <= N <= 20
# Each trial list contains complete trajectory records in their original order:
[marker_name, X, Y, Z, exists, start_frame, end_frame, source_offset, target_range]
```

XYZ and exists are copied NumPy arrays recovered from NPZ. The actual sender
consumes these records. Counts vary per trial; a trial producing 13 trajectories
retains all 13 records. Interleaved marker-creation operations remain in manifest
order; existing marker IDs are reused instead of recreated.

All manifests are validated before native delivery. Input/checksum checks are
repeated under the trial lock. Reject wrong identities, mismatched shapes,
non-boolean masks, non-finite existing samples, invalid offsets/ranges and invalid
frequency. QTM checks the exact absolute `.qtm` path, frequency and inclusive
measured range. Identical basenames in different patient folders do not match.
Main's sample construction, residuals and inclusive target range remain intact;
measurement selection/ranges are never altered to fit incorrect offsets.

The callback opens the exact requested measurement when needed, stopping if that
would abandon another edited measurement. Each operation checks identity before
and after mutation and reads samples back. After all operations succeed, the
completed trial is saved; the queue advances only after QTM confirms the same
file is no longer dirty. The button tooltip discloses replacement of named
trajectory ranges and saving each completed trial.

## UI, failures and recovery

One Write Operation button, one progress bar and one wrapping status label remain
on Dynamic Analysis. The button is visible but disabled until processed artifacts
are ready (1–20 trials), and is disabled during delivery. Progress counts
confirmed saved **trials**, not submitted markers: `0 / N`,
`Writing Dynamic i / N`, `Done — N / N`, or the failing trial and actual error.
The coordinator belongs to the application and survives page navigation.
Lower-right write status, Cancel, Details, Retry and OK panels are removed.

The first error stops the entire queue. Completed trial/operation statuses persist
in application-local `qtm-writes.json`; finished batches are archived under
`qtm-write-history`. Clicking Write Operation explicitly again for the same batch
skips completed trials and reads back previous completed/uncertain operations
before continuing. Matching data is adopted without rewriting. A differing or
unverifiable uncertain operation stops for inspection instead of being replayed.

Timeouts never prove failure. The transport queries status without retrying the
mutation. A request confirmed still queued can be cancelled before native
execution and resumed on a later explicit click. If execution/status remains
uncertain, delivery stops. Inspect QTM and reload the bridge only after an active
operation has stopped. Logs record trial/file/marker, destination, range/offset,
length, timestamps, acknowledgments and errors.

## Offline evidence

Before branch integration, 163 focused tests passed: numerical equivalence,
actual subprocess concurrency, calibration readiness and serialized delivery.
Mock delivery covers 1/3/20 trials, variable 13/18-trajectory payloads, optional
markers, receiver/native thread separation, one outstanding operation,
acknowledgment-gated progress, first-failure stop, uncertain completion/read-back,
wrong destination and invalid payloads. Production asynchronous gRPC/REST client
tests use disposable mock servers on random local ports and cover an unavailable
REST dispatcher. They cannot reach the user's QTM endpoints.

The prior offline production export retained all 14,579 GCD lines after excluding
timestamps and temporary paths. The 111 numerical regression tests and earlier
298-array/421-intermediate parity evidence are retained. Real enabled-foot/AFO/
shod/sitting-foot clinical equivalence is not established by the available fixture.

Prior repeated-copy benchmark (six 1,027-frame files; medians of three runs):

| Concurrent files | Batch time | Speedup | Aggregate worker working set |
|---|---:|---:|---:|
| 1 | 13.10 s | 1.00x | 195.5 MiB |
| 2 | 7.27 s | 1.80x | 388.0 MiB |
| 3 | 5.36 s | 2.44x | 581.4 MiB |
| 4 | 5.02 s | 2.61x | 762.4 MiB |

All 72 exports matched their corresponding reference. This is repeated-workload
performance evidence, not a multi-patient clinical validation cohort. No live
QTM throughput or crash-free operation is claimed.

## Disposable live-QTM procedure (not performed)

1. Copy a complete session, saved C3Ds/calibration/events and matching QTM files
   into a disposable folder. Keep original patient measurements closed. Process
   the copies so manifests contain their copied absolute paths.
2. Load this checkout's QTM-GRPC/startup_tools.py in QTM Project Options >
   Miscellaneous > Scripting and reload/restart the updated bridge. Confirm REST
   on localhost:7979 is available and ShrinersDispatchTrajectory is a user command.
   Do not install a GUI runtime into embedded QTM.
3. Save/close unrelated edited measurements. Test one copied trial first. Click
   Write Operation once; check marker names, first/last frames, missing-sample
   gaps, confirmed progress and saved-file identity.
4. Compare QTM read-back with NPZ, then reopen the saved copy and verify persistence.
   Proceed to two different copied trials, then up to 20 with optional markers.
5. On copies, test missing targets, wrong ranges and a disconnect. The first error
   must stop delivery. Inspect uncertain samples before any explicit resumption.
6. Stop on a native error or thread-guard failure. Preserve app/QTM logs. Mock
   tests cannot establish callback behavior or stability in installed QTM.

No real QTM trajectory writes were performed during this refactor. Original main
and static worktree edits are preserved separately; final source commits and
integration hashes are recorded in the main1 integration report.
