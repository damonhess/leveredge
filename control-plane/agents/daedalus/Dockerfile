FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY daedalus.py .
COPY __init__.py .

# Copy shared modules if available
RUN mkdir -p /opt/leveredge/control-plane/shared

# Expose port
EXPOSE 8026

# Run the application
CMD ["python", "daedalus.py"]
