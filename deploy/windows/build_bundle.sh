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

cp app.py saas_app.py deploy/windows/{install.ps1,run-app.ps1,uninstall.ps1,Lancer-Aminos.bat,requirements.txt,LISEZ-MOI.md} "$OUT/"
( cd "$OUT/wheelhouse" && sha256sum * > ../SHA256SUMS.txt )
( cd dist && python3 -c "import shutil; shutil.make_archive('aminos-windows','zip','.','aminos-windows')" )
echo "$(du -h dist/aminos-windows.zip | cut -f1)  dist/aminos-windows.zip  ($(ls $OUT/wheelhouse | wc -l) wheels)"
