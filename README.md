# Montage auto — vidéo brute → vidéo prête à publier

Tu déposes ta vidéo filmée à l'iPhone dans `a_monter/`, tu lances une commande,
et tu récupères dans `montees/` une vidéo prête pour Instagram, TikTok et YouTube Shorts.

## Ce que fait le montage

1. **Coupe les blancs et les « euh »** en gardant une petite respiration naturelle (jamais au milieu d'un mot).
2. **Transcrit ta voix mot par mot** (Whisper, en français), recalée sur la vidéo coupée : synchro à l'image près.
3. **Sous-titres dynamiques** : 1 à 3 mots, gros, Inter ExtraBold blanc, le mot-clé de chaque phrase en bleu #246BFD, petit pop discret.
4. **Zooms** doux (115 %) sur les phrases fortes et **punch-in** secs, maximum un toutes les 5 à 8 s.
5. **Bruitages discrets** : whoosh sur certains zooms, pop sur certains mots-clés.
6. **1 ou 2 animations** : titre d'accroche au début et/ou chiffre géant.
7. **Son de la voix normalisé** (-14 LUFS, sans saturation).
8. **Export** MP4 H.264, 1080x1920, 30 images/s.
9. **Inserts animés** (2 à 3 par minute) : une carte animée occupe le centre pendant 3 à 5 s, ton visage passe
    dans une bulle ronde à contour bleu en haut, puis retour plein écran en fondu. 5 modèles : citation,
    avant/après, schéma en 3 étapes, liste, jauge/chiffre.
10. **Contrôle qualité automatique** : format, durée, synchro, volume, écrans noirs, et une planche d'images à vérifier.

## Installation (une seule fois)

### Windows
1. Télécharge ce dossier sur ton PC (bouton vert **Code > Download ZIP** sur GitHub, puis « Extraire tout »),
   par exemple dans `Documents\Montage-auto`.
2. Double-clique sur **`installer_windows.bat`**.
   - S'il installe Python ou FFmpeg, il te demandera de **fermer la fenêtre et de relancer** le fichier : c'est normal.
   - Si Windows affiche « Windows a protégé votre ordinateur », clique sur **Informations complémentaires > Exécuter quand même**.
3. À la fin, il télécharge le modèle de transcription (≈ 1,5 Go pour « medium ») : laisse tourner.

### Mac (plus tard)
Double-clique sur **`installer_mac.command`** (si le Mac refuse : clic droit > Ouvrir).
Tout le reste fonctionne pareil (`monter.command` au lieu de `monter.bat`).

## Utilisation

**Le plus simple :** dépose ta vidéo dans `a_monter/`, puis double-clique sur `monter.bat`.
Toutes les nouvelles vidéos sont montées une par une.

**Avec Claude Code :** ouvre Claude Code dans ce dossier et dis simplement **« monte ma vidéo »**
(ou « monte la vidéo discours.mov »). Le skill `montage-viral` s'occupe de tout : il analyse,
choisit un titre d'accroche, relit les mots-clés et les zooms, fabrique la vidéo, puis la vérifie
avant de te dire qu'elle est prête.

**En ligne de commande** (pour aller plus loin) :
```
.venv\Scripts\python monter.py ma_video.mov --titre "3 ERREURS À ÉVITER"
.venv\Scripts\python monter.py ma_video.mov --analyse-seulement   (prépare le plan sans fabriquer)
.venv\Scripts\python monter.py ma_video.mov --reprendre           (refait la vidéo depuis le plan)
```

## Les inserts animés et le storyboard

Après la transcription, le système repère les moments à animer (une énumération « un, deux, trois »,
une méthode « d'abord, ensuite, enfin », un « au lieu de dire… dis… », un pourcentage, une citation)
et écrit `travail/<nom>/storyboard.yaml`. **La première fois, le montage s'arrête** pour que tu le relises :
ouvre-le avec le Bloc-notes, change les textes ou les temps, supprime un bloc pour enlever un insert,
puis relance `monter.bat`.

**Ton texte aide** : si tu poses ton script à côté de la vidéo (`a_monter/ma_video.txt`, ou `a_monter/script.txt`),
le système s'en sert (meilleure orthographe, meilleurs moments). Tu peux même imposer un insert en écrivant
une balise au début d'un paragraphe :

```
[citation: Nicolas Boileau] Comme disait Boileau, « ce que l'on conçoit bien s'énonce clairement ».
[avant-après] Au lieu de dire « je vais essayer », dis « je vais le faire ».
[étapes: Ta méthode] D'abord, trouve ton message. Ensuite, construis ton plan. Enfin, répète à voix haute.
[liste: 3 règles] Un, ralentis. Deux, regarde ton public. Trois, fais une pause.
[jauge] 80 % de ton impact vient de ta voix.
```

Les cartes sont fabriquées par **Remotion** (`remotion/`), puis posées sur la vidéo par FFmpeg.
Une carte déjà fabriquée et inchangée est réutilisée : relancer après une petite modification est rapide.

## Régler le style

Tout est dans **`reglages.yaml`** (ouvre-le avec le Bloc-notes) : taille des sous-titres, intensité
des zooms, volume des bruitages, durée minimale des blancs coupés, etc. Chaque ligne est expliquée.

## Où sont les fichiers

| Dossier | Contenu |
|---|---|
| `a_monter/` | tes vidéos brutes |
| `montees/` | les vidéos finales (`<nom>_monte.mp4`) |
| `travail/<nom>/` | transcription, plan du montage (`plan.json`), rapport et planche de contrôle |
| `assets/sfx/` | bruitages (voir `assets/sfx/LISEZMOI.md` pour en trouver) |
| `assets/fonts/` | police Inter (licence libre OFL) |

## Conseils de tournage iPhone

- Filme en **1080p ou 4K, 30 i/s**, en vertical.
- **Désactive la vidéo HDR** (Réglages > Appareil photo > Enregistrer vidéo > Vidéo HDR) : les couleurs
  seront plus fidèles sur Instagram. (Le système sait convertir le HDR, mais le résultat est meilleur sans.)
- Un micro-cravate améliore énormément la coupe des blancs et la transcription.

## Durée de traitement

Sur un PC sans carte graphique NVIDIA, compte environ 3 à 6 minutes pour une vidéo d'une minute
(surtout la transcription, puis les cartes animées). Si c'est trop long : `transcription.modele: small`. Avec une carte NVIDIA, c'est beaucoup plus rapide.

## Qui fait quoi

- **FFmpeg** : coupes, zooms, sous-titres, son, assemblage final (rapide).
- **Remotion** : uniquement les cartes animées. Il dessine chaque image dans un navigateur invisible,
  ce qui est plus lent ; c'est pourquoi il ne fabrique que la carte (pas la vidéo entière), sur fond
  transparent, et réutilise les cartes déjà faites. Sur un PC modeste, compte environ 10 à 40 secondes par carte.
- Remotion est gratuit pour un créateur indépendant (licence payante seulement pour les entreprises de plus de 3 personnes).
