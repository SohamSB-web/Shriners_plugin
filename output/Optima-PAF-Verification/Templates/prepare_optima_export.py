"""Prepare QTM export copies for the Shriners lab's AMTI Optima."""

import json
import msvcrt
import os
from pathlib import Path
import shutil
import struct
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import pythoncom


GENERIC = "Force-plate 1"
OPTIMA = "Amti Optima OR6-7-OP-1K-STT 10409M"

# The field IDs are from the Measurement NBC schema verified for this lab.
PLACEHOLDER = {
    49: bytes(8),  # width
    50: bytes(8),  # length
    51: struct.pack("<I", 4) + bytes(96),  # unset corners
    59: bytes(4),  # plate type
    60: bytes(4),  # plate model
    61: bytes(4),  # board number
    62: bytes(4),  # board index
    63: struct.pack("<7I", 6, 0, 1, 2, 3, 4, 5),  # default channels
    65: struct.pack("<I", 36) + bytes(288),  # unset calibration matrix
}


def _label(field, name):
    value = struct.pack("<I", len(name)) + name.encode("utf-16-le") + b"\x00\x00"
    return struct.pack("<II", field, len(value)) + value


def _plate(data, name):
    label = _label(29, name)
    count = data.count(label)
    if not count:
        return None
    start = data.index(label)
    if count != 1 or start < 28:
        raise ValueError(f"Ambiguous QTM settings for {name}")
    class_id, _, num_fields, height, width, _, _ = struct.unpack_from("<7I", data, start - 28)
    if (height, width) != (8, 8) or not 2 <= num_fields <= 32:
        raise ValueError(f"Unsupported QTM settings for {name}")
    fields = {}
    cursor = start
    for _ in range(num_fields - 1):
        field, size = struct.unpack_from("<II", data, cursor)
        cursor += 8
        if field in fields or cursor + size > len(data):
            raise ValueError(f"Invalid QTM settings for {name}")
        fields[field] = (cursor, data[cursor:cursor + size])
        cursor += size
    if data[cursor:cursor + 12] != bytes(12) or fields.get(30, (0, b""))[1] not in (b"\0", b"\1"):
        raise ValueError(f"Invalid QTM settings for {name}")
    return class_id, fields


def _class_names(metadata):
    classes = {}
    cursor = 8
    for identifier in range(1, struct.unpack_from("<I", metadata)[0] + 1):
        size = struct.unpack_from("<I", metadata, cursor)[0]
        cursor += 4
        title = metadata[cursor:cursor + size]
        if not title.endswith(b"\0"):
            raise ValueError("Invalid QTM settings class")
        classes[identifier] = title[:-1]
        cursor += size
        cursor += 8 + struct.unpack_from("<I", metadata, cursor)[0]
    return classes


def _force_flag_offset(metadata, data):
    generic = _plate(data, GENERIC)
    if generic is None:
        return None
    class_id, fields = generic
    offset, enabled = fields[30]
    if enabled == b"\0" or any(fields.get(field, (0, None))[1] != value for field, value in PLACEHOLDER.items()):
        return None
    classes = _class_names(metadata)
    if classes.get(class_id) != b"ForcePlateSettingsAnalog":
        raise ValueError(f"Unknown configuration for {GENERIC}")
    optima = _plate(data, OPTIMA)
    if (
        optima is None
        or classes.get(optima[0]) != b"ForcePlateSettingsAmtiGen5"
        or optima[1][30][1] != b"\1"
        or optima[1].get(56, (0, b""))[1] != b"\1"
        or data.count(_label(6, OPTIMA)) != 1
    ):
        raise ValueError("The generic placeholder is enabled without an enabled, recorded Shriners AMTI Optima")
    return offset


def _fix_export_recording(path):
    # Only called on a staged copy. The original recordings are opened for copying only.
    root = pythoncom.StgOpenStorage(str(path), None, 0x12)
    measurement = root.OpenStorage("Measurement NBC", None, 0x12)
    metadata = measurement.OpenStream("Metadata", None, 0x12)
    settings = measurement.OpenStream("Data Items", None, 0x12)
    before = settings.Read(settings.Stat(1)[2])
    offset = _force_flag_offset(metadata.Read(metadata.Stat(1)[2]), before)
    if offset is None:
        return False
    settings.Seek(offset, 0)
    settings.Write(b"\0")
    settings.Commit(0)
    measurement.Commit(0)
    root.Commit(0)
    settings.Seek(0, 0)
    if settings.Read(len(before)) != before[:offset] + b"\0" + before[offset + 1:]:
        raise OSError("QTM force settings verification failed")
    return True


def prepare_export_copies(session_xml, output_root):
    session_xml = session_xml.resolve(strict=True)
    folder = session_xml.parent
    session = next(ET.parse(session_xml).iter("Session"), None)
    if session is None:
        raise ValueError("No QTM Session found in session.xml")
    recordings = {}
    for item in session.findall("Measurement"):
        if item.findtext("Fields/Used", "true").strip().lower() in {"false", "0", "no"}:
            continue
        name = item.get("Filename", "")
        source = (folder / name).resolve()
        if Path(name).name != name or source.parent != folder or source.suffix.lower() != ".qtm":
            raise ValueError(f"Invalid local QTM measurement: {name!r}")
        if not source.is_file():
            raise FileNotFoundError(f"Measurement is missing: {name}")
        recordings[name] = source
    if not recordings:
        raise ValueError("No checked QTM recordings in this session")

    output_root.mkdir(parents=True, exist_ok=True)
    target = output_root / f"{folder.name}_{uuid4().hex[:8]}"
    with TemporaryDirectory(prefix=".qtm-", dir=output_root) as tmp:
        staged = Path(tmp) / "recordings"
        staged.mkdir()
        for name, source in recordings.items():
            copy = staged / name
            shutil.copy2(source, copy)
            try:
                changed = _fix_export_recording(copy)
            except (ValueError, OSError, struct.error, pythoncom.com_error) as error:
                raise ValueError(f"{name}: {error}") from error
            print(f"{name}: {'disabled the generic placeholder' if changed else 'kept recorded settings'}")
        staged.rename(target)
    return target


def _qtm_json(path, *args):
    url = f"http://127.0.0.1:7979/api/{path}"
    request = Request(url)
    if path.startswith("scripting/"):
        request = Request(url, data=json.dumps(args).encode(), headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=60) as response:
            payload = response.read()
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        if "main application window to be enabled" in detail:
            raise RuntimeError("Dismiss the open dialog in QTM, then run Start Processing again.") from error
        raise RuntimeError(f"QTM could not complete the requested operation: {detail}") from error
    except URLError as error:
        raise RuntimeError("The QTM scripting service is unavailable. Check that QTM is open and REST is enabled.") from error
    return json.loads(payload) if payload else None


def _file(method, *args):
    return _qtm_json(f"scripting/qtm/file/{method}/", *args)


def export_c3ds(folder, project):
    active = _qtm_json("v1/project").get("ProjectDirectory")
    if not active or Path(active).resolve() != project:
        raise ValueError("Open this Shriners project in QTM before starting export.")

    previous = None
    if _file("is_open"):
        if _file("is_dirty"):
            raise ValueError("Save or close the open QTM recording before starting this export.")
        previous = Path(_file("get_path") or "")
        if not previous.is_file():
            raise ValueError("Close QTM preview before starting this export.")
        _file("close")

    try:
        # Publish C3Ds to the analysis folder after the whole selection has exported.
        with TemporaryDirectory(prefix=".c3d-", dir=folder) as directory:
            staged = Path(directory)
            for recording in sorted(folder.glob("*.qtm")):
                if _file("is_open"):
                    raise RuntimeError("Another measurement was opened in QTM during export.")
                _file("open", str(recording))
                try:
                    if Path(_file("get_path") or "").resolve() != recording:
                        raise RuntimeError(f"QTM did not open the intended copy of {recording.name}")
                    c3d = staged / recording.with_suffix(".c3d").name
                    _file("export_c3d", str(c3d))
                    if not c3d.is_file() or c3d.stat().st_size < 512:
                        raise ValueError(f"QTM did not write a complete export for {recording.name}")
                    with c3d.open("rb") as stream:
                        prefix = stream.read(2)
                    if len(prefix) != 2 or prefix[0] < 2 or prefix[1] != 0x50:
                        raise ValueError(f"Invalid C3D header for {recording.name}")
                    print(f"Exported {c3d.name}", flush=True)
                finally:
                    if _file("is_open") and Path(_file("get_path") or "").resolve() == recording and not _file("is_dirty"):
                        _file("close")
            for c3d in staged.glob("*.c3d"):
                c3d.rename(folder / c3d.name)
    finally:
        if previous and not _file("is_open"):
            _file("open", str(previous))


def _copy_analysis_inputs(session_xml, destination):
    shutil.copy2(session_xml, destination / "session.xml")
    source = session_xml.parent
    for subfolder in (Path("."), Path("Calibration")):
        for pattern in ("Static_*.py", "SittingFootStatic_*.py"):
            for original in (source / subfolder).glob(pattern):
                target = destination / subfolder / original.name
                target.parent.mkdir(exist_ok=True)
                shutil.copy2(original, target)


def main(session_xml):
    project = Path(__file__).resolve().parents[1]
    destination = Path(os.environ["LOCALAPPDATA"]) / "Shriners" / "QTM Export Copies"
    destination.mkdir(parents=True, exist_ok=True)
    # QTM's active measurement is shared by all export requests.
    with (destination / ".export.lock").open("a+b") as lock:
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RuntimeError("A Shriners QTM export is already running.") from error
        with TemporaryDirectory(prefix=".export-", dir=destination) as directory:
            folder = prepare_export_copies(session_xml, Path(directory))
            _copy_analysis_inputs(session_xml, folder)
            export_c3ds(folder, project)
            final_folder = destination / folder.name
            folder.rename(final_folder)
    print(f"QTM exports and analysis inputs: {final_folder}")
    os.startfile(final_folder)


if __name__ == "__main__":
    try:
        main(Path(sys.argv[1]).resolve(strict=True))
    except (OSError, RuntimeError, ValueError, ET.ParseError) as error:
        sys.exit(str(error))
