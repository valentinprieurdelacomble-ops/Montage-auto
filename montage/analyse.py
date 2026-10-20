"""Analyse de la transcription : mots-clés, moments forts, zooms, bruitages, animations.

Tout est écrit dans plan.json, que l'on peut relire et corriger avant le rendu."""
from __future__ import annotations

import re

from .coupes import est_hesitation, normaliser_mot, recaler

MOTS_VIDES = set("""
le la les l un une des du de d au aux et ou mais donc or ni car que qu qui quoi dont où
je j tu il elle on nous vous ils elles me m te t se s lui leur leurs y en ce c ça cela ceci
mon ma mes ton ta tes son sa ses notre nos votre vos ne n pas plus moins très trop bien
est es suis sont êtes sommes était été être avoir ai as a avons avez ont avait fait faire
dans sur sous avec sans pour par chez entre vers comme si alors aussi tout tous toute toutes
cette cet ces celui celle ceux là ici oui non bon voilà juste vraiment peu beaucoup quand
même encore déjà puis après avant parce chose choses fois va vais vas allez aller peut
""".split())

MOTS_FORTS = set("""
jamais toujours personne rien secret secrets erreur erreurs vrai faux vraie fausse pourquoi
comment impossible meilleur meilleure pire essentiel essentielle clé clés confiance peur
stop arrête arrêtez simple puissant puissante charisme éloquence silence voix regard
pause stress trac public cerveau règle règles méthode astuce technique piège pièges
problème solution énorme incroyable seul seule unique vraiment différence important
importante attention honte timide respect autorité impact phrase mots histoire
""".split())

NOMBRES_LETTRES = {
    "deux": "2", "trois": "3", "quatre": "4", "cinq": "5", "six": "6", "sept": "7",
    "huit": "8", "neuf": "9", "dix": "10", "onze": "11", "douze": "12", "quinze": "15",
    "vingt": "20", "trente": "30", "quarante": "40", "cinquante": "50", "cent": "100",
    "soixante": "60", "soixantedix": "70", "quatrevingt": "80", "quatrevingts": "80",
    "quatrevingtdix": "90", "mille": "1000", "million": "1 MILLION", "millions": "MILLIONS",
}


def est_nombre(texte: str) -> str | None:
    """Renvoie l'écriture en chiffres si le mot est un nombre (hors « un/une »)."""
    t = texte.strip(" ,.!?…;:«»\"'")
    if re.fullmatch(r"\d+([.,]\d+)?\s*%?", t):
        return t
    return NOMBRES_LETTRES.get(normaliser_mot(texte))


def est_pourcent(mots: list[dict], j: int) -> bool:
    """« pour cent » / « pourcent » juste après le mot j."""
    suite = [normaliser_mot(m["texte"]) for m in mots[j + 1:j + 3]]
    return suite[:1] in (["pourcent"], ["pourcents"]) or suite == ["pour", "cent"]


def score_mot(texte: str, precedent: str = "") -> float:
    n = normaliser_mot(texte)
    if n == "cent" and normaliser_mot(precedent) == "pour":
        return -1  # « pour cent » : c'est le chiffre d'avant qui compte
    if not n or n in MOTS_VIDES:
        return -1
    s = 0.0
    if est_nombre(texte):
        s += 5
    if n in MOTS_FORTS:
        s += 3
    if len(n) >= 6:
        s += 1 + len(n) / 10
    return s


def recaler_mots(mots: list[dict], segments, reglages) -> list[dict]:
    """Garde les vrais mots (sans « euh ») et les place sur le temps de la vidéo coupée."""
    sortie = []
    for m in mots:
        if est_hesitation(m["texte"], reglages):
            continue
        d, f = recaler(m["debut"], segments, "debut"), recaler(m["fin"], segments, "fin")
        if d is None or f is None or f - d < 0.02:
            continue
        sortie.append({"texte": m["texte"], "debut": round(d, 3), "fin": round(f, 3),
                       "debut_brut": m["debut"], "mot_cle": False})
    return sortie


def decouper_phrases(mots: list[dict]) -> list[dict]:
    phrases, courant = [], []
    for i, m in enumerate(mots):
        courant.append(i)
        fin_phrase = re.search(r"[.!?…]$", m["texte"]) is not None
        suivant = mots[i + 1] if i + 1 < len(mots) else None
        pause_longue = suivant is not None and suivant["debut_brut"] - m["debut_brut"] > 1.2 and len(courant) > 3
        if fin_phrase or pause_longue or suivant is None:
            texte = " ".join(mots[j]["texte"] for j in courant)
            phrases.append({"mots": courant, "texte": texte, "debut": mots[courant[0]]["debut"],
                            "fin": mots[courant[-1]]["fin"]})
            courant = []
    return phrases


def importance(phrase: dict, mots: list[dict], rang: int, total: int) -> tuple[float, str]:
    texte = phrase["texte"]
    raisons, s = [], 0.0
    if any(est_nombre(mots[j]["texte"]) for j in phrase["mots"]):
        s += 3; raisons.append("chiffre")
    if texte.rstrip().endswith("?"):
        s += 2.5; raisons.append("question")
    if any(normaliser_mot(mots[j]["texte"]) in MOTS_FORTS for j in phrase["mots"]):
        s += 2; raisons.append("affirmation forte")
    if texte.rstrip().endswith("!"):
        s += 1; raisons.append("exclamation")
    if len(phrase["mots"]) <= 6:
        s += 1; raisons.append("phrase courte")
    if rang == 0:
        s += 3; raisons.append("accroche")
    if rang == total - 1 and total > 2:
        s += 2; raisons.append("chute")
    return s, ", ".join(raisons) or "rythme"


def choisir_mots_cles(phrases, mots):
    for p in phrases:
        candidats = [(score_mot(mots[j]["texte"], mots[j - 1]["texte"] if j else "")
                      + 0.3 * (k == len(p["mots"]) - 1), j)
                     for k, j in enumerate(p["mots"])]
        meilleur = max(candidats, default=(0, None))
        if meilleur[1] is not None and meilleur[0] >= 1.5:
            mots[meilleur[1]]["mot_cle"] = True
            p["mot_cle"] = meilleur[1]


def placer_zooms(phrases, mots, duree, reglages) -> list[dict]:
    z = reglages["zooms"]
    if not z.get("actif", True):
        return []
    total = len(phrases)
    notes = []
    for rang, p in enumerate(phrases):
        s, raison = importance(p, mots, rang, total)
        notes.append((s, rang, raison))
    choisis: list[int] = []

    def libre(t):
        return all(abs(t - phrases[r]["debut"]) >= z["intervalle_min"] for r in choisis)

    # 1) les phrases les plus fortes d'abord
    for s, rang, _ in sorted(notes, key=lambda n: -n[0]):
        if s >= 3 and libre(phrases[rang]["debut"]) and phrases[rang]["debut"] < duree - 1.5:
            choisis.append(rang)
    # 2) on comble les passages trop longs sans zoom
    for _ in range(50):
        temps = sorted([0.0] + [phrases[r]["debut"] for r in choisis] + [duree])
        trou = max(zip(temps, temps[1:]), key=lambda ab: ab[1] - ab[0])
        if trou[1] - trou[0] <= z["intervalle_max"]:
            break
        options = [(notes[r][0], r) for r in range(total)
                   if trou[0] < phrases[r]["debut"] < trou[1] and libre(phrases[r]["debut"])
                   and phrases[r]["debut"] < duree - 1.5]
        if not options:
            break
        choisis.append(max(options)[1])

    zooms = []
    for k, rang in enumerate(sorted(choisis, key=lambda r: phrases[r]["debut"])):
        p = phrases[rang]
        raison = notes[rang][2]
        punch = any(m in raison for m in ("chiffre", "chute", "phrase courte")) and "question" not in raison
        if rang == 0:
            punch = False
        debut = max(0.0, p["debut"] - 0.05)
        fin = min(p["fin"] + 0.15, debut + z["duree_max"], duree)
        if punch:
            fin = min(fin, debut + 2.5)
        zooms.append({"debut": round(debut, 3), "fin": round(fin, 3),
                      "type": "punch" if punch else "doux",
                      "intensite": z["intensite_punch"] if punch else z["intensite_doux"],
                      "raison": raison, "phrase": p["texte"]})
    # pas de chevauchement
    for a, b in zip(zooms, zooms[1:]):
        a["fin"] = round(min(a["fin"], b["debut"] - 0.4), 3)
    return [zz for zz in zooms if zz["fin"] - zz["debut"] > 0.6]


def placer_animations(phrases, mots, duree, reglages, titre_force: str | None) -> list[dict]:
    a = reglages["animations"]
    anims = []
    titre = titre_force if titre_force is not None else a.get("titre_accroche", "auto")
    if titre and str(titre).lower() not in ("aucun", "non", "false"):
        if str(titre).lower() == "auto":
            # par défaut : la première phrase si elle est courte (sinon pas de titre)
            p0 = phrases[0] if phrases else None
            titre = p0["texte"] if p0 and len(p0["mots"]) <= 7 else None
        if titre:
            anims.append({"type": "titre", "texte": str(titre).strip().rstrip(".").upper(),
                          "debut": 0.0, "fin": round(min(a["duree_titre"], duree), 2)})
    if a.get("chiffre_geant", True) and len(anims) < a["max_par_video"]:
        for p in phrases:
            for j in p["mots"]:
                n = est_nombre(mots[j]["texte"])
                if n and mots[j]["debut"] > (anims[0]["fin"] + 1 if anims else 1.0) and mots[j]["debut"] < duree - 1.5:
                    if score_mot(mots[j]["texte"], mots[j - 1]["texte"] if j else "") < 0:
                        continue  # le « cent » de « pour cent »
                    texte = n + (" %" if est_pourcent(mots, j) and "%" not in n else "")
                    anims.append({"type": "chiffre", "texte": texte.upper(), "debut": round(mots[j]["debut"], 3),
                                  "fin": round(mots[j]["debut"] + 1.4, 3)})
                    break
            if len(anims) >= a["max_par_video"] or any(x["type"] == "chiffre" for x in anims):
                break
    return anims[: a["max_par_video"]]


def placer_bruitages(zooms, mots, duree, reglages) -> list[dict]:
    b = reglages["bruitages"]
    if not b.get("actif", True):
        return []
    sons = []
    # le 1er zoom doux a toujours son whoosh, puis on respecte la proportion demandée
    compteur = 1 - b["whoosh_sur_zooms"] if b["whoosh_sur_zooms"] > 0 else -1e9
    for zm in zooms:
        if zm["type"] != "doux":
            continue
        compteur += b["whoosh_sur_zooms"]
        if compteur >= 1 - 1e-6:
            compteur -= 1
            sons.append({"type": "whoosh", "temps": round(max(0.0, zm["debut"] - 0.12), 3)})
    pops_max = max(1, int(round(b["pops_par_minute"] * duree / 60)))
    candidats = sorted((m for m in mots if m["mot_cle"]), key=lambda m: -score_mot(m["texte"]))
    pops = []
    for m in candidats:
        t = m["debut"]
        if len(pops) >= pops_max:
            break
        if all(abs(t - s["temps"]) >= b["ecart_min"] for s in sons + pops):
            pops.append({"type": "pop", "temps": round(t, 3), "mot": m["texte"]})
    return sorted(sons + pops, key=lambda s: s["temps"])


def construire_plan(mots_bruts, segments, infos_coupes, duree_finale, reglages, titre=None) -> dict:
    mots = recaler_mots(mots_bruts, segments, reglages)
    phrases = decouper_phrases(mots)
    choisir_mots_cles(phrases, mots)
    zooms = placer_zooms(phrases, mots, duree_finale, reglages)
    animations = placer_animations(phrases, mots, duree_finale, reglages, titre)
    sons = placer_bruitages(zooms, mots, duree_finale, reglages)
    for m in mots:
        m.pop("debut_brut", None)
    return {
        "_aide": ("Tu peux modifier ce fichier puis relancer avec --reprendre. "
                  "mots[].mot_cle = mot en bleu ; zooms[].type = doux ou punch ; "
                  "sons[].type = whoosh ou pop ; animations[].type = titre ou chiffre."),
        "coupes": infos_coupes,
        "duree_finale": round(duree_finale, 3),
        "segments": segments,
        "mots": mots,
        "phrases": [{"texte": p["texte"], "debut": p["debut"], "fin": p["fin"]} for p in phrases],
        "zooms": zooms,
        "animations": animations,
        "sons": sons,
    }
