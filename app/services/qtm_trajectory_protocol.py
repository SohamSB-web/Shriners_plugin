"""Exact-measurement trajectory commands using the bridge's existing QTM APIs."""
import math
from pathlib import Path

from app.services.event_store import paths_match
from app.services.qtm_event_protocol import active_path


def guarded_trajectory_command(qtm, timeline, create_marker, set_trajectory, command, args):
    target = args.get("measurement_path")
    if command == "SelectTrajectoryTrial":
        if not args.get("overwrite_confirmed"):
            raise ValueError("Explicit clinician confirmation is required")
        if not target or not Path(target).is_absolute() or Path(target).suffix.lower() != ".qtm" or not Path(target).is_file():
            raise ValueError("The exact destination .qtm file is unavailable")
        if not qtm.file.is_open() or not paths_match(qtm.file.get_path(), target):
            if qtm.file.is_open() and qtm.file.is_dirty():
                raise ValueError("Save or discard the current QTM measurement's edits before starting Write Operation")
            qtm.file.open(target)
    path = active_path(qtm)
    if not target or not paths_match(path, target):
        raise ValueError("Incorrect QTM measurement: open the exact saved target .qtm file")
    measured = dict(timeline.get_measured_range())
    frequency = float(timeline.get_frequency())
    if command == "SelectTrajectoryTrial":
        existing = [name for name in args["markers"]
                    if qtm.data.object.trajectory.find_trajectory(name) is not None]
        if not paths_match(active_path(qtm), target):
            raise ValueError("QTM measurement changed during validation")
        return {"measurement_path": path, "existing": existing, "measured_range": measured,
                "frequency": frequency, "protocol": 2}
    if command == "CompleteTrajectoryTrial":
        if not args.get("overwrite_confirmed") or frequency != args["frequency"] or measured != args["measured_range"]:
            raise ValueError("QTM measurement changed before saving the completed trial")
        qtm.file.save()
        if not paths_match(active_path(qtm), target) or qtm.file.is_dirty():
            raise RuntimeError("QTM could not confirm saving this trial")
        return {"measurement_path": path, "saved": True}
    if command not in {"ApplyTrajectoryOperation", "VerifyTrajectoryOperation"} or not args.get("overwrite_confirmed"):
        raise ValueError("Explicit clinician confirmation is required")
    if frequency != float(args["frequency"]) or measured != args["measured_range"]:
        raise ValueError("QTM recording frequency/range changed after validation")
    operation = args["operation"]
    name = operation["marker"]
    if operation["kind"] not in {"create", "trajectory"} or not isinstance(name, str) or not name.strip() or "\x00" in name:
        raise ValueError("Unsupported marker operation")
    if operation["kind"] == "trajectory":
        payload = args["trajectory"]
        count = len(payload["X"])
        if not count or any(len(payload[key]) != count for key in ("Y", "Z", "exists")):
            raise ValueError("Trajectory XYZ/existence lengths differ")
        start = operation["offset"]
        target_range = operation.get("target_range") or {"start": start, "end": start + count - 1}
        if (type(start) is not int or not all(type(target_range.get(k)) is int for k in ("start", "end"))
                or not measured["start"] <= target_range["start"] <= target_range["end"] <= measured["end"]
                or target_range["start"] < start or target_range["end"] >= start + count):
            raise ValueError("Invalid trajectory recording range")
        if any(type(v) is not bool for v in payload["exists"]):
            raise ValueError("Invalid trajectory existence mask")
        if any(v is not None and (type(v) not in (int, float) or not math.isfinite(v))
               for key in "XYZ" for v in payload[key]):
            raise ValueError("Invalid XYZ sample")
        if any(exists and any(payload[axis][i] is None for axis in "XYZ")
               for i, exists in enumerate(payload["exists"])):
            raise ValueError("Existing trajectory samples must have finite XYZ values")
    if not paths_match(active_path(qtm), target):
        raise ValueError("QTM measurement changed before marker creation")
    if command == "VerifyTrajectoryOperation":
        marker_id = qtm.data.object.trajectory.find_trajectory(name)
        if marker_id is None:
            return {"measurement_path": path, "verified": False, "operation_id": args["operation_id"]}
    else:
        marker_id = create_marker(name)
    if operation["kind"] == "trajectory":
        payload = args["trajectory"]
        xyz = list(zip(payload["X"], payload["Y"], payload["Z"]))
        mask = payload["exists"]
        start = int(operation["offset"])
        target_range = operation.get("target_range") or {"start": start, "end": start + len(xyz) - 1}
        if not paths_match(active_path(qtm), target):
            raise ValueError("QTM measurement changed before trajectory write")
        if command == "ApplyTrajectoryOperation":
            set_trajectory(name, payload["X"], payload["Y"], payload["Z"], mask, start, target_range)
        for frame in range(target_range["start"], target_range["end"] + 1):
            i = frame - start
            expected = xyz[i]
            actual = qtm.data.series._3d.get_sample(marker_id, frame)
            valid = mask[i] and all(v is not None and math.isfinite(v) for v in expected)
            if valid:
                if not actual or len(actual["position"]) != 3 or not all(math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=1e-4)
                                         for a, b in zip(actual["position"], expected)):
                    if command == "VerifyTrajectoryOperation":
                        return {"measurement_path": path, "verified": False, "operation_id": args["operation_id"]}
                    raise RuntimeError("QTM trajectory read-back failed for " + name)
            elif actual is not None:
                if command == "VerifyTrajectoryOperation":
                    return {"measurement_path": path, "verified": False, "operation_id": args["operation_id"]}
                raise RuntimeError("QTM trajectory existence read-back failed for " + name)
    if not paths_match(active_path(qtm), target):
        raise RuntimeError("QTM measurement changed during write; result is uncertain")
    if qtm.data.object.trajectory.find_trajectory(name) is None:
        raise RuntimeError("QTM marker creation could not be verified")
    return {"measurement_path": path, "verified": True, "operation_id": args["operation_id"]}
