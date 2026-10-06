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
- Règles de style du traducteur (noms en gras, **NOM** en majuscules, cachets, logos, aucun commentaire) dans `aminos/prompts.py`.

## Utilisation

```bash
pip install -e ".[all]"
export ANTHROPIC_API_KEY=...

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
