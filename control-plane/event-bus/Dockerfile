FROM python:3.12-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn pydantic

# Copy application
COPY event_bus.py .

# Default database path (can be overridden with volume mount)
ENV EVENT_BUS_DB_PATH=/data/events.db

EXPOSE 8099

CMD ["uvicorn", "event_bus:app", "--host", "0.0.0.0", "--port", "8099"]
