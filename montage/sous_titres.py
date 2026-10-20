"""Sous-titres dynamiques (format ASS, gravés dans l'image par FFmpeg)."""
from __future__ import annotations

import re

from .outils import couleur_ass


def _temps(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _nettoyer(texte: str, majuscules: bool) -> str:
    # On enlève la ponctuation de fin (sauf ? et !) : plus propre à l'écran.
    t = re.sub(r"[,.;:…]+$", "", texte.strip())
    t = t.replace("{", "(").replace("}", ")")
    return t.upper() if majuscules else t


def grouper(mots: list[dict], st: dict) -> list[list[dict]]:
    groupes, courant = [], []
    for i, m in enumerate(mots):
        if courant:
            longueur = sum(len(x["texte"]) + 1 for x in courant) + len(m["texte"])
            prec = courant[-1]
            coupure = (len(courant) >= st["mots_max"] or longueur > st["caracteres_max"]
                       or re.search(r"[,.!?…;:]$", prec["texte"]) or m["debut"] - prec["fin"] > 0.25
                       or m["mot_cle"] and len(courant) >= 2)
            if coupure:
                groupes.append(courant)
                courant = []
        courant.append(m)
    if courant:
        groupes.append(courant)
    return groupes


def _ligne(nom_style, debut, fin, texte):
    return f"Dialogue: 0,{_temps(debut)},{_temps(fin)},{nom_style},,0,0,0,,{texte}"


def ecrire_ass(plan: dict, reglages: dict, chemin) -> None:
    st, an, ex = reglages["sous_titres"], reglages["animations"], reglages["export"]
    W, H = ex["largeur"], ex["hauteur"]
    blanc = couleur_ass(st["couleur"])
    bleu = couleur_ass(st["couleur_mot_cle"])
    contour = couleur_ass(st["couleur_contour"])
    ombre = couleur_ass(st["couleur_contour"], 0x60)
    fond_titre = couleur_ass(an.get("couleur_fond_titre", "#111318"), 0x18)
    police = st["police"]
    taille = st["taille"]

    entete = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sous,{police},{taille},{blanc},{blanc},{contour},{ombre},0,0,0,0,100,100,0,0,1,{st['epaisseur_contour']},{st['ombre']},5,70,70,0,1
Style: Titre,{police},{int(taille * 0.66)},{blanc},{blanc},{fond_titre},{fond_titre},0,0,0,0,100,100,0,0,3,22,0,5,90,90,0,1
Style: Chiffre,{police},{int(taille * 2.9)},{bleu},{bleu},{contour},{ombre},0,0,0,0,100,100,-2,0,1,4,4,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lignes = []
    x, y = W // 2, int(H * st["position_verticale"])
    pop = (r"\fscx86\fscy86\alpha&H80&\t(0,70,\fscx104\fscy104\alpha&H00&)\t(70,140,\fscx100\fscy100)"
           if st.get("animation_pop", True) else "")
    groupes = grouper(plan["mots"], st)
    for k, g in enumerate(groupes):
        debut = g[0]["debut"]
        suivant = groupes[k + 1][0]["debut"] if k + 1 < len(groupes) else None
        fin = g[-1]["fin"] + 0.25
        if suivant is not None:
            fin = suivant if suivant - g[-1]["fin"] < 0.6 else min(fin, suivant)
        fin = max(fin, debut + 0.25)
        morceaux = []
        for m in g:
            t = _nettoyer(m["texte"], st["majuscules"])
            morceaux.append(f"{{\\c{bleu}}}{t}{{\\c{blanc}}}" if m["mot_cle"] else t)
        nb = sum(len(_nettoyer(m["texte"], False)) for m in g) + len(g) - 1
        # mot très long : on réduit la taille pour qu'il tienne sur une ligne
        fs = f"\\fs{int(taille * st['caracteres_max'] / nb)}" if nb > st["caracteres_max"] else ""
        lignes.append(_ligne("Sous", debut, fin, f"{{\\an5\\pos({x},{y}){fs}{pop}}}" + " ".join(morceaux)))

    for a in plan.get("animations", []):
        texte = a["texte"].replace("{", "(").replace("}", ")")
        if a["type"] == "titre":
            yt = int(H * 0.2)
            effet = f"\\an5\\move({x},{yt + 24},{x},{yt},0,260)\\fad(220,260)"
            lignes.append(_ligne("Titre", a["debut"], a["fin"], f"{{{effet}}}{texte}"))
        elif a["type"] == "chiffre":
            yc = int(H * 0.20)  # au-dessus de la tête, pour ne pas cacher le visage
            effet = (f"\\an5\\pos({x},{yc})\\fad(60,220)\\fscx70\\fscy70"
                     r"\t(0,120,\fscx108\fscy108)\t(120,220,\fscx100\fscy100)")
            lignes.append(_ligne("Chiffre", a["debut"], a["fin"], f"{{{effet}}}{texte}"))

    with open(chemin, "w", encoding="utf-8") as f:
        f.write(entete + "\n".join(lignes) + "\n")
