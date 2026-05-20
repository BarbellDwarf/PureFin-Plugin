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
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d

# View logs to confirm GPU usage
docker compose -f docker-compose.yml -f docker-compose.gpu.yml logs -f

# Stop services
docker compose -f docker-compose.yml -f docker-compose.gpu.yml down
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
  
  violence-detector:
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
   docker compose -f docker-compose.yml -f docker-compose.gpu.yml logs nsfw-detector
   ```

2. Verify CUDA version compatibility with your GPU driver

3. Try CPU-only mode first to isolate GPU issues

## Model Downloads

Some AI models require downloading before first use. GPU-accelerated models may be different from CPU versions:

```powershell
# Download models (example)
cd ai-services
python scripts/bootstrap_models.py --models-dir ./models

# Or use the model downloader service
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm violence-detector python -c "from transformers import AutoImageProcessor, AutoModelForImageClassification; AutoImageProcessor.from_pretrained('jaranohaal/vit-base-violence-detection'); AutoModelForImageClassification.from_pretrained('jaranohaal/vit-base-violence-detection'); print('violence model ready')"
```

## Monitoring GPU Usage

### Real-time Monitoring
```bash
# Watch GPU usage
watch -n 1 nvidia-smi

# Or use container-specific monitoring
docker exec -it violence-detector nvidia-smi
```

### Check Service Logs for GPU Confirmation
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml logs | grep -i "gpu\|cuda"
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

---

## AMD GPU on Windows (WSL2 Docker)

AMD GPUs on Windows use ROCm via WSL2 device passthrough (typically `/dev/dxg`). PyTorch ROCm uses a CUDA API shim so `torch.cuda.is_available()` returns `True` when a ROCm build is used — no code changes are needed.

### Requirements

- **AMD GPU driver 22.40+** — Adrenalin Edition 22.40 or later (provides WSL2 ROCm support)
- **ROCm 5.7+ compatible GPU** — RDNA 1/2/3 (RX 5000/6000/7000) or Vega 10+
- **Docker Desktop 4.22+** with WSL2 backend enabled

### Setup steps

1. **Check your AMD GPU** (run in PowerShell):
   ```powershell
   wmic path win32_VideoController get name
   ```

2. **Verify WSL2 exposes the GPU device** (run in a WSL terminal):
   ```bash
   ls /dev/dxg
   ```
   This file must exist for Docker Desktop WSL2 GPU passthrough.

3. **(Optional) Check native ROCm nodes** (WSL terminal):
   ```bash
   ls /dev/kfd /dev/dri/renderD128
   ```
   On some WSL ROCm setups these nodes may be missing while `/dev/dxg` still works for containers.

4. **Run services with AMD GPU acceleration** (installs ROCm 6.2 PyTorch automatically on first build):
   ```powershell
   cd ai-services
   docker compose -f docker-compose.yml -f docker-compose.amd.yml up --build -d
   ```
   The AMD overlay passes `BUILD_WITH_ROCM=1` to all PyTorch-based services
   (`scene-analyzer`, `violence-detector`, and optional `content-classifier`), replacing
   default wheels with ROCm 6.2 wheels. First build takes longer due to ROCm wheel downloads.

5. **If you are on native Linux ROCm (non-WSL), override the AMD device path**:
   ```powershell
   $env:AMD_GPU_DEVICE="/dev/kfd"
   docker compose -f docker-compose.yml -f docker-compose.amd.yml up --build -d
   ```

6. **Run the E2E profile test** (optional, validates all three model profiles on your GPU):
   ```powershell
   # From the repository root:
   .\test-scripts\Test-E2E-AMD.ps1

   # Or supply a short test video for live analysis:
   .\test-scripts\Test-E2E-AMD.ps1 -TestVideoPath "D:\Media\Movies\SomeShortClip.mp4"
   ```

7. **If you get "device not found" errors** when starting AMD services, verify `/dev/dxg` exists in both `Ubuntu` and `docker-desktop` WSL distros. If unavailable, fall back to CPU mode:
   ```powershell
   docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d
   ```

### GFX version overrides

Some AMD GPUs require an environment variable to bypass ROCm GFX version checks. Edit `docker-compose.amd.yml` and uncomment `HSA_OVERRIDE_GFX_VERSION`:

| GPU series          | Value to try  |
|---------------------|---------------|
| RX 7000 (RDNA 3)    | `11.0.0`      |
| RX 6000 (RDNA 2)    | `10.3.0`      |
| RX 5000 (RDNA 1)    | `9.0.0`       |
| Vega 10 / Vega 20   | `9.0.6`       |

Example (in `docker-compose.amd.yml`):
```yaml
environment:
  - HSA_OVERRIDE_GFX_VERSION=10.3.0
```

### Limitations

- **nsfw-detector (TensorFlow) runs CPU-only in AMD mode.** TensorFlow ROCm requires a separate `tensorflow-rocm` build with a different Docker base image. This is not included in the AMD overlay. The service will still work — it just uses the CPU.
- **For CPU-only testing** (no GPU needed), use the base compose file with no overlay:
  ```powershell
  docker compose up --build
  ```
- **ROC_ENABLE_PRE_VEGA**: If you have a pre-Vega AMD GPU and ROCm refuses to initialise, uncomment `ROC_ENABLE_PRE_VEGA=1` in `docker-compose.amd.yml`.

### AMD References

- [ROCm WSL2 Documentation](https://rocm.docs.amd.com/en/latest/deploy/linux/os-native/install-rocm.html)
- [AMD ROCm GitHub](https://github.com/RadeonOpenCompute/ROCm)
- [PyTorch ROCm](https://pytorch.org/get-started/locally/) — select ROCm under the PyTorch install matrix
