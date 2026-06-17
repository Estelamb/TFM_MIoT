# Quick Start

## Prerequisites

- Docker Engine ≥ 24 with Docker Compose v2
- 8 GB RAM minimum

## Start the platform

```bash
cp .env.example .env
# Set SECRET_KEY: openssl rand -hex 32
docker compose up -d
```

| URL | Credentials |
|---|---|
| http://localhost:3000 | admin / aura2026 |
| http://localhost:8000/docs | — |
| http://localhost:9001 | aura / aura_dev |

## First deployment

1. **Register a device** → Devices → Register device
2. **Upload model** → Models → Upload model (`.pt`)
3. **Upload script** → Scripts → Upload script (`.py`)
4. **Deploy** → Deployments → New deployment
5. **Monitor** → Monitoring → live telemetry + inference results
