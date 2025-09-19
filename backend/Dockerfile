FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app

RUN pip install --upgrade pip && pip install .

ENV STORAGE_ROOT=/app/storage \
    TEMP_DIR=/app/storage/tmp

RUN mkdir -p /app/storage/tmp

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
