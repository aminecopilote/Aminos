#!/usr/bin/env bash
# Ubuntu/Debian/macOS: clone the two external repos and install the agents.
#   ./external/install.sh [--tool claude-code] [--division engineering,security] [--dir ~/aminos-external]
# Unrecognised options are passed to agency-agents' scripts/install.sh.
set -euo pipefail

dir="${AMINOS_EXTERNAL_DIR:-$HOME/aminos-external}"
args=()
while [ $# -gt 0 ]; do
  case "$1" in
    --dir) dir="$2"; shift 2 ;;
    *) args+=("$1"); shift ;;
  esac
done
[ ${#args[@]} -gt 0 ] || args=(--tool claude-code --no-interactive)

command -v git >/dev/null || { echo "git missing: sudo apt update && sudo apt install -y git" >&2; exit 1; }

clone() {  # clone <url> <name>
  if [ -d "$dir/$2/.git" ]; then git -C "$dir/$2" pull --ff-only
  else git clone --depth 1 "$1" "$dir/$2"; fi
}
mkdir -p "$dir"
clone https://github.com/msitarzewski/agency-agents.git agency-agents
clone https://github.com/ashishpatel26/500-AI-Agents-Projects.git 500-AI-Agents-Projects

(cd "$dir/agency-agents" && bash scripts/install.sh "${args[@]}")

echo
echo "agency-agents installed (${args[*]})."
echo "500-AI-Agents-Projects (reference list, nothing to install): $dir/500-AI-Agents-Projects"
