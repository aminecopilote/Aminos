<#
.SYNOPSIS  Installs Aminos on Windows (10/11, Server 2019+), no Docker. Run from the unzipped bundle, as Administrator
           (-NoService: no admin needed, but nothing starts at boot and no firewall rule is created).
.EXAMPLE   .\install.ps1                                  # local only: http://127.0.0.1:8501 (use RDP or an SSH tunnel)
.EXAMPLE   .\install.ps1 -Domain aminos.example.com       # public HTTPS + password through Caddy (DNS A record -> this server)
.EXAMPLE   .\install.ps1 -Domain http://localhost:8080    # Caddy over plain HTTP, for tests
#>
param(
    [string]$Dir = "C:\Aminos",
    [int]$Port = 8501,
    [string]$Domain = "",
    [string]$CaddyVersion = "2.8.4",
    [switch]$NoService
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Bundle = Split-Path -Parent $MyInvocation.MyCommand.Path

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole("Administrator")
if (-not $admin -and -not $NoService) { throw "Run PowerShell as Administrator (or add -NoService for a per-user install without boot task or firewall rule)." }
if (-not (Test-Path "$Bundle\wheelhouse")) { throw "wheelhouse\ not found: run this script from the unzipped bundle." }

# --- integrity of the offline wheelhouse -----------------------------------------------------------------------
Write-Host "==> Checking wheel checksums"
foreach ($line in Get-Content "$Bundle\SHA256SUMS.txt") {
    $hash, $name = $line -split "\s+\*?", 2
    $actual = (Get-FileHash -Algorithm SHA256 "$Bundle\wheelhouse\$name").Hash.ToLower()
    if ($actual -ne $hash.ToLower()) { throw "Checksum mismatch: $name" }
}

# --- Python 3.12 (the wheels are built for cp312) --------------------------------------------------------------
function Find-Python {
    foreach ($c in @(@("py", "-3.12"), @("python"))) {
        try {
            $exe = $c[0]; $extra = @($c | Select-Object -Skip 1)
            $v = & $exe @extra -c "import sys;print('%d.%d' % sys.version_info[:2])" 2>$null
            if ($LASTEXITCODE -eq 0 -and $v -eq "3.12") { return ,$c }
        } catch { }
    }
    return $null
}
$py = Find-Python
if (-not $py) {
    Write-Host "==> Installing Python 3.12 (python.org)"
    $installer = Join-Path $env:TEMP "python-3.12.10-amd64.exe"
    Invoke-WebRequest "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe" -OutFile $installer
    Start-Process $installer -ArgumentList "/quiet InstallAllUsers=$(if ($admin) { 1 } else { 0 }) PrependPath=1 Include_test=0" -Wait
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    $py = Find-Python
    if (-not $py) { throw "Python 3.12 installation failed." }
}

# --- application -----------------------------------------------------------------------------------------------
Write-Host "==> Installing Aminos into $Dir"
New-Item -ItemType Directory -Force -Path $Dir, "$Dir\app", "$Dir\data", "$Dir\logs" | Out-Null
$exe = $py[0]; $extra = @($py | Select-Object -Skip 1)
& $exe @extra -m venv "$Dir\venv"
if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
$pip = "$Dir\venv\Scripts\python.exe"
& $pip -m pip install --quiet --no-index --find-links "$Bundle\wheelhouse" -r "$Bundle\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "dependency installation failed" }
$whl = Get-ChildItem "$Bundle\wheelhouse\*" -Include "aminos-*.whl", "agent_coordinator-*.whl" | ForEach-Object { $_.FullName }
& $pip -m pip install --quiet --no-index --no-deps $whl
if ($LASTEXITCODE -ne 0) { throw "Aminos installation failed" }
Copy-Item "$Bundle\app.py" "$Dir\app\app.py" -Force
Copy-Item "$Bundle\run-app.ps1" "$Dir\run-app.ps1" -Force
Copy-Item "$Bundle\uninstall.ps1" "$Dir\uninstall.ps1" -Force

# --- optional public access: Caddy (HTTPS + password) ----------------------------------------------------------
$password = $null
if ($Domain) {
    Write-Host "==> Caddy $CaddyVersion"
    New-Item -ItemType Directory -Force -Path "$Dir\caddy" | Out-Null
    $zipName = "caddy_${CaddyVersion}_windows_amd64.zip"
    $base = "https://github.com/caddyserver/caddy/releases/download/v$CaddyVersion"
    Invoke-WebRequest "$base/$zipName" -OutFile "$Dir\caddy\$zipName"
    Invoke-WebRequest "$base/caddy_${CaddyVersion}_checksums.txt" -OutFile "$Dir\caddy\checksums.txt"
    $expected = ((Get-Content "$Dir\caddy\checksums.txt") | Where-Object { $_ -match [regex]::Escape($zipName) } | Select-Object -First 1) -split "\s+" | Select-Object -First 1
    $alg = switch ($expected.Length) { 64 { "SHA256" } 128 { "SHA512" } default { throw "Unrecognised checksum format in Caddy release" } }
    if ((Get-FileHash -Algorithm $alg "$Dir\caddy\$zipName").Hash.ToLower() -ne $expected.ToLower()) { throw "Caddy download checksum mismatch" }
    Expand-Archive "$Dir\caddy\$zipName" -DestinationPath "$Dir\caddy" -Force
    $password = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 20 | ForEach-Object { [char]$_ })
    $hash = (& "$Dir\caddy\caddy.exe" hash-password --plaintext $password).Trim()
    @"
$Domain {
	basic_auth {
		aminos $hash
	}
	reverse_proxy 127.0.0.1:$Port
}
"@ | Set-Content -Encoding ASCII "$Dir\caddy\Caddyfile"
    Set-Content -Encoding ASCII "$Dir\FIRST_PASSWORD.txt" $password
    icacls "$Dir\FIRST_PASSWORD.txt" /inheritance:r /grant:r "Administrators:F" "SYSTEM:F" "${env:USERDOMAIN}\${env:USERNAME}:F" | Out-Null
    if ($admin -and $Domain -notmatch "^http://") {
        foreach ($p in 80, 443) { New-NetFirewallRule -DisplayName "Aminos HTTP/S $p" -Direction Inbound -Protocol TCP -LocalPort $p -Action Allow -ErrorAction SilentlyContinue | Out-Null }
    }
}

# --- run at boot, restart on failure ---------------------------------------------------------------------------
function Register-AminosTask($name, $exe, $argLine) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    $action = New-ScheduledTaskAction -Execute $exe -Argument $argLine -WorkingDirectory $Dir
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $settings = New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable
    Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -User "SYSTEM" -RunLevel Highest | Out-Null
    Start-ScheduledTask -TaskName $name
}
$appArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$Dir\run-app.ps1`" -Dir `"$Dir`" -Port $Port"
if ($NoService) {
    Start-Process powershell.exe -ArgumentList $appArgs -WindowStyle Hidden
    if ($Domain) { Start-Process "$Dir\caddy\caddy.exe" -ArgumentList "run --config `"$Dir\caddy\Caddyfile`" --adapter caddyfile" -WindowStyle Hidden }
} else {
    Register-AminosTask "Aminos" "powershell.exe" $appArgs
    if ($Domain) { Register-AminosTask "Aminos-Caddy" "$Dir\caddy\caddy.exe" "run --config `"$Dir\caddy\Caddyfile`" --adapter caddyfile" }
}

Write-Host ""
Write-Host "Aminos is starting (first start takes ~20 s)."
if ($Domain) {
    Write-Host "URL:   $(if ($Domain -match '^http') { $Domain } else { "https://$Domain" })"
    Write-Host "User:  aminos"
    Write-Host "Pass:  $password   <- save it, then delete $Dir\FIRST_PASSWORD.txt"
} else {
    Write-Host "URL:   http://127.0.0.1:$Port  (local only: open it from this server, or tunnel: ssh -L ${Port}:127.0.0.1:${Port} user@server)"
}
Write-Host "Logs:  $Dir\logs      Remove: $Dir\uninstall.ps1"
Write-Host "OCR:   scanned PDFs/images need the Claude vision OCR (API key) or Tesseract (https://github.com/UB-Mannheim/tesseract/wiki) with ara/fra/nld data."
Write-Host "Local model: install Ollama for Windows (https://ollama.com/download); the app reaches it at 127.0.0.1:11434."
