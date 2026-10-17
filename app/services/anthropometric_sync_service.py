"""Read/write QTM parameter synchronization and session XML persistence."""
from __future__ import annotations

import json
import datetime
import logging
import math
from decimal import Decimal, InvalidOperation
import os
from pathlib import Path
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

logger = logging.getLogger(__name__)


def get_session_xml_path(path: str | Path | None) -> Path | None:
    """Resolve the session.xml file from a file path, directory path, or session XML path."""
    if not path:
        return None
    p = Path(path).resolve()
    if p.is_file() and p.name.lower() == "session.xml":
        return p
    if p.is_dir() and (p / "session.xml").is_file():
        return p / "session.xml"
    if p.is_file() and (p.parent / "session.xml").is_file():
        return p.parent / "session.xml"
    return None


def sync_static_py_files(session_dir: str | Path, fields: dict) -> list[str]:
    """
    Synchronizes updated anthropometric measurements and patient fields
    into any Static_*.py files located in session_dir or session_dir/Calibration.
    Returns list of updated file paths.
    """
    s_dir = Path(session_dir).resolve()
    candidates = list(s_dir.glob("Static_*.py"))
    calib = s_dir / "Calibration"
    if calib.is_dir():
        candidates.extend(calib.glob("Static_*.py"))

    field_to_var = {
        "BodyMass": ("valueBodyMass", lambda v: f"{float(v):.1f}"),
        "Height": ("valueHeight", lambda v: f"'{float(v):.3f}'"),
        "InterAsisDistance": ("valueASISdist", lambda v: f"'{float(v):.3f}'"),
        "LeftLegLength": ("valueLeftLegLength", lambda v: f"'{float(v):.3f}'"),
        "RightLegLength": ("valueRightLegLength", lambda v: f"'{float(v):.3f}'"),
        "LeftKneeWidth": ("valueLeftKneeWidth", lambda v: f"'{float(v):.3f}'"),
        "RightKneeWidth": ("valueRightKneeWidth", lambda v: f"'{float(v):.3f}'"),
        "LeftAnkleWidth": ("valueLeftAnkleWidth", lambda v: f"'{float(v):.3f}'"),
        "RightAnkleWidth": ("valueRightAnkleWidth", lambda v: f"'{float(v):.3f}'"),
        "LeftAsisTrocanterDistance": ("valueLeftASIStoGTdist", lambda v: f"'{float(v):.3f}'"),
        "RightAsisTrocanterDistance": ("valueRightASIStoGTdist", lambda v: f"'{float(v):.3f}'"),
        "Name": ("valueFirstName", lambda v: f"'{str(v).strip()}'"),
        "ID": ("valuePatientNumber", lambda v: f"'{str(v).strip()}'"),
    }

    updated_files = []
    for cand in set(candidates):
        if not cand.is_file():
            continue
        try:
            lines = cand.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            var_map = {}
            for f_name, val in fields.items():
                if f_name in field_to_var and val not in (None, ""):
                    var_name, formatter = field_to_var[f_name]
                    try:
                        var_map[var_name] = formatter(val)
                    except Exception:
                        pass

            if not var_map:
                continue

            new_lines = []
            seen_vars = set()
            for line in lines:
                stripped = line.strip()
                matched = False
                for var_name, var_val in var_map.items():
                    prefix = f"self.{var_name}"
                    if stripped.startswith(prefix) and ("=" in stripped):
                        new_lines.append(f"self.{var_name} = {var_val}\n")
                        seen_vars.add(var_name)
                        matched = True
                        break
                if not matched:
                    new_lines.append(line)

            # If any variables weren't already in the file, append them
            unseen = [v for v in var_map if v not in seen_vars]
            if unseen:
                insert_idx = len(new_lines)
                for idx, line in enumerate(new_lines):
                    if "AnatRelTech" in line or "Transformation Matrices" in line:
                        insert_idx = idx
                        break
                additions = [f"self.{v} = {var_map[v]}\n" for v in unseen]
                new_lines[insert_idx:insert_idx] = additions

            cand.write_text("".join(new_lines), encoding="utf-8")
            updated_files.append(str(cand))
        except Exception as e:
            logger.warning("Failed to update static py file %s: %s", cand, e)

    return updated_files


def update_session_xml(xml_path: str | Path, fields: dict) -> bool:
    """
    Safely update fields in session.xml, preserving original encoding (UTF-16 LE / UTF-8)
    and XML structure. Updates root Session fields, child Measurement blocks,
    and any static Python config files in the session.
    """
    target = get_session_xml_path(xml_path)
    if not target or not target.is_file():
        return False
    try:
        raw = target.read_bytes()
        if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
            encoding = "utf-16"
        elif raw.startswith(b"\xef\xbb\xbf"):
            encoding = "utf-8-sig"
        elif b"utf-8" in raw[:60].lower():
            encoding = "utf-8"
        else:
            encoding = "utf-16"

        tree = ET.parse(str(target))
        root = tree.getroot()

        # If wrapped in Subject, unwrap Session to become the root element
        if root.tag == "Subject":
            session_elem = root.find(".//Session")
            if session_elem is not None:
                subj_fields = root.find("Fields")
                sess_fields = session_elem.find("Fields")
                if sess_fields is None:
                    sess_fields = ET.SubElement(session_elem, "Fields")
                if subj_fields is not None:
                    for c in subj_fields:
                        if sess_fields.find(c.tag) is None:
                            sess_fields.append(c)
                root = session_elem
                tree = ET.ElementTree(root)

        fields_elem = root.find("Fields")
        if fields_elem is None:
            fields_elem = ET.SubElement(root, "Fields")

        for key, val in fields.items():
            if val is None or val == "":
                continue
            if key in ANTHROPOMETRIC_FIELDS:
                try:
                    formatted_val = f"{float(val):.9f}"
                except (ValueError, TypeError):
                    formatted_val = str(val).strip()
            else:
                formatted_val = str(val).strip()

            elem = fields_elem.find(key)
            if elem is not None:
                elem.text = formatted_val
            else:
                new_elem = ET.SubElement(fields_elem, key)
                new_elem.text = formatted_val

        # Also reflect all changes into all Dynamic and Static measurement blocks
        for meas in root.findall(".//Measurement"):
            m_fields = meas.find("Fields")
            if m_fields is None:
                m_fields = ET.SubElement(meas, "Fields")
            for key, val in fields.items():
                if val is None or val == "":
                    continue
                if key in ANTHROPOMETRIC_FIELDS:
                    try:
                        formatted_val = f"{float(val):.9f}"
                    except (ValueError, TypeError):
                        formatted_val = str(val).strip()
                elif key in PATIENT_FIELDS:
                    formatted_val = str(val).strip()
                else:
                    continue

                m_elem = m_fields.find(key)
                if m_elem is not None:
                    m_elem.text = formatted_val
                else:
                    new_m_elem = ET.SubElement(m_fields, key)
                    new_m_elem.text = formatted_val

        ET.indent(root, space="    ")
        tree.write(str(target), encoding=encoding, xml_declaration=True)

        # Synchronize all Static_*.py files in session directory
        sync_static_py_files(target.parent, fields)
        return True
    except Exception as e:
        logger.error("Failed to update session XML %s: %s", target, e)
        return False


# Field names and units used by the existing calibration model.
ANTHROPOMETRIC_FIELDS = {
    "BodyMass": "kg", "Height": "m", "InterAsisDistance": "m",
    "LeftLegLength": "m", "RightLegLength": "m",
    "LeftKneeWidth": "m", "RightKneeWidth": "m",
    "LeftAnkleWidth": "m", "RightAnkleWidth": "m",
    "LeftAsisTrocanterDistance": "m", "RightAsisTrocanterDistance": "m",
}
PATIENT_FIELDS = {"Name", "ID", "DOB", "Sex"}



def session_identity(node):
    fields = node.get("Fields", {})
    return {"internal_guid": node.get("ID"), "class": fields.get("Class"), "path": fields.get("Path"),
            "normalized_path": os.path.normcase(str(Path(fields["Path"]).resolve())) if fields.get("Path") else None,
            "parent_guids": node.get("ParentIDs", []),
            "patient_name": fields.get("Name"), "patient_number": fields.get("ID"),
            "session_label": fields.get("Session ID"), "body_mass": fields.get("BodyMass"), "height": fields.get("Height")}


class QtmSessionResolutionError(RuntimeError):
    def __init__(self, message, **details):
        super().__init__(message)
        self.details = {"message": message, **details}


def validate_patient_field(name, value):
    text = str(value).strip()
    if name == "Name" and not text:
        raise ValueError("Name: enter the patient name")
    if any(ord(character) < 32 for character in text):
        raise ValueError(f"{name}: control characters are not allowed")
    if name == "Sex" and text not in {"Female", "Male", "Other"}:
        raise ValueError("Sex: select Female, Male or Other")
    if name == "DOB":
        try:
            date = datetime.date.fromisoformat(text)
        except ValueError:
            raise ValueError("DOB: select a valid date") from None
        if date > datetime.date.today():
            raise ValueError("DOB: date of birth cannot be in the future")
        text = date.isoformat()
    return text


def same_field_value(name, a, b):
    if name in ANTHROPOMETRIC_FIELDS:
        return same_parameter_value(a, b)
    return a is not None and b is not None and str(a).strip() == str(b).strip()


def validate_parameter(name, text, unit=None):
    unit = ANTHROPOMETRIC_FIELDS[name] if unit is None else unit
    try:
        value = float(text)
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f"{name}: enter a finite number in {unit}") from None
    if not math.isfinite(value):
        raise ValueError(f"{name}: enter a finite number in {unit}")
    if unit == "m" and not math.isfinite(value * 1000):
        raise ValueError(f"{name}: number cannot be represented in the analysis model's millimetres")
    try:
        if value == 0 and Decimal(str(text)) != 0:
            raise ValueError(f"{name}: number is too small to represent in {unit}")
    except InvalidOperation:
        raise ValueError(f"{name}: enter a finite number in {unit}") from None
    return value


def same_parameter_value(a, b):
    try:
        fa, fb = float(a), float(b)
        if fa == fb:
            return True
        return math.isclose(fa, fb, abs_tol=1e-3, rel_tol=1e-3)
    except (ValueError, TypeError, OverflowError):
        return False


def format_measurement(name: str, value: object) -> str:
    """Format measurement values to match QTM session information display exactly."""
    if value is None or str(value).strip() == "":
        return ""
    try:
        v = float(value)
        if name == "BodyMass":
            return f"{v:.1f}"
        return f"{v:.3f}"
    except (ValueError, TypeError):
        return str(value).strip()


def parameter_text(value, name: str = ""):
    if name:
        return format_measurement(name, value)
    if value is None or str(value).strip() == "":
        return ""
    try:
        v = float(value)
        return f"{v:.3f}"
    except (ValueError, TypeError):
        return str(value)


class QtmAnthropometricClient:
    def __init__(self, base_url="http://localhost:7979/api/v1/paf/instance"):
        self.base_url = base_url
        self.active_measurement = None
        self._session_guid_cache = {}

    def _project(self):
        host = self.base_url.split("/api/", 1)[0]
        with urllib.request.urlopen(host + "/api/v1/project", timeout=3.0) as response:
            project = json.load(response)
        if not project.get("OpenProject") or not project.get("ProjectDirectory"):
            raise RuntimeError("No QTM project is open")
        return project

    def active_session_dir(self):
        """The scripting API exposes the open measurement, not project-tree selection."""
        host = self.base_url.split("/api/", 1)[0]
        request = urllib.request.Request(host + "/api/scripting/qtm/file/get_path/",
                                        data=b"[]", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=3.0) as response:
                path = json.load(response)
        except urllib.error.HTTPError as error:
            no_measurement = error.code == 400 and "method requires a measurement file" in error.read().decode("utf8", errors="replace")
            if error.code in {404, 405, 501} or no_measurement:
                self.active_measurement = None
                return None  # Older API installations can still use the explicit GUI session.
            raise
        self.active_measurement = path
        return str(Path(path).parent.resolve()) if path else None

    def _request(self, instance_id="", *, query="", timeout=3.0):
        url = self.base_url
        if instance_id:
            url += "/" + urllib.parse.quote(instance_id, safe="")
        request = urllib.request.Request(url + query, headers={"Content-Type": "application/json"}, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)

    @staticmethod
    def _matches(node, session_dir):
        fields = node.get("Fields", {})
        path = fields.get("Path")
        return (fields.get("Class") == "Session" and bool(path)
                and os.path.normcase(str(Path(path).resolve())) == session_dir)

    def find_session_guid(self, session_dir):
        context = os.path.normcase(str(Path(session_dir).resolve()))
        if context in self._session_guid_cache:
            guid = self._session_guid_cache[context]
            try:
                node = self._request(guid)
                if self._matches(node, context):
                    return guid
            except Exception:
                pass
            self._session_guid_cache.pop(context, None)

        project = self._project()
        deadline = time.monotonic() + 5.0
        visited, sessions = [], []

        def discover(current, ancestors=()):
            fields = current.get("Fields", {})
            if fields.get("Class") == "Session":
                sessions.append((current, ancestors))
                return
            if fields.get("Class") in {"Measurements", "Measurement"}:
                return
            if "Children" not in current and current.get("ChildIDs"):
                expanded = self._request(current["ID"], query="?depth=2")
                current = expanded
            for child in current.get("Children", []):
                if len(visited) >= 256 or time.monotonic() > deadline:
                    raise RuntimeError("QTM session discovery timed out")
                visited.append(child.get("ID"))
                discover(child, ancestors + (current,))

        discover(self._request(query="?depth=3"))
        matches = [node for node, ancestors in sessions if self._matches(node, context)]
        if matches:
            guid = matches[0]["ID"]
            self._session_guid_cache[context] = guid
            return guid
        return None

    def write(self, session_dir, fields: dict):
        guid = self.find_session_guid(session_dir)
        if not guid:
            raise QtmSessionResolutionError("No matching QTM session found to write parameters.")

        payload = {}
        for name in ANTHROPOMETRIC_FIELDS:
            if name in fields and fields[name] not in (None, ""):
                try:
                    payload[name] = float(fields[name])
                except (ValueError, TypeError):
                    pass
        for name in PATIENT_FIELDS:
            if name in fields and fields[name] not in (None, ""):
                payload[name] = str(fields[name]).strip()

        if not payload:
            return False

        url = self.base_url + "/" + urllib.parse.quote(guid, safe="")
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="PUT")
        success = False
        with urllib.request.urlopen(request, timeout=3.0) as response:
            success = response.status in (200, 204)

        # Also write parameters to all measurement children under this session
        try:
            expanded = self._request(guid, query="?depth=2")
            for child in expanded.get("Children", []):
                child_fields = child.get("Fields", {})
                if child_fields.get("Class") in {"Measurements", "Measurement"}:
                    child_id = child.get("ID")
                    if child_id:
                        c_url = self.base_url + "/" + urllib.parse.quote(child_id, safe="")
                        c_req = urllib.request.Request(c_url, data=data, headers={"Content-Type": "application/json"}, method="PUT")
                        try:
                            with urllib.request.urlopen(c_req, timeout=2.0):
                                pass
                        except Exception:
                            pass
        except Exception:
            pass

        return success

    def read(self, session_dir):
        context = os.path.normcase(str(Path(session_dir).resolve()))
        project = self._project()
        deadline = time.monotonic() + 4.0
        visited, sessions = [], []

        def discover(current, ancestors=()):
            fields = current.get("Fields", {})
            if fields.get("Class") == "Session":
                sessions.append((current, ancestors))
                return
            if fields.get("Class") in {"Measurements", "Measurement"}:
                return
            if "Children" not in current and current.get("ChildIDs"):
                expanded = self._request(current["ID"], query="?depth=2")
                if (expanded.get("ID") != current.get("ID") or
                        expanded.get("Fields", {}).get("Class") != fields.get("Class") or not fields.get("Path") or
                        os.path.normcase(str(Path(expanded.get("Fields", {}).get("Path", "")).resolve()))
                        != os.path.normcase(str(Path(fields["Path"]).resolve()))):
                    raise QtmSessionResolutionError("QTM cannot uniquely expand this parent branch",
                        error_type="ambiguous_read_source", project=project, gui_session_path=context,
                        conflicting_sessions=[session_identity(current), session_identity(expanded)],
                        recommended_resolution="Select the intended QTM session and review its source.")
                current = expanded
            for child in current.get("Children", []):
                if len(visited) >= 256 or time.monotonic() > deadline:
                    raise RuntimeError("QTM session discovery timed out")
                visited.append(child.get("ID"))
                discover(child, ancestors + (current,))

        discover(self._request(query="?depth=3"))
        matches = [(node, ancestors) for node, ancestors in sessions if self._matches(node, context)]
        if len(matches) != 1:
            raise QtmSessionResolutionError("Multiple QTM sessions match the selected folder" if matches else
                                            "No QTM PAF session matches the selected session folder",
                error_type="ambiguous_read_source" if matches else "session_not_found", project=project,
                gui_session_path=context, conflicting_sessions=[session_identity(n) for n, _ in matches],
                recommended_resolution="Open the intended measurement in QTM or select its full session folder.")
        node, ancestors = matches[0]
        self._session_guid_cache[context] = node["ID"]
        parents = [p for p in reversed(ancestors) if p.get("Fields", {}).get("Class") == "Subject"]
        subject = parents[0] if parents else None
        # Older tree responses can expose Subject only through a uniquely proven direct record.
        if subject is None and sum(n["ID"] == node["ID"] for n, _ in sessions) == 1:
            try:
                addressed = self._request(node["ID"], query="?depth=-1")
            except (urllib.error.URLError, TimeoutError):
                addressed = {}
            if addressed.get("ID") == node["ID"] and self._matches(addressed, context):
                parents = [p for p in addressed.get("Parent", []) if p.get("Fields", {}).get("Class") == "Subject"]
                if len(parents) > 1:
                    raise QtmSessionResolutionError("Multiple QTM Subject sources remain possible",
                        error_type="ambiguous_read_source", conflicting_sessions=[session_identity(p) for p in parents])
                if parents:
                    candidate = parents[0]
                    inherited = (ANTHROPOMETRIC_FIELDS.keys() | PATIENT_FIELDS) - node.get("Fields", {}).keys()
                    if inherited & candidate.get("Fields", {}).keys():
                        actual = self._request(candidate["ID"], query="?depth=-1")
                        source_path = candidate.get("Fields", {}).get("Path")
                        target_path = actual.get("Fields", {}).get("Path")
                        if not (source_path and target_path and actual.get("ID") == candidate["ID"]
                                and actual.get("Fields", {}).get("Class") == "Subject"
                                and os.path.normcase(str(Path(source_path).resolve()))
                                == os.path.normcase(str(Path(target_path).resolve()))):
                            raise QtmSessionResolutionError("QTM cannot uniquely resolve the Subject source",
                                error_type="ambiguous_read_source", conflicting_sessions=[session_identity(candidate), session_identity(actual)])
                    subject = candidate
        fields = {}
        for owner in ([subject] if subject else []) + [node]:
            for name, value in owner.get("Fields", {}).items():
                if name in ANTHROPOMETRIC_FIELDS or name in PATIENT_FIELDS:
                    fields[name] = value
        for name in ANTHROPOMETRIC_FIELDS.keys() & fields.keys():
            validate_parameter(name, fields[name])
        errors = {}
        for name in PATIENT_FIELDS & fields.keys():
            if fields[name] in {None, ""}:
                continue
            try:
                validate_patient_field(name, fields[name])
            except ValueError as error:
                errors[name] = f"Invalid QTM metadata: {error}"
        if self._project() != project:
            raise RuntimeError("QTM project changed while reading; Fetch and review again")
        return {"context": context, "fields": fields, "errors": errors,
                "resolution": {"project": project, "gui_session_path": context,
                               "session": session_identity(node), "subject": session_identity(subject) if subject else None}}




class _SyncOperation(QRunnable):
    def __init__(self, service, context, generation):
        super().__init__()
        self.service, self.context, self.generation = service, context, generation
        self.cancelled = threading.Event()

    def run(self):
        result = {"generation": self.generation, "snapshot": None, "error": "", "diagnostics": {},
                  "requested_context": os.path.normcase(str(Path(self.context).resolve()))}
        try:
            active = self.service.client.active_session_dir()
            result["measurement"] = self.service.client.active_measurement
            if not active and not self.context:
                raise RuntimeError("Open a QTM measurement or select a session folder before fetching")
            snapshot = self.service.client.read(active or self.context)
            current = self.service.client.active_session_dir()
            if current and os.path.normcase(str(Path(current).resolve())) != snapshot["context"]:
                raise RuntimeError("QTM session changed during Fetch; review again")
            if self.cancelled.is_set():
                raise RuntimeError("Fetch cancelled")
            result["snapshot"] = snapshot
        except Exception as error:
            result["error"] = str(error)
            result["diagnostics"] = getattr(error, "details", {
                "error_type": "connection_failure" if isinstance(error, OSError)
                              else "invalid_data" if isinstance(error, ValueError) else "operation_failed",
                "message": str(error), "recommended_resolution": "Check QTM and its open project, then Fetch QTM again."})
        try:
            self.service.finished.emit(result)
        except RuntimeError:
            pass  # The page was destroyed while a bounded HTTP request completed.


class AnthropometricSyncService(QObject):
    finished = Signal(object)
    write_finished = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.client = QtmAnthropometricClient()
        self.operation = None

    def request(self, context, generation):
        if self.operation is not None:
            return False
        self.operation = _SyncOperation(self, context, generation)
        QThreadPool.globalInstance().start(self.operation)
        return True

    def cancel(self):
        if self.operation is not None and hasattr(self.operation, "cancelled"):
            self.operation.cancelled.set()

    def write_async(self, context, fields, generation=0):
        op = _WriteOperation(self, context, fields, generation)
        self.operation = op
        QThreadPool.globalInstance().start(op)
        return True


class _WriteOperation(QRunnable):
    def __init__(self, service, session_dir, fields, generation):
        super().__init__()
        self.service, self.session_dir, self.fields, self.generation = service, session_dir, fields, generation
        self.cancelled = threading.Event()

    def run(self):
        try:
            success = self.service.client.write(self.session_dir, self.fields)
            self.service.write_finished.emit({
                "success": success,
                "error": None,
                "generation": self.generation,
                "fields": self.fields
            })
        except Exception as error:
            try:
                self.service.write_finished.emit({
                    "success": False,
                    "error": str(error),
                    "generation": self.generation,
                    "fields": self.fields
                })
            except (RuntimeError, AttributeError):
                pass
        finally:
            try:
                if getattr(self.service, "operation", None) is self:
                    self.service.operation = None
            except (RuntimeError, AttributeError):
                pass
