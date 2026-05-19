FROM python:3.11-slim

# Ensure deterministic PyTorch behavior and silence CuBLAS warnings
ENV CUBLAS_WORKSPACE_CONFIG=:4096:8

# Build args to enable GPU-capable dependencies inside the image.
# Only one should be set to "1" at build time.
ARG BUILD_WITH_CUDA=0
ARG BUILD_WITH_ROCM=0
ENV BUILD_WITH_CUDA=${BUILD_WITH_CUDA}
ENV BUILD_WITH_ROCM=${BUILD_WITH_ROCM}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages.
# For CPU-only: torch is installed from requirements.txt (default PyPI wheels).
# For CUDA:     reinstall torch from the CUDA 12.4 index.
# For ROCm/AMD: reinstall torch from the ROCm 6.2 index (HIP device appears as "cuda" to PyTorch).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
        && if [ "$BUILD_WITH_CUDA" = "1" ]; then \
                 echo "Installing PyTorch with CUDA 12.4 support..." && \
                 pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu124 torch==2.5.1 torchvision==0.20.1; \
             elif [ "$BUILD_WITH_ROCM" = "1" ]; then \
                 echo "Installing PyTorch with ROCm 6.2 support (AMD GPU)..." && \
                 pip install --no-cache-dir --index-url https://download.pytorch.org/whl/rocm6.2 torch==2.5.1 torchvision==0.20.1; \
             fi

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/models /tmp/processing

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting violence-detector service..."\n\
echo "Model source: ${VIOLENCE_MODEL_ID:-jaranohaal/vit-base-violence-detection}"\n\
exec python app.py' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 3000

CMD ["/app/start.sh"]
