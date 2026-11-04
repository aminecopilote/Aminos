<#
.SYNOPSIS  Aminos on a brand-new Windows Server 2022 VPS: installs every prerequisite, then Aminos (multi-user), the back-office,
           HTTPS (Caddy) and, on request, n8n, the supervision loop and the agency. Windows PowerShell 5.1, run as Administrator.
.DESCRIPTION
  Prerequisites installed when missing (each installer's digital signature is verified before it runs):
    Visual C++ runtime 2015-2022 (Microsoft)      Python 3.12 (Python Software Foundation)      Git for Windows (also provides OpenSSL,
    used to verify signatures)      LibreOffice (PDF of the translated pages; skip with -NoPdf)      Node 24 (only with -Agency)
    Tesseract + Arabic/French/Dutch data (only with -WithOcr, not covered by the tests)
  Also: long paths enabled, Windows Defender exclusion for the install folder DURING the install only (npm unpacks tens of
  thousands of files; without it the n8n step takes more than an hour), firewall rules 80/443, boot-time scheduled tasks.
  Every step is logged to <install dir>\install.log (C:\Aminos\install.log by default). Re-running is safe: what is installed is detected and left alone.
.EXAMPLE   .\vps-install.ps1 -Domain aminos.example.com -N8n -AlertUrl https://hooks.example.com/x
.EXAMPLE   .\vps-install.ps1 -Domain aminos.example.com -Ref <commit> -Orchestrator -Agency -WithOcr
.EXAMPLE   .\vps-install.ps1 -CheckOnly            # only verify the machine and the network, install nothing
Without -Domain the site is only reachable from the server itself (http://127.0.0.1:8501 and /erp/ on 8502).
With -Domain, its DNS A record must already point to this server's public IP (Let's Encrypt checks it).
Pin -Ref to a commit SHA for a reproducible install.
#>
[CmdletBinding()]
param(
    [string]$Domain = "",
    [string]$Repo = "aminecopilote/Aminos",
    [string]$Ref = "main",
    [string]$Dir = "C:\Aminos",
    [switch]$N8n,            # n8n automation: monitoring, nightly backup, daily digest, web-form intake
    [string]$AlertUrl = "",  # webhook receiving the alerts (Slack, Mattermost, Discord, ntfy...)
    [switch]$Orchestrator,   # supervision loop every 5 minutes
    [switch]$Agency,         # agent-hq + agent-coordinator copies (installs Node 24 system-wide)
    [switch]$NoPdf,          # do not install LibreOffice (certified translations then carry the statement page only)
    [switch]$NoGit,          # do not install Git for Windows (no `aminos skills install`, no OpenSSL for signature checks)
    [switch]$WithOcr,        # Tesseract with Arabic, French, Dutch (UNTESTED)
    [switch]$NoService,      # per-user run: no boot task, no firewall rule (CI and tests)
    [switch]$KeepDefenderExclusion,
    [switch]$CheckOnly
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.ServicePointManager]::SecurityProtocol
$logDir = if ($CheckOnly) { $env:TEMP } else { $Dir }      # a check leaves nothing behind in the install folder
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$InstallLog = Join-Path $logDir "install.log"
try { Start-Transcript -Path $InstallLog -Append | Out-Null } catch { }

# pinned versions of what is downloaded (installers are signature-checked; Node by SHA-256 from nodejs.org)
$PythonVersion = "3.12.10"
$GitVersion = "2.47.1"; $GitTag = "v2.47.1.windows.1"
$TesseractUrl = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe"

function Step($m) { Write-Host ""; Write-Host "==> $m" -ForegroundColor Cyan }
function Note($m) { Write-Host "    $m" }
function Warn($m) { Write-Host "    ! $m" -ForegroundColor Yellow }
function Fail($m) { Write-Host "    X $m" -ForegroundColor Red; throw $m }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole("Administrator")

function Get-File($url, $dest) {
    foreach ($try in 1..3) {
        try { Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $dest -TimeoutSec 900; return } catch {
            if ($try -eq 3) { throw "Download failed: $url ($_)" }
            Start-Sleep -Seconds (5 * $try)
        }
    }
}
function Assert-Signed($path, $subjectPattern) {
    $sig = Get-AuthenticodeSignature $path
    if ($sig.Status -ne "Valid") { Fail "Signature of $path is not valid ($($sig.Status))" }
    if ($sig.SignerCertificate.Subject -notmatch $subjectPattern) { Fail "$path is signed by '$($sig.SignerCertificate.Subject)', expected '$subjectPattern'" }
}
function Update-SessionPath {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
function Test-Online($url) {
    try { Invoke-WebRequest -UseBasicParsing -Uri $url -Method Head -TimeoutSec 20 | Out-Null; return $true } catch {
        # a server that answers with an HTTP error is reachable; only transport failures count
        return [bool]($_.Exception.Response)
    }
}

# ---------------------------------------------------------------------------------------------------------------------
Step "Checking the machine"
$os = Get-CimInstance Win32_OperatingSystem
Note "$($os.Caption), build $($os.BuildNumber)"
if (-not [Environment]::Is64BitOperatingSystem) { Fail "A 64-bit Windows is required." }
if ([int]$os.BuildNumber -lt 17763) { Fail "Windows Server 2019 / Windows 10 1809 or newer is required (found build $($os.BuildNumber))." }
if ($os.Caption -notmatch "Server") { Warn "This is not a Windows Server edition; it should still work." }
$ramGb = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
Note "RAM: $ramGb GB"
if ($ramGb -lt 3.5) { Warn "Less than 4 GB of RAM: the app will start, but translations of long documents may be slow." }
$sysDrive = (Get-Item $env:SystemRoot).PSDrive
$freeGb = [math]::Round($sysDrive.Free / 1GB, 1)
Note "Free space on $($sysDrive.Name): $freeGb GB"
if ($freeGb -lt 8) { Fail "At least 8 GB of free disk space is required (found $freeGb GB)." }
if ($freeGb -lt 15) { Warn "Less than 15 GB free: LibreOffice, n8n and the backups need room." }
if (-not $isAdmin -and -not $NoService -and -not $CheckOnly) { Fail "Run PowerShell as Administrator (or add -NoService for a per-user test install)." }

$hosts = @("https://github.com", "https://pypi.org", "https://files.pythonhosted.org", "https://www.python.org", "https://raw.githubusercontent.com")
if ($N8n -or $Agency) { $hosts += "https://nodejs.org" }
if (-not $NoPdf) { $hosts += "https://download.documentfoundation.org" }
$bad = @($hosts | Where-Object { -not (Test-Online $_) })
if ($bad.Count) { Fail "Cannot reach: $($bad -join ', '). Check the VPS firewall / outbound access." }
Note "Network OK ($($hosts.Count) hosts)"

if ($Domain) {
    $publicHost = $Domain -replace "^https?://", ""
    if ($publicHost -match "^[A-Za-z0-9.-]+$" -and $publicHost -notmatch "^(localhost|127\.)") {
        try {
            $myIp = (Invoke-RestMethod -UseBasicParsing "https://api.ipify.org" -TimeoutSec 20).Trim()
            $dnsIps = @(Resolve-DnsName $publicHost -Type A -ErrorAction Stop | Where-Object { $_.IPAddress } | ForEach-Object { $_.IPAddress })
            if ($dnsIps -contains $myIp) { Note "DNS OK: $publicHost -> $myIp" }
            else { Warn "$publicHost resolves to [$($dnsIps -join ', ')] but this server is ${myIp}: HTTPS will not be issued until the A record points here." }
        } catch { Warn "Could not verify the DNS record of $publicHost ($($_.Exception.Message))." }
    }
}
if ($CheckOnly) { Write-Host ""; Write-Host "Check finished: nothing installed." -ForegroundColor Green; try { Stop-Transcript | Out-Null } catch { }; return }

# ---------------------------------------------------------------------------------------------------------------------
$work = Join-Path $env:TEMP ("aminos-vps-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Force -Path $work | Out-Null
$defenderAdded = $false
try {
    if ($isAdmin) {
        Step "Windows settings"
        Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -Type DWord
        Note "Long paths enabled"
        try {
            Add-MpPreference -ExclusionPath $Dir, $work -ErrorAction Stop
            $defenderAdded = $true
            Note "Defender: $Dir excluded during the install only (removed at the end)"
        } catch { Warn "Defender exclusion not possible ($($_.Exception.Message)); the install will be slower." }
    }

    Step "Visual C++ runtime"
    $vc = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" -ErrorAction SilentlyContinue
    if ($vc -and $vc.Installed -eq 1) { Note "already installed ($($vc.Version))" }
    elseif ($isAdmin) {
        $f = Join-Path $work "vc_redist.x64.exe"
        Get-File "https://aka.ms/vs/17/release/vc_redist.x64.exe" $f
        Assert-Signed $f "Microsoft Corporation"
        $p = Start-Process $f -ArgumentList "/install /quiet /norestart" -Wait -PassThru
        if ($p.ExitCode -notin 0, 1638, 3010) { Fail "VC++ runtime installer failed (exit $($p.ExitCode))" }
        Note "installed"
    } else { Warn "not installed (needs Administrator)" }

    Step "Python $PythonVersion"
    $havePython = $false
    try { $v = & py -3.12 -c "import sys;print('%d.%d' % sys.version_info[:2])" 2>$null; $havePython = ($LASTEXITCODE -eq 0 -and $v -eq "3.12") } catch { }
    if (-not $havePython) {
        try { $v = & python -c "import sys;print('%d.%d' % sys.version_info[:2])" 2>$null; $havePython = ($LASTEXITCODE -eq 0 -and $v -eq "3.12") } catch { }
    }
    if ($havePython) { Note "Python 3.12 found" }
    else {
        $f = Join-Path $work "python-$PythonVersion-amd64.exe"
        Get-File "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe" $f
        Assert-Signed $f "Python Software Foundation"
        $all = if ($isAdmin) { 1 } else { 0 }
        $p = Start-Process $f -ArgumentList "/quiet InstallAllUsers=$all PrependPath=1 Include_test=0 Include_launcher=1" -Wait -PassThru
        if ($p.ExitCode -ne 0) { Fail "Python installer failed (exit $($p.ExitCode))" }
        Update-SessionPath
        Note "installed"
    }

    Step "Git for Windows (also provides OpenSSL)"
    if ($NoGit) { Note "skipped (-NoGit)" }
    elseif (Get-Command git -ErrorAction SilentlyContinue) { Note "already installed" }
    elseif (-not $isAdmin) { Warn "not installed (needs Administrator)" }
    else {
        $f = Join-Path $work "Git-$GitVersion-64-bit.exe"
        Get-File "https://github.com/git-for-windows/git/releases/download/$GitTag/Git-$GitVersion-64-bit.exe" $f
        Assert-Signed $f "Johannes Schindelin|Git for Windows"
        $p = Start-Process $f -ArgumentList "/VERYSILENT /NORESTART /SP- /NOCANCEL" -Wait -PassThru
        if ($p.ExitCode -ne 0) { Fail "Git installer failed (exit $($p.ExitCode))" }
        Update-SessionPath
        Note "installed"
    }

    if ($Agency) {
        Step "Node 24 (system-wide, for agent-hq)"
        $nodeOk = $false
        try { $nv = & node --version 2>$null; $nodeOk = ($LASTEXITCODE -eq 0 -and [int]($nv -replace '^v(\d+)\..*', '$1') -ge 22) } catch { }
        if ($nodeOk) { Note "Node $nv found" }
        elseif (-not $isAdmin) { Warn "not installed (needs Administrator)" }
        else {
            $idx = "https://nodejs.org/dist/latest-v24.x"
            $line = ((Invoke-WebRequest -UseBasicParsing "$idx/SHASUMS256.txt").Content -split "`n") | Where-Object { $_ -match "node-v24\.[0-9.]+-x64\.msi" } | Select-Object -First 1
            if (-not $line) { Fail "Node 24 MSI not listed on nodejs.org" }
            $sha, $msiName = $line.Trim() -split "\s+", 2
            $f = Join-Path $work $msiName
            Get-File "$idx/$msiName" $f
            if ((Get-FileHash -Algorithm SHA256 $f).Hash.ToLower() -ne $sha.ToLower()) { Fail "Node download checksum mismatch" }
            Assert-Signed $f "OpenJS Foundation"
            $p = Start-Process msiexec.exe -ArgumentList "/i `"$f`" /qn /norestart" -Wait -PassThru
            if ($p.ExitCode -notin 0, 3010) { Fail "Node installer failed (exit $($p.ExitCode))" }
            Update-SessionPath
            Note "installed $msiName"
        }
    }

    Step "LibreOffice (PDF of the translated pages)"
    $soffice = @("C:\Program Files\LibreOffice\program\soffice.exe", "C:\Program Files (x86)\LibreOffice\program\soffice.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($NoPdf) { Note "skipped (-NoPdf)" }
    elseif ($soffice) { Note "already installed" }
    elseif (-not $isAdmin) { Warn "not installed (needs Administrator)" }
    else {
        try {
            $html = (Invoke-WebRequest -UseBasicParsing "https://download.documentfoundation.org/libreoffice/stable/").Content
            $versions = @([regex]::Matches($html, 'href="(\d+\.\d+\.\d+)/"') | ForEach-Object { [version]$_.Groups[1].Value } | Sort-Object -Descending)
            if (-not $versions) { throw "no stable version listed" }
            $lo = $versions[0].ToString()
            $f = Join-Path $work "LibreOffice_${lo}_Win_x86-64.msi"
            Get-File "https://download.documentfoundation.org/libreoffice/stable/$lo/win/x86_64/LibreOffice_${lo}_Win_x86-64.msi" $f
            Assert-Signed $f "The Document Foundation"
            $p = Start-Process msiexec.exe -ArgumentList "/i `"$f`" /qn /norestart ALLUSERS=1 REGISTER_ALL_MSO_TYPES=0 UI_LANGS=fr_FR,en_US" -Wait -PassThru
            if ($p.ExitCode -notin 0, 3010) { throw "msiexec exit $($p.ExitCode)" }
            Note "installed LibreOffice $lo"
        } catch { Warn "LibreOffice not installed ($($_.Exception.Message)). Certified translations will carry the statement page only. Install it later and re-run." }
    }

    if ($WithOcr) {
        Step "Tesseract OCR (Arabic, French, Dutch) - not covered by the tests"
        $tess = "C:\Program Files\Tesseract-OCR"
        if (-not $isAdmin) { Warn "not installed (needs Administrator)" }
        else {
            try {
                if (-not (Test-Path "$tess\tesseract.exe")) {
                    $f = Join-Path $work "tesseract-setup.exe"
                    Get-File $TesseractUrl $f
                    $sig = Get-AuthenticodeSignature $f
                    if ($sig.Status -ne "Valid") { Warn "the Tesseract installer is not digitally signed (status $($sig.Status)); continuing because you asked for it" }
                    $p = Start-Process $f -ArgumentList "/S" -Wait -PassThru
                    if ($p.ExitCode -ne 0) { throw "installer exit $($p.ExitCode)" }
                }
                foreach ($lang in "ara", "fra", "nld", "eng") {
                    if (-not (Test-Path "$tess\tessdata\$lang.traineddata")) {
                        Get-File "https://github.com/tesseract-ocr/tessdata_fast/raw/main/$lang.traineddata" "$tess\tessdata\$lang.traineddata"
                    }
                }
                $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
                if ($machinePath -notlike "*Tesseract-OCR*") { [Environment]::SetEnvironmentVariable("Path", "$machinePath;$tess", "Machine") }
                Update-SessionPath
                Note "installed"
            } catch { Warn "Tesseract not installed ($($_.Exception.Message))" }
        }
    }

    # -----------------------------------------------------------------------------------------------------------------
    Step "Aminos ($Repo @ $Ref)"
    $bootstrap = Join-Path $work "bootstrap.ps1"
    Get-File "https://raw.githubusercontent.com/$Repo/$Ref/deploy/windows/bootstrap.ps1" $bootstrap
    $params = @{ Repo = $Repo; Ref = $Ref; Dir = $Dir; Saas = $true }
    if ($Domain) { $params.Domain = $Domain }
    if ($N8n) { $params.N8n = $true }
    if ($AlertUrl) { $params.AlertUrl = $AlertUrl }
    if ($Orchestrator) { $params.Orchestrator = $true }
    if ($Agency) { $params.Agency = $true }
    if ($NoService) { $params.NoService = $true }
    $global:LASTEXITCODE = 0     # an earlier probe (py, node) may have left a non-zero code behind
    & $bootstrap @params
    if ($LASTEXITCODE -ne $null -and $LASTEXITCODE -ne 0) { Fail "bootstrap.ps1 failed (exit $LASTEXITCODE)" }

    # -----------------------------------------------------------------------------------------------------------------
    Step "Checking that everything answers"
    $checks = @(@{ Name = "translation app + superagent"; Url = "http://127.0.0.1:8501/_stcore/health"; Test = { param($r) $r.Content -eq "ok" } },
                @{ Name = "back-office (/erp/)"; Url = "http://127.0.0.1:8502/erp/"; Test = { param($r) $r.StatusCode -eq 200 } })
    if ($N8n) { $checks += @{ Name = "n8n"; Url = "http://127.0.0.1:5678/healthz"; Test = { param($r) $r.StatusCode -eq 200 } } }
    $failed = @()
    foreach ($c in $checks) {
        $ok = $false
        foreach ($i in 1..60) {
            try { if (& $c.Test (Invoke-WebRequest -UseBasicParsing $c.Url -TimeoutSec 10)) { $ok = $true; break } } catch { }
            Start-Sleep -Seconds 3
        }
        if ($ok) { Note "OK    $($c.Name)" } else { Warn "FAIL  $($c.Name)  (logs in $Dir\logs)"; $failed += $c.Name }
    }
    & "$Dir\venv\Scripts\aminos.exe" superagent selftest
    if ($LASTEXITCODE -ne 0) { Warn "superagent self-test reported a problem (see above)"; $failed += "superagent self-test" }

    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Green
    $base = if ($Domain) { if ($Domain -match "^https?://") { $Domain } else { "https://$Domain" } } else { "http://127.0.0.1" }
    if ($Domain) { Write-Host " Application + superagent : $base/" ; Write-Host " Back-office              : $base/erp/" }
    else { Write-Host " Application + superagent : http://127.0.0.1:8501   (from this server, or an SSH/RDP tunnel)"; Write-Host " Back-office              : http://127.0.0.1:8502/erp/" }
    Write-Host " Administrator            : admin"
    if (Test-Path "$Dir\FIRST_PASSWORD.txt") { Write-Host " Password (shown once)    : $((Get-Content "$Dir\FIRST_PASSWORD.txt" -Raw).Trim())   <- save it, then delete $Dir\FIRST_PASSWORD.txt (KEEP $Dir\saas.env)" }
    if ($N8n) { Write-Host " n8n editor               : http://127.0.0.1:5678 via RDP or tunnel; create the owner account NOW" }
    Write-Host " Install log              : $InstallLog      App logs: $Dir\logs"
    Write-Host " Reboot test              : restart the VPS once and check that the site comes back (boot-time tasks)"
    if ($failed.Count) { Write-Host " TO CHECK                 : $($failed -join ', ')" -ForegroundColor Yellow }
    Write-Host "================================================================================" -ForegroundColor Green
    if ($failed.Count) { exit 1 }
} finally {
    if ($defenderAdded -and -not $KeepDefenderExclusion) {
        try { Remove-MpPreference -ExclusionPath $Dir, $work -ErrorAction Stop } catch { }
    }
    Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
    try { Stop-Transcript | Out-Null } catch { }
}
