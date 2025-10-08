FROM python:3.11-slim

# Ensure deterministic PyTorch behavior and silence CuBLAS warnings
ENV CUBLAS_WORKSPACE_CONFIG=:4096:8

# Build arg to enable CUDA-capable dependencies inside the image
ARG BUILD_WITH_CUDA=0
ENV BUILD_WITH_CUDA=${BUILD_WITH_CUDA}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
        && if [ "$BUILD_WITH_CUDA" = "1" ]; then \
                 echo "Installing NVIDIA CUDA libraries for TF 2.15 (without TensorRT)..." && \
                 pip install --no-cache-dir \
                     nvidia-cuda-runtime-cu12==12.2.140 \
                     nvidia-cudnn-cu12==8.9.4.25 \
                     nvidia-cublas-cu12==12.2.5.6 \
                     nvidia-cufft-cu12==11.0.8.103 \
                     nvidia-curand-cu12==10.3.3.141 \
                     nvidia-cusolver-cu12==11.5.2.141 \
                     nvidia-cusparse-cu12==12.1.2.141 \
                     nvidia-nccl-cu12==2.16.5 \
                     nvidia-nvjitlink-cu12==12.2.140 \
                     nvidia-cuda-nvrtc-cu12==12.2.140 \
                     nvidia-cuda-cupti-cu12==12.2.142; \
             fi

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/models /tmp/processing

# Copy model downloader script (will be added to volume mount)

# Create startup script 
RUN echo '#!/bin/bash\n\
echo "Starting NSFW detector service..."\n\
echo "Models should be pre-downloaded to /app/models volume"\n\
exec python app.py' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 3000

CMD ["/app/start.sh"]
