FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    anthropic \
    pydantic

COPY steward.py .

EXPOSE 8220

CMD ["uvicorn", "steward:app", "--host", "0.0.0.0", "--port", "8220"]
