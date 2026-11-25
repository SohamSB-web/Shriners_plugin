"""Session-local transactional event revisions and explicitly authorized QTM jobs."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3


class EventRevisionConflict(RuntimeError):
    pass


def paths_match(path_a, path_b) -> bool:
    """Robust path equality check across Windows, OneDrive, 8.3 short paths, and symlinks."""
    if not path_a or not path_b:
        return False
    s_a = os.path.normcase(os.path.normpath(str(path_a)))
    s_b = os.path.normcase(os.path.normpath(str(path_b)))
    if s_a == s_b:
        return True
    try:
        if os.path.samefile(path_a, path_b):
            return True
    except (OSError, ValueError):
        pass
    try:
        pa = Path(path_a)
        pb = Path(path_b)
        if pa.stem.strip().lower() == pb.stem.strip().lower():
            if pa.parent == pb.parent:
                return True
            try:
                if os.path.samefile(pa.parent, pb.parent):
                    return True
            except (OSError, ValueError):
                pass
    except (OSError, ValueError):
        pass
    return False


def measurement_path(session, trial):
    session = Path(session).resolve()
    if session.name.lower() == "events":
        session = session.parent
    if session.is_file():
        session = session.parent
    path = Path(trial)
    if path.name != str(path):
        resolved_parent = path.resolve().parent
        if resolved_parent != session:
            try:
                if not os.path.samefile(resolved_parent, session):
                    raise ValueError("Event trial is outside the selected session")
            except (OSError, ValueError):
                raise ValueError("Event trial is outside the selected session")
    if path.name in ("", ".", "..") or path.suffix.lower() not in (".qtm", ".c3d"):
        raise ValueError("An exact QTM/C3D measurement filename is required")
    target = (session / (path.stem + ".qtm")).resolve()
    return os.path.normcase(str(target))


class EventStore:
    def __init__(self, session):
        self.session = Path(session).resolve()
        if self.session.name.lower() == "events":
            self.session = self.session.parent
        if self.session.is_file():
            self.session = self.session.parent
        self.path = self.session / "Events" / "events.sqlite3"

    @contextmanager
    def transaction(self):
        if not (self.session / "Events").resolve().is_relative_to(self.session):
            raise ValueError("Event storage escapes the selected session")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise ValueError("Event database must not be a symlink")
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS trials (
                    id TEXT PRIMARY KEY, session_path TEXT NOT NULL, measurement_path TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 0, remote_signature TEXT,
                    sync_status TEXT NOT NULL DEFAULT 'Events Saved', sync_error TEXT NOT NULL DEFAULT '',
                    remote_events TEXT, projection_error TEXT NOT NULL DEFAULT '');
                CREATE TABLE IF NOT EXISTS event_revisions (
                    trial_id TEXT REFERENCES trials(id), revision INTEGER, payload TEXT NOT NULL,
                    provenance TEXT NOT NULL, intentional_deletion INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(trial_id, revision));
                CREATE TABLE IF NOT EXISTS trial_events (
                    trial_id TEXT REFERENCES trials(id), ordinal INTEGER, payload TEXT NOT NULL,
                    PRIMARY KEY(trial_id, ordinal));
                CREATE TABLE IF NOT EXISTS event_sync_outbox (
                    trial_id TEXT REFERENCES trials(id), revision INTEGER, state TEXT NOT NULL,
                    expected_remote TEXT, diagnostic TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(trial_id, revision),
                    FOREIGN KEY(trial_id, revision) REFERENCES event_revisions(trial_id, revision));
                CREATE TABLE IF NOT EXISTS event_audit_log (
                    id INTEGER PRIMARY KEY, trial_id TEXT REFERENCES trials(id), revision INTEGER,
                    action TEXT NOT NULL, detail TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            """)
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def key(self, trial):
        return measurement_path(self.session, trial)

    def read(self, trial, db=None):
        if db is None:
            if not self.path.is_file():
                return None
            if self.path.is_symlink() or not self.path.parent.resolve().is_relative_to(self.session):
                raise ValueError("Event storage is outside this session")
            db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=10)
            db.row_factory = sqlite3.Row
            try:
                db.execute("BEGIN")
                return self.read(trial, db)
            finally:
                db.close()
        key = self.key(trial)
        row = db.execute("SELECT * FROM trials WHERE id=?", (key,)).fetchone()
        if row is None or row["revision"] == 0:
            return None
        revision = db.execute("SELECT * FROM event_revisions WHERE trial_id=? AND revision=?",
                              (key, row["revision"])).fetchone()
        result = dict(row)
        result.update(payload=json.loads(revision["payload"]), provenance=revision["provenance"],
                      intentional_deletion=bool(revision["intentional_deletion"]))
        job = db.execute("SELECT * FROM event_sync_outbox WHERE trial_id=? AND revision=?",
                         (key, row["revision"])).fetchone()
        result["job"] = dict(job) if job else None
        return result

    def commit(self, trial, data, provenance, *, enqueue=True, expected_revision=None, deleted=False):
        key = self.key(trial)
        with self.transaction() as db:
            db.execute("INSERT OR IGNORE INTO trials(id,session_path,measurement_path) VALUES(?,?,?)",
                       (key, str(self.session), key))
            row = db.execute("SELECT * FROM trials WHERE id=?", (key,)).fetchone()
            if expected_revision is not None and row["revision"] != expected_revision:
                raise EventRevisionConflict("Events changed since this editor was opened; review the latest revision")
            revision = row["revision"] + 1
            status = "Pending QTM Sync" if enqueue else "Events Saved"
            data = json.loads(json.dumps(data, allow_nan=False))
            for event in data["events"]:
                frame = event["frame"]
                if not event.get("label") or int(frame) != float(frame) or int(frame) < 1:
                    raise ValueError("Events require a label and a whole absolute QTM timeline frame")
            data["meta"].update(event_revision=revision, intentional_deletion=deleted, provenance=provenance)
            db.execute("INSERT INTO event_revisions VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)",
                       (key, revision, json.dumps(data, allow_nan=False), provenance, int(deleted)))
            db.execute("DELETE FROM trial_events WHERE trial_id=?", (key,))
            db.executemany("INSERT INTO trial_events VALUES(?,?,?)",
                           [(key, i, json.dumps(event, allow_nan=False)) for i, event in enumerate(data["events"])])
            db.execute("UPDATE event_sync_outbox SET state='superseded' WHERE trial_id=?", (key,))
            if enqueue:
                db.execute("INSERT INTO event_sync_outbox(trial_id,revision,state,expected_remote) VALUES(?,?,'pending',?)",
                           (key, revision, row["remote_signature"]))
            db.execute("UPDATE trials SET revision=?,sync_status=?,sync_error='',remote_events=NULL,projection_error='' WHERE id=?",
                       (revision, status, key))
            db.execute("INSERT INTO event_audit_log(trial_id,revision,action,detail) VALUES(?,?,?,?)",
                       (key, revision, provenance, json.dumps({"event_count": len(data["events"]), "intentional_deletion": deleted})))
            return self.read(trial, db)

    def status(self, db, record, status, error="", remote=None):
        remote_json = json.dumps(remote) if remote is not None else None
        if record["sync_status"] == status and record["sync_error"] == error and record["remote_events"] == remote_json:
            return
        if record["sync_status"] != status or record["sync_error"] != error:
            db.execute("INSERT INTO event_audit_log(trial_id,revision,action,detail) VALUES(?,?,?,?)",
                       (record["id"], record["revision"], status, error))
        db.execute("UPDATE trials SET sync_status=?,sync_error=?,remote_events=? WHERE id=? AND revision=?",
                   (status, error, remote_json, record["id"], record["revision"]))

    def retry(self, trial, revision, expected_remote=None):
        with self.transaction() as db:
            record = self.read(trial, db)
            if record is None or record["revision"] != revision:
                raise EventRevisionConflict("The saved event revision changed; review again")
            expected = json.dumps(expected_remote) if expected_remote is not None else record["remote_signature"]
            db.execute("INSERT INTO event_sync_outbox(trial_id,revision,state,expected_remote) VALUES(?,?,'pending',?) "
                       "ON CONFLICT(trial_id,revision) DO UPDATE SET state='pending',expected_remote=excluded.expected_remote,diagnostic=''",
                       (record["id"], revision, expected))
            self.status(db, record, "Pending QTM Sync")
