#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: bootstrap_emulator.sh [--workspace <path>] [--validate]

Reads emulator settings from .automation/config.yaml and verifies the AVD exists.
USAGE
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VALIDATE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace)
      WORKSPACE="$(cd "$2" && pwd)"
      shift 2
      ;;
    --validate)
      VALIDATE=true
      shift 1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

CONFIG_PATH="$WORKSPACE/.automation/config.yaml"
if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Config not found at $CONFIG_PATH" >&2
  exit 1
fi

AVD_NAME=$(python3 - "$CONFIG_PATH" <<'PY'
import sys
import yaml
from pathlib import Path

config = yaml.safe_load(Path(sys.argv[1]).read_text())
android = config.get("defaults", {}).get("android", {})
emu = android.get("emulator", {})
print(emu.get("avd", "Pixel_7_Pro_API_34"))
PY
)

if ! command -v avdmanager >/dev/null 2>&1; then
  echo "avdmanager not found. Install Android SDK tools and ensure they are on PATH." >&2
  exit 1
fi

if ! command -v sdkmanager >/dev/null 2>&1; then
  echo "sdkmanager not found. Install Android SDK command-line tools." >&2
  exit 1
fi

if ! command -v emulator >/dev/null 2>&1; then
  echo "emulator binary not found. Ensure Android SDK platform-tools/emulator are installed." >&2
  exit 1
fi

if [[ "$VALIDATE" == "true" ]]; then
  if avdmanager list avd | grep -F "$AVD_NAME" >/dev/null 2>&1; then
    echo "AVD '$AVD_NAME' is available."
    exit 0
  fi
  echo "AVD '$AVD_NAME' not found." >&2
  exit 1
fi

echo "Checking for existing AVD '$AVD_NAME'"
if avdmanager list avd | grep -F "$AVD_NAME" >/dev/null 2>&1; then
  echo "AVD already exists."
  exit 0
fi

echo "AVD '$AVD_NAME' is missing. Install a system image and create it manually, for example:"
echo "  sdkmanager \"system-images;android-34;google_apis;x86_64\""
echo "  avdmanager create avd --name $AVD_NAME --package \"system-images;android-34;google_apis;x86_64\" --device pixel_7_pro"
echo "Once created, rerun with --validate."
exit 1
