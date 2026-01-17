FROM python:3.11-slim

WORKDIR /app

# Install FFmpeg for video processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create shared modules directory
RUN mkdir -p /opt/leveredge/control-plane/shared

# Copy shared modules (built with context from parent directory)
COPY shared/ /opt/leveredge/control-plane/shared/

# Create media storage directories
RUN mkdir -p /opt/leveredge/media/images \
    /opt/leveredge/media/videos \
    /opt/leveredge/media/audio \
    /opt/leveredge/media/thumbnails

# Copy application
COPY erato.py .

EXPOSE 8033

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8033/health')" || exit 1

CMD ["uvicorn", "erato:app", "--host", "0.0.0.0", "--port", "8033"]
