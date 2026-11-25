"""Focused offline tests. QTM writes are mocked; Qt/Matplotlib/C3D are real."""
import ast
import json
import math
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication
from app.services.frame_coordinates import (index_to_frame, frame_to_index, frame_to_time, time_to_frame,
    sample_index_to_frame, frame_to_sample_index, FRAME_CONVENTION, trace_event)
from app.services import event_service
from app.services.gcd_service import GCDService
from app.ui.charts.clinical_plots import ClinicalPlotCanvas
from app.ui.dialogs.event_details_dialog import EventDetailsDialog
from app.ui.pages.case_presentation_page import CasePresentationPage
from benchmark_case_presentation import populate

SERVERS = ["Gait-lab-Vicon-to-QTM/QTM_GRPC/tools/Py3_staticmain.py", "QTM-GRPC/tools/Py3_staticmain.py"]


def functions_from_file(path, names, namespace):
    """Load real functions without starting the embedded QTM menu/server."""
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    tree.body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(tree, str(path), "exec"), namespace)
    return namespace


@pytest.fixture(scope="session")
def qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture(params=SERVERS)
def server(request):
    labels = {"LHJC": 176}
    trajectory = SimpleNamespace(find_trajectory=lambda name: labels.get(name))
    def add(name):
        if name in labels:
            raise ValueError("duplicate marker")
        labels[name] = 200 + len(labels)
        return labels[name]
    trajectory.add_trajectory = Mock(side_effect=add)
    timeline = SimpleNamespace(get_measured_range=lambda: {"start": 0, "end": 1026},
                               get_selected_range=lambda: {"start": 100, "end": 219},
                               get_frame_count=lambda: 1027, get_frequency=lambda: 120)
    series = SimpleNamespace(set_samples=Mock())
    events = SimpleNamespace(get_events=lambda: [])
    qtm = SimpleNamespace(gui=SimpleNamespace(timeline=timeline),
                          data=SimpleNamespace(object=SimpleNamespace(trajectory=trajectory, event=events),
                                               series=SimpleNamespace(_3d=series)))
    ns = functions_from_file(request.param, {"setTrajectory", "createMarker", "getEvents"},
                             {"qtm": qtm, "math": math, "time_to_frame": time_to_frame, "frame_to_sample_index": frame_to_sample_index,
                              "sample_index_to_frame": sample_index_to_frame, "FRAME_CONVENTION": FRAME_CONVENTION, "trace_event": trace_event, "get_current_open_trial_name": lambda: "Trial"})
    return ns, qtm, series, trajectory


def test_full_trajectory_ignores_short_selection(server):
    ns, qtm, series, _ = server
    x = list(range(1027))
    ns["setTrajectory"]("LHJC", x, x, x, [True] * len(x))
    marker, target, samples = series.set_samples.call_args.args
    assert marker == 176 and target == {"start": 0, "end": 1026}
    assert len(samples) == 1027 and samples[-1]["position"] == [1026] * 3


def test_selected_range_maps_source_without_resampling(server):
    ns, _, series, _ = server
    x = list(range(1027))
    ns["setTrajectory"]("LHJC", x, x, x, [True] * len(x), 0, {"start": 100, "end": 219})
    _, target, samples = series.set_samples.call_args.args
    assert len(samples) == 120
    assert samples[0]["position"] == [100] * 3 and samples[-1]["position"] == [219] * 3


def test_partial_source_and_missing_samples(server):
    ns, _, series, _ = server
    ns["setTrajectory"]("LHJC", [1, None, float("nan"), 4], [2]*4, [3]*4, [True, False, True, True], 100)
    _, target, samples = series.set_samples.call_args.args
    assert target == {"start": 100, "end": 103}
    assert samples[1:3] == [None, None]


@pytest.mark.parametrize("source,target", [(0, {"start": 2, "end": 1}), (0, {"start": -1, "end": 2}),
                                            (0, {"start": 1020, "end": 1040}), (50, {"start": 20, "end": 21})])
def test_bad_ranges_never_write(server, source, target):
    ns, _, series, _ = server
    with pytest.raises(ValueError, match="LHJC.*ID=176.*source frames=.*target frames=.*target start=.*end="):
        ns["setTrajectory"]("LHJC", [1]*3, [1]*3, [1]*3, [True]*3, source, target)
    series.set_samples.assert_not_called()


def test_mismatched_lengths_and_ambiguous_legacy_payload(server):
    ns, _, series, _ = server
    with pytest.raises(ValueError, match="lengths differ"):
        ns["setTrajectory"]("LHJC", [1], [1, 2], [1], [True])
    with pytest.raises(ValueError, match="missing source_start"):
        ns["setTrajectory"]("LHJC", [1]*120, [1]*120, [1]*120)
    series.set_samples.assert_not_called()


def test_marker_creation_idempotent_and_real_errors_propagate(server):
    ns, _, _, trajectory = server
    assert ns["createMarker"]("LHJC") == 176
    first = ns["createMarker"]("RHJC")
    assert ns["createMarker"]("RHJC") == first
    assert trajectory.add_trajectory.call_count == 1
    trajectory.add_trajectory.side_effect = RuntimeError("measurement unavailable")
    with pytest.raises(RuntimeError, match="measurement unavailable"):
        ns["createMarker"]("NEW")


@pytest.mark.parametrize("start,frequency", [(1, 120), (100, 100), (201, 240), (295, 59.94)])
def test_event_conversion_save_load_and_ui(qt, tmp_path, start, frequency):
    for frame in (start, 295, start + 1026):
        index = frame_to_index(frame, start)
        assert index_to_frame(index, start) == frame
        assert time_to_frame(frame_to_time(frame, frequency), frequency) == frame
    info = event_service.save_trial_events(tmp_path, "Trial.qtm", [{"frame": 295, "label": "LSTRIKE"}],
                                          {"frame_rate": frequency, "initial_frame_offset": start - 1, "total_frames": 1027})
    for _ in range(3):
        info = event_service.load_trial_events(tmp_path, "Trial.qtm")
        info = event_service.save_trial_events(tmp_path, "Trial.qtm", info["events"], info["meta"])
        assert info["events"][0]["frame"] == 295
        assert info["events"][0]["relative_frame"] == 295 - start
        assert info["events"][0]["time"] == 294 / frequency
    dialog = EventDetailsDialog("Trial.qtm", info, session_dir=tmp_path)
    assert any(dialog._table.item(0, c) and dialog._table.item(0, c).text() == "295"
               for c in range(dialog._table.columnCount()))
    dialog._spin_frame.setValue(start + 1026)
    dialog._on_add_event_clicked()
    assert dialog._events[-1]["frame"] == start + 1026
    dialog._has_unsaved_changes = False
    dialog.close()


def test_old_auto_sidecar_migrates_once(tmp_path):
    path = tmp_path / "auto_event_Trial_results.json"
    path.write_text(json.dumps({"events": [{"frame": 295, "relative_frame": 294, "label": "LSTRIKE"}],
                                "meta": {"qtm_base_frame": 1, "initial_frame_offset": 0, "frame_rate": 120}}))
    info = event_service.load_trial_events(tmp_path, "Trial.qtm")
    assert info["events"][0]["frame"] == 295
    event_service.save_trial_events(tmp_path, "Trial.qtm", info["events"], info["meta"])
    assert event_service.load_trial_events(tmp_path, "Trial.qtm")["events"][0]["frame"] == 295


def test_qtm_read_write_roundtrip(server):
    ns, qtm, _, _ = server
    frames = [1, 295, 1027]
    qtm.data.object.event.get_events = lambda: [{"label": "LSTRIKE", "time": frame_to_time(f, 120)} for f in frames]
    result = ns["getEvents"]()
    assert result["events_dict"]["LSTRIKE"]["FrameNo"] == frames
    assert [e["frame"] for e in result["raw_events"]] == frames


def test_grpc_client_payloads_preserve_absolute_frame():
    sent = []
    ns = functions_from_file("Gait-lab-Vicon-to-QTM/gapi.py", {"SetEvent", "SetEvents", "SetTrajectory"},
                             {"json": json, "frame_to_time": frame_to_time, "FRAME_CONVENTION": FRAME_CONVENTION,
                              "trace_event": trace_event, "sample_index_to_frame": sample_index_to_frame, "grpc_send_command": lambda command, payload: sent.append((command, json.loads(payload))) or "OK"})
    ns["SetEvent"]("LSTRIKE", 295, 240, offset=200)
    assert sent[-1][1]["time"] == 294 / 240
    ns["SetEvents"]({"LSTRIKE": [200, 295, 400]}, 240, offset=200)
    assert [e["time"] for e in sent[-1][1]["events"]] == [frame_to_time(f,240) for f in [200,295,400]]
    ns["SetTrajectory"]("LHJC", [1,2,3], [1,2,3], [1,2,3], [True]*3, 0, 3, 200)
    assert sent[-1][1]["source_start"] == 200


@pytest.mark.parametrize("payload_format", ["raw", "legacy", "list"])
def test_event_service_grpc_serialization_and_retrieval(monkeypatch, payload_format):
    import socket
    import grpc
    sys.path.insert(0, str(ROOT / "QTM-GRPC"))
    import qtm_data_transfer_pb2_grpc as rpc
    sent = []
    event = {"label": "LSTRIKE", "time": 294 / 240, "frame": 295}
    payload = {"raw_events": [event], "frequency": 240, "initial_frame_offset": 200,
               "frame_convention": FRAME_CONVENTION}
    if payload_format == "legacy":
        payload.pop("raw_events")
        payload["events_dict"] = {"LSTRIKE": {"FrameNo": [295], "EventOffset": [0.0]}}
    elif payload_format == "list":
        payload = [event]

    def command(request, **kwargs):
        sent.append((request.command_name, json.loads(request.command_args_json)))
        return SimpleNamespace(success=True, message=json.dumps(payload) if request.command_name == "GetEvents" else "OK")

    monkeypatch.setattr(socket.socket, "connect_ex", lambda *args: 0)
    monkeypatch.setattr(event_service, "get_qtm_active_file", lambda: "Trial.qtm")
    monkeypatch.setattr(rpc, "QtmTkinterBridgeStub", lambda channel: SimpleNamespace(SendCommandToQtm=command))
    ok, msg = event_service.send_events_to_qtm([event], frame_rate=240, offset=200, trial_filename="Trial.qtm")
    assert ok, msg
    assert sent[-1][1]["events"][0]["time"] == 294 / 240
    ok, msg, _, events, meta = event_service.fetch_events_from_qtm(trial_filename="Trial.qtm", default_frame_rate=240)
    assert ok, msg
    assert events[0]["frame"] == 295
    assert events[0]["time"] == pytest.approx(294 / 240, abs=0.00005)
    assert events[0]["relative_frame"] == 295 - (201 if payload_format != "list" else 1)


@pytest.mark.parametrize("start", [0, 200, 7200])
def test_real_c3d_roundtrip(tmp_path, start):
    import ezc3d
    path = tmp_path / "Trial.c3d"
    trial = ezc3d.c3d()
    trial["parameters"]["POINT"]["RATE"]["value"] = [120]
    trial["parameters"]["POINT"]["LABELS"]["value"] = ["TEST"]
    trial["data"]["points"] = np.ones((4, 1, 1027))
    trial["header"]["points"]["first_frame"] = start
    trial.write(str(path))
    frames = [start + 1, start + 296, start + 1027]
    info = event_service.save_trial_events(tmp_path, "Trial.qtm",
        [{"frame": f, "label": "LSTRIKE"} for f in frames],
        {"frame_rate": 120, "initial_frame_offset": start})
    reader = ezc3d.c3d(str(path))
    times = reader["parameters"]["EVENT"]["TIMES"]["value"]
    np.testing.assert_array_equal(np.rint((times[0] * 60 + times[1]) * 120), np.asarray(frames) - 1)
    assert [e["relative_frame"] for e in info["events"]] == [0, 295, 1026]


@pytest.mark.parametrize("start", [0, 200])
def test_auto_detection_end_to_end_with_mock_qtm(tmp_path, monkeypatch, start):
    import importlib
    engine = ROOT / "Gait-lab-Vicon-to-QTM"
    monkeypatch.syspath_prepend(str(engine))
    synth = importlib.import_module("test_auto_event_zero_events")
    synth.build_session(str(tmp_path))
    import ezc3d
    path = tmp_path / "ZeroEvents.c3d"
    trial = ezc3d.c3d(str(path))
    trial["header"]["points"]["first_frame"] = start
    trial.write(str(path))
    import gapi
    import Py3_Utils
    import auto_event_trigger as trigger
    sent = []
    monkeypatch.setattr(Py3_Utils, "GetForcePlate", lambda: {})
    monkeypatch.setattr(gapi, "GetForcePlate", lambda: {})
    monkeypatch.setattr(gapi, "grpc_send_command", lambda command, body: sent.append((command, json.loads(body))) or "OK")
    monkeypatch.setattr(trigger, "get_qtm_active_measurement", lambda: "ZeroEvents.qtm")
    trigger.process_trial(str(tmp_path / "ZeroEvents.qtm"))
    info = event_service.load_trial_events(tmp_path, "ZeroEvents.qtm")
    writes = [body for command, body in sent if command == "SetEvent"]
    assert len(info["events"]) == len(writes) == 8
    for event, write in zip(info["events"], writes):
        assert event["frame"] == event["relative_frame"] + start + 1
        assert time_to_frame(write["time"], 100) == event["frame"]
    original_positions = [(e["label"], e["relative_frame"]) for e in info["events"]]
    sent.clear()
    trigger.process_trial(str(tmp_path / "ZeroEvents.qtm"))
    repeated = event_service.load_trial_events(tmp_path, "ZeroEvents.qtm")
    assert [(e["label"], e["relative_frame"]) for e in repeated["events"]] == original_positions
    assert [e["frame"] for e in repeated["events"]] == [e["frame"] for e in info["events"]]
    from Py3_varExtractor import extract_c3d
    fields = extract_c3d(str(path), False)
    for event in info["events"]:
        assert event["relative_frame"] + 1 in fields["EVENTS"][event["label"]]["FrameNo"]


def test_canvas_reuses_artists_and_matches_values(qt):
    canvas = ClinicalPlotCanvas()
    x = np.arange(101)
    args = dict(x_data=[x, x], y_data=[np.sin(x), np.cos(x)], colors=["blue", "red"],
                curve_ids=["L1", "R1"], toe_offs=[60, 61], opposite_toe_offs=[10, 11], title="Clinical")
    canvas.plot_gait_data(**args)
    ids = [id(line) for line in canvas.axes.lines]
    count = len(canvas.axes.lines)
    with patch.object(canvas.fig, "tight_layout") as layout, patch.object(canvas, "draw_idle") as redraw:
        for _ in range(3):
            canvas.plot_gait_data(**args)
        layout.assert_not_called()
        assert redraw.call_count == 3
    assert [id(line) for line in canvas.axes.lines] == ids
    args.update(x_data=[x], y_data=[np.cos(x)*2], colors=["red"], curve_ids=["R1"])
    canvas.plot_gait_data(**args)
    assert not canvas._trial_artists["L1"]["curve"].get_visible()
    np.testing.assert_array_equal(canvas._trial_artists["R1"]["curve"].get_ydata(), np.cos(x)*2)
    assert len(canvas.axes.lines) == count
    canvas.close()


def test_page_means_cache_invalidation_and_trial_changes(qt):
    page = CasePresentationPage()
    populate(page)
    page._refresh_plots(show_overlay=False)
    canvases = page._plot_grid.get_all_canvases()
    canvas_ids = [id(c) for c in canvases]
    canvas = canvases[0]
    old_line = canvas._trial_artists["L1"]["curve"]
    old_mean = canvas._trial_artists["Mean_L"]["curve"].get_ydata().copy()
    page._active_trial_filter.remove("L1")
    page._refresh_plots(show_overlay=False)
    assert not old_line.get_visible()
    assert not np.array_equal(canvas._trial_artists["Mean_L"]["curve"].get_ydata(), old_mean)
    page._active_trial_filter.add("L1")
    page._refresh_plots(show_overlay=False)
    assert canvas._trial_artists["L1"]["curve"] is old_line and old_line.get_visible()
    np.testing.assert_allclose(canvas._trial_artists["Mean_L"]["curve"].get_ydata(), old_mean)
    gcd = page._trial_data["L1"]
    name = page._get_page_settings().left_names[0]
    original = GCDService.get_variable_array(gcd, name)
    assert GCDService.get_variable_array(gcd, name) is original
    gcd.get_variable(name)[0] += 10
    changed = GCDService.get_variable_array(gcd, name)
    assert changed[0] == original[0] + 10
    page._refresh_plots(show_overlay=False)
    assert old_line.get_ydata()[0] == changed[0]
    assert [id(c) for c in page._plot_grid.get_all_canvases()] == canvas_ids
    page._trial_data.clear()
    page._refresh_plots(show_overlay=False)
    assert not old_line.get_visible()
    page.close()


def test_checkbox_burst_coalesces(qt):
    page = CasePresentationPage()
    with patch.object(page, "_refresh_plots") as refresh:
        page._on_filter_toggled("L1", False)
        page._on_filter_toggled("L1", True)
        page._on_filter_toggled("L2", False)
        qt.processEvents()
        assert refresh.call_count == 1
    page.close()


@pytest.mark.parametrize("frequency", [100, 120, 240, 59.94])
def test_both_reported_mismatches_are_physical_sample_errors(frequency):
    # Sample 294 is the independently calibrated QTM displayed frame 295.
    physical_sample = 294
    correct_frame = sample_index_to_frame(physical_sample)
    assert correct_frame == 295
    wrong_before_time = correct_frame / frequency  # QTM displayed frame 296
    wrong_after_time = (physical_sample - 1) / frequency  # QTM frame 294
    assert time_to_frame(wrong_before_time, frequency) == 296
    assert time_to_frame(wrong_after_time, frequency) == 294
    assert frame_to_time(correct_frame, frequency) * frequency == pytest.approx(physical_sample)
    assert time_to_frame(frame_to_time(correct_frame, frequency), frequency) == 295


@pytest.mark.parametrize("source,frame,relative", [
    ({"qtm_base_frame": 1}, 295, 294),
    ({"qtm_base_frame": 200}, 294, 94),
    ({"frame_convention": "qtm_absolute_zero_based"}, 294, 94),
    ({"source": "qtm_timeline"}, 295, 94),
    ({"manual_override": True}, 295, 94),
])
def test_legacy_data_provenance_and_no_cumulative_offset(tmp_path, source, frame, relative):
    offset = 0 if relative == 294 else 200
    path = tmp_path / "auto_event_Trial_results.json"
    path.write_text(json.dumps({"events": [{"frame": frame, "relative_frame": relative, "label": "LSTRIKE"}],
                               "meta": dict(source, initial_frame_offset=offset, frame_rate=120)}))
    for _ in range(3):
        info = event_service.load_trial_events(tmp_path, "Trial.qtm")
        assert info["events"][0]["frame"] == 295
        assert info["events"][0]["relative_frame"] == relative
        assert info["events"][0]["time"] == 294 / 120
        event_service.save_trial_events(tmp_path, "Trial.qtm", info["events"], info["meta"])
