FROM python:3.11-slim

# Build arg to enable CUDA-capable dependencies inside the image
ARG BUILD_WITH_CUDA=0
ENV BUILD_WITH_CUDA=${BUILD_WITH_CUDA}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
        && if [ "$BUILD_WITH_CUDA" = "1" ]; then \
                 echo "Installing PyTorch with CUDA 12.4 support for NVIDIA GPUs (10 series to 50 series)..." && \
                 pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu124 torch==2.5.1 torchvision==0.20.1; \
             fi

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/models /tmp/processing

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting content classifier service with PyTorch..."\n\
echo "Models should be pre-downloaded to /app/models volume"\n\
exec python app_pytorch.py' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 3000

CMD ["/app/start.sh"]
