#!/bin/bash
# AURA Run Edge — Linux Startup Script
# ==========================================
# Launches the Hardware Daemon in the background and runs the Docker Compose
# stack for the local Edge Agent.

# Resolve script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Load environment variables from .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo "Loading configuration from $SCRIPT_DIR/.env..."
    set -a
    . "$SCRIPT_DIR/.env"
    set +a
fi

# Automatically configure docker network variables based on AURA_HARDWARE_TYPE
if [ "$AURA_HARDWARE_TYPE" = "simulated" ]; then
    echo "Simulated mode detected. Activating aura_aura-net external network..."
    export AURA_DOCKER_NETWORK="aura_aura-net"
    export AURA_DOCKER_NETWORK_EXTERNAL="true"
else
    echo "Physical/device hardware mode detected. Using local bridge network..."
    export AURA_DOCKER_NETWORK="edge-net"
    export AURA_DOCKER_NETWORK_EXTERNAL="false"
fi

echo "--------------------------------------------------------"
echo " Starting AURA Edge Stack (Daemon + Container) "
echo "--------------------------------------------------------"

# 1. Start the Hardware Daemon in the background
echo "[1/2] Starting Hardware Daemon in background..."
nohup python3 "$SCRIPT_DIR/hardware_daemon.py" > /dev/null 2>&1 &
DAEMON_PID=$!
disown $DAEMON_PID
echo "Hardware Daemon started with PID: $DAEMON_PID"

# 2. Build and start the edge agent docker compose stack
echo "[2/2] Running Docker Compose build and up..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d --build

echo ""
echo "Everything is up and running!"
echo "Verify logs with:"
echo "  docker compose -f edge-runtime/docker-compose.yml logs -f edge-agent"
echo "--------------------------------------------------------"
