FROM python:3.11-slim

ENV CUBLAS_WORKSPACE_CONFIG=:4096:8

ARG BUILD_WITH_CUDA=0
ARG BUILD_WITH_ROCM=0
ENV BUILD_WITH_CUDA=${BUILD_WITH_CUDA}
ENV BUILD_WITH_ROCM=${BUILD_WITH_ROCM}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
        && if [ "$BUILD_WITH_CUDA" = "1" ]; then \
                 echo "Installing PyTorch with CUDA 12.4 support..." && \
                 pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu124 torch==2.5.1 torchvision==0.20.1; \
             elif [ "$BUILD_WITH_ROCM" = "1" ]; then \
                 echo "Installing PyTorch with ROCm 6.2 support (AMD GPU)..." && \
                 pip install --no-cache-dir --index-url https://download.pytorch.org/whl/rocm6.2 torch==2.5.1 torchvision==0.20.1; \
             fi

COPY . .

RUN mkdir -p /app/models /tmp/processing

RUN echo '#!/bin/bash\n\
echo "Starting NSFW detector service..."\n\
echo "Model: ${NSFW_MODEL_ID:-AdamCodd/vit-base-nsfw-detector}"\n\
exec python app.py' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 3000
CMD ["/app/start.sh"]
