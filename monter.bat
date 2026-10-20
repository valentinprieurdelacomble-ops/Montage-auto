@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Le systeme n'est pas encore installe : double-clique d'abord sur installer_windows.bat
  pause
  exit /b 1
)
".venv\Scripts\python.exe" monter.py %*
echo.
pause
