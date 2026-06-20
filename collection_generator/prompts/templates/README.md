# Templates de prompts (optionnel)

Ce dossier peut accueillir des variantes de prompt par style ou par univers.

Par défaut, le générateur utilise :

- `prompts/base_prompt.txt` — le prompt maître verrouillé (parties fixes +
  emplacements `[VARIABLE]` remplis automatiquement) ;
- `prompts/negative_prompt.txt` — le prompt négatif officiel.

Pour créer un template spécifique à un style, ajoutez ici un fichier nommé
`STYLE_<CODE>.txt` (ex. `STYLE_SAMURAI.txt`). S'il existe, le `prompt_builder`
l'utilisera à la place du prompt de base pour ce style — tout en conservant les
mêmes emplacements `[VARIABLE]` afin de ne jamais casser la cohérence.

> Tant qu'aucun template spécifique n'est présent, c'est le prompt maître qui
> s'applique à toute la collection (recommandé pour une cohérence stricte).
