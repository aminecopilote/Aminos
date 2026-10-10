# Windows (PowerShell 5.1+): clone the two external repos and install the agents.
#   .\external\install.ps1 [-Tool claude-code] [-Division engineering,security] [-Dir C:\path]
# The agency-agents installer is a bash script: Git for Windows (Git Bash) or WSL is required.
param(
  [string]$Tool = "claude-code",
  [string]$Division = "",
  [string]$Dir = (Join-Path $HOME "aminos-external")
)
$ErrorActionPreference = "Stop"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "git missing: winget install --id Git.Git -e"
}

function Sync-Repo($url, $name) {
  $path = Join-Path $Dir $name
  if (Test-Path (Join-Path $path ".git")) { git -C $path pull --ff-only }
  else { git clone --depth 1 $url $path }
  if ($LASTEXITCODE -ne 0) { throw "git failed for $name" }
}
New-Item -ItemType Directory -Force -Path $Dir | Out-Null
Sync-Repo "https://github.com/msitarzewski/agency-agents.git" "agency-agents"
Sync-Repo "https://github.com/ashishpatel26/500-AI-Agents-Projects.git" "500-AI-Agents-Projects"

$opts = "--tool $Tool --no-interactive"
if ($Division) { $opts += " --division $Division" }

$gitBash = Join-Path ${env:ProgramFiles} "Git\bin\bash.exe"
$repo = Join-Path $Dir "agency-agents"
if (Test-Path $gitBash) {
  Push-Location $repo
  & $gitBash -c "bash scripts/install.sh $opts"
  Pop-Location
} elseif (Get-Command wsl -ErrorAction SilentlyContinue) {
  # WSL installs into the WSL home, not the Windows profile.
  $wslPath = (wsl wslpath -a $repo).Trim()
  wsl bash -c "cd '$wslPath' && bash scripts/install.sh $opts"
} else {
  throw "Git Bash or WSL required (winget install --id Git.Git -e)."
}
if ($LASTEXITCODE -ne 0) { throw "agency-agents install failed" }

Write-Host "`nagency-agents installed ($opts)."
Write-Host "500-AI-Agents-Projects (reference list, nothing to install): $(Join-Path $Dir '500-AI-Agents-Projects')"
