FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    pydantic

COPY librarian.py .

EXPOSE 8050

CMD ["uvicorn", "librarian:app", "--host", "0.0.0.0", "--port", "8050"]
