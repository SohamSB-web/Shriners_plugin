# -*- coding: utf-8 -*-
"""
QTM & Trial Metadata Service for Shriners Gait Analysis.

Extracts dynamic trial metadata, camera frequency, frame count,
and forceplate strike comments directly from QTM (.qtm) and C3D (.c3d) files,
as well as session.xml and QTM PAF automation data.
"""

from __future__ import annotations

import logging
import os
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def parse_session_xml_comments(session_dir: Path | str) -> Dict[str, str]:
    """
    Parse session.xml in session_dir to retrieve mapping of trial filename/stem to comments.
    Comments contain forceplate strike tags (e.g. 'right', 'left', 'bad FP strike', 'no fp strike').
    """
    comments_map: Dict[str, str] = {}
    s_dir = Path(session_dir)
    xml_path = s_dir / "session.xml"
    if not xml_path.is_file():
        return comments_map

    try:
        tree = ET.parse(str(xml_path))
        root = tree.getroot()
        for m in root.findall(".//Measurement"):
            fn = m.attrib.get("Filename", "")
            c_elem = m.find(".//Fields/Comments")
            c_text = c_elem.text.strip() if c_elem is not None and c_elem.text else ""
            if fn:
                comments_map[fn] = c_text
                comments_map[Path(fn).stem] = c_text
                comments_map[fn.lower()] = c_text
                comments_map[Path(fn).stem.lower()] = c_text
    except Exception as e:
        logger.warning("Error parsing session.xml at %s: %s", xml_path, e)

    return comments_map


def extract_qtm_metadata(qtm_path: Path | str) -> Dict[str, Any]:
    """
    Directly parse a binary .qtm file (OLE2 compound document) to extract:
    - Frame count (Measurement/Frames)
    - Camera capture frequency (Measurement/Capture)
    - Forceplate strike comment (Project Metadata/Data Items)
    """
    result: Dict[str, Any] = {
        "frames": 0,
        "frequency": 0,
        "duration": 0.0,
        "comment": "",
    }
    p = Path(qtm_path)
    if not p.is_file():
        return result

    try:
        import olefile

        if not olefile.isOleFile(str(p)):
            return result

        ole = olefile.OleFileIO(str(p))

        # 1. Measurement Frames
        if ole.exists("Measurement/Frames"):
            fdata = ole.openstream("Measurement/Frames").read()
            if len(fdata) >= 16:
                result["frames"] = struct.unpack("<I", fdata[12:16])[0]

        # 2. Measurement Capture Frequency
        if ole.exists("Measurement/Capture"):
            cdata = ole.openstream("Measurement/Capture").read()
            if len(cdata) >= 16:
                freq_val = struct.unpack("<I", cdata[12:16])[0]
                if 10 <= freq_val <= 2000:
                    result["frequency"] = freq_val

        if result["frames"] > 0 and result["frequency"] > 0:
            result["duration"] = round(result["frames"] / result["frequency"], 2)

        # 3. Comment from Project Metadata/Data Items
        if ole.exists("Project Metadata/Data Items"):
            ditems = ole.openstream("Project Metadata/Data Items").read()
            # Extract UTF-16LE strings
            strings = [
                m.group().decode("utf-16le")
                for m in re.finditer(rb"(?:[\x20-\x7e]\x00){2,}", ditems)
            ]
            for s in strings:
                s_lower = s.lower().strip()
                if (
                    s_lower in [
                        "right",
                        "left",
                        "bad fp strike",
                        "no fp strike",
                        "left crouch",
                        "right crouch",
                    ]
                    or "strike" in s_lower
                    or "fp" in s_lower
                    or "crouch" in s_lower
                ):
                    result["comment"] = s.strip()
                    break

        ole.close()
    except ImportError:
        logger.debug("olefile not installed; skipping binary QTM inspection.")
    except Exception as e:
        logger.debug("Error extracting QTM metadata from %s: %s", p, e)

    return result


def extract_c3d_metadata(c3d_path: Path | str) -> Dict[str, Any]:
    """
    Extract frame count and frequency from a .c3d header.
    """
    result: Dict[str, Any] = {
        "frames": 0,
        "frequency": 0,
        "duration": 0.0,
        "comment": "",
    }
    p = Path(c3d_path)
    if not p.is_file():
        return result

    try:
        with open(p, "rb") as f:
            header = f.read(512)
        if len(header) >= 18 and header[1] == 0x50:
            first_frame, last_frame = struct.unpack("<HH", header[6:10])
            if last_frame >= first_frame:
                result["frames"] = last_frame - first_frame + 1
            rate = struct.unpack("<f", header[14:18])[0]
            if 10.0 <= rate <= 2000.0:
                result["frequency"] = int(round(rate))
            if result["frames"] > 0 and result["frequency"] > 0:
                result["duration"] = round(result["frames"] / result["frequency"], 2)
    except Exception as e:
        logger.debug("Error reading C3D header from %s: %s", p, e)

    return result


def detect_forceplate_strike(session_dir: Path, stem: str) -> str:
    """
    Biomechanical detection of forceplate strike leg (Right vs Left) from C3D analog and kinematic markers.
    Used as an automatic fallback when QTM comments were not entered by the clinician.
    """
    c3d_path = session_dir / f"{stem}.c3d"
    if not c3d_path.is_file():
        for f in session_dir.glob("*.c3d"):
            if f.stem.lower() == stem.lower():
                c3d_path = f
                break

    if not c3d_path.is_file():
        return ""

    try:
        import ezc3d
        import numpy as np

        c = ezc3d.c3d(str(c3d_path))
        if "analogs" not in c["data"] or c["data"]["analogs"].shape[1] < 3:
            return ""

        analog = c["data"]["analogs"][0]
        labels = c["parameters"].get("ANALOG", {}).get("LABELS", {}).get("value", [])
        fz_idx = 2
        for i, l in enumerate(labels):
            if "FZ" in l.upper():
                fz_idx = i
                break
        if fz_idx >= len(analog):
            return ""

        fz = analog[fz_idx]
        baseline = np.median(fz[:min(30, len(fz))])
        fz_clean = np.abs(fz - baseline)
        contact = np.where(fz_clean > 50.0)[0]
        if len(contact) == 0:
            return "no fp strike"

        mid = contact[len(contact) // 2]

        point_labels = [l.upper() for l in c["parameters"].get("POINT", {}).get("LABELS", {}).get("value", [])]
        points = c["data"]["points"]

        def find_idx(*candidates):
            for cand in candidates:
                for idx, name in enumerate(point_labels):
                    if cand in name:
                        return idx
            return -1

        r_idx = find_idx("RIGHT_HEE", "R_HEE", "RHEE", "RANK", "R_ANK", "RIGHT_ANK", "RTOE")
        l_idx = find_idx("LEFT_HEE", "L_HEE", "LHEE", "LANK", "L_ANK", "LEFT_ANK", "LTOE")

        if r_idx < 0 or l_idx < 0:
            return ""

        m_prev = max(0, mid - 1)
        m_next = min(points.shape[2] - 1, mid + 1)
        r_vel = np.linalg.norm(points[:3, r_idx, m_next] - points[:3, r_idx, m_prev])
        l_vel = np.linalg.norm(points[:3, l_idx, m_next] - points[:3, l_idx, m_prev])

        # Stance foot on plate is stationary (vel < 5 mm/frame); swing foot is moving (vel > 50 mm/frame)
        if r_vel < l_vel:
            return "right"
        else:
            return "left"
    except Exception as e:
        logger.debug("Automatic FP strike detection failed for %s: %s", stem, e)
        return ""


def natural_sort_key(filename: str) -> List[Any]:
    """Sort strings containing numbers in natural human order (e.g. Dynamic 2 before Dynamic 10)."""
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"(\d+)", filename)
    ]


def get_session_dynamic_trials(session_dir: Path | str) -> List[Dict[str, Any]]:
    """
    Discover, deduplicate, and fetch metadata for all dynamic trials in a session directory.

    Rules:
    - Deduplicate by trial stem (e.g. 'Dynamic 1.qtm' and 'Dynamic 1.c3d' become one entry,
      preferring .qtm).
    - Sort naturally by numerical suffix (Dynamic 1, Dynamic 2, ..., Dynamic 10).
    - Fetch frame count, frequency, and forceplate strike comment from .qtm, .c3d, and session.xml.
    - If comments are blank, automatically detect strike leg from forceplate contact & marker kinematics.
    """
    s_dir = Path(session_dir)
    if not s_dir.is_dir():
        return []

    # Parse session.xml comments for fast lookup
    xml_comments = parse_session_xml_comments(s_dir)

    # Group files by stem, prioritizing .qtm over .c3d
    trials_by_stem: Dict[str, Path] = {}
    for file in s_dir.glob("Dynamic*.*"):
        sfx = file.suffix.lower()
        if sfx in [".qtm", ".c3d"]:
            stem_key = file.stem.lower()
            if stem_key not in trials_by_stem or sfx == ".qtm":
                trials_by_stem[stem_key] = file

    # Fallback to Gait trials if no Dynamic trials found
    if not trials_by_stem:
        for file in s_dir.glob("Gait*.*"):
            sfx = file.suffix.lower()
            if sfx in [".qtm", ".c3d"]:
                stem_key = file.stem.lower()
                if stem_key not in trials_by_stem or sfx == ".qtm":
                    trials_by_stem[stem_key] = file

    # Sort naturally
    sorted_files = sorted(trials_by_stem.values(), key=lambda p: natural_sort_key(p.name))

    trial_list: List[Dict[str, Any]] = []
    for file_path in sorted_files:
        fname = file_path.name
        stem = file_path.stem

        # Extract metadata
        meta: Dict[str, Any]
        if file_path.suffix.lower() == ".qtm":
            meta = extract_qtm_metadata(file_path)
            # If C3D also exists and frequency was missing, try C3D
            if meta["frequency"] == 0:
                c3d_sibling = s_dir / f"{stem}.c3d"
                if c3d_sibling.is_file():
                    c3d_meta = extract_c3d_metadata(c3d_sibling)
                    if c3d_meta["frequency"] > 0:
                        meta["frequency"] = c3d_meta["frequency"]
                    if meta["frames"] == 0 and c3d_meta["frames"] > 0:
                        meta["frames"] = c3d_meta["frames"]
        else:
            meta = extract_c3d_metadata(file_path)

        # Recompute duration
        if meta["frames"] > 0 and meta["frequency"] > 0:
            meta["duration"] = round(meta["frames"] / meta["frequency"], 2)

        # Comment resolution: QTM file > session.xml > Biomechanical C3D detection
        comment = meta.get("comment", "")
        if not comment:
            comment = xml_comments.get(fname, "") or xml_comments.get(stem, "")
        if not comment:
            comment = detect_forceplate_strike(s_dir, stem)

        # Determine activity and strike display text
        c_lower = comment.lower()
        activity = "Crouch Walking" if "crouch" in c_lower else "Walking"

        # Format metadata display string
        frames = meta.get("frames", 0)
        freq = meta.get("frequency", 0)
        dur = meta.get("duration", 0.0)

        meta_parts: List[str] = []
        if frames > 0:
            meta_parts.append(f"{frames} frames")
        if freq > 0:
            meta_parts.append(f"{freq} Hz")
        if dur > 0:
            meta_parts.append(f"{dur:.2f}s")
        meta_parts.append(activity)

        metadata_str = " • ".join(meta_parts) if meta_parts else f"Walking trial ({fname})"

        trial_list.append({
            "filename": fname,
            "stem": stem,
            "filepath": str(file_path),
            "frames": frames,
            "frequency": freq,
            "duration": dur,
            "comment": comment,
            "activity": activity,
            "metadata_str": metadata_str,
        })

    return trial_list
