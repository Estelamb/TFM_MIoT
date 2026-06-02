FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir aiomqtt httpx numpy psutil
COPY edge-runtime/aura_hw/ /app/aura_hw/
COPY edge-runtime/scripts/ /app/scripts/
COPY edge-runtime/agent.py /app/agent.py
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1
ENV AURA_DEVICE_ID=dev-device-001
ENV AURA_MQTT_HOST=mosquitto
CMD ["python", "agent.py"]
