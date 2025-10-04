import fs from 'fs';
import path from 'path';

type EntryMap = Map<string, { size: number; file: string }>;

type CompareSummary = {
  platform: string;
  baselineCount: number;
  candidateCount: number;
  added: string[];
  removed: string[];
  sizeChanged: Array<{ file: string; baseline: number; candidate: number }>;
};

const args = process.argv.slice(2);
const params: Record<string, string> = {};
for (let i = 0; i < args.length; i += 2) {
  const key = args[i];
  const value = args[i + 1];
  if (key && key.startsWith('--') && value !== undefined) {
    params[key.slice(2)] = value;
  }
}

if (!params.baseline || !params.candidate) {
  console.error('Usage: compare_snapshots.ts --baseline <dir> --candidate <dir> [--output <json>]');
  process.exit(1);
}

const workspace = path.resolve(__dirname, '..', '..');

function collectSnapshots(directory: string): EntryMap {
  const entries: EntryMap = new Map();
  if (!fs.existsSync(directory)) {
    return entries;
  }
  const walk = (dir: string) => {
    fs.readdirSync(dir).forEach((item) => {
      const full = path.join(dir, item);
      const stat = fs.statSync(full);
      if (stat.isDirectory()) {
        walk(full);
      } else if (item.toLowerCase().endsWith('.png')) {
        const key = path.relative(directory, full);
        entries.set(key, { size: stat.size, file: full });
      }
    });
  };
  walk(directory);
  return entries;
}

const baseline = collectSnapshots(path.resolve(params.baseline));
const candidate = collectSnapshots(path.resolve(params.candidate));

const added: string[] = [];
const removed: string[] = [];
const sizeChanged: Array<{ file: string; baseline: number; candidate: number }> = [];

candidate.forEach((value, key) => {
  if (!baseline.has(key)) {
    added.push(key);
  }
});

baseline.forEach((value, key) => {
  if (!candidate.has(key)) {
    removed.push(key);
    return;
  }
  const candidateEntry = candidate.get(key)!;
  if (candidateEntry.size !== value.size) {
    sizeChanged.push({ file: key, baseline: value.size, candidate: candidateEntry.size });
  }
});

const summary: CompareSummary = {
  platform: 'android',
  baselineCount: baseline.size,
  candidateCount: candidate.size,
  added,
  removed,
  sizeChanged,
};

if (params.output) {
  fs.writeFileSync(path.resolve(params.output), JSON.stringify(summary, null, 2));
}

console.log(`Android snapshot diff: baseline=${baseline.size} candidate=${candidate.size}`);
if (added.length) {
  console.log(`  Added (${added.length}): ${added.slice(0, 10).join(', ')}`);
}
if (removed.length) {
  console.log(`  Removed (${removed.length}): ${removed.slice(0, 10).join(', ')}`);
}
if (sizeChanged.length) {
  console.log(`  Size changed (${sizeChanged.length}): ${sizeChanged.slice(0, 10).map((entry) => entry.file).join(', ')}`);
}
