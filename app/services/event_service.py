# -*- coding: utf-8 -*-
"""
Event Service — utilities for inspecting and summarizing gait event detection results.

Loads and parses auto_event_{stem}_results.json produced by auto_event_trigger.py.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import sys
import re
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from app.services.frame_coordinates import (frame_to_time, frame_to_index, time_to_frame, normalize_saved_events, recording_start_frame, FRAME_CONVENTION, sample_index_to_frame, trace_event)
from app.services.event_store import EventStore, EventRevisionConflict

logger = logging.getLogger(__name__)


def normalize_trial_name(name: str | Path | None) -> str:
    """Normalize a trial name by removing path, extension, unsaved markers (*), and extra whitespace/separators."""
    if not name:
        return ""
    s = str(name).strip().lstrip("*").rstrip("*").strip()
    p = Path(s)
    stem = p.stem if p.suffix else s
    stem = stem.lstrip("*").rstrip("*").strip()
    return re.sub(r'[\s_\-]+', ' ', stem.lower()).strip()


def trial_names_match(name1: str | Path | None, name2: str | Path | None) -> bool:
    """Check if two trial names or filenames refer to the exact same trial (e.g. 'Dynamic 1' vs 'Dynamic 1.qtm')."""
    n1 = normalize_trial_name(name1)
    n2 = normalize_trial_name(name2)
    return bool(n1 and n2 and n1 == n2)


def _read_c3d_event_projection(path):
    """Read an existing projection during migration, without rewriting the recording."""
    if not path.is_file():
        return None
    try:
        import ezc3d
        c = ezc3d.c3d(str(path))
        group = c["parameters"].get("EVENT", {})
        labels = group.get("LABELS", {}).get("value", [])
        contexts = group.get("CONTEXTS", {}).get("value", [])
        times = group.get("TIMES", {}).get("value", [])
        if not labels:
            return None
        frequency = float(c["header"]["points"]["frame_rate"])
        events = []
        for i, label in enumerate(labels):
            if label in {"Foot Strike", "Foot Off"} and i < len(contexts):
                label = f"{contexts[i]} {label}"
            label = normalize_qtm_event_label(label)
            if label in {"RSTRIKE", "ROFF", "LSTRIKE", "LOFF"}:
                events.append({"label": label, "frame": time_to_frame(float(times[0][i]) * 60 + float(times[1][i]), frequency)})
        return {"events": events, "meta": {"frame_rate": frequency, "frame_convention": FRAME_CONVENTION,
                "recording_start_frame": sample_index_to_frame(c["header"]["points"]["first_frame"])}}
    except Exception:
        return None


def load_trial_events(session_dir: str | Path, trial_filename: str) -> Optional[Dict[str, Any]]:
    """
    Load auto-detected gait events for a dynamic trial from auto_event_<stem>_results.json.

    Parameters
    ----------
    session_dir : str or Path
        Directory containing the session.xml and trial files.
    trial_filename : str
        Filename of the dynamic trial (e.g. "Dynamic 1.qtm" or "Dynamic 1.c3d").

    Returns
    -------
    dict or None
        Parsed event structure or None if no results file exists.
    """
    s_dir = Path(session_dir)
    stem = Path(trial_filename).stem
    events_dir = s_dir / "Events"
    store = EventStore(s_dir)
    stored = store.read(trial_filename)

    # Search for matching results JSON in Events/ first, then session root (case-insensitive)
    candidates = [
        events_dir / f"auto_event_{stem}_results.json",
        events_dir / f"auto_event_{stem.lower()}_results.json",
        s_dir / f"auto_event_{stem}_results.json",
        s_dir / f"auto_event_{stem.lower()}_results.json",
    ]

    # Also search by glob if not exact match
    target_path: Optional[Path] = None
    for c in candidates:
        if c.is_file():
            target_path = c
            break

    if target_path is None:
        target_norm = normalize_trial_name(stem)
        search_dirs = [events_dir, s_dir] if events_dir.is_dir() else [s_dir]
        for d in search_dirs:
            for f in d.glob("auto_event_*_results.json"):
                m = re.match(r"^auto_event_(.+)_results$", f.stem, re.IGNORECASE)
                if m and normalize_trial_name(m.group(1)) == target_norm:
                    target_path = f
                    break
            if target_path:
                break

    if stored is not None:
        target_path = events_dir / f"auto_event_{stem}_results.json"
    c3d_source = None
    if stored is None:
        c3d_source = _read_c3d_event_projection(s_dir / f"{stem}.c3d")
        if target_path is None and c3d_source and c3d_source["events"]:
            normalized = normalize_saved_events(c3d_source["events"], c3d_source["meta"])
            stored = store.commit(trial_filename, {"events": normalized, "meta": c3d_source["meta"]},
                                  "legacy_c3d_import", enqueue=False, expected_revision=0)
            target_path = events_dir / f"auto_event_{stem}_results.json"
    if target_path is None or (stored is None and not target_path.is_file()):
        return None

    try:
        if stored is not None:
            data = stored["payload"]
        else:
            with open(target_path, "r", encoding="utf-8") as fp:
                data = json.load(fp)

        events_list: List[Dict[str, Any]] = data.get("events", [])
        meta: Dict[str, Any] = dict(data.get("meta", {}))
        events_list = normalize_saved_events(events_list, meta)
        meta["frame_convention"] = FRAME_CONVENTION
        meta["recording_start_frame"] = recording_start_frame(meta)
        if stored is None:
            conflicts = []
            for candidate in candidates:
                if candidate.is_file() and candidate.resolve() != target_path.resolve():
                    try:
                        other = json.loads(candidate.read_text(encoding="utf-8"))
                        if other.get("events") != data.get("events"):
                            conflicts.append(str(candidate))
                    except (OSError, ValueError):
                        conflicts.append(str(candidate))
            if conflicts:
                meta["migration_conflicts"] = conflicts
            if c3d_source:
                from app.services.qtm_event_protocol import event_signature
                if event_signature(c3d_source["events"]) != event_signature(events_list):
                    meta.setdefault("migration_conflicts", []).append(str(s_dir / f"{stem}.c3d"))
            stored = store.commit(trial_filename, {"events": events_list, "meta": meta},
                                  "legacy_import", enqueue=False, expected_revision=0)
        meta.update(event_revision=stored["revision"], event_sync_status=stored["sync_status"],
                    event_sync_error=stored["sync_error"], projection_error=stored["projection_error"],
                    intentional_deletion=stored["intentional_deletion"], provenance=stored["provenance"])
        if meta.get("migration_conflicts"):
            meta["event_sync_status"] = "QTM Conflict"

        # Compute counts by label
        r_hs = 0
        r_to = 0
        l_hs = 0
        l_to = 0
        for ev in events_list:
            lbl = ev.get("label", "").upper()
            if lbl == "RSTRIKE" or lbl == "AUTO_RHS":
                r_hs += 1
            elif lbl == "ROFF" or lbl == "AUTO_ROF":
                r_to += 1
            elif lbl == "LSTRIKE" or lbl == "AUTO_LHS":
                l_hs += 1
            elif lbl == "LOFF" or lbl == "AUTO_LOF":
                l_to += 1

        total = len(events_list)
        pairing_valid = meta.get("pairing_valid", True)
        filter_method = meta.get("filter_method", "temporal")
        zone_frames = meta.get("zone_frames", [0, 0])
        frame_rate = float(meta.get("frame_rate") or meta.get("frequency") or 100.0)
        initial_frame_offset = int(meta.get("initial_frame_offset", 0))

        return {
            "trial_filename": trial_filename,
            "filepath": str(target_path),
            "events": events_list,
            "meta": meta,
            "total_events": total,
            "r_hs": r_hs,
            "r_to": r_to,
            "l_hs": l_hs,
            "l_to": l_to,
            "pairing_valid": pairing_valid,
            "filter_method": filter_method,
            "zone_frames": zone_frames,
            "frame_rate": frame_rate,
            "initial_frame_offset": initial_frame_offset,
            "summary_text": f"{total} Events (R: {r_hs + r_to}, L: {l_hs + l_to})",
        }
    except Exception as e:
        logger.warning("Error reading event results file %s: %s", target_path, e)
        return None


def get_session_events_summary(
    session_dir: str | Path,
    trial_filenames: List[str],
) -> Dict[str, Any]:
    """
    Summarize event labeling status across all dynamic trials in a session.
    """
    total_trials = len(trial_filenames)
    labeled_trials = 0
    total_events = 0
    trials_data: Dict[str, Optional[Dict[str, Any]]] = {}

    for fname in trial_filenames:
        ev_data = load_trial_events(session_dir, fname)
        trials_data[fname] = ev_data
        if ev_data is not None and ev_data.get("total_events", 0) > 0:
            labeled_trials += 1
            total_events += ev_data.get("total_events", 0)

    return {
        "total_trials": total_trials,
        "labeled_trials": labeled_trials,
        "total_events": total_events,
        "all_labeled": (total_trials > 0 and labeled_trials == total_trials),
        "trials_data": trials_data,
    }


def check_event_pairing(events: List[Dict[str, Any]]) -> bool:
    """Check if gait strike and toe-off events alternate correctly per side."""
    if not events:
        return True
    sorted_evs = sorted(events, key=lambda x: int(x.get("frame", 0)))
    for side in ("R", "L"):
        side_evs = [
            e.get("label", "").upper()
            for e in sorted_evs
            if (e.get("label", "").upper().startswith(side) or f"AUTO_{side}" in e.get("label", "").upper())
        ]
        for i in range(len(side_evs) - 1):
            curr = side_evs[i]
            nxt = side_evs[i + 1]
            curr_is_strike = "STRIKE" in curr or "HS" in curr
            nxt_is_strike = "STRIKE" in nxt or "HS" in nxt
            curr_is_off = "OFF" in curr or "OF" in curr
            nxt_is_off = "OFF" in nxt or "OF" in nxt
            if (curr_is_strike and nxt_is_strike) or (curr_is_off and nxt_is_off):
                return False
    return True


def save_trial_events(
    session_dir: str | Path,
    trial_filename: str,
    events_list: List[Dict[str, Any]],
    meta: Optional[Dict[str, Any]] = None,
    *, provenance: str = "manual_edit", expected_revision: Optional[int] = None, enqueue: bool = True,
) -> Dict[str, Any]:
    """
    Save manually edited or newly added gait events to auto_event_<stem>_results.json.
    """
    s_dir = Path(session_dir)
    events_dir = s_dir / "Events"
    events_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(trial_filename).stem

    # Target path inside Events/ subfolder
    target_path = events_dir / f"auto_event_{stem}_results.json"
    candidates = [
        events_dir / f"auto_event_{stem}_results.json",
        events_dir / f"auto_event_{stem.lower()}_results.json",
    ]
    for c in candidates:
        if c.is_file():
            target_path = c
            break

    offset = int(meta.get("initial_frame_offset", 0)) if meta else 0
    freq = float(meta.get("frame_rate") or meta.get("frequency") or 100.0) if meta else 100.0

    # Standardize & sort events, preserving rich timeline fields
    clean_events: List[Dict[str, Any]] = []
    for ev in sorted(events_list, key=lambda x: int(x.get("frame", 0))):
        f = int(ev.get("frame", 0))
        if f < 1 or f != float(ev.get("frame", 0)):
            raise ValueError("Events must use whole absolute QTM timeline frames")
        lbl = str(ev.get("label", "")).strip().upper()
        if not lbl:
            continue
        rel_f = frame_to_index(f, recording_start_frame(meta or {}))
        time_s = frame_to_time(f, freq)
        side = ev.get("side") or ("R" if "R" in lbl else ("L" if "L" in lbl else ""))
        etype = ev.get("type") or ("STRIKE" if ("STRIKE" in lbl or "HS" in lbl) else ("OFF" if ("OFF" in lbl or "OF" in lbl) else ""))
        clean_events.append({
            **ev,
            "frame": f,
            "label": lbl,
            "time": time_s,
            "relative_frame": int(rel_f),
            "side": side,
            "type": etype,
        })

    # Recalculate metrics
    r_hs, r_to, l_hs, l_to = 0, 0, 0, 0
    for ev in clean_events:
        lbl = ev["label"]
        if lbl in ("RSTRIKE", "AUTO_RHS"):
            r_hs += 1
        elif lbl in ("ROFF", "AUTO_ROF"):
            r_to += 1
        elif lbl in ("LSTRIKE", "AUTO_LHS"):
            l_hs += 1
        elif lbl in ("LOFF", "AUTO_LOF"):
            l_to += 1

    pairing_valid = check_event_pairing(clean_events)
    if meta is None:
        meta = {}
    meta = dict(meta)
    meta["pairing_valid"] = pairing_valid
    meta["manual_override"] = provenance != "auto_label"
    meta["total_events"] = len(clean_events)
    meta["frame_rate"] = freq
    meta["initial_frame_offset"] = offset
    meta["frame_convention"] = FRAME_CONVENTION
    meta["recording_start_frame"] = recording_start_frame(meta)

    data = {
        "events": clean_events,
        "meta": meta,
    }

    store = EventStore(s_dir)
    previous = store.read(trial_filename)
    if provenance == "auto_label" and not clean_events and previous and previous["payload"]["events"]:
        raise ValueError("Detection returned no events; the previous saved revision was preserved")
    if expected_revision is None and meta.get("event_revision") is not None:
        expected_revision = int(meta["event_revision"])
    stored = store.commit(trial_filename, data, provenance, enqueue=enqueue, expected_revision=expected_revision,
                          deleted=not clean_events and provenance in {"manual_edit", "manual_delete", "qtm_accepted"})
    project_trial_events(s_dir, trial_filename, stored["revision"])
    return load_trial_events(s_dir, trial_filename)


def project_trial_events(session_dir, trial_filename, revision):
    """Recoverable projections: retain the committed DB revision even if an export fails."""
    store = EventStore(session_dir)
    with store.transaction() as db:
        stored = store.read(trial_filename, db)
        if stored is None or stored["revision"] != revision:
            raise EventRevisionConflict("Projection belongs to a superseded event revision")
        target = Path(session_dir) / "Events" / f"auto_event_{Path(trial_filename).stem}_results.json"
        temporary = None
        errors = []
        try:
            if target.is_symlink():
                raise ValueError("Event JSON destination is a symlink")
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(stored["payload"], stream, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            if json.loads(temporary.read_text(encoding="utf-8")) != stored["payload"]:
                raise ValueError("JSON event read-back failed")
            os.replace(temporary, target)
        except (OSError, ValueError) as error:
            errors.append(str(error))
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        c3d = Path(session_dir) / f"{Path(trial_filename).stem}.c3d"
        meta = stored["payload"]["meta"]
        if c3d.is_file() and not write_events_to_c3d(c3d, stored["payload"]["events"],
                                                  frame_rate=meta["frame_rate"], offset=meta.get("initial_frame_offset", 0)):
            errors.append("C3D event export failed; committed events remain in SQLite")
        db.execute("UPDATE trials SET projection_error=? WHERE id=? AND revision=?",
                   ("; ".join(errors), stored["id"], revision))
        return not errors


def get_qtm_active_file() -> Optional[str]:
    """
    Return the filename/trial name currently open in Qualisys Track Manager (QTM),
    or None if QTM is not running or no measurement is open.
    """
    try:
        import ctypes
        from ctypes import wintypes

        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible

        titles = []
        def foreach_window(hwnd, lParam):
            if IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buff, length + 1)
                    t = buff.value
                    if "Qualisys Track Manager" in t:
                        titles.append(t)
            return True

        EnumWindows(EnumWindowsProc(foreach_window), 0)
        for t in titles:
            parts = t.split(" - Qualisys Track Manager")
            if len(parts) > 1 and parts[0].strip():
                return parts[0].strip()
    except Exception:
        pass
    return None


def write_events_to_c3d(
    c3d_path: str | Path,
    events: List[Any],
    frame_rate: float = 120.0,
    offset: int = 0,
) -> bool:
    """
    Write gait events directly into the C3D file's EVENT parameter group.

    Parameters
    ----------
    c3d_path : str or Path
        Path to the .c3d file
    events : list
        List of dicts or tuples representing events.
    frame_rate : float
        Capture frequency in Hz.
    offset : int
        Initial frame offset.

    Returns
    -------
    bool
        True if successfully written, False otherwise.
    """
    p = Path(c3d_path)
    if not p.is_file():
        return False
    try:
        import ezc3d
        import numpy as np

        c = ezc3d.c3d(str(p))
        N = len(events)
        times = np.zeros((2, N), dtype=float)
        contexts = []
        labels = []
        descriptions = [''] * N
        subjects = [''] * N
        icon_ids = [0] * N
        generic_flags = [0] * N


        for i, ev in enumerate(events):
            if isinstance(ev, (list, tuple)):
                f, lbl = ev[0], str(ev[1]).strip().upper()
                t = frame_to_time(f, frame_rate)
            elif isinstance(ev, dict):
                f = int(ev.get('frame', 0))
                lbl = str(ev.get('label', '')).strip().upper()
                t = frame_to_time(f, frame_rate)
            else:
                continue

            times[0, i] = int(t // 60)
            times[1, i] = t % 60
            labels.append(lbl)
            if lbl.startswith('R') or 'RIGHT' in lbl:
                contexts.append('Right')
            elif lbl.startswith('L') or 'LEFT' in lbl:
                contexts.append('Left')
            else:
                contexts.append('General')

        c.add_parameter('EVENT', 'USED', N)
        c.add_parameter('EVENT', 'TIMES', times)
        c.add_parameter('EVENT', 'CONTEXTS', contexts)
        c.add_parameter('EVENT', 'LABELS', labels)
        c.add_parameter('EVENT', 'DESCRIPTIONS', descriptions)
        c.add_parameter('EVENT', 'SUBJECTS', subjects)
        c.add_parameter('EVENT', 'ICON_IDS', icon_ids)
        c.add_parameter('EVENT', 'GENERIC_FLAGS', generic_flags)
        if p.is_symlink():
            raise ValueError("C3D event projection must not follow a symlink")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=p.parent, suffix=".c3d", delete=False) as stream:
                temporary = Path(stream.name)
            c.write(str(temporary))
            verified = ezc3d.c3d(str(temporary))["parameters"]["EVENT"]
            if list(verified["LABELS"]["value"]) != labels or not np.allclose(verified["TIMES"]["value"], times):
                raise ValueError("C3D event projection read-back failed")
            os.replace(temporary, p)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        return True
    except Exception as e:
        logger.warning("Could not write events to C3D file %s: %s", p, e)
        return False


def send_events_to_qtm(events_list, frame_rate=100.0, offset=0, port=50052, trial_filename=None, session_dir=None):
    """Explicit push of an already committed revision; never target a name alone."""
    from app.services.event_sync_service import push_saved_events
    from app.services.qtm_event_protocol import event_signature
    if not trial_filename:
        return False, "An exact selected trial is required"
    if session_dir is None:
        if not trial_filename or not Path(trial_filename).is_absolute():
            return False, "Exact session/measurement path is required; events remain saved locally"
        session_dir = Path(trial_filename).parent
    info = load_trial_events(session_dir, Path(trial_filename).name)
    if info is None or event_signature(info["events"]) != event_signature(events_list):
        return False, "Commit this event set locally before pushing it to QTM"
    return push_saved_events(session_dir, Path(trial_filename).name, port)


def normalize_qtm_event_label(raw_label: str) -> str:
    """Normalize user-created or QTM-native event labels into standard clinical tokens."""
    lbl = str(raw_label).strip().upper().replace(" ", "_").replace("-", "_")

    is_right = (
        "RIGHT" in lbl
        or lbl.startswith("R_")
        or lbl.startswith("RSTRIKE")
        or lbl.startswith("ROFF")
        or lbl in ("RHS", "ROF")
        or "AUTO_R" in lbl
    )
    is_left = (
        "LEFT" in lbl
        or lbl.startswith("L_")
        or lbl.startswith("LSTRIKE")
        or lbl.startswith("LOFF")
        or lbl in ("LHS", "LOF")
        or "AUTO_L" in lbl
    )

    is_strike = any(k in lbl for k in ["STRIKE", "HEEL", "HS"])
    is_off = any(k in lbl for k in ["OFF", "TOE", "ROF", "LOF", "_OF"])

    if is_right and is_strike:
        return "RSTRIKE"
    if is_right and is_off:
        return "ROFF"
    if is_left and is_strike:
        return "LSTRIKE"
    if is_left and is_off:
        return "LOFF"

    # Fallback to direct tokens if already normalized
    if lbl in ("RSTRIKE", "AUTO_RHS"):
        return "RSTRIKE"
    if lbl in ("ROFF", "AUTO_ROF"):
        return "ROFF"
    if lbl in ("LSTRIKE", "AUTO_LHS"):
        return "LSTRIKE"
    if lbl in ("LOFF", "AUTO_LOF"):
        return "LOFF"

    return str(raw_label).strip().upper()


def fetch_events_from_qtm(port=50052, trial_filename=None, default_frame_rate=None, session_dir=None):
    """Read-only, full-measurement snapshot from the guarded bridge protocol."""
    from app.services.event_sync_service import event_rpc
    from app.services.event_store import measurement_path
    try:
        remote = event_rpc("GetEventSnapshot", port=port)
        if trial_filename:
            folder = session_dir or (Path(trial_filename).parent if Path(trial_filename).is_absolute() else None)
            if folder is None or remote["measurement_path"] != measurement_path(folder, trial_filename):
                return False, "QTM full session/measurement identity does not match", remote["measurement_path"], [], {}
        meta = {key: value for key, value in remote.items() if key != "events"}
        events = normalize_saved_events(remote["events"], meta)
        return True, f"Retrieved {len(events)} events", remote["measurement_path"], events, meta
    except Exception as error:
        return False, str(error), None, [], {}


def sync_qtm_events_to_session(session_dir, trial_filenames=None, port=50052, force=False):
    """Observe safely; only explicitly authorized outbox revisions may write to QTM."""
    from app.services.event_sync_service import observe_session_events
    folder = Path(session_dir)
    trials = trial_filenames or [p.name for p in folder.glob("*.qtm")]
    return observe_session_events(folder, trials, port, force)
