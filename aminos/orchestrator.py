"""Orchestrateur Central: supervision loop for a Windows machine (collect -> analyse -> decide -> act -> log).

Each cycle produces one strict-JSON record (see `run_cycle`) appended to <logdir>/orch-<date>.jsonl.
Analysis is deterministic (fixed thresholds), so a cycle is reproducible and testable. Actions are only *proposed*:
a command runs when `execute=True` AND it matches ALLOWED_ACTIONS exactly; anything else is logged as refused.
Every collector is read-only and a failing collector yields {"error": ...} instead of stopping the cycle.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

# alert thresholds from the specification
THRESHOLDS = {"cpu_pct": 90.0, "mem_free_mb": 500.0, "docker_restarts": 3, "log_window_s": 300, "log_max_level": 2}

# the only commands that may ever be executed, even with execute=True
ALLOWED_ACTIONS = [
    re.compile(r"^Restart-Service -Name '(wuauserv|Spooler|Aminos|Aminos-Caddy)'$"),
    re.compile(r"^docker restart [A-Za-z0-9][A-Za-z0-9_.-]{0,100}$"),
]

# Runner(tool, command) -> (returncode, stdout). tool is one of RUNNABLE.
Runner = Callable[[str, str], "tuple[int, str]"]
RUNNABLE = {"powershell", "docker", "kubectl", "nvidia-smi", "git", "python"}


def default_logdir() -> Path:
    return Path(r"C:\orchestrator\logs") if os.name == "nt" else Path("orchestrator-logs")


def subprocess_runner(timeout: int = 30, cwd: str | None = None) -> Runner:
    def run(tool: str, command: str) -> tuple[int, str]:
        if tool not in RUNNABLE:
            return 126, f"tool not allowed: {tool}"
        argv = {"powershell": ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                "python": [sys.executable, "-c", command]}.get(tool) or [tool, *shlex.split(command)]
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=cwd)
            return p.returncode, p.stdout
        except FileNotFoundError:
            return 127, f"{tool}: not installed"
        except subprocess.TimeoutExpired:
            return 124, f"{tool}: timeout after {timeout}s"
    return run


def _json(rc: int, out: str):
    if rc != 0:
        return {"error": out.strip()[:200] or f"exit code {rc}"}
    out = out.strip()
    if not out:
        return []
    try:
        data = json.loads(out)
    except ValueError:
        return {"error": "output is not JSON: " + out[:100]}
    return data if isinstance(data, list) else [data]


def collect(run: Runner, repo: str = ".") -> dict:
    """Read-only observations. Commands follow the specification; JSON output is requested where the original used tables."""
    ps = lambda cmd: _json(*run("powershell", cmd))
    obs: dict = {}
    obs["cpu_top"] = ps("Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 Id,ProcessName,CPU,WS | ConvertTo-Json")
    obs["mem"] = ps("Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory,"
                    "TotalVirtualMemorySize,FreeVirtualMemory | ConvertTo-Json")
    # the specification's '\Paging File\% Usage' is not a valid counter path: the instance is required
    obs["counters"] = ps("(Get-Counter '\\Memory\\Available MBytes','\\Processor(_Total)\\% Processor Time',"
                         "'\\Paging File(_Total)\\% Usage').CounterSamples | "
                         "Select-Object Path,CookedValue | ConvertTo-Json")
    rc, out = run("nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits")
    obs["gpu"] = [dict(zip(("util_pct", "mem_used_mb", "mem_total_mb"), (v.strip() for v in line.split(","))))
                  for line in out.splitlines() if line.strip()] if rc == 0 else []
    obs["docker"] = _docker(run)
    rc, out = run("kubectl", "get pods -A -o json")
    obs["k8s"] = ([{"namespace": i["metadata"]["namespace"], "name": i["metadata"]["name"], "phase": i["status"].get("phase")}
                   for i in json.loads(out).get("items", [])] if rc == 0 and out.strip() else [])
    obs["logs_critical"] = ps("Get-WinEvent -LogName System -MaxEvents 20 | Where-Object {$_.Level -le 3} | "
                              "Select-Object @{n='TimeCreated';e={$_.TimeCreated.ToUniversalTime().ToString('o')}},Id,Level,Message | ConvertTo-Json")
    obs["net_listen"] = ps("Get-NetTCPConnection -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess | "
                           "Sort-Object LocalPort | ConvertTo-Json")
    rc, out = run("git", "status --short --branch")
    obs["git_status"] = out.strip() if rc == 0 else f"unavailable: {out.strip()[:100]}"
    rc, out = run("python", "import sys;print(sys.version.split()[0])")
    obs["py_check"] = out.strip() if rc == 0 else f"unavailable: {out.strip()[:100]}"
    return obs


def _docker(run: Runner) -> list | dict:
    rc, out = run("docker", 'ps -a --format "{{json .}}"')
    if rc != 0:
        return [] if rc == 127 else {"error": out.strip()[:200]}
    rows = []
    for line in out.splitlines():
        if not line.strip():
            continue
        c = json.loads(line)
        rc2, restarts = run("docker", f"inspect --format {{{{.RestartCount}}}}|{{{{.State.ExitCode}}}} {c['Names']}")
        count, _, exit_code = restarts.strip().partition("|") if rc2 == 0 else ("0", "", "")
        rows.append({"name": c["Names"], "status": c.get("Status", ""), "ports": c.get("Ports", ""),
                     "restart_count": int(count or 0), "exit_code": int(exit_code) if exit_code.lstrip("-").isdigit() else None})
    return rows


def analyse(obs: dict, now: datetime | None = None) -> tuple[str, list[str], str, list[dict]]:
    """-> (analysis text, alerts, decision, proposed actions)."""
    now = now or datetime.now(timezone.utc)
    t, alerts, actions = THRESHOLDS, [], []
    samples = {s.get("Path", ""): s.get("CookedValue") for s in obs.get("counters", []) if isinstance(s, dict) and "Path" in s}
    cpu = next((v for k, v in samples.items() if "processor time" in k.lower()), None)
    free_mb = next((v for k, v in samples.items() if "available mbytes" in k.lower()), None)
    if free_mb is None and obs.get("mem") and isinstance(obs["mem"], list) and "FreePhysicalMemory" in obs["mem"][0]:
        free_mb = obs["mem"][0]["FreePhysicalMemory"] / 1024  # reported in KB
    if cpu is None and free_mb is None and ("counters" in obs or "mem" in obs):
        alerts.append("mesures CPU et mémoire indisponibles : la collecte a échoué, l'état de la machine est inconnu")
    if cpu is not None and cpu > t["cpu_pct"]:
        alerts.append(f"CPU {cpu:.0f}% > {t['cpu_pct']:.0f}%")
    if free_mb is not None and free_mb < t["mem_free_mb"]:
        alerts.append(f"mémoire libre {free_mb:.0f} Mo < {t['mem_free_mb']:.0f} Mo")
    for c in obs.get("docker", []) if isinstance(obs.get("docker"), list) else []:
        if c["restart_count"] > t["docker_restarts"]:
            alerts.append(f"conteneur {c['name']} : {c['restart_count']} redémarrages > {t['docker_restarts']}")
        if c["exit_code"] == 137 and not c["status"].startswith("Up"):
            actions.append({"tool": "docker", "command": f"docker restart {c['name']}", "reason": "Exit code 137"})
    recent = 0
    for e in obs.get("logs_critical", []) if isinstance(obs.get("logs_critical"), list) else []:
        try:
            age = (now - datetime.fromisoformat(e["TimeCreated"].replace("Z", "+00:00"))).total_seconds()
        except (KeyError, ValueError):
            continue
        if 0 <= age <= t["log_window_s"] and e.get("Level", 9) <= t["log_max_level"]:
            recent += 1
    if recent:
        alerts.append(f"{recent} événement(s) système de niveau Erreur ou plus en {t['log_window_s'] // 60} min")
    if not alerts and not actions:
        return "Aucune anomalie : charge, mémoire, conteneurs et journaux dans les seuils.", [], "Aucune action", []
    decision = "Alerter utilisateur"
    if actions:
        decision = "Redémarrer service " + ", ".join(a["command"].split()[-1] for a in actions)
    elif cpu is not None and cpu > t["cpu_pct"]:
        decision = "Lancer diagnostic approfondi"
    return "Anomalies : " + " ; ".join(alerts or [a["reason"] for a in actions]), alerts, decision, actions


def execute_action(run: Runner, action: dict, execute: bool) -> dict:
    result = dict(action)
    allowed = any(p.match(action["command"]) for p in ALLOWED_ACTIONS)
    if not allowed:
        result["executed"], result["status"] = False, "refused: not in the allow-list"
    elif not execute:
        result["executed"], result["status"] = False, "dry-run (use --execute to run allow-listed actions)"
    else:
        tool = "powershell" if action["tool"] == "powershell" else action["tool"]
        rc, out = run(tool, action["command"])
        result["executed"], result["status"] = True, "ok" if rc == 0 else f"failed (exit {rc}): {out.strip()[:120]}"
    return result


def next_cycle_id(logdir: Path, day: str) -> str:
    f = logdir / f"orch-{day}.jsonl"
    n = sum(1 for _ in f.open(encoding="utf-8")) if f.exists() else 0
    return f"orch-{n + 1:03d}"


def run_cycle(run: Runner, logdir: Path | None = None, interval: int = 300, execute: bool = False,
              repo: str = ".", now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    logdir = Path(logdir or default_logdir())
    logdir.mkdir(parents=True, exist_ok=True)
    day = now.strftime("%Y-%m-%d")
    obs = collect(run, repo)
    analysis, alerts, decision, proposed = analyse(obs, now)
    record = {"timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "cycle_id": next_cycle_id(logdir, day), "observations": obs,
              "analysis": analysis, "alerts": alerts, "decision": decision,
              "actions": [execute_action(run, a, execute) for a in proposed],
              "next_check_seconds": min(interval, 60) if alerts else interval}
    with open(logdir / f"orch-{day}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def loop(run: Runner, logdir: Path | None, interval: int, execute: bool, max_cycles: int | None = None,
         sleep: Callable[[float], None] = time.sleep, emit: Callable[[str], None] = print) -> int:
    n = 0
    while max_cycles is None or n < max_cycles:
        rec = run_cycle(run, logdir, interval, execute)
        n += 1
        emit(json.dumps({k: rec[k] for k in ("timestamp", "cycle_id", "analysis", "decision", "alerts", "next_check_seconds")},
                        ensure_ascii=False))
        if max_cycles is None or n < max_cycles:
            sleep(rec["next_check_seconds"])
    return n
