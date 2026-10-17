import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..'))
from pyside6_compat import tk, ttk, messagebox
import grpc
from concurrent import futures
import threading
import json # For command arguments

# Import the generated classes (adjust path if you use a 'patch' subdirectory)
# e.g., from patch import qtm_data_transfer_pb2
# e.g., from patch import qtm_data_transfer_pb2_grpc
import qtm_data_transfer_pb2
import qtm_data_transfer_pb2_grpc

# Configuration
TKINTER_APP_GRPC_PORT = 50051 # Port this Tkinter app listens on
QTM_SCRIPT_GRPC_PORT = 50052  # Port the QTM script will listen on

class QtmTkinterBridgeServicer(qtm_data_transfer_pb2_grpc.QtmTkinterBridgeServicer):
    def __init__(self, app_gui):
        self.app_gui = app_gui

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


class TkinterApp:
    def __init__(self, root_tk):
        self.root = root_tk
        self.root.title("QTM Data Receiver & Commander")

        # --- Data Display Section ---
        data_frame = ttk.LabelFrame(self.root, text="Received QTM Data")
        data_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.labels = {}
        fields_to_display = ["Frames", "Capture_Frequency", "First_Frame", "Last_Frame"]
        for i, field_name in enumerate(fields_to_display):
            ttk.Label(data_frame, text=f"{field_name.replace('_', ' ')}:").grid(row=i, column=0, padx=5, pady=2, sticky="w")
            self.labels[field_name] = ttk.Label(data_frame, text="N/A")
            self.labels[field_name].grid(row=i, column=1, padx=5, pady=2, sticky="w")

        self.status_label = ttk.Label(data_frame, text="Waiting for data...")
        self.status_label.grid(row=len(fields_to_display), column=0, columnspan=2, pady=5)

        # --- Command Sending Section ---
        command_frame = ttk.LabelFrame(self.root, text="Send Command to QTM")
        command_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(command_frame, text="Command Name:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.command_name_entry = ttk.Entry(command_frame, width=30)
        self.command_name_entry.grid(row=0, column=1, padx=5, pady=2)
        self.command_name_entry.insert(0, "PrintMessage") # Example command

        ttk.Label(command_frame, text="Arguments (JSON):").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.command_args_entry = ttk.Entry(command_frame, width=30)
        self.command_args_entry.grid(row=1, column=1, padx=5, pady=2)
        self.command_args_entry.insert(0, '{"text": "Hello from Tkinter!"}') # Example args

        send_button = ttk.Button(command_frame, text="Send Command", command=self.send_command_to_qtm)
        send_button.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.root.columnconfigure(0, weight=1)

    def update_data_display(self, qtm_fields_data):
        self.root.after(0, self._do_update_gui, qtm_fields_data)

    def _do_update_gui(self, qtm_fields_data):
        self.labels["Frames"].config(text=str(qtm_fields_data.frames))
        self.labels["Capture_Frequency"].config(text=f"{qtm_fields_data.capture_frequency:.2f} Hz")
        self.labels["First_Frame"].config(text=str(qtm_fields_data.first_frame))
        self.labels["Last_Frame"].config(text=str(qtm_fields_data.last_frame))
        self.status_label.config(text="Data updated!")
        
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
                messagebox.showinfo("QTM Response", f"Success: {response.success}\nMessage: {response.message}")
        except grpc.RpcError as e:
            print(f"TkinterApp Client: Error sending command to QTM: {e}")
            messagebox.showerror("gRPC Error", f"Failed to send command to QTM: {e.details()}")
        except Exception as e:
            print(f"TkinterApp Client: Unexpected error: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
    def SetTrajectory(self,name,X,Y,Z):
        payload={}
        payload["name"] = name
        payload["X"] = X
        payload["Y"] = Y
        payload["Z"] = Z
        payload_json = json.dumps(payload)
        self.grpc_send_command("SetTrajectory", payload_json)
        

    def send_command_to_qtm(self):
        cmd_name = self.command_name_entry.get()
        cmd_args_json = self.command_args_entry.get()

        if not cmd_name:
            messagebox.showerror("Error", "Command name cannot be empty.")
            return

        try:
            # Validate JSON if args are provided
            if cmd_args_json:
                json.loads(cmd_args_json)
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Command arguments are not valid JSON.")
            return

        try:
            with grpc.insecure_channel(f'localhost:{QTM_SCRIPT_GRPC_PORT}') as channel:
                stub = qtm_data_transfer_pb2_grpc.QtmTkinterBridgeStub(channel)
                command_request = qtm_data_transfer_pb2.CommandToQtm(
                    command_name=cmd_name,
                    command_args_json=cmd_args_json
                )
                response = stub.SendCommandToQtm(command_request, timeout=5) # Added timeout
                print(f"TkinterApp Client: Command sent. QTM Response: {response.message}, Success: {response.success}")
                messagebox.showinfo("QTM Response", f"Success: {response.success}\nMessage: {response.message}")
        except grpc.RpcError as e:
            print(f"TkinterApp Client: Error sending command to QTM: {e}")
            messagebox.showerror("gRPC Error", f"Failed to send command to QTM: {e.details()}")
        except Exception as e:
            print(f"TkinterApp Client: Unexpected error: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")


def run_tkinter_grpc_server(app_gui):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    qtm_data_transfer_pb2_grpc.add_QtmTkinterBridgeServicer_to_server(
        QtmTkinterBridgeServicer(app_gui), server
    )
    server.add_insecure_port(f'[::]:{TKINTER_APP_GRPC_PORT}')
    print(f"TkinterApp gRPC server started on port {TKINTER_APP_GRPC_PORT}")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    root = tk.Tk()
    app_gui = TkinterApp(root)

    grpc_server_thread = threading.Thread(target=run_tkinter_grpc_server, args=(app_gui,), daemon=True)
    grpc_server_thread.start()

    root.mainloop()