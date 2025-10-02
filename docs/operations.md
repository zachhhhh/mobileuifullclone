# Operational Runbook

## Scheduled Captures
- Export `CLONE_IPA_PATH`/`CLONE_APK_PATH` to point at the latest binaries
- Execute `automation/shared/scheduled_capture.sh` (cron/CI) to run the pipeline for both platforms
- Review `docs/release-summary.json` and `docs/release-diff.json`; archive previous summaries as `docs/release-summary.prev.json`

Example cron entry (runs daily 2am):
```
0 2 * * * /usr/local/bin/bash -lc "cd /path/to/repo && CLONE_IPA_PATH=path/to/app.ipa CLONE_APK_PATH=path/to/app.apk automation/shared/scheduled_capture.sh >> logs/capture.log 2>&1"
```

## Incident Response
- On failed QA or security audit, create an issue referencing the report artefacts
- Roll back to last known good release summary stored under `docs/releases/`
- Notify stakeholders via configured channels (Slack/email)

## Onboarding
- Share `docs/product-alignment.md`, `docs/security-hardening.md`, and this runbook with new contributors
- Provide access to remote simulator hosts and environment secrets vault
