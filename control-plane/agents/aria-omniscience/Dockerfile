FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aria_omniscience.py .

EXPOSE 8112

CMD ["uvicorn", "aria_omniscience:app", "--host", "0.0.0.0", "--port", "8112"]
