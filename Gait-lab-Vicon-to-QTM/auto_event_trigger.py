#!/usr/bin/env python
"""Standalone CLI for triggering automated gait event labeling.

This script lives one level above the main Python package; when it is
invoked its working directory may not include the package path.  Insert the
relevant directories on sys.path so imports succeed even if the cwd is
`plugin` instead of `plugin/Gait-lab-Vicon-to-QTM`.
"""

import os, sys
from pathlib import Path

GAIT_ENGINE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = GAIT_ENGINE_DIR.parent

if str(PROJECT_ROOT / "QTM-GRPC") not in sys.path:
    sys.path.append(str(PROJECT_ROOT / "QTM-GRPC"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(GAIT_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(GAIT_ENGINE_DIR))

# Status lines below use non-ASCII characters (checkmarks, em dashes, arrows).
# On Windows the console/subprocess stream defaults to the legacy cp1252
# codepage, which can't encode them and raises UnicodeEncodeError, aborting
# the script *before* it reaches the QTM write loop. Force UTF-8 so a
# cosmetic character never blocks the actual event write.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Usage examples:
#     python auto_event_trigger.py --file path/to/trial.qtm
#     python auto_event_trigger.py --file file1.qtm file2.qtm
#
# This script replicates the detection portion of Py3_DynamicMain but is
# # designed to be run headlessly from outside QTM.  It connects to QTM via the
# # gapi layer to write events back to the timeline.


import argparse
import os
import numpy as np
import json
import logging
from pathlib import Path
from Py3_varExtractor import extract_fields_by_filename
import Py3_GaitModules as gait
from gapi import SetEvent
from app.services.frame_coordinates import index_to_frame, frame_to_time, sample_index_to_frame, FRAME_CONVENTION, trace_event

# configure logging later after knowing filename
logger = logging.getLogger("auto_event")
logger.setLevel(logging.INFO)

# Ground truth from visual QTM inspection — update these if confirmed
# frames change after re-processing
GROUND_TRUTH_EVENTS = [
    # (454, "LSTRIKE"),   # confirmed: frame 454, 3.77s — left foot contact
    # (638, "RSTRIKE"),   # confirmed: frame 638, 5.31s — right foot planted
]



def get_qtm_active_measurement():
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


def write_events_to_c3d(c3d_path, events, frame_rate=120.0, offset=0):
    """Write gait events directly into the C3D file's EVENT parameter group."""
    if not os.path.isfile(c3d_path):
        return False
    try:
        import ezc3d
        c = ezc3d.c3d(str(c3d_path))
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
        c.write(str(c3d_path))
        return True
    except Exception as e:
        logger.warning(f"Could not write events to C3D file {c3d_path}: {e}")
        return False


def process_trial(qtm_path):
    # set up per-trial logging
    dirname = os.path.dirname(qtm_path)
    base = os.path.splitext(os.path.basename(qtm_path))[0]
    from app.services.event_service import load_trial_events
    existing = load_trial_events(dirname, os.path.basename(qtm_path))
    expected_revision = existing["meta"]["event_revision"] if existing else 0
    events_dir = os.path.join(dirname, "Events")
    os.makedirs(events_dir, exist_ok=True)
    logpath = os.path.join(events_dir, f"auto_event_{base}.log")
    # Clean up obsolete loose log in session root if present
    legacy_log = os.path.join(dirname, f"auto_event_{base}.log")
    if os.path.isfile(legacy_log) and os.path.abspath(legacy_log) != os.path.abspath(logpath):
        try:
            os.remove(legacy_log)
        except OSError:
            pass
    fh = logging.FileHandler(logpath, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(message)s"))
    if not logger.handlers:
        logger.addHandler(fh)
        logger.addHandler(logging.StreamHandler())

    dir_path = os.path.dirname(qtm_path)
    session_xml = os.path.join(dir_path, "session.xml")
    if not os.path.exists(session_xml):
        logger.error(f"[STAGE 1] FAILED: session.xml not found for {qtm_path}")
        return
    filename = os.path.basename(qtm_path)
    fields = extract_fields_by_filename(session_xml, filename, False)
    if fields is None:
        logger.error(f"[STAGE 1] FAILED: unable to read fields for {qtm_path}")
        return
    frame_rate = fields.get("Capture_Frequency", 0)
    n_frames = fields.get("Frames", 0)
    logger.info(f"[STAGE 1] File loaded: {filename} | Frame rate: {frame_rate} fps | Total frames: {n_frames}")

    # ── STAGE 2: Infer marker names from field keys ──────────────────────────
    GAIT_EVENT_MARKER_NAMES = {}
    keys = list(fields.keys())

    def _find(primary, secondary=None):
        secondary = secondary or []
        for k in keys:
            kl = k.lower()
            for sub in primary:
                if sub in kl:
                    return k
        for k in keys:
            kl = k.lower()
            for sub in secondary:
                if sub in kl:
                    return k
        return None

    GAIT_EVENT_MARKER_NAMES['L_HEEL'] = _find(
        ['left_heel', 'l_heel', 'lheel', 'l_fcc', 'l_calc', 'l_foot_heel', 'lhee'],
        ['heel', 'calc'],
    )
    GAIT_EVENT_MARKER_NAMES['R_HEEL'] = _find(
        ['right_heel', 'r_heel', 'rheel', 'r_fcc', 'r_calc', 'r_foot_heel', 'rhee'],
        ['heel', 'calc'],
    )
    GAIT_EVENT_MARKER_NAMES['L_TOE']  = _find(
        ['left_toe', 'l_toe', 'ltoe', 'left_2nd3rd_mt_head', 'l_2nd3rd', 'l_fm1', 'l_fm2', 'l_foot_toe', 'l_mt2'],
        ['toe', '2nd3rd', 'mt_head'],
    )
    GAIT_EVENT_MARKER_NAMES['R_TOE']  = _find(
        ['right_toe', 'r_toe', 'rtoe', 'right_2nd3rd_mt_head', 'r_2nd3rd', 'r_fm1', 'r_fm2', 'r_foot_toe', 'r_mt2'],
        ['toe', '2nd3rd', 'mt_head'],
    )
    GAIT_EVENT_MARKER_NAMES['SACRUM'] = _find(['sacrum', 'sacr'], ['sac'])
    logger.info(f"[STAGE 2] Inferred marker map: {GAIT_EVENT_MARKER_NAMES}")

    _sacr_label = GAIT_EVENT_MARKER_NAMES.get('SACRUM')
    _sacr_in_fields = _sacr_label and _sacr_label in fields
    if not _sacr_in_fields:
        if 'Left_PSIS' in fields and 'Right_PSIS' in fields:
            logger.warning("[STAGE 2] Sacrum not present, creating virtual marker from PSIS")
            sacx = [(l + r) / 2 for l, r in zip(fields['Left_PSIS']['X'], fields['Right_PSIS']['X'])]
            sacy = [(l + r) / 2 for l, r in zip(fields['Left_PSIS']['Y'], fields['Right_PSIS']['Y'])]
            sacz = [(l + r) / 2 for l, r in zip(fields['Left_PSIS']['Z'], fields['Right_PSIS']['Z'])]
            exists = [a and b for a, b in zip(fields['Left_PSIS']['Exists'], fields['Right_PSIS']['Exists'])]
            _sacr_label = '__AUTO_SACRUM__'
            GAIT_EVENT_MARKER_NAMES['SACRUM'] = _sacr_label
            fields[_sacr_label] = {'X': sacx, 'Y': sacy, 'Z': sacz, 'Exists': exists}
        else:
            logger.warning("[STAGE 2] Sacrum marker not found and cannot synthesize.")

    if not GAIT_EVENT_MARKER_NAMES.get('L_TOE') or not GAIT_EVENT_MARKER_NAMES.get('R_TOE'):
        logger.warning("[STAGE 2] Toe markers not found; ROFF/LOFF will use synthetic timing.")

    # ── STAGE 3-6: Detection → Pairing → Zone filter → Validation ───────────
    try:
        event_list, detection_meta = gait.detect_bilateral_gait_events(
            fields,
            GAIT_EVENT_MARKER_NAMES,
            frame_rate=frame_rate,
            start_frame=fields.get('First Frame', 0),
            end_frame=fields.get('Last Frame', None),
            ap_axis='auto',
            fp_data=fields.get('FP'),
            fp_fz_threshold=20.0,
        )
    except Exception as e:
        logger.error(f"[STAGE X] FAILED: auto detection error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return

    # report metadata
    logger.info(f"[STAGE 3] Zone: {detection_meta.get('zone_frames')} "
                f"method={detection_meta.get('filter_method')}")
    logger.info(f"[STAGE 4] Raw counts: R_HS={detection_meta.get('raw_R_HS',0)} "
                f"R_TO={detection_meta.get('raw_R_TO',0)} "
                f"L_HS={detection_meta.get('raw_L_HS',0)} "
                f"L_TO={detection_meta.get('raw_L_TO',0)}")

    # ── Ground truth validation (diagnostic only) ────────────────────────────
    if GROUND_TRUTH_EVENTS:
        # Build raw event list for validation (before zone filter)
        raw_events = []
        for side_code, hs_lbl, to_lbl in [('R', gait.AUTO_RHS_LABEL, gait.AUTO_ROF_LABEL),
                                           ('L', gait.AUTO_LHS_LABEL, gait.AUTO_LOF_LABEL)]:
            for f in detection_meta.get(f'raw_{side_code}_HS_frames', []):
                raw_events.append((f, hs_lbl))
            for f in detection_meta.get(f'raw_{side_code}_TO_frames', []):
                raw_events.append((f, to_lbl))
        # If raw frame lists aren't in metadata, use the final event_list
        if not raw_events:
            raw_events = event_list
        gait.validate_against_ground_truth(
            raw_events, GROUND_TRUTH_EVENTS,
            tolerance_frames=5, frame_rate=frame_rate)

    # count per label for summary
    label_counts = {}
    for frame, label in event_list:
        label_counts[label] = label_counts.get(label, 0) + 1
    det_summary = ", ".join(f"{k}={v}" for k, v in sorted(label_counts.items()))
    print(f"Detection results: {det_summary}")
    logger.info(f"[STAGE 5] Final event list: {det_summary}")

    # ── Write sidecar JSON ───────────────────────────────────────────────────
    offset = fields.get('initial_frame_offset', 0)
    # Detection returns relative array indices; QTM displays absolute timeline frames.
    qtm_base = sample_index_to_frame(offset)
    detection_meta['initial_frame_offset'] = offset
    detection_meta['qtm_base_frame'] = qtm_base
    detection_meta['frame_convention'] = FRAME_CONVENTION
    detection_meta['recording_start_frame'] = qtm_base
    detection_meta['total_frames'] = int(fields['Frames'])
    detection_meta['frame_rate'] = frame_rate
    detection_meta['qtm_timeline_synced'] = False
    results_path = os.path.join(events_dir, f"auto_event_{base}_results.json")
    try:
        serialisable = []
        for f, l in event_list:
            timeline_frame = index_to_frame(f, qtm_base)
            trace_event("detector", l, timeline_frame, frame_rate, qtm_base, detector_output=f)
            time_sec = frame_to_time(timeline_frame, frame_rate)
            serialisable.append({
                'frame': timeline_frame,
                'label': l,
                'time': time_sec,
                'relative_frame': int(f),
            })
        from app.services.event_service import save_trial_events
        saved = save_trial_events(dirname, os.path.basename(qtm_path), serialisable,
                                  detection_meta, provenance="auto_label", expected_revision=expected_revision)
        logger.info("Events committed locally at revision %s", saved["meta"]["event_revision"])
    except Exception:
        logger.exception("Event transaction failed; detection was not reported saved")
        raise

    total_events = len(event_list)
    if total_events == 0:
        logger.info("[STAGE 7] COMPLETE. No events detected.")
        return

    # JSON and C3D exports are verified, recoverable projections of the committed revision.
    if saved["meta"].get("projection_error"):
        logger.warning("Event export pending: %s", saved["meta"]["projection_error"])

    # ── 8-event sequence validation ──────────────────────────────────────────
    eight_ok = gait.validate_eight_event_sequence(event_list)
    if not eight_ok:
        logger.warning("[STAGE 6] 8-event validation FAILED — writing events anyway, "
                       "but check STAGE 4/5 warnings above.")

    # ── Sequence order validation (from detection pipeline) ──────────────────
    seq_ok = detection_meta.get('sequence_valid', None)
    if seq_ok is not None:
        seq_str = 'PASS ✓' if seq_ok else 'FAIL'
        print(f"[SEQUENCE] Order validation: {seq_str}")
        logger.info(f"[SEQUENCE] Order validation: {seq_str}")
        if not seq_ok:
            for v in detection_meta.get('sequence_violations', []):
                logger.warning(f"[SEQUENCE] {v}")

    # One guarded attempt; another open trial leaves this explicit operation in the outbox.
    from app.services.event_sync_service import observe_session_events
    _, message, _, _, info = observe_session_events(dirname, [os.path.basename(qtm_path)])
    status = info["meta"]["event_sync_status"] if info else "Pending QTM Sync"
    logger.info("[STAGE 7] %s: %d committed events — %s (%s)", base, total_events, status, message)
    print(f"[STAGE 7] {base}: {total_events} events committed — {status}")


def main():
    parser = argparse.ArgumentParser(description="CLI auto event labeling")
    parser.add_argument('--file', '-f', nargs='+',
                        help="Path(s) to one or more .qtm dynamic files")
    # support legacy -s/-f from DynamicMain
    parser.add_argument('--sessionPath', '-s', help="session.xml directory")
    parser.add_argument('--filename', '-n', help="name of the .qtm file")
    # GUI helper passes -t BF by default; ignore it
    parser.add_argument('--t', '-t', help="unused (buffer parameter)", default=None)
    args = parser.parse_args()

    file_list = []
    # if sessionPath supplied, interpret any file names relative to it
    if args.sessionPath and args.file:
        sess_dir = args.sessionPath
        if sess_dir.lower().endswith('.xml'):
            sess_dir = os.path.dirname(sess_dir)
        for fn in args.file:
            file_list.append(os.path.join(sess_dir, fn))
    elif args.file:
        file_list.extend(args.file)
    elif args.sessionPath and args.filename:
        sess_dir = args.sessionPath
        if sess_dir.lower().endswith('.xml'):
            sess_dir = os.path.dirname(sess_dir)
        file_list.append(os.path.join(sess_dir, args.filename))
    else:
        parser.error("Must supply --file or both --sessionPath and --filename")

    for path in file_list:
        process_trial(path)

if __name__ == '__main__':
    main()
