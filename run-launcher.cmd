@echo off
setlocal
python "%~dp0launcher.py"
if errorlevel 1 pause
