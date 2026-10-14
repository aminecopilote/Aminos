# Started by the "Aminos" scheduled task (or by hand). Logs: <install dir>\logs\app.log
param([string]$Dir = (Split-Path -Parent $MyInvocation.MyCommand.Path), [int]$Port = 8501)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path "$Dir\logs", "$Dir\data" | Out-Null
$log = "$Dir\logs\app.log"
function Log($m) { Add-Content -Path $log -Value ("[{0}] {1}" -f (Get-Date -Format s), $m) }
Log "run-app.ps1 started (PowerShell $($PSVersionTable.PSVersion), user $env:USERNAME)"
try {
    Set-Location "$Dir\data"      # the app's default translation memory "tm.sqlite" lands here
    $streamlit = "$Dir\venv\Scripts\streamlit.exe"
    if (-not (Test-Path $streamlit)) { throw "missing $streamlit" }
    Log "launching $streamlit on 127.0.0.1:$Port"
    & $streamlit run "$Dir\app\app.py" --server.address=127.0.0.1 --server.port=$Port `
        --server.headless=true --browser.gatherUsageStats=false --server.maxUploadSize=50 2>&1 |
        ForEach-Object { Add-Content -Path $log -Value "$_" }
    Log "streamlit exited with code $LASTEXITCODE"
} catch {
    Log "ERROR: $_"
    exit 1
}
