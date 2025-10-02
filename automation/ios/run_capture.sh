#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CAPTURE_ROOT="$WORKSPACE_DIR/captures/ios"
BINARY_DIR="$CAPTURE_ROOT/binaries"
UI_DIR="$CAPTURE_ROOT/ui"
NETWORK_DIR="$CAPTURE_ROOT/network"
ASSET_DIR="$CAPTURE_ROOT/assets"

IPA_PATH=$(ls -t "$BINARY_DIR"/*.ipa 2>/dev/null | head -n1 || true)
if [[ -z "$IPA_PATH" ]]; then
  echo "No IPA found in $BINARY_DIR" >&2
  exit 1
fi

echo "Using IPA: $IPA_PATH"
mkdir -p "$UI_DIR" "$NETWORK_DIR" "$ASSET_DIR"

echo "Installing automation dependencies"
npm install --prefix automation/ios >/dev/null 2>&1 || true
pip3 install -r automation/ios/requirements.txt >/dev/null 2>&1 || true

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

# Run Appium walkthrough to populate UI artefacts
node automation/ios/walkthrough.mjs \
  --app "$IPA_PATH" \
  --output "$UI_DIR"

# Summarise layouts from collected hierarchy dumps
python3 automation/ios/layout_dump.py \
  --input "$UI_DIR" \
  --output "$UI_DIR/layout-summary.json" \
  --run latest

RUN_ID_FILE="$UI_DIR/latest-run.txt"
if [[ -f "$RUN_ID_FILE" ]]; then
  RUN_ID="$(cat "$RUN_ID_FILE" | tr -d '\n' | tr -d '\r')"
  SUMMARY_PATH="$UI_DIR/$RUN_ID/summary.json"
  REPORT_DIR="$WORKSPACE_DIR/reports/ios"
  mkdir -p "$REPORT_DIR"
  if [[ -f "$SUMMARY_PATH" ]]; then
    cp "$SUMMARY_PATH" "$REPORT_DIR/ui-run.json"
  fi
  if [[ -f "$UI_DIR/layout-summary.json" ]]; then
    cp "$UI_DIR/layout-summary.json" "$REPORT_DIR/layout-summary.json"
  fi
fi

# Extract assets from the IPA bundle
python3 automation/ios/extract_assets.py \
  --app "$IPA_PATH" \
  --output "$ASSET_DIR" \
  --report "$WORKSPACE_DIR/reports/ios/assets-summary.json"

echo "Capture completed. Artefacts stored under $CAPTURE_ROOT"
