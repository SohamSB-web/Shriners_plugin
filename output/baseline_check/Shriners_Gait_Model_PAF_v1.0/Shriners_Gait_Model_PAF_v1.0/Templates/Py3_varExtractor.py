import xml.etree.ElementTree as ET
import os
from ezc3d import c3d
import numpy as np
from Py3_Utils import ProcessForceplateData, ForcePlateGUI


def extract_c3d(c3dfile):
    fields = {}
    reader = c3d(c3dfile, extract_forceplat_data=True)
    fields["Name"]="Test"
    initial_frame_offset = reader["header"]["points"]["first_frame"]
    fields["initial_frame_offset"] = initial_frame_offset
    fields["Capture_Frequency"] = reader["parameters"]["POINT"]["RATE"]["value"][0]
    fields["Frames"] = reader["parameters"]["POINT"]["FRAMES"]["value"][0]
    fields["Points"] = reader["parameters"]["POINT"]["LABELS"]["value"]
    fields["Units"] = reader["parameters"]["POINT"]["UNITS"]["value"][0]

    # Replaced getTimeLineMeasure() gRPC call with direct C3D file values
    fields["First Frame"], fields["Last Frame"] = (
        max(reader["header"]["points"]["first_frame"] - initial_frame_offset, 0),
        max(reader["header"]["points"]["last_frame"] + 1 - initial_frame_offset, 0),
    )

    # Extract Events directly from C3D
    events_dict = {
        "LSTRIKE": {"FrameNo": [], "EventOffset": []},
        "LOFF": {"FrameNo": [], "EventOffset": []},
        "RSTRIKE": {"FrameNo": [], "EventOffset": []},
        "ROFF": {"FrameNo": [], "EventOffset": []}
    }
    
    if "EVENT" in reader["parameters"] and "USED" in reader["parameters"]["EVENT"] and reader["parameters"]["EVENT"]["USED"]["value"][0] > 0:
        event_p = reader["parameters"]["EVENT"]
        contexts = event_p["CONTEXTS"]["value"]
        labels = event_p["LABELS"]["value"]
        times = event_p["TIMES"]["value"]
        
        # ezc3d TIMES is typically [2, N], row 1 is time in seconds
        if len(times.shape) == 2:
            time_sec = 60.0 * times[0, :] + times[1, :]
        else:
            time_sec = times
        
        for ctx, lbl, t in zip(contexts, labels, time_sec):
            ctx = ctx.strip()
            lbl = lbl.strip()
            
            key = lbl.upper() if lbl.upper() in events_dict else None
            if ctx == "Left" and lbl == "Foot Strike":
                key = "LSTRIKE"
            elif ctx == "Left" and lbl == "Foot Off":
                key = "LOFF"
            elif ctx == "Right" and lbl == "Foot Strike":
                key = "RSTRIKE"
            elif ctx == "Right" and lbl == "Foot Off":
                key = "ROFF"
            
            if key:
                exact_frame = (t * fields["Capture_Frequency"]) - initial_frame_offset + 1
                frame_no = int(exact_frame)
                offset = exact_frame - frame_no
                
                events_dict[key]["FrameNo"].append(frame_no)
                events_dict[key]["EventOffset"].append(offset)
                
    fields["Events"] = events_dict
    fields["FP"] = ProcessForceplateData(reader)
    # ForcePlateGUI(fields["FP"]).run()
    for key, val in reader["parameters"]["PROCESSING"].items():
        if "value" not in val or len(val["value"]) == 0:
            continue

        fields[key] = val["value"][0]
    try:
        
        fields["Bodymass"] = fields["BodyMass"]
    except Exception as e:
        fields["Bodymass"] = fields.get("Bodymass",0)
    channels = [
        ("X",1),
        ("Y",1),
        ("Z",1),
    ]
    for inx, val in enumerate(fields["Points"]):
        val=val.strip()
        fields[val] = {}
        fields[val]["Exists"] = []
        for i, channel in enumerate(channels):
            data = reader["data"]["points"][i][inx] * channel[1]
            
            # Record Exists before interpolating
            exists_mask = ~np.isnan(data)
            # fields[val]["Exists"] array should be True/False
            # if we append for each channel, we'll append 3x the frames. 
            # We only need to append once per point, so we'll do it below if i == 0
            if i == 0:
                fields[val]["Exists"] = exists_mask.tolist()

            # Interpolate missing values (NaNs) to avoid polyfit SVD errors
            if exists_mask.any() and not exists_mask.all():
                xp = np.where(exists_mask)[0]
                fp = data[exists_mask]
                data[~exists_mask] = np.interp(np.where(~exists_mask)[0], xp, fp)
            elif not exists_mask.any():
                data[:] = 0.0

            fields[val][channel[0]] = data.tolist() if isinstance(data, np.ndarray) else data
    print(fields.keys())

    return fields


def extract_fields_by_filename(xml_file_path, target_filename):
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
                        )
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
        / "Data"
        / "test_002"
        / "2025-02-21_0003"
    )
    xml_file_path = str(_demo / "session.xml")
    target_filename = "Dynamic 1.qtm"

    fields = extract_fields_by_filename(xml_file_path, target_filename)

    if fields:
        print(f"Fields for {target_filename}:")
        for key, value in list(fields.items()):
            print(f"{key}:{value}")
    else:
        print("No fields found or an error occurred.")
