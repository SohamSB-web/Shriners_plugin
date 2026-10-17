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
from typing import Any, Dict, List, Optional, Tuple

from app.services.frame_coordinates import (frame_to_time, frame_to_index, time_to_frame, normalize_saved_events, recording_start_frame, FRAME_CONVENTION, sample_index_to_frame, trace_event)

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

    if target_path is None or not target_path.is_file():
        return None

    try:
        with open(target_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        events_list: List[Dict[str, Any]] = data.get("events", [])
        meta: Dict[str, Any] = dict(data.get("meta", {}))
        events_list = normalize_saved_events(events_list, meta)
        meta["frame_convention"] = FRAME_CONVENTION
        meta["recording_start_frame"] = recording_start_frame(meta)

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
        lbl = str(ev.get("label", "")).strip().upper()
        if not lbl:
            continue
        rel_f = frame_to_index(f, recording_start_frame(meta or {}))
        time_s = frame_to_time(f, freq)
        side = ev.get("side") or ("R" if "R" in lbl else ("L" if "L" in lbl else ""))
        etype = ev.get("type") or ("STRIKE" if ("STRIKE" in lbl or "HS" in lbl) else ("OFF" if ("OFF" in lbl or "OF" in lbl) else ""))
        clean_events.append({
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
    meta["manual_override"] = True
    meta["total_events"] = len(clean_events)
    meta["frame_rate"] = freq
    meta["initial_frame_offset"] = offset
    meta["frame_convention"] = FRAME_CONVENTION
    meta["recording_start_frame"] = recording_start_frame(meta)

    data = {
        "events": clean_events,
        "meta": meta,
    }

    with open(target_path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2)

    # Clean up obsolete loose JSON in session root if present
    for legacy_name in [f"auto_event_{stem}_results.json", f"auto_event_{stem.lower()}_results.json"]:
        legacy_path = s_dir / legacy_name
        if legacy_path.is_file() and legacy_path.resolve() != target_path.resolve():
            try:
                legacy_path.unlink()
            except OSError:
                pass

    # Also write events directly into the trial's .c3d file if it exists
    c3d_candidates = [
        s_dir / f"{stem}.c3d",
        s_dir / f"{stem.lower()}.c3d",
    ]
    for c3d_cand in c3d_candidates:
        if c3d_cand.is_file():
            write_events_to_c3d(c3d_cand, clean_events, frame_rate=freq, offset=offset)
            break

    total = len(clean_events)
    return {
        "trial_filename": trial_filename,
        "filepath": str(target_path),
        "events": clean_events,
        "meta": meta,
        "total_events": total,
        "r_hs": r_hs,
        "r_to": r_to,
        "l_hs": l_hs,
        "l_to": l_to,
        "pairing_valid": pairing_valid,
        "filter_method": meta.get("filter_method", "manual"),
        "zone_frames": meta.get("zone_frames", [0, 0]),
        "frame_rate": freq,
        "initial_frame_offset": offset,
        "summary_text": f"{total} Events (R: {r_hs + r_to}, L: {l_hs + l_to})",
    }


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
        c.write(str(p))
        return True
    except Exception as e:
        logger.warning("Could not write events to C3D file %s: %s", p, e)
        return False


def send_events_to_qtm(
    events_list: List[Dict[str, Any]],
    frame_rate: float = 100.0,
    offset: int = 0,
    port: int = 50052,
    trial_filename: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Write gait events directly to Qualisys Track Manager (QTM) timeline via gRPC.

    Parameters
    ----------
    events_list : list of dicts with 'frame' and 'label'
    frame_rate : capture frequency in Hz
    offset : initial frame offset
    port : QTM gRPC port (default 50052)
    trial_filename : optional filename of the trial (e.g. 'Dynamic 1.qtm').
        If provided, verifies that QTM currently has this trial open before
        modifying the QTM timeline to prevent cross-trial contamination.

    Returns
    -------
    tuple of (success: bool, message: str)
    """
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            is_open = (s.connect_ex(('127.0.0.1', port)) == 0)
    except Exception:
        is_open = False

    # Verify that QTM currently has this trial open before sending to live timeline
    if trial_filename:
        active_qtm_file = get_qtm_active_file()
        if active_qtm_file:
            if not trial_names_match(trial_filename, active_qtm_file):
                return False, (
                    f"QTM currently has '{active_qtm_file}' open, not '{trial_filename}'. "
                    f"Live timeline update skipped to avoid cross-trial contamination. "
                    f"Events are safely saved inside {trial_filename}'s file."
                )

    if not is_open:
        return False, f"QTM server not reachable on port {port}. Changes saved locally."

    try:
        from app.services.settings_service import SettingsService
        cfg_qtm = SettingsService().load_app_settings().qtm_grpc_location
        if cfg_qtm and Path(cfg_qtm).is_dir():
            qtm_dir = str(Path(cfg_qtm).resolve())
        else:
            cand1 = Path(__file__).resolve().parent.parent.parent / "QTM-GRPC"
            cand2 = Path(__file__).resolve().parent.parent.parent / "Gait-lab-Vicon-to-QTM" / "QTM_GRPC"
            if cand1.is_dir():
                qtm_dir = str(cand1)
            elif cand2.is_dir():
                qtm_dir = str(cand2)
            else:
                qtm_dir = str(cand1)
        if qtm_dir not in sys.path:
            sys.path.insert(0, qtm_dir)
        import grpc
        import qtm_data_transfer_pb2
        import qtm_data_transfer_pb2_grpc

        bulk_events = []
        for ev in sorted(events_list, key=lambda x: int(x.get("frame", 0))):
            f = int(ev.get("frame", 0))
            lbl = str(ev.get("label", "")).strip().upper()
            if not lbl:
                continue
            time_sec = frame_to_time(f, frame_rate)
            trace_event("application_send", lbl, f, frame_rate, sample_index_to_frame(offset))
            bulk_events.append({"label": lbl, "time": time_sec, "frame": f, "frame_convention": FRAME_CONVENTION})

        with grpc.insecure_channel(f"localhost:{port}") as channel:
            stub = qtm_data_transfer_pb2_grpc.QtmTkinterBridgeStub(channel)

            # Optional: attempt ClearEvents for this trial if available
            try:
                clear_args = {"trial_name": trial_filename} if trial_filename else {}
                clear_req = qtm_data_transfer_pb2.CommandToQtm(
                    command_name="ClearEvents",
                    command_args_json=json.dumps(clear_args),
                )
                stub.SendCommandToQtm(clear_req, timeout=2)
            except Exception:
                pass

            payload_data = {"events": bulk_events}
            if trial_filename:
                payload_data["trial_name"] = str(trial_filename)
            payload = json.dumps(payload_data)
            req = qtm_data_transfer_pb2.CommandToQtm(
                command_name="SetEvents",
                command_args_json=payload,
            )
            response = stub.SendCommandToQtm(req, timeout=5)
            msg = getattr(response, "message", "Events sent")
            ok = getattr(response, "success", True)
            return ok, f"QTM: {msg}"
    except Exception as e:
        logger.warning("Error communicating with QTM: %s", e)
        return False, f"QTM gRPC error: {e}"


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


def fetch_events_from_qtm(
    port: int = 50052,
    trial_filename: Optional[str] = None,
    default_frame_rate: Optional[float] = None,
    session_dir: Optional[str | Path] = None,
) -> Tuple[bool, str, Optional[str], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fetch live gait events directly from Qualisys Track Manager (QTM) timeline over gRPC.

    Parameters
    ----------
    port : int
        QTM gRPC server port (default 50052).
    trial_filename : optional str
        If provided, checks if the active QTM trial matches this filename.
    default_frame_rate : optional float
        Fallback frame rate if QTM payload does not specify frequency.
    session_dir : optional str | Path
        Directory containing trial files for C3D frequency resolution.

    Returns
    -------
    tuple of (success: bool, message: str, active_trial: str | None, events: list, meta: dict)
    """
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.05)
            is_open = (s.connect_ex(('127.0.0.1', port)) == 0)
    except Exception:
        is_open = False

    if not is_open:
        return False, f"QTM server not reachable on port {port}.", None, [], {}

    # Get active trial name from OS window or fallback
    active_trial = get_qtm_active_file()

    try:
        from app.services.settings_service import SettingsService
        cfg_qtm = SettingsService().load_app_settings().qtm_grpc_location
        if cfg_qtm and Path(cfg_qtm).is_dir():
            qtm_dir = str(Path(cfg_qtm).resolve())
        else:
            cand1 = Path(__file__).resolve().parent.parent.parent / "QTM-GRPC"
            cand2 = Path(__file__).resolve().parent.parent.parent / "Gait-lab-Vicon-to-QTM" / "QTM_GRPC"
            if cand1.is_dir():
                qtm_dir = str(cand1)
            elif cand2.is_dir():
                qtm_dir = str(cand2)
            else:
                qtm_dir = str(cand1)
        if qtm_dir not in sys.path:
            sys.path.insert(0, qtm_dir)
        import grpc
        import qtm_data_transfer_pb2
        import qtm_data_transfer_pb2_grpc

        with grpc.insecure_channel(f"localhost:{port}") as channel:
            stub = qtm_data_transfer_pb2_grpc.QtmTkinterBridgeStub(channel)

            # 1. Query active measurement if not detected via window
            if not active_trial:
                try:
                    req_active = qtm_data_transfer_pb2.CommandToQtm(command_name="GetActiveMeasurement", command_args_json="{}")
                    resp_active = stub.SendCommandToQtm(req_active, timeout=2)
                    if resp_active and resp_active.success and resp_active.message:
                        active_trial = resp_active.message.strip()
                except Exception:
                    pass

            # If no measurement is currently open in QTM, there are no timeline events to query
            if not active_trial:
                return False, "No measurement currently open in QTM.", None, [], {}

            # If trial_filename was given, verify match
            if trial_filename and active_trial:
                if not trial_names_match(trial_filename, active_trial):
                    return False, f"QTM has '{active_trial}' open, not '{trial_filename}'.", active_trial, [], {}

            # 2. Query timeline events
            req_events = qtm_data_transfer_pb2.CommandToQtm(command_name="GetEvents", command_args_json="{}")
            resp_events = stub.SendCommandToQtm(req_events, timeout=3)
            if not resp_events or not resp_events.success:
                return False, f"Failed to get events from QTM: {getattr(resp_events, 'message', 'No response')}", active_trial, [], {}

            raw_payload = json.loads(resp_events.message) if resp_events.message else {}
            # The bridge returns {} on read failure; a valid empty read has raw_events: [].
            if not isinstance(raw_payload, (dict, list)) or raw_payload == {}:
                return False, "QTM returned no valid event data.", active_trial, [], {}

            # 3. Query frame count / frequency if available
            freq = 0.0
            total_frames = 0
            if isinstance(raw_payload, dict):
                freq = float(raw_payload.get("frequency") or 0.0)
                total_frames = int(raw_payload.get("total_frames") or 0)
                if not active_trial and raw_payload.get("active_trial"):
                    active_trial = raw_payload["active_trial"]

            # Fallback frequency resolution from default parameter or session C3D
            if freq <= 0.0:
                if default_frame_rate and default_frame_rate > 0:
                    freq = float(default_frame_rate)
                elif session_dir and (trial_filename or active_trial):
                    s_stem = Path(trial_filename or active_trial or "").stem
                    s_path = Path(session_dir)
                    for cand in [s_path / f"{s_stem}.c3d", s_path / f"{s_stem.lower()}.c3d"]:
                        if cand.is_file():
                            try:
                                import ezc3d
                                c_obj = ezc3d.c3d(str(cand))
                                freq = float(c_obj["header"]["points"]["frame_rate"])
                                break
                            except Exception:
                                pass
            if freq <= 0.0:
                freq = 100.0

            start_frame = recording_start_frame(raw_payload) if isinstance(raw_payload, dict) else recording_start_frame({})
            # Parse events into clean_events list
            clean_events: List[Dict[str, Any]] = []

            # Format A: raw_events list [{"label": ..., "time": ..., "frame": ...}]
            if isinstance(raw_payload, dict) and "raw_events" in raw_payload:
                for ev in raw_payload["raw_events"]:
                    lbl = normalize_qtm_event_label(ev.get("label", ""))
                    if not lbl:
                        continue
                    t = float(ev.get("time", 0.0))
                    f = time_to_frame(t, freq) if "time" in ev else int(ev["frame"])
                    side = "R" if lbl.startswith("R") or "RIGHT" in lbl else ("L" if lbl.startswith("L") or "LEFT" in lbl else "")
                    etype = "STRIKE" if "STRIKE" in lbl or "HS" in lbl else ("OFF" if "OFF" in lbl or "OF" in lbl else "")
                    clean_events.append({
                        "frame": f,
                        "label": lbl,
                        "time": t,
                        "relative_frame": frame_to_index(f, start_frame),
                        "side": side,
                        "type": etype,
                    })

            # Format B: legacy events_dict { "RSTRIKE": { "FrameNo": [120, 245], "EventOffset": [...] } }
            elif isinstance(raw_payload, dict):
                ev_dict = raw_payload.get("events_dict", raw_payload)
                for raw_lbl, item in ev_dict.items():
                    if isinstance(item, dict) and "FrameNo" in item:
                        norm_lbl = normalize_qtm_event_label(raw_lbl)
                        frames = item["FrameNo"]
                        offsets = item.get("EventOffset", [0.0] * len(frames))
                        for f, off in zip(frames, offsets):
                            if raw_payload.get("frame_convention") == "qtm_absolute_zero_based":
                                f = sample_index_to_frame(f)
                            t = frame_to_time(f, freq) + float(off) / freq
                            side = "R" if norm_lbl.startswith("R") or "RIGHT" in norm_lbl else ("L" if norm_lbl.startswith("L") or "LEFT" in norm_lbl else "")
                            etype = "STRIKE" if "STRIKE" in norm_lbl or "HS" in norm_lbl else ("OFF" if "OFF" in norm_lbl or "OF" in norm_lbl else "")
                            clean_events.append({
                                "frame": int(f),
                                "label": norm_lbl,
                                "time": t,
                                "relative_frame": frame_to_index(f, start_frame),
                                "side": side,
                                "type": etype,
                            })

            elif isinstance(raw_payload, list):
                for ev in raw_payload:
                    if isinstance(ev, dict):
                        lbl = normalize_qtm_event_label(ev.get("label", ""))
                        if not lbl:
                            continue
                        t = float(ev.get("time", 0.0))
                        f = time_to_frame(t, freq) if "time" in ev else int(ev["frame"])
                        side = "R" if lbl.startswith("R") or "RIGHT" in lbl else ("L" if lbl.startswith("L") or "LEFT" in lbl else "")
                        etype = "STRIKE" if "STRIKE" in lbl or "HS" in lbl else ("OFF" if "OFF" in lbl or "OF" in lbl else "")
                        clean_events.append({
                            "frame": f,
                            "label": lbl,
                            "time": t,
                            "relative_frame": frame_to_index(f, start_frame),
                            "side": side,
                            "type": etype,
                        })

            for ev in clean_events:
                trace_event("application_read", ev["label"], ev["frame"], freq, start_frame)
            clean_events.sort(key=lambda x: int(x.get("frame", 0)))
            meta = {
                "source": "qtm_timeline",
                "initial_frame_offset": int(raw_payload.get("initial_frame_offset", 0)) if isinstance(raw_payload, dict) else 0,
                "recording_start_frame": start_frame,
                "frame_convention": FRAME_CONVENTION,
                "frame_rate": freq,
                "total_frames": total_frames,
                "active_trial": active_trial or "",
            }
            return True, f"Retrieved {len(clean_events)} event(s) from QTM.", active_trial, clean_events, meta

    except Exception as e:
        logger.warning("Error fetching events from QTM: %s", e)
        return False, f"QTM gRPC fetch error: {e}", active_trial, [], {}


def sync_qtm_events_to_session(
    session_dir: str | Path,
    trial_filenames: Optional[List[str]] = None,
    port: int = 50052,
    force: bool = False,
) -> Tuple[bool, str, Optional[str], List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Check if QTM has timeline events for any trial in the current session,
    and update the corresponding local trial event results if changed.

    Returns
    -------
    tuple of (updated: bool, message: str, matched_filename: str | None, events: list, ev_info: dict | None)
    """
    s_dir = Path(session_dir)
    if not s_dir.is_dir():
        return False, "Session directory does not exist.", None, [], None

    ok, msg, active_trial, clean_events, meta = fetch_events_from_qtm(port=port, session_dir=s_dir)
    if not ok or not active_trial:
        return False, msg, active_trial, clean_events, None

    # Find which trial filename in the session matches active_trial
    candidates = trial_filenames if trial_filenames else [f.name for f in s_dir.glob("*.qtm")] + [f.name for f in s_dir.glob("*.c3d")]
    matched_file: Optional[str] = None
    for cand in candidates:
        if trial_names_match(cand, active_trial):
            matched_file = cand
            break

    if not matched_file:
        return False, f"QTM active trial '{active_trial}' does not match any trial in session.", active_trial, clean_events, None

    # Resolve accurate capture frame rate from C3D file
    matched_stem = Path(matched_file).stem
    c3d_cand = s_dir / f"{matched_stem}.c3d"
    if not c3d_cand.is_file():
        for cand in s_dir.glob("*.c3d"):
            if cand.stem.lower() == matched_stem.lower():
                c3d_cand = cand
                break
    real_freq = None
    if c3d_cand.is_file():
        try:
            import ezc3d
            c_obj = ezc3d.c3d(str(c3d_cand))
            real_freq = float(c_obj["header"]["points"]["frame_rate"])
        except Exception:
            pass

    if real_freq and real_freq > 0:
        meta["frame_rate"] = real_freq
        for ev in clean_events:
            ev_f = int(ev.get("frame", 0))
            ev["time"] = frame_to_time(ev_f, real_freq)

    # Compare with existing saved events for this trial
    existing_info = load_trial_events(s_dir, matched_file)
    existing_events = existing_info.get("events", []) if existing_info else []

    existing_signature = [(int(e.get("frame", 0)), str(e.get("label", "")).upper()) for e in existing_events]
    new_signature = [(int(e.get("frame", 0)), str(e.get("label", "")).upper()) for e in clean_events]

    # Check if frame rate also changed from 100.0 to real_freq
    existing_freq = float(existing_info.get("frame_rate") or 100.0) if existing_info else 100.0
    freq_differ = real_freq and abs(existing_freq - real_freq) > 0.01

    if not force and not freq_differ and existing_signature == new_signature:
        return False, f"Events for {matched_file} are already in sync with QTM.", matched_file, clean_events, existing_info


    # Events differ or frequency corrected! Save the updated events to results JSON and C3D
    saved_meta = dict(existing_info.get("meta", {})) if existing_info else {}
    saved_meta.update(meta)
    if real_freq and real_freq > 0:
        saved_meta["frame_rate"] = real_freq
    saved_meta["synced_from_qtm"] = True
    saved_meta["qtm_timeline_synced"] = True
    ev_info = save_trial_events(s_dir, matched_file, clean_events, meta=saved_meta)

    return True, f"Synchronized {len(clean_events)} event(s) from QTM for {matched_file}.", matched_file, clean_events, ev_info
