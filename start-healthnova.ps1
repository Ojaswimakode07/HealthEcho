$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$backend = Join-Path $root "healthnova-backend"
$frontend = Join-Path $root "healthnova-frontend"
$apiBaseUrl = "http://127.0.0.1:8000"
$appUrl = "http://127.0.0.1:5173"
$stateDir = Join-Path $root ".tmp"
$backendState = Join-Path $stateDir "healthnova-backend.pid"
$frontendState = Join-Path $stateDir "healthnova-frontend.pid"
$frontendOutLog = Join-Path $stateDir "healthnova-frontend.out.log"
$frontendErrLog = Join-Path $stateDir "healthnova-frontend.err.log"
$frontendModeFile = Join-Path $stateDir "healthnova-frontend.mode"
$runBackend = Join-Path $root "run-backend.ps1"

function Resolve-BackendPython {
  if (Test-Path (Join-Path $backend ".runtime312\Scripts\python.exe")) {
    return (Join-Path $backend ".runtime312\Scripts\python.exe")
  }
  if (Test-Path (Join-Path $backend ".venv312\Scripts\python.exe")) {
    return (Join-Path $backend ".venv312\Scripts\python.exe")
  }
  if (Test-Path (Join-Path $backend ".venv\Scripts\python.exe")) {
    return (Join-Path $backend ".venv\Scripts\python.exe")
  }
  return $null
}

function Test-HttpOk {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [int]$TimeoutSec = 5
  )

  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
    return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
  } catch {
    return $false
  }
}

function Wait-HttpOk {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [int]$Attempts = 20,
    [int]$DelayMs = 1000
  )

  for ($index = 0; $index -lt $Attempts; $index++) {
    if (Test-HttpOk -Url $Url) {
      return $true
    }
    Start-Sleep -Milliseconds $DelayMs
  }

  return $false
}

function Write-PidFile {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][int]$ProcessId
  )

  if (!(Test-Path $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir | Out-Null
  }

  Set-Content -Path $Path -Value "$ProcessId"
}

function Start-FrontendStaticServer {
  if (Test-Path $frontendOutLog) { Remove-Item -LiteralPath $frontendOutLog -Force -ErrorAction SilentlyContinue }
  if (Test-Path $frontendErrLog) { Remove-Item -LiteralPath $frontendErrLog -Force -ErrorAction SilentlyContinue }

  Push-Location $frontend
  try {
    & npm.cmd run build | Out-Host
  } finally {
    Pop-Location
  }

  $distDir = Join-Path $frontend "dist"
  if (!(Test-Path $distDir)) {
    throw "Frontend static build did not produce $distDir"
  }

  $staticProc = Start-Process -FilePath $backendPython `
    -WorkingDirectory $root `
    -ArgumentList "-m", "http.server", "5173", "--bind", "127.0.0.1", "--directory", $distDir `
    -RedirectStandardOutput $frontendOutLog `
    -RedirectStandardError $frontendErrLog `
    -WindowStyle Hidden `
    -PassThru
  Write-PidFile -Path $frontendState -ProcessId $staticProc.Id
  Set-Content -Path $frontendModeFile -Value "static"
  return $staticProc
}

if (!(Test-Path $backend) -or !(Test-Path $frontend)) {
  throw "Project folders not found under $root"
}

$backendPython = Resolve-BackendPython
if (-not $backendPython) {
  throw "Backend Python environment not found. Create .runtime312, .venv312, or .venv first."
}

if (!(Test-Path (Join-Path $backend ".env")) -and (Test-Path (Join-Path $backend ".env.example"))) {
  Copy-Item (Join-Path $backend ".env.example") (Join-Path $backend ".env")
}

if (!(Test-Path (Join-Path $frontend ".env")) -and (Test-Path (Join-Path $frontend ".env.example"))) {
  Copy-Item (Join-Path $frontend ".env.example") (Join-Path $frontend ".env")
}

$frontendEnvPath = Join-Path $frontend ".env"
$frontendEnvLines = if (Test-Path $frontendEnvPath) { Get-Content $frontendEnvPath } else { @() }
if ($frontendEnvLines | Where-Object { $_ -match '^\s*VITE_API_BASE_URL=' }) {
  $frontendEnvLines = $frontendEnvLines | ForEach-Object {
    if ($_ -match '^\s*VITE_API_BASE_URL=') { "VITE_API_BASE_URL=$apiBaseUrl" } else { $_ }
  }
} else {
  $frontendEnvLines += "VITE_API_BASE_URL=$apiBaseUrl"
}
Set-Content -Path $frontendEnvPath -Value $frontendEnvLines

Write-Host "Starting HealthNova with persistent frontend and backend windows..." -ForegroundColor Cyan

$backendStarted = $false
if (-not (Test-HttpOk -Url "$apiBaseUrl/health")) {
  $backendProc = Start-Process -FilePath "powershell.exe" -ArgumentList "-ExecutionPolicy", "Bypass", "-File", $runBackend -PassThru
  Write-PidFile -Path $backendState -ProcessId $backendProc.Id
  $backendStarted = $true
}

$frontendStarted = $false
$frontendMode = "dev"
if (-not (Test-HttpOk -Url $appUrl)) {
  if (!(Test-Path $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir | Out-Null
  }

  if (Test-Path $frontendOutLog) { Remove-Item -LiteralPath $frontendOutLog -Force -ErrorAction SilentlyContinue }
  if (Test-Path $frontendErrLog) { Remove-Item -LiteralPath $frontendErrLog -Force -ErrorAction SilentlyContinue }

  $frontendProc = Start-Process -FilePath "npm.cmd" `
    -WorkingDirectory $frontend `
    -ArgumentList "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173" `
    -RedirectStandardOutput $frontendOutLog `
    -RedirectStandardError $frontendErrLog `
    -PassThru
  Write-PidFile -Path $frontendState -ProcessId $frontendProc.Id
  Set-Content -Path $frontendModeFile -Value "dev"
  $frontendStarted = $true
}

$backendOk = Wait-HttpOk -Url "$apiBaseUrl/health" -Attempts 20 -DelayMs 1000
$frontendOk = Wait-HttpOk -Url $appUrl -Attempts 20 -DelayMs 1000

if (-not $frontendOk) {
  $frontendErrorText = if (Test-Path $frontendErrLog) { Get-Content -Path $frontendErrLog -Raw -ErrorAction SilentlyContinue } else { "" }
  if ($frontendErrorText -match "EPERM: operation not permitted, lstat" -or $frontendStarted) {
    try {
      if ($frontendProc -and !$frontendProc.HasExited) {
        Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
      }
    } catch {
    }
    $null = Start-FrontendStaticServer
    $frontendOk = Wait-HttpOk -Url $appUrl -Attempts 20 -DelayMs 1000
    if ($frontendOk) {
      $frontendMode = "static"
    }
  }
} elseif (Test-Path $frontendModeFile) {
  $frontendMode = (Get-Content -Path $frontendModeFile -ErrorAction SilentlyContinue | Select-Object -First 1) -as [string]
}

Write-Host ""
Write-Host "HealthNova startup summary" -ForegroundColor Green
Write-Host "Frontend: $appUrl" -ForegroundColor $(if ($frontendOk) { "Green" } else { "Yellow" })
Write-Host "Backend API: $apiBaseUrl/docs" -ForegroundColor $(if ($backendOk) { "Green" } else { "Yellow" })
Write-Host "Backend window started: $backendStarted" -ForegroundColor DarkGray
Write-Host "Frontend window started: $frontendStarted" -ForegroundColor DarkGray
Write-Host "Frontend mode: $frontendMode" -ForegroundColor DarkGray
Write-Host "PID files: $backendState and $frontendState" -ForegroundColor DarkGray
Write-Host "Frontend logs: $frontendOutLog and $frontendErrLog" -ForegroundColor DarkGray

if ($frontendOk) {
  Start-Process $appUrl
}
