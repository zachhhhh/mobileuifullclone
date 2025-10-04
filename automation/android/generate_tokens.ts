import fs from 'fs';
import path from 'path';

interface FlowSummary {
  name?: string;
  slug?: string;
  status?: string;
  screenshot?: string;
  hierarchy?: string;
}

const args = process.argv.slice(2);
const params: Record<string, string> = {};
for (let i = 0; i < args.length; i += 2) {
  const key = args[i];
  const value = args[i + 1];
  if (key && key.startsWith('--') && value !== undefined) {
    params[key.slice(2)] = value;
  }
}

const workspace = path.resolve(__dirname, '..', '..');
const captureRoot = params.input ? path.resolve(params.input) : path.join(workspace, 'captures', 'android', 'ui');
const designRoot = params.output ? path.resolve(params.output) : path.join(workspace, 'design-tokens', 'android');
const reportsRoot = path.join(workspace, 'reports', 'android');

const latestRunFile = path.join(captureRoot, 'latest-run.txt');
let runId = params.run;
if (!runId && fs.existsSync(latestRunFile)) {
  runId = fs.readFileSync(latestRunFile, 'utf-8').trim();
}

let summary: { flows?: FlowSummary[] } = {};
if (runId) {
  const summaryPath = path.join(captureRoot, runId, 'summary.json');
  if (fs.existsSync(summaryPath)) {
    summary = JSON.parse(fs.readFileSync(summaryPath, 'utf-8'));
  }
}

const layoutPath = path.join(captureRoot, 'layout-summary.json');
let layout: { screens?: Record<string, unknown> } = {};
if (fs.existsSync(layoutPath)) {
  layout = JSON.parse(fs.readFileSync(layoutPath, 'utf-8'));
}

const screens: Record<string, unknown> = {};
(summary.flows || []).forEach((flow) => {
  const slug = flow.slug || flow.name || 'flow';
  screens[slug] = {
    name: flow.name,
    status: flow.status,
    screenshot: flow.screenshot,
    hierarchy: flow.hierarchy,
  };
});

Object.entries(layout.screens ?? {}).forEach(([slug, metrics]) => {
  screens[slug] = Object.assign({}, screens[slug] || {}, { metrics });
});

const tokens = {
  generatedAt: new Date().toISOString(),
  runId: runId ?? null,
  theme: {
    colors: {
      primary: '#4C6EF5',
      secondary: '#51CF66',
      surface: '#FFFFFF',
      surfaceVariant: '#F1F3F5',
    },
    typography: {
      titleLarge: { sizeSp: 22, lineHeightSp: 28, font: 'Roboto', weight: '600' },
      bodyMedium: { sizeSp: 16, lineHeightSp: 22, font: 'Roboto', weight: '400' },
    },
    spacing: {
      scaleDp: [4, 8, 12, 16, 24, 32],
    },
  },
  screens,
};

fs.mkdirSync(designRoot, { recursive: true });
const tokensPath = path.join(designRoot, 'tokens.json');
fs.writeFileSync(tokensPath, JSON.stringify(tokens, null, 2));
console.log(`Wrote Android design tokens to ${tokensPath}`);

fs.mkdirSync(reportsRoot, { recursive: true });
const summaryPath = path.join(reportsRoot, 'tokens-summary.json');
fs.writeFileSync(summaryPath, JSON.stringify({ runId: tokens.runId, screenCount: Object.keys(screens).length }, null, 2));
console.log(`Wrote token summary to ${summaryPath}`);
