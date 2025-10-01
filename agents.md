# Mobile App Clone Agent Playbook (Fully Automated)

## Purpose
This playbook defines how autonomous agents and scheduled jobs clone your owned mobile app, starting on iOS then Android. Every step is automated—humans only review reports and resolve exceptions.

## Guardrails
- Operate exclusively on binaries, APIs, and credentials you control; confirm licensing for third-party assets before mirroring.
- Never emit signing keys, production secrets, or user data in logs or artefacts.
- Tag every automation run with timestamp, app build, git commit, and tool versions for traceability.

## Automation Infrastructure
- **Orchestrator**: GitHub Actions (or equivalent CI) with reusable composite actions per task.
- **Job Runner**: macOS runners for iOS capture/build, Linux runners for backend/tests, optional self-hosted Android/Windows if required.
- **Artefact Store**: Git LFS + S3/GCS bucket `artifacts/` for large binaries, captures, reports.
- **Configuration**: `.automation/config.yaml` tracks bundle IDs, proxy settings, simulator/emulator profiles, cron schedules, Slack/webhook targets.
- **Secrets Management**: CI secrets vault providing App Store/Play Console tokens, proxy creds, signing certs, encrypted environment files.

## Shared Automated Pipeline
1. **Version Ingest Job**
   - Trigger: cron + manual dispatch.
   - Steps: query App Store/Play APIs, download latest IPA/AAB via fastlane supply/deliver, checksum binary, push to `captures/<platform>/binaries/<version>`. Create git tag `source/<platform>/<version>`.
2. **Environment Provision Job**
   - Uses macOS runner setup script to install/verify Xcode, simulators, Node, Python, Appium, mitmproxy.
   - Generates cache keys to reuse simulator images and npm/pip deps.
3. **Appium Walkthrough Job**
   - Spins up simulator/emulator defined in config.
  - Launches Appium server (Node) with walkthrough scripts (`automation/<platform>/walkthrough.mjs`).
   - Scripts navigate all documented flows, saving XML hierarchy and screenshots to `captures/<platform>/ui/<timestamp>/`.
   - Emits JSON summary (visited screens, error states) to `reports/<platform>/ui-run.json`.
4. **Network Capture Job**
   - Runs in parallel with walkthrough using mitmproxy inline script.
   - Stores raw flows `.mitm` + normalized curl/Postman collections under `captures/<platform>/network/<timestamp>/`.
   - Generates diff vs previous capture via JSON comparison, posting highlights to Slack/Teams.
5. **Asset & Data Extraction Job**
   - iOS: mounts simulator container, runs asset catalog dump, copies fonts/strings/SQLite into `captures/ios/assets/`.
   - Android: executes `apktool`, `jadx` tasks, extracts resources and data files to `captures/android/assets/`.
   - Produces manifest (`manifests/<platform>/assets.json`) with hashes for diffing.
6. **Spec Generation Job**
   - Aggregates UI dumps + asset manifests to regenerate `design-tokens/<platform>/` and component specs (Markdown/JSON).
   - Converts mitmproxy output into OpenAPI files (`fixtures/shared/api.yaml`) and fixture payloads.
7. **Backend Sync Job**
   - Runs contract tests ensuring existing backend implementation matches latest fixtures.
   - On drift, opens issue with failing endpoints, attaches expected vs actual payloads.
8. **Client Build & Snapshot Job**
   - Builds clone apps (Swift/Kotlin) using captured design tokens and assets.
   - Executes integration tests and Appium parity tests against build artefacts.
   - Generates screenshot diffs (`reports/<platform>/visual-diff.html`) and publishes to artefact store.
9. **Performance & Security Scan Job**
   - Profiles startup / frame pacing (Xcode Instruments CLI, Android Profiler headless), compares to baseline thresholds.
   - Verifies certificate pinning, secure storage, analytics event coverage.
10. **Report & Notification Job**
   - Consolidates results into `reports/daily-summary.md` including version changes, diffs, regressions, action items.
   - Posts summary to Slack/email with links to artefacts.

---

## iOS Automated Flow

### Pipelines & Scripts
- **Binary Fetch**: `.automation/scripts/ios/download_latest.sh`
- **Simulator Prep**: `.automation/scripts/ios/bootstrap_simulator.sh`
- **Appium Suite**: `automation/ios/walkthrough.mjs` (Node + WebdriverIO) covering onboarding, auth, core flows, settings.
- **UI Inspector CLI**: `automation/ios/layout_dump.py` condenses Appium XML hierarchies into screen-level metrics (element counts, accessibility labels, bounding boxes).
- **Asset Extractor**: `automation/ios/extract_assets.py` unpacks the IPA and mirrors images/fonts/animations into structured manifests.
- **Mitmproxy Add-on**: `automation/ios/mitm_capture.py` normalizes headers, strips volatile fields, emits OpenAPI.
- **Design Token Generator**: `automation/ios/generate_tokens.ts` merges layout dumps and color sampling into JSON/Swift constants.
- **Clone Build**: `client-ios/fastlane/Fastfile` lane `clone_build` runs `xcodebuild`, `swiftformat`, unit + UI tests.
- **Parit yTesting**: `automation/ios/compare_snapshots.ts` runs screenshot diff + XML tree comparison.

### Artefact Layout
- `captures/ios/binaries/<version>/app.ipa`
- `captures/ios/ui/<timestamp>/{screen}.png|xml`
- `captures/ios/network/<timestamp>/flows.mitm`
- `captures/ios/assets/<timestamp>/{images,fonts,db}`
- `design-tokens/ios/{colors.json,typography.json,spacing.json}`
- `reports/ios/{ui-run.json,visual-diff.html,api-diff.md,performance.csv}`

### Automation Notes
- Jobs run sequentially via workflow `ios-clone.yml`; each stage uploads artefacts and sets output variables for downstream jobs.
- Failures auto-create GitHub issues with logs and next steps.
- Manual approval gates only for deploying backend changes to production clones.

---

## Android Automated Flow

### Pipelines & Scripts
- **Binary Fetch**: `.automation/scripts/android/download_latest.sh` using Play Developer API.
- **Emulator Prep**: `.automation/scripts/android/bootstrap_emulator.sh` creates/starts AVD with GPU offscreen rendering.
- **Appium Suite**: `automation/android/walkthrough.mjs` aligned with iOS flow coverage.
- **Layout Dump**: `automation/android/layout_dump.py` summarises Appium XML dumps into metrics (class frequencies, accessibility coverage, bounds).
- **Asset Extractor**: `automation/android/extract_assets.py` decodes the APK via `apktool` and catalogs drawables/fonts/XML into manifests.
- **Mitmproxy Add-on**: shared script with platform flag to handle Android-specific headers.
- **Token Generator**: `automation/android/generate_tokens.ts` converts metrics to dp/sp tokens and Compose theme definitions.
- **Clone Build**: `client-android/gradlew cloneBuild` lane executing unit, instrumentation, and screenshot tests.
- **Parity Testing**: `automation/android/compare_snapshots.ts` for pixel + hierarchy diff.

### Artefact Layout
- `captures/android/binaries/<version>/app.apk`
- `captures/android/ui/<timestamp>/{screen}.png|xml`
- `captures/android/network/<timestamp>/flows.mitm`
- `captures/android/assets/<timestamp>/{drawables,fonts,db}`
- `design-tokens/android/{colors.json,typography.json,spacing.json}`
- `reports/android/{ui-run.json,visual-diff.html,api-diff.md,performance.csv}`

### Automation Notes
- Workflow `android-clone.yml` mirrors iOS pipeline; shared composite actions keep logic DRY.
- Emulator snapshots cached between runs to speed up Appium sessions.
- CI enforces Play Protect compliance by running `lint` and `security` tasks.

---

## Continuous Synchronisation
- **Update Detector**: scheduled job checks upstream release feeds; on new version, triggers full pipeline and posts change summary.
- **Diff Engine**: `automation/shared/diff_suite.py` compares latest artefacts against previous run, tagging diffs ≥ threshold.
- **Ticket Bot**: automatically files issues with labels (`ui-drift`, `api-change`, `asset-change`) and includes repro steps + artefact links.
- **Baseline Refresh**: once clone updates are merged, workflow `approve-baseline.yml` promotes new artefacts to baseline storage.

## Repository Layout (Automated)
```
/agents.md
/.automation/
  config.yaml
  scripts/
    ios/
    android/
    shared/
  workflows/
    ios-clone.yml
    android-clone.yml
    shared-actions/
/backend/
/client-ios/
/client-android/
/automation/
  ios/
  android/
  shared/
/captures/
  ios/
  android/
/design-tokens/
  ios/
  android/
/fixtures/
  shared/
/reports/
  ios/
  android/
/docs/
```

## Next Actions for Agents
1. Implement `.automation/config.yaml` with bundle IDs, device profiles, notification webhooks.
2. Commit initial CI workflows (`ios-clone.yml`, `android-clone.yml`) referencing scripts above.
3. Develop the iOS Appium walkthrough suite and mitmproxy add-on; run pipeline dry-run to populate artefacts.
4. Mirror automation for Android once iOS pipeline passes and artefacts validate.

## Automation Container Usage
- Build and start the infrastructure: `docker compose -f .automation/docker-compose.yml up -d orchestrator mitmproxy`
- Run the pipeline for an IPA/APK from repo root: `docker compose -f .automation/docker-compose.yml run --rm orchestrator python3 automation/shared/run_pipeline.py ios path/to/app.ipa`
- Provide remote runner credentials via env vars (`IOS_REMOTE_HOST`, `IOS_REMOTE_USER`, `IOS_REMOTE_IDENTITY`, `ANDROID_REMOTE_HOST`, etc.) before invoking the orchestrator for full capture.
- Pipeline artefacts land under `captures/`, derived specs under `design-tokens/`, and reports under `reports/`.
- For CI, reference `.automation/docker-compose.yml` to reproduce the environment in GitHub Actions or other orchestrators.

### Remote Runner Setup
- Clone this repository on your macOS (iOS) and Linux/macOS (Android) runners; set `IOS_REMOTE_WORKSPACE` / `ANDROID_REMOTE_WORKSPACE` if paths differ from the orchestrator.
- On each runner, execute `.automation/scripts/shared/bootstrap_remote.sh` to install Node, Appium, mitmproxy, apktool, and supporting CLI tools.
- Ensure Xcode command line tools and the required simulators are installed on the iOS runner; create the AVD listed in `.automation/config.yaml` on the Android runner.
- Export SSH credentials for the orchestrator: `IOS_REMOTE_HOST`, `IOS_REMOTE_USER`, `IOS_REMOTE_IDENTITY` (optional), and `IOS_REMOTE_BOOTSTRAP=true` for first-run automation (analogous vars for Android).
- The orchestrator automatically `scp`/`rsync`s binaries and artefacts; confirm `rsync` is available on both ends and that firewall rules allow TCP/22.

### Flow Authoring
- Update `automation/ios/flows.json` and `automation/android/flows.json` with Appium selectors (`accessibility id`, `xpath`, etc.) describing each journey. The walkthrough scripts iterate these flows to capture screenshots and XML hierarchies.
- Regenerate flows as the app evolves; keep selectors resilient by preferring accessibility identifiers over brittle XPaths.

### Running Locally
- Provide the binary and platform, e.g. `docker compose -f .automation/docker-compose.yml run --rm orchestrator python3 automation/shared/run_pipeline.py ios path/to/MyApp.ipa` or `... android path/to/MyApp.apk`.
- Run the orchestrator twice (once per platform) when you need fresh captures for both iOS and Android.
- Logs for Appium/mitmproxy live under `captures/<platform>/network/*.mitm` and the Appium console output streamed to the orchestrator terminal; persist them by redirecting when necessary.

### CI Integration Notes
- Add GitHub Actions secrets mirroring the SSH environment vars plus any API tokens required by binary download scripts.
- Use the orchestrator image (`mobile-clone/orchestrator:latest`) in jobs, mounting repository and providing the binary path via workflow artifacts.
- Gate merge by requiring the orchestrator workflow to pass, ensuring layout specs, assets, and backend contracts stay current.
