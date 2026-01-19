FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY adapters/ ./adapters/
COPY magnus.py .

EXPOSE 8017

CMD ["uvicorn", "magnus:app", "--host", "0.0.0.0", "--port", "8017"]
