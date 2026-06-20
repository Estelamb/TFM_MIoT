# AURA Run Edge — Windows Startup Script
# ====================================
# Launches the Hardware Daemon in a separate process and runs the Docker Compose
# stack for the local Edge Agent.

# Force execution in the script's folder
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (!$scriptDir) { $scriptDir = "." }

Write-Host "--------------------------------------------------------" -ForegroundColor Cyan
Write-Host " Starting AURA Edge Stack (Daemon + Container) " -ForegroundColor Cyan
Write-Host "--------------------------------------------------------" -ForegroundColor Cyan

# 1. Start the Hardware Daemon in a new window
Write-Host "[1/2] Starting Hardware Daemon in a new process..." -ForegroundColor Yellow
Start-Process python -ArgumentList "$scriptDir\hardware_daemon.py" -WorkingDirectory $scriptDir

# 2. Build and start the edge agent docker compose stack
Write-Host "[2/2] Running Docker Compose build and up..." -ForegroundColor Yellow
docker compose -f "$scriptDir\docker-compose.yml" up -d --build

Write-Host "`nEverything is up and running!" -ForegroundColor Green
Write-Host "Verify logs with:" -ForegroundColor Gray
Write-Host "  docker compose -f edge-runtime/docker-compose.yml logs -f edge-agent" -ForegroundColor Gray
Write-Host "--------------------------------------------------------" -ForegroundColor Cyan
