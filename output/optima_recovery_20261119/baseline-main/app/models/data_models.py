# -*- coding: utf-8 -*-
"""
Data models for the Shriners Gait Analysis Platform.

Plain dataclasses / typed containers that flow between the service layer
and the UI.  No Qt or Tkinter imports here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class GCDVariable:
    """A single variable extracted from a GCD file."""
    name: str
    data: list  # list of floats (101 points) or list of strings (file names)


@dataclass
class GCDData:
    """Parsed contents of one GCD file."""
    file_path: str = ""
    variable_names: List[str] = field(default_factory=list)
    variable_data: List[list] = field(default_factory=list)
    variable_sd: List[list] = field(default_factory=list)

    def get_variable(self, name: str) -> Optional[list]:
        """Return data for *name*, or ``None`` if not present."""
        if name in self.variable_names:
            idx = self.variable_names.index(name)
            return self.variable_data[idx]
        return None

    def get_variable_sd(self, name: str) -> Optional[list]:
        """Return SD data for *name*, or ``None`` if not present."""
        if name in self.variable_names and self.variable_sd:
            idx = self.variable_names.index(name)
            if idx < len(self.variable_sd):
                return self.variable_sd[idx]
        return None

    def has_variable(self, name: str) -> bool:
        return name in self.variable_names


@dataclass
class TrialInfo:
    """Metadata for one trial (left or right, 1–5)."""
    side: str = ""        # "L" or "R"
    number: int = 0       # 1–5
    gcd_filename: str = "--"
    gcd_data: Optional[GCDData] = None
    selected: bool = False

    @property
    def label(self) -> str:
        return f"{self.side}{self.number}"

    @property
    def is_loaded(self) -> bool:
        return self.gcd_filename != "--" and self.gcd_data is not None


@dataclass
class SessionInfo:
    """Represents a single clinical session row."""
    directory: str = ""
    analysis_date: str = ""
    study_type: str = "Initial"
    activity_type: str = "Walk"
    orthosis: str = ""
    assistive_device: str = ""
    static_file: str = ""
    left_trials: List[TrialInfo] = field(default_factory=list)
    right_trials: List[TrialInfo] = field(default_factory=list)
    mr_left: str = "--"
    mr_right: str = "--"

    def __post_init__(self):
        if not self.left_trials:
            self.left_trials = [
                TrialInfo(side="L", number=i) for i in range(1, 11)
            ]
        elif len(self.left_trials) < 10:
            existing_count = len(self.left_trials)
            for i in range(existing_count + 1, 11):
                self.left_trials.append(TrialInfo(side="L", number=i))

        if not self.right_trials:
            self.right_trials = [
                TrialInfo(side="R", number=i) for i in range(1, 11)
            ]
        elif len(self.right_trials) < 10:
            existing_count = len(self.right_trials)
            for i in range(existing_count + 1, 11):
                self.right_trials.append(TrialInfo(side="R", number=i))


@dataclass
class PatientInfo:
    """Patient-level metadata."""
    mrn: str = ""
    sessions: List[SessionInfo] = field(default_factory=list)


@dataclass
class AppSettings:
    """Application-wide settings, loaded from FilePathSettings etc."""
    institute_name: str = "Motion Analysis Center"
    patients_data_location: str = ""
    vicon_files_location: str = "./"
    display_settings_location: str = ""
    gdi_features_filename: str = ""
    initial_path_for_pdf: str = ""
    norm_ave_gcd_filename: str = ""
    norm_run_ave_gcd_filename: str = ""
    use_greenville_folder_structure: bool = False
    mr_or_ave: str = "MR"
    emg_min_on: float = 0.5

    # Processing & QTM settings
    conda_env_name: str = "python-example"
    qtm_grpc_location: str = ""

    # Theme
    dark_mode: bool = False


@dataclass
class QTMConnectionInfo:
    """QTM/gRPC connection state."""
    connected: bool = False
    server: str = "localhost"
    port: int = 50051
    frames: int = 0
    capture_frequency: float = 0.0
    first_frame: int = 0
    last_frame: int = 0


@dataclass
class ProcessingStatus:
    """Current state of the processing pipeline."""
    step: str = "idle"
    progress: int = 0
    message: str = ""
    current_file: str = ""
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    completed: bool = False


@dataclass
class PageSettings:
    """Display settings for one analysis page (kinematics, kinetics, etc.)."""
    left_names: List[str] = field(default_factory=list)
    right_names: List[str] = field(default_factory=list)
    titles: List[str] = field(default_factory=list)
    y_labels: List[str] = field(default_factory=list)
    upper_limits: List[float] = field(default_factory=list)
    lower_limits: List[float] = field(default_factory=list)
    y_tick_labels: List[list] = field(default_factory=list)
    unit_labels: List[str] = field(default_factory=list)
