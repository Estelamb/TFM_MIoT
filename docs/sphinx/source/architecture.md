# Architecture

## Service topology

```
Frontend (Next.js :3000)
    │ HTTP + JWT
    ▼
API Gateway (:8000)
    │ gRPC
    ├─▶ device-service      (:50051)  PostgreSQL
    ├─▶ ai-service          (:50052)  PostgreSQL + MinIO
    ├─▶ script-service      (:50053)  PostgreSQL + MinIO
    ├─▶ compilation-service (:50054)  MinIO + Docker socket
    ├─▶ deployment-service  (:50055)  PostgreSQL + MinIO + MQTT
    └─▶ monitoring-service  (:50056)  MongoDB + MQTT + Prometheus
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
