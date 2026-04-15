$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$backendDir = Join-Path $root "healthnova-backend"
$stateDir = Join-Path $root ".tmp"
$supervisorPidFile = Join-Path $stateDir "healthnova-backend-supervisor.pid"
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

if (!(Test-Path $stateDir)) {
  New-Item -ItemType Directory -Path $stateDir | Out-Null
}

Set-Content -Path $supervisorPidFile -Value "$PID"

$python = Resolve-BackendPython
Set-Location $backendDir

if (!(Test-Path ".env") -and (Test-Path ".env.example")) {
  Copy-Item .env.example .env
}

while ($true) {
  if (Test-BackendHealthy) {
    Start-Sleep -Seconds 5
    continue
  }

  $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -Path $outLog -Value "[$timestamp] Starting backend supervisor cycle"
  try {
    $proc = Start-Process `
      -FilePath $python `
      -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
      -WorkingDirectory $backendDir `
      -WindowStyle Hidden `
      -RedirectStandardOutput $outLog `
      -RedirectStandardError $errLog `
      -PassThru

    Set-Content -Path $uvicornPidFile -Value "$($proc.Id)"

    while (-not $proc.HasExited) {
      if (Test-BackendHealthy) {
        Start-Sleep -Seconds 5
        continue
      }
      Start-Sleep -Seconds 2
    }

    $exitStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $errLog -Value "[$exitStamp] Backend process exited with code $($proc.ExitCode)"
  } catch {
    $errorStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $errLog -Value "[$errorStamp] Backend process crashed: $($_.Exception.Message)"
  }
  Start-Sleep -Seconds 2
}
