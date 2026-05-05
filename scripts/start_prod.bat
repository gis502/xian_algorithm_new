@echo off
REM Windows startup script - Production environment (background mode)
echo ========================================
echo   Starting Production Environment
echo ========================================

REM Change to project root directory
cd /d "%~dp0.."

REM Check and create virtual environment if not exists
if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found, creating...
    python -m venv .venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        echo Please ensure Python is installed and accessible
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
)

REM Activate virtual environment
call .venv\Scripts\activate.bat
echo Virtual environment activated

REM Upgrade pip and install dependencies
echo Checking dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip -q
.venv\Scripts\python.exe -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully

REM Set environment variable
set ENVIRONMENT=production

REM Create logs directory if not exists
if not exist "logs" mkdir logs

REM Start application in background using start command
start "Xian Algorithm Prod" cmd /c "title Xian Algorithm Prod && .venv\Scripts\python.exe start.py"

echo.
echo Application started in background
echo To view logs, check: logs\app_*.log
echo To stop the application, run: scripts\stop.bat
echo ========================================

