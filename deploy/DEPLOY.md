# Installer Aminos sur un VPS

Pile : Aminos (interface web Streamlit, OCR Tesseract ar/fr/en/nl) derrière **Caddy** (HTTPS automatique + mot de passe),
volume persistant pour la mémoire de traduction, **Ollama** optionnel pour traduire sans rien envoyer à un tiers.

## Prérequis
- Ubuntu 22.04 ou 24.04 neuf, accès root, ports 80/443 ouverts chez l'hébergeur.
- Sans modèle local : 2 vCPU / 4 Go de RAM suffisent. **Avec modèle local** (`--local-llm`) : prévoir 8 Go minimum pour
  `qwen3:8b`, 16 Go et plus pour un modèle de 14 milliards de paramètres, sans GPU les réponses sont lentes.
- Un nom de domaine dont l'enregistrement A pointe vers le serveur (sinon certificat auto-signé : avertissement du navigateur).

## Installation (une commande, lisez le script avant)
```bash
curl -fsSL -o install.sh https://raw.githubusercontent.com/aminecopilote/Aminos/main/deploy/install.sh
less install.sh
sudo bash install.sh --domain aminos.exemple.com                       # fournisseurs distants ou clé d'API
sudo bash install.sh --domain aminos.exemple.com --local-llm --model qwen3:8b   # tout reste sur le serveur
```
Le script installe Docker (dépôt officiel), active le pare-feu (SSH, 80, 443), clone le dépôt dans `/opt/aminos`,
crée l'utilisateur `aminos` avec un mot de passe aléatoire **affiché une seule fois**, puis lance la pile.
Tant que la PR n'est pas fusionnée dans `main`, ajoutez `--branch claude/stoic-rubin-iq1po6` et adaptez l'URL du script.

## Exploitation
```bash
cd /opt/aminos/deploy
docker compose ps                       # état
docker compose logs -f aminos           # journaux
git pull && docker compose up -d --build   # mise à jour
./backup.sh /root/sauvegardes           # archive de la mémoire de traduction
docker compose down                     # arrêt (les données restent dans les volumes)
```
Clé d'API facultative : éditez `/opt/aminos/deploy/.env` (`ANTHROPIC_API_KEY=`) puis `docker compose up -d`.

## Confidentialité et sécurité
- L'application n'est jamais publiée directement : seul Caddy écoute sur 80/443, avec mot de passe.
- Documents confidentiels : choisissez le fournisseur **ollama** (local). Les autres fournisseurs envoient le texte à un tiers.
- Les fichiers téléversés sont traités dans un répertoire temporaire ; la mémoire de traduction (`/data/tm.sqlite`) conserve
  les phrases traduites : sauvegardez-la et protégez le serveur comme les pièces elles-mêmes.
- Le banc de notarisation reste un **essai** (autorité de test, pas d'apostille, pas de signature qualifiée) : n'y mettez pas de clé réelle.

## Testé / non testé
Testé (conteneur de développement) : construction Python de l'image, démarrage, santé, non-root, volume inscriptible,
Caddy + authentification (401 / 401 / 200), WebSocket et affichage dans un navigateur. La CI GitHub construit l'image
complète (couche apt/Tesseract). **Non testé** : `install.sh` sur un vrai VPS (Docker, pare-feu, Let's Encrypt),
Ollama et le téléchargement d'un modèle, les appels à un vrai fournisseur LLM.
