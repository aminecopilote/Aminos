# Installs all skills from this repo into your user-level Claude Code skills folder
# and also into the _certification workspace. Run in PowerShell:  .\install-skills.ps1
$ErrorActionPreference = 'Stop'
$src = Join-Path $PSScriptRoot '.claude\skills'
$targets = @(
  (Join-Path $env:USERPROFILE '.claude\skills'),
  'C:\Users\verta\Downloads\_certification\.claude\skills',
  # atelier workspace: one folder per AI agent (Claude Code, Codex/Gemini/other agents)
  'C:\Users\verta\Downloads\_certification\atelier\.claude\skills',
  'C:\Users\verta\Downloads\_certification\atelier\.agents\skills',
  'C:\Users\verta\Downloads\_certification\atelier\.codex\skills',
  'C:\Users\verta\Downloads\_certification\atelier\.gemini\skills'
)
foreach ($t in $targets) {
  New-Item -ItemType Directory -Force -Path $t | Out-Null
  Copy-Item -Path (Join-Path $src '*') -Destination $t -Recurse -Force
  Write-Host "Installed $((Get-ChildItem $t -Directory).Count) skills into $t"
}
Write-Host 'Done. Restart Claude Code to load the skills.'
