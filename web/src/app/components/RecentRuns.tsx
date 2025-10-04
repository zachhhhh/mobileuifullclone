import path from 'node:path';
import { promises as fs } from 'node:fs';

interface RunEntry {
  id: string;
  appName: string;
  version: string;
  receivedAt: string;
  platform: string | null;
  status: string;
  logFile?: string;
  notes?: string;
  folder: string;
}

async function readRunDirectory(folderName: string, dir: string): Promise<RunEntry | null> {
  try {
    const metadataRaw = await fs.readFile(path.join(dir, 'metadata.json'), 'utf-8');
    const metadata = JSON.parse(metadataRaw) as Record<string, any>;
    const pipelinePath = path.join(dir, 'pipeline.json');
    let pipeline: Record<string, any> = {};
    try {
      const pipelineRaw = await fs.readFile(pipelinePath, 'utf-8');
      pipeline = JSON.parse(pipelineRaw);
    } catch (error) {
      pipeline = {};
    }
    return {
      id: metadata.id ?? path.basename(dir),
      appName: metadata.appName ?? 'Unknown',
      version: metadata.version ?? 'n/a',
      receivedAt: metadata.receivedAt ?? '',
      platform: metadata.platform ?? pipeline.platform ?? null,
      status: pipeline.status ?? 'pending',
      logFile: pipeline.logFile ?? metadata.pipelineLog,
      notes: pipeline.note ?? metadata.notes,
      folder: folderName,
    };
  } catch (error) {
    return null;
  }
}

async function loadRecentRuns(limit = 10): Promise<RunEntry[]> {
  const uploadsRoot = path.join(process.cwd(), 'storage', 'uploads');
  try {
    const dirs = await fs.readdir(uploadsRoot);
    const stats = await Promise.all(
      dirs.map(async (entry) => {
        const full = path.join(uploadsRoot, entry);
        try {
          const stat = await fs.stat(full);
          return stat.isDirectory() ? { full, folder: entry, mtime: stat.mtimeMs } : null;
        } catch (error) {
          return null;
        }
      })
    );
    const candidates = stats
      .filter((item): item is { full: string; folder: string; mtime: number } => item !== null)
      .sort((a, b) => b.mtime - a.mtime)
      .slice(0, limit);

    const runs = await Promise.all(candidates.map((candidate) => readRunDirectory(candidate.folder, candidate.full)));
    return runs.filter((run): run is RunEntry => run !== null);
  } catch (error) {
    return [];
  }
}

function formatDate(value: string) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default async function RecentRuns() {
  const runs = await loadRecentRuns();

  if (runs.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 text-sm text-slate-300">
        <h2 className="text-lg font-semibold text-slate-100">Recent Runs</h2>
        <p className="mt-2 text-slate-400">Uploads will appear here with pipeline status once processed.</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 text-sm text-slate-300">
      <h2 className="text-lg font-semibold text-slate-100">Recent Runs</h2>
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="text-slate-400">
            <tr>
              <th className="px-3 py-2">App</th>
              <th className="px-3 py-2">Version</th>
              <th className="px-3 py-2">Platform</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Received</th>
              <th className="px-3 py-2">Log</th>
              <th className="px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} className="border-t border-slate-800">
                <td className="px-3 py-2 font-medium text-slate-100">{run.appName}</td>
                <td className="px-3 py-2">{run.version || 'n/a'}</td>
                <td className="px-3 py-2 capitalize">{run.platform ?? 'unknown'}</td>
                <td className="px-3 py-2">
                  <span
                    className={
                      run.status === 'succeeded'
                        ? 'text-emerald-300'
                        : run.status === 'failed'
                        ? 'text-rose-300'
                        : run.status === 'running'
                        ? 'text-amber-300'
                        : 'text-slate-400'
                    }
                  >
                    {run.status}
                  </span>
                </td>
                <td className="px-3 py-2 text-slate-400">{formatDate(run.receivedAt)}</td>
                <td className="px-3 py-2">
                  {run.logFile ? (
                    <a
                      href={`/api/log?file=${encodeURIComponent(run.logFile)}`}
                      className="text-blue-300 hover:underline"
                    >
                      View
                    </a>
                  ) : (
                    <span className="text-slate-500">—</span>
                  )}
                </td>
                <td className="px-3 py-2">
                  {run.platform ? (
                    <form action="/api/retry" method="post">
                      <input type="hidden" name="folder" value={run.folder} />
                      <button
                        type="submit"
                        className="rounded-lg border border-blue-400 px-3 py-1 text-xs font-semibold text-blue-200 hover:bg-blue-500/10 disabled:cursor-not-allowed disabled:opacity-50"
                        disabled={run.status === 'running'}
                      >
                        Retry
                      </button>
                    </form>
                  ) : (
                    <span className="text-slate-500">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
