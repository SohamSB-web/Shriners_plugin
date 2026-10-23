import inspect
import os
import time
from zipfile import Path
import grpc
from concurrent import futures
import threading
import json # For command arguments

# Import the generated classes (adjust path if you use a 'patch' subdirectory)
# e.g., from patch import qtm_data_transfer_pb2
# e.g., from patch import qtm_data_transfer_pb2_grpc
from pathlib import Path
_GAIT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _GAIT_DIR.parent
this_dir = str(Path(__file__).resolve().parent.parent / "QTM-GRPC")
if not os.path.isdir(this_dir):
    this_dir = str(_GAIT_DIR)

import sys
if this_dir not in sys.path:
    sys.path.insert(0, this_dir)
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from app.services.frame_coordinates import frame_to_time, FRAME_CONVENTION, trace_event, sample_index_to_frame
from proto import qtm_data_transfer_pb2_grpc,qtm_data_transfer_pb2

# Configuration
TKINTER_APP_GRPC_PORT = 50051 # Port this Tkinter app listens on
QTM_SCRIPT_GRPC_PORT = 50052  # Port the QTM script will listen on

class QtmTkinterBridgeServicer(qtm_data_transfer_pb2_grpc.QtmTkinterBridgeServicer):
    def __init__(self ):
        #self.app_gui = app_gui
        pass

    # This method is called by the QTM script
    def SendQtmFieldsToApp(self, request, context):
        print(f"TkinterApp Server: Received QtmFields - Frames={request.frames}, Freq={request.capture_frequency}, First={request.first_frame}, Last={request.last_frame}")
        self.app_gui.update_data_display(request)
        return qtm_data_transfer_pb2.Ack(message="Data received by Tkinter server", success=True)

    # This method is NOT implemented by this server; it's for the QTM script's server
    def SendCommandToQtm(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented by TkinterApp server!')
        return qtm_data_transfer_pb2.Ack()
    
def _is_qtm_port_open():
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.05)
            return s.connect_ex(('127.0.0.1', QTM_SCRIPT_GRPC_PORT)) == 0
    except Exception:
        return False


def grpc_send_command(command_name, command_args_json):
    if not _is_qtm_port_open():
        # QTM script is not running on port 50052; return None immediately without 5s timeout
        return None

    try:
        with grpc.insecure_channel(f'localhost:{QTM_SCRIPT_GRPC_PORT}') as channel:
            stub = qtm_data_transfer_pb2_grpc.QtmTkinterBridgeStub(channel)
            command_request = qtm_data_transfer_pb2.CommandToQtm(
                command_name=command_name,
                command_args_json=command_args_json
            )
            response = stub.SendCommandToQtm(command_request, timeout=2)
            print(f"QTM Bridge Client: Command '{command_name}' sent. Success: {response.success}")
            if not response.success:
                print(f"QTM Bridge Client: QTM reported failure for '{command_name}': {response.message}")
                return None
            return response.message
    except grpc.RpcError as e:
        print(f"QTM Bridge Client: Error sending command to QTM: {e}")
    except Exception as e:
        print(f"QTM Bridge Client: Unexpected error: {e}")
    return None

def SetTrajectory(name,X,Y,Z,exists,start,end,offset=0, target_range=None):
    # start/end are the existing half-open processing window; offset maps
    # source array index zero to the absolute QTM sample index.
    if not (len(X) == len(Y) == len(Z) == len(exists)):
        raise ValueError(f"Trajectory '{name}': X/Y/Z/exists lengths differ")
    payload = {"name": name}
    for key, values in (("X", X), ("Y", Y), ("Z", Z)):
        payload[key] = [float(v) if v is not None else None for v in values]
    payload["exists"] = [bool(v) for v in exists]
    payload["source_start"] = int(offset)
    if target_range is not None:
        payload["target_range"] = target_range
    payload_json = json.dumps(payload)
    
    
    grpc_send_command("SetTrajectory", payload_json)
def SetEvent(label, frame_no, frequency, offset=0, trial_name=None):
    """Write a single event back to QTM.

    Both single and bulk commands serialize absolute QTM frames to the
    original measurement clock. A crop offset must not be subtracted twice.

    Parameters
    ----------
    label : str
        Event label, e.g. 'LSTRIKE', 'ROFF'.
    frame_no : int
        Absolute QTM displayed timeline frame (one-based), including the recording offset.
    frequency : float
        Capture frequency (Hz) used to convert frame → time.
    offset : int
        Recording origin retained for call compatibility; frame_no is already absolute.
    trial_name : str, optional
        Name of the trial file (e.g. 'Dynamic 1'). If provided, QTM verifies
        that this trial matches the active measurement before writing.
    """
    if float(frequency) <= 0:
        raise ValueError("Capture frequency must be positive")
    time_seconds = frame_to_time(frame_no, frequency)
    trace_event("grpc_send", label, frame_no, frequency, sample_index_to_frame(offset))
    event = {"label": label, "time": time_seconds, "frame": int(frame_no), "frame_convention": FRAME_CONVENTION}
    if trial_name:
        event["trial_name"] = str(trial_name)
    payload = json.dumps(event)
    resp = grpc_send_command("SetEvent", payload)
    if resp is None:
        print(f"[gapi] WARNING — SetEvent('{label}', frame={frame_no}) got no response from QTM.")
    return resp


def SetEvents(events_dict, frequency, offset=0, trial_name=None):
    """Write multiple events to QTM in a single bulk gRPC call.

    Parameters
    ----------
    events_dict : dict
        Mapping of label → list of frame numbers, e.g.
        {'Auto_LHS': [10, 120], 'Auto_LTO': [55, 160], ...}.
    frequency : float
        Capture frequency (Hz).
    offset : int
        Recording origin retained for call compatibility; frame_no is already absolute.
    trial_name : str, optional
        Name of the trial file (e.g. 'Dynamic 1'). If provided, QTM verifies
        that this trial matches the active measurement before writing.
    """
    if float(frequency) <= 0:
        raise ValueError("Capture frequency must be positive")
    bulk_events = []
    for label, frame_list in events_dict.items():
        for frame_no in frame_list:
            time_seconds = frame_to_time(frame_no, frequency)
            bulk_events.append({"label": label, "time": time_seconds, "frame": int(frame_no), "frame_convention": FRAME_CONVENTION})

    total = len(bulk_events)
    if total == 0:
        print("[gapi] SetEvents: nothing to write (0 events).")
        return

    payload_data = {"events": bulk_events}
    if trial_name:
        payload_data["trial_name"] = str(trial_name)
    payload = json.dumps(payload_data)
    resp = grpc_send_command("SetEvents", payload)
    if resp is not None:
        print(f"[gapi] SetEvents: wrote {total} events to QTM.")
    else:
        print(f"[gapi] WARNING — SetEvents got no response from QTM.")
    return resp


def CreateModeledMarker(markerName):
    
    grpc_send_command("CreateModelMarker", json.dumps({"markerName": markerName}))
def ResetTimeline():
    grpc_send_command("ResetTimeline", json.dumps({}))
def SetMeasuredRange(start,end):
    grpc_send_command("SetMeasuredRange", json.dumps({"start": start, "end": end}))
def GetEvents(name,fields):
    events=fields["EVENTS"]
    
    if name in events:
        return events[name]["FrameNo"],events[name]["EventOffset"]
    return [],[]

def GetForcePlate():
    payload=grpc_send_command("GetForcePlate", json.dumps({}))
    if payload is None:
        return {}
    # QTM returns success=False with a plain-text error (not JSON) when the
    # command can't be serviced, e.g. "method requires a measurement" if the
    # trial isn't currently open/active in QTM. grpc_send_command doesn't
    # surface that success flag, so treat a non-JSON reply the same as "no
    # force plate data available" instead of crashing on json.loads.
    try:
        payload_json = json.loads(payload)
    except json.JSONDecodeError:
        print(f"[gapi] WARNING — GetForcePlate got a non-JSON response from QTM: {payload}")
        return {}
    #print(payload_json.keys())
    return payload_json

def getTimeLineMeasure():
    res = grpc_send_command("GetMeasurementRange", json.dumps({}))
    if res is None:
        return None
    return json.loads(res)
def getProjDirectory():
    res = json.loads(grpc_send_command("GetProjDirectory", json.dumps({})))
    if res is None:
        return None
    #print(res)
    res=res["path"]+"Data"
    
    #print(res)
    return res

def run_qtm_grpc_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    qtm_data_transfer_pb2_grpc.add_QtmTkinterBridgeServicer_to_server(
        QtmTkinterBridgeServicer(), server
    )
    server.add_insecure_port(f'[::]:{TKINTER_APP_GRPC_PORT}')
    print(f"QTM Bridge gRPC server started on port {TKINTER_APP_GRPC_PORT}")
    server.start()
    server.wait_for_termination()

# Backward compatibility alias
run_tkinter_grpc_server = run_qtm_grpc_server

if __name__ == '__main__':
    grpc_server_thread = threading.Thread(target=run_qtm_grpc_server, daemon=True)
    grpc_server_thread.start()
    print("QTM Bridge gRPC server thread started. Main thread waiting. Press Ctrl+C to stop.")
    try:
        # Keep the main thread alive so the daemon server thread can run
        while True:
            getProjDirectory()
            time.sleep(1)  # Or use input("Press Enter to stop server...\n")
    except KeyboardInterrupt:
        print("Shutting down server...")
    # Add any server cleanup code here if necessary, e.g., server.stop(0)
    # This would require getting the server instance from run_tkinter_grpc_server
    print("Exiting main thread.")

   