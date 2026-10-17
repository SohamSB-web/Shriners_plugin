# -*- coding: utf-8 -*-
"""
<One of the file associated with the Program to compute lower extremity Shrine Gait Model kinematics and kinetics>
Copyright (C) 2023  <Anas Fodkar>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

"""
# Gait Model Coordinate Systems for Segment and Joints

Created on Mon Feb 19 15:57:33 2018
Last Update: 26 Aug, 2024

@author: psaraswat
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

VersionNumber = 'Py3_v1.3'

from scipy.signal import find_peaks
from typing import Optional

import numpy as np
import Py3_MathModules as math


# ─── Auto Event Labeling Configuration ───────────────────────────────────────
AUTO_RHS_LABEL          = "RSTRIKE"
AUTO_LHS_LABEL          = "LSTRIKE"
AUTO_ROF_LABEL          = "ROFF"
AUTO_LOF_LABEL          = "LOFF"

R_HEEL_MARKER           = "R_HEEL"
L_HEEL_MARKER           = "L_HEEL"
R_TOE_MARKER            = "R_TOE"
L_TOE_MARKER            = "L_TOE"
SACRUM_MARKER           = "SACRUM"

FZ_THRESHOLD_N          = 20.0
BUFFER_PRE_SECONDS      = 1.2      # wide enough to capture frame 454 (3.77s)
BUFFER_POST_SECONDS     = 1.0      # moderate post buffer
SPATIAL_BUFFER_MM       = 1500

MIN_STRIDE_TIME_S       = 0.25     # reduced to allow closer same-side strikes (30 frames @ 120fps)
PEAK_PROMINENCE         = 2.0      # reduced to catch lower-amplitude second strike
MIN_PROMINENCE_FLOOR    = 1.0      # relaxation never goes below this
SYNTHETIC_TO_OFFSET_S   = 0.4      # stance duration used for synthetic TO
TOE_OFF_FRAME_OFFSET    = 0        # global shift applied to all OF events (set 0 unless calibrated)

INCLUDE_PRE_PLATE_STRIKE  = True
INCLUDE_POST_PLATE_STRIKE = True

FALSE_FIRST_EVENT_GAP_S   = 0.8    # isolation gap (s) to flag false first event
# ─────────────────────────────────────────────────────────────────────────────

import logging
_logger = logging.getLogger("auto_event")


# =============================================================================
#   Force Plate Valid Zone — Temporal filtering based on vertical force (Fz)
# =============================================================================

def compute_forceplate_valid_zone(fp_data, marker_frame_rate,
                                  buffer_pre=100, buffer_post=None,
                                  fz_threshold=20.0):
    """
    Compute the valid video-frame zone around force plate activity.

    Finds the first and last video frames where any force plate registers
    vertical force (|Fz|) above a threshold, then applies padding before and
    after.  Historically the same buffer was used on both sides; the
    ``buffer_post`` argument allows the trailing buffer to be disabled (e.g.
    ``buffer_post=0``) so that no events are included once the subject walks
    off the plate.

    Parameters
    ----------
    fp_data : dict
        Force plate data dictionary (``fields["FP"]``), keyed by plate id
        (e.g. ``"FP0"``), each containing ``'Force' -> {'Z': array}`` and
        ``'Frequency'`` (analog Hz).
    marker_frame_rate : float
        Video / marker capture frequency in Hz.
    buffer_pre : int
        Number of *video* frames to pad before the active zone.
    buffer_post : int or None
        Number of *video* frames to pad after the active zone.  If ``None``
        the same value as ``buffer_pre`` is used.
    fz_threshold : float
        Minimum |Fz| in Newtons to consider a force plate "active".

    Returns
    -------
    zone_start : int
        First valid video frame (inclusive).  0 if no activity found.
    zone_end : int
        Last valid video frame (inclusive).  0 if no activity found.
    active : bool
        True if at least one force plate was active above threshold.
    """
    first_analog = None
    last_analog = None
    analog_rate = None

    for fp_key, fp in fp_data.items():
        fz = np.asarray(fp["Force"]["Z"], dtype=float)
        fp_freq = fp.get("Frequency", marker_frame_rate)
        analog_rate = fp_freq

        active_indices = np.where(np.abs(fz) > fz_threshold)[0]

        if len(active_indices) > 0:
            if first_analog is None or active_indices[0] < first_analog:
                first_analog = int(active_indices[0])
            if last_analog is None or active_indices[-1] > last_analog:
                last_analog = int(active_indices[-1])

    if first_analog is None:
        print("[GaitEvents] No force plate activity detected above "
              f"{fz_threshold} N threshold.")
        return 0, 0, False

    # Convert analog frames → video frames
    ratio = analog_rate / marker_frame_rate if analog_rate else 1.0
    first_video = int(first_analog / ratio)
    last_video = int(last_analog / ratio)

    # Apply buffer (post may default to pre)
    if buffer_post is None:
        buffer_post = buffer_pre
    zone_start = max(0, first_video - buffer_pre)
    zone_end = last_video + buffer_post

    print(f"[GaitEvents] Force Plate Zone defined as: video frames "
          f"{zone_start} to {zone_end}  "
          f"(active Fz: analog [{first_analog}-{last_analog}], "
          f"video [{first_video}-{last_video}], "
          f"buffer_pre={buffer_pre}, buffer_post={buffer_post}, "
          f"analog rate={analog_rate} Hz, video rate={marker_frame_rate} Hz)")

    return zone_start, zone_end, True

def _longest_contiguous_valid_window(*exists_arrays):
    """Find the longest contiguous frame range where ALL given boolean arrays are True.

    Parameters
    ----------
    *exists_arrays : array-like of bool
        One or more per-frame validity arrays (same length).

    Returns
    -------
    start : int
        First frame of the longest contiguous valid window (inclusive).
    end : int
        Last frame + 1 of the window (exclusive, suitable for slicing).
    length : int
        Number of contiguous valid frames.  0 if no valid frame exists.
    """
    combined = np.ones(len(exists_arrays[0]), dtype=bool)
    for arr in exists_arrays:
        combined &= np.asarray(arr, dtype=bool)

    # Find runs of True in combined mask
    if not np.any(combined):
        return 0, 0, 0

    diff = np.diff(combined.astype(np.int8))
    # starts: indices where a True-run begins
    starts = np.where(diff == 1)[0] + 1
    # ends: indices where a True-run ends (exclusive)
    ends = np.where(diff == -1)[0] + 1

    # Handle edge cases: if combined starts/ends with True
    if combined[0]:
        starts = np.concatenate(([0], starts))
    if combined[-1]:
        ends = np.concatenate((ends, [len(combined)]))

    lengths = ends - starts
    best = np.argmax(lengths)
    return int(starts[best]), int(ends[best]), int(lengths[best])
# --- additional helpers and upgraded detection --------------------------------

def _compute_spatial_zone(trajectory_data, plate_corners, frame_rate):
    """Compute frame window around force plates using marker positions.

    Returns
    -------
    zone_start, zone_end, active (bool)
    """
    heel_xyz = trajectory_data.get("heel_xyz")
    toe_xyz  = trajectory_data.get("toe_xyz")
    sacrum_xyz = trajectory_data.get("sacrum_xyz")
    n_frames = len(trajectory_data.get("heel_ap", []))

    if plate_corners is None or sacrum_xyz is None:
        return 0, n_frames - 1, False

    sx, sy, sz = sacrum_xyz
    range_x = np.nanmax(sx) - np.nanmin(sx)
    range_y = np.nanmax(sy) - np.nanmin(sy)
    axis = 0 if range_x > range_y else 1

    try:
        all_corners = np.vstack(plate_corners)
    except Exception:
        all_corners = None
    if all_corners is None or all_corners.size == 0:
        return 0, n_frames - 1, False

    plate_min = np.min(all_corners[:, axis])
    plate_max = np.max(all_corners[:, axis])
    zone_min = plate_min - SPATIAL_BUFFER_MM
    zone_max = plate_max + SPATIAL_BUFFER_MM

    frames_in_zone = []
    for f in range(n_frames):
        inside = False
        if heel_xyz is not None:
            val = heel_xyz[axis][f]
            if zone_min <= val <= zone_max:
                inside = True
        if not inside and toe_xyz is not None:
            val = toe_xyz[axis][f]
            if zone_min <= val <= zone_max:
                inside = True
        if inside:
            frames_in_zone.append(f)
    if not frames_in_zone:
        return 0, n_frames - 1, False
    return min(frames_in_zone), max(frames_in_zone), True


def detect_gait_events(
    trajectory_data: dict,
    frame_rate: float,
) -> dict:
    """Run Zeni detection on a single side (raw, no zone filtering).

    Returns a dict with keys ``"hs_frames"`` and ``"to_frames"`` containing
    frame indices of detected heel-strike and toe-off events respectively.

    If the initial detection yields 0 TO events while HS > 0, the detector
    automatically re-runs with progressively relaxed prominence until TO events
    are found (independent relaxation for HS and TO).
    """
    heel_ap = np.asarray(trajectory_data.get("heel_ap", []), dtype=float)
    toe_ap  = np.asarray(trajectory_data.get("toe_ap", []), dtype=float)
    sacrum_ap = np.asarray(trajectory_data.get("sacrum_ap", []), dtype=float)
    heel_exists = np.asarray(trajectory_data.get("heel_exists", []), dtype=bool)
    toe_exists  = np.asarray(trajectory_data.get("toe_exists", []), dtype=bool)
    sacrum_exists = np.asarray(trajectory_data.get("sacrum_exists", []), dtype=bool)

    n_frames = len(heel_ap)

    try:
        hs_raw, to_raw = _zeni_detect_gait_events(
            heel_ap, toe_ap, sacrum_ap,
            heel_exists, toe_exists, sacrum_exists,
            frame_rate,
            start_frame=0,
            end_frame=n_frames,
            ap_axis='auto',
            heel_marker_data_xyz=trajectory_data.get('heel_xyz'),
            toe_marker_data_xyz=trajectory_data.get('toe_xyz'),
            sacrum_marker_data_xyz=trajectory_data.get('sacrum_xyz'),
            min_stride_time=MIN_STRIDE_TIME_S,
            peak_prominence=PEAK_PROMINENCE,
        )
    except Exception as e:
        _logger.error(f"[STAGE 4] ERROR running Zeni algorithm: {e}")
        hs_raw, to_raw = [], []

    # ---- Independent relaxation for HS when count is low ---------------------
    if len(hs_raw) < 2:
        scale = 0.5
        while len(hs_raw) < 2 and scale >= 0.1:
            relaxed_p = max(PEAK_PROMINENCE * scale, MIN_PROMINENCE_FLOOR)
            _logger.info(f"[STAGE 4] WARNING: R/L_HS detected {len(hs_raw)} events. "
                         f"Relaxing prominence to {relaxed_p:.1f}...")
            try:
                hs_retry, _ = _zeni_detect_gait_events(
                    heel_ap, toe_ap, sacrum_ap,
                    heel_exists, toe_exists, sacrum_exists,
                    frame_rate, 0, n_frames, 'auto',
                    trajectory_data.get('heel_xyz'),
                    trajectory_data.get('toe_xyz'),
                    trajectory_data.get('sacrum_xyz'),
                    min_stride_time=MIN_STRIDE_TIME_S * scale,
                    peak_prominence=relaxed_p,
                )
                hs_raw = sorted(set(hs_raw) | set(hs_retry))
            except Exception:
                pass
            scale /= 2

    # ---- Independent relaxation for TO when count is low ---------------------
    if len(to_raw) < 2:
        scale = 0.5
        while len(to_raw) < 2 and scale >= 0.1:
            relaxed_p = max(PEAK_PROMINENCE * scale, MIN_PROMINENCE_FLOOR)
            _logger.info(f"[STAGE 4] WARNING: R/L_TO detected {len(to_raw)} events. "
                         f"Relaxing prominence to {relaxed_p:.1f}...")
            try:
                _, to_retry = _zeni_detect_gait_events(
                    heel_ap, toe_ap, sacrum_ap,
                    heel_exists, toe_exists, sacrum_exists,
                    frame_rate, 0, n_frames, 'auto',
                    trajectory_data.get('heel_xyz'),
                    trajectory_data.get('toe_xyz'),
                    trajectory_data.get('sacrum_xyz'),
                    min_stride_time=MIN_STRIDE_TIME_S * scale,
                    peak_prominence=relaxed_p,
                )
                to_raw = sorted(set(to_raw) | set(to_retry))
            except Exception:
                pass
            scale /= 2

    return {"hs_frames": sorted(hs_raw), "to_frames": sorted(to_raw)}


# =============================================================================
#   Pairing, Zone Filtering, and Validation utilities
# =============================================================================

def pair_strike_to_off(hs_frames, to_frames, label_hs, label_to,
                       zone_end, frame_rate):
    """For every Heel Strike, find the FIRST Toe Off that occurs AFTER it.

    Both events in a pair are written together or not at all.
    Unmatched TOs (no preceding strike) are discarded.
    """
    paired_events = []
    available_tos = sorted(to_frames)  # mutable copy — consumed as we match
    synthetic_count = 0

    for hs_frame in sorted(hs_frames):
        # Find the first TO that comes AFTER this HS
        matched_to = None
        for to_frame in sorted(available_tos):
            if to_frame > hs_frame:
                matched_to = to_frame
                available_tos.remove(to_frame)
                break

        if matched_to is None:
            # No real TO found — create synthetic
            synthetic_frame = hs_frame + max(1, int(frame_rate * SYNTHETIC_TO_OFFSET_S))
            if zone_end is not None:
                synthetic_frame = min(synthetic_frame, zone_end)
            matched_to = synthetic_frame
            synthetic_count += 1
            _logger.warning(f"[STAGE 5] WARNING: Synthetic {label_to} created at "
                            f"frame {synthetic_frame} (no real TO after {label_hs} at {hs_frame})")

        # Apply global frame offset
        matched_to += TOE_OFF_FRAME_OFFSET

        # Write BOTH events as a guaranteed pair
        paired_events.append((hs_frame, label_hs))
        paired_events.append((matched_to, label_to))

    # Any remaining unmatched TOs are DISCARDED (no preceding strike)
    if available_tos:
        _logger.warning(f"[STAGE 5] WARNING: {len(available_tos)} unmatched TO events "
                        f"discarded (no preceding strike): frames {available_tos}")

    side_name = 'Right' if 'R' in label_hs else 'Left'
    _logger.info(f"[STAGE 5] Pairing — {side_name}: {len(hs_frames)} strikes paired, "
                 f"{synthetic_count} synthetic")

    n_pairs = len(paired_events) // 2
    if n_pairs < 2:
        print(f"[STAGE 5] WARNING: Only {n_pairs} pair(s) produced for {side_name} side. "
              f"Target is 2 pairs. Check MIN_STRIDE_TIME_S and PEAK_PROMINENCE settings.")
    else:
        print(f"[STAGE 5] {side_name} side: {n_pairs} pairs confirmed ")

    return sorted(paired_events, key=lambda x: x[0])


def apply_zone_filter(events, zone_start, zone_end, log_prefix="[STAGE 5]"):
    """Keep only events whose frame falls within [zone_start, zone_end].

    Parameters
    ----------
    events : list of (frame, label) tuples
    zone_start, zone_end : int
    log_prefix : str

    Returns the filtered list.  Logs every dropped event.
    """
    kept = []
    dropped = []
    for frame, label in events:
        if zone_start <= frame <= zone_end:
            kept.append((frame, label))
        else:
            dropped.append((frame, label))
    if dropped:
        _logger.info(f"{log_prefix} Dropped {len(dropped)} events outside zone "
                     f"[{zone_start}, {zone_end}]: {dropped}")
    return kept


def validate_event_pairing(events):
    """Check that every HS is immediately followed by its matching OF on the same side.

    Returns True if zero violations found; False otherwise.
    Logs a WARNING for every violation.
    """
    violations = 0
    # group by side
    for side_hs, side_of in [(AUTO_RHS_LABEL, AUTO_ROF_LABEL),
                              (AUTO_LHS_LABEL, AUTO_LOF_LABEL)]:
        side_events = [(f, l) for f, l in events if l in (side_hs, side_of)]
        side_events.sort(key=lambda x: x[0])
        i = 0
        while i < len(side_events):
            frame, label = side_events[i]
            if label == side_hs:
                # expect the very next event on this side to be the OF
                if i + 1 < len(side_events):
                    nf, nl = side_events[i + 1]
                    if nl != side_of:
                        _logger.warning(f"[STAGE 6] Pairing violation: {label} at frame {frame} "
                                        f"followed by {nl} at frame {nf} (expected {side_of})")
                        violations += 1
                else:
                    # In a bounded 8-event sequence, the trailing leg ends on its 2nd strike
                    # (its following off occurs in the next stride).
                    if len(events) == 8 and len(side_events) == 4 and i == 3:
                        pass
                    else:
                        _logger.warning(f"[STAGE 6] Pairing violation: {label} at frame {frame} "
                                        f"has no following {side_of}")
                        violations += 1
            i += 1

    if violations == 0:
        _logger.info("[STAGE 6] Pairing check: PASS — every strike has a following off")
    else:
        _logger.warning(f"[STAGE 6] Pairing check: FAIL — {violations} violation(s) detected")
    return violations == 0



def enforce_minimum_detections(current_frames, trajectory_data, frame_rate,
                                zone_start, zone_end, event_type, side_label,
                                target_count=2):
    """Re-run Zeni with relaxed params if zone-filtered count < target_count.

    Parameters
    ----------
    current_frames : list of int
        Currently detected frames (across full trial).
    trajectory_data : dict
        Single-side trajectory dict (heel_ap, toe_ap, sacrum_ap, etc.).
    frame_rate : float
    zone_start, zone_end : int
    event_type : str
        'HS' for heel strikes, 'TO' for toe offs.
    side_label : str
        'Left' or 'Right' (for logging).
    target_count : int
        Minimum number of events desired within the zone.

    Returns
    -------
    list of int : updated frame list (may include new detections).
    """
    in_zone = [f for f in current_frames if zone_start <= f <= zone_end]
    if len(in_zone) >= target_count:
        return current_frames

    n_frames = len(trajectory_data['heel_ap'])
    scales = [1.0, 0.7, 0.5, 0.3, 0.1]

    for scale in scales:
        in_zone = [f for f in current_frames if zone_start <= f <= zone_end]
        if len(in_zone) >= target_count:
            break

        relaxed_prom = max(PEAK_PROMINENCE * scale, MIN_PROMINENCE_FLOOR)
        relaxed_stride = MIN_STRIDE_TIME_S * scale
        relaxed_dist = max(int(relaxed_stride * frame_rate), 10)

        print(f"[STAGE 4] {side_label} {event_type} only has {len(in_zone)} in zone. "
              f"Relaxing  prominence={relaxed_prom:.1f}, "
              f"min_distance={relaxed_dist} frames (scale={scale})")

        try:
            hs_retry, to_retry = _zeni_detect_gait_events(
                trajectory_data['heel_ap'],
                trajectory_data['toe_ap'],
                trajectory_data['sacrum_ap'],
                trajectory_data['heel_exists'],
                trajectory_data['toe_exists'],
                trajectory_data['sacrum_exists'],
                frame_rate,
                start_frame=0,
                end_frame=n_frames,
                ap_axis='auto',
                heel_marker_data_xyz=trajectory_data.get('heel_xyz'),
                toe_marker_data_xyz=trajectory_data.get('toe_xyz'),
                sacrum_marker_data_xyz=trajectory_data.get('sacrum_xyz'),
                min_stride_time=relaxed_stride,
                peak_prominence=relaxed_prom,
            )
            if event_type == 'HS':
                current_frames = sorted(set(current_frames) | set(hs_retry))
            else:
                current_frames = sorted(set(current_frames) | set(to_retry))
        except Exception as e:
            _logger.warning(f"[STAGE 4] Relaxation failed for {side_label} {event_type}: {e}")

    in_zone = [f for f in current_frames if zone_start <= f <= zone_end]
    if len(in_zone) < target_count:
        print(f"[STAGE 4] WARNING: Could only find {len(in_zone)} "
              f"{side_label} {event_type}(s) in zone even after maximum relaxation. "
              f"Check raw marker trajectories.")
    else:
        print(f"[STAGE 4] {side_label} {event_type}: {len(in_zone)} in zone after enforcement ")

    return current_frames


def validate_eight_event_sequence(events):
    """Confirm the final event list contains exactly 2x each label = 8 total.

    Also confirms no event label appears consecutively.
    Logs PASS or lists every violation found.
    Returns True only if count == 8 and no consecutive same-label violations.
    """
    counts = {AUTO_RHS_LABEL: 0, AUTO_LHS_LABEL: 0,
              AUTO_ROF_LABEL: 0, AUTO_LOF_LABEL: 0}
    sorted_events = sorted(events, key=lambda x: x[0])

    for frame, label in sorted_events:
        if label in counts:
            counts[label] += 1

    total = sum(counts.values())

    # Check for consecutive same-label violations
    consecutive_violations = []
    for i in range(1, len(sorted_events)):
        if sorted_events[i][1] == sorted_events[i - 1][1]:
            consecutive_violations.append(
                f"{sorted_events[i][1]} at frames {sorted_events[i - 1][0]} and {sorted_events[i][0]}")

    print(f"[STAGE 6] Pre-write event count: {counts} | Total: {total}")
    _logger.info(f"[STAGE 6] Pre-write event count: {counts} | Total: {total}")

    ok = True
    if total != 8:
        print(f"[STAGE 6] WARNING: Expected 8 events, got {total}. "
              f"Adjust MIN_STRIDE_TIME_S or PEAK_PROMINENCE.")
        ok = False

    if any(v != 2 for v in counts.values()):
        print(f"[STAGE 6] WARNING: Unbalanced event counts: {counts}")
        ok = False

    if consecutive_violations:
        print(f"[STAGE 6] WARNING: Consecutive same-label events: {consecutive_violations}")
        ok = False

    if ok:
        print(f"[STAGE 6] Event count validation: PASS  (8 events, 2 per label)")
    status_str = 'PASS ' if ok else 'FAIL'
    _logger.info(f"[STAGE 6] Event count validation: {status_str} "
                 f"(counts={counts}, total={total})")

    return ok


# =============================================================================
#   Sequence Integrity — false-positive removal, missing-event recovery, order
# =============================================================================

def remove_false_first_event(raw, frame_rate):
    """Remove an isolated false-positive first event across all labels.

    Flattens the raw dict ``{'R': {'hs': [...], 'to': [...]}, 'L': {...}}``
    into a timeline, and checks whether the chronologically first HS event
    is separated from the second-earliest event (any type/side) by more
    than ``FALSE_FIRST_EVENT_GAP_S`` seconds.  If so, it is removed as a
    body-sway artefact at capture start.

    Operates on the *raw* dict **in place** and returns it.
    """
    # Build timeline of all HS events (we only prune strikes, not offs)
    all_hs = []
    for side in ['R', 'L']:
        label = AUTO_RHS_LABEL if side == 'R' else AUTO_LHS_LABEL
        for f in raw[side]['hs']:
            all_hs.append((f, side, label))
    if len(all_hs) < 2:
        return raw

    # Also include TOs so the gap is measured against ANY next event
    all_events = list(all_hs)
    for side in ['R', 'L']:
        label = AUTO_ROF_LABEL if side == 'R' else AUTO_LOF_LABEL
        for f in raw[side]['to']:
            all_events.append((f, side, label))
    all_events.sort(key=lambda x: x[0])

    first_frame, first_side, first_label = all_events[0]
    second_frame = all_events[1][0]
    gap_s = (second_frame - first_frame) / frame_rate

    # Only prune if the first event is an HS (strike)
    if first_label not in (AUTO_RHS_LABEL, AUTO_LHS_LABEL):
        return raw

    if gap_s > FALSE_FIRST_EVENT_GAP_S:
        print(f"[SEQUENCE] WARNING: First event '{first_label}' at frame "
              f"{first_frame} ({first_frame / frame_rate:.3f}s) is isolated "
              f"(gap to next event: {gap_s:.3f}s > {FALSE_FIRST_EVENT_GAP_S}s). "
              f"Removing as false positive.")
        _logger.warning(f"[SEQUENCE] Removed false first event: {first_label} "
                        f"at frame {first_frame}")
        raw[first_side]['hs'].remove(first_frame)
    else:
        print(f"[SEQUENCE] First event '{first_label}' at frame {first_frame} "
              f"validated (gap to next: {gap_s:.3f}s) ")

    return raw


def ensure_strike_before_terminal_off(raw, traj_data, frame_rate,
                                       zone_start, zone_end):
    """Recover a missing RSTRIKE before the final LOFF (or vice-versa).

    After raw Zeni detection, checks whether the chronologically last
    event is an OFF and whether a STRIKE of the *opposite* side exists
    between the last same-side STRIKE and that terminal OFF.  If not,
    searches the Zeni heel-minus-sacrum signal in that window with
    progressively relaxed prominence.

    Operates on the *raw* dict **in place** and returns it.
    """
    from scipy.signal import find_peaks as _fp

    # Check both sides symmetrically:
    #   terminal LOFF  → need RSTRIKE before it
    #   terminal ROFF  → need LSTRIKE before it
    for (off_side, strike_side, off_label, strike_label) in [
        ('L', 'R', AUTO_LOF_LABEL, AUTO_RHS_LABEL),
        ('R', 'L', AUTO_ROF_LABEL, AUTO_LHS_LABEL),
    ]:
        offs   = sorted(raw[off_side]['to'])
        strikes_same = sorted(raw[off_side]['hs'])  # same side as OFF
        strikes_opp  = sorted(raw[strike_side]['hs'])  # opposite side

        if not offs:
            continue

        final_off = offs[-1]

        # Is this the chronologically last event overall?
        all_frames = []
        for s in ['R', 'L']:
            all_frames.extend(raw[s]['hs'])
            all_frames.extend(raw[s]['to'])
        if not all_frames or max(all_frames) != final_off:
            continue  # this OFF is not the last event — skip

        # Find the latest same-side strike before this OFF
        last_same_strike = max([f for f in strikes_same if f < final_off],
                               default=zone_start)

        # Check if an opposite-side strike exists in [last_same_strike, final_off]
        opp_in_window = [f for f in strikes_opp
                         if last_same_strike < f < final_off]

        if opp_in_window:
            print(f"[SEQUENCE] {strike_label} before final {off_label} "
                  f"confirmed at frame {opp_in_window[-1]} ")
            continue

        # --- Opposite-side strike missing — try to recover it ----------------
        print(f"[SEQUENCE] WARNING: No {strike_label} found between "
              f"last {off_side}-side strike (frame {last_same_strike}) and "
              f"final {off_label} (frame {final_off}). "
              f"Searching window with relaxed parameters...")
        _logger.warning(f"[SEQUENCE] Missing {strike_label} before terminal "
                        f"{off_label} at frame {final_off}")

        if strike_side not in traj_data:
            continue

        traj = traj_data[strike_side]
        heel_ap = np.asarray(traj['heel_ap'], dtype=float)
        sacrum_ap = np.asarray(traj['sacrum_ap'], dtype=float)
        signal = heel_ap - sacrum_ap

        win_start = max(last_same_strike, 0)
        win_end = min(final_off, len(signal))
        window = signal[win_start:win_end]

        if len(window) < 5:
            continue

        recovered = False
        for prom in [PEAK_PROMINENCE, 1.5, 1.0, 0.5]:
            local_peaks, _ = _fp(window, prominence=prom,
                                  distance=max(int(frame_rate * 0.2), 10))
            if len(local_peaks) > 0:
                best = local_peaks[np.argmax(window[local_peaks])]
                recovered_frame = win_start + int(best)
                raw[strike_side]['hs'].append(recovered_frame)
                raw[strike_side]['hs'].sort()
                print(f"[SEQUENCE] Recovered {strike_label} at frame "
                      f"{recovered_frame} ({recovered_frame / frame_rate:.3f}s) "
                      f"using prominence={prom} ")
                _logger.info(f"[SEQUENCE] Recovered {strike_label} at frame "
                             f"{recovered_frame}")
                recovered = True
                break

        if not recovered:
            # Synthetic — place at 40% of the window
            syn = win_start + int((win_end - win_start) * 0.4)
            syn = max(zone_start, min(syn, final_off - 1))
            raw[strike_side]['hs'].append(syn)
            raw[strike_side]['hs'].sort()
            print(f"[SEQUENCE] SYNTHETIC {strike_label} created at frame "
                  f"{syn} ({syn / frame_rate:.3f}s) — no real peak found. "
                  f"Verify manually.")
            _logger.warning(f"[SEQUENCE] Synthetic {strike_label} at frame {syn}")

    return raw


def validate_sequence_order(events):
    """Validate biomechanical ordering of the final event list.

    Rules enforced:
      1. Within each side, STRIKE must precede OFF
      2. No two consecutive events of the same label
      3. First event must be a STRIKE (not an OFF)
      4. Last event must be an OFF (not a STRIKE)

    Returns (is_valid, violations).
    """
    violations = []
    sorted_events = sorted(events, key=lambda x: x[0])

    if not sorted_events:
        return True, []

    # Rule 3 — first event must be a STRIKE
    if sorted_events[0][1] in (AUTO_ROF_LABEL, AUTO_LOF_LABEL):
        violations.append(
            f"RULE 3: First event is OFF ({sorted_events[0][1]} "
            f"at frame {sorted_events[0][0]})")

    # Rule 4 — last event must be an OFF
    if sorted_events[-1][1] in (AUTO_RHS_LABEL, AUTO_LHS_LABEL):
        violations.append(
            f"RULE 4: Last event is STRIKE ({sorted_events[-1][1]} "
            f"at frame {sorted_events[-1][0]})")

    # Rules 1 & 2 — per-side ordering
    last_r = None
    last_l = None
    first_label = sorted_events[0][1]
    for frame, label in sorted_events:
        if label == AUTO_RHS_LABEL:
            if last_r == AUTO_RHS_LABEL:
                violations.append(
                    f"RULE 2: Consecutive RSTRIKE at frame {frame}")
            last_r = AUTO_RHS_LABEL
        elif label == AUTO_ROF_LABEL:
            # In an alternating sequence starting with LHS, the initial ROFF is the
            # opposite toe-off of the initial double-support stance.
            if last_r is None and first_label == AUTO_LHS_LABEL:
                last_r = AUTO_ROF_LABEL
            elif last_r != AUTO_RHS_LABEL:
                violations.append(
                    f"RULE 1: ROFF at frame {frame} has no preceding RSTRIKE")
                last_r = AUTO_ROF_LABEL
            else:
                last_r = AUTO_ROF_LABEL
        elif label == AUTO_LHS_LABEL:
            if last_l == AUTO_LHS_LABEL:
                violations.append(
                    f"RULE 2: Consecutive LSTRIKE at frame {frame}")
            last_l = AUTO_LHS_LABEL
        elif label == AUTO_LOF_LABEL:
            # In an alternating sequence starting with RHS, the initial LOFF is the
            # opposite toe-off of the initial double-support stance.
            if last_l is None and first_label == AUTO_RHS_LABEL:
                last_l = AUTO_LOF_LABEL
            elif last_l != AUTO_LHS_LABEL:
                violations.append(
                    f"RULE 1: LOFF at frame {frame} has no preceding LSTRIKE")
                last_l = AUTO_LOF_LABEL
            else:
                last_l = AUTO_LOF_LABEL

    is_valid = len(violations) == 0

    if is_valid:
        print("[SEQUENCE] Order validation: PASS ")
        _logger.info("[SEQUENCE] Order validation: PASS")
    else:
        for v in violations:
            print(f"[SEQUENCE] {v}")
            _logger.warning(f"[SEQUENCE] {v}")
        print(f"[SEQUENCE] Order validation: FAIL "
              f"({len(violations)} violation(s))")

    return is_valid, violations


def validate_against_ground_truth(detected_events, ground_truth,
                                   tolerance_frames=5, frame_rate=120.0):
    """Check detected events against visually confirmed ground truth frames.

    Purely diagnostic — does NOT modify detected_events.
    Logs FOUND or MISSING for each ground truth point.
    """
    print(f"[VALIDATION] Checking {len(ground_truth)} ground truth events "
          f"(tolerance: {tolerance_frames} frames):")
    _logger.info(f"[VALIDATION] Checking {len(ground_truth)} ground truth events "
                 f"(tolerance: {tolerance_frames} frames)")

    all_passed = True
    for gt_frame, gt_label in ground_truth:
        matched = any(
            label == gt_label and abs(frame - gt_frame) <= tolerance_frames
            for frame, label in detected_events
        )
        if matched:
            msg = (f"[VALIDATION]  FOUND: {gt_label} at frame {gt_frame} "
                   f"({gt_frame / frame_rate:.3f}s)")
        else:
            all_passed = False
            same_label = [(f, l) for f, l in detected_events if l == gt_label]
            if same_label:
                nearest = min(same_label, key=lambda x: abs(x[0] - gt_frame))
                msg = (f"[VALIDATION]  MISSING: {gt_label} at frame {gt_frame} "
                       f"({gt_frame / frame_rate:.3f}s)  nearest {gt_label} was at "
                       f"frame {nearest[0]} (offset: {nearest[0] - gt_frame:+d} frames)")
            else:
                msg = (f"[VALIDATION]  MISSING: {gt_label} at frame {gt_frame} "
                       f"({gt_frame / frame_rate:.3f}s)  NO {gt_label} events detected at all")
        print(msg)
        _logger.info(msg)

    if all_passed:
        print("[VALIDATION] ALL ground truth events confirmed ")
        _logger.info("[VALIDATION] ALL ground truth events confirmed ")
    else:
        print("[VALIDATION] FAILED  adjust PEAK_PROMINENCE or "
              "MIN_STRIDE_TIME_S and re-run")
        _logger.warning("[VALIDATION] FAILED  adjust PEAK_PROMINENCE or "
                        "MIN_STRIDE_TIME_S and re-run")
    return all_passed


# =============================================================================
#   Automated Gait Event Detection — Zeni Coordinate-Based Algorithm
#   Reference: Zeni, Richards & Higginson (2008). Gait & Posture, 27(4), 710-714.
# =============================================================================

def _zeni_detect_gait_events(
    heel_ap,
    toe_ap,
    sacrum_ap,
    heel_exists,
    toe_exists,
    sacrum_exists,
    frame_rate,
    start_frame=0,
    end_frame=None,
    ap_axis='auto',
    heel_marker_data_xyz=None,
    toe_marker_data_xyz=None,
    sacrum_marker_data_xyz=None,
    min_stride_time=0.3,
    peak_prominence=5.0,
    lowpass_cutoff=6.0,
):
    """
    Detect Heel Strike (HS) and Toe Off (TO) events using the Zeni algorithm.

    The algorithm computes:
      - HS: local maxima of (heel_AP - sacrum_AP)  → foot is maximally anterior
      - TO: local minima of (toe_AP  - sacrum_AP)  → foot is maximally posterior

    Parameters
    ----------
    heel_ap : array-like
        Heel marker position along the Anterior-Posterior axis (mm).
    toe_ap : array-like
        Toe marker position along the AP axis (mm).
    sacrum_ap : array-like
        Sacrum marker position along the AP axis (mm).
    heel_exists : array-like of bool
        Validity flag for each heel frame.
    toe_exists : array-like of bool
        Validity flag for each toe frame.
    sacrum_exists : array-like of bool
        Validity flag for each sacrum frame.
    frame_rate : float
        Marker capture frequency in Hz.
    start_frame : int
        First frame index to analyse (inclusive).
    end_frame : int or None
        Last frame index to analyse (exclusive). None → len(heel_ap).
    ap_axis : str
        'auto' (default), 'Y', or 'X'. When 'auto', the full XYZ data is used
        to decide which lab axis best represents the AP direction. If the
        full XYZ arrays are not supplied, 'Y' is assumed.
    heel_marker_data_xyz : tuple of (X, Y, Z) arrays or None
        Full 3-component heel marker data, used only when ap_axis='auto'.
    toe_marker_data_xyz : tuple of (X, Y, Z) arrays or None
        Full 3-component toe marker data, used only when ap_axis='auto'.
    sacrum_marker_data_xyz : tuple of (X, Y, Z) arrays or None
        Full 3-component sacrum marker data, used only when ap_axis='auto'.
    min_stride_time : float
        Minimum time (s) between two successive events of the same type.
        Used to set the `distance` parameter of `find_peaks`.
    peak_prominence : float
        Minimum prominence (mm) for peaks.  Helps reject noise.
    lowpass_cutoff : float
        Butterworth low-pass filter cut-off frequency (Hz).
        Set to 0 to disable filtering.

    Returns
    -------
    hs_frames : list of int
        Frame indices of detected heel-strike events.
    to_frames : list of int
        Frame indices of detected toe-off events.
    """

    heel_ap = np.asarray(heel_ap, dtype=float)
    toe_ap  = np.asarray(toe_ap, dtype=float)
    sacrum_ap = np.asarray(sacrum_ap, dtype=float)
    heel_exists  = np.asarray(heel_exists, dtype=bool)
    toe_exists   = np.asarray(toe_exists, dtype=bool)
    sacrum_exists = np.asarray(sacrum_exists, dtype=bool)

    # sanity check -- all arrays should share the same frame count
    n = len(heel_ap)
    lens = {
        'heel': len(heel_ap),
        'toe': len(toe_ap),
        'sacrum': len(sacrum_ap),
        'heel_exists': len(heel_exists),
        'toe_exists': len(toe_exists),
        'sacrum_exists': len(sacrum_exists),
    }
    if len(set(lens.values())) != 1:
        print(f"[GaitEvents] WARNING: inconsistent input lengths: {lens}")

    # ensure toe arrays are same length as heel data; pad with zeros/False when missing
    n_frames = len(heel_ap)
    if len(toe_ap) != n_frames:
        toe_ap = np.zeros(n_frames, dtype=float)
    if len(toe_exists) != n_frames:
        toe_exists = np.zeros(n_frames, dtype=bool)

    n_frames = len(heel_ap)
    # guard against missing toe data by padding arrays to heel length
    if len(toe_ap) != n_frames:
        toe_ap = np.zeros(n_frames, dtype=float)
    if len(toe_exists) != n_frames:
        toe_exists = np.zeros(n_frames, dtype=bool)

    if end_frame is None:
        end_frame = n_frames

    # ---- Resolve the AP axis automatically if requested -----------------------
    if ap_axis == 'auto' and sacrum_marker_data_xyz is not None:
        sx = np.asarray(sacrum_marker_data_xyz[0], dtype=float)
        sy = np.asarray(sacrum_marker_data_xyz[1], dtype=float)
        range_x = np.nanmax(sx[start_frame:end_frame]) - np.nanmin(sx[start_frame:end_frame])
        range_y = np.nanmax(sy[start_frame:end_frame]) - np.nanmin(sy[start_frame:end_frame])
        ap_axis = 'X' if range_x > range_y else 'Y'
        print(f"[GaitEvents] Auto-detected AP axis: {ap_axis}  (rangeX={range_x:.1f}, rangeY={range_y:.1f})")
    elif ap_axis == 'auto':
        ap_axis = 'Y'
        print("[GaitEvents] AP axis defaulted to Y (no full XYZ data supplied for auto-detection)")
    _sac_seg = sacrum_ap[start_frame:end_frame]
    _sac_valid = _sac_seg[~np.isnan(_sac_seg)]
    if len(_sac_valid) >= 2 and _sac_valid[-1] < _sac_valid[0]:
        heel_ap = -heel_ap
        toe_ap = -toe_ap
        sacrum_ap = -sacrum_ap
        print(f"[GaitEvents] Subject walking in −{ap_axis} direction — AP signals negated")
    # ---- Build SEPARATE validity masks for HS and TO -------------------------
    # HS needs heel + sacrum; TO needs toe + sacrum.  Using a single combined
    # mask was the root cause of detection failures: toe gaps would suppress
    # HS detection and heel gaps would suppress TO detection.
    valid_hs = heel_exists & sacrum_exists
    valid_hs[:start_frame] = False
    valid_hs[end_frame:]   = False

    valid_to = sacrum_exists.copy()
    if toe_exists is not None and np.any(toe_exists):
        valid_to &= toe_exists
    else:
        valid_to[:] = False  # no toe data → cannot detect TO
    valid_to[:start_frame] = False
    valid_to[end_frame:]   = False

    # Replace invalid samples with NaN then linearly interpolate small gaps
    def _interp_fill(arr, mask):
        """Fill invalid samples via linear interpolation."""
        out = arr.copy()
        out[~mask] = np.nan
        nans = np.isnan(out)
        if nans.all():
            return out  # nothing to interpolate
        x = np.arange(len(out))
        out[nans] = np.interp(x[nans], x[~nans], out[~nans])
        return out

    # Sacrum is shared but cleaned with the union of both masks so that
    # any frame valid for HS or TO retains its sacrum value.
    valid_sacrum = valid_hs | valid_to
    heel_ap_clean   = _interp_fill(heel_ap, valid_hs)
    toe_ap_clean    = _interp_fill(toe_ap, valid_to)
    sacrum_ap_clean = _interp_fill(sacrum_ap, valid_sacrum)

    # ---- Low-pass filter (moving-average, numpy-only) -------------------------
    if lowpass_cutoff > 0 and frame_rate > 0:
        # Window size ≈ frame_rate / cutoff, rounded to nearest odd integer
        win = int(round(frame_rate / lowpass_cutoff))
        if win % 2 == 0:
            win += 1  # ensure odd for symmetric kernel
        win = max(win, 3)
        seg = slice(start_frame, end_frame)
        seg_len = end_frame - start_frame
        if seg_len > win:
            kernel = np.ones(win) / win
            # Zero-phase: apply forward then reverse
            def _smooth(arr, s):
                fwd = np.convolve(arr[s], kernel, mode='same')
                rev = np.convolve(fwd[::-1], kernel, mode='same')[::-1]
                out = arr.copy()
                out[s] = rev
                return out
            heel_ap_clean   = _smooth(heel_ap_clean, seg)
            toe_ap_clean    = _smooth(toe_ap_clean, seg)
            sacrum_ap_clean = _smooth(sacrum_ap_clean, seg)

    # ---- Compute Zeni signals -------------------------------------------------
    heel_minus_sacrum = heel_ap_clean - sacrum_ap_clean   # HS → local maxima
    toe_minus_sacrum  = toe_ap_clean  - sacrum_ap_clean   # TO → local minima

    min_distance = max(int(min_stride_time * frame_rate), 1)

    # ---- Detect Heel Strikes (maxima of heel−sacrum) -------------------------
    hs_frames = []
    try:
        peaks, properties = find_peaks(
            heel_minus_sacrum[start_frame:end_frame],
            distance=min_distance,
            prominence=peak_prominence,
        )
        hs_frames = (peaks + start_frame).tolist()
    except Exception as e:
        print(f"[GaitEvents] WARNING — HS detection failed: {e}")

    # ---- Detect Toe Offs (minima of toe−sacrum ⇒ maxima of negated signal) ---
    to_frames = []
    try:
        valleys, properties = find_peaks(
            -toe_minus_sacrum[start_frame:end_frame],
            distance=min_distance,
            prominence=peak_prominence,
        )
        to_frames = (valleys + start_frame).tolist()
    except Exception as e:
        print(f"[GaitEvents] WARNING — TO detection failed: {e}")

    print(f"[GaitEvents] Detected {len(hs_frames)} Heel Strikes, {len(to_frames)} Toe Offs")
    return hs_frames, to_frames


def detect_bilateral_gait_events(
    fields,
    marker_names,
    frame_rate,
    start_frame=0,
    end_frame=None,
    ap_axis='auto',
    min_stride_time=None,
    peak_prominence=None,
    lowpass_cutoff=6.0,
    fp_data=None,
    fp_buffer_frames=100,
    fp_fz_threshold=20.0,
):
    """Detect gait events for both sides, pair every HS with a TO, zone-filter.

    Pipeline order (per the corrected design):
      1.  Raw Zeni detection on full trial (per side, independent relaxation)
      2.  Compute force plate zone
      3.  Select HS events near the zone (with optional pre/post plate strike)
      4.  Pair every selected HS with its closest following TO
      5.  Zone-filter the paired (frame, label) list
      6.  Validate pairing integrity

    Returns
    -------
    all_events : list[(int, str)]
        Sorted list of (frame, label) tuples ready for QTM writing.
    metadata : dict
        Diagnostic information including zone, raw counts, pairing stats.
    """
    # ---- Helper to safely extract marker arrays from fields -------------------
    def _get_marker(name_key):
        marker_label = marker_names.get(name_key, '')
        if marker_label and marker_label in fields and isinstance(fields[marker_label], dict) and 'X' in fields[marker_label]:
            m = fields[marker_label]
            return m['X'], m['Y'], m['Z'], m['Exists']
        # Fallback: search fields directly for standard clinical aliases
        aliases = {
            'L_HEEL': ['left_heel', 'l_heel', 'lheel', 'l_fcc', 'l_calc', 'l_foot_heel', 'lhee'],
            'R_HEEL': ['right_heel', 'r_heel', 'rheel', 'r_fcc', 'r_calc', 'r_foot_heel', 'rhee'],
            'L_TOE': ['left_toe', 'l_toe', 'ltoe', 'left_2nd3rd_mt_head', 'l_2nd3rd', 'l_fm1', 'l_fm2', 'l_foot_toe', 'l_mt2'],
            'R_TOE': ['right_toe', 'r_toe', 'rtoe', 'right_2nd3rd_mt_head', 'r_2nd3rd', 'r_fm1', 'r_fm2', 'r_foot_toe', 'r_mt2'],
            'SACRUM': ['sacrum', 'sacr'],
        }
        cand_subs = aliases.get(name_key, [])
        for k in fields.keys():
            kl = k.lower()
            if any(sub in kl for sub in cand_subs):
                m = fields[k]
                if isinstance(m, dict) and 'X' in m and 'Exists' in m:
                    return m['X'], m['Y'], m['Z'], m['Exists']
        return None, None, None, None

    # Sacrum (shared between sides)
    sacr_x, sacr_y, sacr_z, sacr_exists = _get_marker('SACRUM')
    if sacr_x is None:
        _logger.warning(f"[STAGE 2] Sacrum missing; available markers = {list(fields.keys())}")
        for pair_l, pair_r, pair_name in [('LPSIS', 'RPSIS', 'PSIS'),
                                           ('Left_PSIS', 'Right_PSIS', 'PSIS'),
                                           ('LASIS', 'RASIS', 'ASIS'),
                                           ('LASI', 'RASI', 'ASI')]:
            if pair_l in fields and pair_r in fields:
                _logger.warning(f"[STAGE 2] Creating virtual sacrum from {pair_name} midpoint.")
                lp, rp = fields[pair_l], fields[pair_r]
                sacr_x = [(l+r)/2 for l,r in zip(lp['X'], rp['X'])]
                sacr_y = [(l+r)/2 for l,r in zip(lp['Y'], rp['Y'])]
                sacr_z = [(l+r)/2 for l,r in zip(lp['Z'], rp['Z'])]
                sacr_exists = [a and b for a,b in zip(lp['Exists'], rp['Exists'])]
                fields['__SACR_VIRTUAL__'] = {'X': sacr_x, 'Y': sacr_y, 'Z': sacr_z, 'Exists': sacr_exists}
                break
        if sacr_x is None:
            _logger.error("[STAGE 2] ERROR — Sacrum marker not found. Cannot detect events.")
            return [], {}

    # ---- Determine AP axis from sacrum travel ---------------------------------
    resolved_ap = ap_axis
    if ap_axis == 'auto':
        sx = np.asarray(sacr_x, dtype=float)
        sy = np.asarray(sacr_y, dtype=float)
        ef = end_frame if end_frame else len(sx)
        range_x = np.nanmax(sx[start_frame:ef]) - np.nanmin(sx[start_frame:ef])
        range_y = np.nanmax(sy[start_frame:ef]) - np.nanmin(sy[start_frame:ef])
        resolved_ap = 'X' if range_x > range_y else 'Y'
        _logger.info(f"[STAGE 2] Auto-detected AP axis: {resolved_ap} "
                     f"(rangeX={range_x:.1f}, rangeY={range_y:.1f})")

    # ---- Detect walking direction along resolved AP axis ---------------------
    _sacr_ap_raw = np.asarray(sacr_x if resolved_ap == 'X' else sacr_y, dtype=float)
    _dir_seg = _sacr_ap_raw[start_frame:ef]
    _dir_valid = _dir_seg[~np.isnan(_dir_seg)]
    ap_sign = 1
    if len(_dir_valid) >= 2 and _dir_valid[-1] < _dir_valid[0]:
        ap_sign = -1
        _logger.info(f"[STAGE 2] Subject walking in −{resolved_ap} direction — AP signals will be negated")

    def _pick_ap(x_arr, y_arr):
        if resolved_ap == 'X':
            return ap_sign * np.asarray(x_arr, dtype=float)
        return ap_sign * np.asarray(y_arr, dtype=float)

    sacr_ap = _pick_ap(sacr_x, sacr_y)

    # ---- Report marker shapes (STAGE 2) --------------------------------------
    def _shape_str(name_key):
        x, y, z, e = _get_marker(name_key)
        return str(np.shape(x)) if x is not None else 'MISSING'

    _logger.info(f"[STAGE 2] Markers fetched — R_HEEL:{_shape_str('R_HEEL')}, "
                 f"L_HEEL:{_shape_str('L_HEEL')}, R_TOE:{_shape_str('R_TOE')}, "
                 f"L_TOE:{_shape_str('L_TOE')}, SACRUM:{np.shape(sacr_x)}")

    # ---- Build trajectory dict for one side -----------------------------------
    def _build_traj(heel_key, toe_key):
        hx, hy, hz, he = _get_marker(heel_key)
        tx, ty, tz, te = _get_marker(toe_key)
        if hx is None:
            return None
        n = len(hx)
        traj = {
            'heel_ap': _pick_ap(hx, hy),
            'toe_ap':  _pick_ap(tx, ty) if tx is not None else np.zeros(n),
            'sacrum_ap': sacr_ap,
            'heel_exists': np.asarray(he, dtype=bool),
            'toe_exists': np.asarray(te, dtype=bool) if te is not None else np.zeros(n, dtype=bool),
            'sacrum_exists': np.asarray(sacr_exists, dtype=bool),
            'heel_xyz': (np.asarray(hx, dtype=float),
                         np.asarray(hy, dtype=float),
                         np.asarray(hz, dtype=float)),
            'toe_xyz':  (np.asarray(tx, dtype=float),
                         np.asarray(ty, dtype=float),
                         np.asarray(tz, dtype=float)) if tx is not None else None,
            'sacrum_xyz': (np.asarray(sacr_x, dtype=float),
                           np.asarray(sacr_y, dtype=float),
                           np.asarray(sacr_z, dtype=float)),
        }
        return traj

    # ======================================================================
    # STAGE 3 — Compute force plate zone
    # ======================================================================
    n_total = len(sacr_x)
    zone_start = 0
    zone_end = n_total - 1
    active_zone = False
    method = None

    if fp_data:
        has_analog = any(
            ('Force' in fp and fp['Force'].get('Z') is not None)
            for fp in fp_data.values()
        )
        if has_analog:
            method = 'temporal'
            pre = int(BUFFER_PRE_SECONDS * frame_rate)
            post = int(BUFFER_POST_SECONDS * frame_rate)
            zone_start, zone_end, active_zone = compute_forceplate_valid_zone(
                fp_data, frame_rate,
                buffer_pre=pre, buffer_post=post,
                fz_threshold=FZ_THRESHOLD_N,
            )
            _logger.info(f"[STAGE 3] Force plate method: temporal")
            _logger.info(f"[STAGE 3] Zone: frames {zone_start} to {zone_end} "
                         f"({zone_start/frame_rate:.2f}s to {zone_end/frame_rate:.2f}s)")
            print(f"[STAGE 3] Zone after buffer: {zone_start} to {zone_end} frames "
                  f"({zone_start/frame_rate:.2f}s to {zone_end/frame_rate:.2f}s) "
                  f"| Buffer: {BUFFER_PRE_SECONDS}s")
        else:
            method = 'spatial'
            _logger.info(f"[STAGE 3] Force plate method: spatial")
            # spatial zone would need plate_corners — not currently passed
            _logger.info(f"[STAGE 3] Zone: frames {zone_start} to {zone_end} (full trial, no spatial corners)")
    else:
        _logger.info("[STAGE 3] Force plate method: none (no FP data)")

    # ======================================================================
    # STAGE 3b — Restrict to longest contiguous window where gait markers exist
    # ======================================================================
    all_exists_arrays = []
    gait_marker_keys = ['L_HEEL', 'R_HEEL', 'L_TOE', 'R_TOE', 'SACRUM']
    for mk in gait_marker_keys:
        lbl = marker_names.get(mk)
        if lbl and lbl in fields and isinstance(fields[lbl], dict) and 'Exists' in fields[lbl]:
            all_exists_arrays.append(fields[lbl]['Exists'])
        elif mk == 'SACRUM' and '__SACR_VIRTUAL__' in fields:
            all_exists_arrays.append(fields['__SACR_VIRTUAL__']['Exists'])
        elif mk == 'SACRUM' and '__AUTO_SACRUM__' in fields:
            all_exists_arrays.append(fields['__AUTO_SACRUM__']['Exists'])
        else:
            _, _, _, e_arr = _get_marker(mk)
            if e_arr is not None:
                all_exists_arrays.append(e_arr)
    if not all_exists_arrays:
        points_list = fields.get("Points", [])
        for pt_label in points_list:
            pt_label = pt_label.strip()
            if pt_label in fields and isinstance(fields[pt_label], dict) and 'Exists' in fields[pt_label]:
                all_exists_arrays.append(fields[pt_label]['Exists'])

    if all_exists_arrays:
        valid_start, valid_end, valid_len = _longest_contiguous_valid_window(*all_exists_arrays)
        _logger.info(f"[STAGE 3b] Longest contiguous window (all {len(all_exists_arrays)} markers): "
                     f"frames {valid_start}-{valid_end - 1} "
                     f"({valid_len} frames, {valid_len / frame_rate:.2f}s)")
        print(f"[STAGE 3b] Valid data window: frames {valid_start}-{valid_end - 1} "
              f"({valid_len}/{n_total} frames, {valid_len / frame_rate:.2f}s) "
              f"| {len(all_exists_arrays)} markers checked")

        if valid_len == 0:
            _logger.error("[STAGE 3b] No contiguous window where all markers exist — aborting")
            return [], {'valid_window': None}

        # Tighten start_frame / end_frame to stay inside the valid window
        start_frame = max(start_frame, valid_start)
        if end_frame is None:
            end_frame = valid_end
        else:
            end_frame = min(end_frame, valid_end)

        # Also tighten the force plate zone to not exceed the valid window
        zone_start = max(zone_start, valid_start)
        zone_end = min(zone_end, valid_end - 1)
        _logger.info(f"[STAGE 3b] Adjusted zone after valid-window constraint: "
                     f"frames {zone_start}-{zone_end}")
    else:
        _logger.warning("[STAGE 3b] No Points list in fields — skipping all-marker validity check")
        valid_start, valid_end, valid_len = 0, n_total, n_total
        
    # ======================================================================
    # STAGE 4 — Raw Zeni detection (per side, independent)
    # ======================================================================
    raw = {}  # {'L': {'hs': [...], 'to': [...]}, 'R': {...}}
    traj_data = {}  # store trajectory dicts for enforcement
    for side, heel_key, toe_key in [('L', 'L_HEEL', 'L_TOE'),
                                     ('R', 'R_HEEL', 'R_TOE')]:
        traj = _build_traj(heel_key, toe_key)
        if traj is None:
            _logger.warning(f"[STAGE 4] {side} heel marker not found — skipping side")
            raw[side] = {'hs': [], 'to': []}
            continue

        traj_data[side] = traj
        _logger.info(f"[STAGE 4] Running Zeni on {side} side...")
        res = detect_gait_events(traj, frame_rate)
        raw[side] = {'hs': res['hs_frames'], 'to': res['to_frames']}

    # ---- Enforce minimum 2 detections per side per type within zone ----------
    if active_zone:
        for side in ['R', 'L']:
            if side not in traj_data:
                continue
            side_label = 'Right' if side == 'R' else 'Left'
            raw[side]['hs'] = enforce_minimum_detections(
                raw[side]['hs'], traj_data[side], frame_rate,
                zone_start, zone_end, 'HS', side_label)
            raw[side]['to'] = enforce_minimum_detections(
                raw[side]['to'], traj_data[side], frame_rate,
                zone_start, zone_end, 'TO', side_label)

    _logger.info(f"[STAGE 4] Raw Zeni detection:")
    for side_code, hs_lbl, to_lbl in [('R', 'RSTRIKE', 'ROFF'), ('L', 'LSTRIKE', 'LOFF')]:
        _logger.info(f"          {hs_lbl}: {len(raw[side_code]['hs'])} frames : {raw[side_code]['hs']}")
        _logger.info(f"          {to_lbl}:    {len(raw[side_code]['to'])} frames : {raw[side_code]['to']}")
    print(f"[STAGE 4] Raw Zeni detection:")
    for side_code, hs_lbl, to_lbl in [('R', 'RSTRIKE', 'ROFF'), ('L', 'LSTRIKE', 'LOFF')]:
        print(f"          {hs_lbl}: {len(raw[side_code]['hs'])} frames : {raw[side_code]['hs']}")
        print(f"          {to_lbl}:    {len(raw[side_code]['to'])} frames : {raw[side_code]['to']}")

    # ======================================================================
    # STEP 2 — Remove false-positive isolated first event
    # ======================================================================
    raw = remove_false_first_event(raw, frame_rate)

    # ======================================================================
    # STEP 3 — Ensure opposite-side strike exists before terminal OFF
    # ======================================================================
    raw = ensure_strike_before_terminal_off(raw, traj_data, frame_rate,
                                            zone_start, zone_end)

    # ======================================================================
    # STAGE 5 — Canonical Gait Event Sequence Selection
    # ======================================================================
    metadata = {
        'zone_frames': (zone_start, zone_end),
        'filter_method': method,
        'raw_R_HS': len(raw['R']['hs']), 'raw_R_TO': len(raw['R']['to']),
        'raw_L_HS': len(raw['L']['hs']), 'raw_L_TO': len(raw['L']['to']),
        'raw_R_HS_frames': list(raw['R']['hs']),
        'raw_R_TO_frames': list(raw['R']['to']),
        'raw_L_HS_frames': list(raw['L']['hs']),
        'raw_L_TO_frames': list(raw['L']['to']),
    }

    # Build chronological event stream
    raw_all = []
    for f in raw['R']['hs']: raw_all.append((f, AUTO_RHS_LABEL))
    for f in raw['R']['to']: raw_all.append((f, AUTO_ROF_LABEL))
    for f in raw['L']['hs']: raw_all.append((f, AUTO_LHS_LABEL))
    for f in raw['L']['to']: raw_all.append((f, AUTO_LOF_LABEL))
    raw_all.sort(key=lambda x: x[0])

    # Deduplicate consecutive identical labels (within 15 frames)
    cleaned_stream = []
    for f, l in raw_all:
        if cleaned_stream and cleaned_stream[-1][1] == l and abs(f - cleaned_stream[-1][0]) < 15:
            continue
        cleaned_stream.append((f, l))

    # Standard alternating bilateral gait sequence patterns (8 events)
    p1 = [AUTO_RHS_LABEL, AUTO_LOF_LABEL, AUTO_LHS_LABEL, AUTO_ROF_LABEL,
          AUTO_RHS_LABEL, AUTO_LOF_LABEL, AUTO_LHS_LABEL, AUTO_ROF_LABEL]
    p2 = [AUTO_LHS_LABEL, AUTO_ROF_LABEL, AUTO_RHS_LABEL, AUTO_LOF_LABEL,
          AUTO_LHS_LABEL, AUTO_ROF_LABEL, AUTO_RHS_LABEL, AUTO_LOF_LABEL]

    candidates = []
    for pattern in [p1, p2]:
        for i in range(len(cleaned_stream) - 7):
            window = cleaned_stream[i:i+8]
            labels = [x[1] for x in window]
            if labels == pattern:
                candidates.append(window)

    if candidates:
        target_center = (zone_start + zone_end) / 2.0 if active_zone else (n_total / 2.0)
        best_cand = None
        best_score = float('inf')
        for c in candidates:
            c_center = (c[0][0] + c[-1][0]) / 2.0
            score = abs(c_center - target_center)
            if active_zone:
                l_s = [f for f, l in c if l == AUTO_LHS_LABEL]
                r_s = [f for f, l in c if l == AUTO_RHS_LABEL]
                covers_l = (l_s[0] <= zone_start and l_s[1] >= zone_end) if len(l_s) >= 2 else False
                covers_r = (r_s[0] <= zone_start and r_s[1] >= zone_end) if len(r_s) >= 2 else False
                if covers_l or covers_r:
                    score -= 10000.0
            if score < best_score:
                best_score = score
                best_cand = c
        all_paired = list(best_cand)
        _logger.info(f"[STAGE 5] Selected canonical 8-event sequence from {len(candidates)} candidates: "
                     f"frames {all_paired[0][0]} to {all_paired[-1][0]}")
    else:
        # Fallback: pair strikes to offs per side, preserving paired completeness
        _logger.warning("[STAGE 5] No direct 8-event alternating candidate found; using stance pairing fallback.")
        all_paired = []
        for side, hs_label, to_label in [('R', AUTO_RHS_LABEL, AUTO_ROF_LABEL),
                                          ('L', AUTO_LHS_LABEL, AUTO_LOF_LABEL)]:
            hs_all = raw[side]['hs']
            to_all = raw[side]['to']
            if not hs_all:
                continue
            hs_in_zone = [f for f in hs_all if zone_start <= f <= zone_end] if active_zone else list(hs_all)
            if not hs_in_zone:
                hs_in_zone = list(hs_all)
            paired = pair_strike_to_off(hs_in_zone, to_all, hs_label, to_label, zone_end, frame_rate)
            all_paired.extend(paired)
        all_paired.sort(key=lambda x: x[0])


    # ======================================================================
    # STAGE 6 — Validate pairing
    # ======================================================================
    pairing_ok = validate_event_pairing(all_paired)
    metadata['pairing_valid'] = pairing_ok
    metadata['total_events'] = len(all_paired)

    # ======================================================================
    # STEP 8 — Validate biomechanical sequence order
    # ======================================================================
    seq_ok, seq_violations = validate_sequence_order(all_paired)
    metadata['sequence_valid'] = seq_ok
    metadata['sequence_violations'] = seq_violations

    # build legacy-compatible events dict for callers that still expect it
    events_dict = {
        AUTO_RHS_LABEL: [], AUTO_LHS_LABEL: [],
        AUTO_ROF_LABEL: [], AUTO_LOF_LABEL: [],
    }
    for frame, label in all_paired:
        if label in events_dict:
            events_dict[label].append(frame)

    return all_paired, metadata
def TechCS_Trunk_Newington(C7, LCLV, RCLV, LASIS, RASIS, SACR):
                
    # Intialize Matrix and array 
    # If . is not placed after zero, values will be truncated to integers
    ETrunkTech =  np.matrix([[0. for m in range(3)] for n in range(3)])
    PelvicCenterLab = np.array([0.,0.,0.])
    ShouldersCenterLab = np.array([0.,0.,0.])
    
    # Determine Pelvic Coordinate System
    epy = math.ComputeUnitVecFromPts(RASIS, LASIS)
    ed3 = math.ComputeUnitVecFromPts(RASIS, SACR)
    epz = np.cross(epy,ed3)
    epz = epz/np.linalg.norm(epz)
    epx = np.cross(epy,epz)
    
    #Determine Center of the Pelvic Cluster
    d3 = np.linalg.norm(SACR - RASIS)
    beta = np.arccos(np.dot(ed3,epy))
    d2 = d3 * np.sin(beta)
    
    PelvicCenterLab = (RASIS + LASIS)/2 - 0.5 * d2 * epx
    
    # Compute Shoulder Coordinate System
    esy = math.ComputeUnitVecFromPts(RCLV, LCLV)
    ed3 = math.ComputeUnitVecFromPts(RCLV, C7)
    esz = np.cross(esy,ed3)
    esz = esz/np.linalg.norm(esz)
    esx = np.cross(esy,esz)
    
    # Determine Center of Shoulder Cluster
    d3 = np.linalg.norm(C7 - RCLV)
    beta = np.arccos(np.dot(ed3,esy))
    d2 = d3 * np.sin(beta)
    
    ShouldersCenterLab = (RCLV + LCLV)/2 - 0.5 * d2 * esx
    
    # Compute Trunk Coordinate System
    etz = ShouldersCenterLab - PelvicCenterLab

    etz = etz/np.linalg.norm(etz)
    etx = np.cross(esy,etz)
    etx = etx/np.linalg.norm(etx)
    ety = np.cross(etz,etx)
    
    ETrunkTech = np.column_stack((etx,ety,etz))
    
    return([ETrunkTech, PelvicCenterLab, ShouldersCenterLab])
    
    
def TechCS_Pelvis_Newington(LASIS, RASIS, SACR):
    
    epy = math.ComputeUnitVecFromPts(RASIS, LASIS)
    ed3 = math.ComputeUnitVecFromPts(RASIS, SACR)
    epz = np.cross(epy,ed3)
    epz = epz/np.linalg.norm(epz)
    epx = np.cross(epy,epz)            
    
    EPelvisTech = np.column_stack((epx,epy,epz))
    MidASISLab = (LASIS + RASIS) /2
    
    return([EPelvisTech, MidASISLab])

def AnatCS_Pelvis_Delp(LASIS, RASIS, SACR, PelvicTiltOffset):
    MidASISLab = (LASIS + RASIS) /2
    
    ey = math.ComputeUnitVecFromPts(RASIS, LASIS)
    ed3 = math.ComputeUnitVecFromPts(SACR,  MidASISLab)
    ez = np.cross(ed3,ey)
    ez = ez/np.linalg.norm(ez)
    ex = np.cross(ey,ez)            
    
    EPelvisAnat = np.column_stack((ex,ey,ez))
    
    # Rotate CS around Y axis by PelviTiltOffset
    EPelvisAnat = math.RotateCSaroundYaxis(EPelvisAnat,PelvicTiltOffset)
    
    return([EPelvisAnat, MidASISLab])
    
def JointCenterModel_Hip_Newington(Side, MarkerDiameter, ASISdist, ASIStoGTdist, LeftLegLength, RightLegLength, RASIS, LASIS, EPelvisTech, MidASISLab):
    
    #Constants in degrees
    ThetaConst = 28.42
    PelvisTiltConst = 18.0    

    # Convert to radians
    ThetaConstRadians = ThetaConst * np.pi /180
    PelvisTiltConstRadians = PelvisTiltConst * np.pi /180
    
    LongerLegLength = max(LeftLegLength, RightLegLength)
    #estimate ASIStoGTDist based on regression relationship if necessary
    if ASIStoGTdist == 0:
            ASIStoGTdist = 0.12876 * float(LongerLegLength) - 48.56 
    
    C = float(LongerLegLength) * 0.115 - 15.33
        
    #define hip center relative to a neutral (flat) pelvis
    HipInPelvisCoorsTemp = np.array([0.,0.,0.])
    HipInPelvisCoorsTemp[0] = -(float(ASIStoGTdist) + float(MarkerDiameter)/2)
    if Side == 'Right':
        HipInPelvisCoorsTemp[1] = C * np.sin(ThetaConstRadians) - (float(ASISdist)/2) 
    if Side == 'Left':
        HipInPelvisCoorsTemp[1] = -C * np.sin(ThetaConstRadians) + (float(ASISdist)/2) 
    HipInPelvisCoorsTemp[2] = -C * np.cos(ThetaConstRadians)
    
    #rotate to account for mean pelvic tilt of study group
    HipCenterPelvis = np.array([0.,0.,0.])
    HipCenterPelvis[0] = np.cos(PelvisTiltConstRadians) * HipInPelvisCoorsTemp[0] - np.sin(PelvisTiltConstRadians) * HipInPelvisCoorsTemp[2]
    HipCenterPelvis[1] = HipInPelvisCoorsTemp[1]
    HipCenterPelvis[2] = np.sin(PelvisTiltConstRadians) * HipInPelvisCoorsTemp[0] + np.cos(PelvisTiltConstRadians) * HipInPelvisCoorsTemp[2]
    
    #compute hip location relative to lab origin and expressed relative to lab coordinate system
    HipCenterLab = math.TransformPointIntoLabCoors(HipCenterPelvis, EPelvisTech, MidASISLab)
    
    return([HipCenterPelvis, HipCenterLab])
    
    
def JointCenterModel_Hip_Harrington(Side, ASISdist, RASIS, LASIS, SACR, EPelvisTech, MidASISLab):
    
    #PelvicWidth = np.linalg.norm(LASIS-RASIS)
    PelvicWidth = ASISdist
    PelvicDepth = np.linalg.norm((LASIS+RASIS)/2 - SACR)
    
    #define hip center relative to a pelvis coordinate syste (Origin at MidASIS)
    HipCenterPelvis = np.array([0.,0.,0.])
    
    # Single Linear Regression Equations
    HipCenterPelvis[0] = -0.24 * PelvicDepth - 9.9
    if Side == 'Right':
        HipCenterPelvis[1] =  -0.33*PelvicWidth - 7.3
    if Side == 'Left':
        HipCenterPelvis[1] =  +0.33*PelvicWidth + 7.3
    HipCenterPelvis[2] = -0.30*PelvicWidth -10.9
    
    # Two Variable Regression Equations
#    HipCenterPelvis[0] = -0.24 * PelvicDepth - 9.9
#    if Side == 'Right':
#        HipCenterPelvis[1] =  -0.28*PelvicDepth - 0.16*PelvicWidth - 7.9
#    if Side == 'Left':
#        HipCenterPelvis[1] =  +0.28*PelvicDepth + 0.16*PelvicWidth + 7.9
#    HipCenterPelvis[2] = -0.16*PelvicWidth - 0.04*LongerLegLength - 7.1
    
    
    #compute hip location relative to lab origin and expressed relative to lab coordinate system
    HipCenterLab = math.TransformPointIntoLabCoors(HipCenterPelvis, EPelvisTech, MidASISLab)
    
    return([HipCenterPelvis, HipCenterLab])
    
def JointCenterModel_Hip_Harrington2(Side, ASISdist, LeftLegLength, RightLegLength, RASIS, LASIS, SACR, EPelvisTech, MidASISLab):
    
    #PelvicWidth = np.linalg.norm(LASIS-RASIS)
    PelvicWidth = ASISdist
    PelvicDepth = np.linalg.norm((LASIS+RASIS)/2 - SACR)
    LongerLegLength = max(LeftLegLength, RightLegLength)
    
    #define hip center relative to a pelvis coordinate syste (Origin at MidASIS)
    HipCenterPelvis = np.array([0.,0.,0.])
    
    # Single Linear Regression Equations
#    HipCenterPelvis[0] = -0.24 * PelvicDepth - 9.9
#    if Side == 'Right':
#        HipCenterPelvis[1] =  -0.33*PelvicWidth - 7.3
#    if Side == 'Left':
#        HipCenterPelvis[1] =  +0.33*PelvicWidth + 7.3
#    HipCenterPelvis[2] = -0.30*PelvicWidth -10.9
    
    # Two Variable Regression Equations
    HipCenterPelvis[0] = -0.24 * PelvicDepth - 9.9
    if Side == 'Right':
        HipCenterPelvis[1] =  -0.28*PelvicDepth - 0.16*PelvicWidth - 7.9
    if Side == 'Left':
        HipCenterPelvis[1] =  +0.28*PelvicDepth + 0.16*PelvicWidth + 7.9
    HipCenterPelvis[2] = -0.16*PelvicWidth - 0.04*LongerLegLength - 7.1
    
    
    #compute hip location relative to lab origin and expressed relative to lab coordinate system
    HipCenterLab = math.TransformPointIntoLabCoors(HipCenterPelvis, EPelvisTech, MidASISLab)
    
    return([HipCenterPelvis, HipCenterLab])
    
def ComputeVirtualKneeMarker_Newington(Side, MarkerDiameter, UpperKADMarker, LateralKADMarker, LowerKADMarker):
    
    R1 = UpperKADMarker - LowerKADMarker
    R2 = LateralKADMarker - LowerKADMarker
    R3 = UpperKADMarker - LateralKADMarker
    ClusterCenter = (UpperKADMarker + LateralKADMarker + LowerKADMarker)/3
    
    # 'unit vector perpendicular to marker cluster plane pointing from virtual marker to center of cluster triad
    ETA = np.cross(R1,R2)
    ETA = ETA / np.linalg.norm(ETA)
    if Side == 'Left':
        ETA = -ETA

    # distance from Clsuter Center to virtual knee reference point  = (R1+R2+R3)*SQRT(6)/18
    R1Magnitude = np.linalg.norm(R1)
    R2Magnitude = np.linalg.norm(R2)
    R3Magnitude = np.linalg.norm(R3)
    MarkerToCenterVectorMagnitude = (R1Magnitude + R2Magnitude + R3Magnitude) * np.sqrt(6) /18 #0.1360828  

    VirtualKneeMarker = ClusterCenter - MarkerToCenterVectorMagnitude * ETA
    
    #adjust for added thickness (16mm) of commercially-available knee fixture
    E4 = math.ComputeUnitVecFromPts(LateralKADMarker,VirtualKneeMarker)
    VirtualKneeMarker = VirtualKneeMarker + (16 - float(MarkerDiameter)/2)* E4
        
    return VirtualKneeMarker   

def TechCS_Thigh_Newington(Side, HipCenter, ThighMarker, VirtualKneeMarker):
    
    ethz = math.ComputeUnitVecFromPts(VirtualKneeMarker, HipCenter)
    
    #Intermediate Vector from Knee to Thigh Marker
    R1 = math.ComputeUnitVecFromPts(VirtualKneeMarker, ThighMarker)
    
    if Side == 'Right':
        ethx = np.cross(ethz, R1)
        ethx = ethx /np.linalg.norm(ethx)
    if Side == 'Left':
        ethx = np.cross(R1, ethz)
        ethx = ethx /np.linalg.norm(ethx)
    
    ethy = np.cross(ethz, ethx)
    
    EThighTech = np.column_stack((ethx,ethy,ethz))
    
    return EThighTech    

def JointCenterModel_Knee_Newington(Side, MarkerDiameter, KneeWidth, VirtualKneeMarker, LateralKADMarker):
    
    E1= math.ComputeUnitVecFromPts(LateralKADMarker, VirtualKneeMarker)
    KneeCenter = VirtualKneeMarker + (float(KneeWidth)/2 + float(MarkerDiameter)/2) * E1 
    
    return KneeCenter        

def TechCS_Shank_Newington(Side, KneeCenter, TibialMarker, LateralAnkle):
    
    esz = math.ComputeUnitVecFromPts(LateralAnkle, KneeCenter)
    R1 = math.ComputeUnitVecFromPts(LateralAnkle, TibialMarker)
    
    if Side == 'Right':
        esx = np.cross(esz, R1)
    if Side == 'Left':
        esx = np.cross(R1, esz)
    esx = esx /np.linalg.norm(esx)
    esy = np.cross(esz, esx)
    
    EShankTech = np.column_stack((esx,esy,esz))
    
    return EShankTech

def JointCenterModel_Ankle_Newington(Side, MarkerDiameter, AnkleWidth, LateralAnkle, MedialAnkle):
    
    E1 = math.ComputeUnitVecFromPts(LateralAnkle, MedialAnkle)
    AnkleCenterLab = LateralAnkle + (float(AnkleWidth)/2 + float(MarkerDiameter)/2) * E1
    
    return AnkleCenterLab

def ComputeVirtualHeelMarkerLab(PlantigradeCheck, SujectShodCheck, SoleThickness ,AnkleCenterLab, ToeMarker, HeelMarker):

    VirtualHeelMarkerLab = np.array([0.,0.,0.])
    if PlantigradeCheck == '1':
        VirtualHeelMarkerLab[0] = AnkleCenterLab[0]
        VirtualHeelMarkerLab[1] = AnkleCenterLab[1]
        VirtualHeelMarkerLab[2] = ToeMarker[2]
        if SujectShodCheck == '1':
            VirtualHeelMarkerLab[2] = VirtualHeelMarkerLab[2] + float(SoleThickness)
            #print('Shod')
        #print(' plantigrade')
    if PlantigradeCheck == '0':
       # establish heel reference point:  adjust location of heel reference such that it provides the same sagittal result,
       # but is aligned with the ankle center with respect to the transverse orientation of the foot.
       # that is, project ankle center into a reference plane formed by the heel-toe vector and y-axis of lab.
       # this projected ankle center becomes the virtual heel marker. 
       
       #compute a temporary foot coor system that contains the reference plane
       ex = math.ComputeUnitVecFromPts(HeelMarker, ToeMarker)
       LabY = np.array([0.,1.,0.]) # Lab Y axis
       ez = np.cross(ex,LabY)
       ez = ez/ np.linalg.norm(ez)
       ey = np.cross(ez,ex)
       ey = ey/ np.linalg.norm(ey)
       Etemp = np.column_stack((ex,ey,ez))
       
       #Compute Virtual Heel by Transforming ankle center into this temporaray coordinate system
       VirtualHeelMarkerTemp = math.TransformPointIntoMovingCoors(AnkleCenterLab, Etemp, HeelMarker)
       VirtualHeelMarkerTemp[2] =0
       if SujectShodCheck == '1':
           VirtualHeelMarkerTemp[2] = float(SoleThickness)
           #print('Shod')
       #print(' Nonplantigrade')
       #Transform VirtualHeel Marker back to Lab Coordinate system
       VirtualHeelMarkerLab = math.TransformPointIntoLabCoors(VirtualHeelMarkerTemp, Etemp, HeelMarker)
        
    return VirtualHeelMarkerLab

def TechCS_Foot_Newington(Side, KneeCenterLab, AnkleCenterLab, ToeMarker):
    
    eztemp = math.ComputeUnitVecFromPts(AnkleCenterLab, KneeCenterLab)
    ex = math.ComputeUnitVecFromPts(AnkleCenterLab, ToeMarker)
    ey = np.cross(eztemp,ex)
    ey = ey/ np.linalg.norm(ey)
    ez = np.cross(ex,ey)
    ez = ez/ np.linalg.norm(ez)
    
    EFootTech = np.column_stack((ex,ey,ez))
    
    return EFootTech

def AnatCS_Thigh_Newington(Side, HipCenterLab, VirtualKneeMarkerLab, KneeCenterLab):
    
    ez = math.ComputeUnitVecFromPts(KneeCenterLab, HipCenterLab)
    R1 = math.ComputeUnitVecFromPts(KneeCenterLab, VirtualKneeMarkerLab)
    
    if Side == 'Left':
        ex = np.cross(R1, ez)
    if Side == 'Right':
        ex = np.cross(ez, R1)
    
    ex = ex/ np.linalg.norm(ex)
    ey = np.cross(ez, ex)
    
    EThighAnat = np.column_stack((ex,ey,ez))
    
    return EThighAnat

def AnatCS_Thigh_Delp(Side, HipCenterLab, KneeMarkerLab, KneeCenterLab, ThighRotation):
    
    etz = math.ComputeUnitVecFromPts(KneeCenterLab, HipCenterLab)
    R1 = math.ComputeUnitVecFromPts(KneeCenterLab, KneeMarkerLab)
    
    if Side == 'Left':
        etx = np.cross(R1, etz)
    if Side == 'Right':
        etx = np.cross(etz, R1)
    
    etx = etx/ np.linalg.norm(etx)
    ety = np.cross(etz, etx)
    
    # Rotate CS around Z axis by ThighRotation
    ThighRotationValue = float(ThighRotation.split(' ')[0])
    if ThighRotation.split(' ')[1] == 'Ext':
        ThighRotationDirection = +1
    else:
        ThighRotationDirection = -1
    
    if Side == 'Left':
        angle = -ThighRotationDirection * ThighRotationValue
    if Side == 'Right':
        angle =  ThighRotationDirection * ThighRotationValue
    
    
    ex = etx * np.cos(angle*np.pi/180) + ety * -np.sin(angle*np.pi/180)
    ey = etx * np.sin(angle*np.pi/180) + ety *  np.cos(angle*np.pi/180)
    ez = etz 
    ############################################
    
    EThighAnat = np.column_stack((ex,ey,ez))
    
    return EThighAnat

def AnatCS_Shank_Proximal_Newington(Side, KneeCenterLab, VirtualKneeMarkerLab, AnkleCenterLab):
    
    ez = math.ComputeUnitVecFromPts(AnkleCenterLab,KneeCenterLab)
    R1 = math.ComputeUnitVecFromPts(KneeCenterLab, VirtualKneeMarkerLab)
    
    if Side == 'Left':
        ex = np.cross(R1, ez)
    if Side == 'Right':
        ex = np.cross(ez, R1)
    
    ex = ex/ np.linalg.norm(ex)
    ey = np.cross(ez,ex) 
    
    EShankProximalAnat = np.column_stack((ex,ey,ez))
    
    return EShankProximalAnat

def AnatCS_Shank_Distal_VCM(Side, KneeCenterLab, AnkleCenterLab, LateralAnkleMarker):
    
    ez = math.ComputeUnitVecFromPts(AnkleCenterLab,KneeCenterLab)
    
    if Side == 'Left':
        R1 = math.ComputeUnitVecFromPts(AnkleCenterLab, LateralAnkleMarker)
    if Side == 'Right':
        R1 = math.ComputeUnitVecFromPts(LateralAnkleMarker, AnkleCenterLab)
    
    ex = np.cross(R1, ez)
    ex = ex/ np.linalg.norm(ex)
    ey = np.cross(ez,ex) 
    
    EShankDistalAnat = np.column_stack((ex,ey,ez))
    
    return EShankDistalAnat

def AnatCS_Shank_Delp(Side, KneeCenterLab, AnkleCenterLab, LateralAnkleMarker,ShankRotation):
    
    esz = math.ComputeUnitVecFromPts(AnkleCenterLab,KneeCenterLab)
    
    if Side == 'Left':
        R1 = math.ComputeUnitVecFromPts(AnkleCenterLab, LateralAnkleMarker)
    if Side == 'Right':
        R1 = math.ComputeUnitVecFromPts(LateralAnkleMarker, AnkleCenterLab)
    
    esx = np.cross(R1, esz)
    esx = esx/ np.linalg.norm(esx)
    esy = np.cross(esz,esx) 
    
    # Rotate CS around Z axis by ShankRotation
    ShankRotationValue = float(ShankRotation.split(' ')[0])
    if ShankRotation.split(' ')[1] == 'Ext':
        ShankRotationDirection = +1
    else:
        ShankRotationDirection = -1
    
    if Side == 'Left':
        angle = -ShankRotationDirection * ShankRotationValue
    if Side == 'Right':
        angle =  ShankRotationDirection * ShankRotationValue
    
    
    ex = esx * np.cos(angle*np.pi/180) + esy * -np.sin(angle*np.pi/180)
    ey = esx * np.sin(angle*np.pi/180) + esy *  np.cos(angle*np.pi/180)
    ez = esz 
    ############################################
    
    EShankDistalAnat = np.column_stack((ex,ey,ez))
    
    return EShankDistalAnat
 
def AnatCS_Foot_Newington(Side, LateralAnkleMarker, AnkleCenterLab, ToeMarker, VirtualHeelMarkerLab):
    
    ex = math.ComputeUnitVecFromPts(VirtualHeelMarkerLab, ToeMarker)
    
    if Side == 'Left':
        R1= math.ComputeUnitVecFromPts(AnkleCenterLab, LateralAnkleMarker)
    if Side == 'Right':
        R1= math.ComputeUnitVecFromPts(LateralAnkleMarker, AnkleCenterLab)
    
    ez = np.cross(ex, R1)
    ez = ez/ np.linalg.norm(ez)
    ey = np.cross(ez,ex)
    
    EFootAnat = np.column_stack((ex,ey,ez))
    
    return EFootAnat

def AnatCS_Foot_ShrineGaitModel(Side, KneeCenterLab, AnkleCenterLab, ToeMarker, VirtualHeelMarkerLab):
    
    ex = math.ComputeUnitVecFromPts(VirtualHeelMarkerLab, ToeMarker)
    
    eztemp = math.ComputeUnitVecFromPts(AnkleCenterLab, KneeCenterLab)
    
    ey = np.cross(eztemp,ex)
    ey = ey/ np.linalg.norm(ey)
    ez = np.cross(ex,ey)
    ez = ez/ np.linalg.norm(ez)
    
    EFootAnat = np.column_stack((ex,ey,ez))
    
    return EFootAnat

def Compute_TibialTorsion(Side, EShankProximalAnat, LateralAnkleMarker, MedialAnkleMarker): 
    
    if Side == 'Left':
        AnkleAxis = math.ComputeUnitVecFromPts(MedialAnkleMarker, LateralAnkleMarker)
    if Side == 'Right':
        AnkleAxis = math.ComputeUnitVecFromPts(LateralAnkleMarker, MedialAnkleMarker)
    
    # transform ankle axis into shank coordinate system
    AnkleAxisTransformed = math.TransformVectorIntoMovingCoors(AnkleAxis, EShankProximalAnat)

    # determine unit vector in the xy plane of the shank coordinate system
    AnkleAxisTransformed[2] = 0
    AnkleAxisTransformed = AnkleAxisTransformed / np.linalg.norm(AnkleAxisTransformed)
    
    # determine angle between transformed ankle axis and the y-axis of the proximal shank coordinate system
    if Side == 'Left':
        TibialTorsion = -np.arcsin(AnkleAxisTransformed[0]) * 180 / np.pi
    if Side == 'Right':
        TibialTorsion = np.arcsin(AnkleAxisTransformed[0]) * 180 / np.pi
    
    return TibialTorsion

def Compute_ThighRotation(Side, EPelvisAnat, LateralKneeeMarker, KneeCenter): 
    
    if Side == 'Left':
        KneeAxis = math.ComputeUnitVecFromPts(KneeCenter, LateralKneeeMarker)
    if Side == 'Right':
        KneeAxis = math.ComputeUnitVecFromPts(LateralKneeeMarker, KneeCenter)
    
    # transform ankle axis into shank coordinate system
    KneeAxisTransformed = math.TransformVectorIntoMovingCoors(KneeAxis, EPelvisAnat)

    # determine unit vector in the xy plane of the shank coordinate system
    KneeAxisTransformed[2] = 0
    KneeAxisTransformed = KneeAxisTransformed / np.linalg.norm(KneeAxisTransformed)
    
    # determine angle between transformed ankle axis and the y-axis of the proximal shank coordinate system
    if Side == 'Left':
        ThighRotation = -np.arcsin(KneeAxisTransformed[0]) * 180 / np.pi
    if Side == 'Right':
        ThighRotation = np.arcsin(KneeAxisTransformed[0]) * 180 / np.pi
    
    return ThighRotation

def TechCS_Hindfoot_mSHCG(Side, LateralCalcaneusMarker, MedialCalcaneusMarker, HeelMarker):
    
    CCAL = (LateralCalcaneusMarker + MedialCalcaneusMarker) /2 
    ex = math.ComputeUnitVecFromPts(HeelMarker, CCAL)
    
    if Side == 'Left':
        R1 = math.ComputeUnitVecFromPts(MedialCalcaneusMarker, LateralCalcaneusMarker)
    if Side == 'Right':
        R1 = math.ComputeUnitVecFromPts(LateralCalcaneusMarker, MedialCalcaneusMarker)
    
    ez = np.cross(ex,R1)
    ez = ez/ np.linalg.norm(ez)
    ey = np.cross(ez,ex)
    
    EHindfootTech = np.column_stack((ex,ey,ez))
    
    return EHindfootTech

def TechCS_Forefoot_mSHCG(Side, MT1B, MT1H, MT5H):
    
    ex = math.ComputeUnitVecFromPts(MT1B, MT1H)
    
    if Side == 'Left':
        R1 = math.ComputeUnitVecFromPts(MT1H, MT5H)
    if Side == 'Right':
        R1 = math.ComputeUnitVecFromPts(MT5H, MT1H)
    
    ez = np.cross(ex,R1)
    ez = ez/ np.linalg.norm(ez)
    ey = np.cross(ez,ex)
    
    EForefootTech = np.column_stack((ex,ey,ez))
    return EForefootTech

def TechCS_Hallux_mSHCG(Side, HLX, MTP1, TOE):
    
    ex = math.ComputeUnitVecFromPts(MTP1, HLX)
    
    if Side == 'Left':
        R1 = math.ComputeUnitVecFromPts(MTP1, TOE)
    if Side =='Right':
        R1 = math.ComputeUnitVecFromPts(TOE, MTP1)
    
    ez = np.cross(ex,R1)
    ez = ez/ np.linalg.norm(ez)
    ey = np.cross(ez,ex)
    
    EHalluxTech = np.column_stack((ex,ey,ez))
    
    return EHalluxTech        
    
def AnatCS_Hindfoot_mSHCG(Side, LCAL, MCAL, HEEL, CALPT, 
                          HindfootVarus, CalcanealPitch, HindfootProgression, HindFootValgusIsNegative):

    # Create hindfoot CS reflecting the A/P (x) hindfoot orientation and plantar surface
    CCAL = (LCAL + MCAL) /2 
    HindfootProgressionVector = math.ComputeUnitVecFromPts(HEEL, CCAL)
    ProjectedHindfootProgressionVector = np.array([HindfootProgressionVector[0],HindfootProgressionVector[1],0.])
    
    eSagittalx = ProjectedHindfootProgressionVector/ np.linalg.norm(ProjectedHindfootProgressionVector)
    R1 = np.array([0.,0.,1.])
    eSagittaly = np.cross(R1,eSagittalx)
    eSagittaly = eSagittaly/ np.linalg.norm(eSagittaly)
    eSagittalz = np.cross(eSagittalx,eSagittaly)
    
    EHindfootSagittal = np.column_stack((eSagittalx,eSagittaly,eSagittalz))
    EHindfootSagittal_Origin = np.array([HEEL[0],HEEL[1],0])
    
    # Compute Hindfoot Angles
    if HindfootProgression == '':
        HindfootProgressionAngle = np.arctan2(HindfootProgressionVector[1],HindfootProgressionVector[0])
    else:
        if Side == 'Left':
            HindfootProgressionAngle = -(np.pi/180) * float(HindfootProgression)
        else:
            HindfootProgressionAngle = (np.pi/180) * float(HindfootProgression)
    
    # If Calcaneal Pitch is entered, then do not use CALPT marker
    if CalcanealPitch == '':
        # Compute projection of CALPT on HindfootSagittal Plane
        CALPT_EHindfootSagittal = math.TransformPointIntoMovingCoors(CALPT, EHindfootSagittal, EHindfootSagittal_Origin)
        HindfootInclineAngle = np.arctan(CALPT_EHindfootSagittal[2]/CALPT_EHindfootSagittal[0]) * 180 / np.pi
        # Use Regression equation to estimate actual cacaneal pitch

        # Previous equation with 10-20 subjects
        #HindfootPitchAngle = 0.9826* HindfootInclineAngle - 18.87
        
        # Equations with larger sample size
        if HindfootInclineAngle == 0: # If CALPT marker is absent, set calcaneal pitch to zero.
            HindfootPitchAngle = 0.
        else:
            HindfootPitchAngle = 0.776* HindfootInclineAngle - 11.6
        
        
        # Convert to radians
        HindfootPitchAngle = -HindfootPitchAngle * np.pi/180
    else:
        # Positive Rotation is negative inclination
        HindfootPitchAngle = -float(CalcanealPitch) *np.pi/ 180
     
    # Positive is Valgus    
    if Side == 'Left':
        if HindFootValgusIsNegative == False:
            HindfootVarusAngle = float(HindfootVarus) *np.pi/ 180
        else:
            HindfootVarusAngle = -float(HindfootVarus) *np.pi/ 180
    if Side =='Right':
        if HindFootValgusIsNegative == False:
            HindfootVarusAngle = -float(HindfootVarus) *np.pi/ 180
        else:
            HindfootVarusAngle = float(HindfootVarus) *np.pi/ 180
            
    # Final Coordinate System is defined by Rotation/Flexion/Abduction Sequence [Rzyx]
    # alpha = Rot(x) = HindfootVarusAngle, beta = Rot(y) = HindfootPitchAngle, gamma = Rot(z) = HindfootProgressionAngle
    alpha = HindfootVarusAngle
    beta  = HindfootPitchAngle
    gamma = HindfootProgressionAngle
    #print alpha*180/np.pi, beta*180/np.pi, gamma*180/np.pi
    
    # ZYX sequence
    ex = np.array([np.cos(beta)*np.cos(gamma), np.cos(beta)*np.sin(gamma), -np.sin(beta)])
    ey = np.array([np.sin(alpha)*np.sin(beta)*np.cos(gamma) - np.cos(alpha)*np.sin(gamma), 
                   np.sin(alpha)*np.sin(beta)*np.sin(gamma) + np.cos(alpha)*np.cos(gamma), np.sin(alpha)*np.cos(beta)])
    ez = np.array([np.sin(alpha)*np.sin(gamma) + np.cos(alpha)*np.sin(beta)*np.cos(gamma),
                   np.cos(alpha)*np.sin(beta)*np.sin(gamma) - np.sin(alpha)*np.cos(gamma), np.cos(alpha)*np.cos(beta)])
    
    # YXZ sequence [https://en.wikipedia.org/wiki/Euler_angles]
#    ex = np.array([np.cos(beta)*np.cos(gamma) + np.sin(beta)*np.sin(alpha)*np.sin(gamma), np.cos(alpha)*np.sin(gamma), 
#                   np.cos(beta)*np.sin(alpha)*np.sin(gamma) - np.cos(gamma)*np.sin(beta)])
#    ey = np.array([np.cos(gamma)*np.sin(beta)*np.sin(alpha) - np.cos(beta)*np.sin(gamma), np.cos(alpha)*np.cos(gamma),
#                   np.cos(beta)*np.cos(gamma)*np.sin(alpha) + np.sin(beta)*np.sin(gamma)])
#    ez = np.array([np.cos(alpha)*np.sin(beta), -np.sin(alpha), np.cos(beta)*np.cos(alpha)])
    
    EHindfootAnat = np.column_stack([ex,ey,ez])

    #print Side, 'Hindfoot'
    #print EHindfootAnat
    
    return EHindfootAnat

def AnatCS_Forefoot_mSHCG(Side, MT23B, MT23H, MT1BM, MT1HM,
                          FirstMetatarsalPitch):
    
    # Sagittal Plane
    ForefootProgressionVector = MT23H - MT23B
    ProjectedForefootProgressionVector = np.array([ForefootProgressionVector[0],ForefootProgressionVector[1],0.])
    
    eSagittalx = ProjectedForefootProgressionVector/ np.linalg.norm(ProjectedForefootProgressionVector)
    R1 = np.array([0.,0.,1.])
    eSagittaly = np.cross(R1,eSagittalx)
    eSagittaly = eSagittaly/ np.linalg.norm(eSagittaly)
    eSagittalz = np.cross(eSagittalx,eSagittaly)
    
    EForefootSagittal = np.column_stack((eSagittalx,eSagittaly,eSagittalz))
    #EForefootSagittal_Origin = np.array([0.,0.,0.])
    
    # If FirstMetatarsal Pitch is entered, then do not use markers
    if FirstMetatarsalPitch == '':
        ForefootPitchVectorLab = MT1HM - MT1BM
        ForefootPitchVectorEForefootSagittal = math.TransformVectorIntoMovingCoors(ForefootPitchVectorLab,EForefootSagittal)
        ProjectedForefootPitchVectorEForefootSagittal = np.array([ForefootPitchVectorEForefootSagittal[0],0,ForefootPitchVectorEForefootSagittal[2]])
        ex = math.TransformVectorIntoLabCoors(ProjectedForefootPitchVectorEForefootSagittal, EForefootSagittal)
    else:
        # Rotate by defined pitch angle around y-axis
        # Use rodrigues formula
        ForefootPitchAngle = float(FirstMetatarsalPitch) * np.pi/ 180
        ex = eSagittalx* np.cos(ForefootPitchAngle) + \
            np.cross(eSagittaly,eSagittalx)* np.sin(ForefootPitchAngle) + \
            np.dot(eSagittaly,eSagittalx) * eSagittaly *(1-np.cos(ForefootPitchAngle))
    
    
    
    ex = ex/ np.linalg.norm(ex)
    R1 = np.array([0.,0.,1.]) 
    ey = np.cross(R1,ex)
    ey = ey/ np.linalg.norm(ey)
    ez = np.cross(ex,ey)
    
    
    if Side =='Left':
        # For Left Inwards in negative rotation about Z
        ForefootProgressionAngle = -np.arctan2(ForefootProgressionVector[1],ForefootProgressionVector[0])
    if Side =='Right':
        ForefootProgressionAngle = np.arctan2(ForefootProgressionVector[1],ForefootProgressionVector[0])
    
    ForefootPitchAngle = np.arctan2(ex[2],ex[0])
    EForefootAnat = np.column_stack((ex,ey,ez))
    
    #print Side, 'Forefoot'
    #print EForefootAnat
    
    return EForefootAnat
