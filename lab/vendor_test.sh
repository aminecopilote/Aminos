#!/usr/bin/env bash
# Clone the five third-party repos at pinned commits, install them in isolation and run their own tests.
# Usage: lab/vendor_test.sh [name ...]   (default: all).  Results: lab/results/<name>.{log,status}
# Third-party code is untrusted: npm installs use --ignore-scripts, everything lives under lab/vendor (gitignored).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR="$ROOT/lab/vendor"; RESULTS="$ROOT/lab/results"
mkdir -p "$VENDOR" "$RESULTS"

declare -A REPO=(
  [agent-coordinator]=SuperInstance/agent-coordinator
  [agent-hq]=tools-for-agents/agent-hq
  [reverseengineeranything]=ChristopheAI/reverseengineeranything
  [legal-translator]=zaibunnisa33/legal-translator
  [agency-agents]=msitarzewski/agency-agents
)
declare -A SHA=(
  [agent-coordinator]=4d2560d2e53d2d066328ed4a0250376efe44aa2a
  [agent-hq]=785cd8c9a55b2b517eb8eb8f680cd65985992282
  [reverseengineeranything]=9f3639f29ff8a35d0b862bfe81c27668d667c14f
  [legal-translator]=69d2ed6ac038bf6ba5589c792ba4a1a998400d59
  [agency-agents]=bd956db032d907387e6b9ddebff3e18f1de8c679
)

fetch() { # name: full clone, then the pinned commit
  local n=$1 d="$VENDOR/$1"
  [ -d "$d/.git" ] || git clone -q "https://github.com/${REPO[$n]}.git" "$d" || return 1
  git -C "$d" checkout -q "${SHA[$n]}"
}

run_one() { # name
  local n=$1 d="$VENDOR/$1" log="$RESULTS/$1.log"
  : > "$log"
  { fetch "$n" && cd "$d" && case "$n" in
      agent-coordinator)
        python3 -m venv "$VENDOR/.venv-$n" && . "$VENDOR/.venv-$n/bin/activate"
        pip install -q -e . pytest pytest-asyncio && python -m pytest -q tests ;;
      agent-hq)
        node --test ;;
      reverseengineeranything)
        npm ci --ignore-scripts --no-audit --no-fund && npm run build && npx vitest run ;;
      legal-translator)
        python3 -m venv "$VENDOR/.venv-$n" && . "$VENDOR/.venv-$n/bin/activate"
        pip install -q -r requirements.txt && python -I -c "import ast,sys,pathlib; [ast.parse(p.read_text()) for p in pathlib.Path('.').rglob('*.py')]; print('syntax ok')" \
          && python -c "import translator, translator.prompts as p; print('import ok', [x for x in dir(p) if not x.startswith('_')][:8])" ;;
      agency-agents)
        python3 - <<'PY'
import json, pathlib
agents = list(pathlib.Path('.').glob('*/*.md'))
print('markdown files:', len(agents))
d = json.load(open('divisions.json')); print('divisions.json keys:', type(d).__name__, len(d))
PY
        ;;
    esac; } >> "$log" 2>&1
  local rc=$?
  echo "$rc" > "$RESULTS/$n.status"
  printf '%-26s %s\n' "$n" "$([ $rc -eq 0 ] && echo PASS || echo "FAIL($rc)")"
}

names=("$@"); [ ${#names[@]} -eq 0 ] && names=("${!REPO[@]}")
for n in "${names[@]}"; do run_one "$n" & done
wait
