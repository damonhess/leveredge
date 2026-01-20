FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY ../../shared /app/shared

# Copy agent code
COPY aria_memory.py .

# Set Python path
ENV PYTHONPATH=/app:/app/shared

# Expose port
EXPOSE 8114

# Run the service
CMD ["python", "aria_memory.py"]
