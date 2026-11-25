"""Exercise real HTTP transport and Qt controls against a disposable PAF endpoint."""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import struct
import re
import sys
import threading
import time
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from PySide6.QtCore import QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
from app.services.anthropometric_sync_service import (
    ANTHROPOMETRIC_FIELDS, QtmAnthropometricClient, same_parameter_value, validate_parameter,
)
from app.ui.pages.static_analysis_page import StaticAnalysisPage


VALUES = {"BodyMass": 75, "Height": 1.735678, "InterAsisDistance": .2154321,
          "LeftLegLength": .812345, "RightLegLength": .823456,
          "LeftKneeWidth": .084567, "RightKneeWidth": .093456,
          "LeftAnkleWidth": .064567, "RightAnkleWidth": .073456,
          "LeftAsisTrocanterDistance": .123456, "RightAsisTrocanterDistance": .134567}


def f32(value):
    return struct.unpack("f", struct.pack("f", value))[0]


def wait_for(app, predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(.005)
    raise AssertionError("Qt operation did not complete")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def paf(tmp_path):
    class State:
        fail = False
        delay = 0
        active_file = None
        active_error = False
        puts = []
        gets = []
        nodes = {}

        def add_session(self, key, folder):
            folder.mkdir(parents=True, exist_ok=True)
            fields = {name: f32(value) for name, value in VALUES.items()}
            fields.update(Class="Session", Path=str(folder), ID="subject", Name="Test", DOB="2000-01-01", Sex="Female")
            self.nodes[key] = {"ID": key, "Fields": fields, "ChildIDs": [], "ParentIDs": []}
            xml = "<Session><Fields>" + "".join(f"<{n}>{v}</{n}>" for n, v in fields.items() if n in VALUES) + "</Fields></Session>"
            (folder / "session.xml").write_text(xml, encoding="utf8")
            return folder / "session.xml"

    state = State()
    state.project = {"OpenProject": "Test project", "ProjectDirectory": str(tmp_path)}
    state.session = state.add_session("session-a", tmp_path / "subject-a" / "same-date")
    state.other = state.add_session("session-b", tmp_path / "subject-b" / "same-date")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, value, status=200):
            body = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def do_GET(self):
            time.sleep(state.delay)
            if state.fail:
                return self.respond({"error": "unavailable"}, 503)
            parsed = urllib.parse.urlparse(self.path)
            key = urllib.parse.unquote(parsed.path.rsplit("/", 1)[-1])
            state.gets.append(self.path)
            if self.path == "/api/v1/project":
                return self.respond(state.project)
            if key == "instance":
                return self.respond({"ChildIDs": list(state.nodes), "Children": list(state.nodes.values())})
            if key not in state.nodes:
                return self.respond({}, 404)
            node = copy.deepcopy(state.nodes[key])
            if "typeInfo=true" in parsed.query:
                node["Fields"] = {n: {"ReadOnly": False, "TypeName": "Float32"}
                                  for n in node["Fields"]}
            self.respond(node)

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.path == "/api/scripting/qtm/file/get_path/":
                if state.active_error:
                    return self.respond({"error": "method requires a measurement file"}, 400)
                return self.respond(state.active_file)
            self.respond({}, 404)

        def do_PUT(self):
            state.puts.append(self.path)
            content_len = int(self.headers.get("Content-Length", 0))
            if content_len > 0:
                try:
                    payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
                    parsed = urllib.parse.urlparse(self.path)
                    key = urllib.parse.unquote(parsed.path.rsplit("/", 1)[-1])
                    if key in state.nodes:
                        state.nodes[key]["Fields"].update(payload)
                except Exception:
                    pass
            self.respond({"status": "ok"}, 200)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state.url = f"http://127.0.0.1:{server.server_port}/api/v1/paf/instance"
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def page(app, paf, monkeypatch):
    widget = StaticAnalysisPage()
    widget._anthro_sync.client = QtmAnthropometricClient(paf.url)
    widget.set_session(str(paf.session), "Static 1.qtm")
    widget.show()
    assert widget._anthro_sync.operation is None
    widget._on_fetch_clicked()
    wait_for(app, lambda: widget._anthro_connected and widget._anthro_sync.operation is None)
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.No)
    yield widget
    widget.close()
    wait_for(app, lambda: widget._anthro_sync.operation is None)
    widget.deleteLater()
    app.processEvents()


def edit(page, name, text, commit=True):
    widget = page._anthro_widgets[name]
    widget.setText(text)
    widget.textEdited.emit(text)
    if commit:
        widget.editingFinished.emit()
        page._on_save_clicked()  # Commit only through the manual button.


def idle(app, page):
    wait_for(app, lambda: page._anthro_sync.operation is None)


@pytest.mark.parametrize("name", list(VALUES))
def test_each_external_qtm_parameter_updates_correct_gui_without_write(app, paf, page, name):
    value = f32(VALUES[name] + (.125 if name == "BodyMass" else .0001234))
    before = {n: w.text() for n, w in page._anthro_widgets.items()}
    paf.nodes["session-a"]["Fields"][name] = value
    page._on_fetch_clicked()
    idle(app, page)
    assert same_parameter_value(page._anthro_widgets[name].text(), value)
    for other in VALUES.keys() - {name}:
        assert page._anthro_widgets[other].text() == before[other]
    page._on_fetch_clicked()
    idle(app, page)
    assert paf.puts == []
    assert "depth=3" in paf.gets[-3]  # Recheck all session copies for GUID collisions.
    assert "session-a" in paf.gets[-2]


def test_show_hide_and_local_reload_never_poll_qtm(app, paf, page):
    requests = len(paf.gets)
    page.hide()
    page.show()
    page._auto_fetch_static_data()
    QTest.qWait(2100)
    assert len(paf.gets) == requests and paf.puts == []


def test_bad_incoming_numeric_data_reports_error_without_overwriting(app, paf, page):
    original = page._body_mass.text()
    paf.nodes["session-a"]["Fields"]["BodyMass"] = "nan"
    page._on_fetch_clicked()
    idle(app, page)
    assert page._body_mass.text() == original
    assert not page._anthro_connected
    assert "BodyMass: enter a finite number" in page._sync_details_text()
    assert paf.puts == []


@pytest.mark.parametrize("connection", ["connected", "initial-poll", "unavailable"])
def test_run_button_opens_loading_and_starts_with_existing_calibration_values(
        app, paf, page, monkeypatch, connection):
    calls = []
    monkeypatch.setattr(page._service, "process_static",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    page._first_name.setText("Test")
    page._patient_number.setText("subject")
    page._set_combo(page._dob_day, "01")
    page._set_combo(page._dob_month, "Jan")
    page._set_combo(page._dob_year, "2000")
    # Old QTM sessions and marker-derived dimensions can be outside input bounds.
    page._height.setText("0.209999993")
    page._anthro_inputs["left_leg_length"].setText("0")
    if connection != "connected":
        page._anthro_connected = False
        paf.fail = connection == "unavailable"
    paf.delay = .15
    if connection == "initial-poll":
        page._start_manual_sync()  # A read in flight must not prevent local processing.
        assert page._anthro_sync.operation is not None
    QTest.mouseClick(page._run_btn, Qt.LeftButton)
    assert page._stack.currentWidget() is page._processing_widget
    assert page._progress_bar.value() == 10
    assert len(calls) == 1
    assert Path(calls[0][0][0]) == paf.session
    assert calls[0][0][1] == "Static 1.qtm"
    assert calls[0][1] == {"condition": "BF"}
    idle(app, page)
    assert len(calls) == 1


