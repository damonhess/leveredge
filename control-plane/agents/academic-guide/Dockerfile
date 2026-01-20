FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY shared/ /opt/leveredge/control-plane/shared/

# Copy agent
COPY academic_guide.py .

EXPOSE 8231

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8231/health || exit 1

CMD ["uvicorn", "academic_guide:app", "--host", "0.0.0.0", "--port", "8231"]
