FROM python:3.11-slim

WORKDIR /app

# Install git for commit scanning (before pip so it's cached better)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY varys.py .

EXPOSE 8020

CMD ["uvicorn", "varys:app", "--host", "0.0.0.0", "--port", "8020"]
