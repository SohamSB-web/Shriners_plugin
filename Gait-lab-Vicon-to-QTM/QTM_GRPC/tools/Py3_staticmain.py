from concurrent import futures
import json
import sys
import os
import inspect
import importlib
import threading



this_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
if this_dir not in sys.path:
    sys.path.append(this_dir)
# pyrefly: ignore [missing-import]
import qtm
# pyrefly: ignore [missing-import]
import qtm.data.series._6d as data_6d
# pyrefly: ignore [missing-import]
import qtm.settings.processing._6d as rb
# pyrefly: ignore [missing-import]
import qtm.data.object.event as qtm_event  # explicit import for event API
# pyrefly: ignore [missing-import]
from qtm.gui import add_command,set_command_execute_function,insert_menu_button,insert_menu_separator 
# pyrefly: ignore [missing-import]
import qtm.gui.timeline as tline
# pyrefly: ignore [missing-import]
import qtm.gui.message as msg
import math
from pathlib import Path
for _parent in Path(this_dir).parents:
    if (_parent / "app" / "services" / "frame_coordinates.py").is_file():
        if str(_parent) not in sys.path:
            sys.path.insert(0, str(_parent))
        break
from app.services.frame_coordinates import (time_to_frame, frame_to_sample_index,
                                            sample_index_to_frame, FRAME_CONVENTION, trace_event)
import os
import qtm_data_transfer_pb2 as qtm_data_transfer_pb2
import qtm_data_transfer_pb2_grpc as qtm_data_transfer_pb2_grpc
import grpc
import subprocess
importlib.reload(qtm_data_transfer_pb2)
importlib.reload(qtm_data_transfer_pb2_grpc)
have_numpy = True
try:
    import numpy as np
except Exception as e:
    #print(f"Error importing numpy: {e}")
    have_numpy = False


# Configuration
TKINTER_APP_GRPC_PORT = 50051  # Port the Tkinter app listens on
QTM_SCRIPT_GRPC_PORT = 50052   # Port this QTM script will listen on

def get_current_open_trial_name():
    """
    Get the name of the trial currently open in QTM.
    Uses QTM window title or timeline properties.
    """
    try:
        import ctypes
        from ctypes import wintypes

        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible

        titles = []
        def foreach_window(hwnd, lParam):
            if IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buff, length + 1)
                    t = buff.value
                    if "Qualisys Track Manager" in t:
                        titles.append(t)
            return True

        EnumWindows(EnumWindowsProc(foreach_window), 0)
        for t in titles:
            parts = t.split(" - Qualisys Track Manager")
            if len(parts) > 1 and parts[0].strip():
                return parts[0].strip()
    except Exception:
        pass
    return None


# --- QTM Script's gRPC Server Implementation ---
class QtmCommandServicer(qtm_data_transfer_pb2_grpc.QtmTkinterBridgeServicer):
    # This method is called by the Tkinter App
    def SendCommandToQtm(self, request, context):
        cmd_name = request.command_name
        cmd_args_json = request.command_args_json
        print(f"QTM Server: Received command '{cmd_name}' ")

        try:
            args = {}
            if cmd_args_json:
                args = json.loads(cmd_args_json)
            
            # --- Execute QTM internal commands based on cmd_name ---
            if cmd_name == "PrintMessage":
                message_text = args.get("text", "No message text provided.")
                print(f"QTM Server: Attempting to display message: {message_text}")
                qtm.gui.message.add_message("Info",f"Command from Tkinter: {message_text}","info")
                return qtm_data_transfer_pb2.Ack(message=f"Command '{cmd_name}' executed.", success=True)
            
            elif cmd_name in {"GetEventSnapshot", "ApplyEventRevision"}:
                from app.services.qtm_event_protocol import guarded_event_command
                payload = guarded_event_command(qtm, qtm_event, tline, cmd_name, args)
                return qtm_data_transfer_pb2.Ack(message=json.dumps(payload), success=True)

            elif cmd_name == "GetActiveMeasurement":
                active_trial = get_current_open_trial_name()
                return qtm_data_transfer_pb2.Ack(
                    message=active_trial or "",
                    success=bool(active_trial)
                )

            elif cmd_name == "GetFrameCount":
                # Example of a command that reads QTM data
                frame_count = qtm.gui.timeline.get_frame_count()
                return qtm_data_transfer_pb2.Ack(message=f"Current frame count: {frame_count}", success=True)
            elif cmd_name=="SetTrajectory":
                payload=args
                setTrajectory(payload["name"], payload["X"], payload["Y"], payload["Z"],
                              payload.get("exists"), payload.get("source_start"), payload.get("target_range"))
                return qtm_data_transfer_pb2.Ack(message=f"Set trajectory for {payload['name']}", success=True)
            elif cmd_name == "GetForcePlate":
                payload=GetForcePlateData()
                return qtm_data_transfer_pb2.Ack(message=json.dumps(payload), success=True)
            elif cmd_name=="CreateModelMarker":
                try:
                    marker_name = args["markerName"]
                    print(f"QTM Server: Creating model marker '{marker_name}'")
                    marker_id = createMarker(marker_name)
                    return qtm_data_transfer_pb2.Ack(message=f"Model marker '{marker_name}' ID={marker_id} ready", success=True)
                except KeyError:
                    print("QTM Server: 'markerName' argument is required for CreateModelMarker command.")
                    return qtm_data_transfer_pb2.Ack(message="Missing 'markerName' argument.", success=False)
            elif cmd_name == "GetEvents":
                events = getEvents()
                return qtm_data_transfer_pb2.Ack(message=json.dumps(events), success=True)
            elif cmd_name == "ClearEvents":
                target_trial = args.get("trial_name") or args.get("trial_filename")
                if target_trial:
                    active_trial = get_current_open_trial_name()
                    if active_trial:
                        import re
                        clean_target = re.sub(r'[\s_\-]+', ' ', os.path.splitext(os.path.basename(str(target_trial)))[0].lower().strip().lstrip('*').rstrip('*')).strip()
                        clean_active = re.sub(r'[\s_\-]+', ' ', os.path.splitext(os.path.basename(str(active_trial)))[0].lower().strip().lstrip('*').rstrip('*')).strip()
                        if clean_target and clean_active and clean_target != clean_active:
                            skip_msg = f"ClearEvents skipped: QTM open file '{active_trial}' does not match target '{target_trial}'"
                            print(f"QTM Server: {skip_msg}")
                            return qtm_data_transfer_pb2.Ack(message=skip_msg, success=False)

                try:
                    cleared = 0
                    if hasattr(qtm_event, "delete_event") and hasattr(qtm_event, "get_events"):
                        for ev in qtm_event.get_events():
                            try:
                                ev_id = ev.get("id") if isinstance(ev, dict) else ev
                                qtm_event.delete_event(ev_id)
                                cleared += 1
                            except Exception:
                                pass
                    elif hasattr(qtm_event, "clear_events"):
                        qtm_event.clear_events()
                    return qtm_data_transfer_pb2.Ack(message=f"Cleared {cleared} events", success=True)
                except Exception as e:
                    return qtm_data_transfer_pb2.Ack(message=f"Clear note: {e}", success=False)
            elif cmd_name == "SetEvent":
                target_trial = args.get("trial_name") or args.get("trial_filename")
                if target_trial:
                    active_trial = get_current_open_trial_name()
                    if active_trial:
                        import re
                        clean_target = re.sub(r'[\s_\-]+', ' ', os.path.splitext(os.path.basename(str(target_trial)))[0].lower().strip().lstrip('*').rstrip('*')).strip()
                        clean_active = re.sub(r'[\s_\-]+', ' ', os.path.splitext(os.path.basename(str(active_trial)))[0].lower().strip().lstrip('*').rstrip('*')).strip()
                        if clean_target and clean_active and clean_target != clean_active:
                            skip_msg = f"SetEvent skipped: QTM open file '{active_trial}' does not match target '{target_trial}'"
                            print(f"QTM Server: {skip_msg}")
                            return qtm_data_transfer_pb2.Ack(message=skip_msg, success=False)

                print(args)
                label = args.get("label", "Unknown")
                time_val = float(args.get("time", 0.0))
                print(f"QTM Server: SetEvent '{label}' at t={time_val:.4f}s")
                try:
                    qtm_event.add_event({"label": label, "time": time_val})
                    trace_event("QTM_write", label, time_to_frame(time_val, tline.get_frequency()), tline.get_frequency())
                    return qtm_data_transfer_pb2.Ack(message=f"Event '{label}' set at t={time_val:.4f}s", success=True)
                except Exception as ev_err:
                    print(f"QTM Server: SetEvent error: {ev_err}")
                    msg.add_message("Error", f"SetEvent error: {ev_err}", "error")
                    return qtm_data_transfer_pb2.Ack(message=f"Error setting event: {ev_err}", success=False)

            elif cmd_name == "SetEvents":
                target_trial = args.get("trial_name") or args.get("trial_filename")
                if target_trial:
                    active_trial = get_current_open_trial_name()
                    if active_trial:
                        import re
                        clean_target = re.sub(r'[\s_\-]+', ' ', os.path.splitext(os.path.basename(str(target_trial)))[0].lower().strip().lstrip('*').rstrip('*')).strip()
                        clean_active = re.sub(r'[\s_\-]+', ' ', os.path.splitext(os.path.basename(str(active_trial)))[0].lower().strip().lstrip('*').rstrip('*')).strip()
                        if clean_target and clean_active and clean_target != clean_active:
                            skip_msg = f"SetEvents skipped: QTM open file '{active_trial}' does not match target '{target_trial}'"
                            print(f"QTM Server: {skip_msg}")
                            return qtm_data_transfer_pb2.Ack(message=skip_msg, success=False)

                # Bulk event write via repeated add_event calls
                new_events = args.get("events", [])
                print(f"QTM Server: SetEvents called with {len(new_events)} events")
                ok_count, fail_count = 0, 0
                for ev in new_events:
                    #print(ev)
                    try:
                        qtm_event.add_event({"label": ev["label"], "time": ev["time"]})
                        ok_count += 1
                    except Exception as e:
                        print(f"QTM Server: Error setting event: {e}")  
                        fail_count += 1
                result_msg = f"SetEvents: {ok_count} written, {fail_count} failed out of {len(new_events)}"
                print(f"QTM Server: {result_msg}")
                if fail_count > 0:
                    msg.add_message("Warning", result_msg, "warning")
                else:
                    msg.add_message("Info", f"Auto events: wrote {ok_count} events", "info")
                return qtm_data_transfer_pb2.Ack(
                    message=result_msg, success=(fail_count == 0))

            elif cmd_name == "GetMeasurementRange":
                rng=GetMeasurementRange()
                return qtm_data_transfer_pb2.Ack(message=json.dumps(rng), success=True)
            elif cmd_name == "GetProjDirectory":
                proj_dir=GetProjDirectory()
                
                return qtm_data_transfer_pb2.Ack(message=json.dumps(proj_dir), success=True)
            elif cmd_name == "ResetTimeline":
                ResetTimeline()
                return qtm_data_transfer_pb2.Ack(message="Timeline reset to full range.", success=True)
            elif cmd_name == "SetMeasuredRange":
                start = float(args.get("start", 0.0))
                end = float(args.get("end", 0.0))
                SetMeasuredRange(start, end)
                return qtm_data_transfer_pb2.Ack(message=f"Measured range set to {start:.2f}s - {end:.2f}s", success=True)
            else:
                print(f"QTM Server: Unknown command '{cmd_name}'")
                print("helo")
                return qtm_data_transfer_pb2.Ack(message=f"Unknown command: {cmd_name}", success=False)


        except json.JSONDecodeError:
            print("QTM Server: Error decoding JSON arguments.")
            return qtm_data_transfer_pb2.Ack(message="Invalid JSON arguments.", success=False)
        except Exception as e:
            print(f"QTM Server: Error processing command '{cmd_name}': {e}")
            return qtm_data_transfer_pb2.Ack(message=f"Error executing command: {str(e)}", success=False)

    # This method is NOT implemented by this server; it's for the Tkinter app's server
    def SendQtmFieldsToApp(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented by QTM script server!')
        return qtm_data_transfer_pb2.Ack()

qtm_grpc_server_thread = None
qtm_grpc_server = None

def start_qtm_grpc_server():
    global qtm_grpc_server
    qtm_grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    qtm_data_transfer_pb2_grpc.add_QtmTkinterBridgeServicer_to_server(
        QtmCommandServicer(), qtm_grpc_server
    )
    qtm_grpc_server.add_insecure_port(f'[::]:{QTM_SCRIPT_GRPC_PORT}')
    qtm_grpc_server.start()
    print(f"QTM Script gRPC server started on port {QTM_SCRIPT_GRPC_PORT}, waiting for commands...")
    # qtm_grpc_server.wait_for_termination() # This would block, run in thread

def stop_qtm_grpc_server():
    global qtm_grpc_server
    if qtm_grpc_server:
        print("Stopping QTM Script gRPC server...")
        qtm_grpc_server.stop(0) # 0 for graceful shutdown
        qtm_grpc_server = None
        print("QTM Script gRPC server stopped.")


# --- QTM Script's gRPC Client Logic ---


def send_qtm_fields_via_grpc(fields_data):
    try:
        with grpc.insecure_channel(f'localhost:{TKINTER_APP_GRPC_PORT}') as channel:
            stub = qtm_data_transfer_pb2_grpc.QtmTkinterBridgeStub(channel)
            qtm_fields_message = qtm_data_transfer_pb2.QtmFields(
                frames=fields_data.get("Frames", 0),
                capture_frequency=float(fields_data.get('Capture_Frequency', 0.0)),
                first_frame=fields_data.get("First Frame", 0),
                last_frame=fields_data.get("Last Frame", 0)
            )
            response = stub.SendQtmFieldsToApp(qtm_fields_message, timeout=5) # Added timeout
            print(f"QTM Client: Sent fields. TkinterApp Response: {response.message}, Success: {response.success}")
            # qtm.gui.message.add_message((f"gRPC to Tkinter: {response.message}") # Optional: show in QTM UI
    except grpc.RpcError as e:
        error_message = f"QTM Client: Error sending data to TkinterApp: {e.details()}"
        print(error_message)
        qtm.gui.message.add_message("Error",error_message,"error")
    except Exception as e:
        error_message = f"QTM Client: An unexpected error occurred: {e}"
        print(error_message)
        qtm.gui.message.add_message("Error",error_message,"error")

helloWorldcmd="HelloWorld"
StartExec="StartExec"
RunStaticMain="RunStaticMain"
TestEvents="TestEvents"
def GetForcePlateData():
    forcePlateIds = qtm.data.series.force.get_series_ids()
    payload = {}
    for id in forcePlateIds:
        payload[id] = {
            "Force": {
                "X": [],
                "Y": [],
                "Z": []
            },
            "Moment": {
                "X": [],
                "Y": [],
                "Z": []
            },
            "Center_of_Pressure": {
                "X": [],
                "Y": [],
                "Z": []
            },
            "Exists": [],
            "Frequency":qtm.data.series.force.get_frequency(id)
        }
        
        try:
            vals = qtm.data.series.force.get_samples(id)
            
            for sample in vals:
                if sample:  # Sample exists
                    force = sample["force"]
                    moment = sample["moment"] 
                    cop = sample["center_of_pressure"]
                    
                    payload[id]["Force"]["X"].append(force[0])
                    payload[id]["Force"]["Y"].append(force[1])
                    payload[id]["Force"]["Z"].append(force[2])
                    
                    payload[id]["Moment"]["X"].append(moment[0])
                    payload[id]["Moment"]["Y"].append(moment[1])
                    payload[id]["Moment"]["Z"].append(moment[2])
                    
                    payload[id]["Center_of_Pressure"]["X"].append(cop[0])
                    payload[id]["Center_of_Pressure"]["Y"].append(cop[1])
                    payload[id]["Center_of_Pressure"]["Z"].append(cop[2])
                    
                    payload[id]["Exists"].append(True)
                else:  # No sample at this frame
                    payload[id]["Force"]["X"].append(None)
                    payload[id]["Force"]["Y"].append(None)
                    payload[id]["Force"]["Z"].append(None)
                    
                    payload[id]["Moment"]["X"].append(None)
                    payload[id]["Moment"]["Y"].append(None)
                    payload[id]["Moment"]["Z"].append(None)
                    
                    payload[id]["Center_of_Pressure"]["X"].append(None)
                    payload[id]["Center_of_Pressure"]["Y"].append(None)
                    payload[id]["Center_of_Pressure"]["Z"].append(None)
                    
                    payload[id]["Exists"].append(False)
                    
        except Exception as e:
            print(f"Error getting force plate data for ID {id}: {e}")
            qtm.gui.message.add_message("Error", f"Error getting force plate data for ID {id}: {e}", "error")
    print(payload.keys())
    return payload

def ResetTimeline():
    full_time=qtm.gui.timeline.get_measured_range()
    qtm.gui.timeline.set_measured_range(full_time)
    return {}

def SetMeasuredRange(start,end):
    qtm.gui.timeline.set_measured_range({"start": start, "end": end})
    return {}
    
def GetMeasurementRange():
    
    return qtm.gui.timeline.get_selected_range()
def GetProjDirectory():
    return {"path":qtm.settings.directory.get_project_directory()}
def getEvents():
    """
    Get all events and return them in a structured dictionary format
    Returns:
    {
        label: {
            "FrameNo": [],
            "EventOffset": []
        }
    }
    """
    try:
        active_trial = get_current_open_trial_name()
        if not active_trial:
            return {}

        events = qtm.data.object.event.get_events()
        frequency = qtm.gui.timeline.get_frequency()  # Default to 120 if not available
        total_frames = qtm.gui.timeline.get_frame_count()  # Get actual frame count
        measured = qtm.gui.timeline.get_measured_range()
        
        events_dict = {}
        
        for event in events:
            label = event["label"]
            time = event["time"]  # Time in seconds
            
            # QTM event times use the absolute measurement clock (frame zero at t=0).
            frame_no = time_to_frame(time, frequency)
            sample_index = frame_to_sample_index(frame_no)
            
            # Calculate event offset (time within the frame)
            # This is the fractional part of the frame timing
            event_offset = (time * frequency) - sample_index
            
            # Ensure the absolute frame is inside the inclusive measured range
            if measured["start"] <= sample_index <= measured["end"]:
                if label not in events_dict:
                    events_dict[label] = {
                        "FrameNo": [],
                        "EventOffset": []
                    }
                
                trace_event("QTM_read", label, frame_no, frequency, sample_index_to_frame(measured["start"]))
                events_dict[label]["FrameNo"].append(frame_no)
                events_dict[label]["EventOffset"].append(event_offset)
            else:
                print(f"Warning: Event '{label}' at frame {frame_no} is outside valid range (1-{total_frames})")
        
        print(f"Found {len(events)} events across {len(events_dict)} unique labels")
        print(f"Events dictionary: {events_dict}")

        raw_events = []
        for event in events:
            try:
                raw_events.append({
                    "label": event.get("label", ""),
                    "time": float(event.get("time", 0.0)),
                    "frame": time_to_frame(float(event.get("time", 0.0)), frequency),
                })
            except Exception:
                pass

        return {
            "events_dict": events_dict,
            "raw_events": raw_events,
            "frequency": frequency,
            "total_frames": total_frames,
            "initial_frame_offset": measured["start"],
            "recording_start_frame": sample_index_to_frame(measured["start"]),
            "frame_convention": FRAME_CONVENTION,
            "active_trial": active_trial or "",
        }

    except Exception as e:
        print(f"Info: Unable to get events (no measurement open or timeline unavailable): {e}")
        return {}
def get_points():
    try:
        ids=qtm.data.object.trajectory.get_trajectory_ids()
        idLabelMap={}
        for id in ids:
            if qtm.data.object.trajectory.get_label(id):
                idLabelMap[id]=" ".join(qtm.data.object.trajectory.get_label(id).split("_"))
        points_Channels={}
        print(f"Trajectory IDs: {idLabelMap}")
        for id,Label in idLabelMap.items():
            arr=qtm.data.series._3d.get_samples(id)
            tmp={
                "X":[],
                "Y":[],
                'Z':[],
                "Residue":[],
                "Exists":[]
                
            }
            for i in arr:
                if i:
                    pos=i["position"]
                    residue=i["residual"]
                    X=pos[0]
                    Y=pos[1]
                    Z=pos[2]
                    tmp["X"].append(X)
                    tmp["Y"].append(Y)
                    tmp["Z"].append(Z)
                    tmp["Exists"].append(True)
                    tmp["Residue"].append(residue)
                else:
                    tmp["X"].append(None)
                    tmp["Y"].append(None)
                    tmp["Z"].append(None)
                    tmp["Exists"].append(False)
                    tmp["Residue"].append(None)
            points_Channels[Label]=tmp
                    
        #print(f"Points Channels: {points_Channels}")
        return points_Channels
        
    except Exception as e:
        print(f"Error getting trajectory IDs: {e}")
        qtm.gui.message.add_message("Error",f"Error getting trajectory IDs: {e}","error")
        return {}
def set_field_and_send():
    fields = {}
    try:
        fields["Frames"] = qtm.gui.timeline.get_frame_count()
        fields['Capture_Frequency'] = qtm.gui.timeline.get_frequency()
        trace_range = qtm.gui.timeline.get_trace_range()
        fields["First Frame"] = trace_range["start"] if trace_range else 0
        fields["Last Frame"] = trace_range["end"] if trace_range else 0
    except Exception as e:
        print(f"Error getting QTM fields: {e}")
        qtm.gui.message.add_message("Error",f"Error getting QTM fields: {e}","error")
        return

    print("QTM Fields set:")
    for key, value in fields.items():
        print(f"  {key}: {value}")
    
    pointChannels=get_points()
    if not pointChannels:
        print("No points found, not sending fields.")
        return
    
    #send_qtm_fields_via_grpc(fields)

def setTrajectory(name, X, Y, Z, exists=None, source_start=None, target_range=None):
    """Write absolute inclusive QTM sample ranges without changing selection."""
    trajectory = qtm.data.object.trajectory
    label_id = trajectory.find_trajectory(name)
    measured = qtm.gui.timeline.get_measured_range()
    target = dict(target_range if target_range is not None else measured)
    count = len(X)
    start, end = target.get("start"), target.get("end")
    target_count = end - start + 1 if isinstance(start, int) and isinstance(end, int) else 0
    detail = (f"Trajectory '{name}' ID={label_id}: source frames={count}, "
              f"target frames={target_count}, target start={start}, end={end}")
    if (not isinstance(start, int) or not isinstance(end, int) or start > end
            or start < measured["start"] or end > measured["end"]):
        raise ValueError(detail + "; invalid/out-of-measurement target range")
    if label_id is None:
        raise ValueError(detail + "; marker does not exist; create it first")
    if len(Y) != count or len(Z) != count or (exists is not None and len(exists) != count):
        raise ValueError(detail + "; X/Y/Z/exists lengths differ")
    if source_start is None:
        # Legacy XYZ-only payloads are unambiguous only for a full measurement.
        if count != measured["end"] - measured["start"] + 1:
            raise ValueError(detail + "; missing source_start for partial trajectory")
        source_start = measured["start"]
    if not isinstance(source_start, int):
        raise ValueError(detail + "; source_start must be an integer sample index")
    if target_range is None:
        target = {"start": source_start, "end": source_start + count - 1}
        start, end = target["start"], target["end"]
        target_count = count
        detail = (f"Trajectory '{name}' ID={label_id}: source frames={count}, "
                  f"target frames={target_count}, target start={start}, end={end}")
    first = start - source_start
    last = end - source_start + 1
    if start < measured["start"] or end > measured["end"] or count == 0 or first < 0 or last > count:
        raise ValueError(detail + "; source does not cover the requested measurement range")
    samples = []
    for i in range(first, last):
        position = [X[i], Y[i], Z[i]]
        valid = exists is None or bool(exists[i])
        if valid:
            try:
                valid = all(value is not None and math.isfinite(float(value)) for value in position)
            except (TypeError, ValueError):
                raise ValueError(detail + f"; nonnumeric XYZ at source index {i}")
        samples.append({"position": position, "residual": 0.0} if valid else None)
    if len(samples) != target_count:
        raise ValueError(detail + "; sample count mismatch")
    print(detail)
    qtm.data.series._3d.set_samples(label_id, target, samples)
    return label_id


def createMarker(markerName):
    """Reuse an existing labeled trajectory, including after a concurrent create."""
    trajectory = qtm.data.object.trajectory
    label_id = trajectory.find_trajectory(markerName)
    if label_id is not None:
        return label_id
    try:
        return trajectory.add_trajectory(markerName)
    except Exception:
        label_id = trajectory.find_trajectory(markerName)
        if label_id is None:
            raise
        return label_id
def add_my_commands():
    add_command(helloWorldcmd)
    add_command(StartExec)
    add_command(RunStaticMain)
    add_command(TestEvents)
    #set_command_execute_function(RunStaticMain, lambda: runStaticMain())
    set_command_execute_function(StartExec, lambda: set_field_and_send())
    set_command_execute_function(TestEvents, lambda: (getEvents()))
    set_command_execute_function(helloWorldcmd, lambda: (print("Hello World! This is a static processor script.")))

def setup_my_menu():
    my_menu_id = qtm.gui.insert_menu_submenu(None, "Shriner Static Processor")
    insert_menu_button(my_menu_id, "Hello World", helloWorldcmd)
    insert_menu_button(my_menu_id, "Send Fields to Tkinter", StartExec)
    insert_menu_button(my_menu_id, "Get Events", TestEvents)
    #insert_menu_button(my_menu_id, "Run Static Main", RunStaticMain)
    insert_menu_separator(my_menu_id)

menu_priority = 1
def add_menu():
    global qtm_grpc_server_thread
    if have_numpy:
        add_my_commands()
        #setup_my_menu()
        
        # Start the QTM gRPC server in a separate thread
        if qtm_grpc_server_thread is None or not qtm_grpc_server_thread.is_alive():
            qtm_grpc_server_thread = threading.Thread(target=start_qtm_grpc_server, daemon=True)
            qtm_grpc_server_thread.start()
            print("QTM gRPC server thread initiated.")
        else:
            print("QTM gRPC server thread already running.")
            
    else:
        msg_str = "You need Numpy installed in Python to run Shriner gait processor scripts."
        print(msg_str)
        qtm.gui.message.add_message("Errror", msg_str,"error")


if __name__ == "__main__":
    add_menu()
