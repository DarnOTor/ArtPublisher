@echo off
cd /d "%~dp0"
if not exist ".venv" (
    py -m venv .venv
)
call ".venv\Scripts\python.exe" -m pip install -r requirements-ai.txt
call ".venv\Scripts\python.exe" app.py
