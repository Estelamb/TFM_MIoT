# Running AURA Platform

---

## Prerequisites

- Docker Engine ≥ 24 with Docker Compose v2
- 8 GB RAM minimum for the full stack
- Ports available: `3000`, `8000`, `1883`, `5432`, `9000`, `9001`, `27017`, `50051–50056`, `9100`

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
docker compose logs -f monitoring-service
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

## Run the edge agent on a physical device

Install dependencies (Hailo example):

```bash
pip install aiomqtt httpx numpy psutil
# HailoRT SDK must already be installed system-wide
```

Copy the `edge-runtime/` folder to the device, then:

```bash
AURA_DEVICE_ID=<your-device-id> \
AURA_MQTT_HOST=<platform-ip> \
AURA_MQTT_PORT=1883 \
AURA_HARDWARE_TYPE=hailo8 \
AURA_TELEMETRY_INTERVAL=10 \
python agent.py
```

The agent auto-detects hardware if `AURA_HARDWARE_TYPE` is not set.

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
| device-service | gRPC | 50051 | Internal |
| ai-service | gRPC | 50052 | Internal |
| script-service | gRPC | 50053 | Internal |
| compilation-service | gRPC | 50054 | Internal |
| deployment-service | gRPC | 50055 | Internal |
| monitoring-service | gRPC | 50056 | Internal |
| Prometheus metrics | HTTP | 9100 | monitoring-service |
| PostgreSQL | TCP | 5432 | |
| MongoDB | TCP | 27017 | |
