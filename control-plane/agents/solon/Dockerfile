FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create shared modules directory
RUN mkdir -p /opt/leveredge/shared

# Copy shared modules (built with context from parent directory)
COPY shared/ /opt/leveredge/shared/

COPY solon.py .

EXPOSE 8210

CMD ["uvicorn", "solon:app", "--host", "0.0.0.0", "--port", "8210"]
