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

const outputDir = path.resolve(params.output);
ensureDir(outputDir);

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

  const flows = JSON.parse(fs.readFileSync(path.join(__dirname, 'flows.json'), 'utf-8'));

  for (const flow of flows) {
    const screenDir = path.join(outputDir, flow.name);
    ensureDir(screenDir);

    for (const step of flow.steps) {
      /* eslint-disable no-await-in-loop */
      if (step.action === 'tap') {
        const element = await driver.$(step.selector);
        await element.waitForExist({ timeout: step.timeout ?? 10000 });
        await element.click();
      } else if (step.action === 'input') {
        const element = await driver.$(step.selector);
        await element.waitForExist({ timeout: step.timeout ?? 10000 });
        await element.setValue(step.value ?? '');
      } else if (step.action === 'back') {
        await driver.back();
      } else if (step.action === 'sleep') {
        await driver.pause(step.ms ?? 1000);
      }
    }

    await driver.saveScreenshot(path.join(screenDir, 'screenshot.png'));
    const source = await driver.getPageSource();
    fs.writeFileSync(path.join(screenDir, 'source.xml'), source, 'utf-8');
  }

  await driver.deleteSession();
};

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
