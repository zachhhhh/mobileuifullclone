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
- Archive binaries with provenance when needed: `python automation/shared/archive_binary.py ios path/to/app.ipa --version 1.2.3 --release-notes "QA build"` (the pipeline uses the same logic automatically).
- Run the pipeline for an IPA/APK from repo root: `docker compose -f .automation/docker-compose.yml run --rm orchestrator python3 automation/shared/run_pipeline.py ios path/to/app.ipa`
- Provide remote runner credentials via env vars (`IOS_REMOTE_HOST`, `IOS_REMOTE_USER`, `IOS_REMOTE_IDENTITY`, `ANDROID_REMOTE_HOST`, etc.) before invoking the orchestrator for full capture.
- Pipeline artefacts land under `captures/`, derived specs under `design-tokens/`, and reports under `reports/`.
- For CI, reference `.automation/docker-compose.yml` to reproduce the environment in GitHub Actions or other orchestrators.
- Network captures are summarised automatically: per-flow JSON in `reports/<platform>/network/`, aggregated inventories in `reports/<platform>/network-summary.json`, and OpenAPI stubs in `fixtures/shared/api-<platform>.json`.
- Backend stubs sync via `backend/src/sync_endpoints.py`, which reads the captured OpenAPI skeletons and regenerates Express routers mounted in `backend/src/server.mjs`.
  - Stub responses are hydrated from `reports/<platform>/network-summary.json` examples; replace them with real services as you implement business logic.

### Remote Runner Setup
- Clone this repository on your macOS (iOS) and Linux/macOS (Android) runners; set `IOS_REMOTE_WORKSPACE` / `ANDROID_REMOTE_WORKSPACE` if paths differ from the orchestrator.
- On each runner, execute `.automation/scripts/shared/bootstrap_remote.sh` to install Node, Appium, mitmproxy, apktool, and supporting CLI tools.
- Validate prerequisites anytime with `python automation/shared/verify_toolchain.py ios` or `... android` to ensure required binaries remain installed.
- Ensure Xcode command line tools and the required simulators are installed on the iOS runner; create the AVD listed in `.automation/config.yaml` on the Android runner.
- Export SSH credentials for the orchestrator: `IOS_REMOTE_HOST`, `IOS_REMOTE_USER`, `IOS_REMOTE_IDENTITY` (optional), and `IOS_REMOTE_BOOTSTRAP=true` for first-run automation (analogous vars for Android).
- The orchestrator automatically `scp`/`rsync`s binaries and artefacts; confirm `rsync` is available on both ends and that firewall rules allow TCP/22.

### Flow Authoring
- Update `automation/ios/flows.json` and `automation/android/flows.json` with Appium selectors (`accessibility id`, `xpath`, etc.) describing each journey. The walkthrough scripts iterate these flows to capture screenshots and XML hierarchies.
- Regenerate flows as the app evolves; keep selectors resilient by preferring accessibility identifiers over brittle XPaths.
- Each flow supports metadata (`name`, `description`, optional `screenshot`) and step objects with `action`, `selector`, `value`, `timeout`, and `continueOnError`. Use `waitFor`, `input`, `tap`, `sleep`, `back`, `hideKeyboard`, and `keys` to compose journeys.
- After every run the orchestrator writes a per-run summary to `captures/<platform>/ui/<run-id>/summary.json` and publishes `reports/<platform>/ui-run.json` plus `reports/<platform>/layout-summary.json` for quick review.
- Asset extraction scripts output categorized manifests under `captures/<platform>/assets/` alongside `summary.json`, and they mirror high-level stats (counts, bytes, sample files) to `reports/<platform>/assets-summary.json` for quick audits.
- Baseline security audit scans updated asset dumps for secrets/PII keywords and writes results to `reports/<platform>/security-audit.json`; review flagged entries before using captured data.
- Backend uses `helmet` + env-driven CORS (`backend/.env`); update secrets from `backend/.env.example` and complete the checklist in `docs/security-hardening.md`.

### Full Clone Subtask Blueprint
- **Product Alignment**: capture feature list, target personas, KPIs, and legal/branding obligations; confirm upstream toggle states and A/B experiments to mirror.
  - Fill `docs/product-alignment.md` before each capture cycle so automation operates against an agreed scope.
- **Binary Provenance**: archive original builds with checksums, signing provenance, release notes, and environment variable snapshots for reproducibility.
- **Toolchain Provisioning**: maintain orchestrator containers, remote simulator/emulator hosts, secret vaults, CI workflows, and monitoring hooks required for automation.
  - Use `automation/shared/verify_toolchain.py` in CI/cron to enforce required CLI availability on each runner.
- **UI Evidence Collection**: expand Appium flows to cover onboarding, authentication, payments, error recovery, localization, accessibility, offline, and destructive actions; ensure each state saves XML + screenshots.
- **Design Tokenisation**: translate layout summaries into spacing scales, typography ramps, color palettes, elevation schemes, animation timings, and accessibility annotations stored in versioned JSON.
- **Asset Library Replication**: extract and catalogue raster/vector media, fonts, animations, localized strings, audio/video, and packaged databases with hash manifests for integrity checks.
  - Use the generated manifests (`captures/<platform>/assets/manifest.json`) and summaries (`reports/<platform>/assets-summary.json`) to track coverage and detect changes.
- **Backend Contract Derivation**: convert mitmproxy captures into OpenAPI/GraphQL specs, entity relationship diagrams, validation rules, pagination contracts, websocket topics, push payload templates, and rate-limit policies.
  - `automation/shared/summarize_network.py` turns `.mitm` captures into endpoint summaries and OpenAPI skeletons stored under `reports/<platform>/` and `fixtures/shared/`.
- **Security & Privacy Requirements**: enumerate auth flows, MFA, certificate pinning, keychain/keystore usage, encryption keys, analytics consent, privacy prompts, and data retention rules.
  - Automated scan (`automation/shared/security_audit.py`) highlights potential secrets/PII in extracted assets and lists config files needing manual review.
  - Track hardening progress using `docs/security-hardening.md` and ensure clients implement pinning/secure storage before release.
- **Client Rebuild**: reproduce navigation graphs, screen controllers, reusable components, state management, offline caching, analytics instrumentation, and accessibility features using generated design tokens and assets.
  - SwiftUI scaffolding (`client-ios/`) consumes tokens via `TokenStore` and pings the backend `/health` endpoint via `BackendClient`; Android Compose scaffold (`client-android/`) loads tokens and backend status through `BackendClient`. Expand these to render components and hook into real APIs.
- **QA & Compliance**: define unit/integration/E2E suites, snapshot diff baselines, contract tests, accessibility audits, performance thresholds, security scans, and store-review compliance checklists.
  - Baseline QA report generated by `automation/shared/qa_check.py` summarises flow coverage, failed steps, screen counts, and captured endpoints to catch regressions early.
- **Release Engineering**: configure build pipelines, signing assets, app store metadata, rollout strategies, crash reporting, and telemetry dashboards for cloned clients.
  - Release summary generated at `docs/release-summary.json` captures latest capture metrics and audit outcomes for distribution sign-off.
- **Operational Maintenance**: schedule update detectors, automated diff reports, incident response runbooks, documentation updates, and onboarding guides for new contributors.
  - Use `automation/shared/release_report.py` + `automation/shared/diff_report.py` in scheduled workflows to detect upstream changes and generate actionable diffs.

### Running Locally
- Provide the binary and platform, e.g. `docker compose -f .automation/docker-compose.yml run --rm orchestrator python3 automation/shared/run_pipeline.py ios path/to/MyApp.ipa` or `... android path/to/MyApp.apk`.
- Run the orchestrator twice (once per platform) when you need fresh captures for both iOS and Android.
- Logs for Appium/mitmproxy live under `captures/<platform>/network/*.mitm` and the Appium console output streamed to the orchestrator terminal; persist them by redirecting when necessary.
- Review UI coverage via `reports/<platform>/ui-run.json` (step statuses) and `reports/<platform>/layout-summary.json` (element counts, accessibility frequency) before regenerating design tokens or specs.
- Generated design tokens sync into `client-ios/Sources/CloneUI/Resources/tokens.json` and `client-android/app/src/main/assets/tokens.json`. Launch the SwiftUI/Compose scaffolds to sanity-check visuals after each capture.
  - Both scaffolds display the backend health status by calling the clone API (`http://localhost:4000/health` on iOS simulator / `http://10.0.2.2:4000/health` on Android emulator).
- Run automated QA summary via `automation/shared/qa_check.py` (pipeline hook) to confirm flows succeeded, screens were summarised, and endpoints captured; reports gate follow-up tasks.
- Review `docs/release-summary.json` after a pipeline run for a consolidated changelog snapshot.
- Compare against previous baselines using `automation/shared/diff_report.py docs/release-summary.json docs/release-summary.prev.json` to highlight new/removed flows and endpoints.
- Capture performance traces with `automation/ios/profile_instruments.sh` (Time Profiler) and `automation/android/profile_systrace.sh` (Perfetto/atrace) when benchmarking clone builds against the source app.
- Kick off `.github/workflows/release.yml` on demand or via schedule to rerun the capture/build pipeline, regenerate reports, and persist artefacts for review.
- Automate nightly captures with `automation/shared/scheduled_capture.sh`; see `docs/operations.md` for cron examples and incident response guidance.

### CI Integration Notes
- Add GitHub Actions secrets mirroring the SSH environment vars plus any API tokens required by binary download scripts.
- Use the orchestrator image (`mobile-clone/orchestrator:latest`) in jobs, mounting repository and providing the binary path via workflow artifacts.
- Gate merge by requiring the orchestrator workflow to pass, ensuring layout specs, assets, and backend contracts stay current.
