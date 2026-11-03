#!/usr/bin/env bash
# n8n for the Docker install: API tokens, credentials, the five Aminos workflows, activation.
#   cd deploy && bash n8n-setup.sh [alert-webhook-url]
# Re-running loads the workflows again (it overwrites your edits to them) and keeps the existing tokens.
# The editor is not published: ssh -L 5678:127.0.0.1:5678 user@server, then http://localhost:5678 (create the owner account at once).
set -euo pipefail
cd "$(dirname "$0")"
ALERT="${1:-}"
dc() { docker compose --profile n8n "$@"; }

dc up -d aminos erp
ARGS=(--out /data/n8n-setup --data /data/saas --org admin --erp-url http://erp:8502 --app-url http://aminos:8501)
[ -n "$ALERT" ] && ARGS+=(--alert-url "$ALERT")
dc run --rm --no-deps aminos aminos n8n prepare "${ARGS[@]}"

dc stop n8n >/dev/null 2>&1 || true
# as root inside the n8n image: the credentials file is private to the aminos user; ownership of n8n's data is restored at the end
dc run --rm --no-deps -u root --entrypoint sh n8n -c '
  set -e
  n8n import:credentials --input=/import/n8n-setup/credentials.json
  n8n import:workflow --separate --input=/import/n8n-setup/workflows
  for id in $(cat /import/n8n-setup/workflow-ids.txt); do n8n publish:workflow --id="$id"; done
  n8n list:workflow --active=true
  chown -R node:node /home/node/.n8n'
dc up -d n8n
for i in $(seq 60); do dc exec -T n8n wget -qO- http://127.0.0.1:5678/healthz >/dev/null 2>&1 && break; sleep 2; done
dc exec -T n8n wget -qO- http://127.0.0.1:5678/healthz >/dev/null && echo "n8n is running (editor on 127.0.0.1:5678, webhooks on https://\${DOMAIN}/webhook/aminos-demande)"
[ -z "$ALERT" ] && echo "Alerts stay silent until you set the alert URL (node « Config » of each workflow, or re-run with the URL)."
exit 0
