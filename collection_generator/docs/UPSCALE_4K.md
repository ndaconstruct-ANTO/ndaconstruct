# Passer la collection en VRAI 4K avec Real-ESRGAN (gratuit, local)

Les images sont générées en **1024×1024 qualité haute** (le max natif carré de
l'IA). Pour un **vrai ultra-HD** (4096×4096) sans payer, on agrandit avec
**Real-ESRGAN**, un upscaler IA **gratuit et open source** qui ajoute du détail
(contrairement à un simple agrandissement).

> Aucune programmation. Pas de Python. Un seul exécutable + un dossier.

---

## 1. Télécharger Real-ESRGAN (version « ncnn-vulkan », sans installation)

1. Va sur la page officielle des versions :
   **https://github.com/xinntao/Real-ESRGAN/releases**
2. Télécharge le fichier Windows :
   `realesrgan-ncnn-vulkan-*-windows.zip`
3. **Décompresse-le** (par ex. sur ton Bureau). Tu obtiens un dossier contenant
   `realesrgan-ncnn-vulkan.exe`.

*(Il fonctionne avec ou sans carte graphique. Avec un GPU c'est rapide ; sur
CPU c'est plus lent mais ça marche.)*

---

## 2. Préparer les images

- Mets les PNG à agrandir dans un dossier `entree`.
- Crée un dossier `sortie` (vide).

Conseil : agrandis **les transparents** (dossier `collection_transparente`) →
tu gardes la transparence en 4K, puis tu recolles sur les fonds (eux aussi
agrandis). Ou agrandis directement `collection_avec_fonds`.

---

## 3. Lancer l'agrandissement ×4 (1024 → 4096)

Ouvre une fenêtre de commande **dans le dossier de Real-ESRGAN**, puis :

```
realesrgan-ncnn-vulkan.exe -i entree -o sortie -n realesrgan-x4plus -s 4 -f png
```

- `-i entree`  : dossier source
- `-o sortie`  : dossier résultat (4096×4096)
- `-n realesrgan-x4plus` : modèle (bon pour le rendu 3D réaliste)
- `-s 4`       : facteur 4 (×4)
- `-f png`     : garde le PNG (et la transparence)

Le logiciel traite **tout le dossier** automatiquement. ✅

---

## 4. Astuce « 1 clic » (fichier .bat)

Copie le fichier fourni `tools/upscale_realesrgan.bat` à côté de
`realesrgan-ncnn-vulkan.exe`, mets tes images dans `entree`, puis
**double-clique** le .bat. Le résultat 4K apparaît dans `sortie`.

---

## Licence
Real-ESRGAN est sous licence **BSD-3-Clause** (gratuit, usage commercial OK).
Voir le dépôt officiel pour les modèles et leurs licences.
