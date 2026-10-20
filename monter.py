"""Monte automatiquement les vidéos du dossier a_monter/.

Exemples :
  python monter.py                      -> monte toutes les nouvelles vidéos de a_monter/
  python monter.py ma_video.mov         -> monte cette vidéo
  python monter.py ma_video.mov --titre "3 ERREURS À ÉVITER"
  python monter.py ma_video.mov --analyse-seulement   (prépare plan.json sans fabriquer la vidéo)
  python monter.py ma_video.mov --reprendre           (refait la vidéo à partir de plan.json)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from montage.outils import RACINE, ErreurMontage, charger_reglages, verifier_ffmpeg
from montage.pipeline import monter, nom_propre, videos_a_monter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def trouver(nom: str, reglages: dict) -> Path:
    p = Path(nom)
    for candidat in (p, RACINE / p, RACINE / reglages["dossiers"]["entree"] / p):
        if candidat.is_file():
            return candidat.resolve()
    proches = [v for v in videos_a_monter(reglages) if nom.lower() in v.name.lower()]
    if len(proches) == 1:
        return proches[0]
    raise ErreurMontage(f"Je ne trouve pas la vidéo « {nom} » dans {reglages['dossiers']['entree']}/.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Montage vidéo automatique (format Reels / TikTok / Shorts)")
    ap.add_argument("video", nargs="?", help="nom de la vidéo (sinon : toutes les nouvelles vidéos)")
    ap.add_argument("--titre", help='titre d\'accroche, ou "aucun"')
    ap.add_argument("--analyse-seulement", action="store_true", help="prépare plan.json sans faire la vidéo")
    ap.add_argument("--reprendre", action="store_true", help="refait la vidéo à partir de plan.json")
    ap.add_argument("--transcription", type=Path, help="fichier JSON de mots déjà transcrits")
    ap.add_argument("--forcer", action="store_true", help="refait même les vidéos déjà montées")
    ap.add_argument("--reglages", type=Path, help="autre fichier de réglages")
    args = ap.parse_args()

    try:
        verifier_ffmpeg()
        reglages = charger_reglages(args.reglages)
        if args.video:
            videos = [trouver(args.video, reglages)]
        else:
            sortie = RACINE / reglages["dossiers"]["sortie"]
            videos = [v for v in videos_a_monter(reglages)
                      if args.forcer or not (sortie / f"{nom_propre(v)}_monte.mp4").exists()]
            if not videos:
                print("Aucune nouvelle vidéo dans a_monter/. Dépose ta vidéo brute dedans puis relance.")
                return 0
        echecs = 0
        for v in videos:
            rapport = monter(v, reglages, analyse_seulement=args.analyse_seulement,
                             reprendre=args.reprendre, titre=args.titre, transcription=args.transcription)
            echecs += 0 if rapport.get("pret", True) else 1
        return 1 if echecs else 0
    except ErreurMontage as e:
        print(f"\n❌ {e}")
        return 1
    except KeyboardInterrupt:
        print("\nArrêté.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
