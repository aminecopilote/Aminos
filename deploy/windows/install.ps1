<#
.SYNOPSIS  Installs or updates Aminos on Windows (10/11, Server 2019+), no Docker. Run from the unzipped bundle, as Administrator
           (-NoService: no admin needed, but nothing starts at boot and no firewall rule is created).
.EXAMPLE   .\install.ps1                                  # local only: http://127.0.0.1:8501 (use RDP or an SSH tunnel)
.EXAMPLE   .\install.ps1 -Saas -Domain aminos.example.com  # multi-user service: accounts + HTTPS
.EXAMPLE   .\install.ps1 -Saas -Orchestrator -Agency       # + machine supervision every 5 min + agent-hq / agent-coordinator copies
.EXAMPLE   .\install.ps1 -Skills chatgpt-skills:document-converter-suite   # + a third-party skill (text only, pinned commit)
.EXAMPLE   .\install.ps1 -Update                           # new bundle over an existing install: keeps data, passwords and options
#>
param(
    [string]$Dir = "C:\Aminos",
    [int]$Port = 8501,
    [string]$Domain = "",
    [string]$CaddyVersion = "2.8.4",
    [switch]$NoService,
    [switch]$Saas,          # multi-user mode: accounts, one data folder per firm, quotas, audit log
    [switch]$Orchestrator,  # supervision loop "Orchestrateur Central" (task Aminos-Orchestrator, logs in C:\orchestrator\logs)
    [switch]$Agency,        # local copies of agent-hq and agent-coordinator (chef d'agence); agent-hq needs Node 22
    [string[]]$Skills = @(),# third-party skills, "source:skill" (see: aminos skills available chatgpt-skills)
    [switch]$Update         # reuse the options recorded by the previous install
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Bundle = Split-Path -Parent $MyInvocation.MyCommand.Path
$StateFile = "$Dir\install.json"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole("Administrator")
if (-not $admin -and -not $NoService) { throw "Run PowerShell as Administrator (or add -NoService for a per-user install without boot task or firewall rule)." }
if (-not (Test-Path "$Bundle\wheelhouse")) { throw "wheelhouse\ not found: run this script from the unzipped bundle." }

# --- an update re-applies the options of the previous install --------------------------------------------------
if ($Update) {
    if (-not (Test-Path $StateFile)) { throw "No previous install found in $Dir (missing install.json): run install.ps1 without -Update." }
    $prev = Get-Content $StateFile -Raw | ConvertFrom-Json
    if (-not $PSBoundParameters.ContainsKey("Port")) { $Port = [int]$prev.Port }
    if (-not $PSBoundParameters.ContainsKey("Domain")) { $Domain = [string]$prev.Domain }
    if (-not $PSBoundParameters.ContainsKey("Saas")) { $Saas = [bool]$prev.Saas }
    if (-not $PSBoundParameters.ContainsKey("Orchestrator")) { $Orchestrator = [bool]$prev.Orchestrator }
    if (-not $PSBoundParameters.ContainsKey("Agency")) { $Agency = [bool]$prev.Agency }
    if (-not $PSBoundParameters.ContainsKey("NoService")) { $NoService = [bool]$prev.NoService }
}

# --- integrity of everything shipped in the bundle -------------------------------------------------------------
Write-Host "==> Checking bundle checksums"
foreach ($line in Get-Content "$Bundle\SHA256SUMS.txt") {
    $hash, $name = $line -split "\s+\*?", 2
    $actual = (Get-FileHash -Algorithm SHA256 "$Bundle\$name").Hash.ToLower()
    if ($actual -ne $hash.ToLower()) { throw "Checksum mismatch: $name" }
}

# --- stop what is running from $Dir (Windows cannot replace files that are in use) -----------------------------
function Stop-Aminos {
    foreach ($t in "Aminos", "Aminos-Caddy", "Aminos-Orchestrator", "Aminos-AgentHQ") {
        Stop-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
    }
    Get-Process caddy, streamlit, python, node, powershell -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -like "$Dir\*" -and $_.Id -ne $PID } | Stop-Process -Force
    Start-Sleep -Seconds 2
}
if (Test-Path "$Dir\venv") { Write-Host "==> Stopping the running services"; Stop-Aminos }

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
Write-Host "==> $(if ($Update) { 'Updating' } else { 'Installing' }) Aminos in $Dir"
New-Item -ItemType Directory -Force -Path $Dir, "$Dir\app", "$Dir\data", "$Dir\logs" | Out-Null
$exe = $py[0]; $extra = @($py | Select-Object -Skip 1)
if (-not (Test-Path "$Dir\venv\Scripts\python.exe")) {
    & $exe @extra -m venv "$Dir\venv"
    if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
}
$pip = "$Dir\venv\Scripts\python.exe"
& $pip -m pip install --quiet --no-index --find-links "$Bundle\wheelhouse" -r "$Bundle\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "dependency installation failed" }
$whl = Get-ChildItem "$Bundle\wheelhouse\*" -Include "aminos-*.whl", "agent_coordinator-*.whl" | ForEach-Object { $_.FullName }
& $pip -m pip install --quiet --no-index --no-deps --force-reinstall $whl   # same version number, new content: force
if ($LASTEXITCODE -ne 0) { throw "Aminos installation failed" }
Copy-Item "$Bundle\app.py", "$Bundle\saas_app.py" "$Dir\app\" -Force
Copy-Item "$Bundle\run-app.ps1", "$Bundle\run-orchestrator.ps1", "$Bundle\run-agent-hq.ps1", "$Bundle\Lancer-Aminos.bat",
          "$Bundle\uninstall.ps1", "$Bundle\update.ps1" "$Dir\" -Force
# our own skills (the third-party ones live next to them, managed by `aminos skills`)
New-Item -ItemType Directory -Force -Path "$Dir\skills\aminos" | Out-Null
Copy-Item "$Bundle\skills\*" "$Dir\skills\aminos\" -Recurse -Force

# --- secrets and optional public access: Caddy (HTTPS) ---------------------------------------------------------
$password = $null
function New-StrongPassword { -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 20 | ForEach-Object { [char]$_ }) }
function Protect-File($path) {
    icacls $path /inheritance:r /grant:r "Administrators:F" "SYSTEM:F" "${env:USERDOMAIN}\${env:USERNAME}:F" | Out-Null
}
if ($Saas -and -not (Test-Path "$Dir\saas.env")) {      # kept on update: the admin account already exists in the data
    $password = New-StrongPassword
    # saas.env also holds AMINOS_DATA_DIR: do NOT delete it (the application would look for its accounts elsewhere)
    @("AMINOS_ADMIN_USER=admin", "AMINOS_ADMIN_PASSWORD=$password", "AMINOS_DATA_DIR=$Dir\data\saas", "AMINOS_ALLOW_REMOTE_LLM=0") |
        Set-Content -Encoding ASCII "$Dir\saas.env"
    Protect-File "$Dir\saas.env"
    Set-Content -Encoding ASCII "$Dir\FIRST_PASSWORD.txt" $password
    Protect-File "$Dir\FIRST_PASSWORD.txt"
}
if ($Domain) {
    New-Item -ItemType Directory -Force -Path "$Dir\caddy" | Out-Null
    if (-not (Test-Path "$Dir\caddy\caddy.exe")) {
        Write-Host "==> Caddy $CaddyVersion"
        $zipName = "caddy_${CaddyVersion}_windows_amd64.zip"
        $base = "https://github.com/caddyserver/caddy/releases/download/v$CaddyVersion"
        Invoke-WebRequest "$base/$zipName" -OutFile "$Dir\caddy\$zipName"
        Invoke-WebRequest "$base/caddy_${CaddyVersion}_checksums.txt" -OutFile "$Dir\caddy\checksums.txt"
        $expected = ((Get-Content "$Dir\caddy\checksums.txt") | Where-Object { $_ -match [regex]::Escape($zipName) } | Select-Object -First 1) -split "\s+" | Select-Object -First 1
        $alg = switch ($expected.Length) { 64 { "SHA256" } 128 { "SHA512" } default { throw "Unrecognised checksum format in Caddy release" } }
        if ((Get-FileHash -Algorithm $alg "$Dir\caddy\$zipName").Hash.ToLower() -ne $expected.ToLower()) { throw "Caddy download checksum mismatch" }
        Expand-Archive "$Dir\caddy\$zipName" -DestinationPath "$Dir\caddy" -Force
    }
    if (-not (Test-Path "$Dir\caddy\Caddyfile")) {
        if ($Saas) {
            $auth = ""           # the application authenticates users itself; Caddy only provides HTTPS
        } else {
            $password = New-StrongPassword
            $hash = (& "$Dir\caddy\caddy.exe" hash-password --plaintext $password).Trim()
            $auth = "`tbasic_auth {`n`t`taminos $hash`n`t}`n"
            Set-Content -Encoding ASCII "$Dir\FIRST_PASSWORD.txt" $password
            Protect-File "$Dir\FIRST_PASSWORD.txt"
        }
        "$Domain {`n$auth`treverse_proxy 127.0.0.1:$Port`n}`n" | Set-Content -Encoding ASCII "$Dir\caddy\Caddyfile"
    }
    if ($admin -and $Domain -notmatch "^http://") {
        foreach ($p in 80, 443) { New-NetFirewallRule -DisplayName "Aminos HTTP/S $p" -Direction Inbound -Protocol TCP -LocalPort $p -Action Allow -ErrorAction SilentlyContinue | Out-Null }
    }
}

# --- optional: chef d'agence (local copies of agent-hq and agent-coordinator) ----------------------------------
$nodeOk = $false
if ($Agency) {
    Write-Host "==> Agency (agent-hq, agent-coordinator)"
    New-Item -ItemType Directory -Force -Path "$Dir\agency\data" | Out-Null
    Copy-Item "$Bundle\agency\*" "$Dir\agency\" -Recurse -Force -Exclude "data"
    try {
        $nv = (& node --version 2>$null)
        $nodeOk = ($LASTEXITCODE -eq 0 -and [int]($nv -replace '^v(\d+)\..*', '$1') -ge 22)
    } catch { }
    if (-not $nodeOk) { Write-Host "    agent-hq needs Node 22 or newer (winget install OpenJS.NodeJS.22), then re-run with -Update. Files are in place." }
}

# --- optional: third-party skills (pinned commits, text only, never executed) ----------------------------------
foreach ($spec in $Skills) {
    $src, $names = $spec -split ":", 2
    Write-Host "==> Skill $spec"
    $skillArgs = @("skills", "install", $src) + @($names -split "," | Where-Object { $_ }) + @("--dest", "$Dir\skills")
    & "$Dir\venv\Scripts\aminos.exe" @skillArgs
    if ($LASTEXITCODE -ne 0) { Write-Host "    not installed (git is required: winget install Git.Git)" }
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
function Start-Component($name, $exe, $argLine) {
    if ($NoService) { Start-Process $exe -ArgumentList $argLine -WindowStyle Hidden } else { Register-AminosTask $name $exe $argLine }
}
$ps = "powershell.exe"
$psArgs = { param($script, $more) "-NoProfile -ExecutionPolicy Bypass -File `"$Dir\$script`" -Dir `"$Dir`" $more" }
Start-Component "Aminos" $ps (& $psArgs "run-app.ps1" "-Port $Port$(if ($Saas) { ' -Saas' })")
if ($Domain) { Start-Component "Aminos-Caddy" "$Dir\caddy\caddy.exe" "run --config `"$Dir\caddy\Caddyfile`" --adapter caddyfile" }
if ($Orchestrator) {
    New-Item -ItemType Directory -Force -Path "C:\orchestrator\logs" | Out-Null
    Start-Component "Aminos-Orchestrator" $ps (& $psArgs "run-orchestrator.ps1" "")
}
if ($Agency -and $nodeOk) { Start-Component "Aminos-AgentHQ" $ps (& $psArgs "run-agent-hq.ps1" "") }

# --- remember the options for -Update --------------------------------------------------------------------------
[ordered]@{ Port = $Port; Domain = $Domain; Saas = [bool]$Saas; Orchestrator = [bool]$Orchestrator; Agency = [bool]$Agency
            NoService = [bool]$NoService; Skills = $Skills; Updated = (Get-Date -Format s) } |
    ConvertTo-Json | Set-Content -Encoding ASCII $StateFile

try {
    $desktop = if ($admin) { "C:\Users\Public\Desktop" } else { [Environment]::GetFolderPath("Desktop") }
    $lnk = (New-Object -ComObject WScript.Shell).CreateShortcut("$desktop\Aminos.lnk")
    $lnk.TargetPath = "$Dir\Lancer-Aminos.bat"; $lnk.Arguments = "$Port"; $lnk.WorkingDirectory = $Dir; $lnk.Save()
} catch { Write-Host "Desktop shortcut not created: $_" }

Write-Host ""
Write-Host "Aminos is $(if ($Update) { 'updated and restarting' } else { 'starting' }) (first start takes ~20 s)."
if ($Domain) {
    Write-Host "URL:   $(if ($Domain -match '^http') { $Domain } else { "https://$Domain" })"
    Write-Host "User:  $(if ($Saas) { 'admin   (then create each firm''s users in the Administration tab)' } else { 'aminos' })"
} else {
    Write-Host "URL:   http://127.0.0.1:$Port  (local only: open it from this server, or tunnel: ssh -L ${Port}:127.0.0.1:${Port} user@server)"
    if ($Saas) { Write-Host "User:  admin" }
}
if ($password) { Write-Host "Pass:  $password   <- save it, then delete $Dir\FIRST_PASSWORD.txt (keep saas.env: it also holds the data folder setting)" }
elseif ($Update) { Write-Host "Passwords and data are unchanged." }
if ($Orchestrator) { Write-Host "Supervision: logs in C:\orchestrator\logs (aminos orchestrate --once for a single cycle)" }
if ($Agency) { Write-Host "Agency: $Dir\agency  agent-hq on http://127.0.0.1:7700 (local only)$(if (-not $nodeOk) { ' - Node 22 missing, not started' })" }
Write-Host "Logs:  $Dir\logs      Update: .\update.ps1 from a newer bundle      Remove: $Dir\uninstall.ps1"
Write-Host "OCR:   scanned PDFs/images need the Claude vision OCR (API key) or Tesseract (https://github.com/UB-Mannheim/tesseract/wiki) with ara/fra/nld data."
Write-Host "Local model: install Ollama for Windows (https://ollama.com/download); the app reaches it at 127.0.0.1:11434."
