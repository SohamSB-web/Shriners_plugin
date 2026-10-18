"""Exact-measurement event observation and one-shot outbox delivery."""
import json
import os
from pathlib import Path
import sys

from app.services.event_store import EventStore, EventRevisionConflict, measurement_path
from app.services.qtm_event_protocol import event_signature


def event_rpc(command, args=None, port=50052):
    from app.services.settings_service import SettingsService
    directory = SettingsService().load_app_settings().qtm_grpc_location
    if directory not in sys.path:
        sys.path.insert(0, directory)
    import grpc
    import qtm_data_transfer_pb2 as pb
    import qtm_data_transfer_pb2_grpc as rpc
    with grpc.insecure_channel(f"localhost:{port}") as channel:
        response = rpc.QtmTkinterBridgeStub(channel).SendCommandToQtm(
            pb.CommandToQtm(command_name=command, command_args_json=json.dumps(args or {})), timeout=3)
    if not response.success:
        raise RuntimeError(response.message)
    snapshot = json.loads(response.message)
    path = snapshot.get("measurement_path")
    if not path or not Path(path).is_absolute() or "events" not in snapshot:
        raise RuntimeError("QTM bridge lacks verified measurement identity; restart the updated QTM bridge")
    snapshot["measurement_path"] = os.path.normcase(str(Path(path).resolve()))
    return snapshot


def synchronize_pending(session, trial, remote, port=50052):
    """Hold a revision write lock through CAS/read-back; crash rollback leaves the job pending."""
    store = EventStore(session)
    if remote["measurement_path"] != measurement_path(session, trial):
        return
    with store.transaction() as db:
        record = store.read(trial, db)
        if record is None:
            return
        job = record["job"]
        if not job or job["state"] != "pending":
            return
        local = record["payload"]["events"]
        current = event_signature(remote["events"])
        desired = event_signature(local)
        expected = json.loads(job["expected_remote"]) if job["expected_remote"] is not None else None
        if current != desired and (current != expected if expected is not None else bool(current)):
            db.execute("UPDATE event_sync_outbox SET state='conflict',diagnostic=? WHERE trial_id=? AND revision=?",
                       ("QTM timeline differs from the expected previous state", record["id"], record["revision"]))
            store.status(db, record, "QTM Conflict", "Review local and QTM events before choosing a version", remote["events"])
            return
        try:
            if current != desired:
                verified = event_rpc("ApplyEventRevision", {"measurement_path": record["measurement_path"],
                    "revision": record["revision"], "expected_events": current, "events": local}, port)
            else:
                verified = remote  # Crash recovery/idempotence: already applied, no duplicate insertion.
            if (verified["measurement_path"] != record["measurement_path"]
                    or event_signature(verified["events"]) != desired):
                raise RuntimeError("QTM read-back did not match the authoritative event revision")
            status = "QTM Synced" if verified.get("persistent") else "Save in QTM Required"
            db.execute("UPDATE event_sync_outbox SET state=?,diagnostic='' WHERE trial_id=? AND revision=?",
                       ("synced" if verified.get("persistent") else "timeline", record["id"], record["revision"]))
            db.execute("UPDATE trials SET remote_signature=? WHERE id=?", (json.dumps(desired), record["id"]))
            store.status(db, record, status)
        except Exception as error:
            db.execute("UPDATE event_sync_outbox SET state='failed',diagnostic=? WHERE trial_id=? AND revision=?",
                       (str(error), record["id"], record["revision"]))
            store.status(db, record, "Pending QTM Sync", str(error))


def observe_session_events(session, trials, port=50052, force=False, progress=None):
    from app.services.event_service import load_trial_events
    try:
        remote = event_rpc("GetEventSnapshot", port=port)
    except Exception as error:
        _pending_notice(session, trials, str(error))
        return False, str(error), None, [], None
    matches = [trial for trial in trials if measurement_path(session, trial) == remote["measurement_path"]]
    if len(matches) != 1:
        _pending_notice(session, trials, "Open the exact saved measurement in QTM; session/path identity differs")
        return False, "QTM measurement does not uniquely match this session", None, [], None
    trial = matches[0]
    info = load_trial_events(session, trial)
    if info is None:
        return False, "QTM events available; explicitly Pull from QTM to import them", trial, remote["events"], None
    store = EventStore(session)
    before = store.read(trial)
    if before["job"] and before["job"]["state"] == "pending" and not force:
        if progress:
            progress(trial)
        synchronize_pending(session, trial, remote, port)
    else:
        with store.transaction() as db:
            record = store.read(trial, db)
            current = event_signature(remote["events"])
            desired = event_signature(record["payload"]["events"])
            failed = record["job"] and record["job"]["state"] == "failed"
            expected = json.loads(record["job"]["expected_remote"]) if failed and record["job"]["expected_remote"] else []
            if failed and current == expected:
                pass  # Keep the failed job and its diagnostic, without an automatic retry.
            elif failed and current == desired:
                db.execute("UPDATE event_sync_outbox SET state='timeline' WHERE trial_id=? AND revision=?",
                           (record["id"], record["revision"]))
                db.execute("UPDATE trials SET remote_signature=? WHERE id=?", (json.dumps(desired), record["id"]))
                store.status(db, record, "Save in QTM Required")
            elif current != desired:
                store.status(db, record, "QTM Conflict", "QTM differs from saved events; review both versions", remote["events"])
            else:
                signature = json.dumps(current)
                if record["remote_signature"] != signature:
                    db.execute("UPDATE trials SET remote_signature=? WHERE id=?", (signature, record["id"]))
    info = load_trial_events(session, trial)
    return True, info["meta"]["event_sync_status"], trial, remote["events"], info


def _pending_notice(session, trials, message):
    store = EventStore(session)
    if not store.path.is_file():
        return
    with store.transaction() as db:
        for trial in trials:
            record = store.read(trial, db)
            if record and record["job"] and record["job"]["state"] == "pending":
                store.status(db, record, "Pending QTM Sync", message)


def push_saved_events(session, trial, port=50052):
    from app.services.event_service import load_trial_events
    info = load_trial_events(session, trial)
    if info is None:
        return False, "No committed events exist for this trial"
    store = EventStore(session)
    record = store.read(trial)
    if info["meta"].get("event_sync_status") == "QTM Conflict":
        return False, "QTM Event Conflict — review the differences before choosing a version"
    store.retry(trial, record["revision"])
    _, message, matched, _, updated = observe_session_events(session, [trial], port)
    ok = bool(updated and updated["meta"]["event_sync_status"] in {"QTM Synced", "Save in QTM Required"})
    return ok, message if matched else "Pending QTM Sync: " + message


def resolve_event_conflict(session, trial, choice, revision, remote, port=50052):
    from app.services.event_service import save_trial_events, load_trial_events
    if remote["measurement_path"] != measurement_path(session, trial):
        raise ValueError("QTM measurement differs from the selected trial")
    store = EventStore(session)
    if choice == "local":
        old = store.read(trial)
        if old and old["payload"]["meta"].get("migration_conflicts"):
            meta = dict(old["payload"]["meta"])
            meta.pop("migration_conflicts")
            info = save_trial_events(session, trial, old["payload"]["events"], meta,
                                     provenance="manual_reconcile", expected_revision=revision)
            revision = info["meta"]["event_revision"]
        store.retry(trial, revision, event_signature(remote["events"]))
        synchronize_pending(session, trial, remote, port)
    elif choice == "qtm":
        current = event_rpc("GetEventSnapshot", port=port)
        if (current["measurement_path"] != remote["measurement_path"]
                or event_signature(current["events"]) != event_signature(remote["events"])):
            raise EventRevisionConflict("QTM changed during conflict review; review again")
        old = store.read(trial)
        meta = dict(old["payload"]["meta"]) if old else {}
        meta.pop("migration_conflicts", None)
        meta.update({name: remote[name] for name in ("frame_rate", "recording_start_frame", "initial_frame_offset",
                                                   "frame_convention", "total_frames") if name in remote})
        info = save_trial_events(session, trial, remote["events"], meta, provenance="qtm_accepted",
                                 expected_revision=revision, enqueue=False)
        with store.transaction() as db:
            record = store.read(trial, db)
            db.execute("UPDATE trials SET remote_signature=? WHERE id=?", (json.dumps(event_signature(remote["events"])), record["id"]))
            store.status(db, record, "Save in QTM Required")
    else:
        raise ValueError("Choose the local or QTM version explicitly")
    return load_trial_events(session, trial)


# Only the UI uses the worker; detection and SQLite persistence stay usable headlessly.
def start_event_observation(session, trials, callback, progress=None):
    from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

    class Signals(QObject):
        finished = Signal(object)
        progress = Signal(str)

    class Worker(QRunnable):
        def __init__(self):
            super().__init__()
            self.signals = Signals()

        def run(self):
            try:
                result = observe_session_events(session, trials, progress=self.signals.progress.emit)
            except Exception as error:
                result = (False, str(error), None, [], None)
            try:
                self.signals.finished.emit(result)
            except RuntimeError:
                pass

    worker = Worker()
    worker.signals.finished.connect(callback)
    if progress:
        worker.signals.progress.connect(progress)
    QThreadPool.globalInstance().start(worker)
    return worker
