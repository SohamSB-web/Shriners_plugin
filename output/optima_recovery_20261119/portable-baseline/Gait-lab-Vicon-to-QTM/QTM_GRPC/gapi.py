import inspect
import os
import time
import grpc
from concurrent import futures
import threading
import json # For command arguments

# Import the generated classes (adjust path if you use a 'patch' subdirectory)
# e.g., from patch import qtm_data_transfer_pb2
import qtm_data_transfer_pb2
import qtm_data_transfer_pb2_grpc

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
    
def grpc_send_command(self, command_name, command_args_json):
        try:
            with grpc.insecure_channel(f'localhost:{QTM_SCRIPT_GRPC_PORT}') as channel:
                stub = qtm_data_transfer_pb2_grpc.QtmTkinterBridgeStub(channel)
                command_request = qtm_data_transfer_pb2.CommandToQtm(
                    command_name=command_name,
                    command_args_json=command_args_json
                )
                response = stub.SendCommandToQtm(command_request, timeout=5) # Added timeout
                print(f"TkinterApp Client: Command sent. QTM Response: {response.message}, Success: {response.success}")
               # messagebox.showinfo("QTM Response", f"Success: {response.success}\nMessage: {response.message}")
        except grpc.RpcError as e:
            print(f"TkinterApp Client: Error sending command to QTM: {e}")
            #messagebox.showerror("gRPC Error", f"Failed to send command to QTM: {e.details()}")
        except Exception as e:
            print(f"TkinterApp Client: Unexpected error: {e}")
            #messagebox.showerror("Error", f"An unexpected error occurred: {e}")
def SetTrajectory(self,name,X,Y,Z):
    payload={}
    payload["name"] = name
    payload["X"] = X
    payload["Y"] = Y
    payload["Z"] = Z
    payload_json = json.dumps(payload)
    self.grpc_send_command("SetTrajectory", payload_json)

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

   