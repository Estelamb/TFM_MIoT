FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    aiomqtt==2.3.0 \
    httpx==0.27.2 \
    numpy \
    psutil==6.0.0 \
    pyyaml>=6.0

# ── Application source ───────────────────────────────────────────────────────
COPY edge-runtime/aura_hw/   /app/aura_hw/
COPY edge-runtime/pal/       /app/pal/
COPY edge-runtime/scripts/   /app/scripts/
COPY edge-runtime/config/    /app/config/
COPY edge-runtime/agent.py   /app/agent.py

# ── Runtime environment ──────────────────────────────────────────────────────
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    AURA_DEVICE_ID=dev-device-001 \
    AURA_MQTT_HOST=mosquitto \
    AURA_WORK_DIR=/tmp/aura \
    AURA_LOG_LEVEL=INFO

CMD ["python", "agent.py"]
