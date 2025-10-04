import { mkdir, writeFile } from 'node:fs/promises';
import { NextResponse } from 'next/server';
import crypto from 'node:crypto';
import path from 'node:path';
import { launchPipeline } from '@/lib/pipeline';

const STORAGE_ROOT = path.join(process.cwd(), 'storage', 'uploads');
const LOG_ROOT = path.join(process.cwd(), 'storage', 'logs');

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
    .slice(0, 40);
}

type SkippedState = {
  id: string;
  platform: null;
  status: 'skipped';
  startedAt: string;
  completedAt: string;
  note: string;
};

async function savePipelineState(filePath: string, state: SkippedState) {
  await writeFile(filePath, JSON.stringify(state, null, 2));
}

export async function POST(request: Request) {
  const formData = await request.formData();
  const file = formData.get('binary');
  if (!(file instanceof File)) {
    return NextResponse.json({ error: 'binary field missing' }, { status: 400 });
  }

  const appName = (formData.get('appName') as string | null) ?? 'unknown-app';
  const version = (formData.get('version') as string | null) ?? 'unversioned';
  const notes = (formData.get('notes') as string | null) ?? '';

  const id = `${Date.now()}-${crypto.randomUUID()}`;
  const folderName = `${new Date().toISOString().replace(/[:.]/g, '-')}-${slugify(appName) || 'app'}`;
  const targetDir = path.join(STORAGE_ROOT, folderName);
  await mkdir(targetDir, { recursive: true });

  const buffer = Buffer.from(await file.arrayBuffer());
  const filename = file.name || `${slugify(appName) || 'binary'}.bin`;
  const binaryPath = path.join(targetDir, filename);
  await writeFile(binaryPath, buffer);

  const ext = path.extname(filename).toLowerCase();
  const platform = ext === '.ipa' ? 'ios' : ['.apk', '.aab'].includes(ext) ? 'android' : null;
  const logRelative = platform ? `${id}-${platform}.log` : null;

  const metadata = {
    id,
    receivedAt: new Date().toISOString(),
    appName,
    version,
    notes,
    filename,
    sizeBytes: buffer.length,
    platform,
    pipelineLog: logRelative,
  };

  await writeFile(path.join(targetDir, 'metadata.json'), JSON.stringify(metadata, null, 2));

  if (process.env.AUTO_RUN_PIPELINE !== 'false' && platform) {
    const pipelineStatePath = path.join(targetDir, 'pipeline.json');
    await launchPipeline({
      id,
      platform,
      binaryPath,
      logDir: LOG_ROOT,
      logRelative: logRelative!,
      pipelineStatePath,
    });
  } else if (!platform) {
    const pipelineStatePath = path.join(targetDir, 'pipeline.json');
    const state: SkippedState = {
      id,
      platform: null,
      status: 'skipped',
      startedAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
      note: 'Unsupported binary extension',
    };
    await savePipelineState(pipelineStatePath, state);
  }

  return NextResponse.json({ id, filename, sizeBytes: buffer.length, storedAt: targetDir });
}
