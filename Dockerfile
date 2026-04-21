FROM python:3.12-slim

WORKDIR /app

# Install system deps for psycopg2 and audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY .env.example .env.example

# Audio files persist via Docker volume mounted at /app/backend/static/audio
RUN mkdir -p backend/static/audio

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
