#!/usr/bin/env bash
# Build dist/aminos-windows.zip on any OS: Aminos + pinned agent-coordinator wheels, an offline wheelhouse for
# Windows x64 / Python 3.12, the app, and the install scripts.   Usage: deploy/windows/build_bundle.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
AC_SHA=4d2560d2e53d2d066328ed4a0250376efe44aa2a
OUT="dist/aminos-windows"; rm -rf dist; mkdir -p "$OUT/wheelhouse"

python3 -m pip wheel -q --no-deps -w "$OUT/wheelhouse" . && rm -rf build
python3 -m pip wheel -q --no-deps -w "$OUT/wheelhouse" "git+https://github.com/SuperInstance/agent-coordinator@${AC_SHA}"
python3 -m pip download -q --only-binary=:all: --platform win_amd64 --python-version 3.12 --implementation cp --abi cp312 \
  -d "$OUT/wheelhouse" -r deploy/windows/requirements.txt

cp app.py saas_app.py deploy/windows/{install.ps1,update.ps1,run-app.ps1,run-orchestrator.ps1,run-agent-hq.ps1,uninstall.ps1,Lancer-Aminos.bat,requirements.txt,LISEZ-MOI.md} "$OUT/"

# own skills and the chef d'agence notes
mkdir -p "$OUT/skills" "$OUT/agency"
cp -r skills/. "$OUT/skills/"
cp agency/AGENTS.md agency/MEMORY-orchestrateur.md agency/start-agent-hq.mjs "$OUT/agency/"

# local copies of agent-hq and agent-coordinator at the commits that were tested (MIT; licence files come with the source)
snapshot() { # repo sha dest
  local tmp; tmp="$(mktemp -d)"
  git init -q "$tmp" && git -C "$tmp" remote add origin "https://github.com/$1.git" \
    && git -C "$tmp" fetch -q --depth 1 origin "$2" && mkdir -p "$3" && git -C "$tmp" archive FETCH_HEAD | tar -x -C "$3"
  rm -rf "$tmp"
}
snapshot SuperInstance/agent-coordinator "$AC_SHA" "$OUT/agency/agent-coordinator"
snapshot tools-for-agents/agent-hq 785cd8c9a55b2b517eb8eb8f680cd65985992282 "$OUT/agency/agent-hq"

# one manifest for everything in the bundle (install.ps1 refuses a bundle whose files do not match)
( cd "$OUT" && find . -type f ! -name SHA256SUMS.txt | sort | xargs -d '\n' sha256sum | sed 's# \./# #' > SHA256SUMS.txt )
( cd dist && python3 -c "import shutil; shutil.make_archive('aminos-windows','zip','.','aminos-windows')" )
echo "$(du -h dist/aminos-windows.zip | cut -f1)  dist/aminos-windows.zip  ($(ls $OUT/wheelhouse | wc -l) wheels)"
