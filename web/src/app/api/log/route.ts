import { NextResponse } from 'next/server';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

const LOG_ROOT = path.join(process.cwd(), 'storage', 'logs');

export async function GET(request: Request) {
  const url = new URL(request.url);
  const fileParam = url.searchParams.get('file');
  if (!fileParam) {
    return NextResponse.json({ error: 'file parameter required' }, { status: 400 });
  }

  const normalized = path.normalize(fileParam);
  if (normalized.includes('..')) {
    return NextResponse.json({ error: 'invalid file path' }, { status: 400 });
  }

  const target = path.join(LOG_ROOT, normalized);
  try {
    const content = await readFile(target, 'utf-8');
    return new NextResponse(content, {
      status: 200,
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-store',
      },
    });
  } catch (error) {
    return NextResponse.json({ error: 'log not found' }, { status: 404 });
  }
}
