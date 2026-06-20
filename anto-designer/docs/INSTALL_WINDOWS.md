# Créer AntoDesigner.exe et l'installateur Windows

Ce guide explique comment transformer Anto Designer en **application Windows**
avec **icône**, **raccourci Bureau**, **menu Démarrer** et **désinstallation propre**.

> Vous ne ferez ceci qu'une fois (ou à chaque nouvelle version). Après
> installation, vous lancerez Anto Designer **en double-cliquant sur l'icône**,
> sans jamais ouvrir de terminal.

---

## Étape 1 — Construire l'application (AntoDesigner.exe)

1. Installez **Python 3.10+** (cochez « Add Python to PATH »).
2. Dans le dossier `anto-designer`, **double-cliquez** sur :
   ```
   tools\build_windows.bat
   ```
   Ce script installe les dépendances, (re)génère l'icône, puis construit l'app.
3. À la fin, l'application est dans :
   ```
   dist\AntoDesigner\AntoDesigner.exe
   ```
   Vous pouvez déjà la lancer en double-cliquant dessus. ✅

*(Équivalent manuel : `pip install -r requirements.txt pyinstaller` puis
`pyinstaller AntoDesigner.spec`.)*

---

## Étape 2 — Créer l'installateur (optionnel mais recommandé)

L'installateur crée les raccourcis et permet une désinstallation propre.

1. Installez **Inno Setup 6** (gratuit) : https://jrsoftware.org/isinfo.php
2. Ouvrez le fichier :
   ```
   installer\AntoDesigner.iss
   ```
3. Menu **Build → Compile** (ou touche F9).
4. L'installateur est créé ici :
   ```
   installer\Output\AntoDesigner-Setup.exe
   ```
5. Lancez `AntoDesigner-Setup.exe` : il installe l'app, ajoute l'icône sur le
   Bureau et dans le menu Démarrer, et crée un désinstalleur.

---

## Où sont mes projets ?

Vos collections et votre base de données sont dans :
```
%APPDATA%\AntoDesigner
```
Ils **ne sont pas supprimés** lors de la désinstallation (conservés par défaut).

---

## Problèmes fréquents

- **« Python introuvable »** → réinstallez Python en cochant « Add to PATH ».
- **Windows SmartScreen** bloque l'exe non signé → « Informations
  complémentaires » puis « Exécuter quand même » (l'app est locale et sûre).
- **Antivirus** méfiant avec PyInstaller → ajoutez une exception pour le dossier.
- Pour un démarrage plus rapide / fichier unique, on pourra passer en mode
  « onefile » dans une version ultérieure.
