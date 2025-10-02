#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${1:-reports/android}"
mkdir -p "$OUTPUT_DIR"
TRACE_PATH="$OUTPUT_DIR/systrace.html"

if ! command -v systrace > /dev/null && ! command -v perfetto > /dev/null; then
  echo "systrace/perfetto not found. Install Android SDK platform-tools." >&2
  exit 1
fi

if command -v perfetto > /dev/null; then
  perfetto -o "$TRACE_PATH.pftrace" -t 20s \
    sched freq idle am wm gfx view binder_driver hal input res memory
  echo "Perfetto trace saved to $TRACE_PATH.pftrace"
else
  echo "Capturing systrace via atrace"
  adb shell atrace --async_stop || true
  adb shell atrace --async_start sched freq idle am wm gfx view binder_driver hal input res memory
  sleep 20
  adb shell atrace --async_stop > "$TRACE_PATH"
  echo "Systrace saved to $TRACE_PATH"
fi
