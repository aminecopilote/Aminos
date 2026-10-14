<#
.SYNOPSIS  Online installer for Aminos on Windows (no Docker): downloads the code from GitHub at a given version, then runs install.ps1.
           Needs Internet access to github.com, pypi.org and python.org. Run PowerShell as Administrator (or add -NoService).
.EXAMPLE   .\bootstrap.ps1 -Ref <commit> -Saas                          # multi-user, local access http://127.0.0.1:8501
.EXAMPLE   .\bootstrap.ps1 -Ref <commit> -Saas -Domain aminos.example.com -Orchestrator -Agency
.EXAMPLE   .\bootstrap.ps1 -Update                                       # re-download the same ref (a branch name follows its newest commit)
Pin -Ref to a commit SHA: a branch can change under you, a commit cannot.
#>
param(
    [string]$Repo = "aminecopilote/Aminos",
    [string]$Ref = "main",
    [string]$Dir = "C:\Aminos",
    [int]$Port = 8501,
    [string]$Domain = "",
    [switch]$NoService, [switch]$Saas, [switch]$Orchestrator, [switch]$Agency, [switch]$Update,
    [string[]]$Skills = @()
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.ServicePointManager]::SecurityProtocol } catch { }

# the two agency repositories, at the commits that were tested
$AgencySources = @{ "agent-coordinator" = "SuperInstance/agent-coordinator@4d2560d2e53d2d066328ed4a0250376efe44aa2a"
                    "agent-hq"          = "tools-for-agents/agent-hq@785cd8c9a55b2b517eb8eb8f680cd65985992282" }

$work = Join-Path $env:TEMP ("aminos-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Force -Path $work | Out-Null
function Get-GitHubZip($repo, $ref, $dest) {
    $zip = Join-Path $work (($repo -replace "/", "_") + ".zip")
    Write-Host "==> Downloading $repo @ $ref"
    Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/$repo/archive/$ref.zip" -OutFile $zip
    Expand-Archive $zip -DestinationPath $dest -Force
    return (Get-ChildItem $dest -Directory | Select-Object -First 1).FullName      # the single top-level folder
}
try {
    $src = Get-GitHubZip $Repo $Ref "$work\src"
    if (-not (Test-Path "$src\deploy\windows\install.ps1")) { throw "$Repo @ $Ref has no deploy\windows\install.ps1 (wrong ref?)" }

    # lay the files out exactly like the offline bundle, minus the wheelhouse
    $b = "$work\bundle"
    New-Item -ItemType Directory -Force -Path $b, "$b\agency" | Out-Null
    $w = "$src\deploy\windows"
    Copy-Item "$src\app.py", "$src\saas_app.py" $b
    Copy-Item "$w\install.ps1", "$w\update.ps1", "$w\bootstrap.ps1", "$w\run-app.ps1", "$w\run-orchestrator.ps1", "$w\run-agent-hq.ps1",
              "$w\uninstall.ps1", "$w\Lancer-Aminos.bat", "$w\requirements.txt" $b
    Copy-Item "$src\skills" "$b\skills" -Recurse
    Copy-Item "$src\agency\AGENTS.md", "$src\agency\MEMORY-orchestrateur.md", "$src\agency\start-agent-hq.mjs" "$b\agency"
    if ($Agency -or ($Update -and (Test-Path "$Dir\agency\agent-hq"))) {
        foreach ($name in $AgencySources.Keys) {
            $repo, $sha = $AgencySources[$name] -split "@"
            $root = Get-GitHubZip $repo $sha "$work\$name"
            Copy-Item $root "$b\agency\$name" -Recurse
        }
    }

    $p = @{ Dir = $Dir; Port = $Port; Online = $true; SourceDir = $src; Repo = $Repo; Ref = $Ref }
    if ($Domain) { $p.Domain = $Domain }
    if ($Skills.Count) { $p.Skills = $Skills }
    foreach ($sw in "NoService", "Saas", "Orchestrator", "Agency", "Update") { if ((Get-Variable $sw).Value) { $p[$sw] = $true } }
    & "$b\install.ps1" @p
    if ($LASTEXITCODE -ne $null -and $LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
}
