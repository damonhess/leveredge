FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for image/document processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    libfreetype6 \
    libpng-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories
RUN mkdir -p /opt/leveredge/control-plane/shared
RUN mkdir -p /tmp/thalia_output
RUN mkdir -p /opt/leveredge/assets

# Copy shared modules (built with context from parent directory)
COPY shared/ /opt/leveredge/control-plane/shared/

COPY thalia.py .

# Set environment variables
ENV THALIA_OUTPUT_DIR=/tmp/thalia_output
ENV THALIA_ASSETS_DIR=/opt/leveredge/assets

EXPOSE 8032

CMD ["uvicorn", "thalia:app", "--host", "0.0.0.0", "--port", "8032"]
