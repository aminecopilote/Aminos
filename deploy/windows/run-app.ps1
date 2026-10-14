# Started by the "Aminos" scheduled task (or by hand). Logs: <install dir>\logs\app.log
param([string]$Dir = (Split-Path -Parent $MyInvocation.MyCommand.Path), [int]$Port = 8501)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path "$Dir\logs", "$Dir\data" | Out-Null
Set-Location "$Dir\data"      # the app's default translation memory "tm.sqlite" lands here
& "$Dir\venv\Scripts\streamlit.exe" run "$Dir\app\app.py" --server.address=127.0.0.1 --server.port=$Port `
    --server.headless=true --browser.gatherUsageStats=false --server.maxUploadSize=50 *>> "$Dir\logs\app.log"
