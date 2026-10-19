"""Disposable sessions and mocked QTM only; no live clinical recordings are opened."""
import copy
import json
import os
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from app.services import event_service as svc
from app.services import event_sync_service as sync
from app.services.event_store import EventStore, EventRevisionConflict, measurement_path
from app.services.frame_coordinates import frame_to_time, FRAME_CONVENTION
from app.services.qtm_event_protocol import guarded_event_command, event_signature


def events(frame=431):
    return [{"frame": frame, "label": "RSTRIKE", "side": "R", "type": "STRIKE", "custom": {"keep": True}},
            {"frame": frame + 37, "label": "ROFF", "side": "R", "type": "OFF"}]


@pytest.fixture
def remote(tmp_path, monkeypatch):
    session = tmp_path / "PatientA" / "Session"
    session.mkdir(parents=True)
    for name in ("Dynamic 1.qtm", "Dynamic 5.qtm", "Dynamic 10.qtm", "Dynamic 20.qtm"):
        (session / name).write_bytes(b"untouched native recording")
    timelines = {measurement_path(session, name): [] for name in ("Dynamic 5.qtm", "Dynamic 20.qtm")}
    state = SimpleNamespace(session=session, timelines=timelines, active=measurement_path(session, "Dynamic 20.qtm"),
                            calls=[], inserts=0, fail=False, persist=False, crash=False)

    class EventAPI:
        def get_events(self):
            return copy.deepcopy(state.timelines[state.active])

        def add_event(self, event):
            state.inserts += 1
            state.timelines[state.active].append({**event, "id": state.inserts + 1000})

        def delete_event(self, ident):
            state.timelines[state.active] = [e for e in state.timelines[state.active] if e["id"] != ident]

    qtm = SimpleNamespace(file=SimpleNamespace(get_path=lambda: state.active))
    timeline = SimpleNamespace(get_frequency=lambda: 120.0, get_measured_range=lambda: {"start": 300, "end": 999},
                               get_frame_count=lambda: 700)

    def rpc(command, args=None, port=50052):
        state.calls.append(command)
        if state.fail and command == "ApplyEventRevision":
            raise OSError("simulated QTM disconnect")
        result = guarded_event_command(qtm, EventAPI(), timeline, command, args or {})
        result["persistent"] = state.persist
        if state.crash and command == "ApplyEventRevision":
            raise KeyboardInterrupt("crash after QTM application, before SQLite commit")
        return result

    state.rpc = rpc
    monkeypatch.setattr(sync, "event_rpc", rpc)
    return state


def detect(state, frame=431):
    return svc.save_trial_events(state.session, "Dynamic 5.qtm", events(frame),
                                 {"frame_rate": 120, "recording_start_frame": 301, "frame_convention": FRAME_CONVENTION},
                                 provenance="auto_label")


def test_detection_on_5_while_20_open_then_restore_once(remote):
    twenty = remote.active
    remote.timelines[twenty] = [{"id": 8, "label": "LOFF", "time": 2.0}]
    original = copy.deepcopy(remote.timelines[twenty])
    detector_calls = 0
    detector_calls += 1
    info = detect(remote)
    assert info["total_events"] == 2 and info["meta"]["event_sync_status"] == "Pending QTM Sync"
    for _ in range(3):
        sync.observe_session_events(remote.session, ["Dynamic 5.qtm", "Dynamic 20.qtm"])
    assert remote.timelines[twenty] == original and remote.inserts == 0
    remote.active = measurement_path(remote.session, "Dynamic 5.qtm")
    for _ in range(5):
        sync.observe_session_events(remote.session, ["Dynamic 5.qtm", "Dynamic 20.qtm"])
    saved = svc.load_trial_events(remote.session, "Dynamic 5.qtm")
    assert saved["meta"]["event_sync_status"] == "Save in QTM Required"
    assert remote.calls.count("ApplyEventRevision") == 1 and remote.inserts == 2
    assert detector_calls == 1 and remote.timelines[twenty] == original
    assert saved["events"][0]["frame"] == 431 and saved["events"][0]["relative_frame"] == 130
    assert saved["events"][0]["custom"] == {"keep": True}
    assert saved["events"][0]["time"] == frame_to_time(431, 120)
    assert all(p.read_bytes() == b"untouched native recording" for p in remote.session.glob("*.qtm"))


def test_empty_read_never_erases_committed_events_or_projections(remote):
    detect(remote)
    remote.active = measurement_path(remote.session, "Dynamic 5.qtm")
    sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    before = (remote.session / "Events/auto_event_Dynamic 5_results.json").read_bytes()
    remote.timelines[remote.active] = []
    for _ in range(4):
        sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    info = svc.load_trial_events(remote.session, "Dynamic 5.qtm")
    assert info["total_events"] == 2
    assert (remote.session / "Events/auto_event_Dynamic 5_results.json").read_bytes() == before
    assert remote.calls.count("ApplyEventRevision") == 1


def test_explicit_deletion_then_new_detection_restores_latest_revision(remote):
    info = detect(remote)
    remote.active = measurement_path(remote.session, "Dynamic 5.qtm")
    sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    deleted = svc.save_trial_events(remote.session, "Dynamic 5.qtm", [], info["meta"], expected_revision=1)
    assert deleted["meta"]["intentional_deletion"] and deleted["meta"]["event_revision"] == 2
    sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    assert remote.timelines[remote.active] == []
    remote.active = measurement_path(remote.session, "Dynamic 20.qtm")
    info = detect(remote, 500)
    assert info["meta"]["event_revision"] == 3
    sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    remote.active = measurement_path(remote.session, "Dynamic 5.qtm")
    sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    assert svc.load_trial_events(remote.session, "Dynamic 5.qtm")["events"][0]["frame"] == 500
    assert len(remote.timelines[remote.active]) == 2


@pytest.mark.parametrize("choice", ["local", "qtm"])
def test_conflicting_edits_require_explicit_choice(remote, choice):
    detect(remote)
    remote.active = measurement_path(remote.session, "Dynamic 5.qtm")
    remote.timelines[remote.active] = [{"id": 4, "label": "LSTRIKE", "time": 4.0}]
    sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    assert remote.inserts == 0
    record = EventStore(remote.session).read("Dynamic 5.qtm")
    assert record["job"]["state"] == "conflict"
    snapshot = remote.rpc("GetEventSnapshot")
    result = sync.resolve_event_conflict(remote.session, "Dynamic 5.qtm", choice, record["revision"], snapshot)
    assert result["total_events"] == (2 if choice == "local" else 1)
    assert result["meta"]["event_sync_status"] == "Save in QTM Required"


def test_accept_native_empty_deletion_creates_explicit_revision(remote):
    detect(remote)
    remote.active = measurement_path(remote.session, "Dynamic 5.qtm")
    snapshot = remote.rpc("GetEventSnapshot")
    info = sync.resolve_event_conflict(remote.session, "Dynamic 5.qtm", "qtm", 1, snapshot)
    assert info["total_events"] == 0 and info["meta"]["intentional_deletion"]
    assert info["meta"]["event_revision"] == 2


def test_cross_patient_and_prefix_names_cannot_receive_events(remote, tmp_path):
    detect(remote)
    for name in ("Dynamic 1.qtm", "Dynamic 10.qtm", "Dynamic 2.qtm", "Dynamic 20.qtm"):
        remote.active = measurement_path(remote.session, name)
        remote.timelines.setdefault(remote.active, [])
        sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    other = tmp_path / "PatientB" / "Session"
    other.mkdir(parents=True)
    remote.active = measurement_path(other, "Dynamic 5.qtm")
    remote.timelines[remote.active] = []
    sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    assert remote.inserts == 0
    with pytest.raises(RuntimeError, match="mismatch"):
        remote.rpc("ApplyEventRevision", {"measurement_path": measurement_path(remote.session, "Dynamic 5.qtm"),
                                          "expected_events": [], "events": events()})


def test_crash_after_apply_recovers_without_duplicate_events(remote):
    detect(remote)
    remote.active = measurement_path(remote.session, "Dynamic 5.qtm")
    remote.crash = True
    with pytest.raises(KeyboardInterrupt):
        sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    assert EventStore(remote.session).read("Dynamic 5.qtm")["job"]["state"] == "pending"
    assert remote.inserts == 2
    remote.crash = False
    sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    assert remote.inserts == 2
    assert EventStore(remote.session).read("Dynamic 5.qtm")["job"]["state"] == "timeline"


def test_failed_sync_has_diagnostics_without_infinite_retries(remote):
    detect(remote)
    remote.active = measurement_path(remote.session, "Dynamic 5.qtm")
    remote.fail = True
    for _ in range(8):
        sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    record = EventStore(remote.session).read("Dynamic 5.qtm")
    assert remote.calls.count("ApplyEventRevision") == 1
    assert record["job"]["state"] == "failed" and "disconnect" in record["job"]["diagnostic"]
    assert len(record["payload"]["events"]) == 2


def test_acid_rollback_revision_cas_and_concurrent_edits(remote):
    detect(remote)
    store = EventStore(remote.session)
    with store.transaction() as db:
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        db.execute("CREATE TRIGGER abort_audit BEFORE INSERT ON event_audit_log BEGIN SELECT RAISE(ABORT,'test failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        svc.save_trial_events(remote.session, "Dynamic 5.qtm", events(510), expected_revision=1)
    assert store.read("Dynamic 5.qtm")["revision"] == 1
    with store.transaction() as db:
        db.execute("DROP TRIGGER abort_audit")

    def edit(frame):
        try:
            svc.save_trial_events(remote.session, "Dynamic 5.qtm", events(frame), expected_revision=1)
            return "committed"
        except EventRevisionConflict:
            return "stale"

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(edit, [500, 600])) == ["committed", "stale"]
    assert store.read("Dynamic 5.qtm")["revision"] == 2
    with store.transaction() as db:
        assert db.execute("SELECT COUNT(*) FROM event_revisions").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM trial_events").fetchone()[0] == 2


def test_projection_failure_recovers_from_committed_revision(remote, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(svc.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
        info = detect(remote)
    assert info["total_events"] == 2 and "disk full" in info["meta"]["projection_error"]
    assert svc.project_trial_events(remote.session, "Dynamic 5.qtm", 1)
    projected = json.loads((remote.session / "Events/auto_event_Dynamic 5_results.json").read_text())
    assert projected["meta"]["event_revision"] == 1
    assert not svc.load_trial_events(remote.session, "Dynamic 5.qtm")["meta"]["projection_error"]


def test_migration_preserves_contradictory_original_jsons(remote):
    folder = remote.session
    (folder / "Events").mkdir()
    root = folder / "auto_event_Dynamic 5_results.json"
    canonical = folder / "Events/auto_event_Dynamic 5_results.json"
    root.write_text(json.dumps({"events": events(500), "meta": {"manual_override": True}}))
    canonical.write_text(json.dumps({"events": events(), "meta": {"manual_override": True}}))
    before = [p.read_bytes() for p in (root, canonical)]
    info = svc.load_trial_events(folder, "Dynamic 5.qtm")
    assert info["meta"]["migration_conflicts"] and info["meta"]["event_sync_status"] == "QTM Conflict"
    assert before == [p.read_bytes() for p in (root, canonical)]
    assert EventStore(folder).read("Dynamic 5.qtm")["job"] is None


def test_bridge_preserves_non_gait_events_and_rechecks_remote_state(remote):
    detect(remote)
    remote.active = measurement_path(remote.session, "Dynamic 5.qtm")
    remote.timelines[remote.active] = [{"id": 30, "label": "Operator Note", "time": 2.0}]
    sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    assert any(e["label"] == "Operator Note" for e in remote.timelines[remote.active])
    with pytest.raises(RuntimeError, match="Conflict"):
        remote.rpc("ApplyEventRevision", {"measurement_path": remote.active, "expected_events": [], "events": events()})


def test_persistent_status_requires_explicit_verification(remote):
    detect(remote)
    remote.active = measurement_path(remote.session, "Dynamic 5.qtm")
    remote.persist = True  # Mocked capability only; production bridge reports False.
    sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    assert svc.load_trial_events(remote.session, "Dynamic 5.qtm")["meta"]["event_sync_status"] == "QTM Synced"


def test_qt_rows_restore_without_a_second_autolabel_and_keep_zero_revision(remote, monkeypatch):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from app.ui.pages.dynamic_analysis_page import DynamicAnalysisPage
    from app.models.data_models import ProcessingStatus
    app = QApplication.instance() or QApplication([])
    xml = remote.session / "session.xml"
    xml.write_text("<Session/>")
    monkeypatch.setattr(DynamicAnalysisPage, "_schedule", lambda *args: None)
    monkeypatch.setattr("app.ui.pages.dynamic_analysis_page.get_session_dynamic_trials",
                        lambda _: [{"filename": n, "stem": Path(n).stem} for n in ("Dynamic 5.qtm", "Dynamic 20.qtm")])
    page = DynamicAnalysisPage()
    page.load_session(str(xml))
    from PySide6.QtCore import QThreadPool
    QThreadPool.globalInstance().waitForDone(2000)
    app.processEvents()
    page._qtm_sync_timer.stop()
    calls = []

    def detector(*args, **kwargs):
        calls.append(args[1])
        detect(remote)
        page._on_trial_finished(ProcessingStatus(step="complete", completed=True))
        page._process_next_in_queue()

    monkeypatch.setattr(page._service, "run_auto_event_labeling", detector)
    try:
        page._on_single_trial_auto_label("Dynamic 5.qtm")
        row = page._trial_rows["Dynamic 5.qtm"]
        assert "2 Events" in row._events_btn.text()
        remote.active = measurement_path(remote.session, "Dynamic 5.qtm")
        page._poll_qtm_events_sync()
        for _ in range(500):
            app.processEvents()
            if not page._is_syncing_events:
                break
            QTest.qWait(5)
        assert not page._is_syncing_events
        assert "2 Events" in row._events_btn.text()
        assert calls == ["Dynamic 5.qtm"] and remote.inserts == 2
        info = svc.save_trial_events(remote.session, "Dynamic 5.qtm", [], row._events_info["meta"])
        row.set_events_info(info)
        generation = page._analysis_generation
        page.clear_session()
        page._on_event_sync_observed(generation, (True, "old", "Dynamic 5.qtm", events(), info))
        assert page._trial_rows == {} and page._session_path == ""
    finally:
        page.clear_session()
        page.deleteLater()
        app.processEvents()


def test_native_empty_review_and_gui_remove_all_commit_revision(remote, monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    from app.ui.dialogs.event_details_dialog import EventDetailsDialog
    app = QApplication.instance() or QApplication([])
    info = detect(remote)
    dialog = EventDetailsDialog(trial_filename="Dynamic 5.qtm", events_info=info, frame_rate=120,
                               session_dir=remote.session)
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Yes)
    try:
        dialog._on_remove_all_events()
        saved = svc.load_trial_events(remote.session, "Dynamic 5.qtm")
        assert saved["total_events"] == 0 and saved["meta"]["intentional_deletion"]
        assert saved["meta"]["event_revision"] == 2 and remote.inserts == 0
        assert "Events Saved" in dialog._sync_badge.text()
    finally:
        dialog.deleteLater()
        app.processEvents()


def test_c3d_projection_round_trip_and_migration_leave_points_unchanged(remote):
    ezc3d = pytest.importorskip("ezc3d")
    import numpy as np
    path = remote.session / "Dynamic 5.c3d"
    source = ezc3d.c3d()
    source.add_parameter("POINT", "RATE", [120.])
    source.add_parameter("POINT", "LABELS", ["TEST"])
    source["data"]["points"] = np.ones((4, 1, 700))
    source.write(str(path))
    before = ezc3d.c3d(str(path))["data"]["points"].copy()
    info = detect(remote)
    assert not info["meta"]["projection_error"]
    np.testing.assert_array_equal(ezc3d.c3d(str(path))["data"]["points"], before)
    read = svc._read_c3d_event_projection(path)
    assert event_signature(read["events"]) == event_signature(events())


def test_detection_empty_and_stale_edits_cannot_replace_committed_events(remote):
    info = detect(remote)
    with pytest.raises(ValueError, match="previous saved revision"):
        svc.save_trial_events(remote.session, "Dynamic 5.qtm", [], provenance="auto_label")
    with pytest.raises(EventRevisionConflict):
        svc.save_trial_events(remote.session, "Dynamic 5.qtm", events(600), info["meta"], expected_revision=0)
    assert EventStore(remote.session).read("Dynamic 5.qtm")["revision"] == 1


def test_auto_fetch_live_qtm_changes_when_events_exist(remote):
    detect(remote)
    remote.active = measurement_path(remote.session, "Dynamic 5.qtm")
    sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    # Doctor edits events in QTM to 3 events
    remote.timelines[remote.active] = [
        {"id": 1, "label": "RSTRIKE", "time": 2.0},
        {"id": 2, "label": "ROFF", "time": 2.5},
        {"id": 3, "label": "LSTRIKE", "time": 3.0},
    ]
    # Background poll observes QTM
    updated, message, trial, evts, info = sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    assert updated is True
    # The app must have auto-fetched the 3 events from QTM!
    saved = svc.load_trial_events(remote.session, "Dynamic 5.qtm")
    assert saved["total_events"] == 3
    assert len(saved["events"]) == 3
    assert saved["meta"]["provenance"] == "qtm_auto_sync"


def test_zero_qtm_events_never_fetches_or_erases(remote):
    detect(remote)
    remote.active = measurement_path(remote.session, "Dynamic 5.qtm")
    sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    # QTM timeline has 0 events
    remote.timelines[remote.active] = []
    # Background poll observes QTM
    sync.observe_session_events(remote.session, ["Dynamic 5.qtm"])
    # App's saved events must be completely preserved!
    saved = svc.load_trial_events(remote.session, "Dynamic 5.qtm")
    assert saved["total_events"] == 2
    assert len(saved["events"]) == 2
