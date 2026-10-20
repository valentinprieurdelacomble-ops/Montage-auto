"""Télécharge à l'avance le modèle Whisper choisi dans reglages.yaml (une seule fois)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from montage.outils import charger_reglages  # noqa: E402

if __name__ == "__main__":
    modele = charger_reglages()["transcription"]["modele"]
    print(f"Téléchargement du modèle « {modele} »…")
    from faster_whisper import WhisperModel
    WhisperModel(modele, device="cpu", compute_type="int8")
    print("Modèle prêt.")
