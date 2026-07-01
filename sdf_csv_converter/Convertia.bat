@echo off
setlocal EnableExtensions
rem Convertia launcher — double-click for GUI, or pass CLI args (same as Convertia.exe).
rem   Convertia.bat
rem   Convertia.bat input.cdxml -o output.csv

set "ROOT=%~dp0.."
cd /d "%ROOT%"

set "EXE=%ROOT%\standalone\dist\Convertia.exe"
if exist "%EXE%" (
    if "%~1"=="" (
        start "" "%EXE%"
    ) else (
        "%EXE%" %*
        if errorlevel 1 pause
    )
    exit /b 0
)

where python >nul 2>&1
if errorlevel 1 (
    echo Convertia.exe was not found at:
    echo   %EXE%
    echo.
    echo Python is also not on PATH. Either:
    echo   1. Build the standalone app:  cd standalone ^&^& python build_standalone.py
    echo   2. Install Python 3 and run: pip install -r sdf_csv_converter\requirements.txt
    pause
    exit /b 1
)

if "%~1"=="" (
    where pythonw >nul 2>&1
    if not errorlevel 1 (
        start "" pythonw -m sdf_csv_converter.gui
    ) else (
        start "" python -m sdf_csv_converter.gui
    )
) else (
    python -m sdf_csv_converter %*
    if errorlevel 1 pause
)

endlocal
