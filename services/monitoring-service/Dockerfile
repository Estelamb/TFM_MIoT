FROM python:3.12-slim
WORKDIR /app
COPY services/monitoring-service/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt
COPY shared/ /app/shared/
COPY services/monitoring-service/app/ /app/app/
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1
EXPOSE 50056 9100
CMD ["python", "app/main.py"]
