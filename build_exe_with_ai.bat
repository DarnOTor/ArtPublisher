@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv" (
    py -m venv .venv
)
call ".venv\Scripts\python.exe" -m pip install --upgrade pip
call ".venv\Scripts\python.exe" -m pip install -r requirements-ai.txt
call ".venv\Scripts\python.exe" -m pip install pyinstaller
if exist "build" rmdir /s /q "build"
if exist "dist\ArtPublisherAgentPlusAI" rmdir /s /q "dist\ArtPublisherAgentPlusAI"
call ".venv\Scripts\pyinstaller.exe" ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --collect-all ollama ^
  --name "ArtPublisherAgentPlusAI" ^
  --add-data ".env.example;." ^
  --add-data "tag_templates.json;." ^
  --add-data "READY;READY" ^
  --add-data "POSTED;POSTED" ^
  app.py
echo.
echo Build finished: AI-capable build
echo dist\ArtPublisherAgentPlusAI\
echo Ollama itself and the vision model are still installed separately.
pause
