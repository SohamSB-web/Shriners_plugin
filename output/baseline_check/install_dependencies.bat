@echo off
rem ==========================================================================
rem  Shriners Plugin - dependency installer
rem
rem  Creates (or updates) the conda environment used by the QTM processing
rem  GUI and the MAC Case Presentation app, and installs all required
rem  packages into it.
rem
rem  Requirements: Miniconda or Anaconda installed.
rem  Run by double-clicking, or from an "Anaconda Prompt".
rem ==========================================================================
setlocal
set ENV_NAME=python-example
set PY_VERSION=3.9
cd /d "%~dp0"

where conda >nul 2>nul
if errorlevel 1 (
    echo ERROR: conda was not found.
    echo Install Miniconda from https://docs.conda.io/en/latest/miniconda.html
    echo then run this file again from the "Anaconda Prompt".
    goto :fail
)

call conda env list | findstr /r /c:"^%ENV_NAME% " >nul
if errorlevel 1 (
    echo Creating conda environment "%ENV_NAME%" with Python %PY_VERSION% ...
    call conda create -y -n %ENV_NAME% python=%PY_VERSION%
    if errorlevel 1 goto :fail
) else (
    echo Conda environment "%ENV_NAME%" already exists - installing/updating packages.
)

echo.
echo Installing ezc3d from conda-forge ...
call conda install -y -n %ENV_NAME% -c conda-forge ezc3d
if errorlevel 1 goto :fail

echo.
echo Installing Python packages from requirements.txt ...
call conda run --no-capture-output -n %ENV_NAME% python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto :fail

echo.
echo Verifying installation ...
call conda run --no-capture-output -n %ENV_NAME% python -c "import tkinter, numpy, scipy, pandas, matplotlib, lxml, xlrd, reportlab, dateutil, grpc, google.protobuf, ezc3d, qtm_rt; print('All packages imported successfully.')"
if errorlevel 1 goto :fail

echo.
echo ==========================================================================
echo  Installation complete. Environment: %ENV_NAME%
echo ==========================================================================
pause
exit /b 0

:fail
echo.
echo Installation did NOT complete. See the messages above.
pause
exit /b 1
