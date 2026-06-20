# Fiche officielle du Lionceau Maître

Cette fiche décrit le **modèle maître immuable** de la collection, établi à partir
de l'**image de référence officielle** fournie par le client. Tout rendu de la
collection doit conserver cette identité visuelle ; seuls les **traits variables**
autorisés (pelage, yeux, vêtements, couvre-chef, accessoires, métier, objet unique)
peuvent changer.

> **Image de référence officielle** : à déposer dans ce dossier sous le nom
> `reference/master_lion_cub.png`. (Le générateur fonctionne à partir du prompt
> verrouillé ; l'image sert de contrôle visuel et de support pour la cohérence.)

## Caractéristiques verrouillées (observées sur la référence)

| Élément | Caractéristique officielle |
|---|---|
| Espèce | Bébé lionceau anthropomorphe (jamais lion adulte, tigre, ours, chat) |
| Posture | Debout sur deux jambes, droite et stable |
| Vue | Strictement de face, regard droit dans la caméra |
| Cadrage | Corps entier, tête aux pieds, centré, marges égales |
| Tête | Ronde, légèrement surdimensionnée (proportions enfantines) |
| Oreilles | Grandes, rondes, intérieur tufté plus clair |
| Yeux | Grands, ronds, expressifs, symétriques, léger reflet |
| Museau | Court et doux, petit nez triangulaire foncé |
| Marquages | Menton / poitrail / ventre plus clairs, fins points de moustaches |
| Membres | Bras courts le long du corps, jambes courtes |
| Pattes | Grosses pattes félines, 4 doigts arrondis, **aucune main humaine** |
| Pieds | Plantigrades, plats, parallèles, posés au même niveau |
| Absences | **Pas de queue, pas de crinière adulte, pas d'anatomie humaine** |
| Expression | Calme, douce, amicale, bouche fermée |
| Fond | Blanc pur #FFFFFF, studio propre, légère ombre de contact sous les pieds |
| Lumière | Studio douce et homogène, balance des blancs neutre |
| Rendu | 3D premium ultra-réaliste, fourrure très détaillée |
| Format | Carré 1:1, 2048 × 2048 |

## Où ces règles sont appliquées dans le code

- **`prompts/base_prompt.txt`** — blocs `LOCKED` (morphologie, marqueurs
  d'identité, cadrage, fond, lumière). Injecte uniquement les champs variables
  `{fur}`, `{eyes}`, `{style}`, `{object}`, `{headwear}`, `{shoes}`, `{background}`.
- **`prompts/negative_prompt.txt`** — interdits (mains humaines, queue, crinière
  adulte, marques, texte, vues de profil, etc.).
- **`src/quality_control.py`** — contrôles automatiques (format carré, objet
  unique, cohérence style/objet, présence des règles verrouillées).

## Traits variables autorisés (et eux seuls)

Couleur du pelage · couleur des yeux (avec hétérochromie possible) · vêtements ·
couvre-chef · petits accessoires portés · métier / rôle / univers ·
**un seul objet tenu en main**.
