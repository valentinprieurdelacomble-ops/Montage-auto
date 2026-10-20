# Montage-auto

Système de montage vidéo automatique pour un créateur de contenu francophone (non développeur).
- Toujours répondre en français, simplement, sans jargon.
- Pour monter une vidéo : utiliser le skill `montage-viral` (.claude/skills/montage-viral/SKILL.md).
- Tous les réglages sont dans `reglages.yaml` ; le moteur est dans `montage/`, la commande est `monter.py`.
- Les cartes animées (inserts) sont des compositions Remotion dans `remotion/src/` ; le skill `remotion-best-practices` donne les bonnes pratiques Remotion.
- Ne jamais dire qu'une vidéo est prête sans « ✅ Vidéo contrôlée » ET sans avoir regardé `travail/<nom>/planche_controle.jpg`.
- Le système doit rester portable Windows / Mac : pathlib, pas de chemins en dur, FFmpeg appelé sans shell.
