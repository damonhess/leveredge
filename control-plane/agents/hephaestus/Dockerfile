FROM python:3.12-slim

WORKDIR /app

# Install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Configure git user
RUN git config --global user.email "hephaestus@leveredgeai.com" && \
    git config --global user.name "HEPHAESTUS"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY hephaestus_mcp_server.py .

# Expose port
EXPOSE 8011

# Run the server
CMD ["uvicorn", "hephaestus_mcp_server:app", "--host", "0.0.0.0", "--port", "8011"]
