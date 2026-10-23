#!/usr/bin/env python
"""Regression test for auto event labeling on trials with no manual events.

The plugin used to crash with ``KeyError: 'EVENT'`` whenever it was pointed at
a trial that had not been labeled by hand, because QTM/ezc3d only write the
"EVENT" parameter group into a .c3d once the trial holds at least one event.
That defeated the point of *auto* labeling.  This script builds throwaway .c3d
trials covering the cases and checks the whole pipeline runs on each:

    (a) zero events        - no EVENT group at all
    (b) one manual event   - EVENT group with a single entry
    (c) several events     - EVENT group with four entries
    (d) emptied group      - EVENT group present but USED = 0

Run it directly:  python test_auto_event_zero_events.py

It needs no QTM session: the two gRPC calls the pipeline makes (GetForcePlate
and SetEvent) are stubbed out, so the trials are treated as having no force
plates and written events are collected in memory instead of sent to QTM.
"""

import os
import shutil
import sys
import tempfile

import numpy as np
from ezc3d import c3d

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The pipeline prints status lines containing non-ASCII characters ('PASS -check-'
# in auto_event_trigger, arrows and dashes in Py3_GaitModules).  On a console
# using a legacy code page (cp1252 on most Windows installs) those prints raise
# UnicodeEncodeError, which is a separate pre-existing issue and would mask the
# behaviour under test here, so force UTF-8 on stdout for the duration.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

RATE = 100.0
N_FRAMES = 700
STRIDE_S = 1.10
MARKERS = ["Sacrum", "Left_Heel", "Right_Heel", "Left_Toe", "Right_Toe"]
META = {"__METADATA__": {"DESCRIPTION": "", "IS_LOCKED": False}}


def _synth_points():
    """Sacrum travelling in +X with the feet oscillating about it, so the Zeni
    detector has real heel strikes / toe offs to find."""
    t = np.arange(N_FRAMES) / RATE
    w = 2 * np.pi / STRIDE_S
    sac_x = 1200.0 * t
    pts = np.ones((4, len(MARKERS), N_FRAMES))

    def put(i, x, y, z):
        pts[0, i, :], pts[1, i, :], pts[2, i, :] = x, y, z

    put(0, sac_x, np.zeros(N_FRAMES), np.full(N_FRAMES, 950.0))
    put(1, sac_x + 350 * np.sin(w * t), np.full(N_FRAMES, 90.0),
        60 + 55 * (1 - np.cos(w * t)))
    put(2, sac_x + 350 * np.sin(w * t + np.pi), np.full(N_FRAMES, -90.0),
        60 + 55 * (1 - np.cos(w * t + np.pi)))
    ph = 2 * np.pi * 0.45
    put(3, sac_x + 300 * np.sin(w * t - ph), np.full(N_FRAMES, 100.0),
        30 + 45 * (1 - np.cos(w * t - ph)))
    put(4, sac_x + 300 * np.sin(w * t + np.pi - ph), np.full(N_FRAMES, -100.0),
        30 + 45 * (1 - np.cos(w * t + np.pi - ph)))
    return pts


def _base_trial():
    r = c3d()
    r["parameters"]["POINT"]["RATE"]["value"] = [RATE]
    r["parameters"]["POINT"]["LABELS"]["value"] = list(MARKERS)
    r["parameters"]["POINT"]["UNITS"]["value"] = ["mm"]
    r["data"]["points"] = _synth_points()
    return r


def _add_processing(r):
    proc = dict(META)
    proc["Metrics"] = {"type": -1, "description": "", "is_locked": False,
                       "value": ["mm"]}
    proc["BodyMass"] = {"type": 4, "description": "", "is_locked": False,
                        "value": np.array([32.5], dtype=np.float32)}
    r["parameters"]["PROCESSING"] = proc
    return r


def _add_events(r, labels, contexts, times_s):
    n = len(labels)
    ev = dict(META)
    ev["USED"] = {"type": 2, "description": "", "is_locked": False,
                  "value": np.array([n], dtype=np.int32)}
    ev["LABELS"] = {"type": -1, "description": "", "is_locked": False,
                    "value": list(labels)}
    ev["CONTEXTS"] = {"type": -1, "description": "", "is_locked": False,
                      "value": list(contexts)}
    times = np.zeros((2, n), dtype=np.float32)
    if n:
        times[1, :] = times_s
    ev["TIMES"] = {"type": 4, "description": "", "is_locked": False,
                   "value": times}
    r["parameters"]["EVENT"] = ev
    return r


def build_session(session_dir):
    """Write the trials plus a session.xml that points at them."""
    trials = {
        # (a) never labeled: no EVENT group, and no PROCESSING group either
        "ZeroEvents": _base_trial(),
        # (b) exactly one manually labeled event
        "OneEvent": _add_events(_add_processing(_base_trial()),
                                ["Foot Strike"], ["Left"], [2.20]),
        # (c) several manually labeled events
        "ManyEvents": _add_events(
            _add_processing(_base_trial()),
            ["Foot Strike", "Foot Off", "Foot Strike", "Foot Off"],
            ["Left", "Left", "Right", "Right"],
            [2.20, 2.72, 2.75, 3.27]),
        # (d) labeled and then all events deleted again: group kept, USED = 0
        "EmptyEventGroup": _add_events(_add_processing(_base_trial()),
                                       [], [], []),
    }
    for name, r in trials.items():
        r.write(os.path.join(session_dir, name + ".c3d"))

    rows = "\n".join(
        '  <Measurement Filename="{0}.qtm" Type="Dynamic"/>'.format(n)
        for n in trials)
    with open(os.path.join(session_dir, "session.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<Session>\n'
                + rows + "\n</Session>\n")
    return list(trials)


def _stub_qtm():
    """Replace the two gRPC round trips so no live QTM session is needed."""
    import Py3_Utils
    import gapi

    written = []
    Py3_Utils.GetForcePlate = lambda: {}
    gapi.GetForcePlate = lambda: {}

    def set_event(label, frame_no, frequency, offset=0, trial_name=None):
        written.append((frame_no, label))
        return "OK"

    gapi.SetEvent = set_event
    return written, set_event


def main():
    session_dir = tempfile.mkdtemp(prefix="auto_event_test_")
    failures = []
    try:
        build_session(session_dir)
        written, set_event = _stub_qtm()

        from Py3_varExtractor import extract_fields_by_filename
        import auto_event_trigger as aet
        aet.SetEvent = set_event
        import gapi
        gapi.grpc_send_command = lambda *args, **kwargs: "OK"

        session_xml = os.path.join(session_dir, "session.xml")

        # --- extraction: every trial must yield an EVENTS dict and a range ---
        expected_events = {"ZeroEvents": 0, "EmptyEventGroup": 0,
                           "OneEvent": 1, "ManyEvents": 4}
        for name in ["ZeroEvents", "EmptyEventGroup", "OneEvent", "ManyEvents"]:
            n_expected = expected_events[name]
            try:
                fields = extract_fields_by_filename(session_xml,
                                                    name + ".qtm", False)
            except Exception as e:
                failures.append("{0}: extract raised {1}: {2}".format(
                    name, type(e).__name__, e))
                continue
            if fields is None:
                failures.append("{0}: extract returned None".format(name))
                continue
            if "EVENTS" not in fields:
                failures.append("{0}: fields has no EVENTS key".format(name))
                continue
            n_got = sum(len(v["FrameNo"]) for v in fields["EVENTS"].values())
            if n_got != n_expected:
                failures.append("{0}: expected {1} manual events, got {2}".format(
                    name, n_expected, n_got))
            if fields.get("First Frame") is None or fields.get("Last Frame") is None:
                failures.append("{0}: First/Last Frame not set".format(name))
            print("  extract  {0:<16} events={1} range=({2}, {3})".format(
                name, n_got, fields.get("First Frame"), fields.get("Last Frame")))

        # --- full pipeline: all three cases must detect and write events ------
        for name in ["ZeroEvents", "OneEvent", "ManyEvents"]:
            del written[:]
            aet.get_qtm_active_measurement = lambda: name + ".qtm"
            try:
                aet.process_trial(os.path.join(session_dir, name + ".qtm"))
            except Exception as e:
                failures.append("{0}: process_trial raised {1}: {2}".format(
                    name, type(e).__name__, e))
                continue
            if not written:
                failures.append("{0}: pipeline wrote no events".format(name))
            print("  pipeline {0:<16} wrote {1} events".format(name, len(written)))
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)

    print("")
    if failures:
        for f in failures:
            print("FAIL: " + f)
        return 1
    print("ALL PASS - auto event labeling runs on trials with 0, 1 and N events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
