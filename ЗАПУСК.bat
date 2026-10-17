@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    ".venv\Scripts\pythonw.exe" launcher.py
) else (
    py -3 launcher.py
)
if errorlevel 1 pause
