@echo off
rem Starts JarvisUI with the Python interpreter of the Jarvis virtual environment.
rem Expects this folder to be inside the Jarvis repository (e.g. C:\tools\jarvis\jarvis_ui).
set "JARVIS_ROOT=%~dp0.."
set "PYTHONPATH=%JARVIS_ROOT%\src"
start "" "%JARVIS_ROOT%\.venv\Scripts\pythonw.exe" "%~dp0main.py"
