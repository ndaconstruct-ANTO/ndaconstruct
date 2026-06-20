# Guide pas-à-pas — ANTO DESIGNER (pour débutant)

Ce guide utilise des phrases courtes. Suivez les étapes dans l'ordre.

## 1. Installer Python
1. Allez sur https://www.python.org/downloads/
2. Installez Python 3.10 ou plus récent.
3. Sous Windows : cochez **« Add Python to PATH »**.

## 2. Ouvrir le dossier du logiciel
1. Ouvrez le dossier `anto-designer`.
2. Ouvrez un terminal dans ce dossier.

## 3. Installer les composants
Tapez :
```
pip install -r requirements.txt
```

## 4. Vérifier votre ordinateur
```
python tools/hardware_audit.py
```
Lisez le verdict. Les **calques** fonctionnent même sur un PC modeste.

## 5. Lancer Anto Designer
```
python -m anto_designer
```
La fenêtre d'accueil s'ouvre.

## 6. Tester la démo
Dans l'application : bouton **« Lancer la démo »**.
Ou en ligne de commande :
```
python -m anto_designer.cli demo --count 8
```
Les résultats sont dans `demo/_workspace/output/`.

## 7. Comprendre les calques
- Un **calque** = une image PNG transparente (ex. une veste).
- Tous les calques ont la **même taille**.
- Ils s'empilent dans un **ordre** (fond → corps → vêtements → objet).
- On change un calque → on change un détail, **sans changer le personnage**.

## 8. Régler les raretés
Chaque calque a un **poids**. Plus le poids est grand, plus il apparaît souvent.

## 9. Générer une collection
Choisissez le **nombre d'images**. Le logiciel :
- évite les **doublons** ;
- respecte les **incompatibilités** ;
- crée les **images** et les **métadonnées JSON** ;
- écrit un **rapport** de validation.

## 10. Exporter / Sauvegarder
- Les images sont dans le dossier `output/images`.
- Les métadonnées sont dans `output/metadata`.
- Vous pouvez **exporter** une collection (dossier portable) pour la déplacer.

## 11. En cas de problème
- Cliquez sur **« Copier le rapport de diagnostic »** dans l'accueil.
- Collez-le pour demander de l'aide (aucune donnée privée inutile).

## Règles importantes (collection lionceaux)
- Toujours **des chaussures**. 
- **Un seul objet**, dans la **patte droite** (côté gauche de l'image).
- **Pas de mains humaines**, pas de queue, fond **blanc**.
- **Aucune marque** ni logo.
