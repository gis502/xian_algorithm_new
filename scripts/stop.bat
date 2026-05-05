@echo off
REM Windows stop script - Stop the application
echo ========================================
echo   Stopping Application
echo ========================================

REM Change to project root directory
cd /d "%~dp0.."

REM Find and kill python processes running start.py
echo Searching for running application...
tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH 2>nul | findstr /I "python.exe" >nul
if %errorlevel% equ 0 (
    echo Found running Python processes, stopping...
    taskkill /F /FI "WINDOWTITLE eq Xian Algorithm Dev" 2>nul
    taskkill /F /FI "WINDOWTITLE eq Xian Algorithm Prod" 2>nul
    
    REM If title-based kill didn't work, try killing all python.exe running start.py
    for /f "tokens=2 delims=," %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH 2^>nul') do (
        set "PID=%%~a"
        wmic process where "ProcessId=!PID! and CommandLine like '%%start.py%%'" delete >nul 2>&1
    )
    
    echo Application stopped successfully
) else (
    echo No running application found
)

echo ========================================
