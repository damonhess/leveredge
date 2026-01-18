FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aria_chat.py .
COPY prompts/ ./prompts/

EXPOSE 8113

CMD ["uvicorn", "aria_chat:app", "--host", "0.0.0.0", "--port", "8113"]
