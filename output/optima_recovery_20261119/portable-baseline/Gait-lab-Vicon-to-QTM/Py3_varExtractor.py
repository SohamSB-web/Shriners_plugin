from collections import defaultdict
import xml.etree.ElementTree as ET
import os
from ezc3d import c3d
from gapi import GetEvents, getTimeLineMeasure, ResetTimeline, SetMeasuredRange
import numpy as np
from Py3_Utils import ProcessForceplateData, ForcePlateGUI


def extract_c3d(c3dfile, is_static):
    fields = {}
    reader = c3d(c3dfile, extract_forceplat_data=True)
    fields["Name"] = "Test"
    initial_frame_offset = reader["header"]["points"]["first_frame"]
    fields["initial_frame_offset"] = initial_frame_offset
    fields["Capture_Frequency"] = reader["parameters"]["POINT"]["RATE"]["value"][0]
    fields["Frames"] = reader["parameters"]["POINT"]["FRAMES"]["value"][0]
    fields["Points"] = reader["parameters"]["POINT"]["LABELS"]["value"]
    fields["Units"] = reader["parameters"]["POINT"]["UNITS"]["value"][0]
  
    first_frame, last_frame = (
        reader["header"]["points"]["first_frame"],
        reader["header"]["points"]["last_frame"],
    )
    # tmp = getTimeLineMeasure()

    if is_static:
        fields["First Frame"], fields["Last Frame"] = (
            max(first_frame - initial_frame_offset, 0),
            min(last_frame + 1 - initial_frame_offset, fields["Frames"]),
        )
    else:
        # QTM/ezc3d only write the "EVENT" parameter group into a .c3d once the
        # trial holds at least one event, and a trial whose events were all
        # deleted again keeps the group with USED=0 and empty LABELS/TIMES.
        # Both are normal for a trial that has not been labeled by hand yet -
        # which is exactly the input auto event labeling runs on - so read the
        # group defensively and treat "absent" and "present but empty" alike as
        # "no events yet" instead of raising KeyError / ValueError.
        evt_group = reader["parameters"].get("EVENT", {})
        evt_label = evt_group["LABELS"]["value"] if "LABELS" in evt_group else []
        evt_times = evt_group["TIMES"]["value"] if "TIMES" in evt_group else [[], []]
        # Event times are absolute (relative to the start of the original,
        # uncropped recording), but the point/marker arrays extracted below
        # are indexed relative to this c3d's own crop start. Subtract
        # initial_frame_offset, then add one at the legacy gait-consumer
        # boundary: Py3_CreateGCD slices [Strike1 - 1:Strike2].
        evt_frames = list(
            map(
                lambda x: round(x * fields["Capture_Frequency"]) - initial_frame_offset + 1,
                [60.0 * m + sec for m, sec in zip(evt_times[0], evt_times[1])],
            )
        )
        evt_offsets = [
            (60.0 * minutes + seconds) * fields["Capture_Frequency"]
            - round((60.0 * minutes + seconds) * fields["Capture_Frequency"])
            for minutes, seconds in zip(evt_times[0], evt_times[1])
        ]
        tmp = defaultdict(lambda: {"FrameNo": [], "EventOffset": []})
        if "CONTEXTS" in evt_group:
            evt_contexts = evt_group["CONTEXTS"]["value"]
            ctx_map={
                "Right":{
                    "Foot Strike":"RSTRIKE",
                    "Foot Off":"ROFF"
                },
                "Left":{
                    "Foot Strike":"LSTRIKE",
                    "Foot Off":"LOFF"
                }
            }
            for label, frame, off, context in zip(
                evt_label, evt_frames, evt_offsets, evt_contexts
            ):
                tmp[ctx_map.get(context,{}).get(label,label)]["FrameNo"].append(frame)
                tmp[ctx_map.get(context,{}).get(label,label)]["EventOffset"].append(off)

        else:

            for label, frame, off in zip(evt_label, evt_frames, evt_offsets):
                tmp[label]["FrameNo"].append(frame)
                tmp[label]["EventOffset"].append(off)

        fields["EVENTS"] = tmp
        if evt_frames:
            fields["First Frame"], fields["Last Frame"] = (
                max(min(evt_frames) - 1 - 10, 0),
                min(max(evt_frames) - 1 + 10, fields["Frames"]),
            )
        else:
            # Check for auto_event sidecar JSON if c3d has no events
            c3d_dir = os.path.dirname(c3dfile)
            c3d_stem = os.path.splitext(os.path.basename(c3dfile))[0]
            json_candidates = [
                os.path.join(c3d_dir, "Events", f"auto_event_{c3d_stem}_results.json"),
                os.path.join(c3d_dir, "Events", f"auto_event_{c3d_stem.lower()}_results.json"),
                os.path.join(c3d_dir, f"auto_event_{c3d_stem}_results.json"),
                os.path.join(c3d_dir, f"auto_event_{c3d_stem.lower()}_results.json"),
            ]
            json_path = None
            for p in json_candidates:
                if os.path.isfile(p):
                    json_path = p
                    break

            sidecar_loaded = False
            if json_path:
                try:
                    import json as _json
                    with open(json_path, 'r', encoding='utf-8') as jf:
                        jdata = _json.load(jf)
                    loaded_events = jdata.get("events", [])
                    if loaded_events:
                        tmp_json = defaultdict(lambda: {"FrameNo": [], "EventOffset": []})
                        all_ev_frames = []
                        for ev in loaded_events:
                            lbl = ev.get("label", "")
                            rel_f = ev.get("relative_frame")
                            if rel_f is None:
                                f_val = int(ev.get("frame", 0))
                                qtm_base = initial_frame_offset + 1  # Displayed frame at C3D array index zero
                                rel_f = f_val - qtm_base
                            else:
                                rel_f = int(rel_f)
                            # Py3_CreateGCD expects 1-based frames (Strike1 - 1 : Strike2):
                            frame_1based = rel_f + 1
                            tmp_json[lbl]["FrameNo"].append(frame_1based)
                            tmp_json[lbl]["EventOffset"].append(0.0)
                            all_ev_frames.append(rel_f)

                        fields["EVENTS"] = tmp_json
                        if all_ev_frames:
                            fields["First Frame"] = max(min(all_ev_frames) - 10, 0)
                            fields["Last Frame"] = min(max(all_ev_frames) + 10, fields["Frames"])
                            sidecar_loaded = True
                            print(f"[varExtractor] Loaded {len(loaded_events)} events from sidecar {os.path.basename(json_path)}")
                except Exception as ex:
                    print(f"[varExtractor] Warning: failed to load sidecar events from {json_path}: {ex}")

            if not sidecar_loaded:
                # Nothing labeled yet, so there is no event range to narrow to:
                # hand back the whole captured range (the same range the static
                # branch uses) so auto labeling searches the full trial.
                print("No EVENT data in c3d or sidecar JSON; using full capture range.")
                fields["First Frame"], fields["Last Frame"] = (
                    max(first_frame - initial_frame_offset, 0),
                    min(last_frame + 1 - initial_frame_offset, fields["Frames"]),
                )

    # if tmp is not None:
    #     event_arr=[]
    #     for i in ["LSTRIKE","LOFF","RSTRIKE","ROFF"]:
    #         tmpFrame,tmpOffset=GetEvents(i,offset=0)
    #         event_arr.extend(tmpFrame)
    #     print(f"Events found: {event_arr}")
    #     if len(event_arr)<8:
    #         fields["First Frame"], fields["Last Frame"] = (
    #             max(tmp["start"]-initial_frame_offset,0),
    #             min(tmp["end"] + 1-initial_frame_offset,fields["Frames"]),
    #         )

    #     else: # If we have enough events, we can use them to set the measured range more accurately
    #         fields["First Frame"], fields["Last Frame"] = (
    #             max(min(event_arr)-10-initial_frame_offset,0),
    #             min(max(event_arr)+10 + 1-initial_frame_offset,fields["Frames"]),
    #         )

    # fields["Last Frame"] = reader['header']["points"]['last_frame']
    fields["FP"] = ProcessForceplateData(reader)
    # ForcePlateGUI(fields["FP"]).run()

    skip_keys = [
        "Session ID",
        "ID",
        "BodyMass",
        "Mass",
        "Bodymass",
        "Uncropped Measurement Frames",
        "Cropped Measurement Start Frame",
        "Cropped Measurement End Frame",
    ]
    # "PROCESSING" is optional in the same way "EVENT" is: it is only written
    # once a trial has been through the modelling pipeline, so a raw unlabeled
    # trial can legitimately have no group at all.  Fall back to an empty group
    # (subject metrics stay unset) rather than raising.
    processing = reader["parameters"].get("PROCESSING", {})
    if not processing:
        print("No PROCESSING data in c3d; subject metrics unavailable.")
    metrics_declared = "Metrics" in processing
    metric = processing.get("Metrics", {}).get("value", ["mm"])[0]
    # With Settings.paf lengths in meters QTM writes e.g. Height=1.435 and no
    # "Metrics" tag, while older c3d files hold the same value as 1435 (mm).
    # Body-size lengths are never < 10 mm, so a small value means meters.
    length_keys = {
        "Height", "InterAsisDistance", "LeftLegLength", "RightLegLength",
        "LeftKneeWidth", "RightKneeWidth", "LeftAnkleWidth", "RightAnkleWidth",
        "LeftAsisTrocanterDistance", "RightAsisTrocanterDistance",
    }

    for key, val in processing.items():
        if "value" not in val or len(val["value"]) == 0:
            continue

        value = val["value"][0]
        is_numeric = isinstance(value, (int, float)) or (
            isinstance(value, str) and value.isdigit()
        )

        if key not in skip_keys and is_numeric:
            if metric == "m":
                value = value * 1000
            elif metric == "cm":
                value = value * 10
            elif (
                not metrics_declared
                and key in length_keys
                and isinstance(value, (int, float, np.floating))
                and 0 < abs(value) < 10
            ):
                value = value * 1000

        fields[key] = value
        print(value)

        # fields[key] = val["value"][0]
        # print(val["value"][0])
    try:
        fields["Bodymass"] = fields["BodyMass"]
    except Exception as e:
        fields["Bodymass"] = fields.get("Bodymass", 0)
    channels = [
        ("X", 1),
        ("Y", 1),
        ("Z", 1),
    ]
    for inx, val in enumerate(fields["Points"]):
        val = val.strip()
        fields[val] = {}
        fields[val]["Exists"] = []
        for i, channel in enumerate(channels):
            fields[val][channel[0]] = reader["data"]["points"][i][inx] * channel[1]
        fields[val]["Exists"] = [
        not (np.isnan(fields[val]["X"][j]) or
             np.isnan(fields[val]["Y"][j]) or
             np.isnan(fields[val]["Z"][j]))
        for j in range(len(fields[val]["X"]))
        ]
        #print(val,fields[val]["Exists"][:10])
    #print(fields.keys())

    return fields


def extract_fields_by_filename(xml_file_path, target_filename, is_static):
    """
    Extract all fields from session.xml for a given filename.

    Args:
        xml_file_path (str): Path to the session.xml file
        target_filename (str): The filename to search for (e.g., "Dynamic 1.qtm")

    Returns:
        dict: Dictionary containing all fields for the specified filename, or None if not found
    """
    try:
        # Parse the XML file
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        # Search for measurement with the target filename
        for measurement in root.findall(".//Measurement"):
            filename_attr = measurement.get("Filename")
            if filename_attr == target_filename:
                # Extract all fields
                fields = {}
                # fields_element = measurement.find('Fields')

                # if fields_element is not None:
                #     for field in fields_element:
                #         if field.text:
                #             try:
                #             # Try to convert to float
                #                 fields[field.tag] = float(field.text)
                #             except ValueError:
                #             # If conversion fails, keep as string
                #                 fields[field.tag] = field.text
                #         else:
                #             fields[field.tag] = field.text

                # Also include measurement attributes
                fields["Type"] = measurement.get("Type")
                fields["Filename"] = measurement.get("Filename").split(".")[0]
                fields["Path"] = os.path.join(os.path.dirname(xml_file_path))
                # fields["Bodymass"] = fields["Weight"]

                fields = {
                    **fields,
                    **extract_c3d(
                        os.path.join(
                            os.path.dirname(xml_file_path),
                            filename_attr.split(".")[0] + ".c3d",
                        ),
                        is_static,
                    ),
                }

                return fields

        print(f"No measurement found with filename: {target_filename}")
        return None

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return None
    except FileNotFoundError:
        print(f"File not found: {xml_file_path}")
        return None


if __name__ == "__main__":
    from pathlib import Path
    _demo = (
        Path(__file__).resolve().parent.parent
        / "Shriners_Gait_Model_PAF_v1.0"
        / "Shriners_Gait_Model_PAF_v1.0"
        / "Data"
        / "test_002"
        / "2025-02-21_0003"
    )
    xml_file_path = str(_demo / "session.xml")
    target_filename = "Dynamic 1.qtm"

    fields = extract_fields_by_filename(xml_file_path, target_filename, False)

    if fields:
        print(f"Fields for {target_filename}:")
        for key, value in list(fields.items()):
            print(f"{key}:{value}")
    else:
        print("No fields found or an error occurred.")
