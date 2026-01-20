FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    pydantic \
    docker

COPY varys.py .

EXPOSE 8112

CMD ["uvicorn", "varys:app", "--host", "0.0.0.0", "--port", "8112"]
