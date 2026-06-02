FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY services/ai-service/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt
COPY shared/ /app/shared/
COPY services/ai-service/app/ /app/app/
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1
EXPOSE 50052
CMD ["python", "app/main.py"]
