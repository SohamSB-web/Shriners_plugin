# -*- coding: utf-8 -*-
"""
Gait Processing Service — wraps the existing processing scripts
(Py3_StaticMain, Py3_DynamicMain) behind a clean interface.

Uses QThread worker pattern so the UI never freezes.
"""

from __future__ import annotations

import sys
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from app.models.data_models import ProcessingStatus

logger = logging.getLogger(__name__)

_GAIT_DIR = Path(__file__).resolve().parent.parent.parent / "Gait-lab-Vicon-to-QTM"


def _resolve_python_launcher(conda_env: str) -> list[str]:
    """Find direct conda python executable to avoid conda run argument parsing and buffering bugs."""
    if conda_env.lower() in sys.executable.lower() and Path(sys.executable).is_file():
        return [sys.executable, "-u"]

    home = Path.home()
    program_data = Path(os.environ.get("ProgramData", os.environ.get("ALLUSERSPROFILE", "C:\\ProgramData")))
    candidates = [
        home / ".conda" / "envs" / conda_env / "python.exe",
        home / "miniconda3" / "envs" / conda_env / "python.exe",
        home / "anaconda3" / "envs" / conda_env / "python.exe",
        program_data / "miniconda3" / "envs" / conda_env / "python.exe",
        program_data / "anaconda3" / "envs" / conda_env / "python.exe",
    ]
    for c in candidates:
        if c.is_file():
            return [str(c), "-u"]
    return ["conda", "run", "--no-capture-output", "-n", conda_env, "python", "-u"]


class ProcessingWorker(QObject):
    """Background worker for running gait processing scripts."""

    progress = Signal(ProcessingStatus)
    log_line = Signal(str)
    finished = Signal(ProcessingStatus)
    error = Signal(str)

    def __init__(
        self,
        script_name: str,
        session_xml_path: str,
        filename: str,
        conda_env: str = "python-example",
        extra_args: list | None = None,
        interactive: bool = False,
    ):
        super().__init__()
        self.script_name = script_name
        self.session_xml_path = session_xml_path
        self.filename = filename
        self.conda_env = conda_env
        self.extra_args = extra_args or []
        self.interactive = interactive
        self._cancelled = False
        self._process: Optional[subprocess.Popen] = None

    def cancel(self):
        self._cancelled = True
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
            except Exception as e:
                logger.warning("Error terminating process: %s", e)

    def run(self):
        """Execute the processing script in the conda environment with live streaming output."""
        status = ProcessingStatus(
            step="running",
            message=f"Running {self.script_name}...",
            current_file=self.filename,
        )
        self.progress.emit(status)

        script_path = _GAIT_DIR / self.script_name
        launcher = _resolve_python_launcher(self.conda_env)
        cmd = launcher + [
            str(script_path),
            "-s", self.session_xml_path,
            "-f", self.filename,
        ] + self.extra_args

        logger.info("Running command: %s", " ".join(cmd))
        self.log_line.emit(f"Command: {' '.join(cmd)}")

        env = dict(os.environ)
        if self.interactive:
            env["SHRINERS_NON_INTERACTIVE"] = "0"
            env["SHRINERS_FORCEPLATE_INTERACTIVE"] = "1"
        else:
            env["SHRINERS_NON_INTERACTIVE"] = "1"
        env["SHRINERS_AUTO_SELECT_CYCLE"] = "1"
        if launcher[0].endswith("python.exe"):
            py_dir = os.path.dirname(launcher[0])
            lib_bin = os.path.join(py_dir, "Library", "bin")
            if os.path.isdir(lib_bin):
                env["PATH"] = lib_bin + os.pathsep + env.get("PATH", "")

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(_GAIT_DIR),
                bufsize=1,
                encoding="utf-8",
                errors="replace",
                env=env,
            )

            stdout_lines: list[str] = []
            if self._process.stdout:
                import re
                for line in iter(self._process.stdout.readline, ""):
                    if self._cancelled:
                        break
                    line_clean = line.rstrip("\r\n")
                    if line_clean:
                        stdout_lines.append(line_clean)
                        self.log_line.emit(line_clean)

                        # Parse detailed progress messages
                        if "Frame " in line_clean:
                            m = re.search(r"Frame\s+(\d+)/(\d+)", line_clean)
                            if m:
                                curr, total = int(m.group(1)), int(m.group(2))
                                pct = min(75, int(curr / max(1, total) * 75))
                                status.progress = pct
                                status.message = f"Analyzing frame {curr}/{total}"
                                self.progress.emit(status)
                        elif "FOR LOOP FINISHED" in line_clean:
                            status.progress = 80
                            status.message = "Computing kinetics and muscle dynamics..."
                            self.progress.emit(status)
                        elif "CreateGCD_Main" in line_clean:
                            status.progress = 90
                            status.message = "Generating GCD data file..."
                            self.progress.emit(status)
                        elif "[STAGE " in line_clean:
                            m_st = re.search(r"\[STAGE\s+(\d+)\]", line_clean)
                            if m_st:
                                s_idx = int(m_st.group(1))
                                st_pcts = {1: 15, 2: 30, 3: 50, 4: 70, 5: 80, 6: 90, 7: 100}
                                status.progress = st_pcts.get(s_idx, 50)
                            status.message = line_clean.strip()
                            self.progress.emit(status)
                        elif "ASIS" in line_clean or "Marker" in line_clean:
                            status.message = line_clean
                            self.progress.emit(status)

                self._process.stdout.close()

            return_code = self._process.wait()

            if self._cancelled:
                status.step = "cancelled"
                status.message = "Processing cancelled by user"
                self.finished.emit(status)
                return

            if return_code == 0:
                status.step = "complete"
                status.progress = 100
                status.message = f"{self.script_name} completed successfully"
                status.completed = True
            else:
                status.step = "error"
                status.message = f"{self.script_name} failed (exit code {return_code})"
                # Capture recent output lines for diagnostic info
                if stdout_lines:
                    status.errors = stdout_lines[-15:]
                logger.error("Script failed with code %d", return_code)

            self.finished.emit(status)

        except FileNotFoundError:
            msg = "conda executable not found. Ensure conda is installed and on PATH."
            logger.error(msg)
            self.error.emit(msg)
        except Exception as e:
            msg = f"Processing failed: {e}"
            logger.error(msg, exc_info=True)
            self.error.emit(msg)


class GaitProcessingService(QObject):
    """
    Service interface for gait data processing.

    Methods return immediately; actual processing runs on a background
    QThread. Connect to signals to receive progress, log, and completion events.
    """

    processing_started = Signal(str)    # script name
    processing_log = Signal(str)        # live stdout/stderr lines
    processing_progress = Signal(ProcessingStatus)
    processing_finished = Signal(ProcessingStatus)
    processing_error = Signal(str)

    def __init__(self, conda_env: str = "python-example", parent=None):
        super().__init__(parent)
        self.conda_env = conda_env
        self._thread: Optional[QThread] = None
        self._worker: Optional[ProcessingWorker] = None
        self._generation = 0

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def process_static(self, session_xml_path: str, filename: str, condition: str = "BF") -> None:
        """Run static calibration in a background thread (headless — no GUI window)."""
        self._run_script("Py3_StaticMain.py", session_xml_path, filename, extra_args=["-t", condition, "--headless"])

    def process_dynamic(
        self,
        session_xml_path: str,
        filename: str,
        condition: str = "BF",
        left_plate: str | None = None,
        right_plate: str | None = None,
        interactive_fp: bool = False,
    ) -> None:
        """Run dynamic analysis in a background thread with force plate options."""
        extra_args = ["-t", condition]
        if left_plate:
            extra_args.extend(["--leftPlate", left_plate])
        if right_plate:
            extra_args.extend(["--rightPlate", right_plate])
        if interactive_fp:
            extra_args.append("--interactiveFP")

        self._run_script(
            "Py3_DynamicMain.py",
            session_xml_path,
            filename,
            extra_args=extra_args,
            interactive=interactive_fp,
        )

    def run_auto_event_labeling(self, session_xml_path: str, filename: str, condition: str = "BF") -> None:
        """Run auto event labeling in a background thread."""
        self._run_script(
            "auto_event_trigger.py", session_xml_path, filename,
            extra_args=["-t", condition],
        )

    def cancel(self) -> None:
        if self._worker:
            self._worker.cancel()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)

    def invalidate(self) -> None:
        """Stop the old session's job and discard its queued output."""
        self._generation += 1
        self.cancel()

    def _run_script(
        self,
        script_name: str,
        session_xml_path: str,
        filename: str,
        extra_args: list | None = None,
        interactive: bool = False,
    ) -> None:
        if self.is_running:
            self.processing_error.emit("A processing job is already running.")
            return

        self._thread = QThread()
        generation = self._generation
        self._worker = ProcessingWorker(
            script_name, session_xml_path, filename,
            conda_env=self.conda_env,
            extra_args=extra_args,
            interactive=interactive,
        )
        self._worker.moveToThread(self._thread)

        # Wire signals
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(lambda status: self._emit_current(generation, self.processing_progress, status))
        self._worker.log_line.connect(lambda line: self._emit_current(generation, self.processing_log, line))
        self._worker.finished.connect(lambda status: self._on_finished(status, generation))
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(lambda message: self._on_error(message, generation))
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        thread = self._thread
        self._thread.finished.connect(lambda: self._release_thread(thread))

        self.processing_started.emit(script_name)
        self._thread.start()

    def _emit_current(self, generation, signal, value):
        if generation == self._generation:
            signal.emit(value)

    def _release_thread(self, thread):
        if self._thread is thread:
            self._thread = None
            self._worker = None

    def _on_finished(self, status: ProcessingStatus, generation=None) -> None:
        self._emit_current(self._generation if generation is None else generation, self.processing_finished, status)

    def _on_error(self, msg: str, generation=None) -> None:
        self._emit_current(self._generation if generation is None else generation, self.processing_error, msg)
