"""Conversions at the QTM sample / displayed timeline boundary.

Verified in QTM: scripting sample index 354 is displayed as marker frame 355
at 2.95 seconds (120 Hz). C3D first_frame, as exposed by ezc3d, is a
zero-based sample origin. Event timestamps use the original measurement clock.
"""
import math
import logging
import os

QTM_TIMELINE_FIRST_FRAME = 1
FRAME_CONVENTION = "qtm_timeline_one_based"


def sample_index_to_frame(sample_index):
    """Convert an absolute scripting sample index to the visible QTM frame."""
    return int(round(sample_index)) + QTM_TIMELINE_FIRST_FRAME


def frame_to_sample_index(frame):
    return int(frame) - QTM_TIMELINE_FIRST_FRAME


def recording_start_frame(meta):
    """Actual displayed frame of array element zero, including a crop origin."""
    return int(meta.get("recording_start_frame", sample_index_to_frame(meta.get("initial_frame_offset", 0))))


def index_to_frame(index, start_frame=QTM_TIMELINE_FIRST_FRAME):
    return int(round(index)) + int(start_frame)


def frame_to_index(frame, start_frame=QTM_TIMELINE_FIRST_FRAME):
    return int(frame) - int(start_frame)


def frame_to_time(frame, frequency):
    frequency = float(frequency)
    if not math.isfinite(frequency) or frequency <= 0:
        raise ValueError("Capture frequency must be finite and positive")
    return frame_to_sample_index(frame) / frequency


def time_to_frame(seconds, frequency):
    frame_to_time(QTM_TIMELINE_FIRST_FRAME, frequency)
    return sample_index_to_frame(float(seconds) * float(frequency))


def trace_event(stage, label, frame, frequency, start_frame=QTM_TIMELINE_FIRST_FRAME, **details):
    """Opt-in diagnostics; one identifier follows a label and physical sample."""
    if os.environ.get("SHRINERS_FRAME_TRACE") == "1":
        event_id = f"{label}:{frame_to_sample_index(frame)}"
        logging.getLogger(__name__).warning(
            "[FRAME TRACE] Event=%s stage=%s recording_start_frame=%s sample_index=%s "
            "relative_index=%s frequency=%s QTM_frame=%s time=%s details=%s",
            event_id, stage, start_frame, frame_to_sample_index(frame),
            frame_to_index(frame, start_frame), frequency, frame, frame_to_time(frame, frequency), details)


def normalize_saved_events(events, meta):
    """Migrate identifiable prior conventions once; preserve unversioned manual frames."""
    start = recording_start_frame(meta)
    frequency = float(meta.get("frame_rate") or meta.get("frequency") or 100.0)
    convention = meta.get("frame_convention")
    result = []
    for event in events:
        ev = dict(event)
        frame = int(ev.get("frame", QTM_TIMELINE_FIRST_FRAME))
        if convention == "qtm_absolute_zero_based":
            frame = sample_index_to_frame(frame)
        elif convention != FRAME_CONVENTION and not meta.get("manual_override"):
            if "qtm_base_frame" in meta and ev.get("relative_frame") is not None:
                frame = index_to_frame(ev["relative_frame"], start)
        ev.update(frame=frame, relative_frame=frame_to_index(frame, start),
                  time=frame_to_time(frame, frequency))
        result.append(ev)
    return result
