# 🦁 Générateur de collection NFT — Lionceaux

Ce projet crée une **grande collection d'images NFT de lionceaux** avec une
**cohérence visuelle stricte** : tous les personnages ont la même stature, le
même cadrage, le même fond, la même lumière. Seuls varient le **pelage**, les
**yeux**, le **style/métier**, l'**objet tenu** et la **rareté**.

> **Important** : par défaut, le projet fonctionne en **mode simulation**. Il
> construit les combinaisons, les prompts et les métadonnées **sans générer
> d'image** et **sans aucune dépense**. La génération payante n'est jamais
> lancée automatiquement.

---

## 📑 Sommaire

1. [Installer Python](#1-installer-python)
2. [Ouvrir le projet](#2-ouvrir-le-projet)
3. [Installer les dépendances](#3-installer-les-dépendances)
4. [Lancer le mode simulation](#4-lancer-le-mode-simulation)
5. [Ajouter une couleur d'yeux](#5-ajouter-une-nouvelle-couleur-dyeux)
6. [Ajouter un style](#6-ajouter-un-nouveau-style)
7. [Choisir le nombre d'images](#7-choisir-le-nombre-dimages)
8. [Consulter les prompts générés](#8-consulter-les-prompts-générés)
9. [Activer plus tard une API d'image](#9-activer-plus-tard-une-api-dimage)
10. [Lancer les tests](#10-lancer-les-tests)
11. [Récupérer les images et métadonnées finales](#11-récupérer-les-images-et-métadonnées-finales)

---

## 1. Installer Python

Le projet a besoin de **Python 3.9 ou plus récent**.

- **Windows / macOS** : téléchargez Python depuis https://www.python.org/downloads/
  et lancez l'installateur. Sur Windows, cochez la case
  **« Add Python to PATH »** pendant l'installation.
- **Linux (Ubuntu/Debian)** : `sudo apt install python3 python3-pip`

Pour vérifier l'installation, ouvrez un terminal et tapez :

```bash
python --version
```

Vous devez voir quelque chose comme `Python 3.11.x`. (Sur certains systèmes, la
commande est `python3` au lieu de `python`.)

---

## 2. Ouvrir le projet

Téléchargez ce projet (ou clonez-le avec git), puis ouvrez un terminal **dans le
dossier du projet** (celui qui contient ce fichier `README.md`).

```bash
cd chemin/vers/ndaconstruct
```

---

## 3. Installer les dépendances

Le mode simulation n'a besoin que d'une petite bibliothèque (`PyYAML`).

```bash
pip install -r requirements.txt
```

> Astuce : si `pip` ne fonctionne pas, essayez `pip3` ou
> `python -m pip install -r requirements.txt`.

---

## 4. Lancer le mode simulation

C'est le cœur du projet. Cette commande crée 100 personnages, leurs prompts et
leurs métadonnées, **sans générer d'image** :

```bash
python -m src.main generate --count 100
```

Pour seulement **voir un aperçu** sans rien écrire sur le disque :

```bash
python -m src.main preview --count 5 --show-prompts
```

Pour afficher les informations de la collection :

```bash
python -m src.main info
```

Exemple de sortie de `info` :

```
Collection : Lion
Pelages    : 9
Yeux       : 20
Styles     : 82
Combinaisons uniques max : 15660
Fond actif : white
Résolution : 2048x2048 (1:1)
```

---

## 5. Ajouter une nouvelle couleur d'yeux

Ouvrez **`config/eye_colors.yaml`** et ajoutez un bloc à la liste. Aucun code à
modifier :

```yaml
  - { key: lava_red, name: "Rouge Lave", prompt: "glowing lava red eyes", hex: "#FF3B1F", rarity_weight: 3, energetic: true }
```

- `key` : identifiant unique (lettres minuscules, underscores).
- `name` : nom affiché dans les métadonnées.
- `prompt` : description envoyée au générateur d'image (en anglais).
- `rarity_weight` : plus le nombre est grand, plus la couleur est fréquente.

Relancez une simulation : la nouvelle couleur est automatiquement combinable avec
les 9 pelages.

---

## 6. Ajouter un nouveau style

Ouvrez **`config/styles.yaml`** et copiez un bloc existant. Exemple :

```yaml
  - key: librarian
    name: "Bibliothécaire"
    description: "Gilet et lunettes, allure calme et studieuse."
    outfit_prompt: "wearing a knitted vest over a shirt with round glasses"
    palette: ["#5D4037", "#FFFFFF", "#7F8C8D"]
    headwear: null
    shoes: "generic leather shoes without brand"
    objects:
      - { key: book_stack, name: "Pile de Livres", prompt: "holding a single stack of books in one paw" }
    forbidden: ["weapons"]
    rarity_weight: 6
```

Règles importantes :

- **Un seul objet** est tenu par personnage : listez plusieurs objets possibles
  dans `objects`, le moteur en choisit **un seul** par image.
- Les **chaussures** restent **génériques** (jamais de marque).
- `headwear: null` si le personnage n'a pas de couvre-chef.

Le système est prévu pour accueillir **des centaines de styles** sans toucher au
code.

---

## 7. Choisir le nombre d'images

Avec l'option `--count` :

```bash
python -m src.main generate --count 500
```

Vous pouvez aussi changer la valeur par défaut dans **`config/collection.yaml`**
(`generation.count`).

Pour **restreindre** les traits utilisés :

```bash
# Uniquement les pelages or et blanc, styles roi et pirate
python -m src.main generate --count 20 --fur gold white --styles king pirate
```

> Le moteur refuse de créer plus de combinaisons uniques qu'il n'en existe et
> affiche un message clair indiquant le maximum possible.

---

## 8. Consulter les prompts générés

Après une génération, les prompts sont écrits dans **`output/prompts/`** :

- `output/prompts/0001.txt` … : un fichier lisible par personnage (prompt
  positif, prompt négatif, paramètres techniques) ;
- `output/prompts/all_prompts.json` : tous les prompts au format JSON.

Vous pouvez aussi les afficher dans le terminal :

```bash
python -m src.main preview --count 3 --show-prompts
```

---

## 9. Activer plus tard une API d'image

Le projet ne dépend **d'aucun fournisseur précis**. L'interface générique se
trouve dans `src/image_provider.py`. Le fournisseur **OpenAI (`gpt-image-1`) est
déjà implémenté et fonctionnel** ; `stable_diffusion`, `flux` et `comfyui` sont
prévus (emplacement `TODO` à compléter).

### Utiliser OpenAI (gpt-image-1)

1. Installez les paquets nécessaires :
   ```bash
   pip install openai Pillow
   ```
2. Copiez le fichier d'exemple d'environnement et renseignez votre clé :
   ```bash
   cp .env.example .env
   # puis dans .env : OPENAI_API_KEY=sk-...
   ```
3. Lancez la génération réelle **en le demandant explicitement** :
   ```bash
   python -m src.main generate --count 10 --provider openai --real
   ```

**À savoir sur `gpt-image-1`** (le code s'en occupe automatiquement) :

- Les tailles supportées sont `1024x1024`, `1536x1024`, `1024x1536`. Pour un
  carré, l'image est demandée en `1024x1024` puis **agrandie** à la résolution
  de `config/collection.yaml` (`image.width/height`, ex. 2048) via Pillow.
  Réglez `providers.openai.upscale_to_target: false` pour garder le 1024 natif.
- `gpt-image-1` n'a **pas** de paramètre `negative_prompt` : les interdits sont
  automatiquement repliés dans le texte du prompt (« Strictly avoid: … »).
- `gpt-image-1` n'a **pas** de paramètre `seed` : la seed reste enregistrée dans
  les métadonnées, mais la reproductibilité pixel-parfaite n'est pas garantie
  côté OpenAI.
- Qualité réglable via `providers.openai.quality` (`low`/`medium`/`high`/`auto`).

> **Sécurité dépenses** : tant que vous n'ajoutez pas `--real` **et**
> `--provider openai`, le projet reste en simulation. Le `test_mode` de
> `config/collection.yaml` force aussi la simulation. Sans clé `OPENAI_API_KEY`,
> le fournisseur s'arrête avec un message clair. Aucune génération payante n'a
> lieu sans votre autorisation explicite.

---

## 10. Lancer les tests

```bash
python -m pytest tests/ -q
```

Les tests vérifient : les 9 couleurs de pelage, l'unicité des identifiants,
l'absence de doublons, la règle de l'objet unique, la correspondance style ↔
objet, la stabilité du prompt de base, la génération des JSON, la
reproductibilité par seed, les combinaisons interdites et le calcul des raretés.

---

## 11. Récupérer les images et métadonnées finales

Après une génération, tout se trouve dans le dossier **`output/`** :

| Dossier / fichier                    | Contenu                                                      |
|--------------------------------------|--------------------------------------------------------------|
| `output/images/`                     | les images PNG (uniquement en génération réelle)             |
| `output/metadata/0001.json` …        | une fiche de métadonnées NFT par personnage                  |
| `output/collection.csv`              | tableau global de toute la collection                        |
| `output/prompts/`                    | les prompts (texte + JSON)                                   |
| `output/reports/quality_report.json` | rapport de contrôle qualité (VALIDÉE / À CONTRÔLER / REFUSÉE) |
| `output/reports/stats.json`          | statistiques et pourcentages de rareté par trait             |
| `output/registries/`                 | registres des identifiants, des seeds, des combinaisons      |

Exemple de métadonnées (`output/metadata/0001.json`) :

```json
{
  "name": "Lion #0001",
  "description": "Collection de lionceaux uniques - cohérence visuelle stricte.",
  "image": "0001.png",
  "attributes": [
    { "trait_type": "Pelage", "value": "Bleu Ice" },
    { "trait_type": "Yeux", "value": "Vert Émeraude" },
    { "trait_type": "Style", "value": "Samouraï" },
    { "trait_type": "Objet", "value": "Katana" },
    { "trait_type": "Rareté", "value": "Rare" }
  ]
}
```

---

## 🖥️ Interface web (facultative)

Une petite interface graphique locale est disponible avec Streamlit :

```bash
pip install streamlit
python -m streamlit run web/app.py
```

Elle permet de choisir le nombre d'images, les pelages, les styles, la
résolution, puis d'explorer les combinaisons, prompts et statistiques — toujours
en mode simulation.

---

## 🗂️ Architecture du projet

```
.
├── README.md
├── requirements.txt
├── .env.example
├── config/                 # toute la configuration (modifiable sans coder)
│   ├── collection.yaml         # paramètres globaux (résolution, fond, seed…)
│   ├── fur_colors.yaml         # les 9 couleurs de pelage
│   ├── eye_colors.yaml         # bibliothèque de couleurs d'yeux
│   ├── styles.yaml             # bibliothèque de styles / métiers
│   ├── rarity.yaml             # paliers et calcul de rareté
│   └── forbidden_combinations.yaml  # combinaisons interdites
├── prompts/
│   ├── base_prompt.txt         # prompt de base VERROUILLÉ (cohérence)
│   ├── negative_prompt.txt     # interdits (queue, mains humaines, marques…)
│   └── templates/
├── src/                    # le code
│   ├── main.py                 # ligne de commande + pipeline complet
│   ├── combination_generator.py
│   ├── prompt_builder.py
│   ├── image_provider.py       # interface générique des fournisseurs d'images
│   ├── metadata_generator.py
│   ├── rarity_engine.py
│   ├── duplicate_checker.py
│   ├── quality_control.py
│   └── utils.py
├── web/
│   └── app.py                  # interface Streamlit facultative
├── output/                 # tout ce qui est généré
└── tests/                  # tests automatisés
```

---

## 🔒 Les règles verrouillées

Ces règles garantissent la **cohérence absolue** du personnage :

- **Personnage** : lionceau debout, **entier de la tête aux pieds**, centré,
  face caméra, marge identique tout autour.
- **Jamais** de mains humaines (toujours des **pattes de lionceau**).
- **Jamais** de queue visible.
- **Un seul objet maximum**, toujours cohérent avec le style ; la seconde patte
  reste vide.
- **Aucune marque**, aucun logo, aucun texte, aucun filigrane.
- **Format strict 1:1**, fond blanc immaculé identique, lumière de studio douce.
- **Aucun doublon** : deux personnages ne peuvent pas avoir la même combinaison.

Ces règles vivent dans `prompts/base_prompt.txt` et `prompts/negative_prompt.txt`
et sont vérifiées par `src/quality_control.py`.
