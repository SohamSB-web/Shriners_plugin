# QTM Events Reappear After Deletion — Read-Only Audit

**Audit date:** 2026-10-14  
**Project:** `C:\Users\ADMIN\Music\Shriners_Plugin`  
**Scope:** Source/process inspection only. No QTM command was sent; no event, measurement, session, or source file was changed. This report is the only file created.

## 1. Executive summary

The events are restored by the **Shriners application**, not by QTM itself and not merely because the gRPC bridge is running.

The visible `DynamicAnalysisPage` starts a QTimer at a 1,200 ms interval when a session loads and restarts it when the page is shown. Every tick calls `sync_qtm_events_to_session(..., force=False)`. When that function sees an empty QTM event list for the active matching trial but finds non-empty stored auto-label results, it intentionally calls `send_events_to_qtm()` to repopulate QTM. That function sends `ClearEvents` followed by `SetEvents`; the QTM bridge then calls `qtm_event.add_event()` once for each stored event.

This directly explains why **Remove All Events** in QTM appears to work and then events return shortly afterwards: the next poll sees an empty timeline and treats it as a condition to restore cached events. The expected delay is at most approximately 1.2 seconds while Dynamic Analysis is visible for the session (plus any active gRPC work).

## 2. Runtime observations

| Endpoint | Current state | Owning process | Meaning |
|---|---|---|---|
| TCP 50051 | Listening | `python.exe app.py` (PID 26924) | Application-side gRPC service |
| TCP 50052 | Listening | `QTM.exe` (PID 7316) | QTM embedded script bridge |

The current project declares 50051 as the application-side port and 50052 as the QTM-side script port in both bridge copies. A listener accepts requests; it does not itself schedule an event write. The application timer is the recurring writer trigger.

## 3. Confirmed event storage

Auto-labeling persists its results before it writes to the live QTM timeline:

| Location | Lines | Behavior |
|---|---:|---|
| `Gait-lab-Vicon-to-QTM/auto_event_trigger.py` | 297-332 | Creates `Events/auto_event_<trial>_results.json` with events, frame/time metadata, and `qtm_timeline_synced=False`. |
| same | 339-353 | Writes the events into the corresponding C3D file when present. |
| `app/services/event_service.py` | 41-142 | `load_trial_events()` loads the JSON sidecar from `Events/` or legacy session-root locations. |
| `app/services/event_service.py` | 204-313 | `save_trial_events()` persists event data when application synchronization updates it. |

Therefore the GUI has a durable local cache of auto-label results after auto-labeling finishes. Deleting events only in QTM does not remove that cache.

## 4. Complete event-writing call chain

### Initial auto-label run

```text
DynamicAnalysisPage._start_next_processing()
  app/ui/pages/dynamic_analysis_page.py:1166-1182
    ↓ starts ProcessingService.run_auto_event_labeling()
GaitProcessingService.run_auto_event_labeling()
  app/services/processing_service.py:258-263
    ↓ runs auto_event_trigger.py in a QThread worker
auto_event_trigger.process_trial()
  Gait-lab-Vicon-to-QTM/auto_event_trigger.py:297-332
    ↓ writes cached auto_event_<trial>_results.json
auto_event_trigger.process_trial()
  lines 371-409
    ↓ if the matching trial is currently open in QTM:
    ↓ sends ClearEvents, then one SetEvent per detected event
gapi.SetEvent()
  Gait-lab-Vicon-to-QTM/gapi.py:99-130
    ↓ gRPC command to localhost:50052
QtmCommandServicer.SendCommandToQtm("SetEvent")
  QTM-GRPC/tools/Py3_staticmain.py:165-189
    ↓ qtm_event.add_event(...)
QTM timeline shows the events
```

This path runs once for each auto-label job. It is not a retry loop.

### Reappearance after QTM-side Remove All Events

```text
DynamicAnalysisPage QTimer every 1.2 s
  app/ui/pages/dynamic_analysis_page.py:119-121, 649-652, 888-927
    ↓ _poll_qtm_events_sync()
sync_qtm_events_to_session(..., force=False)
  app/services/event_service.py:786-805
    ↓ fetches current QTM timeline events
QTM reports zero events while cached JSON has events
  app/services/event_service.py:842-864
    ↓ explicit auto-population branch
send_events_to_qtm(cached events)
  app/services/event_service.py:867-873
    ↓ sends ClearEvents then bulk SetEvents
send_events_to_qtm()
  app/services/event_service.py:433-537
    ↓ gRPC command to localhost:50052
QtmCommandServicer.SendCommandToQtm("SetEvents")
  QTM-GRPC/tools/Py3_staticmain.py:191-223
    ↓ qtm_event.add_event(...) for each cached event
QTM timeline shows the events again
```

The decisive branch is `event_service.py:856-878`:

```python
if len(clean_events) == 0 and len(existing_events) > 0:
    # ...
    if not force or not is_synced:
        push_ok, push_msg = send_events_to_qtm(...)
```

The background timer always calls with `force=False` (`dynamic_analysis_page.py:910-915`), so `not force` is always true. The stored `qtm_timeline_synced` flag does not prevent restoration during background polling.

## 5. Event-writing paths

| Writer | File and lines | Trigger | Repeats? | Cache / post-auto-label behavior |
|---|---|---|---|---|
| Auto-label direct writer | `auto_event_trigger.py:371-409` | Auto-label job completes while the matching QTM trial is open | Once per job; one `SetEvent` per detected event | Writes JSON and C3D first; can write to QTM after auto-labeling has completed. |
| Background auto-population | `event_service.py:856-878` | QTM returns no events and stored JSON has events | Yes, via the 1.2 s page timer | **Confirmed reappearance path.** |
| Manual Push to QTM | `dynamic_analysis_page.py:772-808` | User clicks the per-trial push action | User initiated | Reads stored JSON then calls `send_events_to_qtm()`. |
| Manual dialog Save and Update QTM | `event_details_dialog.py:1191-1229` | User saves edited events | User initiated | Saves JSON, then sends events to QTM. |
| Direct QTM bridge single write | `Py3_staticmain.py:165-189` | Receives `SetEvent` | One per inbound request | No local cache or timer. |
| Direct QTM bridge bulk write | `Py3_staticmain.py:191-223` | Receives `SetEvents` | One per inbound request | No local cache or timer. |

Both `QTM-GRPC/tools/Py3_staticmain.py` and `Gait-lab-Vicon-to-QTM/QTM_GRPC/tools/Py3_staticmain.py` contain materially equivalent handlers. The configured application default is `QTM-GRPC`; which copy QTM loaded cannot be proved from static inspection alone. This does not alter the confirmed application-side reappearance path.

## 6. Background services, timers, and watchers

### Dynamic Analysis QTimer — confirmed recurring trigger

`DynamicAnalysisPage.__init__` creates `_qtm_sync_timer`, sets it to 1,200 ms, and connects it to `_poll_qtm_events_sync()` at lines 113-121. `load_session()` starts it and schedules an initial sync at lines 649-652. `showEvent()` restarts it if needed at lines 998-1002; `hideEvent()` stops it at lines 1004-1007. `clear_session()` stops it at lines 526-542.

The timer does not run merely because the application process exists. It runs while a session is loaded and the Dynamic Analysis page is visible. A user can therefore observe restoration shortly after entering or returning to this page.

### File-system watcher — not an event writer

`QFileSystemWatcher` watches auto-event JSON files at `dynamic_analysis_page.py:113-117` and 929-996. Its callbacks reload JSON only to update row status/badges. They do not call `send_events_to_qtm()` or `SetEvents`.

### Processing QThread — one job, not recurring synchronization

`GaitProcessingService.run_auto_event_labeling()` creates a worker thread for a single script invocation (`processing_service.py:258-313`). It is the initial event producer, but static inspection found no retry/reconnection loop that reruns it after QTM event deletion.

### gRPC servers — passive request handlers

The QTM bridge starts a `grpc.server(...)` on 50052 at `Py3_staticmain.py:262-271`. Its `SetEvent` and `SetEvents` branches write only after an inbound command. No timer, polling loop, QTM event-list callback, or automatic reinsert operation exists in the bridge handler.

## 7. QTM startup script analysis

`QTM-GRPC/startup_tools.py:45-87` and `Gait-lab-Vicon-to-QTM/QTM_GRPC/startup_tools.py:40-82` discover modules with `menu_priority > 0` and call each module's `add_menu()`.

`Py3_staticmain.py:622-640` marks itself `menu_priority = 1`. Its `add_menu()` starts the 50052 gRPC server thread if that module's `qtm_grpc_server_thread` is absent or not alive. It registers menu commands, including a read-only `getEvents()` command, but it does not call `SetEvent`, `SetEvents`, auto-labeling, or synchronization on startup.

There are two copies of the startup/bridge code in the repository. If both scripts are registered in QTM, they could attempt to bind port 50052, but a second listener cannot normally coexist on that same port. The audit found one live QTM listener only. Static evidence does not show duplicate bridge instances as the reason for reappearance.

## 8. Hypothesis evaluation

| Hypothesis | Result | Evidence |
|---|---|---|
| A — Persistent gRPC event synchronization | **Confirmed, application-side.** | Dynamic Analysis timer polls every 1.2 s and invokes the auto-population branch at `event_service.py:856-878`. The gRPC server alone is passive. |
| B — Automatic retry mechanism | **Not supported.** | `send_events_to_qtm()` makes one request; no retry loop was found. The repeated action is the timer-driven synchronization, not a transport retry. |
| C — QTM startup-script callback | **Not supported.** | Startup registers menus and starts the bridge server; it has no event-list change callback or event-writing startup action. |
| D — Dynamic Analysis refresh | **Confirmed in the broader sense.** | Loading/showing Dynamic Analysis starts/restarts the timer; the initial check is scheduled after 400 ms. File watcher refresh itself does not write. |
| E — Duplicate bridge instances | **Unproven and unlikely as primary cause.** | There are duplicate source copies, but one listener was observed and the source already independently proves a periodic writer. |
| F — Other event-producing mechanism | **Possible but not needed to explain this behavior.** | Auto-label script and manual actions can write, but the background auto-population branch is sufficient to reproduce the reported immediate return. No other QTM plugin was inspected. |

## 9. Direct answers

**Q1. Is the issue caused simply by the gRPC server running continuously?**  
No. The bridge is continuously available but only writes after `SetEvent` or `SetEvents`. The recurring application timer supplies that request.

**Q2. Is any background task repeatedly calling SetEvents?**  
Yes. `_qtm_sync_timer` calls `_poll_qtm_events_sync()` every 1.2 seconds. When QTM is empty and cached results are non-empty, `sync_qtm_events_to_session()` calls `send_events_to_qtm()`, which sends `SetEvents`.

**Q3. Does QTM automatically restore events, or does our Shriners application restore them?**  
The Shriners application restores them. QTM receives a bulk `SetEvents` request and performs the requested `qtm_event.add_event()` calls.

**Q4. What exact function causes the events to reappear?**  
`app.services.event_service.sync_qtm_events_to_session()` at lines 856-878, invoked by `DynamicAnalysisPage._poll_qtm_events_sync()` at lines 888-927. The direct write function is `send_events_to_qtm()` at lines 433-537.

**Q5. What is the smallest safe change that would prevent this without breaking auto-labeling?**  
Do not implement it until reviewed. The narrowest candidate is to remove/disable only the background branch that calls `send_events_to_qtm()` when QTM reports zero events (`event_service.py:856-878`) while preserving manual Push, dialog Save and Update QTM, and the single post-auto-label write. A reviewed implementation must define whether an empty QTM timeline means intentional user deletion or a transient/unavailable read before changing this behavior.

## 10. Remaining uncertainties and safe diagnostic plan

Static inspection establishes the causal path but does not prove which request arrived in the user's specific live incident. A safe observation plan, requiring approval before implementation, is:

1. Add temporary, read-only structured log records at the entry of `send_events_to_qtm()` and QTM `SendCommandToQtm()` containing command name, active trial, event count, caller context, and process ID. Do not log patient values or event content.
2. Observe whether `SetEvents` follows QTM's manual Remove All Events and correlate it with the 1.2-second timer.
3. Close or hide Dynamic Analysis without changing QTM data, then observe whether requests stop; `hideEvent()` is expected to stop the timer.
4. Review the QTM scripting configuration to identify whether one or both bridge startup scripts are registered, without executing menu commands.
5. Test any future change only on a non-clinical copy of a measurement.

## 11. Audit verification

- No source code was edited.
- No gRPC, REST, QTM UI, or QTM scripting command was sent.
- No QTM event was deleted, inserted, saved, or modified.
- No service was started, stopped, or restarted.
- No patient/session/measurement data was accessed beyond process/listener metadata and source paths.
- The only created file is this audit report.
