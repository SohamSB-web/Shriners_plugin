@echo off
setlocal
python "%~dp0prepare_optima_export.py" "%CD%\session.xml"
if errorlevel 1 (
    echo The QTM export did not complete. Check the message above before retrying.
    pause
    exit /b 1
)
