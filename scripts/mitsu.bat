@echo off
REM Mitsu command-line launcher for Windows
cd /d "%~dp0\.."
set MITSU_CLI=1
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe main.py %*
) else (
    python main.py %*
)
