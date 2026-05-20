FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Ensure deterministic PyTorch behavior and silence CuBLAS warnings
ENV CUBLAS_WORKSPACE_CONFIG=:4096:8

# Install ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/processing

EXPOSE 3000

CMD ["python3", "app.py"]
