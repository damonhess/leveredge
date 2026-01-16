FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aloy.py .

# Create data directory for SQLite
RUN mkdir -p /app/data

EXPOSE 8015

CMD ["uvicorn", "aloy:app", "--host", "0.0.0.0", "--port", "8015"]
