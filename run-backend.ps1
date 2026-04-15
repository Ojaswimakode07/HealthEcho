$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$stateDir = Join-Path $root ".tmp"
$watchdogScript = Join-Path $root "backend-watchdog.ps1"
$watchdogPidFile = Join-Path $stateDir "healthnova-backend-watchdog.pid"
$healthUrl = "http://127.0.0.1:8000/health"

function Test-BackendHealthy {
  try {
    $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
    return $response.StatusCode -eq 200
  } catch {
    return $false
  }
}

function Test-WatchdogRunning {
  if (!(Test-Path $watchdogPidFile)) {
    return $false
  }

  try {
    $pidValue = [int](Get-Content -Path $watchdogPidFile -ErrorAction Stop | Select-Object -First 1)
    $process = Get-Process -Id $pidValue -ErrorAction Stop
    return $process -ne $null
  } catch {
    return $false
  }
}

if (!(Test-Path $watchdogScript)) {
  throw "Backend watchdog script not found at $watchdogScript"
}

if (!(Test-Path $stateDir)) {
  New-Item -ItemType Directory -Path $stateDir | Out-Null
}

if (Test-BackendHealthy) {
  Write-Host "HealthNova backend is already healthy on http://127.0.0.1:8000"
  exit 0
}

if (-not (Test-WatchdogRunning)) {
  Write-Host "Starting HealthNova backend watchdog window..."
  $command = "`$Host.UI.RawUI.WindowTitle = 'HealthNova Backend'; & '$watchdogScript'"
  $proc = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $command `
    -PassThru
  Set-Content -Path $watchdogPidFile -Value "$($proc.Id)"
} else {
  Write-Host "HealthNova backend watchdog is already running."
}

for ($index = 0; $index -lt 30; $index++) {
  if (Test-BackendHealthy) {
    Write-Host "HealthNova backend is healthy on http://127.0.0.1:8000"
    exit 0
  }
  Start-Sleep -Seconds 1
}

throw "HealthNova backend did not become healthy in time."
