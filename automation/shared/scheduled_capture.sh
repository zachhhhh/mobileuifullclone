#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${CLONE_IPA_PATH:-}" && -z "${CLONE_APK_PATH:-}" ]]; then
  echo "Set CLONE_IPA_PATH and/or CLONE_APK_PATH for scheduled captures" >&2
  exit 1
fi

if [[ -n "${CLONE_IPA_PATH:-}" ]]; then
  python3 automation/shared/run_pipeline.py ios "$CLONE_IPA_PATH"
fi

if [[ -n "${CLONE_APK_PATH:-}" ]]; then
  python3 automation/shared/run_pipeline.py android "$CLONE_APK_PATH"
fi
