@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [CYBERLEEK] First run: creating virtual environment and installing dependencies...
    python -m venv .venv
    if errorlevel 1 goto :err
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :err
)

start "" ".venv\Scripts\pythonw.exe" "app.py"
exit /b 0

:err
echo.
echo [CYBERLEEK] Setup failed. Is Python installed and on PATH?
pause
exit /b 1
