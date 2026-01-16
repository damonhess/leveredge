FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY hephaestus_mcp_server.py .

# Expose port
EXPOSE 8011

# Run the server
CMD ["uvicorn", "hephaestus_mcp_server:app", "--host", "0.0.0.0", "--port", "8011"]
