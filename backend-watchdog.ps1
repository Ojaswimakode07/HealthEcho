$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$backendDir = Join-Path $root "healthnova-backend"
$stateDir = Join-Path $root ".tmp"
$watchdogPidFile = Join-Path $stateDir "healthnova-backend-watchdog.pid"
$uvicornPidFile = Join-Path $stateDir "healthnova-backend-uvicorn.pid"
$outLog = Join-Path $backendDir ".uvicorn-live.out.log"
$errLog = Join-Path $backendDir ".uvicorn-live.err.log"
$healthUrl = "http://127.0.0.1:8000/health"

function Resolve-BackendPython {
  if (Test-Path (Join-Path $backendDir ".runtime312\Scripts\python.exe")) {
    return (Join-Path $backendDir ".runtime312\Scripts\python.exe")
  }
  if (Test-Path (Join-Path $backendDir ".venv312\Scripts\python.exe")) {
    return (Join-Path $backendDir ".venv312\Scripts\python.exe")
  }
  if (Test-Path (Join-Path $backendDir ".venv\Scripts\python.exe")) {
    return (Join-Path $backendDir ".venv\Scripts\python.exe")
  }
  throw "Backend Python environment not found."
}

function Test-BackendHealthy {
  try {
    $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
    return $response.StatusCode -eq 200
  } catch {
    return $false
  }
}

if (!(Test-Path $backendDir)) {
  throw "Backend directory not found at $backendDir"
}

if (!(Test-Path $stateDir)) {
  New-Item -ItemType Directory -Path $stateDir | Out-Null
}

Set-Content -Path $watchdogPidFile -Value "$PID"
$python = Resolve-BackendPython

Set-Location $backendDir

if (!(Test-Path ".env") -and (Test-Path ".env.example")) {
  Copy-Item ".env.example" ".env"
}

Write-Host "HealthNova backend watchdog is active on http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "This window will keep the backend alive. Leave it open while using the app." -ForegroundColor DarkGray

while ($true) {
  if (Test-BackendHealthy) {
    Start-Sleep -Seconds 4
    continue
  }

  $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -Path $outLog -Value "[$timestamp] Backend watchdog starting uvicorn"

  $env:PYTHONDONTWRITEBYTECODE = "1"
  $proc = Start-Process `
    -FilePath $python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $backendDir `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -WindowStyle Hidden `
    -PassThru

  Set-Content -Path $uvicornPidFile -Value "$($proc.Id)"

  $becameHealthy = $false
  for ($attempt = 0; $attempt -lt 15; $attempt++) {
    if (Test-BackendHealthy) {
      $becameHealthy = $true
      break
    }
    Start-Sleep -Seconds 1
  }

  if ($becameHealthy) {
    Write-Host "Backend healthy at $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Green
  } else {
    $failStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $errLog -Value "[$failStamp] Backend did not become healthy after launch."
  }

  while (-not $proc.HasExited) {
    Start-Sleep -Seconds 3
    if (-not (Test-BackendHealthy)) {
      continue
    }
  }

  $exitStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -Path $errLog -Value "[$exitStamp] Backend process exited with code $($proc.ExitCode). Restarting."
  Write-Host "Backend stopped. Restarting..." -ForegroundColor Yellow
  Start-Sleep -Seconds 2
}
