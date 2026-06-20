# 🦁 Lionceaux NFT — Générateur de collection

Ce projet crée une **grande collection cohérente** de lionceaux NFT : même
personnage de base, même cadrage, même fond, et seuls quelques traits varient
(pelage, yeux, vêtements/métier, objet tenu). Il génère automatiquement les
**combinaisons uniques**, les **prompts**, les **métadonnées NFT**, la
**rareté**, les **rapports de contrôle qualité** — et, sur autorisation, les
**images** via une API.

> 🟢 **Le mode simulation est le mode par défaut : il ne coûte rien** et ne
> contacte aucune API. On l'utilise pour tout préparer et tout vérifier avant
> de dépenser le moindre euro.

---

## 1. Installer Python

1. Allez sur https://www.python.org/downloads/ et installez **Python 3.10+**.
2. Sous Windows, cochez « Add Python to PATH » pendant l'installation.
3. Vérifiez dans un terminal :
   ```bash
   python --version
   ```

## 2. Ouvrir le projet

Ouvrez un terminal **dans le dossier `collection_generator/`** :
```bash
cd collection_generator
```

## 3. Installer les dépendances

```bash
pip install -r requirements.txt
```
(La seule dépendance obligatoire est **PyYAML**. Tout le reste utilise la
bibliothèque standard de Python.)

## 4. Lancer le mode simulation (gratuit)

```bash
python -m src.main generate --count 100
```
Cela crée, dans `output/` :
- `metadata/` — un fichier JSON par lionceau ;
- `prompts/` — le prompt (positif + négatif) de chaque lionceau ;
- `reports/` — registres, statistiques de rareté, rapports de validation ;
- `collection.csv` — le tableau global de la collection.

**Aucune image n'est générée et aucune dépense n'est engagée** en simulation.

## 5. Ajouter une nouvelle couleur d'yeux

Ouvrez `config/eye_colors.yaml` et copiez une ligne :
```yaml
  - { code: AQUA, name_en: "Aqua", name_fr: "Aqua", hex: "#7FFFD4", rarity_weight: 6 }
```
C'est tout : aucun code à modifier.

## 6. Ajouter un nouveau style / métier

Ouvrez `config/styles.yaml` et ajoutez un bloc (respectez **un seul objet**) :
```yaml
  - code: TEACHER_SPORT
    name_en: "Sports Coach"
    name_fr: "Professeur de sport"
    outfit: "tracksuit with whistle lanyard"
    headwear: "Sports cap"
    held_object: "Single whistle"
    palette: ["#2C3E50", "#E74C3C", "#FFFFFF"]
    forbidden: ["second object"]
    rarity: "Common"
```

## 7. Choisir le nombre d'images

```bash
python -m src.main generate --count 500
```
Vous pouvez aussi filtrer :
```bash
python -m src.main generate --count 50 --fur GOLD ICE --styles SAMURAI NINJA
```

## 8. Consulter les prompts générés

Les prompts sont dans `output/prompts/`. Chaque fichier contient la partie
**POSITIVE** (envoyée au générateur d'images) et la partie **NEGATIVE**.

## 9. Activer plus tard une API d'images (génération réelle, payante)

1. Copiez `.env.example` en `.env` et renseignez votre clé :
   ```
   OPENAI_API_KEY=sk-...
   ```
2. Lancez avec `--real` (autorisation explicite) :
   ```bash
   python -m src.main generate --count 10 --provider openai --real
   ```
   Les images PNG apparaissent dans `output/images/`.

> ℹ️ L'API d'OpenAI génère au format carré jusqu'à 1024×1024. Pour atteindre
> 2048×2048, on pourra brancher un autre fournisseur (Stable Diffusion, Flux,
> ComfyUI, modèle local) : l'interface `src/image_provider.py` est prévue pour.

## 10. Lancer les tests

```bash
python -m unittest discover -s tests -v
```

## 11. Récupérer les images et métadonnées finales

Tout est dans le dossier `output/` :
- images : `output/images/`
- métadonnées : `output/metadata/`
- tableau global : `output/collection.csv`
- rareté & validation : `output/reports/`

---

## Comment la cohérence est garantie

- Un **prompt maître verrouillé** (`prompts/base_prompt.txt`) contient toutes
  les règles fixes (morphologie, cadrage, fond, caméra, format). Seuls les
  emplacements `[VARIABLE]` (pelage, yeux, style, objet…) sont remplis.
- Un **prompt négatif officiel** (`prompts/negative_prompt.txt`) interdit
  notamment : mains humaines, queue, lion adulte, plusieurs objets, marques,
  textes, fonds colorés, vues de profil, etc.
- Le **contrôle qualité** (`src/quality_control.py`) vérifie chaque image
  réelle (format carré, résolution, fond blanc, personnage centré et entier)
  et chaque combinaison (un seul objet, cohérence style/objet).

## Structure du projet

```
collection_generator/
├── config/        # couleurs, styles, rareté, interdits (YAML, modifiables)
├── prompts/       # prompt maître + prompt négatif (+ templates optionnels)
├── src/           # code (modulaire)
├── output/        # résultats générés
└── tests/         # tests automatisés
```

## Interface web (option future)

Une petite interface Streamlit pourra être ajoutée (`pip install streamlit`).
Elle n'est pas requise : la ligne de commande couvre déjà tout le pipeline.
