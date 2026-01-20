FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create shared modules directory
RUN mkdir -p /opt/leveredge/control-plane/shared

# Copy shared modules (built with context from parent directory)
COPY shared/ /opt/leveredge/control-plane/shared/

COPY nutritionist.py .

EXPOSE 8232

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8232/health || exit 1

CMD ["uvicorn", "nutritionist:app", "--host", "0.0.0.0", "--port", "8232"]
