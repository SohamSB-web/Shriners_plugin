"""gRPC stores commands; only a QTM GUI command callback may execute them."""
import hashlib
import json
import threading
import time

DISPATCH_COMMAND = "ShrinersDispatchTrajectory"


class QTMCommandDispatcher:
    def __init__(self, execute):
        self.execute = execute
        self.owner_thread = threading.get_ident()
        self.lock = threading.Lock()
        self.token = None
        self.pending = None
        self.results = {}

    @property
    def busy(self):
        with self.lock:
            return self.token is not None

    def receive(self, command, args):
        """Infrastructure thread entry point. Never calls a native QTM API."""
        token = args.get("token")
        if not isinstance(token, str) or not token:
            raise ValueError("Missing trajectory batch identity")
        with self.lock:
            if command == "BeginTrajectoryBatch":
                if self.token not in (None, token):
                    raise RuntimeError("Another QTM write batch is active; finish it before starting another")
                self.token = token
                return {"protocol": 2, "dispatcher": DISPATCH_COMMAND}
            if token != self.token:
                raise RuntimeError("QTM write batch identity does not match")
            if command == "EndTrajectoryBatch":
                if self.pending:
                    raise RuntimeError("QTM operation still pending; its completion is uncertain")
                self.token = None
                return {"released": True}
            key = (token, args["request_id"])
            if command == "GetTrajectoryCommandStatus":
                return dict(self.results.get(key, {"state": "NOT_FOUND"}))
            if command == "CancelQueuedTrajectoryCommand":
                result = self.results.get(key)
                if result is None or result["state"] != "QUEUED":
                    raise RuntimeError("Cannot cancel an operation which may already have executed")
                result["state"] = "CANCELLED"
                self.pending = None
                return {"state": "CANCELLED"}
            if command != "QueueTrajectoryCommand":
                raise ValueError("Unsupported trajectory dispatcher command")
            name = args["command"]
            if name not in {"SelectTrajectoryTrial", "ApplyTrajectoryOperation", "VerifyTrajectoryOperation",
                            "CompleteTrajectoryTrial"}:
                raise ValueError("Unsupported native trajectory command")
            digest = hashlib.sha256(json.dumps([name, args["args"]], sort_keys=True, allow_nan=False).encode()).hexdigest()
            old = self.results.get(key)
            if old:
                if old["digest"] != digest:
                    raise ValueError("Request identity reused for a different trajectory payload")
                return dict(old)
            if self.pending:
                raise RuntimeError("A native QTM operation is already pending")
            self.results[key] = {"state": "QUEUED", "digest": digest}
            self.pending = (key, name, args["args"])
            return dict(self.results[key])

    def dispatch_one(self):
        """Registered with set_command_execute_function; invoked through QTM's REST send_command."""
        if threading.get_ident() != self.owner_thread:
            raise RuntimeError("QTM trajectory callback is outside its registered scripting thread; no write executed")
        with self.lock:
            if not self.pending:
                return
            key, command, args = self.pending
            if self.results[key]["state"] != "QUEUED":
                return
            self.results[key].update(state="RUNNING", started=time.time())
        try:
            result = self.execute(command, args)
            outcome = {"state": "COMPLETED", "result": result}
        except Exception as exc:
            # A native exception can occur after partial mutation. Read-back is required before resuming.
            outcome = {"state": "UNCERTAIN", "error": str(exc)}
        with self.lock:
            self.results[key].update(outcome, finished=time.time())
            self.pending = None
