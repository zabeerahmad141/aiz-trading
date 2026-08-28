FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos '' mluser && chown -R mluser /app

HEALTHCHECK --interval=60s --timeout=15s --start-period=30s --retries=3 \
  CMD python -c "import os, redis; r=redis.Redis(host='redis', password=os.getenv('REDIS_PASSWORD')); r.ping()" || exit 1

CMD ["sh", "-c", "chown -R mluser:mluser /app/models && exec su mluser -s /bin/sh -c 'python -m src.main'"]
