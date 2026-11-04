@echo off
rem Starts Aminos if it is not running yet, then opens it in the browser. Argument: port (default 8501).
set PORT=%~1
if "%PORT%"=="" set PORT=8501
set DIR=%~dp0
set FLAG=
if exist "%~dp0saas.env" set FLAG=-Saas
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:%PORT%/_stcore/health -TimeoutSec 2) | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
  echo Demarrage d'Aminos, patientez une vingtaine de secondes...
  schtasks /Run /TN Aminos >nul 2>&1
  if errorlevel 1 start "" /B powershell -NoProfile -ExecutionPolicy Bypass -File "%DIR%run-app.ps1" -Dir "%DIR:~0,-1%" -Port %PORT% %FLAG%
  powershell -NoProfile -Command "1..40 | ForEach-Object { try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:%PORT%/_stcore/health -TimeoutSec 2 | Out-Null; exit 0 } catch { Start-Sleep 2 } }; exit 1"
)
start "" http://127.0.0.1:%PORT%
