"""Disposable sessions and mocked transport only; never contact live QTM."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from PySide6.QtWidgets import QApplication, QMessageBox
from app.services import event_service as svc
from app.ui.pages.dynamic_analysis_page import DynamicAnalysisPage
from app.ui.pages.static_analysis_page import StaticAnalysisPage


def events(count):
    return [{"frame": 100 + i * 20, "label": "RSTRIKE" if i % 2 == 0 else "ROFF"}
            for i in range(count)]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("before,after", [(8, 7), (8, 5), (1, 0), (8, 0)])
def test_deletions_persist_and_isolate_trials(tmp_path, before, after):
    svc.save_trial_events(tmp_path, "Dynamic 1.qtm", events(before))
    svc.save_trial_events(tmp_path, "Dynamic 2.qtm", events(8))
    other = tmp_path / "Events" / "auto_event_Dynamic 2_results.json"
    original = other.read_bytes()
    with patch.object(svc, "fetch_events_from_qtm",
                      return_value=(True, "OK", "Dynamic 1.qtm", events(after), {"frame_rate": 100})), \
         patch.object(svc, "send_events_to_qtm") as send:
        for cycle in range(4):
            updated, _, matched, _, info = svc.sync_qtm_events_to_session(
                tmp_path, ["Dynamic 1.qtm", "Dynamic 2.qtm"])
            assert updated == (cycle == 0)
            assert matched == "Dynamic 1.qtm"
            assert info["total_events"] == after
            assert svc.load_trial_events(tmp_path, matched)["total_events"] == after
        send.assert_not_called()
    assert other.read_bytes() == original


def test_failed_read_preserves_cache(tmp_path):
    svc.save_trial_events(tmp_path, "Dynamic 1.qtm", events(8))
    with patch.object(svc, "fetch_events_from_qtm",
                      return_value=(False, "Disconnected", "Dynamic 1.qtm", [], {})):
        assert not svc.sync_qtm_events_to_session(tmp_path, ["Dynamic 1.qtm"])[0]
    assert svc.load_trial_events(tmp_path, "Dynamic 1.qtm")["total_events"] == 8


@pytest.mark.parametrize("payload,success", [('{}', False), ('', False),
                                           ('{"raw_events": [], "frequency": 100}', True),
                                           ('[]', True)])
def test_transport_distinguishes_empty_from_failed_read(payload, success):
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "QTM-GRPC"))
    import qtm_data_transfer_pb2_grpc as rpc
    client = Mock()
    client.SendCommandToQtm.return_value = SimpleNamespace(success=True, message=payload)
    with patch("socket.socket") as sock, \
         patch.object(svc, "get_qtm_active_file", return_value="Dynamic 1.qtm"), \
         patch("app.services.settings_service.SettingsService") as settings, \
         patch.object(rpc, "QtmTkinterBridgeStub", return_value=client), \
         patch("grpc.insecure_channel"):
        sock.return_value.__enter__.return_value.connect_ex.return_value = 0
        settings.return_value.load_app_settings.return_value.qtm_grpc_location = str(root / "QTM-GRPC")
        assert svc.fetch_events_from_qtm()[0] is success


def test_page_zero_status_then_new_events_and_manual_push(app, tmp_path):
    xml = tmp_path / "session.xml"
    xml.write_text("<Session/>")
    (tmp_path / "Dynamic 1.qtm").touch()
    svc.save_trial_events(tmp_path, "Dynamic 1.qtm", events(8))
    page = DynamicAnalysisPage()
    page.load_session(str(xml))
    page._qtm_sync_timer.stop()
    row = page._trial_rows["Dynamic 1.qtm"]
    try:
        with patch.object(svc, "fetch_events_from_qtm") as fetch, \
             patch.object(svc, "send_events_to_qtm") as implicit_send:
            for count in (7, 5, 0, 0, 8):
                fetch.return_value = (True, "OK", "Dynamic 1.qtm", events(count), {"frame_rate": 100})
                page._poll_qtm_events_sync()
                assert row._events_info["total_events"] == count
                if count == 0:
                    assert row._status == "READY"
                    assert row._events_btn.text() == "Not Labeled — 0 Events"
                else:
                    assert row._status == "EVENTS LABELED"
            implicit_send.assert_not_called()
        with patch("app.ui.pages.dynamic_analysis_page.send_events_to_qtm",
                   return_value=(True, "OK")) as send, \
             patch.object(QMessageBox, "information"):
            page._on_push_trial_events_to_qtm("Dynamic 1.qtm")
            assert len(send.call_args.kwargs["events_list"]) == 8
        assert page._qtm_sync_timer.interval() == 1200
    finally:
        page.clear_session()
        page.deleteLater()


def test_static_initializes(app):
    page = StaticAnalysisPage()
    assert page._session_path == ""
    assert page._browse_btn.isEnabled()
    page.clear_session()
    page.deleteLater()


def test_explicit_sender_still_sends_bulk_events():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "QTM-GRPC"))
    import qtm_data_transfer_pb2_grpc as rpc
    import json
    client = Mock()
    client.SendCommandToQtm.return_value = SimpleNamespace(success=True, message="OK")
    with patch("socket.socket") as sock, \
         patch.object(svc, "get_qtm_active_file", return_value="Dynamic 1.qtm"), \
         patch("app.services.settings_service.SettingsService") as settings, \
         patch.object(rpc, "QtmTkinterBridgeStub", return_value=client), \
         patch("grpc.insecure_channel"):
        sock.return_value.__enter__.return_value.connect_ex.return_value = 0
        settings.return_value.load_app_settings.return_value.qtm_grpc_location = str(root / "QTM-GRPC")
        assert svc.send_events_to_qtm(events(8), trial_filename="Dynamic 1.qtm")[0]
    requests = [call.args[0] for call in client.SendCommandToQtm.call_args_list]
    assert [r.command_name for r in requests] == ["ClearEvents", "SetEvents"]
    assert len(json.loads(requests[-1].command_args_json)["events"]) == 8
