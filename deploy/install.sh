#!/usr/bin/env bash
# Run ON the VPS as a normal user in the docker group (or with sudo): bash deploy/install.sh
set -euo pipefail
cd "$(dirname "$0")/.."

command -v docker >/dev/null || { echo "Docker est requis : https://docs.docker.com/engine/install/"; exit 1; }
docker compose version >/dev/null || { echo "Le plugin docker compose est requis"; exit 1; }

if [ ! -f .env ]; then
  umask 077
  cat > .env <<'ENVEOF'
# Une seule clé suffit. Ne jamais versionner ce fichier.
ANTHROPIC_API_KEY=
#GROQ_API_KEY=
#MISTRAL_API_KEY=
ENVEOF
  echo ">> .env créé (droits 600) : renseignez au moins une clé, puis relancez ce script."
  exit 0
fi

docker compose build
docker compose up -d
sleep 5
docker compose ps
curl -fsS http://127.0.0.1:8501/_stcore/health && echo && echo "OK : Aminos écoute sur 127.0.0.1:8501 (tunnel SSH requis)"
