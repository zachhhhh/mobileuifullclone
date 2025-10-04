import { spawn } from 'node:child_process';
import path from 'node:path';
import { createWriteStream } from 'node:fs';
import { mkdir, writeFile } from 'node:fs/promises';

export type PipelineState = {
  id: string;
  platform: 'ios' | 'android';
  status: 'running' | 'succeeded' | 'failed';
  startedAt: string;
  completedAt?: string;
  logFile?: string;
  exitCode?: number;
  note?: string;
};

type LaunchOptions = {
  id: string;
  platform: 'ios' | 'android';
  binaryPath: string;
  logDir: string;
  logRelative: string;
  pipelineStatePath: string;
};

export async function launchPipeline({
  id,
  platform,
  binaryPath,
  logDir,
  logRelative,
  pipelineStatePath,
}: LaunchOptions) {
  await mkdir(logDir, { recursive: true });
  const logFilePath = path.join(logDir, logRelative);
  const state: PipelineState = {
    id,
    platform,
    status: 'running',
    startedAt: new Date().toISOString(),
    logFile: logRelative,
  };
  await writeFile(pipelineStatePath, JSON.stringify(state, null, 2));

  const out = spawn(
    'docker',
    [
      'compose',
      '-f',
      path.join(process.cwd(), '..', '.automation', 'docker-compose.yml'),
      'run',
      '--rm',
      'orchestrator',
      'python3',
      'automation/shared/run_pipeline.py',
      platform,
      binaryPath,
    ],
    {
      cwd: path.join(process.cwd(), '..'),
      stdio: ['ignore', 'pipe', 'pipe'],
    }
  );

  const logStream = createWriteStream(logFilePath);
  out.stdout?.pipe(logStream, { end: false });
  out.stderr?.pipe(logStream, { end: false });
  out.on('close', async (code) => {
    logStream.write(`\nPipeline exited with code ${code}\n`);
    logStream.end();
    const newState: PipelineState = {
      ...state,
      status: code === 0 ? 'succeeded' : 'failed',
      completedAt: new Date().toISOString(),
      exitCode: code ?? undefined,
    };
    try {
      await writeFile(pipelineStatePath, JSON.stringify(newState, null, 2));
    } catch (error) {
      console.error('Failed to write pipeline state', error);
    }
  });
  out.on('error', async (error) => {
    logStream.write(`\nFailed to launch pipeline: ${error.message}\n`);
    logStream.end();
    const newState: PipelineState = {
      ...state,
      status: 'failed',
      completedAt: new Date().toISOString(),
      note: 'Spawn error',
    };
    try {
      await writeFile(pipelineStatePath, JSON.stringify(newState, null, 2));
    } catch (writeError) {
      console.error('Failed to write pipeline state', writeError);
    }
  });
}
