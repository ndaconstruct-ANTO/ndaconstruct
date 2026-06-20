# 🎨 ANTO DESIGNER — NFT Collection Studio

Logiciel **local** pour créer des collections NFT cohérentes par **calques** :
même personnage maître, on change seulement pelage, yeux, tenue, chaussures,
couvre-chef et l'unique objet tenu. **100 % local, hors-ligne, gratuit** pour le
cœur (aucune API payante, aucun abonnement).

> 🟢 Le moteur (calques, génération, raretés, anti-doublons, validation,
> métadonnées) fonctionne **sans Pillow ni GPU** — démontré et testé.

---

## 1. Pré-requis
- **Windows** (ou Linux/macOS), et **Python 3.10+** : https://www.python.org/downloads/
  (sous Windows, cochez « Add Python to PATH »).

## 2. Installation
```bash
cd anto-designer
pip install -r requirements.txt
```

## 3. Auditer VOTRE ordinateur (recommandé)
```bash
python tools/hardware_audit.py
```
→ affiche votre CPU/RAM/GPU/disque et un verdict personnalisé.

## 4. Lancer l'application
```bash
python -m anto_designer
```
(Une fois packagé en `.exe`, il suffira de double-cliquer sur l'icône
**AntoDesigner.exe** — sans terminal.)

## 5. Essayer tout de suite la démo (sans vos images)
```bash
python -m anto_designer.cli demo --count 8
```
→ crée des calques d'exemple, génère 8 NFT (images + métadonnées + rapports)
dans `demo/_workspace/output/`. Idéal pour comprendre le fonctionnement.

## 6. Lancer les tests
```bash
python -m unittest discover -s tests -v
```

---

## Ce que fait déjà cette première version
- ✅ Base de données locale **SQLite** (collections, catégories, calques, règles,
  générations) avec migrations versionnées.
- ✅ **Moteur de calques** : superposition de PNG transparents alignés (Pillow si
  présent, sinon repli stdlib).
- ✅ **Générateur** : combinaisons uniques, **raretés** (poids), **incompatibilités**
  et **dépendances**, **anti-doublons** (signature + hash d'image), reproductible (seed).
- ✅ **Contrôle qualité** : dimensions, image carrée, non vide, catégories obligatoires.
- ✅ **Export** : images PNG + **métadonnées NFT JSON** (compatibles marketplaces),
  nommage configurable, **jamais d'écrasement**.
- ✅ **Export / import** de collection portable (manifeste versionné).
- ✅ **Interface graphique** d'accueil (PySide6) + bouton diagnostic.
- ✅ **Aucune télémétrie**, fichiers 100 % locaux.

## Feuille de route (versions suivantes)
- Éditeur de calques visuel (détourage, masque, déplacement, opacité…).
- Écrans Collection / Bibliothèque / Génération / Validation complets.
- Module **IA local optionnel** (création de vêtements/accessoires) — selon GPU.
- Installateur Windows + icône + `AntoDesigner.exe`.

## 🪟 Créer l'application Windows (icône + double-clic, sans terminal)
1. Double-cliquez `tools\build_windows.bat` → crée `dist\AntoDesigner\AntoDesigner.exe`.
2. (Optionnel) Avec **Inno Setup**, compilez `installer\AntoDesigner.iss` → installateur
   `AntoDesigner-Setup.exe` (raccourci Bureau + menu Démarrer + désinstallation propre).

Guide détaillé : `docs/INSTALL_WINDOWS.md`.

## Documentation
- `docs/AUDIT.md` — audit de faisabilité et verdict.
- `docs/GUIDE.md` — guide pas-à-pas pour débutant.
- `docs/INSTALL_WINDOWS.md` — créer l'exe et l'installateur Windows.
- `LICENSES.md` — licences et usage commercial.
