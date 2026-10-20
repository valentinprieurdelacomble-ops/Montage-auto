#!/bin/bash
# Installation du montage automatique (Mac). Double-clique sur ce fichier.
cd "$(dirname "$0")" || exit 1
echo "=========================================================="
echo "  Installation du montage automatique (Mac)"
echo "=========================================================="

if ! command -v brew >/dev/null 2>&1; then
  echo "[0/4] Installation de Homebrew (le gestionnaire d'applications du Mac)…"
  echo "      Ton mot de passe de session peut t'être demandé (rien ne s'affiche quand tu tapes, c'est normal)."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
fi

command -v python3.12 >/dev/null 2>&1 || { echo "[1/6] Installation de Python…"; brew install python@3.12; }
echo "[1/6] Python OK"
command -v ffmpeg >/dev/null 2>&1 || { echo "[2/6] Installation de FFmpeg…"; brew install ffmpeg; }
echo "[2/6] FFmpeg OK"

command -v node >/dev/null 2>&1 || { echo "[3/6] Installation de Node.js…"; brew install node@22 && brew link --overwrite node@22; }
echo "[3/6] Node.js OK"

echo "[4/6] Installation des bibliothèques…"
[ -x .venv/bin/python ] || python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements.txt || { echo "Problème : envoie une capture à Claude."; exit 1; }

echo "[5/6] Installation de Remotion (cartes animées)…"
(cd remotion && npm ci --no-audit --no-fund && node preparer.mjs) || { echo "Problème Remotion : envoie une capture à Claude."; exit 1; }

echo "[6/6] Téléchargement du modèle Whisper (une seule fois)…"
.venv/bin/python outils/telecharger_modele.py
chmod +x monter.command
echo "C'est installé ! Dépose une vidéo dans a_monter/ puis double-clique sur monter.command"
