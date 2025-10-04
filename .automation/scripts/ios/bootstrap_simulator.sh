#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: bootstrap_simulator.sh [--workspace <path>] [--validate]

Reads simulator settings from .automation/config.yaml and ensures the device exists.
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

readarray -t CONFIG < <(python3 - "$CONFIG_PATH" <<'PY'
import sys
import yaml
from pathlib import Path

config = yaml.safe_load(Path(sys.argv[1]).read_text())
ios = config.get("defaults", {}).get("ios", {})
sim = ios.get("simulator", {})
print(sim.get("device", "iPhone 15 Pro"))
print(sim.get("os", "latest"))
PY
)
DEVICE="${CONFIG[0]}"
OS_VERSION="${CONFIG[1]}"

if ! command -v xcrun >/dev/null 2>&1; then
  echo "xcrun is required. Install Xcode command line tools (xcode-select --install)." >&2
  exit 1
fi

if ! command -v simctl >/dev/null 2>&1; then
  echo "simctl not available. Ensure Xcode is installed." >&2
  exit 1
fi

if [[ "$VALIDATE" == "true" ]]; then
  if ! xcrun simctl list devices | grep -F "$DEVICE" >/dev/null 2>&1; then
    echo "Simulator '$DEVICE' not found." >&2
    echo "Run this script without --validate to create it." >&2
    exit 1
  fi
  echo "Simulator '$DEVICE' is available."
  exit 0
fi

echo "Ensuring simulator '$DEVICE' (iOS $OS_VERSION) exists"

if xcrun simctl list devices | grep -F "$DEVICE" >/dev/null 2>&1; then
  echo "Simulator already present."
  exit 0
fi

RUNTIME=$(xcrun simctl list runtimes | awk -v v="iOS $OS_VERSION" '$0 ~ v {print $NF}' | head -n1)
if [[ -z "$RUNTIME" ]]; then
  echo "Unable to locate runtime for iOS $OS_VERSION. Install the runtime in Xcode first." >&2
  exit 1
fi

device_type=$(xcrun simctl list devicetypes | awk -v d="$DEVICE" '$0 ~ d {print $NF}' | head -n1)
if [[ -z "$device_type" ]]; then
  echo "Unable to resolve device type for $DEVICE. Check simulator name in config." >&2
  exit 1
fi

xcrun simctl create "$DEVICE" "$device_type" "$RUNTIME"
echo "Simulator '$DEVICE' created."
