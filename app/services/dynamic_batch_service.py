"""Application-owned bounded dynamic-file scheduling with independent Python processes."""
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import time
import uuid
import xml.etree.ElementTree as ET

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QSettings, QStandardPaths, Signal

from app.services.dynamic_write_manifest import atomic_json, identity, load_manifest
from app.services.processing_service import _GAIT_DIR, _resolve_python_launcher


def parallel_file_limit():
    available = os.cpu_count() or 1
    try:
        configured = max(1, int(os.environ.get("SHRINERS_MAX_PARALLEL_DYNAMIC_FILES", str(available))))
    except ValueError:
        configured = available
    return min(available, configured)


@dataclass
class DynamicJob:
    patient_id: str
    session_xml: str
    filename: str
    condition: str = "BF"
    left_plate: str = "0"
    right_plate: str = "0"
    interactive_fp: bool = False
    state: str = "QUEUED"
    manifest: str = ""
    error: str = ""
    duration_s: float = 0.0
    gcd_duration_s: float = 0.0
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @property
    def key(self):
        return identity(Path(self.session_xml).parent / (Path(self.filename).stem + ".qtm"))


class DynamicBatchService(QObject):
    changed = Signal()
    trial_changed = Signal(object)
    finished = Signal()
    log = Signal(str)

    def __init__(self, conda_env="python-example", parent=None, history_path=None):
        super().__init__(parent)
        self.conda_env = conda_env
        self.jobs = []
        self._active = {}
        self._cancelled = False
        self._running = False
        self.limit = 1
        self.preferences = QSettings("Shriners", "GaitAnalysis")
        root = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
        self.history_path = Path(history_path) if history_path else root / "dynamic-batch.json"
        if self.history_path.is_file():
            try:
                self.jobs = [DynamicJob(**j) for j in json.loads(self.history_path.read_text())["jobs"]]
                for job in self.jobs:
                    if job.state in {"PROCESSING", "QUEUED"}:
                        job.state, job.error = "CANCELLED", "Application closed before processing completed"
            except (OSError, ValueError, TypeError, KeyError):
                self.jobs = []

    @property
    def is_running(self):
        return self._running

    @property
    def write_ready(self):
        return bool(self.jobs) and not self.is_running and all(j.state == "COMPLETED" and j.manifest for j in self.jobs)

    def start(self, jobs, limit):
        if self.is_running:
            raise RuntimeError("A numerical batch is already running")
        if not jobs or not 1 <= limit <= parallel_file_limit():
            raise ValueError("Invalid dynamic-file concurrency or empty batch")
        if len({j.key for j in jobs}) != len(jobs):
            raise ValueError("The same trial cannot be queued twice")
        sessions = {}
        for job in jobs:
            session = Path(job.session_xml).resolve()
            if not session.is_file() or Path(job.filename).name != job.filename:
                raise ValueError("Select a valid session.xml and local trial filename")
            if not (session.parent / (Path(job.filename).stem + ".c3d")).is_file():
                raise ValueError("Saved C3D required for " + job.filename)
            owner = sessions.setdefault(str(session), job.patient_id)
            if owner != job.patient_id:
                raise ValueError("One session cannot belong to different patient workers")
        self.jobs = jobs
        self.limit = limit
        self._cancelled = False
        self._running = True
        for job in jobs:
            job.state, job.manifest, job.error = "QUEUED", "", ""
            job.run_id = uuid.uuid4().hex
        self.preferences.setValue("processing/parallelDynamicFiles", limit)
        self._save()
        self._pump()

    def _save(self):
        atomic_json(self.history_path, {"jobs": [asdict(j) for j in self.jobs]})
        self.changed.emit()

    def _pump(self):
        for job in self.jobs:
            if len(self._active) >= self.limit:
                break
            if job.state != "QUEUED" or self._cancelled:
                continue
            try:
                self._launch(job.key, job)
            except Exception as exc:
                job.state, job.error = "FAILED", str(exc)
                self.trial_changed.emit(job)
                self._save()
        if not self._active and not any(j.state == "QUEUED" for j in self.jobs):
            self._running = False
            self._save()
            self.finished.emit()

    def _launch(self, key, job):
        filename = job.filename
        if Path(filename).suffix.lower() == ".c3d":
            records = ET.parse(job.session_xml).getroot().findall(".//Measurement")
            filename = next((r.get("Filename") for r in records if r.get("Filename")
                             and Path(r.get("Filename")).name == r.get("Filename")
                             and Path(r.get("Filename")).suffix.lower() in {".qtm", ".c3d"}
                             and Path(r.get("Filename")).stem.casefold() == Path(filename).stem.casefold()), filename)
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.MergedChannels)
        env = QProcessEnvironment.systemEnvironment()
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
            env.insert(name, "1")
        env.insert("SHRINERS_NON_INTERACTIVE", "1")
        env.insert("SHRINERS_AUTO_SELECT_CYCLE", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        launcher = _resolve_python_launcher(self.conda_env)
        lib_bin = Path(launcher[0]).parent / "Library" / "bin"
        if lib_bin.is_dir():
            env.insert("PATH", str(lib_bin) + os.pathsep + env.value("PATH"))
        process.setProcessEnvironment(env)
        process.setWorkingDirectory(str(_GAIT_DIR))
        command = launcher[1:] + [str(_GAIT_DIR / "Py3_DynamicMain.py"), "-s", job.session_xml,
            "-f", filename, "-t", job.condition, "--leftPlate", job.left_plate,
            "--rightPlate", job.right_plate, "--run-id", job.run_id]
        if job.interactive_fp:
            command.append("--interactiveFP")
        self._active[key] = (process, job, time.perf_counter(), bytearray())
        job.state = "PROCESSING"
        process.readyReadStandardOutput.connect(lambda: self._read(key, process))
        process.finished.connect(lambda code, status: self._done(key, process, code))
        process.errorOccurred.connect(lambda error: self._done(key, process, -1)
                                     if error == QProcess.FailedToStart else None)
        self.trial_changed.emit(job)
        self._save()
        process.start(launcher[0], command)

    def _read(self, key, process):
        current = self._active.get(key)
        if not current or current[0] is not process:
            return
        buffer = current[3]
        buffer.extend(bytes(process.readAllStandardOutput()))
        while b"\n" in buffer:
            line, _, rest = buffer.partition(b"\n")
            buffer[:] = rest
            text = line.decode("utf8", "replace").strip()
            self.log.emit(f"{current[1].filename}: {text}")
            if text.startswith("[WRITE_MANIFEST] "):
                current[1].manifest = text[len("[WRITE_MANIFEST] "):]
            if text:
                current[1].error = text[-1000:]

    def _done(self, key, process, code):
        current = self._active.get(key)
        if not current or current[0] is not process:
            return
        self._read(key, process)
        _, job, began, _ = self._active.pop(key)
        job.duration_s = time.perf_counter() - began
        if self._cancelled:
            job.state, job.error = "CANCELLED", "Cancelled by clinician"
        elif code == 0 and job.manifest:
            try:
                meta = json.loads(Path(job.manifest).read_text(encoding="utf8"))
                if meta["run_id"] != job.run_id or meta["trial_id"] != job.key:
                    raise ValueError("Worker returned another trial's manifest")
                if not Path(meta["gcd_path"]).is_file() or not Path(job.manifest).with_name("trajectories.npz").is_file():
                    raise ValueError("Worker artifacts are missing")
                job.state, job.error = "COMPLETED", ""
                job.gcd_duration_s = float(meta.get("timings", {}).get("gcd_s", 0))
            except Exception as exc:
                job.state, job.error = "FAILED", str(exc)
        else:
            job.state = "FAILED"
            job.error = job.error or process.errorString()
        process.deleteLater()
        self.trial_changed.emit(job)
        self._save()
        self._pump()

    def cancel(self):
        if not self._running:
            return
        self._cancelled = True
        for job in self.jobs:
            if job.state == "QUEUED":
                job.state = "CANCELLED"
                self.trial_changed.emit(job)
        for process, *_ in list(self._active.values()):
            pid = int(process.processId())
            if os.name == "nt" and pid:
                killer = QProcess(self)
                killer.errorOccurred.connect(lambda error, p=process: p.kill())
                killer.finished.connect(lambda code, status, p=process: p.kill() if code else None)
                killer.finished.connect(killer.deleteLater)
                killer.start("taskkill", ["/PID", str(pid), "/T", "/F"])
            else:
                process.kill()
        self._save()
        if self._running and not self._active:
            self._pump()

    def shutdown(self):
        self.cancel()
        for process, *_ in list(self._active.values()):
            process.waitForFinished(3000)
