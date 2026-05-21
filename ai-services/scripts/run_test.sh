#!/usr/bin/env bash
# run_test.sh — End-to-end test script for PureFin AI services
#
# Usage:
#   bash run_test.sh [/path/to/media/file]
#
# If no file is given, the script discovers the first .mkv or .mp4 under
# /mnt/d/Media/Movies (the Docker Desktop WSL2 mount of D:\Media\Movies).
#
# Requirements: curl, python3 (for pretty-printing JSON)

set -euo pipefail

SCENE_ANALYZER_URL="http://localhost:3002"
READY_TIMEOUT=60   # seconds to wait for services to become ready

# ---------------------------------------------------------------------------
# Resolve media file
# ---------------------------------------------------------------------------
MEDIA_FILE="${1:-}"

if [[ -z "$MEDIA_FILE" ]]; then
  echo "No media file specified — discovering first .mkv or .mp4 in /mnt/d/Media/Movies ..."
  MEDIA_FILE=$(find /mnt/d/Media/Movies -maxdepth 3 \( -iname "*.mkv" -o -iname "*.mp4" \) -print -quit 2>/dev/null || true)
  if [[ -z "$MEDIA_FILE" ]]; then
    echo "ERROR: No .mkv or .mp4 files found under /mnt/d/Media/Movies."
    echo "       Pass a file path explicitly:  bash run_test.sh /mnt/d/Media/Movies/MyMovie.mkv"
    exit 1
  fi
  echo "Found: $MEDIA_FILE"
fi

# Docker containers see the same /mnt/d path — no translation needed.
CONTAINER_PATH="$MEDIA_FILE"

# ---------------------------------------------------------------------------
# Wait for services to be ready
# ---------------------------------------------------------------------------
wait_for_ready() {
  local service_url="$1"
  local service_name="$2"
  local elapsed=0

  echo -n "Waiting for $service_name to be ready"
  until curl -sf "${service_url}/ready" > /dev/null 2>&1; do
    if (( elapsed >= READY_TIMEOUT )); then
      echo ""
      echo "ERROR: $service_name did not become ready within ${READY_TIMEOUT}s."
      echo "       Check service logs:  docker compose logs $service_name"
      exit 1
    fi
    echo -n "."
    sleep 2
    (( elapsed += 2 ))
  done
  echo " ready!"
}

wait_for_ready "$SCENE_ANALYZER_URL" "scene-analyzer"

# ---------------------------------------------------------------------------
# Send analysis request
# ---------------------------------------------------------------------------
echo ""
echo "Sending analysis request..."
echo "  video_path : $CONTAINER_PATH"
echo "  sample_count: 5"
echo ""

RESPONSE=$(curl -sf -X POST "${SCENE_ANALYZER_URL}/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"video_path\": \"${CONTAINER_PATH}\", \"sample_count\": 5}" \
  2>&1) || {
  echo "ERROR: Request to scene-analyzer failed."
  echo "       Response: $RESPONSE"
  echo "       Is the service running?  docker compose ps"
  exit 1
}

# ---------------------------------------------------------------------------
# Pretty-print response
# ---------------------------------------------------------------------------
echo "=== Analysis Result ==="
echo "$RESPONSE" | python3 -m json.tool
echo "======================="
echo ""
echo "Done."
