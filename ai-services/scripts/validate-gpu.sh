#!/usr/bin/env bash
# validate-gpu.sh — PureFin AI services GPU validation
#
# Tests that the correct GPU accelerator is reachable inside a running container.
# Run AFTER `docker compose up` to confirm the stack is using the expected hardware.
#
# Usage:
#   ./scripts/validate-gpu.sh [--vendor amd|nvidia|intel|cpu]
#
# If --vendor is omitted, the script auto-detects based on what containers are running
# and what GPU devices are present on the host.
#
# Exit codes:
#   0  All checks passed
#   1  One or more checks failed (see output for details)

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS="${GREEN}[PASS]${NC}"; FAIL="${RED}[FAIL]${NC}"; WARN="${YELLOW}[WARN]${NC}"

failures=0

pass()  { printf "%b %s\n" "$PASS" "$1"; }
fail()  { printf "%b %s\n" "$FAIL" "$1"; failures=$((failures + 1)); }
warn()  { printf "%b %s\n" "$WARN" "$1"; }
header(){ printf "\n=== %s ===\n" "$1"; }

# ── Argument handling ─────────────────────────────────────────────────────────
VENDOR="${VENDOR:-auto}"
while [[ $# -gt 0 ]]; do
  case $1 in
    --vendor) VENDOR="$2"; shift 2;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

# ── Auto-detect vendor ────────────────────────────────────────────────────────
if [[ "$VENDOR" == "auto" ]]; then
  if [[ -e /dev/dxg ]] || (command -v rocminfo &>/dev/null && rocminfo 2>/dev/null | grep -q 'Device Type.*GPU'); then
    VENDOR="amd"
  elif [[ -e /dev/nvidia0 ]] || command -v nvidia-smi &>/dev/null; then
    VENDOR="nvidia"
  elif [[ -e /dev/dri/renderD128 ]]; then
    VENDOR="intel"
  else
    VENDOR="cpu"
  fi
  echo "Auto-detected vendor: $VENDOR"
fi

VENDOR=$(echo "$VENDOR" | tr '[:upper:]' '[:lower:]')

# ── Helper: exec in container ─────────────────────────────────────────────────
container_exec() {
  local container="$1"; shift
  docker exec "$container" sh -c "$*" 2>&1
}

container_running() {
  docker ps --format '{{.Names}}' | grep -q "^${1}$"
}

# ── Section 1: Host-level device checks ───────────────────────────────────────
header "Host GPU devices"

case "$VENDOR" in
  amd)
    if [[ -e /dev/dxg ]]; then
      pass "/dev/dxg present (WSL2 DXCore path)"
    elif [[ -e /dev/kfd ]]; then
      pass "/dev/kfd present (native Linux ROCm path)"
    else
      fail "Neither /dev/dxg nor /dev/kfd found — AMD GPU not accessible"
    fi
    if command -v rocminfo &>/dev/null; then
      gpu_name=$(rocminfo 2>/dev/null | grep 'Marketing Name' | head -1 | sed 's/.*: //')
      [[ -n "$gpu_name" ]] && pass "rocminfo: $gpu_name" || warn "rocminfo found no GPU marketing name"
    else
      warn "rocminfo not in PATH — install rocm for host-side checks"
    fi
    ;;
  nvidia)
    if [[ -e /dev/nvidia0 ]]; then
      pass "/dev/nvidia0 present"
    else
      fail "/dev/nvidia0 not found — NVIDIA driver not loaded or GPU absent"
    fi
    if command -v nvidia-smi &>/dev/null; then
      gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
      [[ -n "$gpu_name" ]] && pass "nvidia-smi: $gpu_name" || fail "nvidia-smi returned no GPU"
    else
      fail "nvidia-smi not found — install NVIDIA driver"
    fi
    ;;
  intel)
    if [[ -e /dev/dri/renderD128 ]]; then
      pass "/dev/dri/renderD128 present"
    else
      fail "/dev/dri/renderD128 not found — Intel DRI device not exposed"
    fi
    if command -v vainfo &>/dev/null; then
      vainfo 2>/dev/null | grep -q 'VA-API version' && pass "vainfo: VAAPI driver loaded" \
        || fail "vainfo found but VAAPI driver not loaded"
    else
      warn "vainfo not installed — install vainfo for host-level VAAPI check"
    fi
    ;;
  cpu)
    pass "CPU-only mode — no GPU device checks needed"
    ;;
esac

# ── Section 2: Container health ───────────────────────────────────────────────
header "Container health"

for svc in scene-analyzer violence-detector nsfw-detector; do
  if container_running "$svc"; then
    health=$(docker inspect --format='{{.State.Health.Status}}' "$svc" 2>/dev/null || echo "no-healthcheck")
    case "$health" in
      healthy)       pass "$svc: healthy";;
      no-healthcheck) warn "$svc: running (no healthcheck configured)";;
      *)             fail "$svc: $health";;
    esac
  else
    fail "$svc: not running"
  fi
done

# ── Section 3: PyTorch GPU visibility ─────────────────────────────────────────
header "PyTorch GPU visibility (scene-analyzer)"

if container_running scene-analyzer; then
  torch_check=$(container_exec scene-analyzer python3 -c "
import torch
avail = torch.cuda.is_available()
count = torch.cuda.device_count() if avail else 0
name  = torch.cuda.get_device_name(0) if (avail and count > 0) else 'n/a'
print(f'available={avail} count={count} device={name}')
")
  if echo "$torch_check" | grep -q 'available=True'; then
    pass "PyTorch CUDA/ROCm: $torch_check"
  else
    if [[ "$VENDOR" == "cpu" ]]; then
      pass "CPU mode — PyTorch GPU not expected: $torch_check"
    else
      fail "PyTorch reports no GPU: $torch_check"
    fi
  fi
else
  warn "scene-analyzer not running — skipping PyTorch check"
fi

# ── Section 4: FFmpeg hwaccel inside scene-analyzer ───────────────────────────
header "FFmpeg hwaccel (scene-analyzer)"

if container_running scene-analyzer; then
  listed=$(container_exec scene-analyzer ffmpeg -hide_banner -hwaccels 2>&1 | grep -v 'Hardware acceleration methods' | tr '\n' ' ')
  pass "FFmpeg hwaccels listed: ${listed:-none}"

  ffmpeg_hwaccel_env=$(container_exec scene-analyzer sh -c 'echo ${FFMPEG_HWACCEL:-<not set>}')
  pass "FFMPEG_HWACCEL env: $ffmpeg_hwaccel_env"

  case "$VENDOR" in
    amd)
      # WSL2: expect FFMPEG_HWACCEL=none (no DRI device)
      if [[ "$ffmpeg_hwaccel_env" == "none" ]]; then
        pass "AMD/WSL2: FFMPEG_HWACCEL=none — CPU decode expected, GPU used for AI inference"
      elif container_exec scene-analyzer ls /dev/dri/renderD128 &>/dev/null; then
        pass "AMD native Linux: /dev/dri/renderD128 present — VAAPI decode expected"
        # Quick VAAPI probe
        probe=$(container_exec scene-analyzer ffmpeg -hide_banner -hwaccel vaapi \
          -vaapi_device /dev/dri/renderD128 -f lavfi -i color=black:size=16x16:duration=0.1 \
          -vf format=nv12,hwupload -f null - 2>&1 | tail -3)
        echo "$probe" | grep -q 'Error\|fail\|Invalid' \
          && fail "VAAPI probe failed: $probe" \
          || pass "VAAPI probe: OK"
      else
        warn "AMD: FFMPEG_HWACCEL=$ffmpeg_hwaccel_env but no /dev/dri — check compose device mounts"
      fi
      ;;
    nvidia)
      if [[ "$ffmpeg_hwaccel_env" == "cuda" ]]; then
        probe=$(container_exec scene-analyzer ffmpeg -hide_banner -hwaccel cuda \
          -f lavfi -i color=black:size=16x16:duration=0.1 -f null - 2>&1 | tail -3)
        echo "$probe" | grep -q 'Error\|fail\|Cannot' \
          && fail "CUDA hwaccel probe failed: $probe" \
          || pass "CUDA hwaccel probe: OK"
      else
        fail "NVIDIA mode but FFMPEG_HWACCEL=$ffmpeg_hwaccel_env (expected 'cuda')"
      fi
      ;;
    intel)
      if [[ "$ffmpeg_hwaccel_env" == "vaapi" ]]; then
        vaapi_dev=$(container_exec scene-analyzer sh -c 'echo ${VAAPI_DEVICE:-/dev/dri/renderD128}')
        probe=$(container_exec scene-analyzer ffmpeg -hide_banner -hwaccel vaapi \
          -vaapi_device "$vaapi_dev" \
          -f lavfi -i color=black:size=16x16:duration=0.1 -f null - 2>&1 | tail -3)
        echo "$probe" | grep -q 'Error\|fail\|Invalid' \
          && fail "Intel VAAPI probe failed: $probe" \
          || pass "Intel VAAPI probe: OK"
      else
        fail "Intel mode but FFMPEG_HWACCEL=$ffmpeg_hwaccel_env (expected 'vaapi')"
      fi
      ;;
    cpu)
      pass "CPU mode — FFmpeg hwaccel not expected"
      ;;
  esac
else
  warn "scene-analyzer not running — skipping FFmpeg check"
fi

# ── Section 5: Service /health endpoint ───────────────────────────────────────
header "Service health endpoints"

for svc_port in "scene-analyzer:3002" "violence-detector:3003" "nsfw-detector:3000"; do
  svc="${svc_port%%:*}"; port="${svc_port##*:}"
  if container_running "$svc"; then
    resp=$(docker exec "$svc" curl -sf "http://localhost:${port}/health" 2>&1 || true)
    if echo "$resp" | grep -qi '"status".*"ok"\|"status".*"healthy"\|"alive"'; then
      pass "$svc /health: OK"
    else
      fail "$svc /health: unexpected response: ${resp:0:120}"
    fi
  else
    warn "$svc not running — skipping /health check"
  fi
done

# ── Summary ───────────────────────────────────────────────────────────────────
header "Summary"
if [[ $failures -eq 0 ]]; then
  printf "%b All GPU validation checks passed for vendor=%s\n" "$PASS" "$VENDOR"
else
  printf "%b %d check(s) failed for vendor=%s\n" "$FAIL" "$failures" "$VENDOR"
  exit 1
fi
