# Aminos

Atelier de traduction juridique (AR / FR / EN) : moteur de terminologie, contrôles structurels déterministes et traduction multi-passes. Conçu à partir des approches de [zaibunnisa33/legal-translator](https://github.com/zaibunnisa33/legal-translator) (traduction → rétro-traduction → comparaison → correction, sortie Word RTL) et de [lowtidebuild/legal-translation-agent](https://github.com/lowtidebuild/legal-translation-agent) (modes fast/normal/hard, glossaire persistant, vérification structurelle).

## Fonctions

- **Import de glossaires** (`glossary-import`) : fichier ou dossier entier (récursif) en `.csv`, `.tsv`, `.txt`, `.json`, `.xlsx`, `.docx` (tableaux). Détection de l'en-tête et de l'encodage (UTF-8, UTF-16, cp1256), colonnes optionnelles domaine/note, détection des **conflits** entre sources (la première définition l'emporte).
- **Détection des termes** dans le texte source, robuste à l'arabe : diacritiques, tatwil, variantes d'alif, chiffres arabo-indiens, proclitiques (`بالمحكمة` = `المحكمة`), plus longue expression d'abord.
- **Terminologie imposée** injectée dans le prompt, puis **vérifiée** dans la traduction (variantes `a / b` acceptées, accents ignorés).
- **Contrôles déterministes** : nombres, dates et numéros d'articles manquants ou ajoutés, nombre de segments.
- **Modes** : `fast` (brouillon), `normal` (contrôles puis correction si problème), `hard` (rétro-traduction + comparaison + correction).
- **Sortie .docx** : `**gras**` converti en vrai gras, RTL pour l'arabe, Calibri 10, interligne 1,0, marges 1,27 cm.
- **Extraction PDF / scans / images** : texte natif des PDF (pdfplumber), OCR automatique des pages sans couche texte et des images `.png/.jpg/.webp`, via `--ocr claude` (vision, transcrit aussi cachets et sceaux) ou `--ocr tesseract` (hors ligne, `ara+fra+eng`). Les glossaires `.pdf` à tableaux sont aussi importables.
- **Mémoire de traduction** (SQLite, `--tm tm.sqlite`) : les paragraphes déjà traduits (≥ 98 % de similitude) sont réutilisés sans appel au modèle ; les traductions sans anomalie sont enregistrées. `aminos tm import|export|lookup` pour échanger en TSV et interroger les correspondances approchées.
- **Interface web** (`streamlit run app.py`) : envoi du document et des glossaires, choix des langues/mode/OCR, vue source/traduction côte à côte, alertes de contrôle, téléchargement du .docx.
- **LLM gratuits** (`providers.py`, d'après [mnfst/awesome-free-llm-apis](https://github.com/mnfst/awesome-free-llm-apis)) : `--provider ollama,mistral,groq` essaie les fournisseurs dans l'ordre et passe au suivant en cas de limite (429) ou de panne ; `aminos providers` les liste avec l'état de la clé. Disponibles : ollama (local), groq, mistral, gemini, openrouter, nvidia, huggingface, ovh (sans clé, UE). **Confidentialité** : seul `ollama` garde le document sur votre machine ; les autres sont refusés sauf `--allow-free-tier` (certains paliers gratuits peuvent servir à l'entraînement). Ne les utilisez pas pour des pièces confidentielles. Les modèles par défaut et les limites changent vite : vérifiez la liste et utilisez `--model`.
- Règles de style du traducteur (noms en gras, **NOM** en majuscules, cachets, logos, aucun commentaire) dans `aminos/prompts.py`.

## Utilisation

```bash
pip install -e ".[all]"
export ANTHROPIC_API_KEY=...        # ou GROQ_API_KEY, MISTRAL_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY...

# 1. Importer vos glossaires (dossier « مسارد، قواميس ومعاجم » copié dans le dépôt ou en local)
aminos glossary-import "C:\Users\verta\Downloads\مسارد، قواميس ومعاجم" -o glossary.json --src-col 0 --tgt-col 1

# 2. Voir quels termes s'appliquent à un texte
aminos glossary-find glossary.json source.txt

# 3. Traduire
aminos translate acte.docx -s arabe -t français -g glossary.json -m normal --jurisdiction "droit français" -o acte_fr.docx

# 3b. Scan ou PDF image, avec mémoire de traduction
aminos translate scan.pdf -s arabe -t français --ocr claude --tm tm.sqlite -g glossary.json -o scan_fr.docx

# 4. Contrôler une traduction existante
aminos check source.txt traduction.txt -g glossary.json
```

Tests : `python -m unittest discover -s tests`.

## Limites

Le dossier Windows n'est pas lisible depuis la session cloud : les glossaires doivent être importés en local ou copiés dans le dépôt. Les `.doc` (non `.docx`) ne sont pas lus. Testés ici avec un faux modèle : extraction d'un PDF texte et d'un PDF scanné (OCR simulé), CLI de bout en bout, mémoire de traduction, affichage de l'interface web. Non testés : OCR Claude/Tesseract réels, appels au modèle réels, envoi de fichier dans l'interface web. La mise en page est reproduite au niveau du paragraphe.

## Compétence OpenClaw : catalogue d'agents IA

`skills/ai-agents-catalog/` contient une compétence OpenClaw (SKILL.md + catalogue hors ligne de 132 projets tirés de [500-AI-Agents-Projects](https://github.com/ashishpatel26/500-AI-Agents-Projects), licence MIT). Installation : `skills/ai-agents-catalog/install.sh [dossier_workspace]` (défaut `~/.openclaw/workspace`) ou `openclaw skills install skills/ai-agents-catalog`, puis ouvrir une nouvelle session. Les projets listés sont du code tiers : à lire et exécuter en bac à sable.

## Jeu : أسئلة وتحديات / Questions et défis

`jeu/` contient un jeu de soirée dans le navigateur, en arabe (de droite à gauche) avec le français en sous-titre ; le bouton en haut inverse les deux langues. Aucune installation : HTML, CSS et JavaScript sans dépendance (la police Cairo est chargée depuis Google Fonts si Internet est disponible).

**Lancer** : ouvrir `jeu/index.html` dans un navigateur, ou servir le dossier :

```bash
python3 -m http.server 8000 -d jeu    # puis http://localhost:8000
```

**Comment jouer**

1. Ajouter de 1 à 8 joueurs, choisir le mode (questions et défis, questions seulement, défis seulement), les catégories et le nombre de manches (3, 5, 8 ou 10).
2. À son tour, chaque joueur choisit **سؤال / Question** ou **تحدي / Défi**.
3. **Question** : quatre réponses, 20 secondes si le minuteur est activé. Bonne réponse : 1, 2 ou 3 points selon le niveau (★). Trois bonnes réponses d'affilée : +1 point de bonus (🔥).
4. **Défi** : le joueur relève le défi (avec un minuteur pour certains), puis les autres décident s'il est réussi ; réussi = 1 à 3 points selon le défi.
5. **Joker** (🃏, 2 par joueur) : change la carte sans perdre son tour.
6. Après la dernière manche, le classement s'affiche (ex æquo au même rang). La partie en cours est gardée dans le navigateur et peut être reprise après un rechargement.

**Contenu** : 61 questions en 7 catégories (culture générale, géographie, histoire, sciences, sport, Maroc, énigmes) et 24 défis, dans `jeu/data.js`. Pour en ajouter, suivre le même format ; les tests vérifient que chaque entrée est bilingue et que la bonne réponse existe.

Tests : `node --test jeu/tests/game.test.js` (Node 18 ou plus).
