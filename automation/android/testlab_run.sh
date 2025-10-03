#!/usr/bin/env bash
set -euo pipefail

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud CLI not found. Install the Google Cloud SDK and authenticate." >&2
  exit 1
fi

APK="${1:-client-android/app/build/outputs/apk/debug/app-debug.apk}"
TEST_APK="${2:-client-android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk}"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT to your Firebase project}" 
MATRIX_ARGS=${3:-"--device model=Pixel6,version=34,locale=en,orientation=portrait"}

if [[ ! -f "$APK" ]]; then
  echo "APK not found at $APK" >&2
  exit 1
fi

if [[ ! -f "$TEST_APK" ]]; then
  echo "Test APK not found at $TEST_APK" >&2
  exit 1
fi

RUN_ID="testlab-$(date +%Y%m%d%H%M%S)"
RESULTS_BUCKET="gs://${TESTLAB_RESULTS_BUCKET:-test-lab-$PROJECT_ID}"
RESULTS_DIR="test-lab/${RUN_ID}"

set -x

gcloud firebase test android models list

gcloud firebase test android run \
  --type instrumentation \
  --app "$APK" \
  --test "$TEST_APK" \
  --results-bucket "$RESULTS_BUCKET" \
  --results-dir "$RESULTS_DIR" \
  --timeout 15m \
  $MATRIX_ARGS

set +x

echo "Results uploaded to https://console.firebase.google.com/project/$PROJECT_ID/testlab/histories"
echo "Artifacts: gs://$RESULTS_BUCKET/$RESULTS_DIR"
