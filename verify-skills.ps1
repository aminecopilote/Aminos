# Verifies (and repairs with -Fix) the skills installed in the atelier workspace.
# Usage from the Aminos folder:  powershell -ExecutionPolicy Bypass -File .\verify-skills.ps1 -Fix
param([switch]$Fix)
$src = Join-Path $PSScriptRoot '.claude\skills'
if (-not (Test-Path $src)) { Write-Host "ERROR: $src not found. Run this from the cloned Aminos folder (branch claude/sweet-pascal-8oyvxa)." -ForegroundColor Red; exit 1 }
$atelier = 'C:\Users\verta\Downloads\_certification\atelier'
if (-not (Test-Path $atelier)) { Write-Host "ERROR: $atelier does not exist." -ForegroundColor Red; exit 1 }
Write-Host "--- atelier contents ---"; Get-ChildItem $atelier -Force | Select-Object Mode,Name | Format-Table -AutoSize
$expected = Get-ChildItem $src -Directory
Write-Host "Expected skills: $($expected.Count)"
$targets = '.claude','.agents','.codex','.gemini' | ForEach-Object { Join-Path $atelier "$_\skills" }
foreach ($t in $targets) {
  if (-not (Test-Path $t)) {
    Write-Host "MISSING folder: $t" -ForegroundColor Yellow
    if ($Fix) { New-Item -ItemType Directory -Force -Path $t | Out-Null } else { continue }
  }
  $missing = @(); $badFm = @(); $extra = @()
  foreach ($e in $expected) {
    $md = Join-Path $t "$($e.Name)\SKILL.md"
    if (-not (Test-Path $md)) { $missing += $e.Name; continue }
    $head = Get-Content $md -TotalCount 5 -Raw -ErrorAction SilentlyContinue
    if ($head -notmatch '^---' -or $head -notmatch 'name:' -or $head -notmatch 'description:') { $badFm += $e.Name }
  }
  $names = $expected.Name
  $extra = Get-ChildItem $t -Directory -ErrorAction SilentlyContinue | Where-Object { $names -notcontains $_.Name } | ForEach-Object Name
  $color = if ($missing.Count -or $badFm.Count) { 'Yellow' } else { 'Green' }
  Write-Host "$t : missing=$($missing.Count) badFrontmatter=$($badFm.Count) obsolete=$($extra.Count)" -ForegroundColor $color
  if ($Fix) {
    foreach ($n in ($missing + $badFm)) { Copy-Item (Join-Path $src $n) $t -Recurse -Force }
    foreach ($n in $extra) { if ($n -in 'alirezarezvani-arquiteto-de-empresa','alirezarezvani-chaos-engineering','alirezarezvani-chief-ai-officer-advisor','alirezarezvani-chief-customer-officer-advisor','alirezarezvani-chief-data-officer-advisor','alirezarezvani-eu-ai-act-specialist','alirezarezvani-feature-flags-architect','alirezarezvani-general-counsel-advisor','alirezarezvani-iso42001-specialist','alirezarezvani-kubernetes-operator','alirezarezvani-slo-architect','alirezarezvani-vpe-advisor','google-finding-google-skills','google-google-cloud-recipe-auth','google-google-cloud-recipe-onboarding','google-gcloud','google-retrieving-developer-knowledge') { Remove-Item (Join-Path $t $n) -Recurse -Force } }
    # refresh all files so edits (renamed skills etc.) are current
    Copy-Item -Path (Join-Path $src '*') -Destination $t -Recurse -Force
    Write-Host "  repaired $t" -ForegroundColor Cyan
  } elseif ($missing.Count) { Write-Host "  e.g. missing: $($missing[0..([Math]::Min(4,$missing.Count-1))] -join ', ')" }
}
if (-not $Fix) { Write-Host "Re-run with -Fix to repair." }
