FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    httpx \
    pydantic

COPY claude_bridge.py .

EXPOSE 8250

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8250/health || exit 1

CMD ["uvicorn", "claude_bridge:app", "--host", "0.0.0.0", "--port", "8250"]
