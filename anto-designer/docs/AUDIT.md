# ANTO DESIGNER — Audit de faisabilité (Livrable n°1)

> Méthode suivie : **MESURER → ANALYSER → DÉCIDER → EXÉCUTER → TESTER → VALIDER.**

## ⚠️ Avertissement de transparence (important)

L'assistant qui a produit ce projet s'exécute dans un **conteneur Linux cloud
éphémère**, **pas sur votre ordinateur Windows**. Il est donc **impossible de
lire vos caractéristiques réelles** (votre CPU, GPU, RAM).

➡️ **Action unique à faire de votre côté** : lancez `tools/hardware_audit.py`
sur **votre** PC (voir §11). Il affiche votre matériel et un verdict personnalisé.

Les chiffres ci-dessous décrivent **l'environnement de construction** (pour
référence), pas votre machine.

| Élément | Environnement de build (cloud) |
|---|---|
| OS | Ubuntu 24.04 (Linux) |
| CPU | Intel Xeon ~2.8 GHz, 4 cœurs |
| RAM | 15 Go |
| Disque libre | ~30 Go |
| GPU | **aucun** |
| Python | 3.11 |
| SQLite | inclus (stdlib) ✅ |
| Pillow / PySide6 / GPU AI | absents ici |

---

## 1–4. Comparaison des trois architectures + verdict

| Critère | A — Calques | B — IA locale | C — Hybride |
|---|---|---|---|
| Cohérence du personnage | **Parfaite** (par construction) | Variable (dérive possible) | Très bonne |
| Qualité visuelle | = qualité des calques | Potentiellement élevée | Élevée |
| Besoin GPU | **Aucun** | GPU NVIDIA 6–8 Go+ | GPU pour le module IA seulement |
| Vitesse / image | Très rapide (ms–s) | Lente sans bon GPU | Rapide (calques) |
| Hors-ligne | **Oui** | Oui (après téléchargement modèles) | Oui |
| Coût réel | **0 €** | 0 € (mais GPU requis) | 0 € |
| Milliers d'images | **Oui, facile** | Lourd | Oui |
| Ajout de styles | Ajouter un calque | Réentraîner/prompt | Ajouter un calque (IA pour créer le calque) |
| Risque de variation | **Nul** | Élevé | Faible |
| Maintenance | Simple | Complexe | Moyenne |

**Décision : architecture A (CALQUES) comme cœur, + module IA local OPTIONNEL
(architecture C à terme).**
La priorité absolue étant la **cohérence parfaite du personnage**, les calques
sont la seule approche qui la garantit à 100 %, sur n'importe quel PC, gratuitement.

### ✅ VERDICT : **PROJET RÉALISABLE ENTIÈREMENT EN LOCAL**

- **Totalement possible partout** : génération par calques, base SQLite, raretés,
  anti-doublons, validation, export PNG + métadonnées JSON, sauvegarde/restauration,
  interface graphique.
- **Possible avec limites (dépend du GPU)** : module **IA locale optionnel**
  (Stable Diffusion/Flux/ComfyUI) pour *créer* de nouveaux vêtements/accessoires.
  Sans bon GPU NVIDIA, ce module sera lent ou désactivé — **mais le logiciel
  reste 100 % fonctionnel sans lui**.
- **Aucune dépense obligatoire.** Aucune API payante. Aucun abonnement.

---

## 5–10. Règles métier (lionceaux) intégrées

Modèle maître verrouillé, posture/cadrage/fond fixes, anatomie féline (jamais de
mains humaines), chaussures obligatoires, **un seul objet dans la patte droite**
(côté gauche de l'image), 9 couleurs de pelage, yeux multiples, styles variés,
aucune marque. Ces règles sont portées par : l'ordre des calques, les catégories
(`required`, `max_one`), les règles d'incompatibilité, et le contrôle qualité.

## 7. Technologie retenue (§38)

| Option | Verdict |
|---|---|
| **Python + PySide6** | ✅ **Choisi** : LGPL (gratuit, usage commercial OK), mature, excellent pour images haute résolution + SQLite + traitement par lots ; packaging Windows via PyInstaller → `AntoDesigner.exe`. |
| Electron | ❌ Lourd, JS, gourmand en RAM pour du traitement d'images. |
| Tauri | ⚠️ Léger mais Rust + écosystème image moins direct. |
| .NET | ⚠️ Bon sur Windows mais nous éloigne d'un cœur Python testable et portable. |

## 11. Estimations de performance (calques)

| Résolution | Temps/image (CPU) | 1 000 images |
|---|---|---|
| 1024² | ~0,1–0,5 s (Pillow) | quelques minutes |
| 2048² | ~0,3–1,5 s (Pillow) | ~10–25 min |

Le repli stdlib (sans Pillow) est plus lent : installez **Pillow** pour la vitesse.

## 12. Espace disque estimé

- Logiciel + dépendances : ~300–600 Mo. 
- 1 000 images PNG 2048² : ~1–4 Go selon le contenu.

## 13. Limites de qualité honnêtes

- La qualité des images = **qualité de vos calques**. Anto Designer assemble, il
  n'invente pas (sauf module IA optionnel).
- Le module IA local dépend du GPU ; sans GPU, restez sur les calques.

## 14. Risques techniques

- Calques mal alignés → atténué par le contrôle de dimensions et le gabarit.
- Gros volumes → génération par lots avec arrêt/reprise.
- Pillow absent → repli stdlib (lent mais fonctionnel).

## 15. Arborescence du projet

```
anto-designer/
├── anto_designer/        # cœur (moteur, base, génération, GUI)
│   ├── gui/              # interface PySide6
│   ├── pnglib.py         # PNG stdlib (compositing sans Pillow)
│   ├── layer_engine.py   # superposition de calques (Pillow|stdlib)
│   ├── database.py       # SQLite + migrations versionnées
│   ├── store.py          # CRUD
│   ├── combination.py    # combinaisons uniques (raretés, règles)
│   ├── rarity.py / dedup.py / validation.py / metadata.py
│   ├── generator.py      # orchestration
│   └── project.py        # export/import portable
├── demo/                 # projet de démonstration (sans vos images)
├── tools/hardware_audit.py
├── tests/                # tests unittest
└── docs/                 # AUDIT.md, GUIDE.md
```

## 16. Schéma initial de la base (SQLite)

`collections` → `categories` → `layers` ; `rules` (incompatible/requires) ;
`generated` + `generated_traits`. Versionné via `PRAGMA user_version`.

## 17. Écrans de l'interface

Accueil ✅ (implémenté), Collection, Bibliothèque de calques, Éditeur de calques,
Génération, Validation (les écrans avancés arrivent par versions ; le moteur est
déjà complet et piloté par la démo).

## 18–20. Étapes & tests

Audit ✅ → arborescence ✅ → base ✅ → moteur calques ✅ → génération ✅ →
contrôles ✅ → tests ✅ (10/10) → doc ✅. Tests : voir `tests/` (CRUD, compositing,
combinaisons, capacité, incompatibilités, anti-doublons, métadonnées, validation,
export/import, pipeline démo complet).

## Conclusion

**PROJET RÉALISABLE ENTIÈREMENT EN LOCAL.** La première version fonctionnelle
existe et est testée (voir `README.md` et la démo). L'IA locale reste un module
**optionnel** dépendant de votre GPU.
