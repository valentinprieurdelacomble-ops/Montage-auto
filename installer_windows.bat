@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo ==========================================================
echo   Installation du montage automatique (Windows)
echo ==========================================================
echo.

REM ---- 1. Python ----
set "PY="
where py >nul 2>nul && (py -3.12 --version >nul 2>nul && set "PY=py -3.12")
if not defined PY (where py >nul 2>nul && (py -3 --version >nul 2>nul && set "PY=py -3"))
if not defined PY (where python >nul 2>nul && (python --version >nul 2>nul && set "PY=python"))
if not defined PY (
  echo [1/6] Python n'est pas installe : installation en cours...
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  echo.
  echo  ^>^> Python vient d'etre installe. FERME cette fenetre puis RELANCE installer_windows.bat
  pause
  exit /b 0
)
echo [1/6] Python trouve : %PY%

REM ---- 2. FFmpeg ----
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo [2/6] FFmpeg n'est pas installe : installation en cours...
  winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
  echo.
  echo  ^>^> FFmpeg vient d'etre installe. FERME cette fenetre puis RELANCE installer_windows.bat
  pause
  exit /b 0
)
echo [2/6] FFmpeg trouve

REM ---- 3. Node.js (pour les cartes animees Remotion) ----
where node >nul 2>nul
if errorlevel 1 (
  echo [3/6] Node.js n'est pas installe : installation en cours...
  winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
  echo.
  echo  ^>^> Node.js vient d'etre installe. FERME cette fenetre puis RELANCE installer_windows.bat
  pause
  exit /b 0
)
echo [3/6] Node.js trouve

REM ---- 4. Bibliotheques Python ----
echo [4/6] Installation des bibliotheques (quelques minutes)...
if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo  !! Probleme pendant l'installation des bibliotheques. Envoie une capture de cette fenetre a Claude.
  pause
  exit /b 1
)

REM ---- 5. Remotion (cartes animees) ----
echo [5/6] Installation de Remotion (cartes animees)...
pushd remotion
call npm ci --no-audit --no-fund
if errorlevel 1 (
  popd
  echo  !! Probleme pendant l'installation de Remotion. Envoie une capture de cette fenetre a Claude.
  pause
  exit /b 1
)
node preparer.mjs
popd

REM ---- 6. Modele de transcription ----
echo [6/6] Telechargement du modele Whisper (une seule fois, peut prendre 5 a 10 minutes)...
".venv\Scripts\python.exe" outils\telecharger_modele.py

echo.
echo ==========================================================
echo   C'est installe ! Depose une video dans a_monter\
echo   puis double-clique sur monter.bat
echo ==========================================================
pause
