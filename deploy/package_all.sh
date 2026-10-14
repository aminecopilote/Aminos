#!/usr/bin/env bash
# One downloadable file with everything: dist/Aminos-complet-<commit>.zip
#   windows/   ready-to-install bundle (offline, Python 3.12 / Windows x64)
#   notebooks/ Google Colab notebooks     docs/   guides and reports
#   linux/     Docker, Caddy, install.sh, render.yaml        source/   full source of this commit
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
[ -z "$(git status --porcelain)" ] || { echo "commit your changes first: the package is built from HEAD" >&2; exit 1; }
SHA="$(git rev-parse --short HEAD)"; NAME="Aminos-complet-$SHA"; OUT="dist/$NAME"

deploy/windows/build_bundle.sh >/dev/null            # rebuilds dist/aminos-windows (fresh wheelhouse + manifest)
rm -rf "$OUT"; mkdir -p "$OUT"/{windows,docs,linux,source}
cp -r dist/aminos-windows "$OUT/windows/aminos-windows"
cp -r notebooks "$OUT/notebooks"
cp README.md deploy/SAAS.md deploy/DEPLOY.md lab/REPORT.md lab/CORPORA.md deploy/windows/LISEZ-MOI.md "$OUT/docs/"
git archive HEAD deploy render.yaml .dockerignore | tar -x -C "$OUT/linux"
rm -rf "$OUT/linux/deploy/windows"                   # already shipped, ready to install, under windows/
git archive HEAD | tar -x -C "$OUT/source"

cat > "$OUT/LISEZ-MOI.txt" <<TXT
AMINOS — paquet complet (version $SHA)

Que faire de quoi
  windows\\aminos-windows\\   Installation sur Windows, sans Docker, hors ligne (Python 3.12, Windows 64 bits).
                              PowerShell en administrateur dans ce dossier :
                                Set-ExecutionPolicy -Scope Process Bypass
                                .\\install.ps1 -Saas                    multi-utilisateurs, accès local http://127.0.0.1:8501
                                .\\install.ps1 -Saas -Domain votre.domaine   + HTTPS public (il faut un nom de domaine)
                                .\\install.ps1 -Saas -Orchestrator -Agency   + supervision + chef d'agence
                              Mise à jour avec un nouveau paquet : .\\update.ps1     Désinstallation : C:\\Aminos\\uninstall.ps1
  notebooks\\                 Google Colab : commencez par OpenClaw-GPU-Test.ipynb (voir notebooks\\README.md).
  linux\\                     Serveur Linux : Docker + Caddy (deploy\\install.sh) et render.yaml pour Render.
  docs\\                      Guides : SAAS.md (comptes, confidentialité, limites), DEPLOY.md, REPORT.md (essais), CORPORA.md.
  source\\                    Code source complet de cette version.
  SHA256SUMS.txt             Sommes de contrôle de tous les fichiers du paquet.

À savoir avant d'utiliser
  - L'installation Windows n'a pas été essayée sur votre serveur. Testée sur un vrai Windows par l'intégration continue,
    sauf le démarrage automatique par tâche planifiée : après l'installation, redémarrez une fois le serveur pour vérifier.
  - Aucun modèle de traduction n'est fourni : installez Ollama (https://ollama.com) ou configurez un fournisseur.
    Ce n'est ni une apostille officielle ni une signature qualifiée.
  - agent-hq (agency\\) n'a aucune authentification : il n'écoute que sur 127.0.0.1, ne l'exposez jamais.
  - Les skills tiers (aminos skills ...) ne sont pas audités : relisez-les avant usage.
TXT
( cd "$OUT" && find . -type f ! -name SHA256SUMS.txt | sort | xargs -d '\n' sha256sum | sed 's# \./# #' > SHA256SUMS.txt )
( cd dist && python3 -c "import shutil,sys; shutil.make_archive(sys.argv[1],'zip','.',sys.argv[1])" "$NAME" )
echo "dist/$NAME.zip  $(du -h "dist/$NAME.zip" | cut -f1)  ($(wc -l < "$OUT/SHA256SUMS.txt") fichiers)"
