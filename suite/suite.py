#!/usr/bin/env python3
"""Aminos suite: install, update and start every Aminos project with one command.

Same code on Ubuntu, macOS and Windows. Started by install.sh / install.ps1, then by the
`aminos-suite` command those scripts put on the PATH. Standard library only.

    aminos-suite list                 projects and their state
    aminos-suite start <project>      start a project (aminos, saas, erp, eka, eka-api, jeu, atelier)
    aminos-suite update               fetch the latest code of every project, keep local changes
    aminos-suite kimi ask "question"  Kimi K3 through the Moonshot API (MOONSHOT_API_KEY)
    aminos-suite kimi test|chat|doctor|download   local Kimi K3 C engine (kimi-k3-in-c)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

AMINOS_REPO = "https://github.com/aminecopilote/Aminos.git"
KIMI_REPO = "https://github.com/FareedKhan-dev/kimi-k3-in-c.git"
KIMI_COMMIT = "81bb6c23ccee2154bc35cad922588ab66494a9a9"   # v1.1.0, 2026-10-02 (pinned, tested)
NODE_VERSION = "v24.22.2"                                     # LTS, used only if no Node >= 20 is installed
KIMI_API = "https://api.moonshot.ai/v1"
WIN = os.name == "nt"

# Source of each project. A branch that no longer exists (merged and deleted) falls back to main.
# Override one with AMINOS_SUITE_REF_<NAME>, e.g. AMINOS_SUITE_REF_AMINOS=main.
SOURCES = {
    "aminos":  (AMINOS_REPO, "claude/stoic-rubin-iq1po6"),      # translation, superagent, ERP, n8n
    "eka":     (AMINOS_REPO, "claude/eka-backend-api"),         # EKA CONSEIL site + EKA SYSTÈME
    "jeu":     (AMINOS_REPO, "claude/jeu-questions-defis"),     # questions & challenges game
    "atelier": (AMINOS_REPO, "claude/sweet-pascal-8oyvxa"),     # atelier-agent
    "agents":  (AMINOS_REPO, "claude/admiring-ritchie-z1nubg"), # agency-agents installer (optional)
    "kimi":    (KIMI_REPO, KIMI_COMMIT),                        # Kimi K3 inference in C
}
OPTIONAL = {"agents"}  # installed only with --with agents (writes into your Claude Code agents folder)

HOME = Path(os.environ.get("AMINOS_SUITE_HOME") or Path.home() / "aminos-suite").expanduser().resolve()
PROJECTS, TOOLS, BIN = HOME / "projects", HOME / "tools", HOME / "bin"
ENV_FILE = HOME / ".env"
ENV_TEMPLATE = """# Aminos suite keys: fill in the ones you use. Read by `aminos-suite start` and `aminos-suite kimi`.
MOONSHOT_API_KEY=
# KIMI_BASE_URL=https://api.moonshot.cn/v1   (keys from the China platform)
# KIMI_REASONING_EFFORT=high                 (low | high | max)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
MISTRAL_API_KEY=
GROQ_API_KEY=
OPENROUTER_API_KEY=
# HF_TOKEN=                                  (only for `aminos-suite kimi download`)
"""


def say(msg: str) -> None:
    print(f"[aminos-suite] {msg}", flush=True)


def run(cmd: list, cwd: Path | None = None, env: dict | None = None, check: bool = True, timeout: int | None = None):
    say("$ " + " ".join(str(c) for c in cmd))
    return subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, check=check, timeout=timeout)


def load_env() -> dict:
    env = dict(os.environ)
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            k, sep, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if sep and k and not k.startswith("#") and v and k not in os.environ:
                env[k] = v
    return env


# ------------------------------------------------------------------------- git --
def ref_for(name: str) -> str:
    return os.environ.get(f"AMINOS_SUITE_REF_{name.upper()}") or SOURCES[name][1]


def git_sync(name: str) -> Path:
    """Shallow checkout of the project's ref. Local edits are never overwritten."""
    url, ref = SOURCES[name][0], ref_for(name)
    d = PROJECTS / name
    if not (d / ".git").exists():
        d.mkdir(parents=True, exist_ok=True)
        run(["git", "init", "-q"], cwd=d)
        run(["git", "remote", "add", "origin", url], cwd=d)
    if subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", ref], cwd=d).returncode != 0:
        if url != AMINOS_REPO or ref == "main":
            raise RuntimeError(f"{name}: cannot fetch {ref} from {url}")
        say(f"{name}: {ref} not found (merged?), using main")
        run(["git", "fetch", "-q", "--depth", "1", "origin", "main"], cwd=d)
    has_head = subprocess.run(["git", "rev-parse", "-q", "--verify", "HEAD"], cwd=d, capture_output=True).returncode == 0
    dirty = has_head and subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=d,
                                        capture_output=True, text=True).stdout.strip()
    if dirty:
        say(f"{name}: local changes found, code left as is (commit or discard them to update)")
    else:
        run(["git", "-c", "advice.detachedHead=false", "checkout", "-q", "--force", "--detach", "FETCH_HEAD"], cwd=d)
    return d


# ------------------------------------------------------------------------ node --
def node_bin() -> Path | None:
    """Folder holding node/npm, version >= 20: the system one, else a private copy."""
    local = TOOLS / "node" if WIN else TOOLS / "node" / "bin"
    for folder in [local, *(Path(p) for p in os.environ.get("PATH", "").split(os.pathsep) if p)]:
        exe = folder / ("node.exe" if WIN else "node")
        if exe.exists():
            try:
                out = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=30).stdout
                if int(out.strip().lstrip("v").split(".")[0]) >= 20:
                    return folder
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
    return None


def ensure_node() -> Path:
    found = node_bin()
    if found:
        return found
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    osname = {"linux": "linux", "darwin": "darwin", "win32": "win"}[sys.platform]
    name = f"node-{NODE_VERSION}-{osname}-{arch}" + (".zip" if WIN else ".tar.xz")
    base = f"https://nodejs.org/dist/{NODE_VERSION}/"
    say(f"Node.js >= 20 not found: downloading {name}")
    sums = urllib.request.urlopen(base + "SHASUMS256.txt", timeout=60).read().decode()
    want = next(line.split()[0] for line in sums.splitlines() if line.endswith("  " + name))
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / name
        with urllib.request.urlopen(base + name, timeout=600) as r, open(archive, "wb") as f:
            shutil.copyfileobj(r, f)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != want:
            raise RuntimeError(f"{name}: SHA-256 mismatch, download refused")
        out = Path(tmp) / "x"
        if WIN:
            zipfile.ZipFile(archive).extractall(out)
        else:
            with tarfile.open(archive) as t:
                t.extractall(out, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
        shutil.rmtree(TOOLS / "node", ignore_errors=True)
        TOOLS.mkdir(parents=True, exist_ok=True)
        shutil.move(str(next(out.iterdir())), str(TOOLS / "node"))
    found = node_bin()
    if not found:
        raise RuntimeError("Node.js install failed")
    return found


def node_env() -> dict:
    env = load_env()
    env["PATH"] = str(ensure_node()) + os.pathsep + env.get("PATH", "")
    return env


def npm(env: dict) -> str:
    return shutil.which("npm", path=env["PATH"]) or "npm"


# ----------------------------------------------------------------- installers --
def setup_aminos(d: Path, a) -> None:
    run([sys.executable, "-m", "pip", "install", "-q", "--upgrade", "pip"])
    run([sys.executable, "-m", "pip", "install", "-q", "-e", f"{d}[all]"])
    if not a.no_tests:
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=d, check=False)


def setup_eka(d: Path, a) -> None:
    env = node_env()
    run([npm(env), "ci", "--no-audit", "--no-fund"], cwd=d / "eka-systeme", env=env)
    if not a.no_tests:
        run([npm(env), "test"], cwd=d / "eka-systeme", env=env, check=False)


def setup_jeu(d: Path, a) -> None:
    if not a.no_tests:
        env = node_env()
        run([shutil.which("node", path=env["PATH"]) or "node", "--test", "jeu/tests/game.test.js"], cwd=d, env=env, check=False)


def setup_atelier(d: Path, a) -> None:
    node_env()
    app = d / "atelier-agent"
    if not (app / ".env").exists():   # keys stay in the suite .env, loaded at start
        (app / ".env").write_text("PORT=3000\nSKILLS_DIRS=../.claude/skills\n", encoding="utf-8")


def setup_agents(d: Path, a) -> None:
    if WIN:
        run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", d / "external" / "install.ps1"])
    else:
        run(["bash", d / "external" / "install.sh"])


def msys2_root() -> Path | None:
    for p in (os.environ.get("MSYS2_ROOT"), r"C:\msys64", r"C:\tools\msys64"):
        if p and (Path(p) / "usr" / "bin" / "bash.exe").exists():
            return Path(p)
    return None


def kimi_make(d: Path, target: str = "") -> int:
    """Run `make <target>` in kimi-k3-in-c with the right toolchain for this OS."""
    if WIN:
        root = msys2_root()
        if not root:
            raise RuntimeError("MSYS2 missing (winget install MSYS2.MSYS2), needed to build Kimi K3 on Windows")
        env = dict(os.environ, MSYSTEM="MINGW64", CHERE_INVOKING="1")
        script = ("pacman -S --noconfirm --needed mingw-w64-x86_64-gcc make >/dev/null && "
                  f"make -j{os.cpu_count() or 2} {target}")
        return run([root / "usr" / "bin" / "bash.exe", "-lc", script], cwd=d, env=env, check=False).returncode
    make = shutil.which("gmake") if sys.platform == "darwin" and shutil.which("gmake") else "make"
    if not shutil.which(make) or not (shutil.which("cc") or shutil.which("gcc")):
        raise RuntimeError("C compiler or make missing (Ubuntu: sudo apt install build-essential; macOS: xcode-select --install)")
    if sys.platform == "darwin" and not (shutil.which("brew") and
                                         subprocess.run(["brew", "--prefix", "libomp"], capture_output=True).returncode == 0):
        raise RuntimeError("macOS needs Homebrew's libomp for OpenMP: brew install libomp")
    return run([make, f"-j{os.cpu_count() or 2}", *([target] if target else [])], cwd=d, check=False).returncode


def setup_kimi(d: Path, a) -> None:
    if kimi_make(d):
        raise RuntimeError("Kimi K3 build failed")
    if not a.no_tests:
        say("Kimi K3: running the engine's own tests (about a minute, no model needed)")
        if kimi_make(d, "test"):
            raise RuntimeError("Kimi K3 tests failed")


SETUP = {"aminos": setup_aminos, "eka": setup_eka, "jeu": setup_jeu, "atelier": setup_atelier,
         "agents": setup_agents, "kimi": setup_kimi}


def write_launchers() -> None:
    BIN.mkdir(parents=True, exist_ok=True)
    me, py = Path(__file__).resolve(), Path(sys.executable)
    venv_bin = py.parent
    if WIN:
        (BIN / "aminos-suite.cmd").write_text(
            f'@echo off\r\nset "AMINOS_SUITE_HOME={HOME}"\r\n"{py}" "{me}" %*\r\n', encoding="utf-8")
        (BIN / "aminos.cmd").write_text(f'@echo off\r\n"{venv_bin / "aminos.exe"}" %*\r\n', encoding="utf-8")
    else:
        for name, body in (("aminos-suite", f'AMINOS_SUITE_HOME="{HOME}" exec "{py}" "{me}" "$@"'),
                           ("aminos", f'exec "{venv_bin / "aminos"}" "$@"')):
            f = BIN / name
            f.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
            f.chmod(0o755)


def cmd_install(a) -> int:
    HOME.mkdir(parents=True, exist_ok=True)
    if not ENV_FILE.exists():
        ENV_FILE.write_text(ENV_TEMPLATE, encoding="utf-8")
        if not WIN:
            ENV_FILE.chmod(0o600)
    names = [n for n in SOURCES if n not in OPTIONAL or n in a.with_]
    if a.only:
        names = [n for n in SOURCES if n in a.only]
    names = [n for n in names if n not in a.skip]
    unknown = set(a.only + a.skip + a.with_) - set(SOURCES)
    if unknown:
        say(f"unknown project(s): {', '.join(sorted(unknown))}. Available: {', '.join(SOURCES)}")
        return 2
    results = {}
    for n in names:
        say(f"===== {n} ({ref_for(n)})")
        try:
            SETUP[n](git_sync(n), a)
            results[n] = "ok"
        except (RuntimeError, OSError, subprocess.SubprocessError) as e:
            results[n] = f"FAILED: {e}"
            say(f"{n}: {e}")
    write_launchers()
    saved = json.loads((HOME / "suite.json").read_text()) if (HOME / "suite.json").exists() else {}
    state = {"suite_ref": a.suite_ref or saved.get("suite_ref", "main"), "installed": {**saved.get("installed", {}), **results}}
    (HOME / "suite.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    print("\n================ Aminos suite ================")
    for n, r in results.items():
        print(f"  {n:8} {r}")
    print(f"\n  folder : {HOME}\n  keys   : {ENV_FILE}  (put MOONSHOT_API_KEY there for Kimi K3)")
    print("  next   : aminos-suite list   |   aminos-suite start aminos   |   aminos-suite kimi ask \"Bonjour\"")
    return 0 if all(r == "ok" for r in results.values()) else 1


def cmd_update(a) -> int:
    suite = Path(__file__).resolve().parents[1]
    saved = json.loads((HOME / "suite.json").read_text()) if (HOME / "suite.json").exists() else {}
    ref = a.suite_ref or saved.get("suite_ref") or "main"
    if subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", ref], cwd=suite).returncode == 0:
        if not subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=suite,
                              capture_output=True, text=True).stdout.strip():
            run(["git", "-c", "advice.detachedHead=false", "checkout", "-q", "--detach", "FETCH_HEAD"], cwd=suite)
    extra = [f"--with={','.join(a.with_)}"] if a.with_ else []
    extra += ["--no-tests"] if a.no_tests else []
    return subprocess.run([sys.executable, str(suite / "suite" / "suite.py"), "install", "--suite-ref", ref, *extra]).returncode


# ---------------------------------------------------------------------- start --
def start_spec(name: str):
    py = sys.executable
    return {
        "aminos":  (PROJECTS / "aminos", [py, "-m", "streamlit", "run", "app.py"], "http://localhost:8501"),
        "saas":    (PROJECTS / "aminos", [py, "-m", "streamlit", "run", "saas_app.py"], "http://localhost:8501"),
        "erp":     (PROJECTS / "aminos", [py, "-m", "aminos.erp"], "see the address printed below"),
        "eka":     (PROJECTS / "eka" / "eka-systeme", ["npm", "run", "dev"], "http://localhost:5173"),
        "eka-api": (PROJECTS / "eka" / "eka-systeme", ["npm", "run", "api"], "see the address printed below"),
        "jeu":     (PROJECTS / "jeu" / "jeu", [py, "-m", "http.server", "8080", "--bind", "127.0.0.1"],
                    "http://localhost:8080"),
        "atelier": (PROJECTS / "atelier" / "atelier-agent", ["node", "server.js"], "http://localhost:3000"),
    }.get(name)


def cmd_start(a) -> int:
    spec = start_spec(a.project)
    if not spec:
        say("projects you can start: aminos, saas, erp, eka, eka-api, jeu, atelier (Kimi: aminos-suite kimi ...)")
        return 2
    cwd, argv, url = spec
    if not cwd.exists():
        owner = {"saas": "aminos", "erp": "aminos", "eka-api": "eka"}.get(a.project, a.project)
        say(f"{a.project} is not installed: aminos-suite install --only {owner}")
        return 1
    env = node_env() if argv[0] in ("npm", "node") else load_env()
    if argv[0] in ("npm", "node"):
        argv = [shutil.which(argv[0], path=env["PATH"]) or argv[0], *argv[1:]]
    say(f"{a.project}: {url}  (Ctrl+C to stop)")
    try:
        return subprocess.run(argv + a.args, cwd=cwd, env=env).returncode
    except KeyboardInterrupt:
        return 0


def cmd_list(a) -> int:
    state = json.loads((HOME / "suite.json").read_text()).get("installed", {}) if (HOME / "suite.json").exists() else {}
    for n in SOURCES:
        d = PROJECTS / n
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=d, capture_output=True, text=True).stdout.strip() \
            if (d / ".git").exists() else ""
        print(f"  {n:8} {state.get(n, 'not installed'):14} {ref_for(n)[:40]:40} {rev}")
    env = load_env()
    print(f"\n  Kimi K3 API key: {'set' if env.get('MOONSHOT_API_KEY') or env.get('KIMI_API_KEY') else 'missing'} ({ENV_FILE})")
    return 0


# ----------------------------------------------------------------------- kimi --
def kimi_ask(question: str, env: dict, model: str = "kimi-k3") -> str:
    key = env.get("MOONSHOT_API_KEY") or env.get("KIMI_API_KEY")
    if not key:
        raise RuntimeError(f"MOONSHOT_API_KEY missing: add it to {ENV_FILE} (key from https://platform.kimi.ai)")
    body = {"model": model, "messages": [{"role": "user", "content": question}]}
    if env.get("KIMI_REASONING_EFFORT"):
        body["reasoning_effort"] = env["KIMI_REASONING_EFFORT"]
    req = urllib.request.Request((env.get("KIMI_BASE_URL") or KIMI_API).rstrip("/") + "/chat/completions",
                                 json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.load(r)["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Kimi API: HTTP {e.code} {e.read()[:300].decode(errors='replace')}") from e


def cmd_kimi(a) -> int:
    d = PROJECTS / "kimi"
    model_dir = Path(a.model or HOME / "kimi-model")
    trunk_dir = Path(a.trunk or HOME / "kimi-trunk")
    k3 = d / "bin" / ("k3.exe" if WIN else "k3")
    try:
        if a.action == "ask":
            if not a.text:
                say('usage: aminos-suite kimi ask "your question"')
                return 2
            print(kimi_ask(" ".join(a.text), load_env()))
            return 0
        if not k3.exists():
            say("Kimi K3 engine not built: aminos-suite install --only kimi")
            return 1
        if a.action == "test":
            return kimi_make(d, "test")
        if a.action == "doctor":
            if sys.platform != "linux":
                return subprocess.run([str(k3), "--list-presets"]).returncode
            return run(["bash", "scripts/k3-doctor.sh", model_dir], cwd=d, check=False).returncode
        if a.action == "download":
            if WIN:
                say("download/pack scripts are bash: run them from WSL or the MSYS2 shell (see the kimi-k3-in-c README)")
                return 1
            if not a.yes:
                say(f"This downloads 1.56 TB into {model_dir} and writes a 109 GB trunk into {trunk_dir}. "
                    "Needs HF_TOKEN in the .env. Re-run with --yes to go ahead.")
                return 2
            env = load_env()
            if run(["bash", "scripts/download-model.sh", model_dir], cwd=d, env=env, check=False).returncode:
                return 1
            return run(["bash", "scripts/pack-trunk.sh", model_dir, trunk_dir], cwd=d, env=env, check=False).returncode
        if a.action == "chat":
            if not (model_dir / "config.json").exists() or not trunk_dir.exists():
                say(f"no local model in {model_dir} / {trunk_dir}: use `aminos-suite kimi ask` (API), "
                    "or `aminos-suite kimi download --yes` (1.7 TB of disk)")
                return 1
            return subprocess.run([str(k3), str(model_dir), "--trunk", str(trunk_dir), "--preset", a.preset,
                                   "--tok", str(model_dir), "--chat", *a.text]).returncode
    except RuntimeError as e:
        say(str(e))
        return 1
    return 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="aminos-suite", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    csv = lambda s: [x.strip() for x in s.split(",") if x.strip()]  # noqa: E731
    for name in ("install", "update"):
        p = sub.add_parser(name)
        p.add_argument("--only", type=csv, default=[], help="comma-separated projects")
        p.add_argument("--skip", type=csv, default=[])
        p.add_argument("--with", dest="with_", type=csv, default=[], help="optional projects, e.g. agents")
        p.add_argument("--no-tests", action="store_true", help="skip each project's tests")
        p.add_argument("--suite-ref", default="", help="branch of the Aminos repository holding this installer")
        p.set_defaults(fn=cmd_install if name == "install" else cmd_update)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    p = sub.add_parser("start")
    p.add_argument("project")
    p.add_argument("args", nargs=argparse.REMAINDER)
    p.set_defaults(fn=cmd_start)
    p = sub.add_parser("kimi", help="Kimi K3: ask (API) | test | doctor | download | chat (local engine)")
    p.add_argument("action", choices=["ask", "test", "doctor", "download", "chat"])
    p.add_argument("text", nargs="*")
    p.add_argument("--model", help="checkpoint folder (default: <suite>/kimi-model)")
    p.add_argument("--trunk", help="packed trunk folder (default: <suite>/kimi-trunk)")
    p.add_argument("--preset", default="auto")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=cmd_kimi)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
