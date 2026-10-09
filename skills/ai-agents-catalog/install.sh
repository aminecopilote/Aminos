#!/usr/bin/env bash
# Install the skill into an OpenClaw workspace: ./install.sh [workspace_dir]
set -euo pipefail
src="$(cd "$(dirname "$0")" && pwd)"
ws="${1:-${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}}"
dest="$ws/skills/ai-agents-catalog"
mkdir -p "$dest"
cp -r "$src/SKILL.md" "$src/catalog.json" "$src/scripts" "$dest/"
echo "Installed to $dest. Start a new OpenClaw session to load it."
echo "Alternative: openclaw skills install $src"
