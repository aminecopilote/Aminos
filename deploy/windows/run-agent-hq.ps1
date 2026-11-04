# Started by the "Aminos-AgentHQ" task. agent-hq bound to 127.0.0.1:7700 only (it has no authentication).
param([string]$Dir = (Split-Path -Parent $MyInvocation.MyCommand.Path))
$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path "$Dir\logs", "$Dir\agency\data" | Out-Null
$env:HQ_DB_PATH = "$Dir\agency\data\agenthq.db"
$env:PORT = "7700"
Set-Location "$Dir\agency"
& node "$Dir\agency\start-agent-hq.mjs" "$Dir\agency\agent-hq" 2>&1 | ForEach-Object { Add-Content -Path "$Dir\logs\agent-hq.log" -Value "$_" }
