# FinAlly - start script (Windows PowerShell)
# Idempotent: safe to run repeatedly. Rebuilds the image, replaces any running
# container, and mounts a named volume so the SQLite database persists.

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Image = "finally:latest"
$Container = "finally"

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "No .env found - creating one from .env.example." -ForegroundColor Yellow
        Write-Host "  -> Edit .env and set OPENROUTER_KEY before using the AI chat." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
    } else {
        Write-Host "Error: no .env or .env.example in $ProjectRoot. Aborting." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Building FinAlly Docker image ($Image)..." -ForegroundColor Yellow
docker build -t $Image -f backend/Dockerfile .

Write-Host "Removing any existing '$Container' container..." -ForegroundColor Yellow
try { docker rm -f $Container 2>$null } catch { }

Write-Host "Starting FinAlly..." -ForegroundColor Yellow
docker run -d `
  --name $Container `
  -v finally-data:/app/db `
  -p 8000:8000 `
  --env-file .env `
  --restart unless-stopped `
  $Image

Write-Host "Waiting for FinAlly to become healthy..." -ForegroundColor Yellow
$healthy = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) { $healthy = $true; break }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($healthy) {
    Write-Host "FinAlly is running at http://localhost:8000" -ForegroundColor Green
    Write-Host "Open http://localhost:8000 in your browser." -ForegroundColor Cyan
} else {
    Write-Host "Warning: health check did not pass yet. The container may still be starting." -ForegroundColor Red
    Write-Host "Check logs with: docker logs $Container" -ForegroundColor Yellow
}
