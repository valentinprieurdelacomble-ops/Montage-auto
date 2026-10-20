"""Rendu final avec FFmpeg : coupes, recadrage, zooms, sous-titres, son, bruitages."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .outils import (RACINE, ErreurMontage, attention, filtre_disponible, info, lancer,
                     option_script_filtre)

SONS_EXT = (".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aiff")


def _expr_selection(segments, fps) -> str:
    e = 0.5 / fps  # demi-image de marge : on garde exactement les images voulues
    return "+".join(f"between(t,{a - e:.4f},{b - e:.4f})" for a, b in segments)


def _expr_zoom(zooms, r) -> str:
    """Facteur de zoom en fonction du temps t (1 = pas de zoom)."""
    termes = []
    for z in zooms:
        s, f, A = z["debut"], z["fin"], z["intensite"] - 1
        if z["type"] == "punch":
            termes.append(f"{A:.3f}*gte(t,{s:.3f})*lt(t,{f:.3f})")
        else:
            # montée douce (courbe en S) puis redescente douce
            u = f"clip((t-{s:.3f})/{r:.3f},0,1)"
            v = f"clip(({f:.3f}-t)/{r:.3f},0,1)"
            termes.append(f"{A:.3f}*{u}*{u}*(3-2*{u})*{v}*{v}*(3-2*{v})")
    return "1" + "".join("+" + t for t in termes)


def _filtre_hdr(flux_video: dict) -> str:
    trc = flux_video.get("color_transfer", "")
    if trc not in ("arib-std-b67", "smpte2084"):
        return ""
    if not filtre_disponible("zscale"):
        attention("Vidéo HDR détectée mais ton FFmpeg ne sait pas la convertir : couleurs possiblement "
                  "délavées. Astuce iPhone : Réglages > Appareil photo > Enregistrer vidéo > Vidéo HDR : désactivé.")
        return ""
    info("Vidéo HDR (iPhone) détectée : conversion des couleurs en SDR")
    return (f"zscale=tin={trc}:min=bt2020nc:pin=bt2020:t=linear:npl=203,format=gbrpf32le,"
            "zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")


def _niveau_crete(fichier: Path) -> float:
    res = lancer(["ffmpeg", "-hide_banner", "-i", fichier, "-af", "volumedetect", "-f", "null", "-"])
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", res.stderr)
    return float(m.group(1)) if m else 0.0


def _sons_disponibles(type_son: str) -> list[Path]:
    dossier = RACINE / "assets" / "sfx" / type_son
    return sorted(p for p in dossier.glob("*") if p.suffix.lower() in SONS_EXT) if dossier.exists() else []


def _chaine_voix(reglages: dict, segments, fps) -> str:
    au = reglages["audio"]
    sel = _expr_selection(segments, fps)
    # 1600 échantillons = 1 image à 30 fps : la coupe du son tombe pile sur la coupe de l'image
    paquet = 48000 // fps
    ch = (f"[0:a:0]aresample=48000,aformat=channel_layouts=mono,asetnsamples=n={paquet}:p=1,"
          f"aselect='{sel}',asetpts=N/SR/TB,highpass=f=80")
    fin = ",pan=stereo|c0=c0|c1=c0"  # voix identique à gauche et à droite
    if au.get("debruitage"):
        ch += ",afftdn=nf=-25"
    if au.get("compression", True):
        ch += ",acompressor=threshold=-21dB:ratio=3:attack=8:release=160:makeup=2"
    return ch + fin


def _gain_et_limiteur(gain: float, au: dict) -> str:
    limite = 10 ** ((au["crete_max_db"] - 0.5) / 20)
    return f",volume={gain:.2f}dB,alimiter=limit={limite:.4f}:attack=3:release=60:level=false"


def _mesurer(source: Path, chaine: str) -> float:
    res = lancer(["ffmpeg", "-hide_banner", "-i", source, "-filter_complex",
                  chaine + ",loudnorm=print_format=json[a]", "-map", "[a]", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", res.stderr, re.S)
    if not m:
        raise ErreurMontage("Impossible de mesurer le volume de la voix.")
    return float(json.loads(m.group(0))["input_i"])


def calculer_gain(source: Path, segments, reglages, fps) -> float:
    """Gain (dB) qui amène la voix au volume cible APRÈS le limiteur anti-saturation."""
    au = reglages["audio"]
    base = _chaine_voix(reglages, segments, fps)
    gain = au["volume_cible_lufs"] - _mesurer(source, base)
    for _ in range(3):  # le limiteur enlève un peu de volume : on corrige
        ecart = au["volume_cible_lufs"] - _mesurer(source, base + _gain_et_limiteur(gain, au))
        if abs(ecart) < 0.3:
            break
        gain += ecart
    return gain


def _encoder_base(source: Path, image: str, dossier_travail: Path, fps: int) -> Path:
    """Passe 1 (seulement s'il y a des inserts) : image coupée + zooms, sans son ni texte."""
    base = dossier_travail / "base.mp4"
    (dossier_travail / "filtres_base.txt").write_text(f"[0:v:0]{image}[v]", encoding="utf-8")
    lancer(["ffmpeg", "-y", "-hide_banner", "-v", "error", "-stats", "-i", str(source),
            option_script_filtre(), "filtres_base.txt", "-map", "[v]", "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-g", str(fps), "-pix_fmt", "yuv420p",
            "-r", str(fps), "base.mp4"], cwd=dossier_travail)
    return base


def _graphe_inserts(entrees: list[str], base: Path, inserts, cartes, images, g, reglages) -> tuple[list[str], str]:
    """Pose chaque carte animée sur un fond anthracite, avec le visage dans une bulle ronde en haut."""
    fps = reglages["export"]["fps"]
    T = reglages["inserts"]["transition"]
    W, H, D, cy, S = g["W"], g["H"], g["D"], g["cy"], g["cadrage"]
    R = images["R"]
    y0 = min(max(0, g["y_visage"] - S // 2), H - S)

    def entree(*args) -> int:
        entrees.extend(str(a) for a in args)
        return entrees.count("-i") - 1

    parties = []
    courant = "[1:v:0]"
    for k, (ins, carte) in enumerate(zip(inserts, cartes)):
        s, d = ins["debut"], ins["duree"]
        boucle = ("-loop", "1", "-framerate", fps, "-t", f"{d:.3f}")
        i_fond = entree(*boucle, "-i", images["fond"].resolve())
        i_carte = entree("-i", carte.resolve())
        i_visage = entree("-ss", f"{s:.3f}", "-t", f"{d:.3f}", "-i", base.resolve())
        i_masque = entree(*boucle, "-i", images["masque"].resolve())
        i_anneau = entree(*boucle, "-i", images["anneau"].resolve())
        parties += [
            f"[{i_fond}:v]format=rgb24,setpts=PTS-STARTPTS[f{k}]",
            f"[{i_carte}:v]setpts=PTS-STARTPTS[k{k}]",
            f"[f{k}][k{k}]overlay=0:{g['y_carte']}:shortest=1[la{k}]",
            f"[{i_visage}:v]setpts=PTS-STARTPTS,crop={S}:{S}:{(W - S) // 2}:{y0},scale={D}:{D}:flags=lanczos,"
            f"format=yuva420p[b{k}]",
            f"[{i_masque}:v]format=gray,setpts=PTS-STARTPTS[m{k}]",
            f"[b{k}][m{k}]alphamerge[bm{k}]",
            f"[la{k}][bm{k}]overlay={(W - D) // 2}:{cy - D // 2}:shortest=1[lb{k}]",
            f"[lb{k}][{i_anneau}:v]overlay={(W - R) // 2}:{cy - R // 2}:shortest=1,format=yuva420p,"
            f"fade=t=in:st=0:d={T}:alpha=1,fade=t=out:st={max(0.0, d - T):.3f}:d={T}:alpha=1,"
            f"setpts=PTS+{s:.3f}/TB[l{k}]",
            f"{courant}[l{k}]overlay=0:0:eof_action=pass[c{k}]",
        ]
        courant = f"[c{k}]"
    return parties, courant


def rendre(source: Path, sonde: dict, plan: dict, reglages: dict, dossier_travail: Path, sortie: Path,
           inserts: list[dict] | None = None, cartes: list[Path] | None = None) -> None:
    ex, zr, br, au = reglages["export"], reglages["zooms"], reglages["bruitages"], reglages["audio"]
    W, H, fps = ex["largeur"], ex["hauteur"], ex["fps"]
    segments = plan["segments"]
    flux_v = next(s for s in sonde["streams"] if s["codec_type"] == "video")
    if not any(s["codec_type"] == "audio" for s in sonde["streams"]):
        raise ErreurMontage("Cette vidéo n'a pas de son.")

    # Police copiée à côté des sous-titres (évite les soucis de chemins sous Windows)
    polices = dossier_travail / "polices"
    polices.mkdir(exist_ok=True)
    for p in (RACINE / "assets" / "fonts").glob("*.[ot]tf"):
        shutil.copy2(p, polices / p.name)

    info("Mesure du volume de la voix")
    gain = calculer_gain(source, segments, reglages, fps)

    # ---- Image ----
    sel = _expr_selection(segments, fps)
    z = _expr_zoom(plan.get("zooms", []), zr["duree_transition"])
    cy = zr["centre_vertical"]
    image = (f"fps={fps},{_filtre_hdr(flux_v)}"
             f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1,"
             f"select='{sel}',setpts=N/{fps}/TB")
    if plan.get("zooms"):
        image += (f",scale=w='2*trunc({W / 2}*({z}))':h='2*trunc({H / 2}*({z}))':eval=frame:flags=bicubic,"
                  f"crop={W}:{H}:'(iw-{W})/2':'(ih-{H})*{cy}'")
    texte = ",ass=sous_titres.ass:fontsdir=polices,format=yuv420p[v]"

    entrees = ["-i", str(source)]
    if inserts:
        from .inserts import geometrie, preparer_images
        info("Passe 1/2 : image coupée et zooms")
        base = _encoder_base(source, image, dossier_travail, fps)
        g = geometrie(reglages)
        images = preparer_images(dossier_travail, g, reglages)
        entrees += ["-i", str(base.resolve())]
        parties, courant = _graphe_inserts(entrees, base, inserts, cartes, images, g, reglages)
        video = ";\n".join(parties + [f"{courant}null{texte}"])
    else:
        video = f"[0:v:0]{image}{texte}"

    # ---- Son ----
    # Gain vers le volume cible, puis limiteur : aucune crête ne dépasse.
    voix = _chaine_voix(reglages, segments, fps) + _gain_et_limiteur(gain, au) + "[voix]"

    morceaux_son, etiquettes = [], ["[voix]"]
    sons = plan.get("sons", []) if br.get("actif", True) else []
    par_type: dict[str, list[dict]] = {}
    for s in sons:
        par_type.setdefault(s["type"], []).append(s)
    for type_son, liste in par_type.items():
        fichiers = _sons_disponibles(type_son)
        if not fichiers:
            attention(f"Aucun son dans assets/sfx/{type_son} : bruitages « {type_son} » ignorés.")
            continue
        cible = br["volume_whoosh_db"] if type_son == "whoosh" else br["volume_pop_db"]
        # on alterne entre les fichiers disponibles pour ne pas entendre toujours le même
        groupes: dict[int, list[dict]] = {}
        for k, s in enumerate(liste):
            groupes.setdefault(k % len(fichiers), []).append(s)
        for idx, evts in groupes.items():
            f = fichiers[idx]
            gain_son = cible - _niveau_crete(f)
            n_entree = entrees.count("-i")
            entrees += ["-i", str(f)]
            noms = [f"s{n_entree}_{k}" for k in range(len(evts))]
            morceaux_son.append(f"[{n_entree}:a:0]aresample=48000,aformat=channel_layouts=stereo,"
                                f"volume={gain_son:.2f}dB,asplit={len(evts)}" + "".join(f"[{n}]" for n in noms))
            for n, e in zip(noms, evts):
                ms = int(max(0, e["temps"]) * 1000)
                morceaux_son.append(f"[{n}]adelay={ms}:all=1[{n}d]")
                etiquettes.append(f"[{n}d]")
    if len(etiquettes) > 1:
        mix = (f"{''.join(etiquettes)}amix=inputs={len(etiquettes)}:duration=first:normalize=0,"
               "alimiter=limit=0.89:level=false[a]")
    else:
        mix = "[voix]alimiter=limit=0.89:level=false[a]"

    graphe = ";\n".join([video, voix] + morceaux_son + [mix])
    (dossier_travail / "filtres.txt").write_text(graphe, encoding="utf-8")
    from .sous_titres import ecrire_ass
    ecrire_ass(plan, reglages, dossier_travail / "sous_titres.ass")

    info("Passe 2/2 : vidéo finale" if inserts else "Rendu de la vidéo finale (c'est l'étape la plus longue)")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    temporaire = sortie.with_name(sortie.stem + ".en_cours.mp4")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-v", "error", "-stats", *entrees,
           option_script_filtre(), "filtres.txt", "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", ex["preset"], "-crf", str(ex["qualite_crf"]),
           "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p", "-r", str(fps),
           "-g", str(fps * 2), "-maxrate", "25M", "-bufsize", "50M",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-c:a", "aac", "-b:a", ex["debit_audio"], "-ar", "48000",
           "-movflags", "+faststart", "-t", f"{plan['duree_finale']:.3f}", str(temporaire.resolve())]
    lancer(cmd, cwd=dossier_travail)
    temporaire.replace(sortie)
