# Architecture

## Service topology

```
Frontend (Next.js :3000)
    │ HTTP + JWT
    ▼
API Gateway (:8000)
    │ gRPC
    ├─▶ registry-service       (:50051)  PostgreSQL + MinIO
    ├─▶ mlops-service          (:50052)  MinIO + Docker socket
    └─▶ edge-connector-service (:50053)  PostgreSQL + MongoDB + MinIO + MQTT + Prometheus
```

## MQTT topics

| Topic | Direction | Purpose |
|---|---|---|
| `device/{id}/commands` | Cloud → Edge | Send deploy/update commands |
| `device/{id}/events` | Edge → Cloud | Acknowledge deploy or report failure |
| `device/{id}/telemetry` | Edge → Cloud | CPU, RAM, active model ID |
| `device/{id}/inference` | Edge → Cloud | Inference results (JSON) |

## Database layout

**PostgreSQL** — relational entities:
`devices` · `models` · `scripts` · `deployments`

**MongoDB** — time-series:
`device_states` (upsert) · `inference_results` (append-only)

**MinIO** — binary artefacts:
`models/` · `compiled/` · `scripts/`
