FROM jrottenberg/ffmpeg:6.1-nvidia

# Install Python 3.11 and pip
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/processing

EXPOSE 3000

# Override ffmpeg ENTRYPOINT from base image
ENTRYPOINT []
CMD ["python3", "app.py"]
