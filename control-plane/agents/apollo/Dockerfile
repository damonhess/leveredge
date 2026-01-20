FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck AND docker CLI for container operations
RUN apt-get update && apt-get install -y \
    curl \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install docker compose v2 plugin manually
RUN mkdir -p /usr/local/lib/docker/cli-plugins \
    && curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose \
    && chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY shared/ /opt/leveredge/control-plane/shared/

# Copy all Apollo modules
COPY apollo.py .
COPY service_registry.py .
COPY deployment_executor.py .
COPY migrations.py .

EXPOSE 8234

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8234/health || exit 1

CMD ["uvicorn", "apollo:app", "--host", "0.0.0.0", "--port", "8234"]
