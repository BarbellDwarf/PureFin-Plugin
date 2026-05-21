FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (FFmpeg required for audio extraction)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    procps \
    python3-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade "setuptools<81" wheel \
    && pip install --no-cache-dir --no-build-isolation -r requirements.txt

COPY . .

RUN mkdir -p /app/models /tmp/processing

EXPOSE 3000

CMD ["python", "app.py"]
