"""Transcription mot par mot avec faster-whisper (horodatage de chaque mot)."""
from __future__ import annotations

import json
from pathlib import Path

from .outils import ErreurMontage, attention, info, lancer


def extraire_audio_16k(video: Path, sortie: Path) -> Path:
    lancer(["ffmpeg", "-y", "-v", "error", "-i", video, "-vn", "-ac", "1",
            "-ar", "16000", "-c:a", "pcm_s16le", sortie])
    return sortie


def _choisir_appareil(appareil: str) -> tuple[str, str]:
    if appareil == "cpu":
        return "cpu", "int8"
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    if appareil == "cuda":
        attention("Pas de carte NVIDIA utilisable : je passe sur le processeur.")
    return "cpu", "int8"


def transcrire(audio_16k: Path, reglages: dict, cache: Path) -> list[dict]:
    """Renvoie la liste des mots : {texte, debut, fin, proba} (temps de la vidéo brute)."""
    r = reglages["transcription"]
    cle = {"modele": r["modele"], "langue": r["langue"], "taille_audio": audio_16k.stat().st_size}
    if cache.exists():
        donnees = json.loads(cache.read_text(encoding="utf-8"))
        if donnees.get("cle") == cle:
            info("Transcription déjà faite : je réutilise transcription.json")
            return donnees["mots"]

    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise ErreurMontage("faster-whisper n'est pas installé : relance l'installateur.") from e

    appareil, calcul = _choisir_appareil(r.get("appareil", "auto"))
    info(f"Modèle Whisper « {r['modele']} » sur {appareil} (le 1er lancement le télécharge, patience)")
    try:
        modele = WhisperModel(r["modele"], device=appareil, compute_type=calcul)
    except Exception:
        if appareil == "cpu":
            raise
        attention("La carte graphique n'a pas fonctionné : je passe sur le processeur.")
        modele = WhisperModel(r["modele"], device="cpu", compute_type="int8")

    # Le "euh" dans la consigne aide Whisper à écrire les hésitations (pour les couper).
    consigne = "Euh, bon, alors… euh, voilà. " + (r.get("vocabulaire") or "")
    segments, _ = modele.transcribe(
        str(audio_16k), language=r["langue"], word_timestamps=True,
        vad_filter=True, vad_parameters={"min_silence_duration_ms": 400},
        initial_prompt=consigne, beam_size=5, condition_on_previous_text=False,
    )
    mots = []
    for seg in segments:
        for w in seg.words or []:
            texte = w.word.strip()
            if texte:
                mots.append({"texte": texte, "debut": round(w.start, 3),
                             "fin": round(w.end, 3), "proba": round(w.probability, 3)})
        info(f"{seg.end:6.1f} s : {seg.text.strip()[:70]}")
    if not mots:
        raise ErreurMontage("Whisper n'a entendu aucune parole dans cette vidéo.")
    cache.write_text(json.dumps({"cle": cle, "mots": mots}, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    return mots


def charger_transcription_fournie(chemin: Path) -> list[dict]:
    """Transcription déjà prête (fichier JSON avec une liste de mots)."""
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    return donnees["mots"] if isinstance(donnees, dict) else donnees
