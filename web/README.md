# Clone Intake Portal

A lightweight Next.js front-end for uploading IPA/APK binaries and attaching metadata before triggering the automation pipeline.

## Getting Started

```bash
cd web
npm install
npm run dev
```

The app listens on `http://localhost:3000` by default. Drop an `.ipa`, `.apk`, or `.aab` file on the upload card, fill out the metadata fields, and submit. Files are stored under `web/storage/uploads/<timestamp>-<app-slug>/` alongside a `metadata.json` snapshot.

By default the upload API immediately spawns the orchestrator via Docker Compose and streams logs to `web/storage/logs/<run-id>-<platform>.log`. Disable this behaviour with `AUTO_RUN_PIPELINE=false` before starting the dev server if you prefer manual control.

The home page lists recent uploads with their pipeline status; click **View** to stream the associated log (`/api/log?file=<run-id>.log`) or hit **Retry** to re-run the pipeline on an existing binary (`POST /api/retry`).

## Environment

- Node 18+
- Next.js 14 (App Router)

To enable HTTPS or external storage, adapt `src/app/api/upload/route.ts` to push directly into S3/GCS and emit events for your chosen orchestrator.
