# GPU Acceleration Setup

PureFin AI services support GPU-accelerated inference on AMD, NVIDIA, and Intel hardware.
Each manufacturer uses a dedicated Docker image and compose overlay.

## Architecture Overview

| Layer | AMD (ROCm) | NVIDIA (CUDA) | Intel | CPU |
|-------|-----------|---------------|-------|-----|
| Compose overlay | `docker-compose.amd.yml` | `docker-compose.gpu.yml` | `docker-compose.intel.yml` | *(base only)* |
| PyTorch runtime | ROCm/HIP (via `rocm/pytorch` base) | CUDA 12.4 (via `nvidia/cuda` base) | CPU | CPU |
| FFmpeg decode | CPU¹ | NVDEC (`cuda` hwaccel) | VAAPI (`iHD` driver) | CPU |
| `FFMPEG_HWACCEL` | `none` ¹ | `cuda` | `vaapi` | *(unset)* |

> ¹ AMD WSL2: `/dev/dri` is not exposed via Docker Desktop on WSL2. FFmpeg decode runs on CPU.
> PyTorch AI inference still runs on the AMD GPU via ROCm/HIP.  
> On **native AMD Linux** (not WSL2): mount `/dev/dri/renderD128` and set `FFMPEG_HWACCEL=vaapi`.

---

## AMD (ROCm) — WSL2 + Native Linux

### Host Requirements

#### WSL2 (Windows)
- **Windows 11** or Windows 10 21H2+
- **AMD Adrenalin 26.2.2+** driver with ROCm 7.2.1+ enabled
- ROCm installed in WSL Ubuntu:
  ```bash
  sudo apt install rocm
  ```
- Verify ROCm and the GPU are visible:
  ```bash
  rocminfo | grep -A5 'Device Type.*GPU'
  ls /dev/dxg          # DXCore path — must exist
  ```

#### Native Linux
- AMD driver with ROCm support for your kernel
- Verify:
  ```bash
  rocminfo | grep -A5 'Device Type.*GPU'
  ls /dev/kfd /dev/dri/renderD128
  ```

### Starting the Stack

```bash
# From Ubuntu WSL (or native Linux), cd to ai-services:
cd ai-services

# WSL2
docker compose -f docker-compose.yml -f docker-compose.amd.yml up --build -d

# Native Linux — additionally mount /dev/dri for VAAPI frame decode
FFMPEG_HWACCEL=vaapi \
  docker compose -f docker-compose.yml -f docker-compose.amd.yml up --build -d
```

### Validate

```bash
bash scripts/validate-gpu.sh --vendor amd
```

Expected output:
```
[PASS] /dev/dxg present (WSL2 DXCore path)
[PASS] PyTorch CUDA/ROCm: available=True count=1 device=AMD Radeon RX 9060 XT
[PASS] AMD/WSL2: FFMPEG_HWACCEL=none — CPU decode expected, GPU used for AI inference
```

### Configuration Notes

- `HSA_OVERRIDE_GFX_VERSION` — uncomment for RDNA 2/3 if your GPU fails ROCm version checks
- `LD_PRELOAD` stub — suppresses `librocprofiler-sdk.so` crash on WSL2 where `/sys/class/kfd` sysfs is absent
- `ROCM_LIB_PATH` — override to match your ROCm version (default: `/opt/rocm-7.2.1/lib`)

---

## NVIDIA (CUDA)

### Host Requirements

- NVIDIA GPU (GTX 10-series / RTX 2000-series or newer recommended)
- 4 GB VRAM minimum; 8 GB+ recommended
- NVIDIA driver ≥ 525

#### Install NVIDIA Container Toolkit (Linux)
```bash
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor \
    -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

#### Verify
```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

### Starting the Stack

```bash
cd ai-services
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
```

### Validate

```bash
bash scripts/validate-gpu.sh --vendor nvidia
```

Expected output:
```
[PASS] /dev/nvidia0 present
[PASS] nvidia-smi: NVIDIA GeForce RTX 4080
[PASS] PyTorch CUDA/ROCm: available=True count=1 device=NVIDIA GeForce RTX 4080
[PASS] CUDA hwaccel probe: OK
```

### Multiple GPUs

```yaml
# In docker-compose.gpu.yml override
services:
  scene-analyzer:
    environment:
      CUDA_VISIBLE_DEVICES: "0"
  violence-detector:
    environment:
      CUDA_VISIBLE_DEVICES: "1"
```

---

## Intel GPU (VAAPI / QuickSync)

Supports Intel integrated graphics (Gen 8+) and Arc discrete GPUs.
PyTorch runs on CPU; FFmpeg frame decode uses VAAPI hardware decode.

### Host Requirements

```bash
# Ubuntu 22.04+
sudo apt install intel-media-va-driver-non-free vainfo

# Verify
vainfo
ls /dev/dri/renderD128
```

For older iGPUs (pre-Broadwell):
```bash
sudo apt install i965-va-driver
# Set LIBVA_DRIVER_NAME=i965 in docker-compose.intel.yml
```

### Starting the Stack

```bash
cd ai-services
docker compose -f docker-compose.yml -f docker-compose.intel.yml up --build -d
```

### Validate

```bash
bash scripts/validate-gpu.sh --vendor intel
```

Expected output:
```
[PASS] /dev/dri/renderD128 present
[PASS] vainfo: VAAPI driver loaded
[PASS] Intel VAAPI probe: OK
```

### QuickSync (QSV) instead of VAAPI

For Intel QuickSync Video decode:
```yaml
# docker-compose.intel.yml override
environment:
  FFMPEG_HWACCEL: "qsv"
```

---

## CPU Only (No GPU)

No overlay needed — use the base compose:

```bash
cd ai-services
docker compose up --build -d
```

Or explicitly:
```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up --build -d
```

---

## GPU Validation Script

Run after `docker compose up` to confirm the GPU setup is working:

```bash
# Auto-detect GPU vendor
bash ai-services/scripts/validate-gpu.sh

# Specify vendor explicitly
bash ai-services/scripts/validate-gpu.sh --vendor amd
bash ai-services/scripts/validate-gpu.sh --vendor nvidia
bash ai-services/scripts/validate-gpu.sh --vendor intel
bash ai-services/scripts/validate-gpu.sh --vendor cpu
```

The script checks:
1. Host GPU device nodes (`/dev/dxg`, `/dev/nvidia0`, `/dev/dri/renderD128`)
2. Container health status
3. PyTorch GPU visibility (`torch.cuda.is_available()`)
4. FFmpeg hwaccel probe (actually tests a synthetic frame decode)
5. Service `/health` endpoints

---

## `FFMPEG_HWACCEL` Reference

| Value | Effect |
|-------|--------|
| `none` | Disable FFmpeg GPU decode; use CPU (set automatically for AMD WSL2) |
| `vaapi` | Use VAAPI (AMD/Intel Linux; requires `/dev/dri/renderD128` mounted) |
| `cuda` / `nvdec` | Use NVDEC (NVIDIA only) |
| `amf` | Use AMF (AMD Windows-native; not available in Linux containers) |
| `qsv` | Use Intel QuickSync Video |
| *(unset)* | Auto-detect: AMF → VAAPI → CUDA |

Set via `VAAPI_DEVICE` env var to override the VAAPI device path (default: `/dev/dri/renderD128`).

---

## Performance Reference

| Metric | AMD RX 9060 XT (WSL2) | NVIDIA RTX 4080 | CPU (Ryzen 9800X3D) |
|--------|-----------------------|-----------------|---------------------|
| TransNetV2 inference | ~79 ms/frame | ~30 ms/frame | ~400 ms/frame |
| Scene analysis (2hr film) | ~8–12 min | ~4–6 min | ~45–90 min |
| FFmpeg decode | CPU (WSL2) | NVDEC | CPU |

> AMD native Linux with VAAPI decode is expected to perform similarly to NVIDIA.

---

## Troubleshooting

### AMD: `rocprofiler_set_api_table` crash on WSL2
Suppressed by the `LD_PRELOAD` stub compiled into `Dockerfile.amd`. If you see this error, ensure the AMD image was rebuilt after the stub was added.

### AMD: `No GPU found` / `torch.cuda.is_available() = False`
- WSL2: verify `/dev/dxg` exists and `HSA_ENABLE_DXG_DETECTION=1` is set
- Check `ROCM_LIB_PATH` matches your installed ROCm version: `ls /opt/rocm*/lib/librocdxg.so`

### NVIDIA: `could not select device driver "" with capabilities: [[gpu]]`
NVIDIA Container Toolkit is not configured. Re-run `sudo nvidia-ctk runtime configure --runtime=docker`.

### Intel: VAAPI decode fails inside container
- Ensure `/dev/dri/renderD128` is in the `devices:` list in `docker-compose.intel.yml`
- Run `vainfo` inside the container: `docker exec scene-analyzer vainfo`
- Older iGPUs may need `LIBVA_DRIVER_NAME=i965`

### OOM (exit code 137) during large library analysis
Reduce `sample_count` in the Jellyfin plugin settings, or increase WSL2 memory:
```ini
# %USERPROFILE%\.wslconfig
[wsl2]
memory=24GB
```
Then run `wsl --shutdown` to apply.


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
