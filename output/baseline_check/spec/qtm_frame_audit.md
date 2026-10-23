# QTM Frame Numbering and API Audit

**Date:** 2026-10-11  
**Project audited:** `C:\Users\ADMIN\Music\Shriners_Plugin`  
**Scope:** Read-only audit. No source file, QTM project setting, measurement, event, or trajectory was changed. This report is the only file created by the audit.

## 1. Executive summary

QTM has distinct concepts that must not be collapsed into one constant:

1. the current/visible marker-frame number in the QTM timeline;
2. the selected measurement and trace ranges;
3. a zero-based array/sample index in application code or an exported C3D; and
4. an event time on the measurement clock.

The installed QTM documentation confirms that the timeline exposes a current frame and independently configurable selected measurement range, and that QTM exports can use the selected range. It does **not** document a universal rule that every QTM timeline always starts at frame 1, or a supported setting that changes its display origin to frame 0. Therefore `QTM_TIMELINE_FIRST_FRAME = 1` is an application convention, not a QTM-wide proven invariant.

The local application currently converts all event times through that one-based convention. Its embedded QTM bridge reads timeline ranges, but does not obtain or return a documented canonical first marker-frame number. It also labels the start of the *trace* range as `First Frame`, which is not equivalent to the first selected measurement frame.

No live QTM query was made: QTM was running, but neither the application server (50051) nor the embedded QTM-script bridge (50052) was listening. Running arbitrary expressions in an unavailable/unknown scripting context would not have been safe. One local C3D was read without modification and reported a C3D header first frame of 0; that result applies only to that exported file.

## 2. Installed QTM environment

| Item | Observed value | Evidence / status |
|---|---|---|
| Installation | `C:\Program Files\Qualisys\Qualisys Track Manager` | Local filesystem inspection |
| QTM executable | Qualisys Track Manager 2026.2 (build 17495) | `QTM.exe` version resource |
| Embedded Python | Python 3.10.9 | `python.exe --version` from the QTM installation |
| QTM process | Present during audit | Read-only process inspection |
| Application gRPC listener | 50051 not listening | Read-only TCP listener inspection |
| QTM scripting gRPC listener | 50052 not listening | Read-only TCP listener inspection |
| Local QTM scripting help | Installed | `Help\content\techref\qtm_scripting_interface.htm` and Project Options scripting help |
| REST / RT protocol documentation | Installed and current official web documentation reviewed | See sources below |

The installed scripting help identifies Python and Lua as QTM embedded scripting languages and links to the Qualisys scripting repository. This confirms that `qtm.*` imports in the bridge are intended for the QTM scripting host; it does not establish that those modules may safely be imported from an ordinary external Python process.

## 3. Official QTM documentation findings

### Timeline and ranges

The official Timeline control bar documentation says that, in file mode, the control indicates/selects the current frame, trace range, measurement range, and events. It says the measurement range is the portion of the original measurement used for plotting, exporting, and playback. The installed Timeline Parameters help separately defines:

- **Current position at frame** — current frame;
- **First selected frame** — first frame in the measurement range;
- **Last selected frame** — last frame in the measurement range; and
- trace frames before/after the current frame.

This is direct evidence that a selected range can begin after the original capture start. It is not evidence that QTM renumbers the original measurement when the range is changed.

### Export and frame identity

QTM's C3D export documentation states that the exported frames are selected by the measurement range. The MAT export documents `StartFrame` as the measurement start frame number, `Frames` as the number of frames, and event `Frame` as the corresponding event frame (with event time rounded to the nearest frame). These fields are the documented export-level way to preserve the distinction between start frame and count.

### Real-time protocol

The official RT protocol documents:

- `GetCurrentFrame`, which returns a current real-time data packet only while a measurement is running;
- a **Marker Frame Number** field in each data packet;
- `GetCaptureC3D` and `GetCaptureQTM`, which return capture files; and
- `GetParameters`, which returns QTM settings XML.

The protocol does not document a `GetFirstFrame` command, a timeline selected-range query, or a global display-origin setting. `GetCurrentFrame` is not a safe substitute for the first frame of a saved/open measurement.

## 4. Frame-coordinate model

| Coordinate | Meaning | Source / confidence |
|---|---|---|
| QTM marker frame number | Frame number in a QTM RT data packet / timeline display | Official RT protocol and UI docs; base is not stated |
| Selected measurement range | Inclusive first/last selected frames used for export/playback | Official QTM UI docs |
| Trace range | Displayed trajectory-trace extent around current position | Official QTM UI docs; not a recording identity |
| Event time | Seconds on the QTM measurement clock | Local bridge uses `event["time"]`; MAT export documents event time and frame |
| C3D header first/last frame | Fields stored in an exported C3D header | Local read of one C3D and the C3D-reading implementation |
| Python array index | In-process collection position | Application-local convention only |

For a recording whose displayed first frame is `F0`, an array element `i` should map to `F0 + i`. For an event at time `t` and marker frequency `Hz`, the correct conversion depends on the recording's actual origin and QTM's rounding rule; it cannot safely be inferred from `1 + round(t * Hz)` for every recording.

## 5. Local source audit

### Application convention and event path

| File | Lines | Observed behavior | Audit assessment |
|---|---:|---|---|
| `app/services/frame_coordinates.py` | 1-46 | Sets `QTM_TIMELINE_FIRST_FRAME = 1`; maps sample index to `index + 1`, frame to time as `(frame - 1) / frequency`, and time to `1 + round(seconds * frequency)`. | One-based application convention. Its docstring reports a prior observation, but this audit did not independently reproduce it against the current QTM session. |
| `app/services/frame_coordinates.py` | 24-34, 60-75 | Supports `recording_start_frame` metadata and relative indices, but defaults missing metadata to the one-based constant. | Capable of carrying a crop origin, but callers must supply a verified one. |
| `app/services/event_service.py` | 222-268, 433-532, 702-776 | Persists `initial_frame_offset`, `recording_start_frame`, and `frame_convention`; sends/reads QTM events via event time. | Event transport is time-based, then converted by the local one-based functions. |
| `app/ui/dialogs/event_details_dialog.py` | C3D metadata path | Uses ezc3d C3D point header fields when available. | C3D first frame is an export/file attribute and must not alone define the live QTM display base. |
| `app/services/qtm_metadata_service.py` | 129-158 | Reads C3D header first/last frames only to calculate frame count and frequency; does not expose the start frame to callers. | A start-frame datum is discarded here. |

### Embedded QTM bridge and trajectory path

| File | Lines | QTM operation | Audit assessment |
|---|---:|---|---|
| `Gait-lab-Vicon-to-QTM/QTM_GRPC/tools/Py3_staticmain.py` | 120-123 | `qtm.gui.timeline.get_frame_count()` | Confirms count only; no first-frame identity. |
| same | 385-396 | `get_measured_range`, `set_measured_range`, `get_selected_range` | These are local bridge calls to embedded APIs. Their method names/return types were not independently confirmed in public API reference for this installed build. `get_selected_range` and `get_measured_range` are treated as distinct by this code. |
| same | 415-470 | Gets events, frequency, count, and measured range; converts event time through `time_to_frame`; reports `recording_start_frame = measured.start + 1`. | Conflates measured-range start with a displayed-frame assumption. It needs runtime verification before being used as canonical frame origin. |
| same | 525-529 | Exports `First Frame` / `Last Frame` from `get_trace_range()`. | Naming is misleading: trace range is not the selected measurement range or necessarily the recording origin. |
| same | 546-595 | Writes 3D samples to an explicit inclusive `target_range`; validates it lies inside the measured range. | The bridge treats QTM range values as integer sample/range coordinates. No display-base conversion is applied here. |
| `QTM-GRPC/tools/Py3_staticmain.py` | corresponding code | A second, materially similar bridge copy. | Default application configuration points to this copy; configuration should be verified before future runtime conclusions. |
| `Gait-lab-Vicon-to-QTM/Py3_varExtractor.py` | C3D extraction path | Reads `header.points.first_frame` as `initial_frame_offset`. | C3D-derived origin is propagated locally; it is not a documented live-QTM timeline query. |
| `Gait-lab-Vicon-to-QTM/Py3_Utils.py` | force calibration crop path | Uses C3D point first-frame and analog/point-frequency conversion. | Cropping and analog-rate conversion can alter local indices and must retain source origin. |

### Configuration and active-server determination

`app/services/settings_service.py` defaults the configured bridge folder to `QTM-GRPC`. `app/services/event_service.py` has a fallback to `QTM-GRPC` before `Gait-lab-Vicon-to-QTM/QTM_GRPC`. Both bridge copies declare port 50052. No process was listening on 50052 at audit time, so the active loaded copy could not be established from a live handshake.

## 6. C3D header check

A read-only ezc3d inspection was run against one local dynamic C3D:

| Field | Result |
|---|---:|
| C3D `first_frame` | 0 |
| C3D `last_frame` | 1026 |
| Point frame rate | 120 Hz |
| Header-derived count | 1027 |

This proves that this exported C3D stores a zero first-frame value. It does **not** prove that the QTM timeline for that measurement displayed frame 0, nor that all project measurements/export options behave the same way.

## 7. Questions answered

| Question | Result |
|---|---|
| Is frame 1 mandatory in QTM? | **Not confirmed.** Official documentation reviewed describes frame controls and ranges but does not state a universal base. The application's frame-1 rule is local. |
| Can QTM display or configure frame 0? | **Not established.** No official display-origin setting was found, and no safe live UI/script query was available. A C3D file may contain `first_frame = 0`; that is not proof of QTM GUI behavior. |
| Can laboratory configuration change practical starting frames? | **Yes, for selected/exported measurement range.** QTM exposes first/last selected frame and exports use the selected range. Whether the visible frame label is renumbered was not documented or tested. |
| Does QTM use zero-based internal sample indices? | **Unverified.** The bridge code assumes integer range coordinates and its app layer uses a zero-based sample index, but the official documentation reviewed does not define embedded scripting index origin. |
| Can Python retrieve the actual first frame? | **Potentially through embedded timeline range APIs used by this bridge, but not verified for QTM 2026.2.** The current bridge has no dedicated, documented `get_first_frame` call. |
| Can RT API retrieve the first frame of an open/saved measurement? | **Indirectly only.** RT can provide current packet marker frame number or a capture file; no documented direct first-frame command was found. A read-only capture download/header parse would need an explicit, approved live procedure. |
| Do QTM version, C3D export, crops, or ranges affect results? | **Yes.** QTM docs confirm selected range controls export/playback. C3D headers can carry a separate first frame. Version/API behavior for the installed 2026.2 scripting host remains unverified. |
| Is `QTM_TIMELINE_FIRST_FRAME = 1` universal? | **No evidence supports that conclusion.** It must be treated as an application convention until verified per live measurement/API semantics. |

## 8. Safe verification plan (not executed)

When the QTM embedded bridge is intentionally started and a non-clinical test measurement is open, use only a read-only endpoint that reports:

1. active measurement identity;
2. `get_measured_range()` and `get_selected_range()` values;
3. `get_trace_range()` separately;
4. `get_frame_count()` and `get_frequency()`;
5. the current marker frame reported by the QTM UI and, where applicable, RT packet; and
6. the C3D first/last header frame from an explicitly exported/read-only capture copy.

Record the actual values at the first original frame, a cropped-range first frame, and a non-integer event time. Do not use `SetMeasuredRange`, event writes, trajectory writes, or any XML setting change in an audit.

## 9. Recommendations (no implementation performed)

1. Keep explicit names for `timeline_frame`, `sample_index`, `measurement_range_start`, `trace_range_start`, `c3d_first_frame`, and `event_time`; do not interchange them.
2. Do not use trace range as a first-frame identity. The current bridge's `First Frame` field should be considered ambiguous until redesigned after runtime verification.
3. For future implementation, make the conversion origin a verified per-measurement value and preserve it with every event/result payload. Do not silently default cropped measurements to 1.
4. Prefer event time for QTM transport where QTM stores events by time, but retain the verified source-frame mapping for display and C3D interoperability.
5. Run a controlled test measurement through the exact QTM 2026.2 embedded script configured by the project before changing frame conversion code.

## 10. Sources and commands

Official Qualisys sources reviewed:

- [Timeline control bar](https://docs.qualisys.com/qtm/content/qtm_user_interface/qtm_windows/timeline_control_bar.htm)
- [Export to C3D format](https://docs.qualisys.com/qtm/content/processing_measurement/export_to_c3d_format.htm)
- [Export to MAT format](https://docs.qualisys.com/qtm/content/processing_measurement/export_to_mat_format.htm)
- [QTM Real-time Server Protocol v1.28](https://docs.qualisys.com/qtm-rt-protocol/)
- [Qualisys QTM scripting repository](https://github.com/qualisys/qtm-scripting)
- [Qualisys Python RT SDK](https://github.com/qualisys/qualisys_python_sdk)

Read-only local commands included version/process/listener inspection, targeted `rg` searches and file reads, `Get-FileHash` for audited source files, and `ezc3d.c3d()` against one C3D. No command wrote to source, QTM, project data, settings, measurements, or events.

## 11. Verification and limitations

- The report did not exist before this audit and is the only created file.
- The audited source files were hash-read before report creation; no source edit command was issued.
- QTM was present, but no bridge listener was available. Therefore live timeline/API values, open measurement identity, range semantics, and frame-0 display behavior remain unverified.
- No external `qtm` module was imported from ordinary Python, no QTM terminal expression was run, and no RT command was sent.
- This audit deliberately does not recommend a code change until the controlled live verification above is completed.
