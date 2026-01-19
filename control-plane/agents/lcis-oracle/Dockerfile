FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    pydantic

COPY oracle.py .

EXPOSE 8052

CMD ["uvicorn", "oracle:app", "--host", "0.0.0.0", "--port", "8052"]
