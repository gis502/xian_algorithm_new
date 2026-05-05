@echo off
REM Windows startup script - Development environment (background mode)
echo ========================================
echo   Starting Development Environment
echo ========================================

REM Change to project root directory
cd /d "%~dp0.."

REM Verify we are in the correct directory
if not exist "start.py" (
    echo Error: Cannot find start.py in current directory: %CD%
    echo Please ensure you are running this script from the project directory
    pause
    exit /b 1
)
echo Current directory: %CD%

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
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)
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

REM Create logs directory if not exists
if not exist "logs" mkdir logs

REM Start application in background using start command
REM Create a temporary startup script with clean environment
set TEMP_START_SCRIPT=%TEMP%\start_xian_app_%RANDOM%.bat
(
    echo @echo off
    echo cd /d %CD%
    echo set ENVIRONMENT=development
    echo .venv\Scripts\python.exe start.py
) > "%TEMP_START_SCRIPT%"

start "Xian Algorithm Dev" cmd /k "title Xian Algorithm Dev && call "%TEMP_START_SCRIPT%""

echo.
echo Application started in background
echo To view logs, check: logs\app_*.log
echo To stop the application, run: scripts\stop.bat
echo ========================================

REM Keep the window open briefly to show any immediate errors
timeout /t 3 /nobreak >nul
