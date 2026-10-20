"""Détection des blancs et des hésitations -> liste des morceaux à garder."""
from __future__ import annotations

import re
import wave
from pathlib import Path

import numpy as np

PAS = 0.01  # analyse du son par tranches de 10 ms


def niveau_sonore(audio_16k: Path) -> np.ndarray:
    """Volume (en dB) de chaque tranche de 10 ms."""
    with wave.open(str(audio_16k), "rb") as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    hop, fen = int(sr * PAS), int(sr * 0.03)
    n = max(1, (len(x) - fen) // hop + 1)
    idx = np.arange(fen)[None, :] + hop * np.arange(n)[:, None]
    idx = np.minimum(idx, len(x) - 1)
    rms = np.sqrt(np.mean(x[idx] ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms)


def _intervalles(masque: np.ndarray) -> list[list[float]]:
    d = np.diff(np.concatenate([[0], masque.astype(np.int8), [0]]))
    return [[a * PAS, b * PAS] for a, b in zip(np.where(d == 1)[0], np.where(d == -1)[0])]


def normaliser_mot(texte: str) -> str:
    return re.sub(r"[^\wà-ÿ]", "", texte.lower())


def est_hesitation(texte: str, reglages: dict) -> bool:
    return normaliser_mot(texte) in {normaliser_mot(m) for m in reglages["coupes"]["mots_hesitation"]}


def calculer_segments(audio_16k: Path, mots: list[dict], duree: float, reglages: dict, fps: int):
    """Renvoie (segments gardés [[debut, fin], ...] en temps de la vidéo brute, infos)."""
    c = reglages["coupes"]
    db = niveau_sonore(audio_16k)
    voix = float(np.percentile(db, 95))
    fond = float(np.percentile(db, 10))
    seuil = max(voix - c["seuil_silence_db"], fond + 6)
    parole = db > seuil

    # Les hésitations ("euh") deviennent du silence, sans toucher aux mots voisins.
    nb_hesitations = 0
    if c.get("couper_hesitations", True):
        for i, m in enumerate(mots):
            if not est_hesitation(m["texte"], reglages):
                continue
            debut, fin = m["debut"] - 0.02, m["fin"] + 0.02
            if i > 0:
                debut = max(debut, mots[i - 1]["fin"] + 0.05)
            if i + 1 < len(mots):
                fin = min(fin, mots[i + 1]["debut"] - 0.05)
            if fin - debut > 0.08:
                parole[int(debut / PAS):int(np.ceil(fin / PAS))] = False
                nb_hesitations += 1

    zones = _intervalles(parole)
    # On recolle les zones séparées par un blanc trop court pour être coupé.
    fusion: list[list[float]] = []
    for z in zones:
        if fusion and z[0] - fusion[-1][1] < c["silence_min"]:
            fusion[-1][1] = z[1]
        else:
            fusion.append(z)
    # On jette les mini-bruits isolés (clics, souffles).
    fusion = [z for z in fusion if z[1] - z[0] >= c["duree_min_segment"]]

    # Respiration naturelle avant/après, puis alignement sur les images (pas de décalage son/image).
    resp = c["respiration"]
    segments: list[list[float]] = []
    for a, b in fusion:
        a, b = max(0.0, a - resp), min(duree, b + resp)
        a = np.floor(a * fps) / fps
        b = np.ceil(b * fps) / fps
        if segments and a <= segments[-1][1]:
            segments[-1][1] = max(segments[-1][1], b)
        else:
            segments.append([a, b])
    segments = [[round(a, 4), round(b, 4)] for a, b in segments if b - a > 0]
    garde = sum(b - a for a, b in segments)
    infos = {"seuil_db": round(seuil, 1), "voix_db": round(voix, 1), "hesitations_coupees": nb_hesitations,
             "duree_source": round(duree, 2), "duree_gardee": round(garde, 2), "nb_coupes": max(0, len(segments) - 1)}
    return segments, infos


def recaler(t: float, segments: list[list[float]], cote: str) -> float | None:
    """Temps de la vidéo brute -> temps de la vidéo coupée.
    Si t tombe dans un blanc coupé : 'debut' -> début du morceau suivant, 'fin' -> fin du précédent."""
    decalage = 0.0
    for i, (a, b) in enumerate(segments):
        if t < a:
            if cote == "debut":
                return decalage
            return decalage if i > 0 else None
        if t <= b:
            return decalage + (t - a)
        decalage += b - a
    return decalage if cote == "fin" else None
