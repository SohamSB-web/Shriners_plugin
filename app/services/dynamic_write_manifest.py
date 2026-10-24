"""Local, ordered trajectory outbox. Numerical workers never contact QTM."""
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import uuid

import numpy as np


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def identity(path):
    return hashlib.sha256(os.path.normcase(str(Path(path).resolve())).encode()).hexdigest()[:24]


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf8") as stream:
            json.dump(payload, stream, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def trial_output_lock(session, trial):
    """OS lock is released even if a worker is killed; different trials stay independent."""
    folder = Path(session) / "Processing" / "locks"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / (identity(Path(session) / Path(trial).stem) + ".lock")).open("a+b") as stream:
        stream.seek(0)
        stream.write(b"0")
        stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def input_fingerprints(session, source, calibration):
    session = Path(session).resolve()
    paths = [Path(source).resolve(), Path(calibration).resolve(), session / "session.xml"]
    # Include committed event revisions as well as legacy sidecars, without changing them.
    event_name = ("auto_event_" + Path(source).stem + "_results.json").casefold()
    paths += sorted(p for directory in (session, session / "Events") for p in directory.glob("*.json")
                    if p.is_file() and p.name.casefold() == event_name)
    return {str(p): fingerprint(p) for p in paths if p.is_file()}


class WriteManifest:
    def __init__(self, session, trial, run_id=None):
        self.session = Path(session).resolve()
        self.trial = Path(trial).stem
        self.run_id = run_id or uuid.uuid4().hex
        self.trial_id = identity(self.session / (self.trial + ".qtm"))
        self.operations = []
        self.arrays = {}
        self.initial_inputs = None

    def bind_inputs(self, calibration):
        self.initial_inputs = input_fingerprints(self.session, self.session / (self.trial + ".c3d"), calibration)

    def create(self, name):
        self.operations.append({"kind": "create", "marker": str(name)})

    def trajectory(self, name, x, y, z, exists, start, end, offset=0, target_range=None):
        xyz = np.asarray([x, y, z], dtype=float).T.copy()
        mask = np.asarray(exists, dtype=bool).copy()
        if xyz.ndim != 2 or xyz.shape[1] != 3 or mask.shape != (len(xyz),):
            raise ValueError("Trajectory XYZ/existence lengths differ")
        key = "op_" + str(len(self.operations))
        self.arrays[key + "_xyz"] = xyz
        self.arrays[key + "_exists"] = mask
        self.operations.append({"kind": "trajectory", "marker": str(name), "array": key,
                                "start": int(start), "end": int(end), "offset": int(offset),
                                "target_range": target_range, "ensure_marker": True})

    def publish(self, fields, calibration, version, gcd, timings=None):
        folder = self.session / "Processing" / "QTMWrites" / self.trial_id / self.run_id
        folder.mkdir(parents=True, exist_ok=False)
        arrays = folder / "trajectories.npz"
        with arrays.open("wb") as stream:
            np.savez_compressed(stream, **self.arrays)
        source = self.session / (self.trial + ".c3d")
        current_inputs = input_fingerprints(self.session, source, calibration)
        if self.initial_inputs is not None and self.initial_inputs != current_inputs:
            raise ValueError("Processing inputs changed during numerical calculation; reprocess this trial")
        meta = {"schema": 1, "run_id": self.run_id, "trial_id": self.trial_id,
                "patient_id": identity(self.session.parent), "session_id": identity(self.session),
                "measurement_path": str(self.session / (self.trial + ".qtm")),
                "source_c3d": str(source), "source_fingerprints": current_inputs, "input_fingerprint_version": 2,
                "calibration_path": str(Path(calibration).resolve()),
                "calibration_sha256": fingerprint(calibration), "model_version": version,
                "frames": int(fields["Frames"]), "frequency": float(fields["Capture_Frequency"]),
                "frame_start": int(fields["First Frame"]), "frame_end": int(fields["Last Frame"]),
                "frame_offset": int(fields["initial_frame_offset"]), "operations": self.operations,
                "arrays_sha256": fingerprint(arrays), "gcd_path": str(Path(gcd).resolve()),
                "gcd_sha256": fingerprint(gcd), "timings": timings or {}}
        atomic_json(folder / "manifest.json", meta)
        atomic_json(folder.parent / "latest.json", {"manifest": str(folder / "manifest.json")})
        return folder / "manifest.json"


def load_manifest(path, verify_inputs=True):
    path = Path(path).resolve()
    meta = json.loads(path.read_text(encoding="utf8"))
    if meta.get("schema") != 1 or not meta.get("operations"):
        raise ValueError("Incomplete QTM write manifest")
    source = Path(meta["source_c3d"]).resolve()
    target = source.with_suffix(".qtm")
    if (source.suffix.lower() != ".c3d" or Path(meta["measurement_path"]).resolve() != target
            or meta["trial_id"] != identity(target) or meta["session_id"] != identity(source.parent)
            or not path.is_relative_to(source.parent / "Processing" / "QTMWrites")):
        raise ValueError("Manifest patient/session/trial identity mismatch")
    latest = json.loads((path.parent.parent / "latest.json").read_text(encoding="utf8"))
    if Path(latest["manifest"]).resolve() != path:
        raise ValueError("Trial was reprocessed; select the current write manifest")
    if fingerprint(path.parent / "trajectories.npz") != meta["arrays_sha256"]:
        raise ValueError("Trajectory artifact checksum mismatch")
    if fingerprint(meta["gcd_path"]) != meta["gcd_sha256"]:
        raise ValueError("GCD changed after processing")
    if verify_inputs:
        if meta.get("input_fingerprint_version", 1) >= 2:
            current = input_fingerprints(source.parent, source, meta["calibration_path"])
            unchanged = current == meta["source_fingerprints"]
        else:
            unchanged = all(fingerprint(p) == expected for p, expected in meta["source_fingerprints"].items())
        if not unchanged:
            raise ValueError("Processing input changed; reprocess this trial before writing")
    with np.load(path.parent / "trajectories.npz", allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
    for op in meta["operations"]:
        if (op.get("kind") not in {"create", "trajectory"} or not isinstance(op.get("marker"), str)
                or not op["marker"].strip() or "\x00" in op["marker"]):
            raise ValueError("Invalid write operation")
        if op["kind"] == "trajectory":
            xyz, mask = arrays[op["array"] + "_xyz"], arrays[op["array"] + "_exists"]
            if xyz.shape != (meta["frames"], 3) or mask.shape != (len(xyz),):
                raise ValueError("Invalid trajectory shape")
            if not 0 <= op["start"] <= op["end"] <= len(xyz):
                raise ValueError("Invalid processing frame window")
            if mask.dtype != np.bool_ or not np.issubdtype(xyz.dtype, np.number) or not np.isfinite(xyz[mask]).all():
                raise ValueError("Existing trajectory samples must have finite numeric XYZ values and a boolean mask")
            offset = op["offset"]
            target = op.get("target_range") or {"start": offset, "end": offset + len(xyz) - 1}
            if (type(offset) is not int or any(type(target.get(k)) is not int for k in ("start", "end"))
                    or not offset <= target["start"] <= target["end"] < offset + len(xyz)):
                raise ValueError("Invalid trajectory source offset/target range")
    if not math.isfinite(meta["frequency"]) or meta["frequency"] <= 0:
        raise ValueError("Invalid recording frequency")
    return meta, arrays
