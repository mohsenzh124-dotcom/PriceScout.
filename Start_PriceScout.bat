@echo off
setlocal EnableExtensions

REM PriceScout double-click launcher for Windows
REM - Runs from project root (directory of this .bat file)
REM - Prefers local venv Python, then py launcher, then system python

cd /d "%~dp0"

set "PYTHON_EXE="

if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=py -3"
    ) else (
        where python >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_EXE=python"
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python was not found.
    echo Install Python 3.x or create a local venv in this project.
    pause
    exit /b 1
)

echo Starting PriceScout...
%PYTHON_EXE% run_gui.py
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] PriceScout exited with code %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%
