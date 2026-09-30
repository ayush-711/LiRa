FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (build tools for argon2-cffi/asyncpg wheels are usually not needed,
# but curl is handy for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh && mkdir -p /data/uploads

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
