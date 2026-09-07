@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv" (
    py -m venv .venv
)
call ".venv\Scripts\python.exe" -m pip install --upgrade pip
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
call ".venv\Scripts\python.exe" -m pip install pyinstaller
if exist "build" rmdir /s /q "build"
if exist "dist\ArtPublisherAgentPlus" rmdir /s /q "dist\ArtPublisherAgentPlus"
call ".venv\Scripts\pyinstaller.exe" ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name "ArtPublisherAgentPlus" ^
  --add-data ".env.example;." ^
  --add-data "tag_templates.json;." ^
  --add-data "READY;READY" ^
  --add-data "POSTED;POSTED" ^
  app.py
echo.
echo Build finished: NON-AI build
echo dist\ArtPublisherAgentPlus\
pause
