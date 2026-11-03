#!/usr/bin/env bash
# Aminos suite, one command on Ubuntu/Debian and macOS:
#   curl -fsSL https://raw.githubusercontent.com/aminecopilote/Aminos/main/install.sh | bash
# Options (after `bash -s --`):
#   --ref BRANCH        branch of the Aminos repository holding this installer (default: main)
#   --home DIR          install folder (default: ~/aminos-suite)
#   --no-system         do not install system packages (git, compiler, Python venv, libomp)
#   --only a,b  --skip a,b  --with agents  --no-tests   passed to the suite installer
# Projects: aminos, eka, jeu, atelier, kimi (Kimi K3 in C), agents (optional).
set -euo pipefail

REF="${AMINOS_SUITE_REF:-main}"
SUITE_HOME="${AMINOS_SUITE_HOME:-$HOME/aminos-suite}"
SYSTEM=1
UV_VERSION="0.11.32"
REPO="https://github.com/aminecopilote/Aminos.git"
pass=()
while [ $# -gt 0 ]; do
  case "$1" in
    --ref) REF="$2"; shift 2 ;;
    --home) SUITE_HOME="$2"; shift 2 ;;
    --no-system) SYSTEM=0; shift ;;
    *) pass+=("$1"); shift ;;
  esac
done
say() { printf '[aminos-suite] %s\n' "$*"; }
SUDO=""; [ "$(id -u)" -eq 0 ] || { command -v sudo >/dev/null && SUDO="sudo"; }

# ---- system packages ----------------------------------------------------------------
case "$(uname -s)" in
  Linux)
    if [ "$SYSTEM" = 1 ] && command -v apt-get >/dev/null; then
      need=()
      for p in git curl ca-certificates build-essential python3 python3-venv xz-utils; do
        dpkg -s "$p" >/dev/null 2>&1 || need+=("$p")
      done
      if [ ${#need[@]} -gt 0 ]; then
        say "installing ${need[*]}"
        $SUDO apt-get update -qq && $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${need[@]}"
      fi
    elif [ "$SYSTEM" = 1 ] && command -v dnf >/dev/null; then
      $SUDO dnf install -y -q git curl gcc make python3 xz
    fi ;;
  Darwin)
    if ! xcode-select -p >/dev/null 2>&1; then
      say "Apple command line tools missing: a window opens to install them; run this command again afterwards."
      xcode-select --install || true
      exit 1
    fi
    if [ "$SYSTEM" = 1 ]; then
      if command -v brew >/dev/null; then
        brew list libomp >/dev/null 2>&1 || brew install libomp     # OpenMP for the Kimi K3 engine
      else
        say "Homebrew not found: the Kimi K3 engine needs it (brew install libomp). Everything else installs."
      fi
    fi ;;
  *) say "unsupported system $(uname -s): on Windows use install.ps1"; exit 1 ;;
esac
command -v git >/dev/null || { say "git is required"; exit 1; }

# ---- Python 3.12 via uv (no admin rights), else system python3 >= 3.10 --------------
UV="$(command -v uv || true)"; [ -n "$UV" ] || { [ -x "$HOME/.local/bin/uv" ] && UV="$HOME/.local/bin/uv"; } || true
if [ -z "$UV" ]; then
  say "installing uv $UV_VERSION (Python manager)"
  if curl -LsSf "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-installer.sh" | env UV_NO_MODIFY_PATH=1 sh >/dev/null; then
    UV="$HOME/.local/bin/uv"
  fi
fi

# ---- the suite code itself ------------------------------------------------------------
mkdir -p "$SUITE_HOME"
SRC="$SUITE_HOME/suite"
if [ ! -d "$SRC/.git" ]; then
  git init -q "$SRC" && git -C "$SRC" remote add origin "$REPO"
fi
git -C "$SRC" fetch -q --depth 1 origin "$REF"
if [ -z "$(git -C "$SRC" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
  git -C "$SRC" -c advice.detachedHead=false checkout -q --force --detach FETCH_HEAD
fi

VENV="$SUITE_HOME/venvs/aminos"
if [ ! -x "$VENV/bin/python" ]; then
  if [ -n "$UV" ]; then
    "$UV" venv -q --seed --python 3.12 "$VENV"
  else
    python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || { say "Python >= 3.10 required"; exit 1; }
    python3 -m venv "$VENV"
  fi
fi

AMINOS_SUITE_HOME="$SUITE_HOME" "$VENV/bin/python" "$SRC/suite/suite.py" install --suite-ref "$REF" ${pass[@]+"${pass[@]}"} || status=$?

# ---- put `aminos-suite` and `aminos` on the PATH --------------------------------------
mkdir -p "$HOME/.local/bin"
for c in aminos-suite aminos; do ln -sf "$SUITE_HOME/bin/$c" "$HOME/.local/bin/$c"; done
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
       { [ -f "$rc" ] || [ "$rc" = "$HOME/.zshrc" -a "$(uname -s)" = Darwin ]; } || continue
       grep -q 'aminos-suite PATH' "$rc" 2>/dev/null || printf '\nexport PATH="$HOME/.local/bin:$PATH"  # aminos-suite PATH\n' >> "$rc"
     done
     say "open a new terminal (or run: export PATH=\"\$HOME/.local/bin:\$PATH\") to use aminos-suite" ;;
esac
exit "${status:-0}"
