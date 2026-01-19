FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create shared modules directory
RUN mkdir -p /opt/leveredge/shared

# Copy shared modules (built with context from parent directory)
COPY shared/ /opt/leveredge/shared/

COPY quaestor.py .

EXPOSE 8211

CMD ["uvicorn", "quaestor:app", "--host", "0.0.0.0", "--port", "8211"]
