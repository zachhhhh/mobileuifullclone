#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_PATH="${1:?Workspace path missing}"
REMOTE_HOST="${ANDROID_REMOTE_HOST:-}"
REMOTE_USER="${ANDROID_REMOTE_USER:-}"
IDENTITY_FILE="${ANDROID_REMOTE_IDENTITY:-}"
REMOTE_WORKSPACE="${ANDROID_REMOTE_WORKSPACE:-$WORKSPACE_PATH}"
BOOTSTRAP="${ANDROID_REMOTE_BOOTSTRAP:-false}"

if [[ -z "$REMOTE_HOST" || -z "$REMOTE_USER" ]]; then
  echo "ANDROID_REMOTE_HOST/ANDROID_REMOTE_USER not configured; skipping Android capture." >&2
  exit 0
fi

SSH_BASE=("${REMOTE_USER}@${REMOTE_HOST}")
if [[ -n "$IDENTITY_FILE" ]]; then
  SSH_BASE=(-i "$IDENTITY_FILE" "${SSH_BASE[@]}")
fi

ssh_exec() {
  ssh "${SSH_BASE[@]}" "$@"
}

escape_remote_path() {
  local path="$1"
  printf '%s' "$path" | sed "s/'/'\\''/g"
}

scp_copy() {
  local source="$1"
  local dest_path="$2"
  local escaped="$(escape_remote_path "$dest_path")"
  local target="${REMOTE_USER}@${REMOTE_HOST}:'${escaped}'"
  if [[ -n "$IDENTITY_FILE" ]]; then
    scp -i "$IDENTITY_FILE" "$source" "$target"
  else
    scp "$source" "$target"
  fi
}

APK_PATH=$(python3 - "$WORKSPACE_PATH/captures/android/binaries" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
if not root.exists():
    sys.exit(1)

extensions = {'.apk', '.aab'}
files = [p for p in root.iterdir() if p.suffix in extensions]
files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
if not files:
    sys.exit(1)

print(files[0])
PY
) || true
if [[ -z "$APK_PATH" ]]; then
  echo "No APK/AAB found in $WORKSPACE_PATH/captures/android/binaries" >&2
  exit 1
fi

REMOTE_BIN_DIR="$REMOTE_WORKSPACE/captures/android/binaries"
REMOTE_UI_DIR="$REMOTE_WORKSPACE/captures/android/ui"
REMOTE_ASSET_DIR="$REMOTE_WORKSPACE/captures/android/assets"
REMOTE_NET_DIR="$REMOTE_WORKSPACE/captures/android/network"

escaped_workspace=$(escape_remote_path "$REMOTE_WORKSPACE")
escaped_bin=$(escape_remote_path "$REMOTE_BIN_DIR")
escaped_ui=$(escape_remote_path "$REMOTE_UI_DIR")
escaped_assets=$(escape_remote_path "$REMOTE_ASSET_DIR")
escaped_net=$(escape_remote_path "$REMOTE_NET_DIR")

ssh_exec "mkdir -p '$escaped_bin' '$escaped_ui' '$escaped_assets' '$escaped_net'"

if [[ "$BOOTSTRAP" == "true" ]]; then
  ssh_exec "cd '$escaped_workspace' && .automation/scripts/shared/bootstrap_remote.sh"
fi

echo "Syncing package to remote runner"
scp_copy "$APK_PATH" "$REMOTE_BIN_DIR/"

echo "Triggering remote capture"
ssh_exec "cd '$escaped_workspace' && automation/android/run_capture.sh"

echo "Fetching capture artefacts"
rsync_opts=(-az)
if [[ -n "$IDENTITY_FILE" ]]; then
  rsync_opts=(-az -e "ssh -i $IDENTITY_FILE")
fi
mkdir -p "$WORKSPACE_PATH/captures/android/ui" "$WORKSPACE_PATH/captures/android/assets" "$WORKSPACE_PATH/captures/android/network"
remote_ui="${REMOTE_USER}@${REMOTE_HOST}:'$(escape_remote_path "$REMOTE_UI_DIR/")'"
remote_assets="${REMOTE_USER}@${REMOTE_HOST}:'$(escape_remote_path "$REMOTE_ASSET_DIR/")'"
remote_net="${REMOTE_USER}@${REMOTE_HOST}:'$(escape_remote_path "$REMOTE_NET_DIR/")'"

rsync "${rsync_opts[@]}" "$remote_ui" "$WORKSPACE_PATH/captures/android/ui/"
rsync "${rsync_opts[@]}" "$remote_assets" "$WORKSPACE_PATH/captures/android/assets/"
rsync "${rsync_opts[@]}" "$remote_net" "$WORKSPACE_PATH/captures/android/network/"

echo "Remote Android capture complete."
