# gta-clip-desk

Scripts Python de clipping GTA 6 : découverte de clips Twitch (streamers autorisés), détection de moments, découpe
verticale 1080x1920 avec sous-titres et hook, bip audio, contrôles (filigrane, règles).

Dérivé de [Bodila51/gtavi-claudecode](https://github.com/Bodila51/gtavi-claudecode) (licence MIT, commit
`dd95d39`, dépôt supprimé depuis), avec des correctifs (`moments.py`, `cut.py`, `check.py`) et des scripts ajoutés
(`accounts.py`, `discover.py`, `watermark_check.py`, `bleep.py`, `sexual_terms.py`). Voir `LICENSE`.

- `requirements.txt` : dépendances minimales du desk automatique.
- `requirements-all.txt` : dépendances complètes de l'original (traduction, voix : `live`, `translate`, etc.).
- `skills/` et `.claude-plugin/` : skills du plugin d'origine pour Claude Code, non utilisés par le passage automatique.
- Les layouts `facecam` et `react` de `cut.py` ont besoin d'un modèle de visage téléchargé.
