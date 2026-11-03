#!/usr/bin/env bash
# Aminos on Ubuntu 22.04 / 24.04 without Docker: Python venv + systemd + Caddy (HTTPS). Run as root.
#
#   curl -fsSL -o install.sh https://raw.githubusercontent.com/aminecopilote/Aminos/main/deploy/ubuntu/install.sh
#   less install.sh        # read it first
#   sudo bash install.sh --domain aminos.example.com [--pdf] [--ref main]
#
# Services (all bound to 127.0.0.1, Caddy is the only public entry):
#   aminos.service      translation app + superagent      http://127.0.0.1:8501
#   aminos-erp.service  back-office (/erp/)               http://127.0.0.1:8502
# Options: --domain D   public name (automatic Let's Encrypt; the DNS A record must point here). Without it: self-signed HTTPS.
#          --pdf        also install LibreOffice Writer, so certified translations include the translated pages as PDF
#          --ref R      branch, tag or commit to install (default main)
#          --source P   install from a local checkout instead of GitHub (used by the CI)
#          --n8n        also install n8n (automation: monitoring, nightly backup, daily digest, web form intake) on
#                       127.0.0.1:5678 with ready-made workflows; the editor is reached through an SSH tunnel,
#                       only /webhook/* is published by Caddy. Needs Node 24 (installed from NodeSource).
#          --alert-url U   webhook that receives the alerts (Slack, Mattermost, Discord, ntfy...); editable later in n8n
#          --n8n-reimport  load the workflows again (overwrites your edits to them)
#          --no-caddy / --no-ufw   skip the reverse proxy / the firewall rules
#          --update     reinstall the code and restart, keeping accounts, data and secrets
#          --uninstall  remove services and code, keep /var/lib/aminos (add --purge to delete the data too)
set -euo pipefail

DOMAIN=""; PDF=0; REF="main"; SOURCE=""; CADDY=1; UFW=1; MODE="install"; PURGE=0; N8N=0; ALERT=""; REIMPORT=0
N8N_VERSION="2.46.4"
REPO="https://github.com/aminecopilote/Aminos"
APP=/opt/aminos; DATA=/var/lib/aminos; ENVF=/etc/aminos/aminos.env
while [ $# -gt 0 ]; do case "$1" in
  --domain) DOMAIN="$2"; shift 2;; --pdf) PDF=1; shift;; --ref) REF="$2"; shift 2;; --source) SOURCE="$2"; shift 2;;
  --no-caddy) CADDY=0; shift;; --no-ufw) UFW=0; shift;; --update) MODE="update"; shift;;
  --uninstall) MODE="uninstall"; shift;; --purge) PURGE=1; shift;;
  --n8n) N8N=1; shift;; --alert-url) ALERT="$2"; shift 2;; --n8n-reimport) REIMPORT=1; shift;;
  *) echo "unknown option: $1" >&2; exit 2;; esac; done

[ -z "$DOMAIN" ] && [ -f /etc/aminos/domain ] && DOMAIN="$(cat /etc/aminos/domain)"   # --update keeps the public name
[ "$N8N" -eq 0 ] && [ -f /etc/aminos/n8n ] && N8N=1                                  # ... and the n8n option
[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo)" >&2; exit 1; }
. /etc/os-release
case "${ID}:${VERSION_ID}" in ubuntu:22.04|ubuntu:24.04) ;; *) echo "tested on Ubuntu 22.04/24.04 only (found ${PRETTY_NAME})" >&2; exit 1;; esac
export DEBIAN_FRONTEND=noninteractive

if [ "$MODE" = "uninstall" ]; then
  systemctl disable --now aminos.service aminos-erp.service aminos-n8n.service 2>/dev/null || true
  rm -f /etc/systemd/system/aminos.service /etc/systemd/system/aminos-erp.service /etc/systemd/system/aminos-n8n.service; systemctl daemon-reload
  rm -rf "$APP"
  if [ "$PURGE" -eq 1 ]; then rm -rf "$DATA" /etc/aminos; echo "removed, data deleted"; else echo "removed; data kept in $DATA and secrets in /etc/aminos"; fi
  exit 0
fi

if [ "$MODE" = "install" ]; then
  echo "==> Packages"
  apt-get update -qq
  PKGS="ca-certificates curl git openssl python3 python3-venv python3-pip fonts-dejavu-core tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra tesseract-ocr-eng tesseract-ocr-nld"
  [ "$UFW" -eq 1 ] && PKGS="$PKGS ufw"
  [ "$PDF" -eq 1 ] && PKGS="$PKGS libreoffice-writer --no-install-recommends"
  # shellcheck disable=SC2086
  apt-get install -y -qq $PKGS >/dev/null
  if [ "$CADDY" -eq 1 ] && ! command -v caddy >/dev/null; then
    echo "==> Caddy (official apt repository)"
    apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https gnupg >/dev/null
    curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt > /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq && apt-get install -y -qq caddy >/dev/null
  fi
fi

echo "==> Code"
id aminos >/dev/null 2>&1 || useradd --system --home-dir "$APP" --shell /usr/sbin/nologin aminos
mkdir -p "$APP" "$DATA" /etc/aminos
if [ -n "$SOURCE" ]; then
  rm -rf "$APP/src"; mkdir -p "$APP/src"; cp -a "$SOURCE"/. "$APP/src/"; rm -rf "$APP/src/.git" "$APP/src/lab/vendor"
else
  rm -rf "$APP/src"; git clone -q "$REPO.git" "$APP/src"; git -C "$APP/src" checkout -q "$REF"
fi
[ -x "$APP/venv/bin/python" ] || python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install -q --upgrade pip
"$APP/venv/bin/pip" install -q "$APP/src[all,docx,swarm]"
chown -R aminos:aminos "$APP" "$DATA"

if [ ! -f "$ENVF" ]; then
  echo "==> Administrator account"
  PASSWORD="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-20)"
  umask 077
  { echo "AMINOS_DATA_DIR=$DATA/saas"; echo "AMINOS_ADMIN_USER=admin"; echo "AMINOS_ADMIN_PASSWORD=$PASSWORD"
    echo "AMINOS_ALLOW_REMOTE_LLM=0"; echo "ANTHROPIC_API_KEY="; echo "AMINOS_PROFILE_DIR=$DATA/profile"; echo "AMINOS_WORK_DIR=$DATA/work"; } > "$ENVF"
  echo "$PASSWORD" > /etc/aminos/FIRST_PASSWORD.txt
  FIRST=1
else
  echo "==> Keeping the existing $ENVF (credentials unchanged)"; FIRST=0
fi
chown root:aminos "$ENVF"; chmod 640 "$ENVF"
umask 022   # the password block above set 077: unit files and the Caddyfile must stay readable by their services
[ -n "$DOMAIN" ] && echo "$DOMAIN" > /etc/aminos/domain

if [ "$N8N" -eq 1 ]; then
  echo "==> n8n $N8N_VERSION"
  echo 1 > /etc/aminos/n8n
  if ! node -v 2>/dev/null | grep -q '^v24'; then
    apt-get install -y -qq ca-certificates curl gnupg >/dev/null
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor --yes -o /usr/share/keyrings/nodesource.gpg
    echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_24.x nodistro main" > /etc/apt/sources.list.d/nodesource.list
    apt-get update -qq && apt-get install -y -qq nodejs >/dev/null
  fi
  # an older Node earlier in PATH (/usr/local/bin on some images) must not run n8n or compile its native modules
  NODE_BIN="$(command -v node)"; "$NODE_BIN" -v | grep -q '^v24' || NODE_BIN=/usr/bin/node
  "$NODE_BIN" -v | grep -q '^v24' || { echo "Node 24 not found ($("$NODE_BIN" -v 2>&1))" >&2; exit 1; }
  echo "$NODE_BIN" > /etc/aminos/node
  mkdir -p "$APP/n8n" "$DATA/n8n"
  PATH="$(dirname "$NODE_BIN"):$PATH" npm install --prefix "$APP/n8n" "n8n@$N8N_VERSION" --force --no-audit --no-fund --loglevel=error
  chown -R aminos:aminos "$APP/n8n" "$DATA/n8n"
  PUBLIC="${DOMAIN:-localhost}"
  cat > /etc/aminos/n8n.env <<N8NENV
N8N_USER_FOLDER=$DATA/n8n
N8N_LISTEN_ADDRESS=127.0.0.1
N8N_PORT=5678
N8N_SECURE_COOKIE=false
N8N_PROXY_HOPS=1
WEBHOOK_URL=https://$PUBLIC/
GENERIC_TIMEZONE=Africa/Casablanca
N8N_DIAGNOSTICS_ENABLED=false
N8N_VERSION_NOTIFICATIONS_ENABLED=false
N8N_PERSONALIZATION_ENABLED=false
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=336
NODES_EXCLUDE='["n8n-nodes-base.executeCommand","n8n-nodes-base.localFileTrigger","n8n-nodes-base.readWriteFile"]'
N8NENV
  chmod 644 /etc/aminos/n8n.env
  if [ ! -f "$DATA/n8n/.aminos-imported" ] || [ "$REIMPORT" -eq 1 ]; then
    echo "==> n8n: tokens, credentials and workflows"
    systemctl stop aminos-n8n.service 2>/dev/null || true
    ARGS=(--out "$DATA/n8n-setup" --data "$DATA/saas" --org admin --erp-url http://127.0.0.1:8502 --app-url http://127.0.0.1:8501)
    [ -n "$ALERT" ] && ARGS+=(--alert-url "$ALERT")
    runuser -u aminos -- "$APP/venv/bin/aminos" n8n prepare "${ARGS[@]}"
    N8NRUN=(runuser -u aminos -- env N8N_USER_FOLDER="$DATA/n8n" N8N_DIAGNOSTICS_ENABLED=false HOME="$DATA" "$NODE_BIN" "$APP/n8n/node_modules/n8n/bin/n8n")
    "${N8NRUN[@]}" import:credentials --input="$DATA/n8n-setup/credentials.json"
    "${N8NRUN[@]}" import:workflow --separate --input="$DATA/n8n-setup/workflows"
    for id in $("${N8NRUN[@]}" list:workflow --onlyId | grep -E '^[A-Za-z0-9]{8,}$'); do "${N8NRUN[@]}" publish:workflow --id="$id" >/dev/null; done
    touch "$DATA/n8n/.aminos-imported"; chown aminos:aminos "$DATA/n8n/.aminos-imported"
  fi
fi

unit() { # name description exec
cat > "/etc/systemd/system/$1.service" <<UNIT
[Unit]
Description=$2
After=network-online.target
Wants=network-online.target

[Service]
User=aminos
Group=aminos
EnvironmentFile=$ENVF
WorkingDirectory=$DATA
Environment=HOME=$DATA
ExecStart=$3
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$DATA
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictSUIDSGID=true

[Install]
WantedBy=multi-user.target
UNIT
}
unit aminos "Aminos translation app" "$APP/venv/bin/streamlit run $APP/src/saas_app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false --server.maxUploadSize=50"
unit aminos-erp "Aminos back-office" "$APP/venv/bin/python -m aminos.erp --host 127.0.0.1 --port 8502"
if [ "$N8N" -eq 1 ]; then
  unit aminos-n8n "Aminos automation (n8n)" "$(cat /etc/aminos/node) $APP/n8n/node_modules/n8n/bin/n8n start"
  sed -i "s#^EnvironmentFile=.*#EnvironmentFile=/etc/aminos/n8n.env#" /etc/systemd/system/aminos-n8n.service
  sed -i "/^ReadWritePaths/s#.*#ReadWritePaths=$DATA#" /etc/systemd/system/aminos-n8n.service
fi
systemctl daemon-reload
systemctl enable aminos.service aminos-erp.service >/dev/null 2>&1
systemctl restart aminos.service aminos-erp.service
if [ "$N8N" -eq 1 ]; then systemctl enable aminos-n8n.service >/dev/null 2>&1; systemctl restart aminos-n8n.service; fi

if [ "$CADDY" -eq 1 ]; then
  echo "==> Caddy"
  SITE="${DOMAIN:-:443}"; TLS=""; [ -z "$DOMAIN" ] && TLS=$'\n\ttls internal'
  WEBHOOK=""; [ "$N8N" -eq 1 ] && WEBHOOK=$'\thandle /webhook/* {\n\t\treverse_proxy 127.0.0.1:5678\n\t}\n'
  cat > /etc/caddy/Caddyfile <<CADDY
$SITE {$TLS
	encode gzip
	header {
		Strict-Transport-Security "max-age=31536000"
		X-Content-Type-Options nosniff
		Referrer-Policy no-referrer
	}
	handle /erp/* {
		reverse_proxy 127.0.0.1:8502
	}
$WEBHOOK	handle {
		reverse_proxy 127.0.0.1:8501
	}
}
CADDY
  systemctl enable caddy >/dev/null 2>&1; systemctl reload caddy 2>/dev/null || systemctl restart caddy
fi
if [ "$UFW" -eq 1 ]; then
  ufw allow OpenSSH >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null; ufw --force enable >/dev/null
fi

echo "==> Waiting for the services"
for i in $(seq 60); do curl -fsS http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1 && curl -fsS -o /dev/null http://127.0.0.1:8502/erp/ 2>/dev/null && break; sleep 2; done
curl -fsS http://127.0.0.1:8501/_stcore/health >/dev/null || { journalctl -u aminos -n 40 --no-pager; exit 1; }
curl -fsS -o /dev/null http://127.0.0.1:8502/erp/ || { journalctl -u aminos-erp -n 40 --no-pager; exit 1; }
if [ "$N8N" -eq 1 ]; then
  for i in $(seq 60); do curl -fsS http://127.0.0.1:5678/healthz >/dev/null 2>&1 && break; sleep 2; done
  curl -fsS http://127.0.0.1:5678/healthz >/dev/null || { journalctl -u aminos-n8n -n 40 --no-pager; exit 1; }
fi
echo "==> Self-test (stand-in model, test certificate, specimen stamp)"
runuser -u aminos -- "$APP/venv/bin/aminos" superagent selftest

echo
if [ -n "$DOMAIN" ]; then BASE="https://$DOMAIN"; else BASE="https://$(curl -fsS https://api.ipify.org 2>/dev/null || hostname -I | cut -d' ' -f1)"; fi
echo "Translation app + superagent : $BASE/"
echo "Back-office                  : $BASE/erp/"
echo "User: admin"
if [ "$FIRST" -eq 1 ]; then echo "Pass: $(cat /etc/aminos/FIRST_PASSWORD.txt)   <- save it, then: shred -u /etc/aminos/FIRST_PASSWORD.txt (keep $ENVF)"; fi
[ -z "$DOMAIN" ] && echo "No domain given: self-signed certificate, the browser will warn. Re-run with --domain to get a real one."
[ "$PDF" -eq 0 ] && echo "Without --pdf the certified translation carries the statement page only (no PDF of the translated pages)."
if [ "$N8N" -eq 1 ]; then
  echo "n8n editor (not published): ssh -L 5678:127.0.0.1:5678 user@server  then  http://localhost:5678  (the first visit creates the owner account: do it now)"
  echo "n8n webhook for the web form : POST ${BASE}/webhook/aminos-demande with header X-Aminos-Secret (secret in $DATA/n8n-setup/credentials.json, readable by root and the aminos user only)"
  [ -z "$ALERT" ] && echo "Alerts are silent until you set the alert URL in n8n (node « Config » of each workflow) or re-run with --alert-url URL --n8n-reimport."
fi
echo "Logs: journalctl -u aminos -u aminos-erp -f      Update: sudo bash install.sh --update"
