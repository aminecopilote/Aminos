# Started by the "Aminos-N8n" scheduled task: n8n automation, bound to 127.0.0.1:5678. Logs: <install dir>\logs\n8n.log
param([string]$Dir = (Split-Path -Parent $MyInvocation.MyCommand.Path), [int]$Port = 5678)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path "$Dir\logs", "$Dir\data\n8n" | Out-Null
$log = "$Dir\logs\n8n.log"
function Log($m) { Add-Content -Path $log -Value ("[{0}] {1}" -f (Get-Date -Format s), $m) }
Log "run-n8n.ps1 started (user $env:USERNAME)"
try {
    $cfg = Get-Content "$Dir\n8n.env.json" -Raw | ConvertFrom-Json
    foreach ($p in $cfg.PSObject.Properties) { Set-Item -Path "Env:$($p.Name)" -Value ([string]$p.Value) }
    $env:N8N_PORT = "$Port"
    $env:PATH = "$Dir\node24;$env:PATH"
    Set-Location "$Dir\data\n8n"
    $ErrorActionPreference = "Continue"
    & "$Dir\node24\node.exe" "$Dir\n8n\node_modules\n8n\bin\n8n" start 2>&1 | ForEach-Object { Add-Content -Path $log -Value "$_" }
    Log "n8n exited with code $LASTEXITCODE"
} catch {
    Log "ERROR: $_"
    exit 1
}
