# Started by the "Aminos-Orchestrator" task. One supervision cycle every 5 minutes; logs in C:\orchestrator\logs\orch-<date>.jsonl
param([string]$Dir = (Split-Path -Parent $MyInvocation.MyCommand.Path), [int]$Interval = 300)
$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path "$Dir\logs", "C:\orchestrator\logs" | Out-Null
Set-Location $Dir
# actions stay proposals (no --execute): the machine owner decides when to allow the allow-listed restarts
& "$Dir\venv\Scripts\aminos.exe" orchestrate --interval $Interval --logdir "C:\orchestrator\logs" --repo $Dir 2>&1 |
    ForEach-Object { Add-Content -Path "$Dir\logs\orchestrator.log" -Value "$_" }
