FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY --from=shared /opt/leveredge/control-plane/shared /opt/leveredge/control-plane/shared

# Copy agent code
COPY scribe.py .

# Expose port
EXPOSE 8301

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8301/health || exit 1

# Run
CMD ["uvicorn", "scribe:app", "--host", "0.0.0.0", "--port", "8301"]
