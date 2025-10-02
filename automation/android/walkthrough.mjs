import { remote } from 'webdriverio';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const args = process.argv.slice(2);
const params = {};
for (let i = 0; i < args.length; i += 2) {
  params[args[i].replace(/^--/, '')] = args[i + 1];
}

if (!params.app || !params.output) {
  console.error('Usage: walkthrough.mjs --app <APK/AAB> --output <dir>');
  process.exit(1);
}

const ensureDir = (dir) => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
};

const slugify = (value, fallback) => {
  if (!value) return fallback;
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '') || fallback;
};

const timeoutMs = Number(process.env.APPIUM_STEP_TIMEOUT ?? 10000);
const runId = new Date().toISOString().replace(/[:.]/g, '-');
const runDir = path.join(path.resolve(params.output), runId);
ensureDir(runDir);

const summary = {
  platform: 'android',
  runId,
  startedAt: new Date().toISOString(),
  app: params.app,
  flows: [],
};

const flowsPath = path.join(__dirname, 'flows.json');
if (!fs.existsSync(flowsPath)) {
  console.error(`Flows file missing: ${flowsPath}`);
  process.exit(1);
}

const flows = JSON.parse(fs.readFileSync(flowsPath, 'utf-8'));
if (!Array.isArray(flows) || flows.length === 0) {
  console.warn('No flows configured.');
}

const run = async () => {
  const caps = {
    platformName: 'Android',
    automationName: 'UiAutomator2',
    app: params.app,
    deviceName: process.env.ANDROID_DEVICE || 'Pixel_7_Pro_API_34',
    platformVersion: process.env.ANDROID_OS_VERSION || '14',
    noReset: true,
    newCommandTimeout: 300,
  };

  const driver = await remote({
    path: '/wd/hub',
    hostname: process.env.APPIUM_HOST || '127.0.0.1',
    port: Number(process.env.APPIUM_PORT || 4723),
    capabilities: caps,
  });

  let hasFailure = false;

  for (let i = 0; i < flows.length; i += 1) {
    const flow = flows[i];
    const flowName = flow.name || `flow-${i + 1}`;
    const flowSlug = flow.slug || slugify(flowName, `flow-${i + 1}`);
    const flowDir = path.join(runDir, flowSlug);
    ensureDir(flowDir);

    const flowResult = {
      name: flowName,
      slug: flowSlug,
      description: flow.description || '',
      steps: [],
      status: 'passed',
    };

    console.log(`\n[Flow] ${flowName}`);

    for (let stepIndex = 0; stepIndex < (flow.steps || []).length; stepIndex += 1) {
      const step = flow.steps[stepIndex];
      const record = {
        index: stepIndex,
        action: step.action,
        description: step.description || '',
        selector: step.selector || null,
        status: 'pending',
      };
      const startedAt = Date.now();

      try {
        switch (step.action) {
          case 'tap': {
            if (!step.selector) throw new Error('selector required for tap');
            const element = await driver.$(step.selector);
            await element.waitForExist({ timeout: step.timeout ?? timeoutMs });
            await element.click();
            break;
          }
          case 'input': {
            if (!step.selector) throw new Error('selector required for input');
            const element = await driver.$(step.selector);
            await element.waitForExist({ timeout: step.timeout ?? timeoutMs });
            if (step.clear !== false && element.clearValue) {
              try {
                await element.clearValue();
              } catch (clearErr) {
                console.warn(`Unable to clear value: ${clearErr.message}`);
              }
            }
            await element.setValue(step.value ?? '');
            break;
          }
          case 'waitFor': {
            if (!step.selector) throw new Error('selector required for waitFor');
            const element = await driver.$(step.selector);
            if (step.state === 'hidden') {
              await element.waitForDisplayed({ timeout: step.timeout ?? timeoutMs, reverse: true });
            } else {
              await element.waitForDisplayed({ timeout: step.timeout ?? timeoutMs });
            }
            break;
          }
          case 'sleep':
            await driver.pause(step.ms ?? 1000);
            break;
          case 'back':
            await driver.back();
            break;
          case 'hideKeyboard':
            try {
              await driver.hideKeyboard();
            } catch (hideErr) {
              console.warn(`hideKeyboard ignored: ${hideErr.message}`);
            }
            break;
          case 'keys':
            await driver.keys(step.value ?? '');
            break;
          default:
            throw new Error(`Unknown action: ${step.action}`);
        }
        record.status = 'passed';
      } catch (err) {
        record.status = 'failed';
        record.error = err?.message ?? String(err);
        flowResult.status = 'failed';
        flowResult.error = record.error;
        hasFailure = true;
        console.error(` ❌ [${flowName}] step ${stepIndex} failed: ${record.error}`);
        if (!step.continueOnError) {
          flowResult.steps.push({ ...record, durationMs: Date.now() - startedAt });
          break;
        }
      }

      record.durationMs = Date.now() - startedAt;
      flowResult.steps.push(record);
    }

    const screenshotBase = flow.screenshot || flowSlug;
    const screenshotPath = path.join(flowDir, `${screenshotBase}.png`);
    const sourcePath = path.join(flowDir, 'source.xml');
    try {
      await driver.saveScreenshot(screenshotPath);
      const source = await driver.getPageSource();
      fs.writeFileSync(sourcePath, source, 'utf-8');
      flowResult.screenshot = path.relative(process.cwd(), screenshotPath);
      flowResult.hierarchy = path.relative(process.cwd(), sourcePath);
    } catch (err) {
      console.warn(`Unable to write capture for ${flowName}: ${err.message}`);
    }

    flowResult.directory = path.relative(process.cwd(), flowDir);
    summary.flows.push(flowResult);
  }

  await driver.deleteSession();

  summary.finishedAt = new Date().toISOString();
  summary.status = hasFailure ? 'failed' : 'passed';
  const summaryPath = path.join(runDir, 'summary.json');
  fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2), 'utf-8');
  fs.writeFileSync(path.join(path.resolve(params.output), 'latest-run.txt'), `${runId}\n`, 'utf-8');

  console.log(`\nCaptured flows written to ${runDir}`);
  if (hasFailure) {
    console.error('One or more flows failed. Review summary for details.');
    process.exit(1);
  }
};

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
