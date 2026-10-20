"""Inserts animés (cartes Remotion) : storyboard automatique, fabrication des cartes, bulle du visage."""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

import numpy as np
import yaml

from .analyse import MOTS_FORTS, MOTS_VIDES, NOMBRES_LETTRES, importance
from .coupes import normaliser_mot
from .outils import RACINE, ErreurMontage, attention, info, lancer

TYPES = ("citation", "avant_apres", "etapes", "liste", "jauge")
DOSSIER_REMOTION = RACINE / "remotion"

# ---------------------------------------------------------------------------
#  Outils de texte
# ---------------------------------------------------------------------------

# mots sur lesquels une phrase raccourcie ne doit pas finir
FINS_FAIBLES = set("de d du des le la les l un une au aux à et ou dans sur pour par avec ta ton tes ma mon mes "
                   "sa son ses ce cette que qu qui en".split())
UNITES = ("secondes", "seconde", "minutes", "minute", "heures", "jours", "fois", "personnes", "mots", "ans", "euros")


def _jetons(texte: str) -> list[str]:
    return [n for n in (normaliser_mot(m) for m in re.split(r"[\s'’\-]+", texte)) if n]


def _propre(texte: str) -> str:
    t = re.sub(r"\s+", " ", texte).strip(" ,;:.-–—«»\"“”")
    return t[:1].upper() + t[1:] if t else t


def _raccourcir(texte: str, mots_max: int = 6) -> str:
    """Garde le début utile d'une phrase (avant la 1re virgule, au plus N mots, sans finir sur « de », « les »…)."""
    t = re.split(r"[,;:.!?]", texte.strip())[0]
    mots = t.split()[:mots_max]
    while len(mots) > 2 and normaliser_mot(mots[-1]) in FINS_FAIBLES:
        mots.pop()
    return _propre(" ".join(mots))


def _nombre(mot: str) -> float | None:
    t = mot.strip(" ,.!?;:%«»")
    if re.fullmatch(r"\d+([.,]\d+)?", t):
        return float(t.replace(",", "."))
    n = NOMBRES_LETTRES.get(normaliser_mot(mot))
    return float(n) if n and n.isdigit() else None


# ---------------------------------------------------------------------------
#  Phrases avec leur temps (transcription, ou script.txt recalé sur la voix)
# ---------------------------------------------------------------------------

def _phrases_transcription(plan: dict) -> list[dict]:
    mots = plan["mots"]
    phrases, i = [], 0
    for p in plan["phrases"]:
        idx = []
        while i < len(mots) and mots[i]["debut"] < p["fin"] + 1e-3:
            if mots[i]["debut"] >= p["debut"] - 1e-3:
                idx.append(i)
            i += 1
        if idx:
            phrases.append({"texte": p["texte"], "debut": p["debut"], "fin": p["fin"], "mots": idx, "balise": None})
    return phrases


def _recaler_texte(texte: str, plan: dict, depuis: int = 0) -> list[int] | None:
    """Indices des mots de la transcription qui correspondent à `texte` (recherche approchée)."""
    cible = _jetons(texte)
    if not cible:
        return None
    mots = plan["mots"]
    jet = [normaliser_mot(m["texte"]) for m in mots]
    n = len(cible)
    meilleur, score = None, 0.0
    for a in range(depuis, max(depuis + 1, len(jet) - max(1, n // 2))):
        for longueur in {n, max(1, n - 1), n + 1}:
            fen = jet[a:a + longueur]
            r = difflib.SequenceMatcher(None, cible, fen, autojunk=False).ratio()
            if r > score:
                meilleur, score = list(range(a, min(len(mots), a + longueur))), r
    return meilleur if score >= 0.55 else None


def _phrases_script(script: str, plan: dict) -> list[dict]:
    """Découpe script.txt en phrases (avec balises éventuelles) et les place sur la voix."""
    phrases, curseur = [], 0
    for num_par, paragraphe in enumerate(re.split(r"\n\s*\n", script)):
        balise = None
        m = re.search(r"\[\s*([a-zéèàç\-_ ]+?)\s*(?::\s*([^\]]+))?\]", paragraphe, re.I)
        if m:
            nom = unicodedata.normalize("NFKD", m.group(1).lower()).encode("ascii", "ignore").decode()
            nom = re.sub(r"[^a-z]", "", nom)
            nom = {"avantapres": "avant_apres", "chiffre": "jauge", "schema": "etapes"}.get(nom, nom)
            if nom in TYPES:
                balise = {"type": nom, "precision": (m.group(2) or "").strip()}
            paragraphe = paragraphe.replace(m.group(0), " ")
        morceaux = [s for s in re.split(r"(?<=[.!?…])\s+", paragraphe.strip()) if s.strip()]
        for k, s in enumerate(morceaux):
            idx = _recaler_texte(s, plan, curseur)
            if not idx:
                continue
            curseur = idx[-1]
            mots = plan["mots"]
            phrases.append({"texte": s.strip(), "debut": mots[idx[0]]["debut"], "fin": mots[idx[-1]]["fin"],
                            "mots": idx, "balise": balise, "paragraphe": num_par if balise else None,
                            "premiere": k == 0})
    return phrases


def trouver_script(source: Path) -> Path | None:
    for c in (source.with_suffix(".txt"), source.with_name(source.stem + "_script.txt"),
              source.with_name("script.txt")):
        if c.is_file():
            return c
    return None


# ---------------------------------------------------------------------------
#  Détection des moments à animer
# ---------------------------------------------------------------------------

MARQUEURS = [
    ("liste", [{"un", "une", "1"}, {"deux", "2"}, {"trois", "3"}, {"quatre", "4"}]),
    ("liste", [{"premièrement", "premier", "première"}, {"deuxièmement", "deuxième", "second", "seconde"},
               {"troisièmement", "troisième"}, {"quatrièmement", "quatrième"}]),
    ("etapes", [{"dabord", "premièrement", "commence"}, {"ensuite", "puis", "après"}, {"enfin", "finalement"}]),
]


def _marqueur(phrase: dict, ensembles) -> int | None:
    """Rang du mot d'énumération qui ouvre la phrase (« Un, », « Ensuite, »…), sinon None."""
    bruts = [m for m in phrase["texte"].split() if normaliser_mot(m) not in ("et", "la", "le", "alors")]
    if not bruts:
        return None
    premier = bruts[0]
    n = normaliser_mot(premier.replace("’", "'").replace("'", ""))
    for rang, ens in enumerate(ensembles):
        if n in ens:
            # un chiffre seul doit être suivi d'une ponctuation (« Un, » mais pas « Un jour » ni « Quatre-vingts »)
            if n in ("un", "une", "deux", "trois", "quatre", "1", "2", "3", "4") and not re.search(r"[,:.)]$", premier):
                return None
            return rang
    return None


def _sans_marqueur(texte: str) -> str:
    t = re.sub(r"^\s*(et\s+)?(alors\s+)?(le |la )?(un|une|deux|trois|quatre|\d[.)]?|premi[eè]rement|deuxi[eè]mement|"
               r"troisi[eè]mement|premi[eè]re?|deuxi[eè]me|second[e]?|troisi[eè]me|quatri[eè]me|d'abord|d’abord|"
               r"ensuite|puis|apr[eè]s|enfin|finalement)\b[\s,:.]*", "", texte, flags=re.I)
    return _raccourcir(t, 6)


def _titre_annonce(phrase: dict | None, n: int) -> str | None:
    if not phrase:
        return None
    jet = phrase["texte"].split()
    for k, m in enumerate(jet):
        v = _nombre(m)
        if v is not None and int(v) == n:
            reste = " ".join(jet[k + 1:k + 4])
            return _propre(f"{n} {re.split(r'[,.!?:;]', reste)[0]}").upper()
    return None


def _moments(indices_debut: list[int], plan: dict, debut: float) -> list[float]:
    return [round(max(0.25, plan["mots"][i]["debut"] - debut), 2) for i in indices_debut]


def _cadrer(ins: dict, fin_parole: float, reglages: dict) -> dict:
    r = reglages["inserts"]
    duree = min(r["duree_max"], max(r["duree_min"], fin_parole - ins["debut"] + 0.6))
    ins["duree"] = round(duree, 2)
    if ins.get("moments"):
        limite = duree - 1.0
        if ins["moments"][-1] > limite:  # tout doit apparaître avant la fin de l'insert
            f = limite / ins["moments"][-1]
            ins["moments"] = [round(m * f, 2) for m in ins["moments"]]
    return ins


def _ajuster_duree(ins: dict, duree: float) -> None:
    ancien = ins["duree"]
    ins["duree"] = duree
    if ins.get("moments"):
        f = (duree - 1.0) / max(1e-6, ancien - 1.0)
        ins["moments"] = [round(min(m, m * f), 2) for m in ins["moments"]]


def _candidats_enumerations(phrases, plan, reglages):
    trouves = []
    for type_ins, ensembles in MARQUEURS:
        i = 0
        while i < len(phrases):
            if _marqueur(phrases[i], ensembles) != 0:
                i += 1
                continue
            suite, attendu, j = [i], 1, i + 1
            while j < len(phrases) and attendu < len(ensembles) and j - suite[-1] <= 2:
                if _marqueur(phrases[j], ensembles) == attendu:
                    suite.append(j)
                    attendu += 1
                j += 1
            if len(suite) >= 2:
                n = len(suite)
                annonce = phrases[i - 1] if i > 0 else None
                t0 = phrases[i]["debut"]
                debut = annonce["debut"] if annonce and t0 - annonce["debut"] < 2.5 else t0 - 0.3
                elements = [_sans_marqueur(phrases[k]["texte"]) for k in suite]
                ins = {"type": type_ins, "debut": round(max(0.0, debut), 2), "elements": elements}
                titre = _titre_annonce(annonce, n)
                if not titre and annonce and t0 - annonce["fin"] < 1.5:
                    titre = _raccourcir(annonce["texte"], 5).upper()
                if titre:
                    ins["titre"] = titre
                ins["moments"] = _moments([phrases[k]["mots"][0] for k in suite], plan, ins["debut"])
                fin = phrases[suite[-1]]["fin"]
                trouves.append((6.0, _cadrer(ins, min(fin, ins["debut"] + reglages["inserts"]["duree_max"]), reglages),
                                phrases[i]["texte"]))
                i = suite[-1] + 1
            else:
                i += 1
    return trouves


RE_AVANT_APRES = [
    r"au lieu de dire[\s,:]+(?P<a>.+?)[,;]?\s+dis(?:-le)?(?: plutôt)?[\s,:]+(?P<b>.+)",
    r"ne dis (?:pas|jamais|plus)[\s,:]+(?P<a>.+?)[,;.]?\s+dis(?: plutôt)?[\s,:]+(?P<b>.+)",
    r"remplace[\s,:]+(?P<a>.+?)\s+par[\s,:]+(?P<b>.+)",
    r"(?:arrête|évite) de dire[\s,:]+(?P<a>.+?)[,;.]\s+dis(?: plutôt)?[\s,:]+(?P<b>.+)",
    r"pas\s+(?P<a>«.+?»|\".+?\")\s*,?\s*mais\s+(?P<b>«.+?»|\".+?\")",
]
RE_CITATION = [
    r"(?i:comme (?:le )?disait|comme l'a dit|comme l’a dit|selon)\s+(?P<auteur>[A-ZÉ][\w'’\-]+(?:\s+(?:de\s+|d')?[A-ZÉ][\w'’\-]+)*)\s*[,:]?\s*(?P<texte>.+)",
    r"(?P<auteur>[A-ZÉ][\w'’\-]+(?:\s+(?:de\s+)?[A-ZÉ][\w'’\-]+)*)\s+(?:disait|a dit|écrivait|répétait)\s*[,:]?\s*(?P<texte>.+)",
]


def _candidat_avant_apres(phrases, k):
    texte = phrases[k]["texte"] + (" " + phrases[k + 1]["texte"] if k + 1 < len(phrases) else "")
    for motif in RE_AVANT_APRES:
        m = re.search(motif, texte, re.I)
        if m and m.start() < len(phrases[k]["texte"]):
            a, b = _raccourcir(m.group("a"), 8), _raccourcir(m.group("b"), 8)
            if a and b:
                return {"type": "avant_apres", "debut": round(phrases[k]["debut"], 2), "avant": a, "apres": b}
    return None


def _candidat_citation(phrases, k, plan, auteur=None, force=False):
    p = phrases[k]
    texte = p["texte"]
    m = None
    for motif in RE_CITATION:
        m = re.search(motif, texte)
        if m:
            break
    if m:
        auteur = auteur or _propre(m.group("auteur"))
        texte = m.group("texte")
        if len(texte.split()) < 3 and k + 1 < len(phrases):
            texte = phrases[k + 1]["texte"]
    elif not force:
        return None
    guillemets = re.search(r"[«\"“](.+?)[»\"”]", texte)
    texte = _propre(guillemets.group(1) if guillemets else texte)
    if not (3 <= len(texte.split()) <= 22):
        return None
    ins = {"type": "citation", "debut": round(max(0.0, p["debut"] - 0.2), 2), "texte": texte}
    if auteur:
        ins["auteur"] = auteur
    idx = _recaler_texte(texte, plan, p["mots"][0])
    if idx and len(idx) == len(texte.split()):
        ins["moments"] = _moments(idx, plan, ins["debut"])
    return ins


def _candidat_jauge(phrases, k):
    p = phrases[k]
    jet = p["texte"].split()
    for j, m in enumerate(jet):
        v = _nombre(m)
        if v is None or v < 2:
            continue
        suite = " ".join(normaliser_mot(x) for x in jet[j + 1:j + 3])
        if "%" in m or suite.startswith("pour cent") or suite.startswith("pourcent"):
            reste = jet[j + 3:] if suite.startswith("pour cent") else jet[j + 2:]
            return {"type": "jauge", "debut": round(p["debut"], 2), "valeur": v, "unite": "%",
                    "libelle": _raccourcir(" ".join(reste), 7) or None}
        unite = normaliser_mot(jet[j + 1]) if j + 1 < len(jet) else ""
        if unite in UNITES:
            return {"type": "jauge", "debut": round(p["debut"], 2), "valeur": v, "unite": unite,
                    "libelle": _raccourcir(" ".join(jet[:j]) or " ".join(jet[j + 2:]), 7) or None, "barre": False}
    return None


def _fin_phrase(phrases, k, n=1):
    return phrases[min(len(phrases) - 1, k + n - 1)]["fin"]


def proposer(plan: dict, reglages: dict, script: str | None) -> list[dict]:
    r = reglages["inserts"]
    duree = plan["duree_finale"]
    phrases = _phrases_script(script, plan) if script else []
    if script and len(phrases) < max(2, len(plan["phrases"]) // 3):
        attention("script.txt ne correspond pas assez à ce qui est dit : je me base sur la transcription.")
        phrases = []
    if not phrases:
        phrases = _phrases_transcription(plan)

    candidats: list[tuple[float, dict, str]] = []
    # 1) Moments imposés dans script.txt avec une balise [liste], [citation: Auteur]...
    vus = set()
    for k, p in enumerate(phrases):
        b = p.get("balise")
        if not b or p["paragraphe"] in vus:
            continue
        vus.add(p["paragraphe"])
        groupe = [x for x in range(k, len(phrases)) if phrases[x].get("paragraphe") == p["paragraphe"]]
        ins = None
        if b["type"] in ("liste", "etapes"):
            sous = [phrases[x] for x in groupe]
            # les points = phrases qui commencent par « Un, », « Ensuite »… ; sinon tout sauf la phrase d'annonce
            marques = [x for x in sous if any(_marqueur(x, ens) is not None for _, ens in MARQUEURS)]
            points = marques if len(marques) >= 2 else (sous[1:] or sous)
            ins = {"type": b["type"], "debut": round(p["debut"], 2),
                   "elements": [_sans_marqueur(x["texte"]) for x in points][:4]}
            titre = b["precision"] or (_raccourcir(sous[0]["texte"], 5) if sous[0] not in points else "")
            if titre:
                ins["titre"] = titre.upper()
            ins["moments"] = _moments([x["mots"][0] for x in points[:4]], plan, ins["debut"])
        elif b["type"] == "citation":
            ins = _candidat_citation(phrases, k, plan, auteur=b["precision"] or r.get("signature"), force=True)
        elif b["type"] == "avant_apres":
            ins = _candidat_avant_apres(phrases, k) or (
                {"type": "avant_apres", "debut": round(p["debut"], 2), "avant": _raccourcir(phrases[k]["texte"], 8),
                 "apres": _raccourcir(phrases[min(k + 1, len(phrases) - 1)]["texte"], 8)})
        elif b["type"] == "jauge":
            ins = _candidat_jauge(phrases, k)
        if ins:
            candidats.append((100.0, _cadrer(ins, phrases[groupe[-1]]["fin"], reglages), p["texte"]))

    # 2) Détection automatique
    candidats += _candidats_enumerations(phrases, plan, reglages)
    for k, p in enumerate(phrases):
        for fabrique, note, nb in ((lambda: _candidat_avant_apres(phrases, k), 5.5, 2),
                                    (lambda: _candidat_citation(phrases, k, plan), 5.0, 2),
                                    (lambda: _candidat_jauge(phrases, k), 4.5, 1)):
            ins = fabrique()
            if ins:
                candidats.append((note, _cadrer(ins, _fin_phrase(phrases, k, nb), reglages), p["texte"]))

    # 3) Roue de secours : les phrases les plus fortes deviennent des citations signées
    for k, p in enumerate(phrases):
        s, _ = importance({"texte": p["texte"], "mots": p["mots"]}, plan["mots"], k, len(phrases))
        n = len(p["texte"].split())
        if 6 <= n <= 18 and k > 0 and any(normaliser_mot(w) in MOTS_FORTS for w in p["texte"].split()):
            ins = _candidat_citation(phrases, k, plan, auteur=r.get("signature"), force=True)
            if ins:
                candidats.append((1.0 + s / 10, _cadrer(ins, p["fin"], reglages), p["texte"]))

    return choisir(candidats, duree, reglages)


def choisir(candidats, duree, reglages) -> list[dict]:
    r = reglages["inserts"]
    budget = r["part_max_video"] * duree
    choisis: list[dict] = []
    types_pris: list[str] = []
    restants = list(candidats)
    while restants and len(choisis) < r["nombre_max"]:
        # on préfère varier les types d'inserts
        restants.sort(key=lambda c: -(c[0] - 1.5 * types_pris.count(c[1]["type"])))
        note, ins, phrase = restants.pop(0)
        a, b = ins["debut"], ins["debut"] + ins["duree"]
        if a < r["debut_min"] or b > duree - 1.0:
            continue
        if any(not (b + r["ecart_min"] <= c["debut"] or c["debut"] + c["duree"] + r["ecart_min"] <= a) for c in choisis):
            continue
        ins = dict(ins)
        reste = budget - sum(c["duree"] for c in choisis)
        if ins["duree"] > reste + 1e-6 and note < 100:
            if reste < r["duree_min"]:
                continue
            _ajuster_duree(ins, round(reste, 2))  # on raccourcit l'insert pour tenir dans le budget
        ins["phrase_dite"] = phrase
        choisis.append(ins)
        types_pris.append(ins["type"])
    return sorted(choisis, key=lambda c: c["debut"])


# ---------------------------------------------------------------------------
#  Fichier storyboard.yaml (lisible et modifiable)
# ---------------------------------------------------------------------------

ENTETE = """# =====================================================================
#  STORYBOARD des inserts animés — {nom}
#  Relis, modifie les textes, supprime un bloc pour enlever un insert,
#  puis relance le montage (monter.bat) pour fabriquer la vidéo.
#
#  type : citation, avant_apres, etapes, liste ou jauge
#  debut : moment dans la vidéo FINALE (secondes) — duree : 3 à 5 secondes
#  phrase_dite : ce que tu dis à ce moment-là (pour info, pas affiché)
#  moments : quand chaque élément apparaît (secondes après le début de l'insert)
#            -> enlève la ligne pour un rythme régulier automatique
#
#  Champs par type :
#   citation    : texte, auteur
#   avant_apres : avant, apres
#   etapes      : titre (facultatif), elements (3 éléments)
#   liste       : titre (facultatif), elements (2 à 4 éléments)
#   jauge       : valeur, unite (%, secondes…), libelle, barre (true/false)
#  Pour ne mettre AUCUN insert : remplace tout par   inserts: []
# =====================================================================
"""


def empreinte_decoupage(plan: dict) -> str:
    return hashlib.sha1(json.dumps(plan["segments"]).encode()).hexdigest()[:10]


def _simple(v):
    """Nombres « numpy » -> nombres simples (lisibles dans le fichier YAML)."""
    if isinstance(v, list):
        return [_simple(x) for x in v]
    if isinstance(v, float):
        return int(v) if float(v).is_integer() and v > 1 else round(float(v), 2)
    return v


def ecrire_storyboard(chemin: Path, inserts: list[dict], plan: dict, nom: str) -> None:
    propres = []
    for ins in inserts:
        ordre = ["type", "debut", "duree", "phrase_dite", "titre", "texte", "auteur", "avant", "apres", "elements",
                 "valeur", "unite", "libelle", "barre", "moments"]
        propres.append({k: _simple(ins[k]) for k in ordre if ins.get(k) is not None})
    corps = yaml.safe_dump({"decoupage": empreinte_decoupage(plan), "inserts": propres},
                           allow_unicode=True, sort_keys=False, width=110)
    chemin.write_text(ENTETE.format(nom=nom) + corps, encoding="utf-8")


def lire_storyboard(chemin: Path, plan: dict, reglages: dict) -> list[dict]:
    try:
        donnees = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ErreurMontage(f"storyboard.yaml contient une erreur de mise en forme :\n{e}\n"
                            "Astuce : vérifie les guillemets et les tirets en début de ligne.") from e
    if donnees.get("decoupage") and donnees["decoupage"] != empreinte_decoupage(plan):
        attention("Le storyboard a été fait pour un ancien découpage de la vidéo : les temps peuvent être décalés. "
                  "Supprime storyboard.yaml pour qu'il soit refait.")
    fps = reglages["export"]["fps"]
    inserts = []
    for k, ins in enumerate(donnees.get("inserts") or [], 1):
        t = ins.get("type")
        if t not in TYPES:
            attention(f"Insert n°{k} ignoré : type « {t} » inconnu (choix : {', '.join(TYPES)}).")
            continue
        manquant = {"citation": ["texte"], "avant_apres": ["avant", "apres"], "etapes": ["elements"],
                    "liste": ["elements"], "jauge": ["valeur"]}[t]
        if any(not ins.get(c) and ins.get(c) != 0 for c in manquant):
            attention(f"Insert n°{k} ({t}) ignoré : il manque {', '.join(manquant)}.")
            continue
        debut = round(float(ins.get("debut", 0)) * fps) / fps
        duree = round(min(8.0, max(1.5, float(ins.get("duree", 4)))) * fps) / fps
        if debut + duree > plan["duree_finale"]:
            duree = round((plan["duree_finale"] - debut) * fps) / fps
        if duree < 1.0:
            attention(f"Insert n°{k} ignoré : il commence après la fin de la vidéo.")
            continue
        if inserts and debut < inserts[-1]["debut"] + inserts[-1]["duree"] + 0.5:
            attention(f"Insert n°{k} ignoré : il chevauche le précédent.")
            continue
        propre = dict(ins, debut=debut, duree=duree)
        if t in ("etapes", "liste"):
            propre["elements"] = [str(e) for e in ins["elements"]][:4 if t == "liste" else 3]
        inserts.append(propre)
    return sorted(inserts, key=lambda i: i["debut"])


# ---------------------------------------------------------------------------
#  Mise en page (bulle, carte) et effets sur le plan
# ---------------------------------------------------------------------------

def geometrie(reglages: dict) -> dict:
    ex, r, st = reglages["export"], reglages["inserts"], reglages["sous_titres"]
    W, H = ex["largeur"], ex["hauteur"]
    D = int(round(r["bulle_taille"] * W / 2)) * 2
    cy = int(r["bulle_position"] * H)
    haut_carte = cy + D // 2 + r["bulle_contour"] + 16
    haut_sous_titres = int(st["position_verticale"] * H - st["taille"] * 0.8)
    hauteur_carte = (haut_sous_titres - 12 - haut_carte) // 2 * 2
    if hauteur_carte < 420:
        attention("Peu de place pour les cartes : réduis la bulle (bulle_taille) ou descends les sous-titres.")
    cadrage = int(round(r["bulle_cadrage"] * W / 2)) * 2
    return {"W": W, "H": H, "D": D, "cy": cy, "y_carte": haut_carte, "h_carte": max(320, hauteur_carte),
            "cadrage": cadrage, "y_visage": int(r.get("bulle_visage", 0.34) * H)}


def appliquer_au_plan(plan: dict, inserts: list[dict], reglages: dict) -> dict:
    """Pendant un insert : pas de zoom, pas de titre/chiffre géant ; un whoosh discret à l'entrée."""
    p = dict(plan)
    zones = [(i["debut"], i["debut"] + i["duree"]) for i in inserts]

    def libre(a, b, marge):
        return all(b <= s - marge or a >= e + marge for s, e in zones)

    p["zooms"] = [z for z in plan.get("zooms", []) if libre(z["debut"], z["fin"], 0.5)]
    p["animations"] = [a for a in plan.get("animations", []) if libre(a["debut"], a["fin"], 0.3)]
    sons = list(plan.get("sons", []))
    if reglages["inserts"].get("whoosh", True) and reglages["bruitages"].get("actif", True):
        for s, _ in zones:
            t = max(0.0, s - 0.08)
            sons = [x for x in sons if abs(x["temps"] - t) >= 1.0]
            sons.append({"type": "whoosh", "temps": round(t, 3)})
    p["sons"] = sorted(sons, key=lambda x: x["temps"])
    p["inserts"] = [{"debut": i["debut"], "duree": i["duree"], "type": i["type"]} for i in inserts]
    return p


# ---------------------------------------------------------------------------
#  Images fixes : fond, masque rond, contour bleu de la bulle
# ---------------------------------------------------------------------------

def _png(chemin: Path, image: np.ndarray, fmt: str) -> None:
    h, w = image.shape[:2]
    brut = chemin.with_suffix(".raw")
    brut.write_bytes(np.ascontiguousarray(image).astype(np.uint8).tobytes())
    lancer(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", fmt, "-s", f"{w}x{h}",
            "-i", brut, "-frames:v", "1", chemin])
    brut.unlink()


def _hex(c: str) -> np.ndarray:
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def preparer_images(dossier: Path, g: dict, reglages: dict) -> dict:
    r = reglages["inserts"]
    rng = np.random.default_rng(3)
    W, H, D = g["W"], g["H"], g["D"]
    # Fond anthracite avec un très léger halo au centre (plus « premium » qu'un aplat)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.45) / H) ** 2)
    halo = np.clip(1 - dist / 0.75, 0, 1) ** 2
    base, clair = _hex("#111318"), _hex("#1B1F28")
    fond = base[None, None, :] + (clair - base)[None, None, :] * halo[..., None]
    fond += rng.uniform(-0.6, 0.6, size=(H, W, 1))  # léger grain : évite les bandes
    _png(dossier / "fond.png", np.clip(fond, 0, 255), "rgb24")
    # Masque rond (bords adoucis)
    yy, xx = np.mgrid[0:D, 0:D].astype(np.float32)
    rayon = np.sqrt((xx - D / 2 + 0.5) ** 2 + (yy - D / 2 + 0.5) ** 2)
    _png(dossier / "masque.png", np.clip(D / 2 - rayon, 0, 1) * 255, "gray")
    # Contour bleu + ombre douce autour de la bulle
    e = r["bulle_contour"]
    marge = e + 30
    R = D + 2 * marge
    yy, xx = np.mgrid[0:R, 0:R].astype(np.float32)
    rayon = np.sqrt((xx - R / 2 + 0.5) ** 2 + (yy - R / 2 + 0.5) ** 2)
    anneau = np.clip(rayon - (D / 2 - 1), 0, 1) * np.clip(D / 2 + e - rayon, 0, 1)
    ombre = np.clip(1 - (rayon - D / 2 - e) / 26, 0, 1) ** 2 * 0.45 * (rayon > D / 2 + e - 1)
    bleu = _hex(reglages["sous_titres"]["couleur_mot_cle"])
    rgba = np.zeros((R, R, 4), np.float32)
    rgba[..., :3] = bleu * anneau[..., None]
    rgba[..., 3] = np.clip(anneau + ombre * (1 - anneau), 0, 1) * 255
    rgba[..., :3] = np.where(rgba[..., 3:4] > 0, rgba[..., :3] / np.maximum(rgba[..., 3:4] / 255, 1e-3), 0)
    _png(dossier / "anneau.png", np.clip(rgba, 0, 255), "rgba")
    return {"fond": dossier / "fond.png", "masque": dossier / "masque.png", "anneau": dossier / "anneau.png", "R": R}


# ---------------------------------------------------------------------------
#  Fabrication des cartes par Remotion
# ---------------------------------------------------------------------------

def _empreinte_modeles() -> str:
    h = hashlib.sha1()
    for p in sorted((DOSSIER_REMOTION / "src").rglob("*")):
        if p.is_file():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:8]


def proprietes(ins: dict, g: dict, reglages: dict) -> dict:
    st = reglages["sous_titres"]
    props = {"type": ins["type"], "duree": ins["duree"], "largeur": g["W"], "hauteur": g["h_carte"],
             "couleurs": {"anthracite": "#111318", "carte": "#1A1D25", "bleu": st["couleur_mot_cle"],
                          "blanc": "#FFFFFF"}}
    for k in ("texte", "auteur", "avant", "apres", "titre", "elements", "moments", "valeur", "unite", "libelle",
              "max", "barre"):
        if ins.get(k) is not None:
            props[k] = ins[k]
    if "valeur" in props:
        props["valeur"] = float(props["valeur"])
    return props


def fabriquer_cartes(inserts: list[dict], g: dict, reglages: dict, dossier: Path) -> list[Path]:
    node = shutil.which("node")
    if node is None:
        raise ErreurMontage("Node.js est introuvable (nécessaire pour les inserts animés). Relance l'installateur, "
                            "ou mets « actif: false » dans la rubrique inserts de reglages.yaml.")
    if not (DOSSIER_REMOTION / "node_modules" / "@remotion" / "renderer").exists():
        raise ErreurMontage("Remotion n'est pas installé. Relance l'installateur (installer_windows.bat).")
    dossier.mkdir(parents=True, exist_ok=True)
    version = _empreinte_modeles()
    sorties, a_faire = [], []
    for ins in inserts:
        props = proprietes(ins, g, reglages)
        cle = hashlib.sha1((version + json.dumps(props, sort_keys=True)).encode()).hexdigest()[:12]
        sortie = dossier / f"carte_{ins['type']}_{cle}.mov"
        sorties.append(sortie)
        if not sortie.exists():
            a_faire.append({"props": props, "sortie": str(sortie.resolve())})
    if not a_faire:
        info("Cartes animées déjà fabriquées : je les réutilise")
        return sorties
    info(f"Fabrication de {len(a_faire)} carte(s) animée(s) avec Remotion")
    processus = reglages["inserts"].get("processus", "auto")
    travail = dossier / "cartes_a_faire.json"
    travail.write_text(json.dumps({"inserts": a_faire, "processus": None if processus == "auto" else int(processus)},
                                  ensure_ascii=False), encoding="utf-8")
    env = None
    if reglages["inserts"].get("navigateur"):
        import os
        env = dict(os.environ, MONTAGE_NAVIGATEUR=reglages["inserts"]["navigateur"])
    res = subprocess.run([node, "rendre.mjs", str(travail.resolve())], cwd=DOSSIER_REMOTION, env=env,
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    for ligne in res.stdout.splitlines():
        if ligne.strip().startswith("•"):
            print("  " + ligne.strip(), flush=True)
    if res.returncode != 0 or any(not Path(a["sortie"]).exists() for a in a_faire):
        raise ErreurMontage("Remotion n'a pas réussi à fabriquer les cartes :\n" + (res.stderr or res.stdout)[-2500:])
    return sorties
