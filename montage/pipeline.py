"""Enchaînement complet : vidéo brute -> vidéo prête à publier."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .analyse import construire_plan
from .coupes import calculer_segments
from .outils import RACINE, ErreurMontage, attention, etape, info, sonder
from .rendu import rendre
from .transcription import charger_transcription_fournie, extraire_audio_16k, transcrire
from .verification import verifier

VIDEOS_EXT = (".mov", ".mp4", ".m4v", ".mkv", ".avi", ".webm")


def nom_propre(p: Path) -> str:
    return re.sub(r"[^\w-]+", "_", p.stem).strip("_") or "video"


def monter(source: Path, reglages: dict, *, analyse_seulement=False, reprendre=False,
           titre: str | None = None, transcription: Path | None = None) -> dict:
    debut = time.time()
    d = reglages["dossiers"]
    nom = nom_propre(source)
    travail = RACINE / d["travail"] / nom
    travail.mkdir(parents=True, exist_ok=True)
    sortie = RACINE / d["sortie"] / f"{nom}_monte.mp4"
    chemin_plan = travail / "plan.json"
    fps = reglages["export"]["fps"]

    print(f"\n══════ Montage de « {source.name} » ══════")
    sonde = sonder(source)
    duree = float(sonde["format"]["duration"])
    v = next((s for s in sonde["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        raise ErreurMontage("Ce fichier ne contient pas d'image.")
    info(f"Vidéo brute : {duree:.1f} s, {v.get('width')}x{v.get('height')}, {v.get('codec_name')}")
    if v.get("width", 1) > v.get("height", 1) and not any(
            abs(int(sd.get("rotation", 0))) == 90 for sd in v.get("side_data_list", [])):
        attention("La vidéo est horizontale : elle sera recadrée au centre en vertical.")

    if reprendre:
        if not chemin_plan.exists():
            raise ErreurMontage("Pas de plan.json à reprendre : lance d'abord sans --reprendre.")
        etape("Reprise du plan existant (plan.json)")
        plan = json.loads(chemin_plan.read_text(encoding="utf-8"))
    else:
        etape("1/4 Écoute de la voix")
        audio = extraire_audio_16k(source, travail / "voix_16k.wav")
        etape("2/4 Transcription mot par mot")
        if transcription:
            info(f"Transcription fournie : {transcription.name}")
            mots = charger_transcription_fournie(transcription)
        else:
            mots = transcrire(audio, reglages, travail / "transcription.json")
        info(f"{len(mots)} mots reconnus")
        etape("3/4 Coupe des blancs et des hésitations, choix des zooms et mots-clés")
        segments, infos = calculer_segments(audio, mots, duree, reglages, fps)
        duree_finale = sum(b - a for a, b in segments)
        info(f"{infos['nb_coupes']} coupes, {infos['hesitations_coupees']} hésitation(s) enlevée(s) : "
             f"{duree:.1f} s -> {duree_finale:.1f} s")
        plan = construire_plan(mots, segments, infos, duree_finale, reglages, titre)
        chemin_plan.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        info(f"{len(plan['zooms'])} zooms, {sum(m['mot_cle'] for m in plan['mots'])} mots-clés en bleu, "
             f"{len(plan['sons'])} bruitages, {len(plan['animations'])} animation(s)")
        info(f"Plan enregistré : {chemin_plan.relative_to(RACINE)}")
        if analyse_seulement:
            return {"plan": str(chemin_plan)}

    etape("4/4 Fabrication de la vidéo")
    rendre(source, sonde, plan, reglages, travail, sortie)

    etape("Contrôle qualité")
    rapport = verifier(sortie, plan, reglages, travail)
    rapport["sortie"] = str(sortie)
    rapport["minutes"] = round((time.time() - debut) / 60, 1)
    (travail / "rapport.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1), encoding="utf-8")
    for x in rapport["ok"]:
        info(f"OK  {x}")
    for x in rapport["problemes"]:
        attention(x)
    if rapport["pret"]:
        print(f"\n✅ Vidéo contrôlée : {sortie.relative_to(RACINE)}  ({rapport['minutes']} min)")
        print(f"   Planche de contrôle : {Path(rapport['planche']).relative_to(RACINE)}")
    else:
        print(f"\n❌ La vidéo a des problèmes (voir ci-dessus). Fichier : {sortie.relative_to(RACINE)}")
    return rapport


def videos_a_monter(reglages: dict) -> list[Path]:
    dossier = RACINE / reglages["dossiers"]["entree"]
    return sorted((p for p in dossier.iterdir() if p.suffix.lower() in VIDEOS_EXT),
                  key=lambda p: p.stat().st_mtime)
