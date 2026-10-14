#!/usr/bin/env bash
# Aminos installer for a fresh Ubuntu 22.04 / 24.04 VPS (run as root).
#   curl -fsSL -o install.sh https://raw.githubusercontent.com/aminecopilote/Aminos/main/deploy/install.sh
#   less install.sh   # read it first
#   sudo bash install.sh --domain aminos.example.com [--local-llm [--model qwen3:8b]] [--branch main]
# Without --domain the site is served on https://<server-ip> with a self-signed certificate.
set -euo pipefail

DOMAIN="localhost"; LOCAL_LLM=0; MODEL="qwen3:8b"; BRANCH="main"; DIR="/opt/aminos"
REPO="https://github.com/aminecopilote/Aminos.git"
while [ $# -gt 0 ]; do case "$1" in
  --domain) DOMAIN="$2"; shift 2;; --local-llm) LOCAL_LLM=1; shift;; --model) MODEL="$2"; shift 2;;
  --branch) BRANCH="$2"; shift 2;; --dir) DIR="$2"; shift 2;;
  *) echo "unknown option: $1" >&2; exit 2;; esac; done

[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo)" >&2; exit 1; }
. /etc/os-release
case "${ID}:${VERSION_ID}" in ubuntu:22.04|ubuntu:24.04) ;; *) echo "tested on Ubuntu 22.04/24.04 only (found ${PRETTY_NAME})" >&2; exit 1;; esac

echo "==> Packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq ca-certificates curl git ufw openssl gnupg >/dev/null

if ! command -v docker >/dev/null; then
  echo "==> Docker (official apt repository)"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq && apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null
fi

echo "==> Firewall (SSH, HTTP, HTTPS only)"
ufw allow OpenSSH >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null
# Docker publishes ports around ufw; the compose file therefore publishes only 80 and 443 and keeps the app internal.

echo "==> Aminos source in ${DIR}"
if [ -d "${DIR}/.git" ]; then git -C "${DIR}" fetch -q origin "${BRANCH}" && git -C "${DIR}" checkout -q "${BRANCH}" && git -C "${DIR}" reset -q --hard "origin/${BRANCH}"
else git clone -q --branch "${BRANCH}" "${REPO}" "${DIR}"; fi
cd "${DIR}/deploy"

if [ ! -f .env ]; then
  echo "==> Administrator account"
  PASSWORD="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-20)"
  umask 077
  { echo "DOMAIN=${DOMAIN}"; echo "AMINOS_ADMIN_USER=admin"; echo "AMINOS_ADMIN_PASSWORD=${PASSWORD}"
    echo "AMINOS_ALLOW_REMOTE_LLM=0"; echo "ANTHROPIC_API_KEY="; } > .env
  echo "${PASSWORD}" > "${DIR}/deploy/FIRST_PASSWORD.txt"   # shown once below; delete after saving it
else
  echo "==> Keeping the existing .env (credentials unchanged)"
fi

echo "==> Build and start"
PROFILE=(); [ "${LOCAL_LLM}" -eq 1 ] && PROFILE=(--profile local-llm)
docker compose "${PROFILE[@]}" up -d --build
if [ "${LOCAL_LLM}" -eq 1 ]; then
  echo "==> Local model ${MODEL} (large download; needs enough RAM)"
  docker compose exec ollama ollama pull "${MODEL}"
fi

echo
echo "Aminos is starting. Health: $(docker compose ps --format '{{.Service}}={{.Status}}' | tr '\n' ' ')"
if [ "${DOMAIN}" = "localhost" ]; then echo "URL:   https://$(curl -fsS https://api.ipify.org 2>/dev/null || hostname -I | cut -d' ' -f1)  (self-signed certificate: the browser will warn)"
else echo "URL:   https://${DOMAIN}   (the DNS A record must point to this server)"; fi
echo "User:  admin   (then create the users of each firm in the Administration tab)"
if [ -f FIRST_PASSWORD.txt ]; then echo "Pass:  $(cat FIRST_PASSWORD.txt)   <- save it, then: shred -u ${DIR}/deploy/FIRST_PASSWORD.txt"; fi
[ "${LOCAL_LLM}" -eq 1 ] && echo "In the web UI choose the provider « ollama » and set --model to ${MODEL} (documents stay on this server)."
