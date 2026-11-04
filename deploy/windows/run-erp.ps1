# Started by the "Aminos-ERP" scheduled task (or by hand): the firm's back-office (clients, cases, quotes, invoices).
# Same accounts and data folder as the translation app. Logs: <install dir>\logs\erp.log
param([string]$Dir = (Split-Path -Parent $MyInvocation.MyCommand.Path), [int]$Port = 8502)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path "$Dir\logs", "$Dir\data" | Out-Null
$log = "$Dir\logs\erp.log"
function Log($m) { Add-Content -Path $log -Value ("[{0}] {1}" -f (Get-Date -Format s), $m) }
Log "run-erp.ps1 started (PowerShell $($PSVersionTable.PSVersion), user $env:USERNAME)"
try {
    if (Test-Path "$Dir\saas.env") {
        foreach ($line in Get-Content "$Dir\saas.env") { $k, $v = $line -split "=", 2; if ($k) { Set-Item -Path "Env:$k" -Value $v } }
    }
    $py = "$Dir\venv\Scripts\python.exe"
    if (-not (Test-Path $py)) { throw "missing $py" }
    Set-Location "$Dir\data"
    $ErrorActionPreference = "Continue"
    & $py -m aminos.erp --data "$env:AMINOS_DATA_DIR" --host 127.0.0.1 --port $Port 2>&1 | ForEach-Object { Add-Content -Path $log -Value "$_" }
    Log "erp exited with code $LASTEXITCODE"
} catch {
    Log "ERROR: $_"
    exit 1
}
