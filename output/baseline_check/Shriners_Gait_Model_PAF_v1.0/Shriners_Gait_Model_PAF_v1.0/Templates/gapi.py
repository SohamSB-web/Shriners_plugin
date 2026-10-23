import inspect
import os
import time
import tkinter as tk
from tkinter import ttk, messagebox
import grpc
from concurrent import futures
import threading
import json # For command arguments

# Import the generated classes (adjust path if you use a 'patch' subdirectory)
# e.g., from patch import qtm_data_transfer_pb2
# e.g., from patch import qtm_data_transfer_pb2_grpc
from pathlib import Path
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent.parent
this_dir = str(Path(__file__).resolve().parent.parent.parent / "QTM-GRPC")
if not os.path.isdir(this_dir):
    this_dir = str(_THIS_DIR)
import sys
if this_dir not in sys.path:
    sys.path.append(this_dir)
import qtm_data_transfer_pb2
import qtm_data_transfer_pb2_grpc

# Configuration
TKINTER_APP_GRPC_PORT = 50051 # Port this Tkinter app listens on
QTM_SCRIPT_GRPC_PORT = 50052  # Port the QTM script will listen on

BATCH_MODE = False

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
    
def grpc_send_command(command_name, command_args_json):
        try:
            with grpc.insecure_channel(f'localhost:{QTM_SCRIPT_GRPC_PORT}') as channel:
                stub = qtm_data_transfer_pb2_grpc.QtmTkinterBridgeStub(channel)
                command_request = qtm_data_transfer_pb2.CommandToQtm(
                    command_name=command_name,
                    command_args_json=command_args_json
                )
                response = stub.SendCommandToQtm(command_request, timeout=5) # Added timeout
                print(f"TkinterApp Client: Command sent. QTM Response: {response.message if response.message[0]!='{' else 'JSON received'}, Success: {response.success}")
                return response.message
               # messagebox.showinfo("QTM Response", f"Success: {response.success}\nMessage: {response.message}")
        except grpc.RpcError as e:
            print(f"TkinterApp Client: Error sending command to QTM: {e}")
            #messagebox.showerror("gRPC Error", f"Failed to send command to QTM: {e.details()}")
        except Exception as e:
            print(f"TkinterApp Client: Unexpected error: {e}")
            #messagebox.showerror("Error", f"An unexpected error occurred: {e}")

def SetTrajectory(name,X,Y,Z,exists,start,end,offset=0, target_range=None):
    if BATCH_MODE:
        return
    # start/end are the existing half-open processing window; offset maps
    # source array index zero to the absolute QTM sample index.
    if not (len(X) == len(Y) == len(Z) == len(exists)):
        raise ValueError(f"Trajectory '{name}': X/Y/Z/exists lengths differ")
    payload = {"name": name}
    if not 0 <= start < end <= len(X):
        raise ValueError(f"Trajectory '{name}': invalid processing window [{start}, {end})")
    for key, values in (("X", X), ("Y", Y), ("Z", Z)):
        payload[key] = [float(v) if v is not None else None for v in values]
    payload["exists"] = [bool(v) for v in exists]
    for key in ("X", "Y", "Z", "exists"):
        payload[key] = payload[key][start:end]
    payload["source_start"] = int(offset) + int(start)
    if target_range is not None:
        payload["target_range"] = target_range
    payload_json = json.dumps(payload)
    
    
    grpc_send_command("SetTrajectory", payload_json)

def CreateModeledMarker(markerName):
    
    grpc_send_command("CreateModelMarker", json.dumps({"markerName": markerName}))

def run_tkinter_grpc_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    qtm_data_transfer_pb2_grpc.add_QtmTkinterBridgeServicer_to_server(
        QtmTkinterBridgeServicer(), server
    )
    server.add_insecure_port(f'[::]:{TKINTER_APP_GRPC_PORT}')
    print(f"TkinterApp gRPC server started on port {TKINTER_APP_GRPC_PORT}")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
  

    grpc_server_thread = threading.Thread(target=run_tkinter_grpc_server, daemon=True)
    grpc_server_thread.start()
    print(f"TkinterApp gRPC server thread started. Main thread waiting. Press Ctrl+C to stop.")
    try:
        # Keep the main thread alive so the daemon server thread can run
        while True:
            time.sleep(1)  # Or use input("Press Enter to stop server...\n")
    except KeyboardInterrupt:
        print("Shutting down server...")
    # Add any server cleanup code here if necessary, e.g., server.stop(0)
    # This would require getting the server instance from run_tkinter_grpc_server
    print("Exiting main thread.")

   