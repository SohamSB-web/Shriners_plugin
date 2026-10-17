# pylint: disable=R0904
# pylint: disable=unused-import
from __future__ import print_function

# disable too many methods refactor message
import sys
import os
import math
import asyncio
import qtm_rt
import xml.etree.ElementTree as ET

class ViconNexusException(Exception):
    def __init__(self, message, additional=''):
        super(ViconNexusException, self).__init__()
        self.message = message
        self.additional = additional

    def __str__(self):
        error_report = self.message
        if self.additional:
            error_report = self.message + ' ' + self.additional
        return error_report
    
class ViconNexus(object):
    @staticmethod
    def _get_safe_string_value(string):
        output = string.Value()
        if sys.version_info < (3, 0):
            output = output.decode('utf-8')
        return output
    
    async def __init__(self, host='127.0.0.1'):
        self.GenerateErrors = True
        self.Client = None
        self.is_connecting = False
        self._qtm_control_password = os.environ.get("QTM_CONTROL_PASSWORD", "password")
        self._loaded_trial_path = None
        if not self.Client.has_transport():
            raise IOError("Unable to connect to Qualisys. If you are working entirely offline, you may need to install the Microsoft Loopback Adapter.")

    async def Connect(self, host='127.0.0.1', port=22223, version='1.25'):
        if self.IsConnected():
            return
        if self.IsConnecting:
            return
        self.IsConnecting = True
        try:
            self.Client = await qtm_rt.connect(host, port=port, version=version)
            if self.Client is None:
                raise IOError(f"Failed to connect to QTM at {host}:{port}. Check QTM status and network settings.")
        except Exception as e:
            self.Client = None
            if self.GenerateErrors:
                raise IOError(f"Unable to connect to QTM at {host}:{port}: {e}. "
                              "Ensure QTM is running and configured for real-time output.") from e
            else:
                print(f"Error connecting to QTM: {e}")
        finally:
            self.IsConnecting = False

    async def Disconnect(self):
        if self.Client.IsConnected():
            try:
                self.Client.disconnect()
                self.Client = None
            except Exception as e:
                if self.GenerateErrors:
                    raise RuntimeError(f"Error during QTM disconnection: {e}") from e
                else:
                    print(f"Error disconnecting from QTM: {e}")

    def IsConnected(self):
        return self.Client is not None and self.Client.has_transport()
    
    async def GetServerInfo(self):
        if not self.IsConnected():
            if self.GenerateErrors:
                raise RuntimeError("Not connected to QTM. Cannot get server info.")
            else:
                print("Not connected to QTM. Cannot get server info.")
                return None, None, None, None, None

        try:
            # qtm_version() returns a string like "3.0.2"
            qtm_version_str = await self.Client.qtm_version()
            print(f"Raw QTM version string: {qtm_version_str}")

            # Parse the version string
            program = "QTM"  # Default program name
            release_type = "Release" # Default release type

            major_version = 0
            minor_version = 0
            point_version = 0

            if qtm_version_str:
                version_parts = qtm_version_str.split('.')
                try:
                    if len(version_parts) > 0:
                        major_version = int(version_parts[0])
                    if len(version_parts) > 1:
                        minor_version = int(version_parts[1])
                    if len(version_parts) > 2:
                        point_version = int(version_parts[2])
                except ValueError:
                    print(f"Warning: Could not parse version string '{qtm_version_str}'. Using default values.")

            return program, major_version, minor_version, point_version, release_type

        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting QTM server info: {e}") from e
            else:
                print(f"Error getting QTM server info: {e}")
                return None, None, None, None, None
            
    async def _get_all_definitions(self):
        if not self.IsConnected():
            if self.GenerateErrors:
                raise RuntimeError("Not connected to QTM. Cannot retrieve definitions.")
            else:
                print("Not connected to QTM. Cannot retrieve definitions.")
                return {}

        definitions = {}
        param_types = ['general', '3d', '6d', 'skeleton']

        for param_type in param_types:
            try:
                xml_string = await self.Client.get_parameters(parameters=[param_type])
                if xml_string:
                    definitions[param_type] = ET.fromstring(xml_string)
                else:
                    print(f"Warning: Received empty XML string for {param_type} parameters.")
                    definitions[param_type] = None
            except Exception as e:
                print(f"Error getting or parsing {param_type} parameters XML: {e}")
                definitions[param_type] = None
        return definitions
    
    async def _get_general_parameters_xml(self):
        if not self.IsConnected():
            if self.GenerateErrors:
                raise RuntimeError("Not connected to QTM. Cannot retrieve general parameters.")
            else:
                print("Not connected to QTM. Cannot retrieve general parameters.")
                return None

        try:
            xml_string = await self.Client.get_parameters(parameters=['general'])
            if not xml_string:
                raise Exception("Received empty XML string for general parameters.")
            root = ET.fromstring(xml_string)
            return root
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting or parsing general parameters XML: {e}") from e
            else:
                print(f"Error getting or parsing general parameters XML: {e}")
                return None

    async def GetFrameCount(self):
        try:
            root = await self._get_general_parameters_xml()
            if root is None:
                return None

            # Assuming the frame count is under <General><StartFrame> and <EndFrame>
            # We need to calculate total frames from start and end.
            start_frame_elem = root.find(".//StartFrame")
            end_frame_elem = root.find(".//EndFrame")

            if start_frame_elem is not None and end_frame_elem is not None:
                start_frame = int(start_frame_elem.text)
                end_frame = int(end_frame_elem.text)
                return end_frame - start_frame + 1 # Inclusive count
            else:
                print("Warning: Could not find StartFrame or EndFrame in general parameters XML.")
                return None
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting frame count: {e}") from e
            else:
                print(f"Error getting frame count: {e}")
                return None

    async def GetFrameRate(self):
        try:
            root = await self._get_general_parameters_xml()
            if root is None:
                return None

            frequency_elem = root.find(".//Frequency")
            if frequency_elem is not None:
                return float(frequency_elem.text)
            else:
                print("Warning: Could not find Frequency in general parameters XML.")
                return None
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting frame rate: {e}") from e
            else:
                print(f"Error getting frame rate: {e}")
                return None

    async def GetTrialRange(self):
        try:
            root = await self._get_general_parameters_xml()
            if root is None:
                return None, None

            start_frame_elem = root.find(".//StartFrame")
            end_frame_elem = root.find(".//EndFrame")

            if start_frame_elem is not None and end_frame_elem is not None:
                return int(start_frame_elem.text), int(end_frame_elem.text)
            else:
                print("Warning: Could not find StartFrame or EndFrame for trial range in general parameters XML.")
                return None, None
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting trial range: {e}") from e
            else:
                print(f"Error getting trial range: {e}")
                return None, None

    async def GetTrialRangeOfInterest(self):
        try:
            root = await self._get_general_parameters_xml()
            if root is None:
                return None, None

            # Assuming ROI is nested under <General><RegionOfInterest>
            roi_start_frame_elem = root.find(".//RegionOfInterest/StartFrame")
            roi_end_frame_elem = root.find(".//RegionOfInterest/EndFrame")

            if roi_start_frame_elem is not None and roi_end_frame_elem is not None:
                return int(roi_start_frame_elem.text), int(roi_end_frame_elem.text)
            else:
                print("Warning: Could not find RegionOfInterest/StartFrame or EndFrame in general parameters XML.")
                return None, None
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting trial region of interest: {e}") from e
            else:
                print(f"Error getting trial region of interest: {e}")
                return None, None

    async def SetTrialRangeOfInterest(self, start_frame: int, end_frame: int):
        if not self.IsConnected():
            if self.GenerateErrors:
                raise RuntimeError("Not connected to QTM. Cannot set trial region of interest.")
            else:
                print("Not connected to QTM. Cannot set trial region of interest.")
                return

        try:
            print("Attempting to take control of QTM...")
            await self.Client.take_control(self._qtm_control_password)
            print("Control of QTM taken.")

            # Construct the XML to set the region of interest
            # This XML structure is based on typical QTM RT Protocol parameter setting
            xml_to_send = f"""
            <QTM_Parameters>
                <General>
                    <RegionOfInterest>
                        <StartFrame>{start_frame}</StartFrame>
                        <EndFrame>{end_frame}</EndFrame>
                    </RegionOfInterest>
                </General>
            </QTM_Parameters>
            """
            print(f"Sending XML to set ROI:\n{xml_to_send}")
            await self.Client.send_xml(xml_to_send)
            print(f"Successfully set trial region of interest to {start_frame}-{end_frame}.")

        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error setting trial region of interest: {e}") from e
            else:
                print(f"Error setting trial region of interest: {e}")
        finally:
            try:
                # Always attempt to release control
                print("Attempting to release control of QTM...")
                await self.Client.release_control()
                print("Control of QTM released.")
            except Exception as e:
                if self.GenerateErrors:
                    raise RuntimeError(f"Error releasing control of QTM: {e}") from e
                else:
                    print(f"Error releasing control of QTM: {e}")

    async def GetTrialName(self):
        if not self.IsConnected():
            if self.GenerateErrors:
                raise RuntimeError("Not connected to QTM. Cannot get trial name.")
            else:
                print("Not connected to QTM. Cannot get trial name.")
                return None, None

        try:
            root = await self._get_general_parameters_xml()
            if root is None:
                return self._loaded_trial_path, None

            trial_name_elem = root.find(".//Name") # QTM's general parameters usually have a 'Name'
            trial_name = trial_name_elem.text if trial_name_elem is not None else None

            # If the trial was loaded via this client, we might have its path
            path = self._loaded_trial_path
            if path and trial_name is None:
                # If name not found in XML but path is known, try to infer name from path
                trial_name = os.path.basename(path).replace(".qtm", "")

            return path, trial_name
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting trial name: {e}") from e
            else:
                print(f"Error getting trial name: {e}")
                return None, None

    async def _get_subject_definitions_xml(self):
        if not self.IsConnected():
            if self.GenerateErrors:
                raise RuntimeError("Not connected to QTM. Cannot retrieve subject definitions.")
            else:
                print("Not connected to QTM. Cannot retrieve subject definitions.")
                return None

        try:
            # Request '6d' parameters as they define rigid bodies, which often correspond to subjects
            xml_string = await self.Client.get_parameters(parameters=['6d'])
            if not xml_string:
                # Try 'skeleton' if '6d' is empty, as some subjects might be defined as skeletons
                xml_string = await self.Client.get_parameters(parameters=['skeleton'])
                if not xml_string:
                    raise Exception("Received empty XML string for 6D or Skeleton parameters.")

            root = ET.fromstring(xml_string)
            return root
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting or parsing subject definitions XML: {e}") from e
            else:
                print(f"Error getting or parsing subject definitions XML: {e}")
                return None

    async def GetSubjectNames(self):
        try:
            root = await self._get_subject_definitions_xml()
            if root is None:
                return []

            names = []
            # Find names from 6D bodies
            for body_elem in root.findall(".//Body"):
                name_elem = body_elem.find("Name")
                if name_elem is not None and name_elem.text:
                    names.append(name_elem.text)

            # Find names from Skeletons (if present in the same XML or if '6d' was empty)
            for skeleton_elem in root.findall(".//Skeleton"):
                name_elem = skeleton_elem.find("Name")
                if name_elem is not None and name_elem.text:
                    names.append(name_elem.text)

            # Remove duplicates if a subject is defined as both 6D body and part of a skeleton (unlikely but safe)
            return sorted(list(set(names)))
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting subject names: {e}") from e
            else:
                print(f"Error getting subject names: {e}")
                return []

    async def GetSubjectInfo(self):
        try:
            root = await self._get_subject_definitions_xml()
            if root is None:
                return [], [], []

            names = []
            templates = []
            active_states = []

            # Process 6D bodies
            for body_elem in root.findall(".//Body"):
                name_elem = body_elem.find("Name")
                if name_elem is not None and name_elem.text:
                    names.append(name_elem.text)
                    templates.append("RigidBody") # Infer template type
                    active_states.append(True) # Assume active if defined

            # Process Skeletons
            for skeleton_elem in root.findall(".//Skeleton"):
                name_elem = skeleton_elem.find("Name")
                if name_elem is not None and name_elem.text:
                    if name_elem.text not in names: # Avoid adding duplicates if a 6D body is also a skeleton root
                        names.append(name_elem.text)
                        templates.append("Skeleton") # Infer template type
                        active_states.append(True) # Assume active if defined

            return names, templates, active_states
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting subject info: {e}") from e
            else:
                print(f"Error getting subject info: {e}")
                return [], [], []

    async def SetSubjectActive(self, subject_name: str, active_state):
        """
        Attempts to set the active state of a subject by name in QTM.
        IMPORTANT NOTE: The QTM RT Protocol does NOT provide a direct equivalent
        to "activate" or "deactivate" a subject by name for streaming purposes
        in the same way Vicon Nexus does.
        This method will raise a NotImplementedError as there's no direct QTM RT command
        to achieve this granular control over subject activity.
        The concept of "active" in QTM usually relates to whether a component (e.g., 6D, skeleton)
        is enabled for streaming in the QTM project settings, not individual subjects.
        To filter subjects, it's generally done client-side after receiving data.

        Parameters:
            subject_name (str): The name of the subject.
            active_state (bool, int, or str): The desired active state.
                                              (True/False, 1/0, '1'/'0'/'Exclusive')
                                              This parameter is ignored as the functionality is not supported.

        Raises:
            NotImplementedError: Always, as this functionality is not supported by qtm-rt.
        """
        if self.GenerateErrors:
            raise NotImplementedError(
                f"Setting subject '{subject_name}' active state is not directly supported by the "
                "Qualisys RT Protocol via the qtm-rt SDK. "
                "The concept of 'active' subjects for streaming is handled differently in QTM. "
                "Consider filtering data client-side or configuring QTM project settings."
            )
        else:
            print(
                f"WARNING: Attempted to set subject '{subject_name}' active state to '{active_state}'. "
                "This functionality is not directly supported by the Qualysys RT Protocol. "
                "No action taken."
            )

    async def load_measurement(self, filename: str):
        if not self.IsConnected():
            if self.GenerateErrors:
                raise RuntimeError("Not connected to QTM. Cannot load measurement.")
            else:
                print("Not connected to QTM. Cannot load measurement.")
                return

        try:
            print("Attempting to take control of QTM...")
            await self.Client.take_control(self._qtm_control_password)
            print("Control of QTM taken.")

            print(f"Attempting to load measurement: {filename}...")
            await self.Client.load(filename)
            self._loaded_trial_path = filename # Store the path of the loaded trial
            print(f"Successfully loaded measurement: {filename}.")

        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error loading measurement: {e}") from e
            else:
                print(f"Error loading measurement: {e}")
        finally:
            try:
                print("Attempting to release control of QTM...")
                await self.Client.release_control()
                print("Control of QTM released.")
            except Exception as e:
                if self.GenerateErrors:
                    raise RuntimeError(f"Error releasing control of QTM: {e}") from e
                else:
                    print(f"Error releasing control of QTM: {e}")

    async def GetMarkerNames(self, subject_name: str):
        if not self.IsConnected():
            if self.GenerateErrors:
                raise RuntimeError("Not connected to QTM. Cannot get marker names.")
            else:
                print("Not connected to QTM. Cannot get marker names.")
                return []

        try:
            definitions = await self._get_all_definitions()
            sixd_root = definitions.get('6d')
            skeleton_root = definitions.get('skeleton')
            marker_names = []

            # Check rigid bodies
            if sixd_root:
                for body_elem in sixd_root.findall(".//Body"):
                    name_elem = body_elem.find("Name")
                    if name_elem is not None and name_elem.text == subject_name:
                        markers_elem = body_elem.find("Markers")
                        if markers_elem:
                            for marker_elem in markers_elem.findall("Marker"):
                                if marker_elem.text:
                                    marker_names.append(marker_elem.text)
                        return sorted(list(set(marker_names))) # Return unique sorted names

            # Check skeletons
            if skeleton_root:
                for skeleton_elem in skeleton_root.findall(".//Skeleton"):
                    name_elem = skeleton_elem.find("Name")
                    if name_elem is not None and name_elem.text == subject_name:
                        bones_elem = skeleton_elem.find("Bones")
                        if bones_elem:
                            for bone_elem in bones_elem.findall("Bone"):
                                markers_elem = bone_elem.find("Markers")
                                if markers_elem:
                                    for marker_elem in markers_elem.findall("Marker"):
                                        if marker_elem.text:
                                            marker_names.append(marker_elem.text)
                        return sorted(list(set(marker_names))) # Return unique sorted names

            if self.GenerateErrors:
                raise ValueError(f"Subject '{subject_name}' not found or has no associated markers in definitions.")
            else:
                print(f"Subject '{subject_name}' not found or has no associated markers.")
                return []
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting marker names for subject '{subject_name}': {e}") from e
            else:
                print(f"Error getting marker names for subject '{subject_name}': {e}")
                return []

    async def GetSegmentNames(self, subject_name: str):
        if not self.IsConnected():
            if self.GenerateErrors:
                raise RuntimeError("Not connected to QTM. Cannot get segment names.")
            else:
                print("Not connected to QTM. Cannot get segment names.")
                return []

        try:
            definitions = await self._get_all_definitions()
            sixd_root = definitions.get('6d')
            skeleton_root = definitions.get('skeleton')
            segment_names = []

            # Check rigid bodies
            if sixd_root:
                for body_elem in sixd_root.findall(".//Body"):
                    name_elem = body_elem.find("Name")
                    if name_elem is not None and name_elem.text == subject_name:
                        segment_names.append(subject_name) # The rigid body itself is a "segment"
                        return sorted(list(set(segment_names)))

            # Check skeletons
            if skeleton_root:
                for skeleton_elem in skeleton_root.findall(".//Skeleton"):
                    name_elem = skeleton_elem.find("Name")
                    if name_elem is not None and name_elem.text == subject_name:
                        bones_elem = skeleton_elem.find("Bones")
                        if bones_elem:
                            for bone_elem in bones_elem.findall("Bone"):
                                bone_name_elem = bone_elem.find("Name")
                                if bone_name_elem is not None and bone_name_elem.text:
                                    segment_names.append(bone_name_elem.text)
                        return sorted(list(set(segment_names)))

            if self.GenerateErrors:
                raise ValueError(f"Subject '{subject_name}' not found or has no associated segments.")
            else:
                print(f"Subject '{subject_name}' not found or has no associated segments.")
                return []
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting segment names for subject '{subject_name}': {e}") from e
            else:
                print(f"Error getting segment names for subject '{subject_name}': {e}")
                return []

    async def GetRootSegment(self, subject_name: str):
        if not self.IsConnected():
            if self.GenerateErrors:
                raise RuntimeError("Not connected to QTM. Cannot get root segment.")
            else:
                print("Not connected to QTM. Cannot get root segment.")
                return None

        try:
            definitions = await self._get_all_definitions()
            sixd_root = definitions.get('6d')
            skeleton_root = definitions.get('skeleton')

            # Check rigid bodies
            if sixd_root:
                for body_elem in sixd_root.findall(".//Body"):
                    name_elem = body_elem.find("Name")
                    if name_elem is not None and name_elem.text == subject_name:
                        return subject_name # Rigid body itself is the root "segment"

            # Check skeletons
            if skeleton_root:
                for skeleton_elem in skeleton_root.findall(".//Skeleton"):
                    name_elem = skeleton_elem.find("Name")
                    if name_elem is not None and name_elem.text == subject_name:
                        bones_elem = skeleton_elem.find("Bones")
                        if bones_elem:
                            # Find bone with no parent or parent 'World'
                            for bone_elem in bones_elem.findall("Bone"):
                                parent_elem = bone_elem.find("Parent")
                                if parent_elem is None or parent_elem.text in ["", "World"]:
                                    root_bone_name_elem = bone_elem.find("Name")
                                    if root_bone_name_elem is not None and root_bone_name_elem.text:
                                        return root_bone_name_elem.text
                        # If skeleton found but no root bone identified
                        if self.GenerateErrors:
                            raise ValueError(f"No root bone found for skeleton '{subject_name}'.")
                        else:
                            print(f"No root bone found for skeleton '{subject_name}'.")
                            return None

            if self.GenerateErrors:
                raise ValueError(f"Subject '{subject_name}' not found.")
            else:
                print(f"Subject '{subject_name}' not found.")
                return None
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting root segment for subject '{subject_name}': {e}") from e
            else:
                print(f"Error getting root segment for subject '{subject_name}': {e}")
                return None

    async def GetSegmentDetails(self, subject_name: str, segment_name: str):
        if not self.IsConnected():
            if self.GenerateErrors:
                raise RuntimeError("Not connected to QTM. Cannot get segment details.")
            else:
                print("Not connected to QTM. Cannot get segment details.")
                return None, [], []

        try:
            definitions = await self._get_all_definitions()
            sixd_root = definitions.get('6d')
            skeleton_root = definitions.get('skeleton')

            parent = None
            children = []
            segment_markers = []

            # Check rigid bodies
            if sixd_root:
                for body_elem in sixd_root.findall(".//Body"):
                    body_name_elem = body_elem.find("Name")
                    if body_name_elem is not None and body_name_elem.text == subject_name:
                        if subject_name == segment_name: # If the segment is the rigid body itself
                            parent = "World" # Rigid bodies are typically top-level
                            # Get markers defining this rigid body
                            markers_elem = body_elem.find("Markers")
                            if markers_elem:
                                for marker_elem in markers_elem.findall("Marker"):
                                    if marker_elem.text:
                                        segment_markers.append(marker_elem.text)
                            return parent, children, sorted(list(set(segment_markers)))

            # Check skeletons
            if skeleton_root:
                for skeleton_elem in skeleton_root.findall(".//Skeleton"):
                    skel_name_elem = skeleton_elem.find("Name")
                    if skel_name_elem is not None and skel_name_elem.text == subject_name:
                        bones_elem = skeleton_elem.find("Bones")
                        if bones_elem:
                            target_bone_elem = None
                            # Find the target segment (bone)
                            for bone_elem in bones_elem.findall("Bone"):
                                bone_name_elem = bone_elem.find("Name")
                                if bone_name_elem is not None and bone_name_elem.text == segment_name:
                                    target_bone_elem = bone_elem
                                    break

                            if target_bone_elem:
                                # Get parent
                                parent_elem = target_bone_elem.find("Parent")
                                parent = parent_elem.text if parent_elem is not None and parent_elem.text else "World"

                                # Get children
                                for bone_elem_child in bones_elem.findall("Bone"):
                                    child_parent_elem = bone_elem_child.find("Parent")
                                    if child_parent_elem is not None and child_parent_elem.text == segment_name:
                                        child_name_elem = bone_elem_child.find("Name")
                                        if child_name_elem is not None and child_name_elem.text:
                                            children.append(child_name_elem.text)

                                # Get markers for this bone
                                markers_elem = target_bone_elem.find("Markers")
                                if markers_elem:
                                    for marker_elem in markers_elem.findall("Marker"):
                                        if marker_elem.text:
                                            segment_markers.append(marker_elem.text)
                                return parent, sorted(list(set(children))), sorted(list(set(segment_markers)))
                            else:
                                if self.GenerateErrors:
                                    raise ValueError(f"Segment '{segment_name}' not found for subject '{subject_name}'.")
                                else:
                                    print(f"Segment '{segment_name}' not found for subject '{subject_name}'.")
                                    return None, [], []

            if self.GenerateErrors:
                raise ValueError(f"Subject '{subject_name}' not found.")
            else:
                print(f"Subject '{subject_name}' not found.")
                return None, [], []
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting segment details for subject '{subject_name}', segment '{segment_name}': {e}") from e
            else:
                print(f"Error getting segment details for subject '{subject_name}', segment '{segment_name}': {e}")
                return None, [], []
            
    async def GetJointNames(self, subject_name: str):
        if not self.IsConnected():
            if self.GenerateErrors:
                raise RuntimeError("Not connected to QTM. Cannot get joint names.")
            else:
                print("Not connected to QTM. Cannot get joint names.")
                return []

        try:
            definitions = await self._get_all_definitions()
            skeleton_root = definitions.get('skeleton')
            joint_names = []
            bones_map = {} # To quickly look up bone names by their element

            if skeleton_root:
                for skeleton_elem in skeleton_root.findall(".//Skeleton"):
                    name_elem = skeleton_elem.find("Name")
                    if name_elem is not None and name_elem.text == subject_name:
                        bones_elem = skeleton_elem.find("Bones")
                        if bones_elem:
                            for bone_elem in bones_elem.findall("Bone"):
                                bone_name_elem = bone_elem.find("Name")
                                if bone_name_elem is not None and bone_name_elem.text:
                                    bones_map[bone_elem] = bone_name_elem.text

                            for bone_elem in bones_elem.findall("Bone"):
                                bone_name = bones_map.get(bone_elem)
                                parent_elem = bone_elem.find("Parent")
                                if parent_elem is not None and parent_elem.text:
                                    parent_bone_name = parent_elem.text
                                    # Ensure parent bone actually exists in the skeleton
                                    if parent_bone_name in bones_map.values() or parent_bone_name == "World":
                                        joint_names.append(f"{parent_bone_name}-{bone_name}")
                        return sorted(list(set(joint_names))) # Return unique sorted names

            if self.GenerateErrors:
                raise ValueError(f"Subject '{subject_name}' not found or is not a skeleton.")
            else:
                print(f"Subject '{subject_name}' not found or is not a skeleton.")
                return []
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting joint names for subject '{subject_name}': {e}") from e
            else:
                print(f"Error getting joint names for subject '{subject_name}': {e}")
                return []

    async def GetJointDetails(self, subject_name: str, joint_name: str):
        if not self.IsConnected():
            if self.GenerateErrors:
                raise RuntimeError("Not connected to QTM. Cannot get joint details.")
            else:
                print("Not connected to QTM. Cannot get joint details.")
                return None, None

        try:
            parts = joint_name.split('-')
            if len(parts) != 2:
                if self.GenerateErrors:
                    raise ValueError(f"Invalid joint name format: '{joint_name}'. Expected 'ParentBone-ChildBone'.")
                else:
                    print(f"Invalid joint name format: '{joint_name}'. Expected 'ParentBone-ChildBone'.")
                    return None, None

            parent_candidate, child_candidate = parts[0], parts[1]

            definitions = await self._get_all_definitions()
            skeleton_root = definitions.get('skeleton')

            if skeleton_root:
                for skeleton_elem in skeleton_root.findall(".//Skeleton"):
                    name_elem = skeleton_elem.find("Name")
                    if name_elem is not None and name_elem.text == subject_name:
                        bones_elem = skeleton_elem.find("Bones")
                        if bones_elem:
                            # Verify child bone exists and its parent matches
                            for bone_elem in bones_elem.findall("Bone"):
                                bone_name_elem = bone_elem.find("Name")
                                if bone_name_elem is not None and bone_name_elem.text == child_candidate:
                                    parent_elem = bone_elem.find("Parent")
                                    current_parent = parent_elem.text if parent_elem is not None and parent_elem.text else "World"
                                    if current_parent == parent_candidate:
                                        return parent_candidate, child_candidate
                            # If we reached here, child bone with correct parent not found in this skeleton
                            if self.GenerateErrors:
                                raise ValueError(f"Joint '{joint_name}' not found for skeleton '{subject_name}'.")
                            else:
                                print(f"Joint '{joint_name}' not found for skeleton '{subject_name}'.")
                                return None, None

            if self.GenerateErrors:
                raise ValueError(f"Subject '{subject_name}' not found or is not a skeleton.")
            else:
                print(f"Subject '{subject_name}' not found or is not a skeleton.")
                return None, None
        except Exception as e:
            if self.GenerateErrors:
                raise Exception(f"Error getting joint details for subject '{subject_name}', joint '{joint_name}': {e}") from e
            else:
                print(f"Error getting joint details for subject '{subject_name}', joint '{joint_name}': {e}")
                return None, None

    async def GetModelOutputNames(self, subject_name: str):
        """
        Retrieves the names of the model outputs associated with the specified subject.
        IMPORTANT NOTE: The QTM RT Protocol does NOT provide a direct equivalent to
        "Model Outputs" as seen in Vicon Nexus (e.g., calculated kinematic/kinetic variables).
        QTM primarily streams raw data (markers, 6D bodies, analog, etc.). Any derived
        outputs are typically calculated client-side or are part of QTM's internal processing
        not directly exposed as named "model outputs" via the RT protocol.

        This method will always raise a NotImplementedError.

        Parameters:
            subject_name (str): The name of an existing subject.

        Raises:
            NotImplementedError: Always, as this functionality is not supported by qtm-rt.
        """
        if self.GenerateErrors:
            raise NotImplementedError(
                "Retrieving model output names is not directly supported by the "
                "Qualisys RT Protocol via the qtm-rt SDK. "
                "QTM primarily streams raw data components. Derived model outputs "
                "are typically calculated client-side."
            )
        else:
            print(
                f"WARNING: Attempted to get model output names for subject '{subject_name}'. "
                "This functionality is not directly supported by the Qualysys RT Protocol. "
                "No information returned."
            )
            return []

    async def GetModelOutputDetails(self, subject_name: str, model_output_name: str):
        """
        Retrieves detailed information about a model output.
        IMPORTANT NOTE: The QTM RT Protocol does NOT provide a direct equivalent to
        "Model Outputs" as seen in Vicon Nexus (e.g., calculated kinematic/kinetic variables).
        QTM primarily streams raw data (markers, 6D bodies, analog, etc.). Any derived
        outputs are typically calculated client-side or are part of QTM's internal processing
        not directly exposed as named "model outputs" via the RT protocol.

        This method will always raise a NotImplementedError.

        Parameters:
            subject_name (str): The name of an existing subject.
            model_output_name (str): The name of an existing model output.

        Raises:
            NotImplementedError: Always, as this functionality is not supported by qtm-rt.
        """
        if self.GenerateErrors:
            raise NotImplementedError(
                "Retrieving model output details is not directly supported by the "
                "Qualysys RT Protocol via the qtm-rt SDK. "
                "QTM primarily streams raw data components. Derived model outputs "
                "are typically calculated client-side."
            )
        else:
            print(
                f"WARNING: Attempted to get model output details for subject '{subject_name}', output '{model_output_name}'. "
                "This functionality is not directly supported by the Qualysys RT Protocol. "
                "No information returned."
            )
            return None, [], []

    async def GetAnalysisParamNames(self, subject_name: str):
        """
        Retrieves the names of the analysis parameters associated with the specified subject.
        IMPORTANT NOTE: The QTM RT Protocol does NOT provide a direct equivalent to
        "Analysis Parameters" as seen in Vicon Nexus (user-defined parameters with values and units).
        QTM's parameter system is more for system configuration.

        This method will always raise a NotImplementedError.

        Parameters:
            subject_name (str): The name of an existing subject.

        Raises:
            NotImplementedError: Always, as this functionality is not supported by qtm-rt.
        """
        if self.GenerateErrors:
            raise NotImplementedError(
                "Retrieving analysis parameter names is not directly supported by the "
                "Qualysys RT Protocol via the qtm-rt SDK. "
                "QTM's parameter system is primarily for system configuration, not user-defined analysis parameters."
            )
        else:
            print(
                f"WARNING: Attempted to get analysis parameter names for subject '{subject_name}'. "
                "This functionality is not directly supported by the Qualysys RT Protocol. "
                "No information returned."
            )
            return []

    async def GetAnalysisParamDetails(self, subject_name: str, param_name: str):
        """
        Retrieves detailed information about an analysis parameter (value, unit, hasvalue).
        IMPORTANT NOTE: The QTM RT Protocol does NOT provide a direct equivalent to
        "Analysis Parameters" as seen in Vicon Nexus (user-defined parameters with values and units).

        This method will always raise a NotImplementedError.

        Parameters:
            subject_name (str): The name of an existing subject.
            param_name (str): The name of an existing analysis parameter.

        Raises:
            NotImplementedError: Always, as this functionality is not supported by qtm-rt.
        """
        if self.GenerateErrors:
            raise NotImplementedError(
                "Retrieving analysis parameter details is not directly supported by the "
                "Qualysys RT Protocol via the qtm-rt SDK. "
                "QTM's parameter system is primarily for system configuration, not user-defined analysis parameters."
            )
        else:
            print(
                f"WARNING: Attempted to get analysis parameter details for subject '{subject_name}', parameter '{param_name}'. "
                "This functionality is not directly supported by the Qualysys RT Protocol. "
                "No information returned."
            )
            return None, None, False

    async def GetAnalysisParam(self, subject_name: str, param_name: str):
        """
        Retrieves the current value of an analysis parameter.
        IMPORTANT NOTE: The QTM RT Protocol does NOT provide a direct equivalent to
        "Analysis Parameters" as seen in Vicon Nexus (user-defined parameters with values and units).

        This method will always raise a NotImplementedError.

        Parameters:
            subject_name (str): The name of an existing subject.
            param_name (str): The name of an existing analysis parameter.

        Returns:
            tuple: (value, hasvalue).

        Raises:
            NotImplementedError: Always, as this functionality is not supported by qtm-rt.
        """
        if self.GenerateErrors:
            raise NotImplementedError(
                "Retrieving analysis parameter value is not directly supported by the "
                "Qualysys RT Protocol via the qtm-rt SDK. "
                "QTM's parameter system is primarily for system configuration, not user-defined analysis parameters."
            )
        else:
            print(
                f"WARNING: Attempted to get analysis parameter value for subject '{subject_name}', parameter '{param_name}'. "
                "This functionality is not directly supported by the Qualysys RT Protocol. "
                "No information returned."
            )
            return None, False

    async def SetAnalysisParam(self, subject_name: str, param_name: str, value: float):
        """
        Sets the current value of an analysis parameter.
        IMPORTANT NOTE: The QTM RT Protocol does NOT provide a direct equivalent to
        "Analysis Parameters" as seen in Vicon Nexus (user-defined parameters with values and units).

        This method will always raise a NotImplementedError.

        Parameters:
            subject_name (str): The name of an existing subject.
            param_name (str): The name of an existing analysis parameter.
            value (float): The desired value of the analysis parameter.

        Raises:
            NotImplementedError: Always, as this functionality is not supported by qtm-rt.
        """
        if self.GenerateErrors:
            raise NotImplementedError(
                "Setting analysis parameter value is not directly supported by the "
                "Qualysys RT Protocol via the qtm-rt SDK. "
                "QTM's parameter system is primarily for system configuration, not user-defined analysis parameters."
            )
        else:
            print(
                f"WARNING: Attempted to set analysis parameter '{param_name}' for subject '{subject_name}' to '{value}'. "
                "This functionality is not directly supported by the Qualysys RT Protocol. "
                "No action taken."
            )

    async def CreateAnalysisParam(self, subject_name: str, param_name: str, value: float, unit: str):
        """
        Creates a new analysis parameter for the specified subject.
        IMPORTANT NOTE: The QTM RT Protocol does NOT provide a direct equivalent to
        "Analysis Parameters" as seen in Vicon Nexus (user-defined parameters with values and units).

        This method will always raise a NotImplementedError.

        Parameters:
            subject_name (str): The name of an existing subject.
            param_name (str): The name of the new analysis parameter.
            value (float): The desired value of the analysis parameter.
            unit (str): The unit associated with the value.

        Raises:
            NotImplementedError: Always, as this functionality is not supported by qtm-rt.
        """
        if self.GenerateErrors:
            raise NotImplementedError(
                "Creating analysis parameters is not directly supported by the "
                "Qualysys RT Protocol via the qtm-rt SDK. "
                "QTM's parameter system is primarily for system configuration, not user-defined analysis parameters."
            )
        else:
            print(
                f"WARNING: Attempted to create analysis parameter '{param_name}' for subject '{subject_name}'. "
                "This functionality is not directly supported by the Qualysys RT Protocol. "
                "No action taken."
            )