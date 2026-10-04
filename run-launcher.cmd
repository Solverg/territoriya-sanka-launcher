@echo off
setlocal
if exist "%~dp0TerritorySanyokLauncher.exe" (
  start "" "%~dp0TerritorySanyokLauncher.exe"
  exit /b 0
)
python "%~dp0launcher.py"
if errorlevel 1 pause

