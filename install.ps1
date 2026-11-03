# Aminos suite, one command on Windows 10/11 or Server (PowerShell 5.1+):
#   irm https://raw.githubusercontent.com/aminecopilote/Aminos/main/install.ps1 | iex
# With options:
#   & ([scriptblock]::Create((irm https://raw.githubusercontent.com/aminecopilote/Aminos/main/install.ps1))) -Ref main -With agents
# Options: -Ref BRANCH, -SuiteHome DIR, -Only a,b, -Skip a,b, -With agents, -NoTests, -NoSystem
# Projects: aminos, eka, jeu, atelier, kimi (Kimi K3 in C, built with MSYS2), agents (optional).
param(
  [string]$Ref = $(if ($env:AMINOS_SUITE_REF) { $env:AMINOS_SUITE_REF } else { "main" }),
  [string]$SuiteHome = $(if ($env:AMINOS_SUITE_HOME) { $env:AMINOS_SUITE_HOME } else { Join-Path $HOME "aminos-suite" }),
  [string]$Only = "",
  [string]$Skip = "",
  [string]$With = "",
  [switch]$NoTests,
  [switch]$NoSystem
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$UvVersion = "0.11.32"
$Repo = "https://github.com/aminecopilote/Aminos.git"
function Say($m) { Write-Host "[aminos-suite] $m" }
function Exec([scriptblock]$b, [string]$what) { & $b; if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" } }
function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
function Winget-Install($id) {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Say "installing $id"
    winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements | Out-Host
    Refresh-Path
    return $true
  }
  return $false
}

# ---- system tools ------------------------------------------------------------------
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  if ($NoSystem -or -not (Winget-Install "Git.Git")) { throw "git is required: install Git for Windows (https://git-scm.com)" }
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) { $env:Path += ";$env:ProgramFiles\Git\cmd" }
}
$msys = @($env:MSYS2_ROOT, "C:\msys64", "C:\tools\msys64") | Where-Object { $_ -and (Test-Path "$_\usr\bin\bash.exe") } | Select-Object -First 1
if (-not $msys -and -not $NoSystem) {
  if (Winget-Install "MSYS2.MSYS2") { $msys = "C:\msys64" }
  else { Say "MSYS2 not found and winget unavailable: the Kimi K3 engine will be skipped (install MSYS2, then aminos-suite update)" }
}
if ($msys) { $env:MSYS2_ROOT = $msys }

# ---- Python 3.12 via uv (no admin rights) -------------------------------------------
$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) { $uv = Join-Path $HOME ".local\bin\uv.exe" }
if (-not (Test-Path $uv)) {
  Say "installing uv $UvVersion (Python manager)"
  $env:UV_NO_MODIFY_PATH = "1"
  Invoke-RestMethod "https://github.com/astral-sh/uv/releases/download/$UvVersion/uv-installer.ps1" | Invoke-Expression
}
if (-not (Test-Path $uv)) { throw "uv install failed" }

# ---- the suite code itself -----------------------------------------------------------
New-Item -ItemType Directory -Force $SuiteHome | Out-Null
$src = Join-Path $SuiteHome "suite"
if (-not (Test-Path "$src\.git")) {
  Exec { git init -q $src } "git init"
  Exec { git -C $src remote add origin $Repo } "git remote"
}
Exec { git -C $src fetch -q --depth 1 origin $Ref } "fetching $Ref"
if (-not (git -C $src status --porcelain --untracked-files=no)) {
  Exec { git -C $src -c advice.detachedHead=false checkout -q --force --detach FETCH_HEAD } "checkout"
}

$venv = Join-Path $SuiteHome "venvs\aminos"
$py = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $py)) { Exec { & $uv venv -q --seed --python 3.12 $venv } "creating the Python environment" }

$suiteArgs = @("$src\suite\suite.py", "install", "--suite-ref", $Ref)
if ($Only) { $suiteArgs += "--only=$Only" }
if ($Skip) { $suiteArgs += "--skip=$Skip" }
if ($With) { $suiteArgs += "--with=$With" }
if ($NoTests) { $suiteArgs += "--no-tests" }
$env:AMINOS_SUITE_HOME = $SuiteHome
& $py @suiteArgs
$status = $LASTEXITCODE

# ---- put aminos-suite on the user PATH ------------------------------------------------
$bin = Join-Path $SuiteHome "bin"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $userPath) { $userPath = "" }
if (-not ($userPath.Split(";") -contains $bin)) {
  [Environment]::SetEnvironmentVariable("Path", ($userPath.TrimEnd(";") + ";" + $bin).TrimStart(";"), "User")
  Say "open a new terminal to use aminos-suite"
}
$env:Path += ";$bin"
# no `exit`: under `irm | iex` it would close the terminal
if ($status -ne 0) { throw "some projects failed (exit $status), see the summary above" }
