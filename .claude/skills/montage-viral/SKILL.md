---
name: montage-viral
description: Monte automatiquement une vidéo face caméra (éloquence, prise de parole) au format Reels/TikTok/Shorts — coupe des blancs, sous-titres dynamiques, zooms, bruitages, inserts animés (cartes Remotion avec visage en bulle), son normalisé. À utiliser dès que l'utilisateur dit « monte ma vidéo », « monte la vidéo X », « fais le montage », ou dépose une vidéo dans a_monter/.
---

# Montage viral — vidéo brute → vidéo prête à publier

Tu travailles pour un créateur de contenu francophone (éloquence, prise de parole) qui n'est
pas développeur. Parle-lui en français, simplement, sans jargon. Le système est dans ce dépôt :
`monter.py` (commande unique), `montage/` (le moteur), `reglages.yaml` (tous les réglages).

## Règles de style (à respecter quand tu modifies un plan)

- Rythme serré, zéro temps mort, mais une respiration naturelle (~0,1–0,2 s) ; jamais de coupe au milieu d'un mot.
- Sous-titres : 1 à 3 mots, gros, centrés un peu sous le milieu, Inter ExtraBold blanc avec contour anthracite,
  **un seul mot-clé bleu #246BFD par phrase** (le mot qui porte le sens : chiffre, mot fort, chute). Pop discret.
- Zooms : doux (~115 %) sur les phrases importantes, « punch » secs (~112 %) pour casser le rythme.
  **Jamais deux zooms à moins de 5 s**, idéalement un toutes les 5–8 s. Moments : affirmations fortes, chiffres, chutes, questions.
- Bruitages discrets : whoosh sur certains zooms doux, pop/click sur quelques mots-clés. Jamais plus fort que la voix.
- **1 ou 2 animations maximum** : titre d'accroche (3 premières secondes) et/ou chiffre géant.
- Sobre et premium : pas d'emojis, pas de transitions tape-à-l'œil, pas d'effets empilés. Palette : blanc, #246BFD, anthracite #111318.
- Export : MP4 H.264 1080x1920, 30 fps, voix à -14 LUFS sans saturation.

### Inserts animés (motion design)
- **2 à 3 inserts de 3 à 5 s** pour une vidéo d'environ 1 minute ; visage plein écran **80–90 % du temps**.
- Pendant un insert : carte animée au centre, visage dans une **bulle ronde à contour bleu** en haut, sous-titres conservés.
  Entrée et sortie en fondu doux. Jamais d'insert pendant l'accroche (2,5 premières secondes).
- 5 modèles (dossier `remotion/src/inserts/`) :
  1. `citation` : phrase d'orateur écrite mot par mot + auteur (`texte`, `auteur`)
  2. `avant_apres` : phrase faible barrée puis phrase forte (`avant`, `apres`) — phrases courtes, 2 à 7 mots
  3. `etapes` : 3 blocs reliés par une ligne qui se trace (`titre`, `elements` ×3, 2–4 mots chacun)
  4. `liste` : 2 à 4 points au rythme de la voix (`titre`, `elements`, `moments`)
  5. `jauge` : chiffre qui monte + barre (`valeur`, `unite`, `libelle`, `barre`)
- Choisis les moments où une carte **aide à comprendre** (énumération, méthode, contraste, chiffre, citation), pas au hasard.
  Textes de cartes courts et percutants : une carte se lit en 2 secondes.

## Commande Python à utiliser

- Windows : `.venv\Scripts\python.exe monter.py ...`
- Mac : `.venv/bin/python monter.py ...`
(Si `.venv` n'existe pas, l'installation n'a pas été faite : propose de lancer `installer_windows.bat` ou `installer_mac.command`.)

## Déroulé

1. **Trouver la vidéo** dans `a_monter/`. Si l'utilisateur ne précise pas, prends la plus récente
   qui n'a pas encore de `montees/<nom>_monte.mp4`. Si plusieurs sont possibles, demande laquelle.

2. **Analyser** : `python monter.py "<nom>" --analyse-seulement`
   → crée `travail/<nom>/transcription.json` (mots bruts de Whisper) et `travail/<nom>/plan.json`.

3. **Relire et améliorer le plan et le storyboard** (c'est là que tu apportes ton jugement de monteur) :
   - Lis `plan.json` → `phrases`, `mots`, `zooms`, `sons`, `animations`.
   - Corrige les fautes de transcription évidentes dans `mots[].texte` (noms propres, mots mal entendus)
     sans toucher aux temps. Si un mot est vraiment faux, corrige aussi `transcription.json` pour les prochaines fois.
   - Vérifie qu'il y a au plus un `mot_cle: true` par phrase, et que c'est le bon mot (mets `true`/`false`).
   - Vérifie les zooms : bons moments, écart ≥ 5 s, `type` `doux` ou `punch`, `intensite` entre 1.10 et 1.20.
   - **Titre d'accroche** : écris une accroche percutante de 3 à 6 mots en MAJUSCULES qui donne envie de
     rester (promesse, question, chiffre), dans `animations` : `{"type":"titre","texte":"...","debut":0,"fin":2.8}`.
     Elle ne doit pas répéter mot pour mot la première phrase si celle-ci est déjà sous-titrée. Max 2 animations au total.
   - Garde les `sons` cohérents avec les zooms et mots-clés (temps en secondes de la vidéo finale), espacés d'au moins 3 s.
   - Ne modifie jamais `segments` ni `duree_finale` à la main.
   - **Storyboard** (`travail/<nom>/storyboard.yaml`, l'en-tête du fichier explique chaque champ) :
     si `a_monter/<nom>.txt` ou `a_monter/script.txt` existe, il a servi de base (balises possibles dans le script :
     `[citation: Auteur]`, `[avant-après]`, `[étapes: Titre]`, `[liste]`, `[jauge]` devant un paragraphe).
     Vérifie 2–3 inserts bien espacés (≥ 6 s), textes courts sans faute, `debut` = moment où l'idée est dite
     (cherche le temps du mot dans `plan.json` → `mots`), `moments` cohérents avec la voix (secondes depuis le début de l'insert).
     Si aucun moment ne s'y prête, il vaut mieux 1 insert juste que 3 inserts forcés.
   - **Montre le storyboard à l'utilisateur** en quelques lignes (moment, type, texte) et demande son accord avant
     le rendu, sauf s'il a dit d'y aller directement.

4. **Fabriquer** : `python monter.py "<nom>" --reprendre`
   (les cartes sont fabriquées par Remotion puis posées par FFmpeg ; une carte inchangée n'est pas refaite.)
   (Si l'utilisateur veut aller vite et sans relecture : `python monter.py "<nom>"` fait tout d'un coup.)

5. **Vérifier avant de dire que c'est prêt** — obligatoire :
   - La commande doit afficher « ✅ Vidéo contrôlée ». Lis `travail/<nom>/rapport.json` : `pret` doit être `true`.
   - **Regarde l'image** `travail/<nom>/planche_controle.jpg` (outil Read) : sous-titres lisibles, bien placés,
     mot-clé en bleu, titre propre, zooms qui gardent le visage dans le cadre, pas de texte coupé.
     Pour chaque insert : carte entièrement visible et lisible, visage bien cadré dans la bulle (sinon régler
     `inserts.bulle_visage` / `bulle_cadrage`), sous-titres non masqués.
   - Si un contrôle échoue ou si l'image montre un défaut : corrige (plan.json ou reglages.yaml) et refais l'étape 4.
   - Ne dis JAMAIS qu'une vidéo est prête si tu n'as pas vu « ✅ » ET regardé la planche.

6. **Rendre compte** en quelques lignes simples : chemin de la vidéo finale, durée avant/après,
   nombre de coupes, zooms, titre choisi, et ce que tu as corrigé. Propose 1 ou 2 réglages s'il y a un défaut
   récurrent (ex. « les fins de mots sont coupées → monter `seuil_silence_db` à 38 »).

## Problèmes fréquents

| Symptôme | Réglage dans `reglages.yaml` |
|---|---|
| Fins de mots mangées | `coupes.seuil_silence_db` ↑ (36–40) ou `coupes.respiration` ↑ (0.15–0.2) |
| Rythme pas assez serré | `coupes.silence_min` ↓ (0.25) |
| Sous-titres trop gros / trop petits | `sous_titres.taille` |
| Trop de zooms | `zooms.intervalle_min` ↑ |
| Bruitages trop présents | `bruitages.volume_whoosh_db` / `volume_pop_db` ↓ (ex. -26) |
| Transcription lente | `transcription.modele: small` |
| Visage mal cadré dans la bulle | `inserts.bulle_visage` (hauteur du visage, ex. 0.30) et `inserts.bulle_cadrage` (↓ = visage plus gros) |
| Trop / pas assez d'inserts | `inserts.nombre_max`, `inserts.part_max_video`, ou modifier `storyboard.yaml` |
| Pas d'inserts du tout | `inserts.actif: false` |
| Refaire le storyboard | `python monter.py "<nom>" --nouveau-storyboard` |
| Rendu des cartes lent | normal sur un PC modeste (≈ 10–40 s par carte) ; les cartes inchangées sont réutilisées |
| Couleurs délavées (iPhone HDR) | désactiver la vidéo HDR sur l'iPhone, ou vérifier que FFmpeg a `zscale` |

Après un changement de `reglages.yaml` qui touche les coupes ou la transcription, relance **sans** `--reprendre`
(la transcription est mise en cache, ça reste rapide).
