FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    pydantic

COPY littlefinger.py .

EXPOSE 8020

CMD ["uvicorn", "littlefinger:app", "--host", "0.0.0.0", "--port", "8020"]
