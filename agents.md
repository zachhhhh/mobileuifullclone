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

### Detailed Workflow Implementation Steps
- **Preflight Setup**
  1. Verify licensing scope and confirm target app bundle IDs/APK package names with legal/partner teams; record approvals in `docs/product-alignment.md`.
  2. Populate `.automation/config.yaml` with bundle IDs, binary sources, simulator/emulator profiles, secrets references, and notification targets.
  3. Provision artefact storage buckets + Git LFS; create required folders (`captures/`, `reports/`, `design-tokens/`) and enable lifecycle policies.
  4. Register CI secrets (store tokens, SSH credentials, Slack webhooks) and grant least-privilege access; test retrieval with a dry-run workflow dispatch.
  5. Pin orchestrator/tool container versions in `.automation/docker-compose.yml` and document them under `docs/toolchain-versions.md` for traceability.

- **Version Ingest Job**
  1. Configure App Store Connect and Play Developer API credentials in the CI secret store; populate `.automation/scripts/*/download_latest.sh` env vars (`ASC_KEY_ID`, `PLAY_SERVICE_ACCOUNT`).
  2. Schedule workflow triggers (`cron` + `workflow_dispatch`) so releases are polled at least daily; reference `.automation/workflows/shared-actions/fetch-version/` composite.
  3. Run `docker compose -f .automation/docker-compose.yml run --rm orchestrator python3 automation/shared/run_pipeline.py ios --stage ingest` to validate IPA download, checksum, and tagging.
  4. Confirm binary artefacts land in `captures/<platform>/binaries/<version>/` with SHA256 summary saved to `reports/<platform>/binary-digest.txt`.
  5. Tag repository with `source/<platform>/<version>` and push to origin; ensure `git describe` resolves inside downstream jobs.

- **Environment Provision Job**
  1. Bootstrap remote runners via `.automation/scripts/shared/bootstrap_remote.sh`; capture logs in `reports/setup/<platform>-bootstrap.log`.
  2. Define cache keys (`runner_version`, `simulator_os`, `npm_lock_hash`, `pip_requirements_hash`) inside the workflow step to reuse dependencies.
  3. Execute `python automation/shared/verify_toolchain.py <platform>` locally and on each runner; remediate missing binaries before marking job green.
  4. Store simulator/emulator snapshots using platform scripts (`bootstrap_simulator.sh`, `bootstrap_emulator.sh`); upload snapshot artefacts for reuse.
  5. Update `.automation/config.yaml` `environments` section with hostnames, workspace paths, and validation timestamp.

- **Appium Walkthrough Job**
  1. Author journey definitions in `automation/<platform>/flows.json` ensuring selectors favour accessibility IDs; add metadata for screenshots and expected checkpoints.
  2. Install dependencies (`npm ci` in `automation/<platform>/`) and lint scripts with `npm run lint`.
  3. Launch simulator/emulator via workflow step, start Appium server with orchestrator image, and execute `node automation/<platform>/walkthrough.mjs --run-id $RUN_ID`.
  4. Collect XML hierarchies + screenshots under `captures/<platform>/ui/<timestamp>/`; verify `reports/<platform>/ui-run.json` flags any failed steps.
  5. Fail the job if coverage thresholds (flows completed %, screen count) drop below values in `.automation/config.yaml:coverageThresholds`.

- **Network Capture Job**
  1. Start mitmproxy container using `.automation/docker-compose.yml` with certificates injected into the simulator/emulator trust store.
  2. Run `automation/<platform>/mitm_capture.py` inline add-on concurrently with walkthrough job; ensure proxy ports are configured via config file.
  3. After walkthrough completion, persist `.mitm` files and derived curl collections to `captures/<platform>/network/<timestamp>/`.
  4. Execute `python automation/shared/summarize_network.py <platform> <timestamp>` to build OpenAPI skeletons and normalized payload inventories.
  5. Generate diff against `captures/<platform>/network/latest/` using `automation/shared/diff_suite.py`; post Slack summary with key changes and risk rating.

- **Asset & Data Extraction Job**
  1. Mount app container or unpack binary (`automation/ios/extract_assets.py` or `automation/android/extract_assets.py`) with the run-specific binary path.
  2. Catalog images/fonts/strings/databases into manifests saved under `captures/<platform>/assets/<timestamp>/manifest.json`.
  3. Run baseline security scan via `python automation/shared/security_audit.py <platform> <timestamp>`; log findings to `reports/<platform>/security-audit.json`.
  4. Sync high-value assets (design-critical images, localized strings) into `design-tokens/<platform>/` and flag any missing translations.
  5. Upload artefact bundle to S3/GCS `artifacts/<platform>/assets/<timestamp>.tar.gz` and record checksum in `reports/<platform>/asset-digest.txt`.

- **Spec Generation Job**
  1. Invoke `automation/<platform>/generate_tokens.ts` with paths to latest layout dump + asset manifests; commit generated `design-tokens/<platform>/*.json` to repo.
  2. Convert mitmproxy outputs into API specs using `automation/shared/openapi_builder.py`; store results in `fixtures/shared/api-<platform>.yaml`.
  3. Generate component docs via `automation/shared/spec_compiler.py` which reads tokens and layout summaries to produce Markdown in `docs/specs/<platform>/`.
  4. Run schema validators (`npm run lint:tokens`, `spectral lint fixtures/shared/api-*.yaml`) to ensure output integrity.
  5. Publish spec artefacts to artefact store and tag git commit `specs/<platform>/<version>` when approved.

- **Backend Sync Job**
  1. Update backend fixtures by copying latest API specs and payload samples into `backend/fixtures/`.
  2. Execute `npm test -- --selectProjects contract` inside `backend/` to validate server behavior against captured fixtures.
  3. On mismatch, file issue via automation (`automation/shared/report_contract_drift.py`) attaching failing diffs and suggested fixes.
  4. Apply fixes under feature branches; rerun tests until parity is restored, then merge with required approvals.
  5. Promote updated backend containers/images after staging verification; note version in `reports/backend-sync.json`.

- **Client Build & Snapshot Job**
  1. Sync design tokens/assets into `client-ios` and `client-android` using `automation/shared/sync_client_assets.py`.
  2. Build iOS clone via `bundle exec fastlane clone_build` and Android clone via `./gradlew cloneBuild`; archive build logs to `reports/<platform>/build.log`.
  3. Run integration + UI parity tests, capturing Appium diffs to `reports/<platform>/visual-diff.html` and failing build on regression thresholds.
  4. Store generated IPAs/APKs in `captures/<platform>/builds/<version>/` with notarization/hardening status appended to manifest.
  5. Trigger optional beta distribution (TestFlight/Internal app sharing) only after security scans pass; document rollout plan in `docs/release-summary.json`.

- **Performance & Security Scan Job**
  1. Run platform profiling scripts (`automation/ios/profile_instruments.sh`, `automation/android/profile_systrace.sh`) on latest builds; compare metrics to thresholds in `.automation/config.yaml:performanceBudget`.
  2. Execute static/dynamic security checks (OWASP MASVS, certificate pinning validation, storage inspection) using scripts in `automation/shared/security/`.
  3. Collate results into `reports/<platform>/performance.csv` and `reports/<platform>/security-report.json`; mark job failed if deviations exceed risk tolerance.
  4. Open security review tickets for critical findings and block promotion until resolved; attach remediation ETA and owners.
  5. Update dashboards/alerts reflecting performance trends and security posture for leadership visibility.

- **Report & Notification Job**
  1. Aggregate per-stage outputs using `automation/shared/report_aggregator.py` to generate `reports/daily-summary.md`.
  2. Attach artefact links (binaries, UI captures, network diffs, performance results) and include run metadata (commit SHA, tool versions, timestamp).
  3. Post summary to Slack/Email/MS Teams using webhook settings from `.automation/config.yaml:notifications`; include severity tags for failed stages.
  4. Persist summary to long-term storage (`artifacts/reports/YYYY/MM/DD/`) and update `docs/release-summary.json` pointer to latest run.
  5. Schedule follow-up tasks (Jira/GitHub issues) automatically for any outstanding failures or manual review items.

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

### Step-by-Step Implementation
1. Validate macOS runner readiness by executing `.automation/scripts/ios/bootstrap_simulator.sh --validate` and confirming required device profiles exist.
2. Populate `automation/ios/flows.json` with onboarding, auth, core feature, paywall, profile, and offline toggles; commit updates alongside screenshot baselines.
3. Run `npm ci` inside `automation/ios/` and launch a dry-run walkthrough via `node automation/ios/walkthrough.mjs --run-id local-dev` to ensure selectors succeed.
4. Execute `python automation/ios/layout_dump.py captures/ios/ui/<timestamp>` to generate layout metrics, then inspect `reports/ios/layout-summary.json` for anomalies.
5. Use `python automation/ios/extract_assets.py captures/ios/binaries/<version>/app.ipa --out captures/ios/assets/<timestamp>` to mirror assets and update manifests.
6. Generate design tokens with `pnpm exec ts-node automation/ios/generate_tokens.ts --run <timestamp>` and sync results into `client-ios/Sources/CloneUI/Resources/tokens.json`.
7. Build and test via `bundle exec fastlane clone_build`; confirm Fastlane uploads artefacts to `captures/ios/builds/<version>/` and publishes test reports.
8. Trigger parity comparison using `node automation/ios/compare_snapshots.ts --baseline captures/ios/ui/latest --candidate captures/ios/ui/<timestamp>` and review diff HTML.
9. Record outcomes in `reports/ios/ui-run.json`, `reports/ios/visual-diff.html`, `reports/ios/assets-summary.json`, and update `docs/release-summary.json` with iOS-specific notes.
10. Before production promotion, perform enterprise distribution checks (notarization, MDM profile compatibility, plist entitlements) as documented in `docs/ios-enterprise-checklist.md`.

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

### Step-by-Step Implementation
1. Ensure Android runner satisfies prerequisites by executing `.automation/scripts/android/bootstrap_emulator.sh --validate` and verifying the configured AVD profile exists.
2. Define test journeys in `automation/android/flows.json` mirroring iOS coverage plus Android-specific flows (back navigation, system intents, notifications).
3. Install dependencies with `npm ci` inside `automation/android/` and execute `node automation/android/walkthrough.mjs --run-id local-dev` to capture a sample run.
4. Post-process UI hierarchies via `python automation/android/layout_dump.py captures/android/ui/<timestamp>`; inspect `reports/android/layout-summary.json` for widget coverage and accessibility ratios.
5. Run `python automation/android/extract_assets.py captures/android/binaries/<version>/app.apk --out captures/android/assets/<timestamp>` to extract resources, strings, and databases.
6. Generate Compose tokens/themes using `pnpm exec ts-node automation/android/generate_tokens.ts --run <timestamp>` and push outputs to `client-android/app/src/main/assets/tokens.json`.
7. Build the clone with `./gradlew clean cloneBuild` and confirm instrumentation + screenshot tests upload their reports under `reports/android/tests/`.
8. Execute parity comparison using `node automation/android/compare_snapshots.ts --baseline captures/android/ui/latest --candidate captures/android/ui/<timestamp>` and resolve any diffs above threshold.
9. Update `reports/android/ui-run.json`, `reports/android/visual-diff.html`, and `reports/android/assets-summary.json`; append findings to `docs/release-summary.json`.
10. Prior to enterprise rollout, satisfy Play integrity requirements (signing keys, Play Protect verdict, app bundle validation) referencing `docs/android-enterprise-checklist.md`.

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
- Initial app loading state is driven by `GET /session`, returning mock authentication/onboarding/feature flag payloads (override defaults via environment variables such as `DEFAULT_AUTHENTICATED`).
  - Additional lifecycle endpoints: `POST /auth/login`, `POST /auth/logout`, `POST /onboarding/advance`, and `GET /feed` (requires authenticated session). Defaults configurable in `backend/.env`.
  - Paywall endpoints (`GET /paywall`, `POST /paywall/purchase`) and profile/flag management (`GET/POST /profile`, `POST /feature-flags`) drive premium upgrades and settings toggles. Notifications preview lives at `GET /notifications/preview`. Downloads are mocked with `POST/DELETE /content/:id/download`, playback progress persists via `POST /content/:id/progress`, and analytics events can be captured through `POST /analytics/events`.

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
  - SwiftUI scaffolding (`client-ios/`) now renders feed cards via `FeedCard`, shows shimmer skeletons while loading, presents paywall (`PaywallView`), notification previews, profile management (`ProfileView`), and content detail/player sheets with offline download toggles and progress tracking. Android Compose mirror provides shimmer placeholders, animated feed cards, paywall/notification/profile sheets, analytics logging, and download-enabled detail UI.
- **QA & Compliance**: define unit/integration/E2E suites, snapshot diff baselines, contract tests, accessibility audits, performance thresholds, security scans, and store-review compliance checklists.
  - Baseline QA report generated by `automation/shared/qa_check.py` summarises flow coverage, failed steps, screen counts, and captured endpoints to catch regressions early.
- **Release Engineering**: configure build pipelines, signing assets, app store metadata, rollout strategies, crash reporting, and telemetry dashboards for cloned clients.
  - Release summary generated at `docs/release-summary.json` captures latest capture metrics and audit outcomes for distribution sign-off.
- **Operational Maintenance**: schedule update detectors, automated diff reports, incident response runbooks, documentation updates, and onboarding guides for new contributors.
  - Use `automation/shared/release_report.py` + `automation/shared/diff_report.py` in scheduled workflows to detect upstream changes and generate actionable diffs.

## Backend Architecture
- **Tech Stack**: Node 20 + Express 4 with Helmet + CORS. Configuration lives in `backend/.env` (see `.env.example`).
- **In-memory state**: `session`, `featureFlags`, `progress`, `downloads`, and `analyticsEvents` are stored in the server instance so automated runs stay deterministic.
- **Endpoints**:
  | Route | Method | Purpose |
  | ----- | ------ | ------- |
  | `/health` | GET | Readiness probe used by clients/tests. |
  | `/session` | GET | Returns auth status, onboarding status, feature flags. |
  | `/auth/login`, `/auth/logout` | POST | Mutate authentication state; credentials are controlled by env vars. |
  | `/onboarding/advance` | POST | Moves onboarding workflow forward or marks completion. |
  | `/feed` | GET | Lists curated content cards (includes duration, difficulty, tags). |
  | `/content/:id` | GET | Provides stream metadata, instructor info, cover art, and saved playback progress. |
  | `/content/:id/progress` | POST | Persists playback position/completion. |
  | `/content/:id/download` | POST/DELETE | Mock download lifecycle (creates `downloads` entry or removes it). |
  | `/paywall` | GET | Returns feature flag + available plans. |
  | `/paywall/purchase` | POST | Marks user as premium. |
  | `/profile` | GET/POST | Fetch/update display name and return feature flags for settings toggles. |
  | `/feature-flags` | POST | Toggle paywall/notifications flags. |
  | `/notifications/preview` | GET | Provides sample push payload view (title/body/deep link). |
  | `/analytics/events` | POST | Records arbitrary analytics payloads for inspection. |
- **Extending**: Swap the in-memory stores with a database (Postgres/Redis) before production. Preserve response contracts established by the automation fixtures.

## Client Architecture – iOS
- **State containers**: `TokenStore` for design tokens; `AppState` orchestrates session/phases, paywall plans, notifications, downloads, analytics logging.
- **Networking**: `BackendClient` (actor) wraps all endpoints, providing typed responses (`SessionResponse`, `ContentDetail`, `PaywallPlan`, etc.).
- **Flows implemented**:
  - Splash/auth/onboarding/home handled by `AppState.phase` and presented inside `RootView`.
  - Skeleton loading with shimmer (`FeedSkeletonList` / `FeedSkeletonCard`).
  - Paywall sheet (`PaywallView`) gating premium functionality with env-driven feature flags.
  - Notification preview sheet (`NotificationPreviewView`).
  - Profile sheet (`ProfileView`) for name updates + feature-flag toggles.
  - Content detail sheet (`FeedDetailView`) with artwork, metadata, slider controls, skip/play buttons, offline download toggle, and progress persistence.
- **Analytics**: `AppState` calls `backend.logEvent` for key milestones (content view/progress, downloads, paywall view/purchase, notification preview, feature toggles, profile updates).
- **Offline stub**: `downloadContent`/`removeDownload` update in-memory set and UI badges; wire into a local file manager when adding real downloads.

## Client Architecture – Android
- **State container**: `UiState` holds phase, tokens, feed, profile, notification preview, downloads, and current content/progress. Coroutine-powered `TokenScreen` orchestrates refresh/login/onboarding.
- **Networking**: `BackendClient` mirrors iOS endpoints with serialization via Kotlinx; includes `logEvent`, `contentDetail`, `updateProgress`, `requestDownload`, and `deleteDownload`.
- **UI components**:
  - Skeleton list (`FeedSkeletonList`) with animated shimmer brush.
  - `HomeView` featuring animated feed cards (`animateItemPlacement`), paywall/notification/profile buttons, download badges.
  - Paywall, notification preview, and profile sheets using Material3 bottom sheets and alert dialogs.
  - `ContentDetailSheet` replicates the playback UI (slider, skip buttons, download toggle) with progress updates.
- **Analytics**: `backend.logEvent` invoked during paywall view/purchase, profile updates, notification previews, downloads, and content progress changes.

## Localization & Accessibility Backlog
- Extract user-facing strings into `.strings`/`strings.xml` resources and wire language toggles into testing pipelines.
- Validate layouts under Dynamic Type / large font settings and ensure content scales without truncation.
- Provide VoiceOver/TalkBack labels for actionable controls (e.g., feed cards, playback buttons, paywall plans, profile toggles).
- Exercise RTL locales in Appium flows (set `locale=ar` in `flows.json`) to verify layout mirroring.
- Capture accessibility snapshots regularly using `xcrun accessibilityAudit` and Android Accessibility Scanner; push results to `reports/<platform>/a11y/`.

## Automation TODOs
- Add Appium coverage for paywall purchase, download toggle, notification preview, and profile name changes.
- Integrate content playback steps (seek, mark complete) into walkthrough scripts; sync results to QA report.
- Extend Test Lab/real-device matrices with offline scenarios (airplane mode) to validate download persistence.
- Prepare localization regression tests once translations land.

## Offline & Downloads
- Downloads remain mock entries but drive UI state (badges, toggle buttons). Upgrade path:
  1. Replace `requestDownload` with real file transfer + store assets under an app-managed directory (e.g., `FileManager` on iOS, `Context.getExternalFilesDir` on Android).
  2. Persist download status in local storage (Core Data/Room) and reconcile with `AppState.downloads`/`UiState.downloads`.
  3. Add background download handling (URLSession background tasks / WorkManager).
  4. Extend Appium flows to validate offline playback (airplane mode scenarios).

## Analytics & Telemetry
- Mock endpoint `/analytics/events` collects instrumentation from both clients. Inspect `state.analyticsEvents` in the backend to confirm payloads.
- Event names currently emitted: `content_view`, `content_progress`, `download`, `download_delete`, `paywall_view`, `purchase`, `notification_preview`, `feature_flags_update`, `profile_update`.
- Feed these events into your analytics stack (Segment/GA4/Amplitude) once real infrastructure is ready.

## Device Farms & QA Enhancements
- CI runbook (`docs/real-device-testing.md`) outlines hybrid strategy: start with Firebase Test Lab (virtual + physical Android) then add hosted grids for iOS.
- Integrate Appium suites with Test Lab via `automation/android/testlab_run.sh` and plan a BrowserStack/Bitrise migration for iOS hardware.
- Update Appium `flows.json` to cover paywall, download toggles, notification previews, and profile edits before enabling farm automation.

## Localization & Accessibility Backlog
- Extract user-facing strings into `.strings`/`strings.xml` resources and wire language toggles into testing pipelines.
- Validate layouts under Dynamic Type / large font settings and ensure content scales without truncation.
- Provide VoiceOver/TalkBack labels for actionable controls (e.g., feed cards, playback buttons, paywall plans, profile toggles).
- Exercise RTL locales in Appium flows (set `locale=ar` in `flows.json`) to verify layout mirroring.
- Capture accessibility snapshots regularly using `xcrun accessibilityAudit` and Android Accessibility Scanner; push results to `reports/<platform>/a11y/`.

## Automation TODOs
- Add Appium coverage for paywall purchase, download toggle, notification preview, and profile name changes.
- Integrate content playback steps (seek, mark complete) into walkthrough scripts; sync results to QA report.
- Extend Test Lab/real-device matrices with offline scenarios (airplane mode) to validate download persistence.
- Prepare localization regression tests once translations land.

## Offline & Downloads
- Downloads remain mock entries but drive UI state (badges, toggle buttons). Upgrade path:
  1. Replace `requestDownload` with real file transfer + store assets under an app-managed directory (e.g., `FileManager` on iOS, `Context.getExternalFilesDir` on Android).
  2. Persist download status in local storage (Core Data/Room) and reconcile with `AppState.downloads`/`UiState.downloads`.
  3. Add background download handling (URLSession background tasks / WorkManager).
  4. Extend Appium flows to validate offline playback (airplane mode scenarios).

## Analytics & Telemetry
- Mock endpoint `/analytics/events` collects instrumentation from both clients. Inspect `state.analyticsEvents` in the backend to confirm payloads.
- Event names currently emitted: `content_view`, `content_progress`, `download`, `download_delete`, `paywall_view`, `purchase`, `notification_preview`, `feature_flags_update`, `profile_update`.
- Feed these events into your analytics stack (Segment/GA4/Amplitude) once real infrastructure is ready.

## Device Farms & QA Enhancements
- CI runbook (`docs/real-device-testing.md`) outlines hybrid strategy: start with Firebase Test Lab (virtual + physical Android) then add hosted grids for iOS.
- Integrate Appium suites with Test Lab via `automation/android/testlab_run.sh` and plan a BrowserStack/Bitrise migration for iOS hardware.
- Update Appium `flows.json` to cover paywall, download toggles, notification previews, and profile edits before enabling farm automation.

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
- Extend device coverage with Firebase Test Lab via `automation/android/testlab_run.sh` (requires `gcloud`); add hosted real-device runs following `docs/real-device-testing.md` once virtual matrices are stable.
- For design reference, review skeleton/premium/profile UX in the clients: shimmer placeholders (`FeedSkeletonList` / `FeedSkeletonCard`), animated feed entries (`animateItemPlacement`), paywall sheets, notification previews, and profile toggles.

### CI Integration Notes
- Add GitHub Actions secrets mirroring the SSH environment vars plus any API tokens required by binary download scripts.
- Use the orchestrator image (`mobile-clone/orchestrator:latest`) in jobs, mounting repository and providing the binary path via workflow artifacts.
- Gate merge by requiring the orchestrator workflow to pass, ensuring layout specs, assets, and backend contracts stay current.

### Observability & Monitoring
- Export structured logs from orchestrator runs and remote runners; forward to your centralized logging stack with context tags (`run_id`, `platform`, `binary_version`, `workflow_job`).
- Collect pipeline metrics (duration, failure rate, asset counts) via Prometheus/OpenTelemetry exporters in `.automation/docker-compose.yml`; surface dashboards tracking trend regressions.
- Stream Appium/mitmproxy traces into long-term storage so UI/network anomalies can be investigated after artefacts are rotated.
- Alert on SLA breaches (e.g., ingest job failure, walkthrough diff spike) using PagerDuty/Slack hooks defined in `.automation/config.yaml` under `notifications.alerts`.

### Incident Response & Rollback
- Maintain runbooks under `docs/operations/*.md` outlining triage for ingest failures, simulator instability, backend drift, or credential expiration.
- Automate rollback workflows (`.automation/workflows/reset-baseline.yml`) that restore the previous artefact baseline and revert generated specs if regression thresholds are exceeded.
- Require hotfix branches to reference incident IDs and attach remediation artefacts before merging back into `main`.
- Capture postmortem templates in `docs/postmortems/` and schedule automated retro reminders when a workflow sets `incident=true`.

### Knowledge Transfer & Onboarding
- Keep `docs/onboarding.md` current with environment setup, required credentials, and safe test binaries so new operators can run dry-runs without production data.
- Record short loom-style walkthroughs of pipeline stages and link them inside `docs/playbooks/` for asynchronous training.
- Tag subject-matter owners in `.automation/config.yaml` (`ownership:` block) so escalations route to the correct maintainers automatically.
- Review automation coverage quarterly; log gaps or deprecated steps in `docs/roadmap.md` and convert approved items into tracker issues.
