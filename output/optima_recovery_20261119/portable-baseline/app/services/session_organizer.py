# -*- coding: utf-8 -*-
"""
Session Organizer Service — manages organized subfolders for all generated files
in a clinical gait analysis session.

Directory layout per session:
    <Session_Directory>/
        session.xml
        *.qtm, *.c3d, data.qpr         (Raw trial acquisition data)
        Events/                        (Auto event detection results & logs)
            auto_event_<trial>_results.json
            auto_event_<trial>.log
        GCD/                           (Kinematics, kinetics, and GDI waveforms)
            <trial>.GCD
        Calibration/                   (Static & sitting foot calibration models)
            Static_<condition>_<subject>.py
            SittingFootStatic_<condition>_<subject>.py
            TempPelfix*.py
        Reports/                       (Clinical case presentations & exported PDFs)
            Gait_Analysis_Report_*.pdf
        Logs/                          (General processing logs)
            processing_*.log
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Standard folder names
FOLDER_EVENTS = "Events"
FOLDER_GCD = "GCD"
FOLDER_CALIBRATION = "Calibration"
FOLDER_REPORTS = "Reports"
FOLDER_LOGS = "Logs"


def get_events_dir(session_dir: str | Path, create: bool = True) -> Path:
    """Return the Events/ subfolder path, optionally creating it."""
    p = Path(session_dir) / FOLDER_EVENTS
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def get_gcd_dir(session_dir: str | Path, create: bool = True) -> Path:
    """Return the GCD/ subfolder path, optionally creating it."""
    p = Path(session_dir) / FOLDER_GCD
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def get_calibration_dir(session_dir: str | Path, create: bool = True) -> Path:
    """Return the Calibration/ subfolder path, optionally creating it."""
    p = Path(session_dir) / FOLDER_CALIBRATION
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def get_reports_dir(session_dir: str | Path, create: bool = True) -> Path:
    """Return the Reports/ subfolder path, optionally creating it."""
    p = Path(session_dir) / FOLDER_REPORTS
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def get_logs_dir(session_dir: str | Path, create: bool = True) -> Path:
    """Return the Logs/ subfolder path, optionally creating it."""
    p = Path(session_dir) / FOLDER_LOGS
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_session_subfolders(session_dir: str | Path) -> None:
    """Ensure all standard session subfolders exist."""
    s_dir = Path(session_dir)
    if not s_dir.is_dir():
        return
    get_events_dir(s_dir, create=True)
    get_gcd_dir(s_dir, create=True)
    get_calibration_dir(s_dir, create=True)
    get_reports_dir(s_dir, create=True)


def find_event_results_file(session_dir: str | Path, trial_stem: str) -> Optional[Path]:
    """
    Locate an auto-event results JSON file for a given trial stem.
    Searches in Events/ first, then falls back to session_dir.
    """
    s_dir = Path(session_dir)
    clean_stem = Path(trial_stem).stem
    candidates = [
        s_dir / FOLDER_EVENTS / f"auto_event_{clean_stem}_results.json",
        s_dir / FOLDER_EVENTS / f"auto_event_{clean_stem.lower()}_results.json",
        s_dir / f"auto_event_{clean_stem}_results.json",
        s_dir / f"auto_event_{clean_stem.lower()}_results.json",
    ]
    for c in candidates:
        if c.is_file():
            return c

    # Fallback to normalized matching
    norm_target = re.sub(r'[\s_\-]+', ' ', clean_stem.lower()).strip()
    search_dirs = [s_dir / FOLDER_EVENTS, s_dir]
    for d in search_dirs:
        if not d.is_dir():
            continue
        for f in d.glob("auto_event_*_results.json"):
            m = re.match(r"^auto_event_(.+)_results$", f.stem, re.IGNORECASE)
            if m:
                cand_norm = re.sub(r'[\s_\-]+', ' ', m.group(1).lower()).strip()
                if cand_norm == norm_target:
                    return f

    return None


def find_gcd_file(session_dir: str | Path, trial_stem: str) -> Optional[Path]:
    """
    Locate a GCD file for a given trial stem.
    Searches in GCD/ first, then falls back to session_dir.
    """
    s_dir = Path(session_dir)
    clean_stem = Path(trial_stem).stem
    candidates = [
        s_dir / FOLDER_GCD / f"{clean_stem}.GCD",
        s_dir / FOLDER_GCD / f"{clean_stem}.gcd",
        s_dir / f"{clean_stem}.GCD",
        s_dir / f"{clean_stem}.gcd",
    ]
    for c in candidates:
        if c.is_file():
            return c

    norm_target = clean_stem.lower().strip()
    for d in [s_dir / FOLDER_GCD, s_dir]:
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.is_file() and f.suffix.lower() == ".gcd" and f.stem.lower().strip() == norm_target:
                return f

    return None


def find_all_gcd_files(session_dir: str | Path) -> List[Path]:
    """
    Find all GCD files for a session, checking GCD/ first, followed by session_dir.
    Returns a deduplicated list with files in GCD/ prioritized.
    """
    s_dir = Path(session_dir)
    if not s_dir.is_dir():
        return []

    gcd_dir = s_dir / FOLDER_GCD
    seen_stems: set[str] = set()
    results: List[Path] = []

    # Priority 1: GCD/ folder
    if gcd_dir.is_dir():
        for f in sorted(gcd_dir.iterdir()):
            if f.is_file() and f.suffix.lower() == ".gcd":
                seen_stems.add(f.stem.lower())
                results.append(f)

    # Priority 2: Session root (fallback)
    for f in sorted(s_dir.iterdir()):
        if f.is_file() and f.suffix.lower() == ".gcd":
            if f.stem.lower() not in seen_stems:
                seen_stems.add(f.stem.lower())
                results.append(f)

    return results


def find_static_calibration_files(session_dir: str | Path, subject_name: str = "") -> List[Path]:
    """
    Find all static calibration (Static_*.py) files for a session, checking
    Calibration/ first, followed by session_dir.
    """
    s_dir = Path(session_dir)
    if not s_dir.is_dir():
        return []

    calib_dir = s_dir / FOLDER_CALIBRATION
    candidates: List[Path] = []

    if subject_name:
        if calib_dir.is_dir():
            candidates.append(calib_dir / f"Static_BF_{subject_name}.py")
            candidates.append(calib_dir / f"Static_{subject_name}.py")
        candidates.append(s_dir / f"Static_BF_{subject_name}.py")
        candidates.append(s_dir / f"Static_{subject_name}.py")

    if calib_dir.is_dir():
        for f in sorted(calib_dir.glob("Static_*.py")):
            if f not in candidates:
                candidates.append(f)

    for f in sorted(s_dir.glob("Static_*.py")):
        if f not in candidates:
            candidates.append(f)

    # Filter to existing files, sorted by mtime descending
    existing = [c for c in candidates if c.is_file()]
    existing.sort(key=lambda p: p.stat().st_mtime_ns, reverse=True)
    return existing


def organize_session_directory(session_dir: str | Path) -> Dict[str, List[str]]:
    """
    Move existing loose generated files from the session root into their proper
    subfolders (Events/, GCD/, Calibration/, Reports/).

    Leaves raw capture files (*.qtm, *.c3d, session.xml, data.qpr, *.paf) untouched in the session root.

    Returns:
        Dictionary mapping category names to lists of moved file basenames.
    """
    s_dir = Path(session_dir)
    if not s_dir.is_dir():
        return {"events": [], "gcd": [], "calibration": [], "reports": []}

    ensure_session_subfolders(s_dir)
    events_dir = s_dir / FOLDER_EVENTS
    gcd_dir = s_dir / FOLDER_GCD
    calib_dir = s_dir / FOLDER_CALIBRATION
    reports_dir = s_dir / FOLDER_REPORTS

    moved: Dict[str, List[str]] = {
        "events": [],
        "gcd": [],
        "calibration": [],
        "reports": [],
    }

    # Iterate over files directly in session root
    for entry in list(s_dir.iterdir()):
        if not entry.is_file():
            continue

        name = entry.name
        name_lower = name.lower()

        # 1. Auto Event files -> Events/
        if (
            name_lower.startswith("auto_event_")
            and (name_lower.endswith(".json") or name_lower.endswith(".log"))
        ):
            target = events_dir / name
            try:
                if target.exists() and target != entry:
                    target.unlink()
                shutil.move(str(entry), str(target))
                moved["events"].append(name)
                logger.info("Organized event file: %s -> %s", name, target)
            except Exception as e:
                logger.warning("Could not move %s to %s: %s", name, target, e)

        # 2. GCD files -> GCD/
        elif name_lower.endswith(".gcd"):
            target = gcd_dir / name
            try:
                if target.exists() and target != entry:
                    target.unlink()
                shutil.move(str(entry), str(target))
                moved["gcd"].append(name)
                logger.info("Organized GCD file: %s -> %s", name, target)
            except Exception as e:
                logger.warning("Could not move %s to %s: %s", name, target, e)

        # 3. Static Calibration files -> Calibration/
        elif (
            name.startswith("Static_")
            or name.startswith("SittingFootStatic_")
            or name.startswith("TempPelfix")
        ) and name_lower.endswith(".py"):
            target = calib_dir / name
            try:
                if target.exists() and target != entry:
                    target.unlink()
                shutil.move(str(entry), str(target))
                moved["calibration"].append(name)
                logger.info("Organized calibration file: %s -> %s", name, target)
            except Exception as e:
                logger.warning("Could not move %s to %s: %s", name, target, e)

        # 4. Report PDFs -> Reports/
        elif name_lower.endswith(".pdf") and (
            "report" in name_lower or "presentation" in name_lower or "gait" in name_lower
        ):
            target = reports_dir / name
            try:
                if target.exists() and target != entry:
                    target.unlink()
                shutil.move(str(entry), str(target))
                moved["reports"].append(name)
                logger.info("Organized report PDF: %s -> %s", name, target)
            except Exception as e:
                logger.warning("Could not move %s to %s: %s", name, target, e)

    return moved
