FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    pydantic

COPY varys.py .

EXPOSE 8112

CMD ["uvicorn", "varys:app", "--host", "0.0.0.0", "--port", "8112"]
