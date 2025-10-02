#!/usr/bin/env bash
set -euo pipefail

APP_BUNDLE_ID="${1:-com.example.cloneapp}"
DEVICE="${IOS_DEVICE_ID:-$(xcrun simctl list devices | grep -Eo '[0-9A-F-]{36}' | head -n1)}"
OUTPUT_DIR="${2:-reports/ios}"
mkdir -p "$OUTPUT_DIR"

TRACE_PATH="$OUTPUT_DIR/time-profiler.trace"

echo "Launching Instruments Time Profiler for $APP_BUNDLE_ID on $DEVICE"

xcrun xctrace record \
  --template 'Time Profiler' \
  --device "$DEVICE" \
  --app "$APP_BUNDLE_ID" \
  --time-limit 20s \
  --output "$TRACE_PATH"

echo "Trace saved to $TRACE_PATH"
