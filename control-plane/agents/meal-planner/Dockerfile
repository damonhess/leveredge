FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create shared modules directory
RUN mkdir -p /opt/leveredge/control-plane/shared

# Copy shared modules (built with context from parent directory)
COPY shared/ /opt/leveredge/control-plane/shared/

COPY meal_planner.py .

EXPOSE 8102

CMD ["uvicorn", "meal_planner:app", "--host", "0.0.0.0", "--port", "8102"]
