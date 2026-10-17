# -*- coding: utf-8 -*-
"""
Settings Service — loads the existing ``*PageSettings.py`` and
``FilePathSettings.py`` configuration files.

The originals use ``exec()`` with ``self.`` prefixed attributes.
This service replicates that mechanism safely by executing settings code
within a temporary namespace object, then copying the results into typed
data models.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from app.models.data_models import AppSettings, PageSettings

logger = logging.getLogger(__name__)

# ── Base directories ─────────
_MAC_DIR = Path(__file__).resolve().parent.parent.parent / "MAC_CasePresentation"
_GAIT_DIR = Path(__file__).resolve().parent.parent.parent / "Gait-lab-Vicon-to-QTM"
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DATA_DIR = _PROJECT_ROOT / "Shriners_Gait_Model_PAF_v1.0" / "Shriners_Gait_Model_PAF_v1.0" / "Data"
_DEFAULT_QTM_DIR = _PROJECT_ROOT / "QTM-GRPC"


class _SettingsNamespace:
    """Temporary ``self`` target for exec'd settings files."""
    pass


class SettingsService:
    """Loads and manages application settings from the existing config files."""

    def __init__(self):
        self._app_settings: Optional[AppSettings] = None
        self._kinematics: Optional[PageSettings] = None
        self._sagittal_kinetics: Optional[PageSettings] = None
        self._coronal_kinetics: Optional[PageSettings] = None
        self._emg: Optional[PageSettings] = None
        self._foot_kinematics: Optional[PageSettings] = None
        self._muscle_length: Optional[PageSettings] = None
        self._muscle_velocity: Optional[PageSettings] = None
        self._muscle_length_velocity: Optional[PageSettings] = None
        self._run_pages: Optional[_SettingsNamespace] = None

    # ── App-level settings from FilePathSettings.py ─────────────

    def load_app_settings(self) -> AppSettings:
        """Load and return application settings from FilePathSettings.py."""
        if self._app_settings is not None:
            return self._app_settings

        settings = AppSettings()
        file_path = _MAC_DIR / "FilePathSettings.py"

        if file_path.is_file():
            try:
                ns = {"__file__": str(file_path), "__builtins__": __builtins__}
                exec(compile(file_path.read_text(encoding="utf-8"), str(file_path), "exec"), ns)

                settings.institute_name = ns.get("InstituteName", settings.institute_name)
                
                pdata = ns.get("PatientsDataLocation", "")
                if pdata and str(pdata).strip():
                    settings.patients_data_location = str(pdata).strip()

                settings.vicon_files_location = ns.get("ViconFilesLocation", settings.vicon_files_location)

                dsl = ns.get("DisplaySettingsFileLocation", "")
                settings.display_settings_location = str(dsl) if dsl else str(_MAC_DIR / "DisplaySettingsLocation")

                gdi = ns.get("GDIFeaturesFileName", "")
                settings.gdi_features_filename = str(gdi) if gdi else ""

                pdf = ns.get("InitialPathForPdf", "")
                settings.initial_path_for_pdf = str(pdf) if pdf else ""

                norm = ns.get("NormAveGCDFileName", "")
                settings.norm_ave_gcd_filename = str(norm) if norm else ""

                norm_run = ns.get("NormRunAveGCDFileName", "")
                settings.norm_run_ave_gcd_filename = str(norm_run) if norm_run else ""

                qtm_grpc = ns.get("QtmGrpcLocation", "")
                if qtm_grpc and str(qtm_grpc).strip():
                    settings.qtm_grpc_location = str(qtm_grpc).strip()

                settings.use_greenville_folder_structure = ns.get("UseGreenvilleFolderStructure", False)
                settings.mr_or_ave = ns.get("MRorAve", "MR")
                settings.emg_min_on = ns.get("EMG_MinOn", 0.5)

                logger.info("Loaded app settings from %s", file_path)
            except Exception as e:
                logger.error("Failed to load FilePathSettings.py: %s", e)

        # Fallback to bundled project defaults if missing or pointing to non-existent foreign directory
        if not settings.patients_data_location or not os.path.isdir(settings.patients_data_location):
            if _DEFAULT_DATA_DIR.is_dir():
                settings.patients_data_location = str(_DEFAULT_DATA_DIR)

        if not settings.qtm_grpc_location or not os.path.isdir(settings.qtm_grpc_location):
            if _DEFAULT_QTM_DIR.is_dir():
                settings.qtm_grpc_location = str(_DEFAULT_QTM_DIR)

        if not settings.display_settings_location or not os.path.isdir(settings.display_settings_location):
            settings.display_settings_location = str(_MAC_DIR / "DisplaySettingsLocation")

        if not settings.gdi_features_filename or not os.path.isfile(settings.gdi_features_filename):
            settings.gdi_features_filename = str(_MAC_DIR / "mmc1-Shriners.xls")

        if not settings.initial_path_for_pdf:
            settings.initial_path_for_pdf = str(_MAC_DIR / "MAC PATIENT RECORDS")

        if not settings.norm_ave_gcd_filename or not os.path.isfile(settings.norm_ave_gcd_filename):
            settings.norm_ave_gcd_filename = str(_MAC_DIR / "TD_Ave.GCD")

        if not settings.norm_run_ave_gcd_filename or not os.path.isfile(settings.norm_run_ave_gcd_filename):
            settings.norm_run_ave_gcd_filename = str(_MAC_DIR / "TD_Run_Ave.GCD")

        self._app_settings = settings
        return settings

    def sync_qtm_grpc_to_gapi(self, qtm_grpc_dir: str) -> bool:
        """
        Directly update the QTM-GRPC directory path in Gait-lab-Vicon-to-QTM/gapi.py
        and related bridge files. If pointing to the project-local QTM-GRPC, uses
        dynamic path resolution without hardcoded machine paths.
        """
        if not qtm_grpc_dir or not str(qtm_grpc_dir).strip():
            return False

        is_bundled = False
        try:
            is_bundled = (Path(qtm_grpc_dir).resolve() == _DEFAULT_QTM_DIR.resolve())
        except Exception:
            is_bundled = False

        target_files = [
            (_PROJECT_ROOT / "Gait-lab-Vicon-to-QTM" / "gapi.py", 'this_dir = str(Path(__file__).resolve().parent.parent / "QTM-GRPC")'),
            (_PROJECT_ROOT / "QTM-GRPC" / "gapi.py", 'this_dir = str(Path(__file__).resolve().parent)'),
            (_PROJECT_ROOT / "Shriners_Gait_Model_PAF_v1.0" / "Shriners_Gait_Model_PAF_v1.0" / "Templates" / "gapi.py", 'this_dir = str(Path(__file__).resolve().parent.parent.parent / "QTM-GRPC")'),
        ]

        # If custom external directory, escape properly
        s = str(qtm_grpc_dir).strip().replace("/", "\\")
        while "\\\\" in s:
            s = s.replace("\\\\", "\\")
        s = s.rstrip("\\")
        target_gapi_path = s + "\\gapi.py"
        double_slashed_path = target_gapi_path.replace("\\", "\\\\")
        external_line = f'this_dir = os.path.dirname(os.path.abspath("{double_slashed_path}"))'

        updated_any = False
        for f, bundled_line in target_files:
            if not f.is_file():
                continue
            rep_line = bundled_line if is_bundled else external_line
            try:
                content = f.read_text(encoding="utf-8")
                lines = content.splitlines(keepends=True)
                new_lines = []
                file_modified = False
                for line in lines:
                    stripped = line.strip()
                    if (
                        stripped.startswith("this_dir = os.path.dirname(os.path.abspath(")
                        or stripped.startswith("this_dir = str(Path(__file__)")
                        or stripped.startswith("this_dir = str(_PROJECT_ROOT")
                    ) and ("gapi.py" in stripped or "QTM-GRPC" in stripped):
                        ending = "\r\n" if line.endswith("\r\n") else "\n"
                        new_lines.append(rep_line + ending)
                        file_modified = True
                    else:
                        new_lines.append(line)

                if file_modified:
                    new_content = "".join(new_lines)
                    if new_content != content:
                        f.write_text(new_content, encoding="utf-8")
                        logger.info("Updated QTM-GRPC directory in %s", f)
                        updated_any = True
            except Exception as e:
                logger.error("Failed to update QTM-GRPC path in %s: %s", f, e)

        return updated_any

    def save_app_settings(self, settings: AppSettings) -> bool:
        """Persist application settings to FilePathSettings.py and sync gapi.py directly."""
        file_path = _MAC_DIR / "FilePathSettings.py"

        def _repr_or_rel(path_str: str, default_rel_code: str, expected_path: Path) -> str:
            if not path_str:
                return default_rel_code
            try:
                p = Path(path_str).resolve()
                if p == expected_path.resolve():
                    return default_rel_code
            except Exception:
                pass
            return repr(path_str)

        data_code = _repr_or_rel(
            settings.patients_data_location,
            'str(PROJECT_ROOT / "Shriners_Gait_Model_PAF_v1.0" / "Shriners_Gait_Model_PAF_v1.0" / "Data")',
            _DEFAULT_DATA_DIR,
        )
        qtm_code = _repr_or_rel(
            settings.qtm_grpc_location,
            'str(PROJECT_ROOT / "QTM-GRPC")',
            _DEFAULT_QTM_DIR,
        )
        disp_code = _repr_or_rel(
            settings.display_settings_location,
            'str(MAC_DIR / "DisplaySettingsLocation")',
            _MAC_DIR / "DisplaySettingsLocation",
        )
        gdi_code = _repr_or_rel(
            settings.gdi_features_filename,
            'str(MAC_DIR / "mmc1-Shriners.xls")',
            _MAC_DIR / "mmc1-Shriners.xls",
        )
        pdf_code = _repr_or_rel(
            settings.initial_path_for_pdf,
            'str(MAC_DIR / "MAC PATIENT RECORDS")',
            _MAC_DIR / "MAC PATIENT RECORDS",
        )
        norm_code = _repr_or_rel(
            settings.norm_ave_gcd_filename,
            'str(MAC_DIR / "TD_Ave.GCD")',
            _MAC_DIR / "TD_Ave.GCD",
        )
        norm_run_code = _repr_or_rel(
            settings.norm_run_ave_gcd_filename,
            'str(MAC_DIR / "TD_Run_Ave.GCD")',
            _MAC_DIR / "TD_Run_Ave.GCD",
        )

        try:
            content = f'''from pathlib import Path

MAC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MAC_DIR.parent

# Institute Name that is printed on top of pdf pages
InstituteName   = {repr(settings.institute_name)}
# Global path for Patients Data directory containing patient folders and sessions
PatientsDataLocation = {data_code}
# Initial Path for where Vicon session GCD files are located 
ViconFilesLocation = {repr(settings.vicon_files_location)}
# Path for where File selection and other information will be stored 
DisplaySettingsFileLocation = {disp_code}
# For GDI Features File Names. GDI is computed if not found in GCD file.
GDIFeaturesFileName = {gdi_code}
# Initial Path for where Pdf can be stored.
InitialPathForPdf = {pdf_code}
# Path for walking norm GCD
NormAveGCDFileName = {norm_code}
# Path for running norm GCD
NormRunAveGCDFileName = {norm_run_code}
# Path for QTM-GRPC directory
QtmGrpcLocation = {qtm_code}
# Flag for whether to use Greenville Folder Structure for storing Pdfs
UseGreenvilleFolderStructure = {repr(settings.use_greenville_folder_structure)}
# Default selection for Whether to use MostRepresentative (MR) or Average (Ave) trial for kinematics. It can be changed in GUI.
MRorAve = {repr(settings.mr_or_ave)}
# Minimum Value when EMG is assumed to be available in GCD data
EMG_MinOn = {settings.emg_min_on}
'''
            file_path.write_text(content, encoding="utf-8")
            self._app_settings = settings
            logger.info("Saved app settings to %s", file_path)

            # Directly update Gait-lab-Vicon-to-QTM/gapi.py with the configured path
            if settings.qtm_grpc_location:
                self.sync_qtm_grpc_to_gapi(settings.qtm_grpc_location)

            return True
        except Exception as e:
            logger.error("Failed to save FilePathSettings.py: %s", e)
            return False

    # ── Page-level settings ──────────────────────────────────────

    def _load_page_file(self, filename: str) -> _SettingsNamespace:
        """Execute a page settings file against a namespace and return it."""
        ns = _SettingsNamespace()
        file_path = _MAC_DIR / filename
        if file_path.is_file():
            try:
                code = file_path.read_text(encoding="utf-8")
                exec(compile(code, str(file_path), "exec"), {"self": ns})
                logger.info("Loaded page settings from %s", file_path)
            except Exception as e:
                logger.error("Failed to load %s: %s", filename, e)
        else:
            logger.warning("Settings file not found: %s", file_path)
        return ns

    def _ns_to_page_settings(
        self,
        ns: _SettingsNamespace,
        left_attr: str,
        right_attr: str,
        titles_attr: str,
        ylabels_attr: str,
        upper_attr: str,
        lower_attr: str,
        yticks_attr: str,
        units_attr: str = "",
    ) -> PageSettings:
        ps = PageSettings()
        ps.left_names = getattr(ns, left_attr, [])
        ps.right_names = getattr(ns, right_attr, [])
        ps.titles = getattr(ns, titles_attr, [])
        ps.y_labels = getattr(ns, ylabels_attr, [])
        ps.upper_limits = getattr(ns, upper_attr, [])
        ps.lower_limits = getattr(ns, lower_attr, [])
        ps.y_tick_labels = getattr(ns, yticks_attr, [])
        if units_attr:
            ps.unit_labels = getattr(ns, units_attr, [])
        return ps

    def get_kinematics_settings(self) -> PageSettings:
        if self._kinematics is None:
            ns = self._load_page_file("KinematicsPageSettings.py")
            self._kinematics = self._ns_to_page_settings(
                ns,
                "LeftAngleNames", "RightAngleNames", "AngleTitles", "AnglesYLabels",
                "AngleUpperLimit", "AngleLowerLimit", "YAxisTickLabels", "AnglesUnitLabels",
            )
        return self._kinematics

    def get_sagittal_kinetics_settings(self) -> PageSettings:
        if self._sagittal_kinetics is None:
            ns = self._load_page_file("SagittalKineticsPageSettings.py")
            self._sagittal_kinetics = self._ns_to_page_settings(
                ns,
                "LeftSagittalKineticsNames", "RightSagittalKineticsNames",
                "SagittalKineticsTitles", "SagittalKineticsYLabels",
                "SagittalKineticsUpperLimit", "SagittalKineticsLowerLimit",
                "SagittalKineticsYAxisTickLabels", "SagittalKineticsUnitLabels",
            )
        return self._sagittal_kinetics

    def get_coronal_kinetics_settings(self) -> PageSettings:
        if self._coronal_kinetics is None:
            ns = self._load_page_file("CoronalKineticsPageSettings.py")
            self._coronal_kinetics = self._ns_to_page_settings(
                ns,
                "LeftCoronalKineticsNames", "RightCoronalKineticsNames",
                "CoronalKineticsTitles", "CoronalKineticsYLabels",
                "CoronalKineticsUpperLimit", "CoronalKineticsLowerLimit",
                "CoronalKineticsYAxisTickLabels", "CoronalKineticsUnitLabels",
            )
        return self._coronal_kinetics

    def get_emg_settings(self) -> PageSettings:
        if self._emg is None:
            ns = self._load_page_file("EMGPageSettings.py")
            ps = PageSettings()
            ps.left_names = getattr(ns, "LeftEMGNames", [])
            ps.right_names = getattr(ns, "RightEMGNames", [])
            ps.titles = getattr(ns, "EMGTitles", [])
            ps.upper_limits = getattr(ns, "EMGUpperLimit", [])
            ps.lower_limits = getattr(ns, "EMGLowerLimit", [])
            ps.y_tick_labels = getattr(ns, "EMGYAxisTickLabels", [])
            self._emg = ps
        return self._emg

    def get_emg_on_off_bars(self):
        """Return (start, end) arrays for EMG activation bars."""
        ns = self._load_page_file("EMGPageSettings.py")
        return (
            getattr(ns, "EMGOnOffBarStart", []),
            getattr(ns, "EMGOnOffBarEnd", []),
        )

    def get_foot_kinematics_settings(self) -> PageSettings:
        if self._foot_kinematics is None:
            ns = self._load_page_file("FootKinematicsPageSettings.py")
            l_key = "LeftFootAngleNames" if hasattr(ns, "LeftFootAngleNames") else "LeftFootKinematicsNames"
            r_key = "RightFootAngleNames" if hasattr(ns, "RightFootAngleNames") else "RightFootKinematicsNames"
            t_key = "FootAngleTitles" if hasattr(ns, "FootAngleTitles") else "FootKinematicsTitles"
            y_key = "FootAnglesYLabels" if hasattr(ns, "FootAnglesYLabels") else "FootKinematicsYLabels"
            u_key = "FootAngleUpperLimit" if hasattr(ns, "FootAngleUpperLimit") else "FootKinematicsUpperLimit"
            low_key = "FootAngleLowerLimit" if hasattr(ns, "FootAngleLowerLimit") else "FootKinematicsLowerLimit"
            tick_key = "FootYAxisTickLabels" if hasattr(ns, "FootYAxisTickLabels") else "FootKinematicsYAxisTickLabels"
            self._foot_kinematics = self._ns_to_page_settings(
                ns, l_key, r_key, t_key, y_key, u_key, low_key, tick_key,
            )
        return self._foot_kinematics

    def get_muscle_length_settings(self) -> PageSettings:
        if self._muscle_length is None:
            ns = self._load_page_file("MuscleLengthPageSettings.py")
            self._muscle_length = self._ns_to_page_settings(
                ns,
                "LeftMuscleLengthNames", "RightMuscleLengthNames",
                "MuscleLengthTitles", "MuscleLengthYLabels",
                "MuscleLengthUpperLimit", "MuscleLengthLowerLimit",
                "MuscleLengthYAxisTickLabels",
            )
        return self._muscle_length

    def get_muscle_velocity_settings(self) -> PageSettings:
        if self._muscle_velocity is None:
            ns = self._load_page_file("MuscleVelocityPageSettings.py")
            self._muscle_velocity = self._ns_to_page_settings(
                ns,
                "LeftMuscleVelocityNames", "RightMuscleVelocityNames",
                "MuscleVelocityTitles", "MuscleVelocityYLabels",
                "MuscleVelocityUpperLimit", "MuscleVelocityLowerLimit",
                "MuscleVelocityYAxisTickLabels",
            )
        return self._muscle_velocity

    def get_muscle_length_velocity_settings(self) -> PageSettings:
        if self._muscle_length_velocity is None:
            ns = self._load_page_file("MuscleLengthVelocityPageSettings.py")
            self._muscle_length_velocity = self._ns_to_page_settings(
                ns,
                "LeftMuscleLengthVelocityNames", "RightMuscleLengthVelocityNames",
                "MuscleLengthVelocityTitles", "MuscleLengthVelocityYLabels",
                "MuscleLengthVelocityUpperLimit", "MuscleLengthVelocityLowerLimit",
                "MuscleLengthVelocityYAxisTickLabels",
            )
        return self._muscle_length_velocity

    def get_run_pages_settings(self) -> _SettingsNamespace:
        """Return raw namespace for the RunPagesSettings (used by PDF)."""
        if self._run_pages is None:
            self._run_pages = self._load_page_file("RunPagesSettings.py")
        return self._run_pages
