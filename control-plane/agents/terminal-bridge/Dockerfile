FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck and docker CLI for docker commands
RUN apt-get update && apt-get install -y \
    curl \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    httpx \
    pydantic

COPY terminal_bridge.py .

EXPOSE 8251

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8251/health || exit 1

CMD ["uvicorn", "terminal_bridge:app", "--host", "0.0.0.0", "--port", "8251"]
