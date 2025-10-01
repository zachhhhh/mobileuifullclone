#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CAPTURE_ROOT="$WORKSPACE_DIR/captures/android"
BINARY_DIR="$CAPTURE_ROOT/binaries"
UI_DIR="$CAPTURE_ROOT/ui"
NETWORK_DIR="$CAPTURE_ROOT/network"
ASSET_DIR="$CAPTURE_ROOT/assets"

APK_PATH=$(ls -t "$BINARY_DIR"/*.apk "$BINARY_DIR"/*.aab 2>/dev/null | head -n1 || true)
if [[ -z "$APK_PATH" ]]; then
  echo "No APK/AAB found in $BINARY_DIR" >&2
  exit 1
fi

echo "Using APK/AAB: $APK_PATH"
mkdir -p "$UI_DIR" "$NETWORK_DIR" "$ASSET_DIR"

echo "Installing automation dependencies"
npm install --prefix automation/android >/dev/null 2>&1 || true
pip3 install -r automation/android/requirements.txt >/dev/null 2>&1 || true

echo "Starting Appium server"
appium --base-path /wd/hub --log-level error &
APPIUM_PID=$!
sleep 5

echo "Starting mitmproxy capture"
MITM_LOG="$NETWORK_DIR/$(date +%Y%m%d%H%M%S).mitm"
mitmdump -w "$MITM_LOG" &
MITM_PID=$!

cleanup() {
  kill $MITM_PID >/dev/null 2>&1 || true
  kill $APPIUM_PID >/dev/null 2>&1 || true
}
trap cleanup EXIT

node automation/android/walkthrough.mjs \
  --app "$APK_PATH" \
  --output "$UI_DIR"

python3 automation/android/layout_dump.py \
  --input "$UI_DIR" \
  --output "$UI_DIR/layout-summary.json"

python3 automation/android/extract_assets.py \
  --app "$APK_PATH" \
  --output "$ASSET_DIR"

echo "Capture completed. Artefacts stored under $CAPTURE_ROOT"
