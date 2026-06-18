# Running AURA Platform

---

## Prerequisites

- Docker Engine ≥ 24 with Docker Compose v2
- 8 GB RAM minimum for the full stack
- Ports available: `3000`, `8000`, `1883`, `5432`, `9000`, `9001`, `27017`, `50051–50053`, `9100`

---

## Quick start — full stack

### 1. Configure environment

```bash
cp .env.example .env
```

Open `.env` and set a real `SECRET_KEY`:

```bash
openssl rand -hex 32
# paste the output as SECRET_KEY in .env
```

All other defaults work out of the box for local development.

### 2. Start the platform

```bash
docker compose up -d
```

First run takes 3–5 minutes to build all images. This starts the core platform services.

### 3. Access the platform

| Service | URL | Credentials |
|---|---|---|
| Frontend | http://localhost:3000 | `admin` / `aura2026` |
| API docs (Swagger) | http://localhost:8000/docs | Login first at `/auth/token` |
| MinIO console | http://localhost:9001 | `aura` / `aura_dev` |
| Prometheus metrics | http://localhost:9100/metrics | — |

### 4. Verify services are healthy

```bash
docker compose ps
docker compose logs -f                  # all services
docker compose logs -f api-gateway      # single service
docker compose logs -f edge-connector-service
```

---

## Demo mode

The frontend includes a **Demo Mode** toggle (bottom-right corner). When enabled, the UI displays mock data so you can explore the interface without a running backend. Toggle it anytime — switching back to Real Mode clears the cache and fetches live data.

---

## Regenerate gRPC stubs

Only needed if you modify any `.proto` file in `shared/proto/`.

```bash
pip install grpcio-tools

python -m grpc_tools.protoc \
  -I shared/proto \
  --python_out=shared/proto_gen \
  --grpc_python_out=shared/proto_gen \
  shared/proto/*.proto

# Fix generated imports
for f in shared/proto_gen/*_pb2_grpc.py; do
  sed -i 's/^import \(.*_pb2\)/from shared.proto_gen import \1/' "$f"
done
```

---

## Run the edge runtime (Agent)

The AURA edge agent runs on the edge device or locally for testing using Docker.

### Running with Docker Compose

Depending on where you are running the agent:

#### Case A: Running locally on the same host as the platform (Testing)
1. **Verify network**: The edge agent container connects to the main platform network (`aura_aura-net`). Ensure you have started the core platform stack first (`docker compose up -d` in the root).
2. **Start the agent**:
   ```bash
   docker compose -f edge-runtime/docker-compose.yml up -d
   ```

#### Case B: Running on a physical edge device
Since the AURA platform runs on a different host, the `aura_aura-net` network does not exist on the device, and the agent must connect over the network.

1. **Modify `edge-runtime/docker-compose.yml`**:
   - Change `AURA_MQTT_HOST` from `mosquitto` to the actual IP address or domain of the platform server (e.g., `192.168.1.100`).
   - Remove or comment out the `networks` block under the `edge-agent` service and the global `networks` section at the bottom of the file so Docker uses the default bridge network.
2. **Start the Host Hardware Daemon** (needed for native Pi camera access):
   - Run the lightweight camera daemon natively on your physical Pi's host OS:
     ```bash
     python3 edge-runtime/hardware_daemon.py
     ```
   - The edge agent container will automatically detect and pull raw frames from this host daemon on port `8008` (using the container bridge gateway route).
3. **Start the agent**:
   ```bash
   docker compose -f docker-compose.yml up -d
   ```

---

### Verify agent logs
Regardless of the case, you can monitor the agent via logs:
```bash
docker compose -f edge-runtime/docker-compose.yml logs -f edge-agent
```

---

### Configuration Parameters Reference

The agent reads configuration from `edge-runtime/config/device_config.yaml`. Any configuration key can be overridden using environment variables in the `docker-compose.yml` file:

| Environment Variable | Default (YAML) | Description |
|---|---|---|
| `AURA_DEVICE_ID` | `IoT-Edge-Device-01` | Unique device identifier. Must match the Device ID in the AURA web console. |
| `AURA_MQTT_HOST` | `localhost` | MQTT Broker host IP/domain. |
| `AURA_MQTT_PORT` | `1883` | MQTT Broker port. |
| `AURA_HARDWARE_TYPE` | `auto` | Edge hardware profile: `hailo8`, `hailo8l`, `rpi`, `rpi_ai_cam`, `jetson_orin_nano`, `simulated`, or `auto` (auto-detect). |
| `AURA_TELEMETRY_INTERVAL`| `10` | Frequency (in seconds) to send CPU/RAM telemetry. |
| `AURA_INFERENCE_INTERVAL`| `0.1` | Loop interval (in seconds) for model inference. |
| `AURA_WORK_DIR` | `/tmp/aura` | Temporary folder for OTA updates and pipeline work. |
| `AURA_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `AURA_COORDINATES` | `[-3.6288, 40.3899]` | GPS coordinates in JSON array style `[longitude, latitude]`. |

---

## Useful commands

```bash
# Rebuild and restart a single service after code change
docker compose up -d --build api-gateway

# PostgreSQL shell
docker compose exec postgres psql -U aura -d aura

# MongoDB shell
docker compose exec mongodb mongosh -u aura -p aura_dev aura

# Subscribe to all MQTT topics (debug)
docker compose exec mosquitto mosquitto_sub -h localhost -t '#' -v

# Check Prometheus metrics
curl http://localhost:9100/metrics | grep aura_device

# Stop everything (keep data volumes)
docker compose down

# Full reset including data
docker compose down -v
```

---

## Service ports reference

| Service | Protocol | Port | Notes |
|---|---|---|---|
| Frontend (Next.js) | HTTP | 3000 | |
| API Gateway | HTTP | 8000 | Swagger at `/docs` |
| MinIO S3 API | HTTP | 9000 | |
| MinIO Console | HTTP | 9001 | |
| MQTT (anonymous) | TCP | 1883 | No TLS in PoC |
| registry-service | gRPC | 50051 | Internal |
| mlops-service | gRPC | 50052 | Internal |
| edge-connector-service | gRPC | 50053 | Internal |
| Prometheus metrics | HTTP | 9100 | edge-connector-service |
| PostgreSQL | TCP | 5432 | |
| MongoDB | TCP | 27017 | |
