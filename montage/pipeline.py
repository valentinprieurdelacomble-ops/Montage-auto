"""Enchaînement complet : vidéo brute -> vidéo prête à publier."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .analyse import construire_plan
from .coupes import calculer_segments
from .inserts import (appliquer_au_plan, ecrire_storyboard, fabriquer_cartes, geometrie, lire_storyboard,
                      proposer, trouver_script)
from .outils import RACINE, ErreurMontage, attention, etape, info, sonder
from .rendu import rendre
from .transcription import charger_transcription_fournie, extraire_audio_16k, transcrire
from .verification import verifier

VIDEOS_EXT = (".mov", ".mp4", ".m4v", ".mkv", ".avi", ".webm")


def nom_propre(p: Path) -> str:
    return re.sub(r"[^\w-]+", "_", p.stem).strip("_") or "video"


def monter(source: Path, reglages: dict, *, analyse_seulement=False, reprendre=False,
           titre: str | None = None, transcription: Path | None = None, nouveau_storyboard=False,
           sans_pause=False) -> dict:
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

    # ---- Storyboard des inserts animés ----
    r_ins = reglages.get("inserts", {})
    chemin_sb = travail / "storyboard.yaml"
    inserts_choisis: list[dict] = []
    if r_ins.get("actif", False):
        nouveau = nouveau_storyboard or not chemin_sb.exists()
        if nouveau:
            etape("Storyboard : choix des moments à animer")
            script = trouver_script(source)
            if script:
                info(f"Je m'appuie sur ton texte : {script.name}")
            proposes = proposer(plan, reglages, script.read_text(encoding="utf-8") if script else None)
            ecrire_storyboard(chemin_sb, proposes, plan, source.name)
            for ins in proposes:
                info(f"{ins['debut']:5.1f} s  {ins['type']:<11} « {ins.get('phrase_dite', '')[:55]} »")
            if not proposes:
                info("Aucun moment évident à animer : vidéo sans insert (tu peux en ajouter dans le storyboard).")
            info(f"Storyboard : {chemin_sb.relative_to(RACINE)}")
        if analyse_seulement:
            return {"plan": str(chemin_plan), "storyboard": str(chemin_sb), "pret": True}
        if nouveau and r_ins.get("relire_storyboard", True) and not sans_pause:
            print(f"\n✋ Relis (et modifie si tu veux) le storyboard : {chemin_sb.relative_to(RACINE)}\n"
                  "   puis relance le montage pour fabriquer la vidéo.")
            return {"storyboard": str(chemin_sb), "pret": True, "pause": True}
        inserts_choisis = lire_storyboard(chemin_sb, plan, reglages)
    elif analyse_seulement:
        return {"plan": str(chemin_plan), "pret": True}

    etape("4/4 Fabrication de la vidéo")
    cartes = []
    if inserts_choisis:
        plan = appliquer_au_plan(plan, inserts_choisis, reglages)
        cartes = fabriquer_cartes(inserts_choisis, geometrie(reglages), reglages, travail / "cartes")
    rendre(source, sonde, plan, reglages, travail, sortie, inserts_choisis, cartes)

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
