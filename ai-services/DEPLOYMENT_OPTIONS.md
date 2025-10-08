# AI Services Deployment Options

## 🚀 Quick Start - Choose Your Performance Level

### Option 1: Default Setup (CPU-Only) - **Recommended for Most Users**
```bash
cd ai-services
docker-compose up -d
```
- ✅ Works on any system
- ✅ No special drivers needed
- ✅ Stable and reliable
- ⚠️ Slower inference (30-60 seconds per video analysis)

### Option 2: GPU Acceleration - **For Power Users with NVIDIA GPUs**
```bash
cd ai-services
docker-compose -f docker-compose.gpu.yml up -d
```
- 🚀 5-10x faster inference (3-6 seconds per video analysis)
- ✅ Better for large media libraries
- ⚠️ Requires NVIDIA GPU (GTX 1060 6GB+ or RTX series)
- ⚠️ Requires NVIDIA Docker runtime setup

### Option 3: Explicit CPU-Only - **For Servers Without GPU**
```bash
cd ai-services
docker-compose -f docker-compose.cpu.yml up -d
```
- ✅ Same as Option 1 but with resource limits
- ✅ Better for shared/server environments
- ✅ Prevents CPU overload

## 📊 Performance Comparison

| Setup | Analysis Speed | Requirements | Best For |
|-------|---------------|--------------|----------|
| **CPU-Only** | 30-60 sec/video | Any computer | Most users, small libraries |
| **GPU-Accelerated** | 3-6 sec/video | NVIDIA GPU + drivers | Large libraries, frequent analysis |

## 🔧 GPU Setup Requirements

If you want to use GPU acceleration, ensure you have:

1. **NVIDIA GPU** (GTX 1060 6GB or better, RTX series recommended)
2. **NVIDIA Drivers** (Latest version)
3. **NVIDIA Container Toolkit**
4. **Docker Desktop with GPU support enabled**

### Quick GPU Check
```bash
# Check if you have NVIDIA GPU
nvidia-smi

# Test GPU Docker access
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi
```

If both commands work, you can use GPU acceleration!

## 🎛️ Switching Between Modes

### Currently Running CPU? Switch to GPU:
```bash
cd ai-services
docker-compose down
docker-compose -f docker-compose.gpu.yml up -d
```

### Currently Running GPU? Switch to CPU:
```bash
cd ai-services
docker-compose -f docker-compose.gpu.yml down
docker-compose up -d
```

### Check What's Currently Running:
```bash
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
```
- Look for container names ending in `-gpu` (GPU mode) or without suffix (CPU mode)

## 🔍 Monitoring Performance

### Check Container Resource Usage:
```bash
docker stats
```

### Check AI Service Health:
```bash
# NSFW Detector
curl http://localhost:3001/health

# Scene Analyzer  
curl http://localhost:3002/health

# Content Classifier
curl http://localhost:3004/health
```

### Check Analysis Logs:
```bash
# See recent analysis activity
docker logs scene-analyzer-gpu    # For GPU mode
docker logs scene-analyzer        # For CPU mode
```

## 🎯 Recommendations

### For Home Users:
- Start with **CPU-only** mode (default)
- Upgrade to **GPU mode** if analysis is too slow

### For Power Users:
- Use **GPU mode** if you have compatible hardware
- Analyze large libraries much faster

### For Servers:
- Use **CPU-only with resource limits** (`docker-compose.cpu.yml`)
- Better resource management in multi-user environments

## 🔧 Performance Tuning

### CPU Mode Optimizations:
```bash
# Reduce analysis samples for faster processing
# Edit ai-services/.env:
ANALYSIS_SAMPLE_COUNT=3  # Default: 5
```

### GPU Mode Optimizations:
```bash
# Enable GPU memory growth to prevent OOM
# This is already configured in docker-compose.gpu.yml
```

## 🚨 Troubleshooting

### GPU Mode Not Working?
1. Check `docker logs nsfw-detector-gpu` for CUDA errors
2. Verify GPU access: `docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi`
3. Fallback to CPU mode: `docker-compose -f docker-compose.gpu.yml down && docker-compose up -d`

### CPU Mode Too Slow?
1. Reduce `sample_count` in analysis requests
2. Upgrade to GPU mode if possible
3. Run analysis during off-peak hours

### Out of Memory Errors?
1. Reduce resource limits in compose file
2. Close other applications during analysis
3. Use CPU mode instead of GPU mode