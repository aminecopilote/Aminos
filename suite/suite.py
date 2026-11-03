#!/usr/bin/env python3
"""Aminos suite: install, update and start every Aminos project with one command.

Same code on Ubuntu, macOS and Windows. Started by install.sh / install.ps1, then by the
`aminos-suite` command those scripts put on the PATH. Standard library only.

    aminos-suite list                 projects and their state
    aminos-suite start <project>      start a project (aminos, saas, erp, eka, eka-api, jeu, atelier)
    aminos-suite update               fetch the latest code of every project, keep local changes
    aminos-suite llm list             local models (llama.cpp, compiled on this machine)
    aminos-suite llm download <model> Gemma 3 1B, Phi-4 mini, Mistral Small 24B, Mixtral 8x7B
    aminos-suite llm chat <model>     chat in the terminal
    aminos-suite llm serve <model>    OpenAI-compatible server on 127.0.0.1:8090 (Aminos: --provider llamacpp)
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
LLAMA_REPO = "https://github.com/ggml-org/llama.cpp.git"
LLAMA_TAG = "b11700"                                          # 2026-10-16, pinned and tested
LLAMA_COMMIT = "23f7aabc16c72f6f707dba227251c35d7bd1ed96"
NODE_VERSION = "v24.22.2"                                     # LTS, used only if no Node >= 20 is installed
LLM_PORT = 8090

# GGUF models, Q4_K_M quantisation: (Hugging Face repository, file, approx. file GB, RAM GB needed).
# The size and SHA-256 are read from Hugging Face at download time and every file is checked.
MODELS = {
    "gemma3-1b":         ("ggml-org/gemma-3-1b-it-GGUF", "gemma-3-1b-it-Q4_K_M.gguf", 0.8, 2),
    "phi4-mini":         ("bartowski/microsoft_Phi-4-mini-instruct-GGUF",
                          "microsoft_Phi-4-mini-instruct-Q4_K_M.gguf", 2.5, 4),
    "mistral-small-24b": ("bartowski/mistralai_Mistral-Small-3.2-24B-Instruct-2506-GGUF",
                          "mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf", 14.3, 16),
    "mixtral-8x7b":      ("TheBloke/Mixtral-8x7B-Instruct-v0.1-GGUF", "mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf", 26.4, 32),
}
WIN = os.name == "nt"

# Source of each project. A branch that no longer exists (merged and deleted) falls back to main.
# Override one with AMINOS_SUITE_REF_<NAME>, e.g. AMINOS_SUITE_REF_AMINOS=main.
SOURCES = {
    "aminos":  (AMINOS_REPO, "claude/stoic-rubin-iq1po6"),      # translation, superagent, ERP, n8n
    "eka":     (AMINOS_REPO, "claude/eka-backend-api"),         # EKA CONSEIL site + EKA SYSTÈME
    "jeu":     (AMINOS_REPO, "claude/jeu-questions-defis"),     # questions & challenges game
    "atelier": (AMINOS_REPO, "claude/sweet-pascal-8oyvxa"),     # atelier-agent
    "agents":  (AMINOS_REPO, "claude/admiring-ritchie-z1nubg"), # agency-agents installer (optional)
    "llama":   (LLAMA_REPO, LLAMA_TAG),                         # llama.cpp, compiled from source
}
OPTIONAL = {"agents"}  # installed only with --with agents (writes into your Claude Code agents folder)

HOME = Path(os.environ.get("AMINOS_SUITE_HOME") or Path.home() / "aminos-suite").expanduser().resolve()
PROJECTS, TOOLS, BIN = HOME / "projects", HOME / "tools", HOME / "bin"
ENV_FILE = HOME / ".env"
MODELS_DIR = HOME / "models"
ENV_TEMPLATE = """# Aminos suite keys: fill in the ones you use. Read by `aminos-suite start` and `aminos-suite llm`.
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
MISTRAL_API_KEY=
GROQ_API_KEY=
OPENROUTER_API_KEY=
# HF_TOKEN=          (optional: Hugging Face token, faster or gated model downloads)
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


def llama_bin(name: str) -> Path:
    return PROJECTS / "llama" / "build" / "bin" / (name + (".exe" if WIN else ""))


def setup_llama(d: Path, a) -> None:
    """Compile llama.cpp: CMake + Ninja everywhere; GCC (Linux), Apple Clang + Metal (macOS), MinGW GCC via MSYS2 (Windows)."""
    rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=d, capture_output=True, text=True).stdout.strip()
    if ref_for("llama") == LLAMA_TAG and rev != LLAMA_COMMIT:
        raise RuntimeError(f"llama.cpp {LLAMA_TAG} is {rev}, expected {LLAMA_COMMIT}: refused")
    flags = ["-DCMAKE_BUILD_TYPE=Release", "-DBUILD_SHARED_LIBS=OFF", "-DLLAMA_BUILD_TESTS=OFF",
             "-DLLAMA_BUILD_EXAMPLES=OFF", "-DLLAMA_OPENSSL=OFF"]
    jobs = str(os.cpu_count() or 2)
    targets = ["--target", "llama-cli", "llama-server", "llama-completion"]
    if WIN:
        root = msys2_root()
        if not root:
            raise RuntimeError("MSYS2 missing (winget install MSYS2.MSYS2): it provides the C++ compiler on Windows")
        env = dict(os.environ, MSYSTEM="UCRT64", CHERE_INVOKING="1")
        flags += ["-DGGML_OPENMP=OFF", "-DCMAKE_EXE_LINKER_FLAGS=-static"]   # one self-contained .exe, no DLLs
        script = ("pacman -S --noconfirm --needed mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-cmake "
                  "mingw-w64-ucrt-x86_64-ninja >/dev/null && "
                  f"cmake -S . -B build -G Ninja {' '.join(flags)} && cmake --build build -j {jobs} {' '.join(targets)}")
        if run([root / "usr" / "bin" / "bash.exe", "-lc", script], cwd=d, env=env, check=False).returncode:
            raise RuntimeError("llama.cpp build failed")
    else:
        if not (shutil.which("c++") or shutil.which("g++") or shutil.which("clang++")):
            raise RuntimeError("C++ compiler missing (Ubuntu: sudo apt install build-essential; macOS: xcode-select --install)")
        run([sys.executable, "-m", "pip", "install", "-q", "cmake>=3.24", "ninja"])   # same CMake on every machine
        venv_bin = Path(sys.executable).parent
        env = dict(os.environ, PATH=str(venv_bin) + os.pathsep + os.environ.get("PATH", ""))
        if sys.platform == "darwin":
            flags.append("-DGGML_OPENMP=OFF")   # Apple Clang has no OpenMP; Metal is on by default
        if run([venv_bin / "cmake", "-S", ".", "-B", "build", "-G", "Ninja", *flags], cwd=d, env=env, check=False).returncode \
                or run([venv_bin / "cmake", "--build", "build", "-j", jobs, *targets], cwd=d, env=env, check=False).returncode:
            raise RuntimeError("llama.cpp build failed")
    if run([llama_bin("llama-cli"), "--version"], check=False).returncode:
        raise RuntimeError("llama-cli does not start")


def total_ram_gb() -> float:
    try:
        if sys.platform == "linux":
            kb = next(int(l.split()[1]) for l in open("/proc/meminfo") if l.startswith("MemTotal:"))
            return kb / 1024 ** 2
        if sys.platform == "darwin":
            return int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout) / 1024 ** 3
        if WIN:
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("len", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                            ("avail", ctypes.c_ulonglong), ("pf", ctypes.c_ulonglong), ("apf", ctypes.c_ulonglong),
                            ("v", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ext", ctypes.c_ulonglong)]
            m = MS(); m.len = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.total / 1024 ** 3
    except (OSError, ValueError, StopIteration, AttributeError):
        pass
    return 0.0


def pick_models(spec: list[str]) -> list[str]:
    if "none" in spec:
        return []
    if "all" in spec:
        return list(MODELS)
    if spec and spec != ["auto"]:
        bad = [m for m in spec if m not in MODELS]
        if bad:
            raise RuntimeError(f"unknown model(s) {', '.join(bad)}. Available: {', '.join(MODELS)}")
        return spec
    ram = total_ram_gb()
    chosen = [m for m, (_, _, _, need) in MODELS.items() if need <= ram + 0.5] or ["gemma3-1b"]
    say(f"{ram:.0f} GB of RAM: models that fit -> {', '.join(chosen)} (others: --models all or llm download <name>)")
    return chosen


def hf_request(url: str, extra: dict | None = None) -> urllib.request.Request:
    headers = {"User-Agent": "aminos-suite", **(extra or {})}
    tok = load_env().get("HF_TOKEN")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    return urllib.request.Request(url, headers=headers)


def download_model(name: str) -> Path:
    repo, wanted, approx, need = MODELS[name]
    with urllib.request.urlopen(hf_request(f"https://huggingface.co/api/models/{repo}/tree/main"), timeout=60) as r:
        files = [f for f in json.load(r) if f.get("type") == "file" and f["path"].endswith(".gguf")]
    entry = next((f for f in files if f["path"] == wanted), None) or \
        next((f for f in files if "q4_k_m" in f["path"].lower()), None)
    if not entry or not entry.get("lfs"):
        raise RuntimeError(f"{name}: no Q4_K_M file in {repo}")
    size, sha = entry["lfs"]["size"], entry["lfs"]["oid"]
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    dest = MODELS_DIR / f"{name}.gguf"
    if dest.exists() and dest.stat().st_size == size:
        say(f"{name}: already downloaded")
        return dest
    part = dest.with_suffix(".part")
    have = part.stat().st_size if part.exists() else 0
    free = shutil.disk_usage(MODELS_DIR).free
    if free < size - have + 1024 ** 3:
        raise RuntimeError(f"{name}: needs {size / 1024 ** 3:.1f} GB, only {free / 1024 ** 3:.1f} GB free")
    if need > total_ram_gb() + 0.5:
        say(f"{name}: needs about {need} GB of RAM, this machine has {total_ram_gb():.0f} GB (it will be very slow)")
    say(f"{name}: downloading {entry['path']} ({size / 1024 ** 3:.1f} GB) from {repo}")
    url = f"https://huggingface.co/{repo}/resolve/main/{entry['path']}"
    with urllib.request.urlopen(hf_request(url, {"Range": f"bytes={have}-"} if have else None), timeout=120) as r:
        mode = "ab" if have and r.status == 206 else "wb"
        done = have if mode == "ab" else 0
        with open(part, mode) as f:
            last = -1
            while chunk := r.read(8 << 20):
                f.write(chunk)
                done += len(chunk)
                pct = done * 100 // size
                if pct // 5 != last:
                    last = pct // 5
                    print(f"  {name}: {pct}%", flush=True)
    h = hashlib.sha256()
    with open(part, "rb") as f:
        while chunk := f.read(16 << 20):
            h.update(chunk)
    if h.hexdigest() != sha:
        part.unlink()
        raise RuntimeError(f"{name}: SHA-256 mismatch, file deleted (run the download again)")
    part.replace(dest)
    say(f"{name}: ok, SHA-256 verified -> {dest}")
    return dest


def llm_smoke_test(model: Path) -> None:
    out = subprocess.run([str(llama_bin("llama-completion")), "-m", str(model), "-p", "The capital of France is", "-n", "8",
                          "-no-cnv", "--temp", "0", "-t", str(min(os.cpu_count() or 2, 8))],
                         capture_output=True, text=True, timeout=900)
    if out.returncode:
        raise RuntimeError(f"llama-completion failed on {model.name}: {out.stderr[-500:]}")
    say(f"test generation with {model.stem}: {out.stdout.strip()[-120:]!r}")


SETUP = {"aminos": setup_aminos, "eka": setup_eka, "jeu": setup_jeu, "atelier": setup_atelier,
         "agents": setup_agents, "llama": setup_llama}


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
    if "llama" in names and results.get("llama") == "ok":
        try:
            for m in pick_models(a.models):
                path = download_model(m)
                results[f"model {m}"] = "ok"
                if not a.no_tests and m == "gemma3-1b":
                    llm_smoke_test(path)
        except (RuntimeError, OSError, urllib.error.URLError, subprocess.SubprocessError) as e:
            results["models"] = f"FAILED: {e}"
            say(str(e))
    write_launchers()
    saved = json.loads((HOME / "suite.json").read_text()) if (HOME / "suite.json").exists() else {}
    state = {"suite_ref": a.suite_ref or saved.get("suite_ref", "main"), "installed": {**saved.get("installed", {}), **results}}
    (HOME / "suite.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    print("\n================ Aminos suite ================")
    for n, r in results.items():
        print(f"  {n:8} {r}")
    print(f"\n  folder : {HOME}\n  keys   : {ENV_FILE}\n  models : {MODELS_DIR}")
    print("  next   : aminos-suite list   |   aminos-suite start aminos   |   aminos-suite llm chat gemma3-1b")
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
    extra += ["--models=none"]  # update never downloads new models; use `aminos-suite llm download`
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
        say("projects you can start: aminos, saas, erp, eka, eka-api, jeu, atelier (models: aminos-suite llm ...)")
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
    print(f"\n  models ({MODELS_DIR}), RAM {total_ram_gb():.0f} GB:")
    for m, (repo, _, gb, need) in MODELS.items():
        state = "downloaded" if (MODELS_DIR / f"{m}.gguf").exists() else "-"
        print(f"  {m:18} {state:10} ~{gb:>5} GB disk  ~{need:>2} GB RAM  {repo}")
    return 0


# ------------------------------------------------------------------------ llm --
def cmd_llm(a) -> int:
    try:
        if a.action == "list":
            return cmd_list(a)
        if not a.model or a.model not in MODELS:
            say(f"choose a model: {', '.join(MODELS)}")
            return 2
        if a.action == "download":
            download_model(a.model)
            return 0
        path = MODELS_DIR / f"{a.model}.gguf"
        if not llama_bin("llama-cli").exists():
            say("llama.cpp is not built: aminos-suite install --only llama --models none")
            return 1
        if not path.exists():
            say(f"{a.model} is not downloaded: aminos-suite llm download {a.model}")
            return 1
        threads = ["-t", str(min(os.cpu_count() or 2, 8))]
        if a.action == "chat":
            argv = [llama_bin("llama-cli"), "-m", path, *threads, *a.extra]
        else:
            say(f"{a.model}: OpenAI-compatible API on http://127.0.0.1:{a.port}/v1 (Aminos: --provider llamacpp)")
            argv = [llama_bin("llama-server"), "-m", path, "--host", "127.0.0.1", "--port", str(a.port),
                    "-c", "8192", *threads, *a.extra]
        return subprocess.run([str(x) for x in argv]).returncode
    except (RuntimeError, OSError, urllib.error.URLError) as e:
        say(str(e))
        return 1
    except KeyboardInterrupt:
        return 0


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
        p.add_argument("--models", type=csv, default=["auto"],
                       help="auto (what fits in RAM), all, none, or names: " + ", ".join(MODELS))
        p.set_defaults(fn=cmd_install if name == "install" else cmd_update)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    p = sub.add_parser("start")
    p.add_argument("project")
    p.add_argument("args", nargs=argparse.REMAINDER)
    p.set_defaults(fn=cmd_start)
    p = sub.add_parser("llm", help="local models with llama.cpp: list | download | chat | serve")
    p.add_argument("action", choices=["list", "download", "chat", "serve"])
    p.add_argument("model", nargs="?")
    p.add_argument("extra", nargs=argparse.REMAINDER, help="extra llama.cpp options")
    p.add_argument("--port", type=int, default=LLM_PORT)
    p.set_defaults(fn=cmd_llm)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
