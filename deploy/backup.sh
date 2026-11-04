#!/usr/bin/env bash
# Archive the translation memory / notarisation ledger volume: deploy/backup.sh [dir]
set -euo pipefail
OUT="${1:-.}"; STAMP="$(date +%Y%m%d-%H%M%S)"
docker run --rm -v aminos_aminos-data:/data:ro -v "$(cd "$OUT" && pwd)":/out alpine \
  tar czf "/out/aminos-data-${STAMP}.tgz" -C /data .
echo "${OUT}/aminos-data-${STAMP}.tgz"
