"""One acknowledged trajectory operation at a time, driven by the Qt event loop."""
from contextlib import ExitStack
import json
import logging
from pathlib import Path
import sys
import time
import uuid

import numpy as np
from PySide6.QtCore import QObject, QTimer, QStandardPaths, Signal, QUrl, QLockFile
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest

from app.services.dynamic_write_manifest import atomic_json, load_manifest, trial_output_lock
from app.services.event_store import paths_match
from app.services.qtm_command_dispatcher import DISPATCH_COMMAND

log = logging.getLogger(__name__)


class TrajectoryNotExecuted(RuntimeError):
    """The dispatcher confirmed cancellation before entering native QTM code."""


class TrajectoryTransport(QObject):
    """gRPC futures receive/status only; REST invokes QTM's registered GUI command."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.network = QNetworkAccessManager(self)
        self.timer = QTimer(self)
        self.timer.setInterval(10)
        self.timer.timeout.connect(self._poll)
        self.future = self.channel = None

    def _grpc(self, command, args, success, failure):
        try:
            from app.services.settings_service import SettingsService
            directory = SettingsService().load_app_settings().qtm_grpc_location
            if directory not in sys.path:
                sys.path.insert(0, directory)
            import grpc
            import qtm_data_transfer_pb2 as pb
            import qtm_data_transfer_pb2_grpc as rpc
            self.channel = grpc.insecure_channel("localhost:50052", options=[("grpc.max_send_message_length", 64*1024*1024)])
            self.future = rpc.QtmTkinterBridgeStub(self.channel).SendCommandToQtm.future(
                pb.CommandToQtm(command_name=command, command_args_json=json.dumps(args, allow_nan=False)), timeout=30)
            self.success, self.failure = success, failure
            self.timer.start()
        except Exception as exc:
            QTimer.singleShot(0, lambda message=str(exc): failure(message))

    def _poll(self):
        if not self.future.done():
            return
        self.timer.stop()
        future, channel, success, failure = self.future, self.channel, self.success, self.failure
        self.future = self.channel = None
        channel.close()
        try:
            response = future.result()
            if not response.success:
                raise RuntimeError(response.message)
            result = json.loads(response.message)
            if not isinstance(result, dict):
                raise ValueError("Invalid QTM dispatcher acknowledgment")
        except Exception as exc:
            failure(str(exc))
        else:
            success(result)

    def send(self, command, args, token, success, failure):
        if command in {"BeginTrajectoryBatch", "EndTrajectoryBatch"}:
            self._grpc(command, {"token": token}, success, failure)
            return
        request_id = uuid.uuid4().hex
        dispatch_error = ""

        def status():
            self._grpc("GetTrajectoryCommandStatus", {"token": token, "request_id": request_id}, done, failure)

        def done(result):
            if result.get("state") == "COMPLETED":
                success(result["result"])
            elif result.get("state") == "QUEUED":
                self._grpc("CancelQueuedTrajectoryCommand", {"token": token, "request_id": request_id},
                           lambda _: failure(TrajectoryNotExecuted("QTM did not execute the command. Check the updated bridge and REST interface on port 7979. " + dispatch_error)), failure)
            else:
                failure(result.get("error") or "QTM completion is uncertain (" + str(result.get("state")) + "); no write will be retried")

        def queued(result):
            if result.get("state") == "COMPLETED":
                done(result)
                return
            if result.get("state") != "QUEUED":
                failure("QTM did not accept a single queued operation")
                return
            request = QNetworkRequest(QUrl("http://localhost:7979/api/scripting/qtm/gui/send_command/"))
            request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
            request.setTransferTimeout(30000)
            reply = self.network.post(request, json.dumps([DISPATCH_COMMAND]).encode())

            def dispatched():
                nonlocal dispatch_error
                # An HTTP timeout can follow a completed mutation. Query status; never resend.
                dispatch_error = reply.errorString() if reply.error() else ""
                reply.deleteLater()
                status()
            reply.finished.connect(dispatched)

        self._grpc("QueueTrajectoryCommand", {"token": token, "request_id": request_id,
                   "command": command, "args": args}, queued, lambda _: status())


def trajectory_queue(meta, arrays):
    """Complete nine-argument SetTrajectory records, in original order."""
    result = []
    for operation in meta["operations"]:
        if operation["kind"] != "trajectory":
            continue
        xyz = arrays[operation["array"] + "_xyz"]
        mask = arrays[operation["array"] + "_exists"]
        result.append([operation["marker"], *[xyz[:, i].copy() for i in range(3)], mask.copy(),
                       operation["start"], operation["end"], operation["offset"], operation.get("target_range")])
    if not result:
        raise ValueError("The trial contains no trajectory writes")
    return result


class QTMWriteService(QObject):
    changed = Signal(object)
    confirmation_ready = Signal(object)
    completed = Signal(object)
    error = Signal(str)

    def __init__(self, parent=None, history_path=None, transport=None):
        super().__init__(parent)
        root = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
        self.history_path = Path(history_path) if history_path else root / "qtm-writes.json"
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        root.mkdir(parents=True, exist_ok=True)
        self.lock = QLockFile(str(root / "qtm-trajectory-write.lock"))
        self.lock.setStaleLockTime(0)
        self.transport = transport or TrajectoryTransport(self)
        self._running = self._preparing = self._lease = False
        self._generator = None
        self._locks = ExitStack()
        self.write_queue = []
        self.history = {}
        if self.history_path.is_file():
            try:
                self.history = json.loads(self.history_path.read_text(encoding="utf8"))
                if self.history.get("state") == "WRITING":
                    self.history.update(state="FAILED", current="Previous QTM completion is uncertain; read-back required")
            except (OSError, ValueError):
                pass

    @property
    def is_running(self):
        return self._running or self._preparing

    def prepare(self, paths):
        if self.is_running:
            raise RuntimeError("A QTM write operation is already active")
        if not 1 <= len(paths) <= 20:
            raise ValueError("Select between 1 and 20 processed dynamic files for Write Operation")
        self._preparing = True
        self.changed.emit(self.history)
        manifests, queue = [], []
        paths = [str(Path(path).resolve()) for path in paths]

        def next_trial():
            if not self._preparing:
                return
            try:
                meta, arrays = load_manifest(paths[len(manifests)])
                if meta["trial_id"] in {m["trial_id"] for m in manifests}:
                    raise ValueError("Duplicate trial in the trajectory write queue")
                queue.append(trajectory_queue(meta, arrays))
                manifests.append(meta)
                if len(manifests) < len(paths):
                    QTimer.singleShot(0, next_trial)
                    return
                self.write_queue = queue
                self._preparing = False
                self.confirmation_ready.emit({"paths": paths, "manifests": manifests})
                self.changed.emit(self.history)
            except Exception as exc:
                self._preparing = False
                self.history = {"state": "FAILED", "completed": 0, "total": len(paths), "current": str(exc)}
                self.changed.emit(self.history)
                self.error.emit(str(exc))
        QTimer.singleShot(0, next_trial)

    def start_confirmed(self, paths):
        if self.is_running:
            raise RuntimeError("A QTM write operation is already active")
        if not 1 <= len(paths) <= 20 or not self.lock.tryLock(0):
            raise RuntimeError("Another Write Operation is active, or the queue size is invalid")
        self._running = True
        self._paths = [str(Path(path).resolve()) for path in paths]
        previous_paths = [t["manifest"] for t in self.history.get("trials", [])]
        self._token = self.history.get("id") if self.history.get("state") == "FAILED" and previous_paths == self._paths else None
        self._token = self._token or uuid.uuid4().hex
        self._previous = {t["manifest"]: t for t in self.history.get("trials", [])}
        self.history = {"state": "WRITING", "id": self._token, "trials": [], "completed": 0,
                        "total": len(paths), "current": "Validating trajectory queue"}
        self._generator = self._write()
        self._publish()
        QTimer.singleShot(0, self._advance)

    def _publish(self):
        self.history["completed"] = sum(t["state"] == "COMPLETED" for t in self.history.get("trials", []))
        atomic_json(self.history_path, self.history)
        self.changed.emit(json.loads(json.dumps(self.history)))

    def _advance(self, result=None):
        if not self._running:
            return
        try:
            command, args = self._generator.send(result)
            if command is None:
                QTimer.singleShot(0, self._advance)
                return
            self.transport.send(command, args, self._token,
                                lambda value: QTimer.singleShot(0, lambda: self._advance(value)), self._fail)
        except StopIteration:
            self._finish()
        except Exception as exc:
            self._fail(str(exc))

    def _write(self):
        trials = self.history["trials"]
        self.write_queue = []
        identities = set()
        for path in self._paths:
            meta, arrays = load_manifest(path)
            if meta["trial_id"] in identities:
                raise ValueError("Duplicate trial in the trajectory write queue")
            identities.add(meta["trial_id"])
            self.write_queue.append(trajectory_queue(meta, arrays))
            old = self._previous.get(path, {})
            states = old.get("operations", ["NOT_STARTED"] * len(meta["operations"]))
            if len(states) != len(meta["operations"]):
                raise ValueError("Saved trajectory status does not match this manifest")
            trials.append({"manifest": path, "trial": Path(meta["source_c3d"]).name,
                           "state": "COMPLETED" if old.get("state") == "COMPLETED" else "NOT_STARTED",
                           "operations": states.copy(), "error": ""})
            yield None, None  # Give Qt a turn between disk/checksum validation of each trial.
        began = yield "BeginTrajectoryBatch", {}
        if began.get("protocol") != 2 or began.get("dispatcher") != DISPATCH_COMMAND:
            raise ValueError("Reload the updated QTM bridge; safe scripting-context trajectory dispatch is required")
        self._lease = True
        for number, trial in enumerate(trials, 1):
            if trial["state"] == "COMPLETED":
                continue
            meta, arrays = load_manifest(trial["manifest"])
            self._locks.enter_context(trial_output_lock(Path(meta["source_c3d"]).parent, meta["source_c3d"]))
            trial["state"] = "WRITING"
            self.history["current"] = f"Writing Dynamic {number} / {len(trials)}"
            self._publish()
            base = {"measurement_path": meta["measurement_path"], "overwrite_confirmed": True}
            context = yield "SelectTrajectoryTrial", {**base, "markers": sorted({o["marker"] for o in meta["operations"]})}
            if not paths_match(context["measurement_path"], meta["measurement_path"]) or context["frequency"] != meta["frequency"]:
                raise ValueError("QTM destination/frequency does not match the processed trial")
            for operation in meta["operations"]:
                if operation["kind"] == "trajectory":
                    target = operation.get("target_range") or {"start": operation["offset"], "end": operation["offset"] + meta["frames"] - 1}
                    if not context["measured_range"]["start"] <= target["start"] <= target["end"] <= context["measured_range"]["end"]:
                        raise ValueError("Processed trajectory does not fit the QTM recording range")
            records = iter(self.write_queue[number - 1])
            for index, operation in enumerate(meta["operations"]):
                args = {**base, "frequency": meta["frequency"], "measured_range": context["measured_range"],
                        "operation": operation, "operation_id": meta["run_id"] + ":" + str(index)}
                if operation["kind"] == "trajectory":
                    record = next(records)
                    if record[0] != operation["marker"]:
                        raise ValueError("Trajectory queue marker order does not match the manifest")
                    xyz = np.column_stack(record[1:4])
                    args["trajectory"] = {axis: [float(v) if np.isfinite(v) else None for v in xyz[:, i]]
                                          for i, axis in enumerate("XYZ")}
                    args["trajectory"]["exists"] = record[4].tolist()
                prior = trial["operations"][index]
                if prior in {"COMPLETED", "WRITING", "UNCERTAIN"}:
                    checked = yield "VerifyTrajectoryOperation", args
                    if checked.get("verified") is True and paths_match(checked["measurement_path"], base["measurement_path"]):
                        trial["operations"][index] = "COMPLETED"
                        continue
                    raise RuntimeError("Previous operation differs or is uncertain; inspect QTM before any further write: " + operation["marker"])
                trial["operations"][index] = "WRITING"
                self._publish()
                log.info("QTM start trial=%s/%s file=%s marker=%s target=%s range=%s offset=%s length=%s time=%s",
                         number, len(trials), trial["trial"], operation["marker"], base["measurement_path"],
                         operation.get("target_range"), operation.get("offset"), meta["frames"], time.time())
                ack = yield "ApplyTrajectoryOperation", args
                if ack.get("operation_id") != args["operation_id"] or ack.get("verified") is not True or not paths_match(ack["measurement_path"], base["measurement_path"]):
                    raise RuntimeError("QTM did not acknowledge this exact trajectory operation")
                log.info("QTM complete trial=%s file=%s marker=%s ack=%s time=%s", number, trial["trial"], operation["marker"], ack, time.time())
                trial["operations"][index] = "COMPLETED"
                self._publish()
            saved = yield "CompleteTrajectoryTrial", {**base, "frequency": meta["frequency"], "measured_range": context["measured_range"]}
            if saved.get("saved") is not True or not paths_match(saved["measurement_path"], base["measurement_path"]):
                raise RuntimeError("QTM did not confirm saving the completed trial")
            trial["state"] = "COMPLETED"
            self._locks.close()
            self._publish()
        yield "EndTrajectoryBatch", {}
        self._lease = False
        self.history.update(state="COMPLETED", current=f"Done — {len(trials)} / {len(trials)}")

    def _fail(self, message):
        if not self._running:
            return
        not_executed = isinstance(message, TrajectoryNotExecuted)
        message = str(message)
        log.error("QTM queue stopped: %s", message)
        self.history["state"] = "FAILED"
        for number, trial in enumerate(self.history["trials"], 1):
            if trial["state"] == "WRITING":
                trial.update(state="FAILED", error=message)
                trial["operations"] = [("NOT_STARTED" if not_executed else "UNCERTAIN") if state == "WRITING" else state for state in trial["operations"]]
                self.history["current"] = f"Writing failed at Dynamic {number} / {self.history['total']} — {message}"
                break
        else:
            self.history["current"] = message
        if self._lease:
            self._lease = False
            self.transport.send("EndTrajectoryBatch", {}, self._token, lambda _: self._finish(),
                                lambda error: self._finish(error))
        else:
            self._finish()

    def _finish(self, release_error=None):
        if release_error:
            self.history["current"] += " — Dispatcher still reserved; inspect QTM and reload scripts before another batch: " + release_error
        self._locks.close()
        self._generator = None
        self._running = False
        self.lock.unlock()
        self._publish()
        atomic_json(self.history_path.parent / "qtm-write-history" / (self.history["id"] + ".json"), self.history)
        self.completed.emit(self.history)

    def shutdown(self):
        if self._running:
            # Preserve uncertainty, never cancel a native mutation or send another write on shutdown.
            self.history.update(state="FAILED", current="Application closed during writing; completion requires read-back")
            self._publish()
            self._locks.close()
            self.lock.unlock()
            self._running = False
            self._generator.close()
            self._generator = None
        self._preparing = False
