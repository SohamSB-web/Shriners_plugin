"""Offline native-context, queue fidelity, acknowledgment and recovery checks."""
import ast
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest
import matplotlib.pyplot  # Required before Qt by the deployed conda environment.
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QPushButton, QProgressBar

from app.services.dynamic_write_manifest import WriteManifest, load_manifest, atomic_json, fingerprint
from app.services.qtm_command_dispatcher import QTMCommandDispatcher, DISPATCH_COMMAND
from app.services.qtm_trajectory_protocol import guarded_trajectory_command
from app.services.qtm_write_service import QTMWriteService, trajectory_queue

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def wait(app, predicate, timeout=60):
    deadline = time.monotonic() + timeout
    while not predicate():
        app.processEvents()
        assert time.monotonic() < deadline, "Qt operation timed out"
        time.sleep(.001)
    app.processEvents()


def manifests(folder, count):
    folder.mkdir(parents=True)
    (folder / "session.xml").write_text("<session/>")
    calibration = folder / "Static_BF_test.py"
    calibration.write_text("# synthetic fixture")
    result = []
    for i in range(count):
        name = f"Dynamic {i+1}"
        (folder / (name + ".c3d")).write_bytes(b"fixture")
        (folder / (name + ".qtm")).touch()
        gcd = folder / (name + ".GCD")
        gcd.write_text("fixture")
        recorder = WriteManifest(folder, name)
        recorder.bind_inputs(calibration)
        names = [f"Marker{n}" for n in range(13)]
        if i % 2:
            names += ["Pelfix", "LHeel", "RToe", "LForefoot", "RHindfoot"]
        for j, marker in enumerate(names):
            recorder.create(marker)
            xyz = np.arange(5.) + i*100 + j*10
            recorder.trajectory(marker, xyz, xyz+1, xyz+2, [True]*4+[False], 1, 4, 10,
                                {"start": 10, "end": 14})
        result.append(str(recorder.publish({"Frames": 5, "Capture_Frequency": 100., "First Frame": 1,
                      "Last Frame": 4, "initial_frame_offset": 10}, calibration, "test", gcd)))
    return result


class FakeNative:
    def __init__(self):
        self.owner = threading.get_ident()
        self.path = None
        self.dirty = False
        self.markers = {}
        self.samples = {}
        self.calls = []
        self.fail_marker = None
        trajectory = SimpleNamespace(find_trajectory=self.find, add_trajectory=self.create)
        series = SimpleNamespace(get_sample=self.sample, set_samples=self.set_samples)
        self.timeline = SimpleNamespace(get_measured_range=lambda: {"start": 10, "end": 14}, get_frequency=lambda: 100.)
        self.qtm = SimpleNamespace(gui=SimpleNamespace(timeline=self.timeline), file=SimpleNamespace(get_path=lambda: self.path, is_open=lambda: bool(self.path),
            is_dirty=lambda: self.dirty, open=self.open, save=self.save), data=SimpleNamespace(
            object=SimpleNamespace(trajectory=trajectory), series=SimpleNamespace(_3d=series)))
        # Exercise the unchanged main-branch sample/range implementation, not a duplicate of it.
        tree = ast.parse((ROOT / "QTM-GRPC/tools/Py3_staticmain.py").read_text(encoding="utf8"))
        definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {"setTrajectory", "createMarker"}]
        import math
        scope = {"qtm": self.qtm, "tline": self.timeline, "math": math}
        exec(compile(ast.Module(body=definitions, type_ignores=[]), "native-fixture", "exec"), scope)
        self.native_write = scope["setTrajectory"]
        self.native_create = scope["createMarker"]

    def open(self, path):
        assert threading.get_ident() == self.owner
        self.path = path
        self.dirty = False

    def save(self):
        assert threading.get_ident() == self.owner
        self.dirty = False

    def find(self, name):
        return self.markers.get((self.path, name))

    def create(self, name):
        assert threading.get_ident() == self.owner
        key = (self.path, name)
        assert key not in self.markers, "Unnecessary repeated marker creation"
        self.markers[key] = len(self.markers)+1
        self.dirty = True
        return self.markers[key]

    def sample(self, marker, frame):
        return self.samples.get((self.path, marker, frame))

    def set_samples(self, marker, target, samples):
        assert threading.get_ident() == self.owner
        for frame, sample in zip(range(target["start"], target["end"]+1), samples):
            self.samples[(self.path, marker, frame)] = sample
        self.dirty = True

    def execute(self, command, args):
        assert threading.get_ident() == self.owner
        self.calls.append((command, args))
        if command == "ApplyTrajectoryOperation" and args["operation"]["marker"] == self.fail_marker:
            raise RuntimeError("Injected native failure")
        return guarded_trajectory_command(self.qtm, self.timeline, self.native_create, self.native_write, command, args)


class FakeTransport:
    def __init__(self, native, delay=1):
        self.dispatcher = QTMCommandDispatcher(native.execute)
        self.delay = delay
        self.active = 0
        self.peak = 0
        self.number = 0
        self.pending = []
        self.lose_ack_at = None

    def send(self, command, args, token, success, failure):
        self.active += 1
        self.peak = max(self.peak, self.active)
        assert self.active == 1, "Overlapping operations"
        self.number += 1
        request_id = str(self.number)
        native = command not in {"BeginTrajectoryBatch", "EndTrajectoryBatch"}
        errors = []

        def receive():
            try:
                result = self.dispatcher.receive("QueueTrajectoryCommand" if native else command,
                    {"token": token, "request_id": request_id, "command": command, "args": args})
                self.pending.append(result)
            except Exception as exc:
                errors.append(str(exc))
        # Real infrastructure thread: must never call the native fake.
        thread = threading.Thread(target=receive)
        thread.start()
        thread.join()

        def finish():
            if errors:
                self.active -= 1
                failure(errors[0])
                return
            if native:
                self.dispatcher.dispatch_one()
                result = self.dispatcher.receive("GetTrajectoryCommandStatus", {"token": token, "request_id": request_id})
                self.active -= 1
                if request_id == self.lose_ack_at:
                    failure("Timed out after write; completion uncertain")
                elif result["state"] == "COMPLETED":
                    success(result["result"])
                else:
                    failure(result["error"])
            else:
                self.active -= 1
                success(self.pending[-1])
        QTimer.singleShot(self.delay, finish)


@pytest.mark.parametrize("count", [1, 3, 20])
def test_complete_queue_order_payloads_and_trial_progress(app, tmp_path, count):
    paths = manifests(tmp_path / "session", count)
    native = FakeNative()
    transport = FakeTransport(native)
    service = QTMWriteService(history_path=tmp_path / "history.json", transport=transport)
    progress = []
    service.changed.connect(lambda history: progress.append(history.copy()))
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(threading.get_ident()))
    timer.start(1)
    service.start_confirmed(paths)
    with pytest.raises(RuntimeError, match="already active"):
        service.start_confirmed(paths)
    wait(app, lambda: not service.is_running)
    timer.stop()
    assert service.history["state"] == "COMPLETED", service.history
    assert service.history["completed"] == count and service.history["total"] == count
    assert len(service.write_queue) == count
    assert [len(q) for q in service.write_queue] == [13 if i % 2 == 0 else 18 for i in range(count)]
    expected = []
    for path, queue in zip(paths, service.write_queue):
        meta, arrays = load_manifest(path)
        assert len(queue) == len([op for op in meta["operations"] if op["kind"] == "trajectory"])
        for record in queue:
            assert len(record) == 9
            assert record[6:] == [4, 10, {"start": 10, "end": 14}]
            assert record[4].tolist() == [True]*4+[False]
        expected += [(meta["measurement_path"], op["marker"], op["kind"]) for op in meta["operations"]]
    applied = [(args["measurement_path"], args["operation"]["marker"], args["operation"]["kind"])
               for command, args in native.calls if command == "ApplyTrajectoryOperation"]
    assert applied == expected
    assert transport.peak == 1 and len(ticks) > count
    assert set(ticks) == {native.owner}
    assert sorted(set(h["completed"] for h in progress)) == list(range(count+1))
    assert all(h["completed"] == sum(t["state"] == "COMPLETED" for t in h["trials"]) for h in progress)


def test_failure_stops_queue_and_uncertain_operation_is_never_replayed(app, tmp_path):
    paths = manifests(tmp_path / "session", 3)
    native = FakeNative()
    transport = FakeTransport(native)
    transport.lose_ack_at = "5"  # Begin, select, create Marker0, write Marker0, create Marker1.
    service = QTMWriteService(history_path=tmp_path / "history.json", transport=transport)
    service.start_confirmed(paths)
    wait(app, lambda: not service.is_running)
    assert service.history["state"] == "FAILED" and service.history["completed"] == 0
    assert [t["state"] for t in service.history["trials"]] == ["FAILED", "NOT_STARTED", "NOT_STARTED"]
    applied = len([c for c, _ in native.calls if c == "ApplyTrajectoryOperation"])
    transport.lose_ack_at = None
    service.start_confirmed(paths)
    wait(app, lambda: not service.is_running)
    assert service.history["state"] == "COMPLETED", service.history
    all_applied = [a for c, a in native.calls if c == "ApplyTrajectoryOperation"]
    assert len({a["operation_id"] for a in all_applied}) == len(all_applied)
    assert applied == 3


def test_mismatched_uncertain_readback_stops_without_write(app, tmp_path):
    paths = manifests(tmp_path / "session", 1)
    native = FakeNative()
    native.fail_marker = "Marker0"
    transport = FakeTransport(native)
    service = QTMWriteService(history_path=tmp_path / "history.json", transport=transport)
    service.start_confirmed(paths)
    wait(app, lambda: not service.is_running)
    count = len(native.calls)
    native.fail_marker = None
    service.start_confirmed(paths)
    wait(app, lambda: not service.is_running)
    assert service.history["state"] == "FAILED"
    assert not any(c == "ApplyTrajectoryOperation" for c, _ in native.calls[count:])


def test_dispatcher_rejects_wrong_thread_overlap_and_payload_reuse():
    calls = []
    dispatcher = QTMCommandDispatcher(lambda *args: calls.append(args) or {"verified": True})
    dispatcher.receive("BeginTrajectoryBatch", {"token": "batch"})
    with pytest.raises(RuntimeError, match="Another"):
        dispatcher.receive("BeginTrajectoryBatch", {"token": "other"})
    args = {"token": "batch", "request_id": "one", "command": "ApplyTrajectoryOperation", "args": {"marker": "X"}}
    dispatcher.receive("QueueTrajectoryCommand", args)
    errors = []
    def wrong_thread():
        try:
            dispatcher.dispatch_one()
        except Exception as exc:
            errors.append(str(exc))
    thread = threading.Thread(target=wrong_thread)
    thread.start(); thread.join()
    assert errors and not calls
    with pytest.raises(RuntimeError, match="pending"):
        dispatcher.receive("QueueTrajectoryCommand", {**args, "request_id": "two"})
    dispatcher.dispatch_one()
    assert dispatcher.receive("QueueTrajectoryCommand", args)["state"] == "COMPLETED"
    dispatcher.dispatch_one()
    assert len(calls) == 1
    with pytest.raises(ValueError, match="reused"):
        dispatcher.receive("QueueTrajectoryCommand", {**args, "args": {"marker": "Y"}})


@pytest.mark.parametrize("change", ["nan", "offset", "target", "mask", "identity"])
def test_invalid_payload_rejected_before_any_native_call(app, tmp_path, change):
    paths = manifests(tmp_path / "session", 1)
    path = Path(paths[0])
    meta = json.loads(path.read_text())
    if change in {"nan", "mask"}:
        _, arrays = load_manifest(path)
        if change == "nan":
            arrays["op_1_xyz"][0, 0] = np.nan
        else:
            arrays["op_1_exists"] = np.ones(5, dtype=int)
        np.savez_compressed(path.with_name("trajectories.npz"), **arrays)
        meta["arrays_sha256"] = fingerprint(path.with_name("trajectories.npz"))
    elif change == "offset":
        meta["operations"][1]["offset"] = "10"
    elif change == "target":
        meta["operations"][1]["target_range"] = {"start": 9, "end": 30}
    else:
        meta["measurement_path"] = str(tmp_path / "other-patient/Dynamic 1.qtm")
    atomic_json(path, meta)
    native = FakeNative()
    service = QTMWriteService(history_path=tmp_path / "history.json", transport=FakeTransport(native))
    service.start_confirmed(paths)
    wait(app, lambda: not service.is_running)
    assert service.history["state"] == "FAILED" and not native.calls


def test_dirty_wrong_measurement_does_not_switch_or_write(app, tmp_path):
    paths = manifests(tmp_path / "session", 1)
    native = FakeNative()
    native.path = str(tmp_path / "another-patient.qtm")
    native.dirty = True
    service = QTMWriteService(history_path=tmp_path / "history.json", transport=FakeTransport(native))
    service.start_confirmed(paths)
    wait(app, lambda: not service.is_running)
    assert service.history["state"] == "FAILED" and not native.markers
    assert "Save or discard" in service.history["current"]


def test_ui_has_only_one_write_button_bar_and_label(app, tmp_path, monkeypatch):
    import app.ui.main_window as module
    from app.models.data_models import AppSettings
    from app.services.dynamic_batch_service import DynamicBatchService
    monkeypatch.setattr(module, "DynamicBatchService", lambda env, parent:
                        DynamicBatchService(env, parent, history_path=tmp_path / "batch.json"))
    monkeypatch.setattr(module, "QTMWriteService", lambda parent:
                        QTMWriteService(parent, history_path=tmp_path / "writes.json", transport=FakeTransport(FakeNative())))
    window = module.MainWindow(AppSettings(patients_data_location=str(tmp_path)))
    buttons = [b.text() for b in window.findChildren(QPushButton)]
    assert buttons.count("Write Operation") == 1
    assert not any(b in buttons for b in ("Cancel QTM Write", "Retry Failed", "View Details", "OK"))
    assert not hasattr(window, "_write_notice") and not hasattr(window, "_qtm_write_status")
    assert len(window._dynamic_page._write_panel.findChildren(QProgressBar)) == 1
    window.close()


@pytest.mark.parametrize("dispatch_enabled", [True, False])
def test_actual_async_grpc_rest_transport_on_disposable_mock_servers(app, tmp_path, monkeypatch, dispatch_enabled):
    """Use random local ports; this cannot send a request to the user's QTM instance."""
    from concurrent.futures import ThreadPoolExecutor
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import sys
    import grpc
    from PySide6.QtCore import QObject, Signal, Qt
    import app.services.qtm_write_service as module
    from app.services.settings_service import SettingsService
    monkeypatch.syspath_prepend(str(ROOT / "QTM-GRPC"))
    import qtm_data_transfer_pb2 as pb
    import qtm_data_transfer_pb2_grpc as rpc

    native = FakeNative()
    dispatcher = QTMCommandDispatcher(native.execute)
    class Servicer(rpc.QtmTkinterBridgeServicer):
        def SendCommandToQtm(self, request, context):
            try:
                payload = dispatcher.receive(request.command_name, json.loads(request.command_args_json))
                return pb.Ack(success=True, message=json.dumps(payload))
            except Exception as exc:
                return pb.Ack(success=False, message=str(exc))
    server = grpc.server(ThreadPoolExecutor(max_workers=3))
    rpc.add_QtmTkinterBridgeServicer_to_server(Servicer(), server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    dispatched = threading.Event()
    class NativeCallback(QObject):
        invoke = Signal()
    callback = NativeCallback()
    def dispatch():
        try:
            dispatcher.dispatch_one()
        finally:
            dispatched.set()
    callback.invoke.connect(dispatch, Qt.QueuedConnection)
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            assert self.path == "/api/scripting/qtm/gui/send_command/"
            assert json.loads(self.rfile.read(int(self.headers["Content-Length"]))) == [DISPATCH_COMMAND]
            if dispatch_enabled:
                dispatched.clear()
                callback.invoke.emit()
                assert dispatched.wait(10)
            self.send_response(200 if dispatch_enabled else 503)
            self.end_headers()
            self.wfile.write(b"null")
        def log_message(self, *_):
            pass
    http = HTTPServer(("127.0.0.1", 0), Handler)
    receiver = threading.Thread(target=http.serve_forever, daemon=True)
    receiver.start()
    real_url, real_channel = module.QUrl, grpc.insecure_channel
    monkeypatch.setattr(module, "QUrl", lambda url: real_url(url.replace("localhost:7979", f"127.0.0.1:{http.server_port}")))
    monkeypatch.setattr(grpc, "insecure_channel", lambda _, **kwargs: real_channel(f"127.0.0.1:{port}", **kwargs))
    monkeypatch.setattr(SettingsService, "load_app_settings", lambda _: SimpleNamespace(qtm_grpc_location=str(ROOT / "QTM-GRPC")))
    paths = manifests(tmp_path / "session", 1)
    service = QTMWriteService(history_path=tmp_path / "history.json")
    try:
        service.start_confirmed(paths)
        wait(app, lambda: not service.is_running)
        if dispatch_enabled:
            assert service.history["state"] == "COMPLETED", service.history
            assert len([c for c, _ in native.calls if c == "ApplyTrajectoryOperation"]) == 26
        else:
            assert service.history["state"] == "FAILED"
            assert not native.calls
            assert "7979" in service.history["current"]
        assert not dispatcher.busy
    finally:
        service.shutdown()
        http.shutdown()
        http.server_close()
        receiver.join(2)
        server.stop(0).wait(2)
