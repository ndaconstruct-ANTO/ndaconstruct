# Générer ta collection GRATUITEMENT sur ton PC (RTX) — €0, aucune facturation

Tu as une **carte NVIDIA RTX** → tu peux générer **gratuitement** (sans OpenAI,
sans abonnement, sans coût par image). On utilise **Fooocus**, l'outil gratuit
le plus simple (basé sur Stable Diffusion XL), pensé pour les débutants.

> Aucune dépense. Aucune carte bancaire. Tout tourne sur ta machine.

---

## 1. Installer Fooocus (gratuit, ~10 min)
1. Va sur la page officielle : **https://github.com/lllyasviel/Fooocus**
2. Section **« Download »** → télécharge le pack Windows
   (`Fooocus_win64_*.7z`).
3. Décompresse-le (avec **7-Zip** : https://www.7-zip.org).
4. Double-clique **`run.bat`**.
   - Au 1er lancement, il télécharge le modèle automatiquement (quelques Go).
   - Une page web s'ouvre toute seule (l'interface de Fooocus).

## 2. Régler la qualité / le format (une fois)
Dans Fooocus :
- Coche **« Advanced »** (en bas).
- Onglet **« Settings »** :
  - **Performance** : *Quality* (ou *Speed* pour tester vite).
  - **Aspect Ratio** : choisis **1024×1024** (carré) — ta RTX peut aussi faire
    **1152×1152 / 1280×1280** selon la VRAM.
- Onglet **« Advanced »** → tu pourras coller le **prompt négatif**.

## 3. Créer le MODÈLE MAÎTRE (étape clé)
1. Ouvre le fichier **`prompts/MASTER_PROMPT.txt`**.
2. Colle le **PROMPT POSITIF** dans la barre de Fooocus, le **NÉGATIF** dans
   « Negative Prompt ».
3. Génère **3-4 fois**, garde celui avec les **bras courts** et les meilleures
   proportions. **C'est ton maître.** Sauvegarde-le (ex. `master_lion.png`).

## 4. Garder le MÊME lionceau sur toute la série (cohérence)
Dans Fooocus :
- Coche **« Input Image »** → onglet **« Image Prompt »**.
- Charge ton **master_lion.png**.
- Règle **Stop At ≈ 0.5** et **Weight ≈ 0.6–0.8** (plus haut = plus fidèle).
- *(Option : active aussi « PyraCanny » avec le master pour garder la posture.)*

Ainsi, chaque génération **repart du même lionceau**, tu changes juste pelage,
yeux, tenue et objet via le prompt.

## 5. Générer les 101 personnages
1. Ouvre le dossier **`prompts_collection/`** (fourni) : il contient
   **un fichier .txt par lionceau** (POSITIF + NÉGATIF déjà prêts, avec toutes
   les règles : tenue complète, contraste pelage/yeux, objet patte droite…).
2. Pour chacun : copie le **POSITIF** dans Fooocus, le **NÉGATIF** dans Negative
   Prompt, garde ton master en Image Prompt, clique **Generate**.
3. Récupère les images dans le dossier `Fooocus/outputs/`.

> Astuce : commence par **1 seul** personnage, valide le rendu (tenue complète,
> bras courts, contraste), puis enchaîne.

## 6. Détourer + fonds + 4K (gratuit aussi)
- **Détourage** (fond transparent) : Fooocus peut générer sur fond uni blanc,
  puis tu enlèves le blanc ; ou utilise un outil gratuit comme **rembg**.
- **Fonds** : réutilise tes fonds déjà créés (dossier `fonds_officiels/`).
- **4K net** : passe les images dans **Real-ESRGAN** (voir `docs/UPSCALE_4K.md`).

---

## Pourquoi c'est mieux pour toi
- **0 € par image** (vs ~0,15 $ chez OpenAI).
- Tu génères **autant que tu veux**, tu refais à volonté **sans payer**.
- Tu gardes le **contrôle total** sur ta machine.

## Ce que j'ai préparé pour toi (gratuit)
- `prompts/MASTER_PROMPT.txt` — pour créer le maître corrigé.
- `prompts_collection/` — les 101 prompts prêts (tenue complète + contrastes).
- `docs/REGLES_COLLECTION.md` — toutes tes règles.
- `docs/UPSCALE_4K.md` — le 4K gratuit.

> ⚠️ Je n'ai engagé **aucune dépense** : tout ceci est du texte/guide.
> La génération se fait **chez toi, gratuitement**.
