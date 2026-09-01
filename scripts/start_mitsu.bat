@echo off
REM Windows launcher for MITSU.
REM Double-clickable from Explorer; from cmd.exe: scripts\start_mitsu.bat

setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0\.."

set PYTHON_BIN=python
where %PYTHON_BIN% >nul 2>nul
if errorlevel 1 (
  set PYTHON_BIN=py
)

if not exist ".venv\Scripts\python.exe" (
  echo [start_mitsu] Creating virtual environment in .venv ^(one-time^)...
  %PYTHON_BIN% -m venv .venv
)

call .venv\Scripts\activate.bat

if not exist ".venv\.mitsu_requirements.sha256" goto :install
set NEEDS_INSTALL=0
for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 requirements.txt).Hash.ToLower()"`) do (
  set HASH=%%H
)
set /p STORED=<.venv\.mitsu_requirements.sha256
if /i not "!STORED!"=="!HASH!" set NEEDS_INSTALL=1
if "!NEEDS_INSTALL!"=="1" goto :install
goto :deps_done

:install
echo [start_mitsu] Installing dependencies ^(one-time or requirements changed^)...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 requirements.txt).Hash.ToLower()"`) do (
  echo %%H>.venv\.mitsu_requirements.sha256
)

:deps_done
if not exist ".env" (
  echo [start_mitsu] No .env found - copying .env.example to .env.
  copy /Y .env.example .env >nul
  echo [start_mitsu] Edit .env and set GEMINI_API_KEY, then run this script again.
  exit /b 0
)

find /i "YOUR_GEMINI_API_KEY" .env >nul
if not errorlevel 1 (
  echo [start_mitsu] GEMINI_API_KEY still has the placeholder value.
  echo [start_mitsu] Edit .env and replace YOUR_GEMINI_API_KEY with your real key.
  exit /b 0
)

echo [start_mitsu] Starting MITSU...
python main.py
endlocal