"""Real subprocess scheduling; local outbox and guarded QTM delivery regressions."""
import json
import os
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest
import matplotlib.pyplot  # Import before Qt in the deployed conda environment.
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QStackedWidget, QWidget

from app.services.dynamic_write_manifest import WriteManifest, load_manifest, atomic_json, trial_output_lock
from app.services.dynamic_batch_service import DynamicBatchService, DynamicJob
from app.services.qtm_write_service import QTMWriteService
from app.services.qtm_trajectory_protocol import guarded_trajectory_command

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_preferences(monkeypatch):
    import app.services.dynamic_batch_service as module
    values = {}
    monkeypatch.setattr(module, "QSettings", lambda *_: SimpleNamespace(
        value=lambda key, default=None: values.get(key, default),
        setValue=lambda key, value: values.update({key: value})))


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def wait_until(app, predicate, timeout=30):
    end = time.monotonic() + timeout
    while not predicate():
        app.processEvents()
        if time.monotonic() > end:
            pytest.fail("Background operation timed out")
        time.sleep(.005)
    app.processEvents()


def artifact(folder, name="Dynamic 1", duplicate=False):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "session.xml").write_text("<session/>")
    (folder / (name + ".c3d")).write_bytes(b"fixture-only")
    calibration = folder / "Static_BF_fixture.py"
    calibration.write_text("# synthetic calibration fixture\n")
    gcd = folder / "GCD" / (name + ".GCD")
    gcd.parent.mkdir(exist_ok=True)
    gcd.write_text("#!DST-Python3_ShrineGaitModel\n!LeftTrunkTilt\n1\n")
    recorder = WriteManifest(folder, name)
    recorder.bind_inputs(calibration)
    recorder.create("LHJC")
    if duplicate:
        recorder.create("LHJC")
    x = np.arange(5, dtype=float)
    recorder.trajectory("LHJC", x, x + 1, x + 2, [True]*4 + [False], 1, 4, 10)
    return recorder.publish({"Frames": 5, "Capture_Frequency": 100., "First Frame": 1,
                             "Last Frame": 4, "initial_frame_offset": 10}, calibration, "fixture", gcd)


def test_manifest_preserves_order_duplicates_masks_and_offsets(tmp_path):
    path = artifact(tmp_path / "session", duplicate=True)
    meta, arrays = load_manifest(path)
    assert [o["kind"] for o in meta["operations"]] == ["create", "create", "trajectory"]
    assert meta["operations"][-1]["offset"] == 10
    np.testing.assert_array_equal(arrays["op_2_xyz"][:, 0], np.arange(5))
    np.testing.assert_array_equal(arrays["op_2_exists"], [True]*4 + [False])
    assert "name" not in meta and "mrn" not in meta


@pytest.mark.parametrize("change", ["input", "arrays", "gcd", "reprocess"])
def test_changed_artifacts_are_rejected(tmp_path, change):
    path = artifact(tmp_path / "session")
    if change == "input":
        (tmp_path / "session/Dynamic 1.c3d").write_bytes(b"changed")
    elif change == "arrays":
        path.with_name("trajectories.npz").write_bytes(b"changed")
    elif change == "gcd":
        (tmp_path / "session/GCD/Dynamic 1.GCD").write_text("changed")
    else:
        artifact(tmp_path / "session")
    with pytest.raises((ValueError, OSError)):
        load_manifest(path)


def test_trial_lock_prevents_concurrent_output_and_releases(tmp_path):
    with trial_output_lock(tmp_path, "Dynamic 1.qtm"):
        with pytest.raises(OSError):
            with trial_output_lock(tmp_path, "Dynamic 1.c3d"):
                pytest.fail("Duplicate output writer acquired the lock")
        with trial_output_lock(tmp_path, "Dynamic 2.c3d"):
            pass
    with trial_output_lock(tmp_path, "Dynamic 1.qtm"):
        pass


def test_local_dynamic_capture_cannot_contact_qtm(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(ROOT / "Gait-lab-Vicon-to-QTM"))
    import gapi
    previous = gapi.dynamic_write_manifest
    try:
        recorder = gapi.begin_local_dynamic(tmp_path, "Dynamic 1")
        monkeypatch.setattr(gapi, "_is_qtm_port_open", lambda: pytest.fail("Numerical worker contacted QTM"))
        assert gapi.GetForcePlate() == {}
        gapi.CreateModeledMarker("LHJC")
        gapi.SetTrajectory("LHJC", [1.], [2.], [3.], [True], 0, 1, 8)
        assert len(recorder.operations) == 2
        with pytest.raises(RuntimeError, match="disabled"):
            gapi.grpc_send_command("SetEvent", "{}")
    finally:
        gapi.dynamic_write_manifest = previous


FAKE_PROCESS = '''
import argparse, json, os, sys, time
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('-s');p.add_argument('-f');p.add_argument('-t')
p.add_argument('--leftPlate');p.add_argument('--rightPlate');p.add_argument('--run-id')
a=p.parse_args()
folder=Path(a.s).parent
began=time.time()
from app.services.dynamic_write_manifest import WriteManifest, trial_output_lock
with trial_output_lock(folder,a.f):
    time.sleep(.25)
    if (folder/'fail').exists():raise RuntimeError('injected numerical failure')
    import numpy as np
    m=WriteManifest(folder,a.f,a.run_id)
    c=folder/'Static_BF_fixture.py';m.bind_inputs(c)
    m.create('LHJC');m.trajectory('LHJC',range(5),range(5),range(5),[True]*5,0,5)
    gcd=folder/'GCD'/(Path(a.f).stem+'.GCD');gcd.parent.mkdir(exist_ok=True)
    gcd.write_text('fixture curve\\n'+'\\n'.join(str(x) for x in np.arange(5)**2))
    manifest=m.publish({'Frames':5,'Capture_Frequency':100.,'First Frame':0,'Last Frame':5,'initial_frame_offset':0},c,'fixture',gcd)
    (folder/(Path(a.f).stem+'.timing.json')).write_text(json.dumps({'start':began,'end':time.time(),'pid':os.getpid()}))
    print('[WRITE_MANIFEST] '+str(manifest),flush=True)
'''


@pytest.fixture
def process_setup(tmp_path, monkeypatch):
    import app.services.dynamic_batch_service as module
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    (script_dir / "Py3_DynamicMain.py").write_text(FAKE_PROCESS)
    monkeypatch.setattr(module, "_GAIT_DIR", script_dir)
    monkeypatch.setattr(module, "_resolve_python_launcher", lambda _: [sys.executable, "-u"])
    monkeypatch.setattr(module, "parallel_file_limit", lambda: 4)
    monkeypatch.setenv("PYTHONPATH", str(ROOT))
    jobs = []
    for patient, count in enumerate([2, 1, 3, 1]):
        session = tmp_path / ("patient_" + str(patient)) / "session"
        session.mkdir(parents=True)
        (session / "session.xml").write_text("<session/>")
        (session / "Static_BF_fixture.py").write_text("# fixture")
        for i in range(count):
            name = f"Dynamic {i+1}.c3d"
            (session / name).write_bytes(b"fixture")
            jobs.append(DynamicJob(str(patient), str(session / "session.xml"), name))
    return DynamicBatchService(history_path=tmp_path / "batch.json"), jobs


@pytest.mark.parametrize("limit", [1, 2, 3, 4])
def test_real_file_process_concurrency_and_isolation(app, process_setup, limit):
    service, jobs = process_setup
    active_counts = []
    service.changed.connect(lambda: active_counts.append(len(service._active)))
    service.start(jobs, limit)
    wait_until(app, lambda: not service.is_running, timeout=60)
    assert all(j.state == "COMPLETED" for j in jobs), [j.error for j in jobs]
    assert max(active_counts) == limit
    assert service.write_ready
    timings = []
    by_patient = {}
    for job in jobs:
        session = Path(job.session_xml).parent
        record = json.loads((session / (Path(job.filename).stem + ".timing.json")).read_text())
        by_patient.setdefault(job.patient_id, []).append(record)
        timings.append(record)
        meta, _ = load_manifest(job.manifest)
        assert Path(meta["source_c3d"]).parent == session
    assert len({t["pid"] for t in timings}) == len(jobs)
    peak = max(sum(t["start"] <= moment < t["end"] for t in timings) for moment in [t["start"] for t in timings])
    assert peak == limit


def test_numerical_failure_blocks_write_button_and_other_patients_continue(app, process_setup):
    service, jobs = process_setup
    (Path(jobs[0].session_xml).parent / "fail").touch()
    service.start(jobs, 2)
    wait_until(app, lambda: not service.is_running)
    assert jobs[0].state == "FAILED"
    assert any(j.state == "COMPLETED" for j in jobs)
    assert not service.write_ready


def test_cancel_cleans_processes_and_queued_jobs(app, process_setup):
    service, jobs = process_setup
    service.start(jobs, 2)
    service.cancel()
    wait_until(app, lambda: not service.is_running)
    assert not service._active
    assert all(j.state == "CANCELLED" for j in jobs)
    assert not service.write_ready


def test_dynamic_page_write_visibility_and_switch_preserves_batch(app, tmp_path):
    from app.ui.pages.dynamic_analysis_page import DynamicAnalysisPage
    batch = DynamicBatchService(history_path=tmp_path / "batch.json")
    writes = QTMWriteService(history_path=tmp_path / "writes.json")
    page = DynamicAnalysisPage(batch_service=batch, write_service=writes)
    assert not page._write_operation_btn.isEnabled()
    job = DynamicJob("patient", str(tmp_path / "session.xml"), "Dynamic 1.c3d", state="COMPLETED", manifest="fixture")
    batch.jobs = [job]
    page._refresh_batch()
    assert page._write_operation_btn.isEnabled()
    page.clear_session()
    assert batch.jobs == [job]
    batch._running = True
    page._refresh_batch()
    assert not page._write_operation_btn.isEnabled()
    assert not page._parallel_files.isEnabled()
    batch._running = False
    job.state = "FAILED"
    page._refresh_batch()
    assert not page._write_operation_btn.isEnabled()
    page.deleteLater()


def test_guarded_bridge_wrong_target_and_readback(tmp_path):
    target = str(tmp_path / "Dynamic 1.qtm")
    samples = {}
    markers = {}
    trajectory = SimpleNamespace(find_trajectory=lambda name: markers.get(name))
    qtm = SimpleNamespace(file=SimpleNamespace(get_path=lambda: target),
        data=SimpleNamespace(object=SimpleNamespace(trajectory=trajectory),
                             series=SimpleNamespace(_3d=SimpleNamespace(get_sample=lambda marker, i: samples.get(i)))))
    timeline = SimpleNamespace(get_measured_range=lambda: {"start": 10, "end": 11}, get_frequency=lambda: 100.)
    def create(name):
        markers[name] = 1
        return 1
    def write(name, x, y, z, mask, offset, target_range):
        samples.update({offset+i: {"position": [a, b, c]} if mask[i] else None for i, (a, b, c) in enumerate(zip(x,y,z))})
    args = {"measurement_path": str(tmp_path / "other.qtm"), "markers": ["LHJC"]}
    with pytest.raises(ValueError, match="Incorrect"):
        guarded_trajectory_command(qtm, timeline, create, write, "GetTrajectoryWriteContext", args)
    assert not markers
    args.update(measurement_path=target, frequency=100., measured_range={"start": 10, "end": 11},
                overwrite_confirmed=True, operation_id="run:1",
                operation={"kind": "trajectory", "marker": "LHJC", "offset": 10},
                trajectory={"X": [1.,2.], "Y": [3.,4.], "Z": [5.,6.], "exists": [True,False]})
    result = guarded_trajectory_command(qtm, timeline, create, write, "ApplyTrajectoryOperation", args)
    assert result["verified"] and samples[11] is None
    samples.clear()
    with pytest.raises(RuntimeError, match="read-back"):
        guarded_trajectory_command(qtm, timeline, create, lambda *_: None, "ApplyTrajectoryOperation", args)


@pytest.mark.parametrize("limit", [3, 6])
def test_same_patient_files_use_selected_limit_above_four(app, process_setup, limit, monkeypatch):
    import app.services.dynamic_batch_service as module
    monkeypatch.setattr(module, "parallel_file_limit", lambda: 12)
    service, jobs = process_setup
    if limit == 3:
        jobs = [j for j in jobs if j.patient_id == "2"]
    else:
        jobs = jobs[:6]
        # Different sessions can belong to one patient; scheduling is explicitly per file.
        for job in jobs:
            job.patient_id = "same-patient"
    active = []
    service.changed.connect(lambda: active.append(len(service._active)))
    service.start(jobs, limit)
    wait_until(app, lambda: not service.is_running)
    assert all(j.state == "COMPLETED" for j in jobs), [j.error for j in jobs]
    assert max(active) == limit
    assert all(j.patient_id == jobs[0].patient_id for j in jobs)


def test_concurrency_ceiling_comes_from_cpu_and_configuration(monkeypatch):
    from app.services.dynamic_batch_service import parallel_file_limit
    monkeypatch.setattr(os, "cpu_count", lambda: 12)
    monkeypatch.delenv("SHRINERS_MAX_PARALLEL_DYNAMIC_FILES", raising=False)
    assert parallel_file_limit() == 12
    monkeypatch.setenv("SHRINERS_MAX_PARALLEL_DYNAMIC_FILES", "7")
    assert parallel_file_limit() == 7
    monkeypatch.setenv("SHRINERS_MAX_PARALLEL_DYNAMIC_FILES", "90")
    assert parallel_file_limit() == 12


def test_preexisting_manifest_remains_available_without_reprocessing(tmp_path):
    path = artifact(tmp_path / "session")
    meta = json.loads(path.read_text())
    meta.pop("calibration_path")
    meta.pop("input_fingerprint_version")
    atomic_json(path, meta)
    loaded, _ = load_manifest(path)
    assert loaded["trial_id"] == meta["trial_id"]


def test_new_sidecar_invalidates_artifact_but_other_trial_does_not(tmp_path):
    path = artifact(tmp_path / "session")
    folder = tmp_path / "session/Events"
    folder.mkdir()
    (folder / "auto_event_Dynamic 10_results.json").write_text("{}")
    load_manifest(path)
    (folder / "auto_event_Dynamic 1_results.json").write_text("{}")
    with pytest.raises(ValueError, match="input changed"):
        load_manifest(path)
