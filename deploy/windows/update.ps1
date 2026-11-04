# Update an existing install: keeps data, passwords, Caddyfile and the options chosen at install time.
#   Offline bundle:   .\update.ps1 [-Dir C:\Aminos] [-NoService]      (run from the NEW unzipped bundle)
#   Online install:   C:\Aminos\update.ps1 [-Ref <commit or branch>]   (downloads that ref again; a branch name follows its newest commit)
param([string]$Dir = "C:\Aminos", [switch]$NoService, [string]$Ref = "")
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path "$here\wheelhouse") {
    if ($NoService) { & "$here\install.ps1" -Update -Dir $Dir -NoService } else { & "$here\install.ps1" -Update -Dir $Dir }
} else {
    $state = Get-Content "$Dir\install.json" -Raw | ConvertFrom-Json
    if (-not $state.Online) { throw "This install came from an offline bundle: run update.ps1 from the new unzipped bundle." }
    $useRef = if ($Ref) { $Ref } else { $state.Ref }
    if ($NoService) { & "$here\bootstrap.ps1" -Update -Dir $Dir -Repo $state.Repo -Ref $useRef -NoService }
    else { & "$here\bootstrap.ps1" -Update -Dir $Dir -Repo $state.Repo -Ref $useRef }
}
exit $LASTEXITCODE
