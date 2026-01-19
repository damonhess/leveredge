FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    anthropic \
    pydantic

COPY asclepius.py .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true

EXPOSE 8024

CMD ["uvicorn", "asclepius:app", "--host", "0.0.0.0", "--port", "8024"]
