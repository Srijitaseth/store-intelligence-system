FROM python:3.12-slim

WORKDIR /app

COPY requirements-api.txt .

RUN pip install --upgrade pip && pip install --default-timeout=300 --no-cache-dir -r requirements-api.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]