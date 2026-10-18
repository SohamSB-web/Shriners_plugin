"""Shared, guarded QTM event protocol. No file writes or QTM imports at import time."""
import os
from pathlib import Path
from app.services.frame_coordinates import frame_to_time, time_to_frame, sample_index_to_frame, FRAME_CONVENTION


def event_label(label):
    text = str(label).upper().replace(" ", "_").replace("-", "_")
    aliases = {"AUTO_RHS": "RSTRIKE", "AUTO_ROF": "ROFF", "AUTO_LHS": "LSTRIKE", "AUTO_LOF": "LOFF",
               "RIGHT_FOOT_STRIKE": "RSTRIKE", "LEFT_FOOT_STRIKE": "LSTRIKE",
               "RIGHT_FOOT_OFF": "ROFF", "LEFT_FOOT_OFF": "LOFF"}
    return aliases.get(text, text)


def event_signature(events):
    return sorted([[event_label(e["label"]), int(e["frame"])] for e in events])


def active_path(qtm):
    path = qtm.file.get_path()
    if not isinstance(path, str) or not Path(path).is_absolute() or Path(path).suffix.lower() != ".qtm":
        raise RuntimeError("QTM did not expose a saved measurement's full path")
    return os.path.normcase(str(Path(path).resolve()))


def guarded_event_command(qtm, event_api, timeline, command, args):
    def snapshot():
        path = active_path(qtm)
        frequency = timeline.get_frequency()
        raw = event_api.get_events()
        events = [{**e, "label": event_label(e["label"]),
                   "frame": time_to_frame(e["time"], frequency)} for e in raw
                  if event_label(e["label"]) in {"RSTRIKE", "ROFF", "LSTRIKE", "LOFF"}]
        if active_path(qtm) != path:
            raise RuntimeError("QTM measurement changed during event read")
        measured = timeline.get_measured_range()
        return {"measurement_path": path, "events": events, "frame_rate": frequency,
                "recording_start_frame": sample_index_to_frame(measured["start"]),
                "initial_frame_offset": measured["start"], "frame_convention": FRAME_CONVENTION,
                "total_frames": timeline.get_frame_count(), "persistent": False}, raw

    remote, raw = snapshot()
    if command == "GetEventSnapshot":
        return remote
    target = args.get("measurement_path")
    if not target or not Path(target).is_absolute() or os.path.normcase(str(Path(target).resolve())) != remote["measurement_path"]:
        raise RuntimeError("Exact patient/session/measurement path mismatch; events not written")
    if event_signature(remote["events"]) != args.get("expected_events"):
        raise RuntimeError("QTM Event Conflict: timeline changed before application")
    desired = args["events"]
    for e in desired:
        if event_label(e["label"]) not in {"RSTRIKE", "ROFF", "LSTRIKE", "LOFF"}:
            raise ValueError("Unsupported gait event label")
        frame_to_time(e["frame"], remote["frame_rate"])
    # Recheck the full identity before every mutation; leave unrelated QTM event types intact.
    for e in raw:
        if event_label(e["label"]) in {"RSTRIKE", "ROFF", "LSTRIKE", "LOFF"}:
            if active_path(qtm) != target:
                raise RuntimeError("QTM measurement changed before event deletion")
            event_api.delete_event(e["id"])
    for e in desired:
        if active_path(qtm) != target:
            raise RuntimeError("QTM measurement changed before event insertion")
        event_api.add_event({"label": event_label(e["label"]), "time": frame_to_time(e["frame"], remote["frame_rate"])})
    verified, _ = snapshot()
    if event_signature(verified["events"]) != event_signature(desired):
        raise RuntimeError("QTM event read-back failed; local revision retained")
    return verified  # The existing bridge has no verified measurement-save API.
