# Removes tasks, firewall rules and the program files. Data (translation memory) is kept in <dir>\data unless -DeleteData.
param([string]$Dir = (Split-Path -Parent $MyInvocation.MyCommand.Path), [switch]$DeleteData)
foreach ($t in "Aminos", "Aminos-Caddy") {
    Stop-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $t -Confirm:$false -ErrorAction SilentlyContinue
}
Get-Process caddy, streamlit, python, powershell -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$Dir*" -and $_.Id -ne $PID } | Stop-Process -Force
Get-NetFirewallRule -DisplayName "Aminos HTTP/S *" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
foreach ($d in "venv", "app", "caddy", "logs") { Remove-Item "$Dir\$d" -Recurse -Force -ErrorAction SilentlyContinue }
Remove-Item "$Dir\FIRST_PASSWORD.txt" -Force -ErrorAction SilentlyContinue
if ($DeleteData) { Remove-Item "$Dir\data" -Recurse -Force -ErrorAction SilentlyContinue }
Write-Host "Aminos removed. Data kept in $Dir\data" -ForegroundColor Green
