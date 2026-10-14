# Update an existing install from a newer bundle: keeps data, passwords, Caddyfile and the options chosen at install time.
#   .\update.ps1 [-Dir C:\Aminos] [-NoService]
param([string]$Dir = "C:\Aminos", [switch]$NoService)
$bundle = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($NoService) { & "$bundle\install.ps1" -Update -Dir $Dir -NoService } else { & "$bundle\install.ps1" -Update -Dir $Dir }
exit $LASTEXITCODE
