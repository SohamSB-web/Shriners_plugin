@echo off
cd /d "%~dp0"
rem Use the conda environment created by install_dependencies.bat, if available
where conda >nul 2>nul && call conda activate python-example >nul 2>nul
python "%~dp0MAC_CasePresentation.py"
if errorlevel 1 (
    echo.
    echo MAC_CasePresentation.py exited with an error. See above for details.
    pause
)
