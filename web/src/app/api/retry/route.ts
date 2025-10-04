import { NextResponse } from 'next/server';
import path from 'node:path';
import { readFile, stat } from 'node:fs/promises';
import { launchPipeline } from '@/lib/pipeline';

const UPLOAD_ROOT = path.join(process.cwd(), 'storage', 'uploads');
const LOG_ROOT = path.join(process.cwd(), 'storage', 'logs');

function normalizeFolder(folder: string) {
  const normalized = path.normalize(folder);
  if (normalized.includes('..')) {
    throw new Error('invalid folder');
  }
  const resolved = path.join(UPLOAD_ROOT, normalized);
  if (!resolved.startsWith(UPLOAD_ROOT)) {
    throw new Error('invalid folder');
  }
  return { normalized, resolved };
}

export async function POST(request: Request) {
  const contentType = request.headers.get('content-type') || '';
  let folder: string | null = null;
  if (contentType.includes('application/json')) {
    const body = await request.json();
    folder = body.folder ?? null;
  } else {
    const formData = await request.formData();
    const value = formData.get('folder');
    folder = typeof value === 'string' ? value : null;
  }

  if (!folder) {
    return NextResponse.json({ error: 'folder parameter required' }, { status: 400 });
  }

  try {
    const { normalized, resolved } = normalizeFolder(folder);
    await stat(resolved);
    const metadataPath = path.join(resolved, 'metadata.json');
    const metadataRaw = await readFile(metadataPath, 'utf-8');
    const metadata = JSON.parse(metadataRaw) as Record<string, any>;
    const platform = metadata.platform;
    if (platform !== 'ios' && platform !== 'android') {
      return NextResponse.json({ error: 'platform missing from metadata' }, { status: 400 });
    }
    const filename = metadata.filename;
    if (typeof filename !== 'string') {
      return NextResponse.json({ error: 'binary filename missing from metadata' }, { status: 400 });
    }
    const binaryPath = path.join(resolved, filename);
    try {
      await stat(binaryPath);
    } catch (error) {
      return NextResponse.json({ error: 'binary not found for run' }, { status: 404 });
    }

    const logRelative = `${metadata.id ?? normalized}-${platform}-retry-${Date.now()}.log`;
    const pipelineStatePath = path.join(resolved, 'pipeline.json');
    await launchPipeline({
      id: metadata.id ?? normalized,
      platform,
      binaryPath,
      logDir: LOG_ROOT,
      logRelative,
      pipelineStatePath,
    });

    const accept = request.headers.get('accept') || '';
    if (accept.includes('application/json')) {
      return NextResponse.json({ status: 'started', folder: normalized, log: logRelative });
    }
    return NextResponse.redirect(new URL('/', request.url));
  } catch (error) {
    return NextResponse.json({ error: (error as Error).message }, { status: 400 });
  }
}
