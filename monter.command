#!/bin/bash
# Monte toutes les nouvelles vidéos de a_monter/ (Mac). Double-clique sur ce fichier.
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
  echo "Le système n'est pas encore installé : double-clique d'abord sur installer_mac.command"
  exit 1
fi
.venv/bin/python monter.py "$@"
