# Licences des composants — ANTO DESIGNER

Tous les composants du **cœur** sont gratuits et compatibles avec un **usage
commercial** (vente de vos collections NFT autorisée). Vos fichiers restent
votre propriété ; aucune télémétrie n'est activée.

| Composant | Version | Licence | Usage dans le projet | Usage commercial | Lien |
|---|---|---|---|---|---|
| Python | 3.10+ | PSF License | Langage | ✅ Oui | https://docs.python.org/3/license.html |
| SQLite | (stdlib `sqlite3`) | Domaine public | Base de données locale | ✅ Oui | https://www.sqlite.org/copyright.html |
| PySide6 (Qt for Python) | ≥6.5 | LGPLv3 | Interface graphique | ✅ Oui (en liaison dynamique) | https://www.qt.io/qt-licensing |
| Pillow | ≥10.0 | MIT-CMU (HPND) | Compositing rapide | ✅ Oui | https://python-pillow.org |
| PyInstaller (optionnel) | ≥6.0 | GPL + exception | Création du .exe | ✅ Oui (exception runtime) | https://pyinstaller.org |

## Module IA local (OPTIONNEL — non installé par défaut)

> ⚠️ À vérifier **avant** d'activer le module IA. Les licences des *modèles*
> diffèrent de celles des *logiciels*.

| Composant | Licence logiciel | Remarque images générées |
|---|---|---|
| PyTorch | BSD-3 | ✅ |
| diffusers (Hugging Face) | Apache-2.0 | ✅ |
| Modèles Stable Diffusion | **variable (CreativeML OpenRAIL, etc.)** | ⚠️ Vérifier au cas par cas : vente d'images, redistribution du modèle, attribution. |

**Règle du projet** : aucun composant juridiquement problématique n'est intégré
silencieusement. Le module IA est séparé, optionnel, et documenté.
