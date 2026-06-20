#!/bin/bash
# AURA Run Edge — Linux Startup Script
# ==========================================
# Launches the Hardware Daemon in the background and runs the Docker Compose
# stack for the local Edge Agent.

# Resolve script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "--------------------------------------------------------"
echo " Starting AURA Edge Stack (Daemon + Container) "
echo "--------------------------------------------------------"

# 1. Start the Hardware Daemon in the background
echo "[1/2] Starting Hardware Daemon in background..."
python3 "$SCRIPT_DIR/hardware_daemon.py" > /dev/null 2>&1 &
DAEMON_PID=$!
echo "Hardware Daemon started with PID: $DAEMON_PID"

# 2. Build and start the edge agent docker compose stack
echo "[2/2] Running Docker Compose build and up..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d --build

echo ""
echo "Everything is up and running!"
echo "Verify logs with:"
echo "  docker compose -f edge-runtime/docker-compose.yml logs -f edge-agent"
echo "--------------------------------------------------------"
