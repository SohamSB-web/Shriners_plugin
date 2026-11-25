# -*- coding: utf-8 -*-
"""
GCD File Service — reads / parses GCD files using the exact same logic
as the existing MAC_CasePresentation.ReadGCD function.

This service wraps the original parsing logic so the UI never needs to
know the internal format.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from app.models.data_models import GCDData, PageSettings

logger = logging.getLogger(__name__)


class GCDService:
    """Service for reading, parsing, and extracting data from GCD files."""

    # ── Core GCD Parser (preserves original logic exactly) ──────────

    @staticmethod
    def read_gcd(gcd_filename: str) -> GCDData:
        """
        Parse a GCD file and return structured data.

        This is a faithful port of the original ``ReadGCD()`` function from
        ``MAC_CasePresentation.py``, preserving all unit conversions and
        special-case handling.
        """
        result = GCDData(file_path=gcd_filename)

        if not gcd_filename or gcd_filename.endswith("--"):
            return result

        if not os.path.isfile(gcd_filename):
            logger.warning("GCD file not found: %s", gcd_filename)
            return result

        try:
            with open(gcd_filename, "r") as f:
                lines = f.readlines()
        except Exception as e:
            logger.error("Failed to read GCD file %s: %s", gcd_filename, e)
            return result

        variable_names: List[str] = []
        variable_data: List[list] = []
        variable_sd: List[list] = []
        variable_name_index = -1
        keywords = ["#", "$", "!"]
        read_text_parameter_flag = False
        gcd_variable_name = ""

        for line in lines:
            if not line.strip():
                continue

            first_char = line[0]

            # Read C3D and Static file name sections
            if first_char == "$":
                read_text_parameter_flag = True
                variable_names.append(line[1:].rstrip("\n").rstrip("\r"))
                variable_data.append([])
                variable_sd.append([])
                variable_name_index += 1

            if first_char not in keywords:
                if read_text_parameter_flag:
                    variable_data[variable_name_index].append(
                        line.rstrip("\n").rstrip("\r")
                    )
                    variable_sd[variable_name_index].append(0.0)

            # Read computed parameters
            if first_char == "!":
                read_text_parameter_flag = False
                gcd_variable_name = line.split(" ")[0][1:].rstrip()
                variable_names.append(gcd_variable_name)
                variable_data.append([])
                variable_sd.append([])
                variable_name_index += 1

            if first_char not in keywords and not read_text_parameter_flag:
                parts = line.strip().split()
                if not parts:
                    continue
                val_raw = float(parts[0]) if parts else 0.0
                sd_raw = float(parts[1]) if len(parts) > 1 else 0.0

                # Apply unit conversions matching original code
                if gcd_variable_name in (
                    "LeftStrideLength", "RightStrideLength", "StrideLength",
                    "LeftStepLength", "RightStepLength", "StepLength",
                    "LeftSpeed", "RightSpeed", "Speed",
                ):
                    variable_data[variable_name_index].append(val_raw / 1000.0)
                    variable_sd[variable_name_index].append(sd_raw / 1000.0)
                elif gcd_variable_name in ("LeftCadence", "RightCadence", "Cadence"):
                    variable_data[variable_name_index].append(2.0 * 60.0 * val_raw)
                    variable_sd[variable_name_index].append(2.0 * 60.0 * sd_raw)
                elif gcd_variable_name in (
                    "LeftOppositeFootOff", "LeftOppositeFootContact",
                    "RightOppositeFootOff", "RightOppositeFootContact",
                ):
                    variable_data[variable_name_index].append(0.0)
                    variable_sd[variable_name_index].append(0.0)
                else:
                    variable_data[variable_name_index].append(val_raw)
                    variable_sd[variable_name_index].append(sd_raw)

        # Resolve static file name to local path if possible
        if "StaticFileName" in variable_names:
            static_idx = variable_names.index("StaticFileName")
            stored_name = os.path.basename(
                str(variable_data[static_idx][0]).replace("\\", "/")
            ) if variable_data[static_idx] else ""
            local_path = os.path.join(os.path.dirname(gcd_filename), stored_name)
            if os.path.isfile(local_path):
                variable_data[static_idx] = [local_path]

        result.variable_names = variable_names
        result.variable_data = variable_data
        result.variable_sd = variable_sd
        return result

    # ── Convenience extractors ──────────────────────────────────────

    @staticmethod
    def get_variable_array(gcd: GCDData, name: str) -> Optional[np.ndarray]:
        """Return the data for *name* as a numpy array, or None."""
        return GCDService._cached_array(gcd, name, sd=False)

    @staticmethod
    def _cached_array(gcd: GCDData, name: str, sd: bool) -> Optional[np.ndarray]:
        # Owned by the loaded trial, not a global cache of historical sessions.
        data = gcd.get_variable_sd(name) if sd else gcd.get_variable(name)
        if data is None:
            return None
        cache = getattr(gcd, "_array_cache", None)
        if cache is None:
            cache = gcd._array_cache = {}
        key = (name, sd)
        signature = tuple(data)  # Detect replacement AND edits to an existing list.
        previous = cache.get(key)
        if previous is not None and previous[0] == signature:
            return previous[1]
        try:
            array = np.array(data, dtype=float)
        except (ValueError, TypeError):
            return None
        array.setflags(write=False)
        if len(cache) >= 256 and key not in cache:
            cache.clear()
        cache[key] = (signature, array)
        return array

    @staticmethod
    def get_variable_sd_array(gcd: GCDData, name: str) -> Optional[np.ndarray]:
        """Return the standard deviation for *name* as a numpy array, or None."""
        return GCDService._cached_array(gcd, name, sd=True)

    @staticmethod
    def get_gait_cycle_x() -> np.ndarray:
        """Return the shared immutable normalized gait-cycle coordinates."""
        if not hasattr(GCDService, "_gait_cycle_x"):
            GCDService._gait_cycle_x = np.arange(0, 101, dtype=float)
            GCDService._gait_cycle_x.setflags(write=False)
        return GCDService._gait_cycle_x

    @staticmethod
    def get_toe_off(gcd: GCDData, side: str) -> float:
        """Return the foot-off percentage for the given side."""
        key = f"{side}FootOff"
        data = gcd.get_variable(key)
        if data and len(data) > 0:
            return float(data[0])
        return 60.0  # default

    @staticmethod
    def get_opposite_foot_off(gcd: GCDData, side: str) -> float:
        key = f"{side}OppositeFootOff"
        data = gcd.get_variable(key)
        if data and len(data) > 0:
            return float(data[0])
        return 0.0

    @staticmethod
    def get_opposite_foot_contact(gcd: GCDData, side: str) -> float:
        key = f"{side}OppositeFootContact"
        data = gcd.get_variable(key)
        if data and len(data) > 0:
            return float(data[0])
        return 0.0

    @staticmethod
    def get_speed(gcd: GCDData, side: str) -> float:
        key = f"{side}Speed"
        data = gcd.get_variable(key)
        if data and len(data) > 0:
            return float(data[0])
        return 0.0

    @staticmethod
    def get_program_version(gcd: GCDData) -> str:
        data = gcd.get_variable("ProgramVersion")
        if data and len(data) > 0:
            return str(data[0])
        return "Unknown"

    @staticmethod
    def get_gdi(gcd: GCDData, side: str) -> Optional[float]:
        key = f"{side}GDI"
        data = gcd.get_variable(key)
        if data and len(data) > 0:
            try:
                return float(data[0])
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def has_emg(gcd: GCDData, emg_min_on: float = 0.5) -> bool:
        """Check if EMG data is meaningfully present in this GCD."""
        for name in gcd.variable_names:
            if "Raw" in name or "EMG" in name:
                data = gcd.get_variable(name)
                if data and len(data) > 1:
                    try:
                        arr = np.array(data, dtype=float)
                        if np.max(np.abs(arr)) > emg_min_on:
                            return True
                    except (ValueError, TypeError):
                        pass
        return False

    @staticmethod
    def find_norm_variable(norm_data: Optional[GCDData], var_name: str) -> Optional[str]:
        """Find matching variable in normative data by testing exact, stripped side prefixes, and normalized names."""
        if not norm_data or not var_name:
            return None
        if norm_data.has_variable(var_name):
            return var_name
        for prefix in ("Left", "Right", "L_", "R_"):
            if var_name.startswith(prefix):
                candidate = var_name[len(prefix):]
                if norm_data.has_variable(candidate):
                    return candidate
        clean_name = var_name.replace(" ", "").replace("_", "").lower()
        for v in norm_data.variable_names:
            v_clean = v.replace(" ", "").replace("_", "").lower()
            if v_clean == clean_name:
                return v
            for prefix in ("left", "right", "l", "r"):
                if clean_name.startswith(prefix) and v_clean == clean_name[len(prefix):]:
                    return v
        return None

