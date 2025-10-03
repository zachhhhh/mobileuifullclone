# Real Device Testing Strategy

## Phase 1 – Firebase Test Lab (Android focus)
- Build instrumentation APKs (`./gradlew assembleDebug assembleAndroidTest`).
- Authenticate with Google Cloud (`gcloud auth login` and `gcloud config set project <project-id>`).
- Run `automation/android/testlab_run.sh` to execute the Appium/Espresso suites on virtual/physical devices.
- Export `TESTLAB_RESULTS_BUCKET` to store artifacts in your own GCS bucket if desired.

## Phase 2 – Hosted Device Grid (Android + iOS)
- Evaluate providers offering both platforms (BrowserStack App Automate, Bitrise, Kobiton).
- Upload the captured IPA/APK and reuse the Appium scripts (`automation/ios/walkthrough.mjs`, `automation/android/walkthrough.mjs`).
- Fetch logs/videos/screenshots and archive alongside `reports/` for release approvals.

## Suggested Device Matrix
| Platform | Device | OS | Notes |
|----------|--------|----|-------|
| Android | Pixel 6 | 14 | High-end reference |
| Android | Moto G Power | 13 | Mid/low tier |
| Android | Galaxy Tab A7 | 12 | Tablet layout |
| iOS | iPhone SE (3rd gen) | 17 | Small screen |
| iOS | iPhone 15 Pro | 17 | Flagship |
| iOS | iPad (10th gen) | 17 | Tablet |

## Reporting
- Store provider artifacts under `reports/device-farm/<provider>/<run-id>/`.
- Update `docs/release-summary.prev.json` before each new run to maintain accurate diffs.
- If failures occur, open issues referencing the farm report and link to the corresponding Appium flow summary in `reports/<platform>/`.
