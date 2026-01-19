FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    anthropic \
    pydantic

# Create shared modules directory
RUN mkdir -p /opt/leveredge/control-plane/shared

COPY plutus.py .

EXPOSE 8207

CMD ["uvicorn", "plutus:app", "--host", "0.0.0.0", "--port", "8207"]
