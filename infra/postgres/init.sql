-- =============================================================================
-- AURA Platform PoC — Schema
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Dispositivos edge
CREATE TABLE IF NOT EXISTS devices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    hardware_type   TEXT NOT NULL,  -- hailo8 | hailo8l | rpi_ai_cam | rpi | jetson_orin_nano
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'offline',  -- online | offline
    last_seen_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Modelos subidos (pt original + compilado)
CREATE TABLE IF NOT EXISTS models (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    description     TEXT,
    source_key      TEXT NOT NULL,       -- MinIO: models/<id>/source.pt
    source_sha256   TEXT NOT NULL,
    compiled_key    TEXT,                -- MinIO: compiled/<id>/model.hef  (null hasta compilar)
    compiled_sha256 TEXT,
    hardware_type   TEXT,                -- para qué hw está compilado
    compile_status  TEXT NOT NULL DEFAULT 'pending',  -- pending | compiling | ready | failed
    compile_error   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Scripts (pre/post inference)
CREATE TABLE IF NOT EXISTS scripts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    description     TEXT,
    script_key      TEXT NOT NULL,       -- MinIO: scripts/<id>/script.py
    script_sha256   TEXT NOT NULL,
    hardware_type   TEXT NOT NULL,       -- para qué hardware está pensado
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Despliegues
CREATE TABLE IF NOT EXISTS deployments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id       UUID NOT NULL REFERENCES devices(id),
    model_id        UUID NOT NULL REFERENCES models(id),
    script_id       UUID NOT NULL REFERENCES scripts(id),
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending | sent | running | failed
    sent_at         TIMESTAMPTZ,
    running_at      TIMESTAMPTZ,
    error_msg       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deployments_device ON deployments(device_id);
CREATE INDEX IF NOT EXISTS idx_deployments_status ON deployments(status);
CREATE INDEX IF NOT EXISTS idx_models_compile_status ON models(compile_status);
