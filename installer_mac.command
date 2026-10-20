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

command -v python3.12 >/dev/null 2>&1 || { echo "[1/4] Installation de Python…"; brew install python@3.12; }
echo "[1/4] Python OK"
command -v ffmpeg >/dev/null 2>&1 || { echo "[2/4] Installation de FFmpeg…"; brew install ffmpeg; }
echo "[2/4] FFmpeg OK"

echo "[3/4] Installation des bibliothèques…"
[ -x .venv/bin/python ] || python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements.txt || { echo "Problème : envoie une capture à Claude."; exit 1; }

echo "[4/4] Téléchargement du modèle Whisper (une seule fois)…"
.venv/bin/python outils/telecharger_modele.py
chmod +x monter.command
echo "C'est installé ! Dépose une vidéo dans a_monter/ puis double-clique sur monter.command"
