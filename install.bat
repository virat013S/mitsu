@echo off
REM ──────────────────────────────────────────────────────────────────────────────
REM Mitsu Installer for Windows
REM ──────────────────────────────────────────────────────────────────────────────

echo.
echo   ╔═══════════════════════════════════════════════╗
echo   ║   MITSU Installer — Windows                   ║
echo   ║   Your Custom AI Assistant                    ║
echo   ╚═══════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

REM Step 1: Check Python
echo   [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ❌ Python 3 is required. Install from https://www.python.org/downloads/
    pause
    exit /b 1
)
echo   ✅ Python found

REM Step 2: Create venv
echo   [2/5] Setting up virtual environment...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    echo   ✅ Created .venv
) else (
    echo   ✅ .venv already exists
)

REM Step 3: Install dependencies
echo   [3/5] Installing dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet >nul 2>&1
.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
echo   ✅ Dependencies installed

REM Step 4: Setup .env
echo   [4/5] Setting up configuration...
if not exist ".env" (
    copy .env.example .env >nul
    echo   ✅ Created .env from template
) else (
    echo   ✅ .env already exists
)

REM Step 5: Install CLI
echo   [5/5] Installing mitsu CLI...
set INSTALL_DIR=%USERPROFILE%\.local\bin
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
copy /Y "scripts\mitsu.bat" "%INSTALL_DIR%\mitsu.bat" >nul
echo   ✅ Installed: %INSTALL_DIR%\mitsu.bat

echo.
echo   ╔═══════════════════════════════════════════════╗
echo   ║           Setup complete!                     ║
echo   ╠═══════════════════════════════════════════════╣
echo   ║                                               ║
echo   ║  1. Configure your API key in .env            ║
echo   ║  2. Run:  mitsu                               ║
echo   ║                                               ║
echo   ╚═══════════════════════════════════════════════╝
echo.
pause
