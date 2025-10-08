# GPU Acceleration Setup

This document explains how to use GPU acceleration with the PureFin AI services for significantly faster content analysis.

## Prerequisites

### NVIDIA GPU Setup

1. **NVIDIA GPU with CUDA Support**
   - NVIDIA GPU (GTX 10-series or newer recommended)
   - At least 4GB VRAM for basic models
   - 8GB+ VRAM recommended for optimal performance

2. **NVIDIA Driver**
   - Install the latest NVIDIA GPU drivers for your operating system
   - Windows: Download from [NVIDIA Driver Downloads](https://www.nvidia.com/Download/index.aspx)
   - Linux: Use package manager or NVIDIA's official installer

3. **NVIDIA Container Toolkit** (Docker GPU Support)
   
   **Windows with WSL2:**
   ```powershell
   # Ensure WSL2 is installed and updated
   wsl --update
   
   # Install NVIDIA CUDA on WSL2
   # Follow: https://docs.nvidia.com/cuda/wsl-user-guide/index.html
   ```

   **Linux:**
   ```bash
   # Add NVIDIA package repositories
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
     sudo tee /etc/apt/sources.list.d/nvidia-docker.list

   # Install NVIDIA Container Toolkit
   sudo apt-get update
   sudo apt-get install -y nvidia-container-toolkit

   # Restart Docker
   sudo systemctl restart docker
   ```

4. **Verify GPU Access**
   ```bash
   # Test NVIDIA Docker runtime
   docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
   ```
   
   If this shows your GPU information, you're ready to use GPU acceleration!

## Usage

### Using GPU-Accelerated Services

Use the GPU-specific Docker Compose file:

```powershell
# Start services with GPU acceleration
cd ai-services
docker-compose -f docker-compose.gpu.yml up -d

# View logs to confirm GPU usage
docker-compose -f docker-compose.gpu.yml logs -f

# Stop services
docker-compose -f docker-compose.gpu.yml down
```

### Fallback to CPU (No GPU Available)

If you don't have a GPU or NVIDIA Docker runtime, use the standard compose file:

```powershell
cd ai-services
docker-compose up -d
```

## Performance Comparison

### With GPU Acceleration
- **Scene Analysis**: ~2-5 seconds per scene
- **Frame Analysis**: ~50-100ms per frame
- **Full Movie Analysis**: 5-15 minutes for a 2-hour movie

### CPU Only
- **Scene Analysis**: ~5-15 seconds per scene
- **Frame Analysis**: ~200-500ms per frame
- **Full Movie Analysis**: 30-60 minutes for a 2-hour movie

## Model Configuration for GPU

The AI services will automatically detect GPU availability and adjust accordingly. You can explicitly control GPU usage with environment variables:

```yaml
environment:
  - USE_GPU=1                    # Enable GPU if available
  - CUDA_VISIBLE_DEVICES=0       # Use first GPU (0-indexed)
  - TF_FORCE_GPU_ALLOW_GROWTH=1  # Allow dynamic GPU memory allocation
```

### Multiple GPUs

If you have multiple GPUs, you can distribute services across them:

```yaml
# docker-compose.gpu.yml modifications
services:
  nsfw-detector:
    environment:
      - CUDA_VISIBLE_DEVICES=0    # Use GPU 0
  
  content-classifier:
    environment:
      - CUDA_VISIBLE_DEVICES=1    # Use GPU 1
```

## Troubleshooting

### GPU Not Detected

**Check NVIDIA Docker Runtime:**
```bash
docker info | grep -i runtime
```

Should show `nvidia` in the list of runtimes.

**Check GPU in Container:**
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Out of Memory Errors

If you get CUDA out of memory errors:

1. **Reduce batch size** in model configuration
2. **Use smaller models** or lower resolution
3. **Limit GPU memory** per service:
   ```yaml
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             count: 1
             capabilities: [gpu]
       limits:
         memory: 4G  # Limit total memory
   ```

### Services Crashing on Startup

1. Check Docker logs:
   ```powershell
   docker-compose -f docker-compose.gpu.yml logs nsfw-detector
   ```

2. Verify CUDA version compatibility with your GPU driver

3. Try CPU-only mode first to isolate GPU issues

## Model Downloads

Some AI models require downloading before first use. GPU-accelerated models may be different from CPU versions:

```powershell
# Download models (example)
cd ai-services
python scripts/download_models.py --gpu

# Or use the model downloader service
docker-compose -f docker-compose.gpu.yml run --rm nsfw-detector python download_models.py
```

## Monitoring GPU Usage

### Real-time Monitoring
```bash
# Watch GPU usage
watch -n 1 nvidia-smi

# Or use container-specific monitoring
docker exec -it nsfw-detector-gpu nvidia-smi
```

### Check Service Logs for GPU Confirmation
```bash
docker-compose -f docker-compose.gpu.yml logs | grep -i "gpu\|cuda"
```

You should see messages like:
```
nsfw-detector     | INFO: GPU detected: NVIDIA GeForce RTX 3080
nsfw-detector     | INFO: Using CUDA device 0
```

## Best Practices

1. **Warm-up Period**: First few analyses may be slower as models initialize on GPU
2. **Batch Processing**: Process multiple videos in sequence for better GPU utilization
3. **Memory Management**: Monitor GPU memory usage and adjust batch sizes accordingly
4. **Mixed Precision**: Use FP16 (half precision) for faster inference with minimal accuracy loss
5. **Model Caching**: Keep models loaded in GPU memory between requests

## Support

For issues related to:
- **GPU Setup**: Consult NVIDIA Docker documentation
- **Performance**: Check model configuration and GPU memory
- **Compatibility**: Verify CUDA version matches your GPU driver

## References

- [NVIDIA Container Toolkit Documentation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/overview.html)
- [Docker Compose GPU Support](https://docs.docker.com/compose/gpu-support/)
- [CUDA Compatibility Guide](https://docs.nvidia.com/deploy/cuda-compatibility/)
