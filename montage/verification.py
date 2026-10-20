"""Contrôle qualité de la vidéo finale : on ne déclare jamais une vidéo prête sans ça."""
from __future__ import annotations

import re
from pathlib import Path

from .outils import lancer, sonder


def verifier(sortie: Path, plan: dict, reglages: dict, dossier_travail: Path) -> dict:
    ex, au = reglages["export"], reglages["audio"]
    problemes, ok = [], []
    s = sonder(sortie)
    v = next((x for x in s["streams"] if x["codec_type"] == "video"), None)
    a = next((x for x in s["streams"] if x["codec_type"] == "audio"), None)
    if not v or not a:
        return {"pret": False, "problemes": ["image ou son manquant"], "ok": []}

    def controle(condition, texte_ok, texte_ko):
        (ok if condition else problemes).append(texte_ok if condition else texte_ko)

    controle(v["codec_name"] == "h264", "vidéo H.264", f"codec vidéo {v['codec_name']}")
    controle((v["width"], v["height"]) == (ex["largeur"], ex["hauteur"]),
             f"format {v['width']}x{v['height']}", f"format {v['width']}x{v['height']}")
    num, den = map(int, v["r_frame_rate"].split("/"))
    controle(abs(num / den - ex["fps"]) < 0.01, f"{ex['fps']} images/s", f"{num / den:.2f} images/s")
    controle(v.get("pix_fmt") == "yuv420p", "couleurs yuv420p", f"pix_fmt {v.get('pix_fmt')}")
    controle(a["codec_name"] == "aac", "son AAC", f"codec son {a['codec_name']}")
    dv, da = float(v.get("duration", 0)), float(a.get("duration", 0))
    attendu = plan["duree_finale"]
    controle(abs(dv - attendu) < 0.15, f"durée {dv:.2f} s (attendu {attendu:.2f} s)",
             f"durée {dv:.2f} s au lieu de {attendu:.2f} s")
    controle(abs(dv - da) < 0.1, "son et image de même durée (synchro)", f"écart son/image {abs(dv - da):.2f} s")

    # Volume réel mesuré sur le fichier final
    res = lancer(["ffmpeg", "-hide_banner", "-nostats", "-i", sortie, "-map", "0:a",
                  "-af", "ebur128=peak=true", "-f", "null", "-"])
    resume = res.stderr[res.stderr.rfind("Summary:"):]
    m_i = re.search(r"I:\s*(-?[\d.]+) LUFS", resume)
    m_p = re.search(r"Peak:\s*(-?[\d.]+|-inf) dBFS", resume)
    lufs = float(m_i.group(1)) if m_i else -99
    crete = float(m_p.group(1)) if m_p and m_p.group(1) != "-inf" else -99
    controle(abs(lufs - au["volume_cible_lufs"]) <= 1.5, f"volume voix {lufs:.1f} LUFS",
             f"volume {lufs:.1f} LUFS (cible {au['volume_cible_lufs']})")
    controle(crete <= -0.5, f"aucune saturation (crête {crete:.1f} dB)", f"crête trop haute : {crete:.1f} dB")

    # Images noires ou figées
    res = lancer(["ffmpeg", "-hide_banner", "-nostats", "-i", sortie, "-vf",
                  "blackdetect=d=0.3:pix_th=0.08", "-an", "-f", "null", "-"])
    noirs = res.stderr.count("black_start")
    controle(noirs == 0, "aucun écran noir", f"{noirs} passage(s) noir(s) détecté(s)")

    if plan.get("inserts"):
        part = sum(i["duree"] for i in plan["inserts"]) / max(1e-6, attendu)
        controle(part <= 0.25, f"{len(plan['inserts'])} insert(s) animé(s), visage plein écran {100 - 100 * part:.0f} % du temps",
                 f"inserts trop présents : visage plein écran seulement {100 - 100 * part:.0f} % du temps")
    planche = planche_contact(sortie, plan, dossier_travail, ex["fps"])
    return {"pret": not problemes, "ok": ok, "problemes": problemes, "planche": str(planche),
            "volume_lufs": lufs, "crete_db": crete, "duree": dv}


def planche_contact(sortie: Path, plan: dict, dossier_travail: Path, fps: int) -> Path:
    """Image avec 12 vignettes prises aux moments clés (titre, zooms, mots-clés…)."""
    duree = plan["duree_finale"]
    temps = [0.6]
    # le milieu et la fin de chaque insert animé (carte entièrement construite)
    for ins in plan.get("inserts", []):
        temps += [ins["debut"] + ins["duree"] * 0.45, ins["debut"] + ins["duree"] - 0.5]
    temps += [(z["debut"] + z["fin"]) / 2 for z in plan.get("zooms", [])[:4]]
    temps += [a["debut"] + 0.5 for a in plan.get("animations", []) if a["type"] == "chiffre"]
    cles = [m["debut"] + 0.15 for m in plan["mots"] if m["mot_cle"]]
    temps += cles[1::max(1, len(cles) // 4)][:4]
    while len(temps) < 12:
        temps.append(duree * len(temps) / 12)
    temps = sorted(min(t, duree - 0.1) for t in temps[:12])
    images = sorted({int(t * fps) for t in temps})
    sel = "+".join(f"eq(n,{i})" for i in images)
    planche = dossier_travail / "planche_controle.jpg"
    lancer(["ffmpeg", "-y", "-v", "error", "-i", sortie.resolve(), "-vf",
            f"select='{sel}',scale=360:640,drawtext=fontfile=polices/InterDisplay-ExtraBold.ttf:"
            "text='%{pts\\:hms}':x=w-tw-10:y=h-th-10:fontsize=26:fontcolor=yellow:box=1:boxcolor=black@0.6,"
            "tile=6x2:padding=4", "-frames:v", "1", "-fps_mode", "passthrough", planche.name], cwd=dossier_travail)
    return planche
