# Removes tasks, firewall rules and the program files. Data (translation memory) is kept in <dir>\data unless -DeleteData.
param([string]$Dir = (Split-Path -Parent $MyInvocation.MyCommand.Path), [switch]$DeleteData)
foreach ($t in "Aminos", "Aminos-Caddy", "Aminos-Orchestrator", "Aminos-AgentHQ") {
    Stop-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $t -Confirm:$false -ErrorAction SilentlyContinue
}
Get-Process caddy, streamlit, python, node, powershell -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$Dir*" -and $_.Id -ne $PID } | Stop-Process -Force
Get-NetFirewallRule -DisplayName "Aminos HTTP/S *" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
foreach ($d in "venv", "app", "caddy", "logs", "skills") { Remove-Item "$Dir\$d" -Recurse -Force -ErrorAction SilentlyContinue }
Remove-Item "$Dir\agency\agent-hq", "$Dir\agency\agent-coordinator" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$Dir\FIRST_PASSWORD.txt", "$Dir\saas.env", "$Dir\Lancer-Aminos.bat", "$Dir\install.json" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\Public\Desktop\Aminos.lnk", "$([Environment]::GetFolderPath('Desktop'))\Aminos.lnk" -Force -ErrorAction SilentlyContinue
if ($DeleteData) { Remove-Item "$Dir\data" -Recurse -Force -ErrorAction SilentlyContinue }
Write-Host "Aminos removed. Data kept in $Dir\data" -ForegroundColor Green
